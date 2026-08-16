"""Mechanism-backed, public-safe R136 gateway over the accepted S0C ledger.

This module deliberately owns no durable truth: accepted durable input is a
strict SignalEvent admitted through DurableSignalLedger.  All other values are
derived receipts which can be rebuilt from their explicit inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence
import yaml


S0C_SRC = Path(__file__).resolve().parents[3] / "S0-SYNTHETIC" / "src"
if str(S0C_SRC) not in sys.path:
    sys.path.insert(0, str(S0C_SRC))
from global_signal_plane.models import SignalEvent, SignalLink, SignalPlaneError  # noqa: E402


class GatewayError(ValueError):
    """Stable public-safe error: no raw source body is included."""

    def __init__(self, code: str, path: str = "/", message: str = "gateway validation failed") -> None:
        super().__init__(message)
        self.code, self.path = code, path


PERSISTENCE = frozenset({"EPHEMERAL", "TRACE_ONLY", "DURABLE_SIGNAL"})
EXECUTION = frozenset({"DIRECT", "DOMAIN_WORKFLOW", "GOVERNED_MISSION"})
MATERIALITY = frozenset({"LOW", "MATERIAL", "HIGH_RISK"})
CLOSURES = frozenset({"PARTIALLY_SATISFIED", "SATISFIED", "BLOCKED", "NEEDS_REVALIDATION", "REVOKED", "SUPERSEDED"})
REQUIRED_ENVELOPE = frozenset({
    "envelope_id", "source_ref", "source_type", "source_project", "source_actor", "source_window_ref",
    "captured_at", "original_intent_ref", "public_safe_summary", "desired_effect", "problem_to_solve",
    "success_condition", "expected_problems", "risks", "assumptions", "unknowns", "dependencies",
    "evidence_refs", "counterevidence_refs", "privacy_scope_ref", "proposed_primary_domain",
    "proposed_related_domains", "persistence_class", "execution_class", "materiality_class", "epistemic_state",
})
SECRET_TOKENS = ("ghp_", "sk-", "password=", "-----begin private key", "api_key")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def instant(value: str, path: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise GatewayError("INVALID_TIMESTAMP", path) from exc
    if parsed.tzinfo is None:
        raise GatewayError("NAIVE_TIMESTAMP_FORBIDDEN", path)
    return parsed.astimezone(timezone.utc)


def public_safe(value: Any, path: str = "/") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key).lower() in {"raw_source_body", "token", "password", "private_key", "secret"}:
                raise GatewayError("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", f"{path}{key}")
            public_safe(child, f"{path}{key}/")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            public_safe(child, f"{path}{index}/")
    elif isinstance(value, str) and any(token in value.lower() for token in SECRET_TOKENS):
        raise GatewayError("PRIVATE_OR_SECRET_VALUE_FORBIDDEN", path)


def _require_axis(value: Any, choices: frozenset[str], path: str) -> str:
    if value not in choices:
        raise GatewayError("INVALID_CLASSIFICATION_AXIS", path)
    return str(value)


def semantic_capture(text: str) -> bool:
    """Small deterministic semantic cue set; explicit refusal always wins.

    It intentionally recognises Chinese and English capture intent aliases but
    does not turn ordinary discussion into a durable record by default.
    """
    normalized = " ".join(text.casefold().split())
    negative = ("不要记录", "不记录", "无需记录", "别记", "do not capture", "don't capture", "no capture")
    positive = ("记录这个", "记住这个", "采集记忆", "收集信号", "创建任务", "capture this", "remember this", "create task")
    return not any(item in normalized for item in negative) and any(item in normalized for item in positive)


def classify(envelope: Mapping[str, Any]) -> dict[str, str]:
    """Validate independent, explicit classification; only upgrades are automatic."""
    persistence = _require_axis(envelope.get("persistence_class"), PERSISTENCE, "/persistence_class")
    execution = _require_axis(envelope.get("execution_class"), EXECUTION, "/execution_class")
    materiality = _require_axis(envelope.get("materiality_class"), MATERIALITY, "/materiality_class")
    # High risk cannot be silently routed into a low-authority direct path.
    if materiality == "HIGH_RISK" and execution != "GOVERNED_MISSION":
        execution = "GOVERNED_MISSION"
    if execution == "GOVERNED_MISSION" and persistence != "DURABLE_SIGNAL":
        persistence = "DURABLE_SIGNAL"
    return {"persistence_class": persistence, "execution_class": execution, "materiality_class": materiality}


def validate_envelope(envelope: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise GatewayError("ENVELOPE_NOT_OBJECT")
    public_safe(envelope)
    missing = sorted(REQUIRED_ENVELOPE - set(envelope))
    if missing:
        raise GatewayError("MISSING_REQUIRED_FIELD", f"/{missing[0]}")
    instant(str(envelope["captured_at"]), "/captured_at")
    for name in ("envelope_id", "source_ref", "source_project", "source_actor", "public_safe_summary", "desired_effect", "success_condition"):
        if not isinstance(envelope[name], str) or not envelope[name].strip():
            raise GatewayError("INVALID_STRING", f"/{name}")
    for name in ("expected_problems", "risks", "assumptions", "unknowns", "dependencies", "evidence_refs", "counterevidence_refs", "proposed_related_domains"):
        if not isinstance(envelope[name], list):
            raise GatewayError("INVALID_ARRAY", f"/{name}")
    result = dict(envelope)
    result.update(classify(envelope))
    return result


@dataclass(frozen=True)
class SystemAwarenessProjection:
    snapshot_ref: str
    source_revisions: tuple[tuple[str, str], ...]
    nodes: tuple[dict[str, Any], ...]
    ledger_checksum: str
    derived_only: bool = True
    authority_granted: bool = False

    @classmethod
    def build(cls, sources: Mapping[str, Mapping[str, Any]], ledger_projection: Mapping[str, Any]) -> "SystemAwarenessProjection":
        nodes: list[dict[str, Any]] = []
        revisions: list[tuple[str, str]] = []
        for ref, source in sorted(sources.items()):
            if not isinstance(source.get("revision"), str):
                raise GatewayError("AWARENESS_SOURCE_REVISION_MISSING", f"/sources/{ref}")
            revisions.append((ref, source["revision"]))
            nodes.append({
                "component_id": source.get("component_id", ref), "component_kind": source.get("component_kind", "UNKNOWN"),
                "source_authority_ref": ref, "source_revision_or_commit": source["revision"],
                "capability_refs": list(source.get("capability_refs", [])), "authority_owner": source.get("authority_owner", "UNKNOWN"),
                "canonical_entrypoints": list(source.get("canonical_entrypoints", [])), "read_set_refs": list(source.get("read_set_refs", [])),
                "route_set_refs": list(source.get("route_set_refs", [])), "dependency_refs": list(source.get("dependency_refs", [])),
                "interface_refs": list(source.get("interface_refs", [])), "maturity": source.get("maturity", "UNKNOWN"),
                "current_phase": source.get("current_phase", "UNKNOWN"), "current_route_or_claim_ref": source.get("current_route_or_claim_ref", "UNKNOWN"),
                "read_boundary_refs": list(source.get("read_boundary_refs", [])), "write_boundary_refs": list(source.get("write_boundary_refs", [])),
                "regression_refs": list(source.get("regression_refs", [])), "unknown_refs": list(source.get("unknown_refs", [])),
                "relevant_open_signal_refs": list(source.get("relevant_open_signal_refs", [])),
            })
        ledger_checksum = str(ledger_projection.get("checksum", "UNKNOWN"))
        basis = {"revisions": revisions, "nodes": nodes, "ledger_checksum": ledger_checksum}
        return cls(f"awareness:{digest(basis)}", tuple(revisions), tuple(nodes), ledger_checksum)

    def is_current(self, sources: Mapping[str, Mapping[str, Any]]) -> bool:
        return all(sources.get(ref, {}).get("revision") == revision for ref, revision in self.source_revisions)


@dataclass(frozen=True)
class RuntimeInvocationReceipt:
    data: Mapping[str, Any]

    @classmethod
    def build(cls, *, execution_id: str, source_repository: str, source_commit: str, entry: Mapping[str, str],
              awareness: SystemAwarenessProjection, mandatory_reads: Sequence[str], actual_reads: Sequence[Mapping[str, Any]],
              outcome_quality: str = "NOT_YET_OBSERVED") -> "RuntimeInvocationReceipt":
        verified = []
        actual_paths = set()
        for read in actual_reads:
            required = {"repository", "commit", "path", "blob_sha_or_equivalent_content_identity", "content_sha256_or_equivalent_digest", "execution_id"}
            if required <= set(read) and read["repository"] == source_repository and read["commit"] == source_commit and read["execution_id"] == execution_id:
                verified.append(dict(read)); actual_paths.add(str(read["path"]))
        process = "PASS" if set(mandatory_reads) <= actual_paths else "UNVERIFIED"
        data = {
            "receipt_id": f"receipt:{digest([execution_id, source_commit, actual_reads])[:24]}", "execution_id": execution_id,
            "trace_id": f"trace:{digest(execution_id)[:24]}", "task_class": "DOMAIN_WORKFLOW", "domain_id": "AI_FILM_READ_ONLY",
            "started_at": "2026-08-16T00:00:00+00:00", "completed_at": "2026-08-16T00:00:01+00:00",
            "source_repository": source_repository, "source_commit": source_commit, "entry_contract_ref": entry["path"],
            "entry_contract_blob_or_content_digest": entry["blob_sha"], "system_awareness_snapshot_ref": awareness.snapshot_ref,
            "matched_route_refs": [], "mandatory_reads_resolved": list(mandatory_reads), "actual_reads": verified,
            "mandatory_scans": [], "actual_scans": [], "capability_invocations": [], "ruleset_digest": digest({"entry": entry, "awareness": awareness.snapshot_ref}),
            "warnings": [] if process == "PASS" else ["MANDATORY_READ_UNPROVEN"], "unknowns": [] if process == "PASS" else ["actual reads self-declared or incomplete"],
            "result_ref": "opaque://read-only-smoke", "validation_result": "VERIFIED" if process == "PASS" else "UNVERIFIED",
            "writeback_decision": "TRACE_ONLY", "process_compliance": process, "outcome_quality": outcome_quality,
            "evidence_refs": [f"git://{source_repository}@{source_commit}/{item['path']}" for item in verified], "privacy_scope_ref": "PUBLIC_SAFE_METADATA_ONLY",
        }
        return cls(data)


def exact_git_read_records(root: str | Path, *, repository: str, commit: str, paths: Sequence[str], execution_id: str) -> list[dict[str, str]]:
    """Create actual-read evidence from Git object identities, never raw content.

    The caller provides a local checked-out read-only exact source.  Worktree
    payloads are compared to ``git show`` so a file merely existing locally is
    not sufficient evidence.  Returned metadata is public-safe digest only.
    """
    source = Path(root).resolve()
    def git(*args: str, binary: bool = False) -> str | bytes:
        completed = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=False)
        if completed.returncode:
            raise GatewayError("EXACT_SOURCE_READ_FAILED")
        return completed.stdout if binary else completed.stdout.decode("utf-8", errors="strict").strip()
    if Path(str(git("rev-parse", "--show-toplevel"))).resolve() != source:
        raise GatewayError("SOURCE_ROOT_NOT_REPOSITORY_ROOT")
    if str(git("rev-parse", "HEAD")) != commit:
        raise GatewayError("SOURCE_REVISION_DRIFT")
    records: list[dict[str, str]] = []
    for path in paths:
        if path.startswith("/") or ".." in Path(path).parts:
            raise GatewayError("FORBIDDEN_SOURCE_PATH")
        blob = str(git("rev-parse", f"{commit}:{path}"))
        committed = git("show", f"{commit}:{path}", binary=True)
        assert isinstance(committed, bytes)
        try:
            local = (source / path).read_bytes()
        except OSError as exc:
            raise GatewayError("SOURCE_PATH_UNREADABLE") from exc
        if local != committed:
            raise GatewayError("SOURCE_WORKTREE_PAYLOAD_MISMATCH")
        records.append({"repository": repository, "commit": commit, "path": path,
                        "blob_sha_or_equivalent_content_identity": blob,
                        "content_sha256_or_equivalent_digest": hashlib.sha256(committed).hexdigest(),
                        "execution_id": execution_id})
    return records


AI_FILM_DIRECTING_PATHS = (
    "PROJECT_INDEX.yaml",
    "10_\u8fd0\u884c\u65f6/read_sets.yaml",
    "10_\u8fd0\u884c\u65f6/director_route_index.yaml",
    "11_\u9a8c\u6536/director_regression_cases.yaml",
)


def ai_film_directing_read_only_smoke(root: str | Path, *, awareness: SystemAwarenessProjection, execution_id: str = "r136-ai-film-read-only-smoke") -> dict[str, Any]:
    """Perform the R136 exact-source smoke and return opaque proof only.

    This does not create a Signal, call a domain write, or expose source text.
    It validates that the declared ``read_sets.directing`` structure exists
    within the exact Git object and produces a trace-only receipt.
    """
    repository = "vxz2datoubo/eustia-ai-film"
    commit = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
    records = exact_git_read_records(root, repository=repository, commit=commit, paths=AI_FILM_DIRECTING_PATHS, execution_id=execution_id)
    source = Path(root).resolve()
    completed = subprocess.run(["git", "-C", str(source), "show", f"{commit}:{AI_FILM_DIRECTING_PATHS[1]}"], capture_output=True, check=False)
    if completed.returncode:
        raise GatewayError("READ_SET_UNAVAILABLE")
    try:
        document = yaml.safe_load(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError) as exc:
        raise GatewayError("READ_SET_PARSE_FAILED") from exc
    read_sets = document.get("read_sets") if isinstance(document, Mapping) else None
    if not isinstance(read_sets, Mapping) or not isinstance(read_sets.get("directing"), (Mapping, list)):
        raise GatewayError("DIRECTING_READ_SET_UNRESOLVED")
    entry = {"path": AI_FILM_DIRECTING_PATHS[0], "blob_sha": records[0]["blob_sha_or_equivalent_content_identity"]}
    receipt = RuntimeInvocationReceipt.build(execution_id=execution_id, source_repository=repository, source_commit=commit, entry=entry, awareness=awareness,
                                              mandatory_reads=AI_FILM_DIRECTING_PATHS, actual_reads=records)
    return {"receipt": dict(receipt.data), "source_binding": {"repository": repository, "commit": commit,
            "authority_path": "PROJECT_INDEX.yaml", "authority_blob_sha": entry["blob_sha"]},
            "directing_read_set_resolved": True, "fixture_ref": f"git://{repository}@{commit}/{AI_FILM_DIRECTING_PATHS[3]}",
            "durable_signal_created": False, "domain_write_authorized": False, "raw_content_published": False}


class SignalIntakeGateway:
    def __init__(self, ledger: Any) -> None:
        self.ledger = ledger

    def intake(self, envelope: Mapping[str, Any], *, request_text: str, explicit_capture: bool | None = None) -> dict[str, Any]:
        checked = validate_envelope(envelope)
        capture = semantic_capture(request_text) if explicit_capture is None else bool(explicit_capture)
        if not capture:
            return {"status": "NOT_CAPTURED", "reason": "EXPLICIT_NO_CAPTURE_OR_NO_SEMANTIC_CAPTURE", "effective_state_changed": False}
        route = classify(checked)
        if route["persistence_class"] != "DURABLE_SIGNAL":
            return {"status": "TRACE_ONLY", "route": route, "effective_state_changed": False}
        event_id = f"r136:{checked['envelope_id']}"
        event_payload = {
            "schema_version": "SignalEvent/v1", "signal_id": f"signal:{checked['envelope_id']}", "event_id": event_id,
            "event_source": "R136_EXPLICIT_INTAKE", "event_type": "EXPLICIT_SIGNAL_CAPTURE", "occurred_at": checked["captured_at"], "observed_at": checked["captured_at"],
            "source_type": checked["source_type"], "source_ref": checked["source_ref"], "source_project": checked["source_project"], "source_actor": checked["source_actor"],
            "primary_domain": checked["proposed_primary_domain"], "related_domains": checked["proposed_related_domains"], "signal_kind": "REQUIREMENT",
            "planning_state": "CAPTURED", "execution_state": "NOT_STARTED", "epistemic_state": checked["epistemic_state"], "privacy_scope_ref": checked["privacy_scope_ref"],
            "authority_targets": [], "touch_set": ["S0E_EXPLICIT_INTAKE"], "related_signal_refs": [], "supersedes_refs": [], "revokes_refs": [], "cross_domain_candidate": False,
            "summary_ref": checked["original_intent_ref"], "idempotency_key": f"r136-envelope:{checked['envelope_id']}", "payload_schema_ref": "SignalIntakeEnvelope/v1",
            "public_safe_metadata": {"envelope_id": checked["envelope_id"], "desired_effect_ref": f"digest:{digest(checked['desired_effect'])}", "success_condition_ref": f"digest:{digest(checked['success_condition'])}", "route": route},
        }
        receipt = self.ledger.ingest(SignalEvent.from_dict(event_payload))
        return {"status": receipt["status"], "route": route, "event_id": event_id, "signal_id": event_payload["signal_id"], "ledger_receipt": receipt}

    def relate(self, *, signal_ref: str, target_ref: str, relation: str, at: str) -> dict[str, Any]:
        instant(at, "/at")
        if relation not in {"SUPERSEDES", "REVOKES", "CONTRADICTS"}:
            raise GatewayError("INVALID_CORRECTION_RELATION", "/relation")
        link = SignalLink.from_dict({"link_id": f"r136-link:{digest([signal_ref,target_ref,relation])[:24]}", "from_signal_ref": signal_ref, "to_signal_ref": target_ref,
            "relation_type": "SUPERSEDES" if relation in {"SUPERSEDES", "REVOKES"} else "CONTRADICTS", "evidence_refs": [f"opaque://r136/{relation.lower()}"], "created_at": at, "created_by": "CODEX"})
        return self.ledger.append_link(link)

    def preflight(self, *, awareness: SystemAwarenessProjection, sources: Mapping[str, Mapping[str, Any]], reconciliation_receipt: Mapping[str, Any] | None, material_conflicts: Sequence[str]) -> dict[str, Any]:
        if not awareness.is_current(sources):
            return {"status": "BLOCKED", "code": "STALE_SYSTEM_AWARENESS", "can_release": False}
        if not reconciliation_receipt or reconciliation_receipt.get("status") != "VALID" or reconciliation_receipt.get("ledger_checksum") != awareness.ledger_checksum:
            return {"status": "BLOCKED", "code": "NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT", "can_release": False}
        if material_conflicts:
            return {"status": "BLOCKED", "code": "MATERIAL_CONFLICT_UNRESOLVED", "can_release": False, "conflicts": list(material_conflicts)}
        return {"status": "PASS", "can_release": True, "reconciliation_receipt_ref": reconciliation_receipt.get("receipt_ref"), "authority_granted": False}

    def release(self, *, preflight: Mapping[str, Any], included_signal_refs: Sequence[str], awareness: SystemAwarenessProjection) -> dict[str, Any]:
        if not preflight.get("can_release"):
            raise GatewayError("FORMAL_RELEASE_PRECHECK_FAILED")
        return {"packet_id": f"release:{digest([included_signal_refs, awareness.snapshot_ref])[:24]}", "mission_candidate_ref": "candidate://r136", "included_signal_refs": list(included_signal_refs), "cluster_refs": [], "desired_effects": [], "success_conditions": [], "merge_keep_separate_rationale": "no automatic merge", "resolved_conflicts": [], "unresolved_conflicts": [], "dependencies": [], "can_parallel_refs": [], "must_serialize_refs": [], "reviewer_or_challenger_requirements": ["CONTROL_TOWER_REVIEW"], "counterfactual_requirements": [], "expected_problems": [], "risks": [], "unknowns": ["CONTROL_TOWER_AUTHORIZATION_REQUIRED"], "required_capability_refs": [], "required_read_set_refs": [], "authority_refs": [], "exact_system_snapshot_ref": awareness.snapshot_ref, "exact_repository_state_refs": [], "route_claim_lane_refs": [], "reconciliation_receipt_ref": preflight["reconciliation_receipt_ref"], "control_tower_required": True, "execution_authorized": False}

    def assess_closure(self, *, signal_ref: str, state: str, effect_evidence_refs: Sequence[str], task_done: bool) -> dict[str, Any]:
        if state not in CLOSURES:
            raise GatewayError("INVALID_CLOSURE_STATE", "/state")
        if state == "SATISFIED" and (not effect_evidence_refs or not task_done):
            raise GatewayError("SATISFACTION_EFFECT_EVIDENCE_REQUIRED")
        return {"assessment_id": f"closure:{digest([signal_ref,state,effect_evidence_refs])[:24]}", "signal_ref": signal_ref, "state": state, "effect_evidence_refs": list(effect_evidence_refs), "task_done": task_done, "append_only": True, "history_retained": True, "authorizes_promotion": False}
