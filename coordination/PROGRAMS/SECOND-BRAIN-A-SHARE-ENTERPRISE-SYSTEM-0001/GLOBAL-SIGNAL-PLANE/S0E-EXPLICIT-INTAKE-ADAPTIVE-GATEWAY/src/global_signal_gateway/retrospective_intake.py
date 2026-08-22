"""R142 public-safe retrospective Signal import, reconciliation, and durable bridge.

This is a thin last-mile layer. It never owns effective Signal truth. Only a
candidate reconciled as NEW_DURABLE_SIGNAL against authority-bound current
observation may cross the existing R136 SignalIntakeGateway into the
caller-supplied existing S0C DurableSignalLedger.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from .domain_authority import authority_evidence_is_bound, resolve_candidate_domain_authority
from .gateway import (
    GatewayError,
    SIGNAL_KINDS,
    SignalIntakeGateway,
    validate_exact_read_proof,
    validate_live_observation_proof,
)
from global_signal_plane.models import SignalPlaneError


CANONICAL_REPOSITORY = "vxz2datoubo/second-brain-coordination"
S0E_GATEWAY_PATH = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src/global_signal_gateway/gateway.py"
REQUIRED_NEW_EXACT_PATHS = (
    "coordination/ACTIVE-CODEX-TASK.yaml",
    "coordination/ACTIVE-PROGRAM-LANES.yaml",
    "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
    "coordination/PROGRAM-CONTROL-TOWER.md",
    S0E_GATEWAY_PATH,
)
SURFACE_EXACT_PATHS = {
    "current_tasks": ("coordination/ACTIVE-CODEX-TASK.yaml",),
    "current_missions": ("coordination/ACTIVE-PROGRAM-LANES.yaml", "coordination/PROGRAM-CONTROL-TOWER.md"),
    "r136_r141_capabilities": (S0E_GATEWAY_PATH, "coordination/PROGRAM-CONTROL-TOWER.md"),
    "dependencies_conflicts_supersession": ("coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml", "coordination/ACTIVE-PROGRAM-LANES.yaml"),
}


class RetrospectiveIntakeError(ValueError):
    """Stable fail-closed R142 error that never echoes private source bodies."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


DISPOSITIONS = frozenset({
    "NEW_DURABLE_SIGNAL", "ALREADY_CANONICAL", "ALREADY_SATISFIED", "DUPLICATE",
    "EXTENDS", "REINFORCES", "CONTRADICTS", "SUPERSEDED", "DOMAIN_CANONICAL_ONLY",
    "NEEDS_REVALIDATION", "REJECT_PRIVATE_OR_UNSAFE", "INSUFFICIENT_PROVENANCE",
})
REQUIRED_CANDIDATE_FIELDS = frozenset({
    "candidate_id", "source_window_ref", "source_message_ref", "source_project",
    "source_time_range", "public_safe_summary", "original_intent_ref", "signal_kind",
    "epistemic_state", "desired_effect", "problem_to_solve", "success_condition",
    "expected_problems", "risks", "assumptions", "unknowns", "dependencies",
    "evidence_refs", "counterevidence_refs", "proposed_primary_domain", "related_domains",
    "privacy_scope", "historical_status", "candidate_relations",
    "model_tool_version_work_item_refs",
})
ARRAY_FIELDS = (
    "expected_problems", "risks", "assumptions", "unknowns", "dependencies",
    "evidence_refs", "counterevidence_refs", "related_domains", "candidate_relations",
)
STRING_FIELDS = (
    "candidate_id", "source_window_ref", "source_message_ref", "source_project",
    "public_safe_summary", "original_intent_ref", "signal_kind", "epistemic_state",
    "desired_effect", "problem_to_solve", "success_condition", "proposed_primary_domain",
    "privacy_scope", "historical_status",
)
ALLOWED_EPISTEMIC_STATES = frozenset({
    "USER_EXPLICIT", "CONFIRMED_FACT", "HIGH_CONFIDENCE_INFERENCE",
    "CANDIDATE_HYPOTHESIS", "UNKNOWN", "NEEDS_REVALIDATION",
})
PRIVATE_FIELD_NAMES = frozenset({
    "raw_source_body", "private_chain_of_thought", "token", "password", "private_key",
    "secret", "api_key", "access_token",
})
SECRET_MARKERS = ("ghp_", "password=", "-----begin private key", "api_key=")
SK_SECRET_PATTERN = re.compile(r"(?<![a-z0-9])sk-[a-z0-9_-]+", re.IGNORECASE)
REQUIRED_SCAN_SURFACES = frozenset({
    "current_signals", "historical_signals", "current_tasks", "current_missions",
    "issues_pr_reviews", "r136_r141_capabilities", "domain_canonical",
    "dependencies_conflicts_supersession",
})
EVIDENCE_ARRAY_FIELDS = (
    "current_signal_refs", "historical_signal_refs", "satisfied_refs", "duplicate_refs",
    "extends_refs", "reinforces_refs", "contradicts_refs", "superseded_refs",
    "domain_canonical_refs", "needs_revalidation_refs", "active_dependency_refs",
    "closed_task_refs", "issue_pr_review_refs", "capability_refs",
)
EVIDENCE_BOOLEAN_FIELDS = ("provenance_complete", "desired_effect_unmet")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def _timestamp(value: str, path: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise RetrospectiveIntakeError("INVALID_TIMESTAMP", path) from exc
    if parsed.tzinfo is None:
        raise RetrospectiveIntakeError("NAIVE_TIMESTAMP_FORBIDDEN", path)


def _safe(value: Any, path: str = "/") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}{key}"
            if str(key).casefold() in PRIVATE_FIELD_NAMES:
                raise RetrospectiveIntakeError("PRIVATE_OR_UNSAFE", child_path)
            _safe(child, f"{child_path}/")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _safe(child, f"{path}{index}/")
    elif isinstance(value, str):
        folded = value.casefold()
        if any(marker in folded for marker in SECRET_MARKERS) or SK_SECRET_PATTERN.search(value):
            raise RetrospectiveIntakeError("PRIVATE_OR_UNSAFE", path)


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RetrospectiveIntakeError("INVALID_STRING", path)
    return value


def _candidate_time(candidate: Mapping[str, Any]) -> str | None:
    value = candidate.get("source_time_range")
    if value == "UNKNOWN":
        return None
    if not isinstance(value, Mapping):
        raise RetrospectiveIntakeError("INVALID_SOURCE_TIME_RANGE", "/source_time_range")
    chosen = value.get("end") if value.get("end") not in (None, "UNKNOWN") else value.get("start")
    if chosen in (None, "UNKNOWN"):
        return None
    _string(chosen, "/source_time_range")
    _timestamp(chosen, "/source_time_range")
    return chosen


def validate_candidate(candidate: Mapping[str, Any], *, index: int = 0) -> dict[str, Any]:
    path = f"/candidates/{index}/"
    if not isinstance(candidate, Mapping):
        raise RetrospectiveIntakeError("CANDIDATE_NOT_OBJECT", path)
    _safe(candidate, path)
    missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(candidate))
    if missing:
        raise RetrospectiveIntakeError("MISSING_REQUIRED_FIELD", f"{path}{missing[0]}")
    unexpected = sorted(set(candidate) - REQUIRED_CANDIDATE_FIELDS)
    if unexpected:
        raise RetrospectiveIntakeError("UNRECOGNIZED_FIELD", f"{path}{unexpected[0]}")
    out = json.loads(canonical(dict(candidate)))
    for field in STRING_FIELDS:
        _string(out[field], f"{path}{field}")
    for field in ARRAY_FIELDS:
        if not isinstance(out[field], list):
            raise RetrospectiveIntakeError("INVALID_ARRAY", f"{path}{field}")
    if out["signal_kind"] not in SIGNAL_KINDS:
        raise RetrospectiveIntakeError("INVALID_SIGNAL_KIND", f"{path}signal_kind")
    if out["epistemic_state"] not in ALLOWED_EPISTEMIC_STATES:
        raise RetrospectiveIntakeError("INVALID_EPISTEMIC_STATE", f"{path}epistemic_state")
    if out["source_time_range"] != "UNKNOWN":
        if not isinstance(out["source_time_range"], Mapping):
            raise RetrospectiveIntakeError("INVALID_SOURCE_TIME_RANGE", f"{path}source_time_range")
        if set(out["source_time_range"]) - {"start", "end"}:
            raise RetrospectiveIntakeError("INVALID_SOURCE_TIME_RANGE", f"{path}source_time_range")
        for bound, value in out["source_time_range"].items():
            if value != "UNKNOWN":
                _string(value, f"{path}source_time_range/{bound}")
                _timestamp(value, f"{path}source_time_range/{bound}")
    _candidate_time(out)
    refs = out["model_tool_version_work_item_refs"]
    if refs != "UNKNOWN" and not isinstance(refs, Mapping):
        raise RetrospectiveIntakeError("INVALID_MODEL_TOOL_REFS", f"{path}model_tool_version_work_item_refs")
    for number, relation in enumerate(out["candidate_relations"]):
        if not isinstance(relation, Mapping):
            raise RetrospectiveIntakeError("INVALID_CANDIDATE_RELATION", f"{path}candidate_relations/{number}")
        if not isinstance(relation.get("relation"), str) or not isinstance(relation.get("target_ref"), str):
            raise RetrospectiveIntakeError("INVALID_CANDIDATE_RELATION", f"{path}candidate_relations/{number}")
        if not isinstance(relation.get("evidence_refs", []), list):
            raise RetrospectiveIntakeError("INVALID_CANDIDATE_RELATION", f"{path}candidate_relations/{number}/evidence_refs")
    out["candidate_digest"] = digest(out)
    return out


def validate_import_package(package: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(package, Mapping):
        raise RetrospectiveIntakeError("PACKAGE_NOT_OBJECT")
    required = {"schema_version", "import_batch_id", "generated_at", "source_window_ref", "candidates"}
    missing = sorted(required - set(package))
    if missing:
        raise RetrospectiveIntakeError("MISSING_REQUIRED_FIELD", f"/{missing[0]}")
    if set(package) - (required | {"expected_canonical_main", "package_metadata"}):
        raise RetrospectiveIntakeError("UNRECOGNIZED_FIELD", "/")
    if package["schema_version"] != "SignalImportPackage/v1":
        raise RetrospectiveIntakeError("INVALID_PACKAGE_SCHEMA", "/schema_version")
    for field in ("import_batch_id", "generated_at", "source_window_ref"):
        _string(package[field], f"/{field}")
    _timestamp(package["generated_at"], "/generated_at")
    if "expected_canonical_main" in package:
        _string(package["expected_canonical_main"], "/expected_canonical_main")
    if not isinstance(package["candidates"], list) or not package["candidates"]:
        raise RetrospectiveIntakeError("CANDIDATES_REQUIRED", "/candidates")
    if "package_metadata" in package:
        _safe(package["package_metadata"], "/package_metadata/")
    normalized: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    for index, raw in enumerate(package["candidates"]):
        candidate_id = raw.get("candidate_id") if isinstance(raw, Mapping) else f"INVALID_INDEX_{index}"
        try:
            item = validate_candidate(raw, index=index)
        except RetrospectiveIntakeError as exc:
            errors.append({"candidate_id": str(candidate_id or f"INVALID_INDEX_{index}"), "code": exc.code, "path": exc.path})
            continue
        prior = seen.get(item["candidate_id"])
        if prior is not None:
            code = "DUPLICATE_CANDIDATE_IN_BATCH" if prior == item["candidate_digest"] else "CANDIDATE_ID_COLLISION"
            errors.append({"candidate_id": item["candidate_id"], "code": code, "path": f"/candidates/{index}/candidate_id"})
            continue
        seen[item["candidate_id"]] = item["candidate_digest"]
        normalized.append(item)
    return {
        "schema_version": "SignalImportPackage/v1",
        "import_batch_id": package["import_batch_id"],
        "source_window_ref": package["source_window_ref"],
        "generated_at": package["generated_at"],
        "expected_canonical_main": package.get("expected_canonical_main", "UNKNOWN"),
        "package_digest": digest(package),
        "candidates": normalized,
        "candidate_errors": errors,
    }


def validate_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise RetrospectiveIntakeError("SNAPSHOT_NOT_OBJECT")
    _safe(snapshot, "/snapshot/")
    required = {"schema_version", "snapshot_id", "canonical_main", "observed_at", "source_provenance_refs", "scan_coverage", "candidate_evidence"}
    missing = sorted(required - set(snapshot))
    if missing:
        raise RetrospectiveIntakeError("MISSING_REQUIRED_FIELD", f"/snapshot/{missing[0]}")
    if snapshot["schema_version"] != "CurrentCanonicalSnapshot/v1":
        raise RetrospectiveIntakeError("INVALID_SNAPSHOT_SCHEMA", "/snapshot/schema_version")
    for field in ("snapshot_id", "canonical_main", "observed_at"):
        _string(snapshot[field], f"/snapshot/{field}")
    _timestamp(snapshot["observed_at"], "/snapshot/observed_at")
    if not isinstance(snapshot["source_provenance_refs"], list) or not snapshot["source_provenance_refs"]:
        raise RetrospectiveIntakeError("SNAPSHOT_PROVENANCE_REQUIRED", "/snapshot/source_provenance_refs")
    coverage = snapshot["scan_coverage"]
    if not isinstance(coverage, Mapping) or set(coverage) != REQUIRED_SCAN_SURFACES:
        raise RetrospectiveIntakeError("INCOMPLETE_SCAN_COVERAGE", "/snapshot/scan_coverage")
    for surface, record in coverage.items():
        if not isinstance(record, Mapping) or record.get("status") != "SCANNED":
            raise RetrospectiveIntakeError("INCOMPLETE_SCAN_COVERAGE", f"/snapshot/scan_coverage/{surface}")
        if not isinstance(record.get("evidence_refs"), list) or not record["evidence_refs"]:
            raise RetrospectiveIntakeError("INVALID_SCAN_EVIDENCE", f"/snapshot/scan_coverage/{surface}/evidence_refs")
    if not isinstance(snapshot["candidate_evidence"], Mapping):
        raise RetrospectiveIntakeError("INVALID_CANDIDATE_EVIDENCE", "/snapshot/candidate_evidence")
    out = json.loads(canonical(dict(snapshot)))
    out["snapshot_digest"] = digest(out)
    return out


def _evidence(candidate_id: str, value: Any) -> dict[str, Any]:
    path = f"/snapshot/candidate_evidence/{candidate_id}/"
    if not isinstance(value, Mapping):
        raise RetrospectiveIntakeError("CANDIDATE_EVIDENCE_REQUIRED", path)
    for field in EVIDENCE_ARRAY_FIELDS:
        if field not in value or not isinstance(value[field], list):
            raise RetrospectiveIntakeError("INVALID_EVIDENCE_ARRAY", f"{path}{field}")
    for field in EVIDENCE_BOOLEAN_FIELDS:
        if field not in value or not isinstance(value[field], bool):
            raise RetrospectiveIntakeError("INVALID_EVIDENCE_BOOLEAN", f"{path}{field}")
    if "authority_domain_id" in value and (not isinstance(value["authority_domain_id"], str) or not value["authority_domain_id"].strip()):
        raise RetrospectiveIntakeError("INVALID_AUTHORITY_DOMAIN_ID", f"{path}authority_domain_id")
    if "authority_evidence_refs" in value and (
        not isinstance(value["authority_evidence_refs"], list)
        or not all(isinstance(ref, str) and ref.strip() for ref in value["authority_evidence_refs"])
    ):
        raise RetrospectiveIntakeError("INVALID_AUTHORITY_EVIDENCE_REFS", f"{path}authority_evidence_refs")
    _safe(value, path)
    return json.loads(canonical(dict(value)))


def _minimum_provenance(candidate: Mapping[str, Any]) -> bool:
    required = (candidate["source_window_ref"], candidate["source_message_ref"], candidate["source_project"], candidate["original_intent_ref"])
    if any(value == "UNKNOWN" for value in required) or _candidate_time(candidate) is None:
        return False
    return any(isinstance(ref, str) and ref not in ("", "UNKNOWN") for ref in candidate["evidence_refs"])


def _exact_ref(proof: Any) -> str:
    return f"git://{proof.repository}@{proof.commit}/{proof.path}#blob={proof.blob_sha};sha256={proof.content_sha256}"


def _s0c_projection_observation(ledger: Any) -> tuple[str, Mapping[str, Any]] | None:
    if ledger is None or not all(hasattr(ledger, name) for name in ("history", "current_projection", "rebuild_projection", "current_projection_version", "input_revision")):
        return None
    projection = ledger.current_projection()
    if projection is None:
        projection = ledger.rebuild_projection(expected_version=ledger.current_projection_version())
    if not isinstance(projection, Mapping) or not projection.get("checksum") or not projection.get("reducer_version"):
        return None
    history = ledger.history()
    if projection.get("ledger_watermark") != len(history) or projection.get("input_revision") != ledger.input_revision():
        return None
    ref = (
        f"s0c://projection/{projection['reducer_version']}/{projection['ledger_watermark']}"
        f"#sha256={projection['checksum']};input_revision={projection['input_revision']}"
    )
    return ref, projection


def governed_snapshot_refs(*, expected_canonical_main: str, live_observation_proof: Any,
                             exact_read_proofs: Sequence[Any], ledger: Any) -> dict[str, Any]:
    """Derive usable evidence refs only from existing sealed providers and the real S0C projection."""
    if not validate_live_observation_proof(live_observation_proof):
        return {"valid": False, "reason": "AUTHORITY_BOUND_LIVE_OBSERVATION_REQUIRED", "refs": []}
    if live_observation_proof.repository != CANONICAL_REPOSITORY or live_observation_proof.current_main_sha != expected_canonical_main:
        return {"valid": False, "reason": "LIVE_OBSERVATION_CANONICAL_BINDING_MISMATCH", "refs": []}
    accepted = [proof for proof in exact_read_proofs if validate_exact_read_proof(
        proof, repository=CANONICAL_REPOSITORY, commit=expected_canonical_main
    )]
    by_path = {proof.path: proof for proof in accepted}
    if not set(REQUIRED_NEW_EXACT_PATHS) <= set(by_path):
        return {"valid": False, "reason": "EXACT_CANONICAL_READ_PROOF_REQUIRED", "refs": []}
    s0c = _s0c_projection_observation(ledger)
    if s0c is None:
        return {"valid": False, "reason": "S0C_CURRENT_PROJECTION_PROOF_REQUIRED", "refs": []}
    s0c_ref, projection = s0c
    exact_refs_by_path = {path: _exact_ref(proof) for path, proof in by_path.items()}
    provider_refs = {live_observation_proof.provider_attribution_ref, *live_observation_proof.exact_refs}
    return {
        "valid": True,
        "reason": "AUTHORITY_BOUND_CURRENT_OBSERVATION_VERIFIED",
        "provider_refs": sorted(provider_refs),
        "exact_read_refs": sorted(exact_refs_by_path.values()),
        "exact_refs_by_path": exact_refs_by_path,
        "s0c_projection_ref": s0c_ref,
        "refs": sorted(provider_refs | set(exact_refs_by_path.values()) | {s0c_ref}),
        "s0c_projection": projection,
    }


def _new_admission_binding(snapshot: Mapping[str, Any], *, expected_canonical_main: str,
                           live_observation_proof: Any, exact_read_proofs: Sequence[Any], ledger: Any) -> dict[str, Any]:
    binding = governed_snapshot_refs(
        expected_canonical_main=expected_canonical_main,
        live_observation_proof=live_observation_proof,
        exact_read_proofs=exact_read_proofs,
        ledger=ledger,
    )
    if not binding["valid"]:
        return binding
    provenance = set(map(str, snapshot.get("source_provenance_refs", [])))
    provider_refs = set(binding["provider_refs"])
    exact_refs = set(binding["exact_read_refs"])
    exact_by_path = binding["exact_refs_by_path"]
    s0c_ref = str(binding["s0c_projection_ref"])
    if live_observation_proof.provider_attribution_ref not in provenance or s0c_ref not in provenance or not provenance.intersection(exact_refs):
        return {"valid": False, "reason": "SNAPSHOT_NOT_BOUND_TO_GOVERNED_OBSERVATION", "refs": binding["refs"]}
    coverage = snapshot["scan_coverage"]
    for surface in REQUIRED_SCAN_SURFACES:
        refs = set(map(str, coverage[surface]["evidence_refs"]))
        if surface in {"current_signals", "historical_signals"}:
            if s0c_ref not in refs:
                return {"valid": False, "reason": "S0C_SCAN_EVIDENCE_NOT_BOUND", "refs": binding["refs"]}
        elif surface in {"issues_pr_reviews", "domain_canonical"}:
            if not refs.intersection(provider_refs):
                return {"valid": False, "reason": "LIVE_PROVIDER_EVIDENCE_NOT_BOUND", "refs": binding["refs"]}
        else:
            required_paths = SURFACE_EXACT_PATHS.get(surface, ())
            required_refs = {exact_by_path[path] for path in required_paths}
            if not required_refs or not refs.intersection(required_refs):
                return {"valid": False, "reason": "CANONICAL_SCAN_EVIDENCE_NOT_BOUND", "refs": binding["refs"]}
    return binding


def _decision(candidate: Mapping[str, Any], disposition: str, reason: str,
              evidence: Mapping[str, Any] | None = None, authority_refs: Sequence[str] = ()) -> dict[str, Any]:
    if disposition not in DISPOSITIONS:
        raise RetrospectiveIntakeError("INVALID_DISPOSITION")
    evidence = evidence or {}
    refs = sorted({str(ref) for field in EVIDENCE_ARRAY_FIELDS for ref in evidence.get(field, []) if isinstance(ref, str)})
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "primary_domain": candidate["proposed_primary_domain"],
        "disposition": disposition,
        "reason": reason,
        "evidence_refs": refs,
        "authority_evidence_refs": sorted(set(map(str, authority_refs))),
        "dependency_refs": list(evidence.get("active_dependency_refs", [])),
        "closed_task_refs": list(evidence.get("closed_task_refs", [])),
        "historical_status": candidate["historical_status"],
    }


def reconcile_candidate(candidate: Mapping[str, Any], snapshot: Mapping[str, Any], *, expected_canonical_main: str,
                        live_observation_proof: Any = None, exact_read_proofs: Sequence[Any] = (), ledger: Any = None) -> dict[str, Any]:
    if snapshot["canonical_main"] != expected_canonical_main:
        return _decision(candidate, "NEEDS_REVALIDATION", "STALE_CANONICAL_SNAPSHOT")
    try:
        ev = _evidence(candidate["candidate_id"], snapshot["candidate_evidence"].get(candidate["candidate_id"]))
    except RetrospectiveIntakeError as exc:
        return _decision(candidate, "INSUFFICIENT_PROVENANCE", exc.code)
    if not ev["provenance_complete"] or not _minimum_provenance(candidate):
        return _decision(candidate, "INSUFFICIENT_PROVENANCE", "PROVENANCE_INCOMPLETE", ev)

    domain_binding = resolve_candidate_domain_authority(
        candidate,
        snapshot,
        expected_canonical_main=expected_canonical_main,
        coordinator_repository=CANONICAL_REPOSITORY,
    )
    if not domain_binding.get("valid"):
        return _decision(
            candidate, "NEEDS_REVALIDATION", str(domain_binding.get("reason", "DOMAIN_ROUTE_UNRESOLVED")),
            ev, domain_binding.get("authority_refs", []),
        )
    if not authority_evidence_is_bound(ev, domain_binding):
        return _decision(candidate, "NEEDS_REVALIDATION", "DOMAIN_AUTHORITY_EVIDENCE_NOT_BOUND", ev, domain_binding["authority_refs"])
    owner_refs = list(domain_binding["authority_refs"])

    s0c = _s0c_projection_observation(ledger)
    if s0c is not None:
        s0c_ref, projection = s0c
        expected_signal_id = f"signal:r142-{candidate['candidate_id']}"
        if any(item.get("signal_id") == expected_signal_id for item in projection.get("signals", [])):
            return _decision(candidate, "ALREADY_CANONICAL", "S0C_CURRENT_PROJECTION_ALREADY_CONTAINS_CANDIDATE", ev, [*owner_refs, s0c_ref])
    precedence: Sequence[tuple[str, str, str]] = (
        ("superseded_refs", "SUPERSEDED", "CURRENT_CANONICAL_SUPERSESSION"),
        ("contradicts_refs", "CONTRADICTS", "CURRENT_CONTRADICTION_REQUIRES_REVIEW"),
        ("satisfied_refs", "ALREADY_SATISFIED", "DESIRED_EFFECT_ALREADY_SATISFIED"),
        ("current_signal_refs", "ALREADY_CANONICAL", "CURRENT_SIGNAL_ALREADY_CANONICAL"),
        ("duplicate_refs", "DUPLICATE", "CURRENT_CANONICAL_DUPLICATE"),
        ("domain_canonical_refs", "DOMAIN_CANONICAL_ONLY", "BELONGS_TO_DOMAIN_CANONICAL_ONLY"),
        ("needs_revalidation_refs", "NEEDS_REVALIDATION", "CURRENT_EVIDENCE_REQUIRES_REVALIDATION"),
        ("extends_refs", "EXTENDS", "EXTENDS_EXISTING_CANONICAL_SIGNAL"),
        ("reinforces_refs", "REINFORCES", "REINFORCES_EXISTING_CANONICAL_SIGNAL"),
    )
    for field, disposition, reason in precedence:
        if ev[field]:
            return _decision(candidate, disposition, reason, ev, owner_refs)
    if not ev["desired_effect_unmet"]:
        return _decision(candidate, "NEEDS_REVALIDATION", "NO_EVIDENCE_FOR_SAFE_ADMISSION", ev, owner_refs)
    binding = _new_admission_binding(
        snapshot,
        expected_canonical_main=expected_canonical_main,
        live_observation_proof=live_observation_proof,
        exact_read_proofs=exact_read_proofs,
        ledger=ledger,
    )
    if not binding["valid"]:
        return _decision(candidate, "NEEDS_REVALIDATION", str(binding["reason"]), ev, [*owner_refs, *binding.get("refs", [])])
    return _decision(candidate, "NEW_DURABLE_SIGNAL", "OWNER_DOMAIN_CANONICAL_AND_GOVERNED_CURRENT_OBSERVATION_PROVE_STILL_UNMET", ev, [*owner_refs, *binding["refs"]])


def reconcile_package(package: Mapping[str, Any], snapshot: Mapping[str, Any], *, expected_canonical_main: str,
                      live_observation_proof: Any = None, exact_read_proofs: Sequence[Any] = (), ledger: Any = None) -> dict[str, Any]:
    parsed = validate_import_package(package)
    current = validate_snapshot(snapshot)
    results: list[dict[str, Any]] = []
    for error in parsed["candidate_errors"]:
        disposition = "REJECT_PRIVATE_OR_UNSAFE" if error["code"] == "PRIVATE_OR_UNSAFE" else "INSUFFICIENT_PROVENANCE"
        results.append({
            "candidate_id": error["candidate_id"], "candidate_digest": "UNKNOWN", "primary_domain": "UNKNOWN",
            "disposition": disposition, "reason": error["code"], "evidence_refs": [], "authority_evidence_refs": [],
            "dependency_refs": [], "closed_task_refs": [], "historical_status": "UNKNOWN",
        })
    for candidate in parsed["candidates"]:
        results.append(reconcile_candidate(
            candidate, current, expected_canonical_main=expected_canonical_main,
            live_observation_proof=live_observation_proof, exact_read_proofs=exact_read_proofs, ledger=ledger,
        ))
    return {
        "import_batch_id": parsed["import_batch_id"], "package_digest": parsed["package_digest"],
        "canonical_snapshot_or_main": current["canonical_main"], "snapshot_digest": current["snapshot_digest"],
        "results": sorted(results, key=lambda item: item["candidate_id"]),
    }


def stage_import_package(package: Mapping[str, Any]) -> dict[str, Any]:
    """Fingerprint a GitHub-stage transport without changing effective truth."""
    parsed = validate_import_package(package)
    return {
        "transport_schema": "SignalImportGitHubStage/v1", "import_batch_id": parsed["import_batch_id"],
        "package_digest": parsed["package_digest"],
        "candidate_ids": sorted(item["candidate_id"] for item in parsed["candidates"]),
        "candidate_errors": list(parsed["candidate_errors"]), "effective_state_changed": False,
        "effective_truth_authority": False, "write_status": "NOT_PERSISTED",
    }


def _r136_envelope(candidate: Mapping[str, Any]) -> dict[str, Any]:
    captured_at = _candidate_time(candidate)
    if captured_at is None:
        raise RetrospectiveIntakeError("PROVENANCE_INCOMPLETE", "/source_time_range")
    refs = candidate["model_tool_version_work_item_refs"]
    source_actor = str(refs.get("model_ref") or refs.get("tool_ref") or "UNKNOWN") if isinstance(refs, Mapping) else "UNKNOWN"
    return {
        "envelope_id": f"r142-{candidate['candidate_id']}", "source_ref": candidate["source_message_ref"],
        "source_type": "HISTORICAL_GPT_CHAT", "source_project": candidate["source_project"],
        "source_actor": source_actor, "source_window_ref": candidate["source_window_ref"],
        "captured_at": captured_at, "original_intent_ref": candidate["original_intent_ref"],
        "public_safe_summary": candidate["public_safe_summary"], "desired_effect": candidate["desired_effect"],
        "problem_to_solve": candidate["problem_to_solve"], "success_condition": candidate["success_condition"],
        "expected_problems": candidate["expected_problems"], "risks": candidate["risks"],
        "assumptions": candidate["assumptions"], "unknowns": candidate["unknowns"],
        "dependencies": candidate["dependencies"], "evidence_refs": candidate["evidence_refs"],
        "counterevidence_refs": candidate["counterevidence_refs"], "privacy_scope_ref": candidate["privacy_scope"],
        "proposed_primary_domain": candidate["proposed_primary_domain"], "proposed_related_domains": candidate["related_domains"],
        "epistemic_state": candidate["epistemic_state"], "persistence_class": "DURABLE_SIGNAL",
        "execution_class": "GOVERNED_MISSION", "materiality_class": "MATERIAL",
    }


def _history_identity(history: Sequence[Mapping[str, Any]]) -> str:
    return f"s0c-history-sha256:{digest(list(history))}"


class RetrospectiveSignalIntakeBridge:
    """One-shot R142 bridge. The caller supplies the existing S0C ledger and sealed observation proofs."""

    def __init__(self, ledger: Any, *, gateway: SignalIntakeGateway | None = None,
                 live_observation_proof: Any = None, exact_read_proofs: Sequence[Any] = ()) -> None:
        self.ledger = ledger
        self.gateway = gateway or SignalIntakeGateway(ledger)
        self.live_observation_proof = live_observation_proof
        self.exact_read_proofs = tuple(exact_read_proofs)

    def process(self, package: Mapping[str, Any], snapshot: Mapping[str, Any], *, expected_canonical_main: str) -> dict[str, Any]:
        parsed = validate_import_package(package)
        reconciliation = reconcile_package(
            package, snapshot, expected_canonical_main=expected_canonical_main,
            live_observation_proof=self.live_observation_proof,
            exact_read_proofs=self.exact_read_proofs,
            ledger=self.ledger,
        )
        candidates = {item["candidate_id"]: item for item in parsed["candidates"]}
        receipts: list[dict[str, Any]] = []
        for decision in reconciliation["results"]:
            candidate = candidates.get(decision["candidate_id"])
            base: dict[str, Any] = {
                "receipt_schema": "RetrospectiveSignalIntakeReceipt/v1",
                "import_batch_id": parsed["import_batch_id"], "candidate_id": decision["candidate_id"],
                "normalized_event_or_link_ids": [],
                "source_signal_kind": candidate["signal_kind"] if candidate else "UNKNOWN",
                "s0c_gateway_signal_kind": "NONE", "disposition": decision["disposition"],
                "disposition_reason": decision["reason"],
                "authority_evidence_refs": list(decision.get("authority_evidence_refs", [])),
                "canonical_snapshot_or_main": reconciliation["canonical_snapshot_or_main"],
                "package_digest": parsed["package_digest"], "durable_ledger_identity_or_receipt": "NONE",
                "replay_checksum": "NONE", "replay_identity": "NONE", "read_back_evidence": "NONE",
                "current_projection_result": "NONE",
                "duplicate_or_superseded_refs": sorted(set(decision["evidence_refs"])) if decision["disposition"] in {"DUPLICATE", "SUPERSEDED", "ALREADY_CANONICAL", "ALREADY_SATISFIED"} else [],
                "public_safety_result": "REJECTED" if decision["disposition"] == "REJECT_PRIVATE_OR_UNSAFE" else "PASS",
                "process_compliance": "SINGLE_WORKER_NO_DAEMON_NO_AUTO_TASK", "write_status": "NOT_PERSISTED",
            }
            if decision["disposition"] != "NEW_DURABLE_SIGNAL" or candidate is None:
                receipts.append(base)
                continue
            try:
                gateway_receipt = self.gateway.intake(
                    _r136_envelope(candidate),
                    request_text=f"governed system signal {candidate['problem_to_solve']}",
                    explicit_capture=True,
                    signal_kind=candidate["signal_kind"],
                )
            except (GatewayError, SignalPlaneError, RetrospectiveIntakeError) as exc:
                base["durable_ledger_identity_or_receipt"] = {"error_code": getattr(exc, "code", type(exc).__name__)}
                receipts.append(base)
                continue
            event_id = str(gateway_receipt.get("event_id", ""))
            if event_id:
                base["normalized_event_or_link_ids"] = [event_id]
            ledger_receipt = gateway_receipt.get("ledger_receipt")
            base["durable_ledger_identity_or_receipt"] = ledger_receipt or "NONE"
            durable_status = ledger_receipt.get("status") if isinstance(ledger_receipt, Mapping) else None
            if durable_status not in {"ADMITTED", "IDEMPOTENT_DUPLICATE"} or not event_id:
                receipts.append(base)
                continue
            history = self.ledger.history()
            read_back = next((item for item in history if item.get("event_id") == event_id), None)
            if read_back is None:
                base["durable_ledger_identity_or_receipt"] = {"gateway_receipt": ledger_receipt, "error_code": "DURABLE_READBACK_MISSING"}
                receipts.append(base)
                continue
            base["s0c_gateway_signal_kind"] = str(read_back.get("signal_kind", "UNKNOWN"))
            if read_back.get("signal_kind") != candidate["signal_kind"]:
                base["durable_ledger_identity_or_receipt"] = {"gateway_receipt": ledger_receipt, "error_code": "DURABLE_SIGNAL_KIND_HISTORY_MISMATCH"}
                receipts.append(base)
                continue
            projection = self.ledger.current_projection()
            if projection is None:
                projection = self.ledger.rebuild_projection(expected_version=self.ledger.current_projection_version())
            replay_ok = bool(self.ledger.observe_replay())
            projection = self.ledger.current_projection() or projection
            if not replay_ok or not isinstance(projection, Mapping) or not projection.get("checksum"):
                base["durable_ledger_identity_or_receipt"] = {"gateway_receipt": ledger_receipt, "error_code": "DURABLE_REPLAY_UNPROVEN"}
                receipts.append(base)
                continue
            projected_signal = next((item for item in projection.get("signals", []) if item.get("signal_id") == gateway_receipt.get("signal_id")), None)
            if projected_signal is None:
                base["durable_ledger_identity_or_receipt"] = {"gateway_receipt": ledger_receipt, "error_code": "DURABLE_PROJECTION_READBACK_MISSING"}
                receipts.append(base)
                continue
            if projected_signal.get("signal_kind") != candidate["signal_kind"]:
                base["durable_ledger_identity_or_receipt"] = {"gateway_receipt": ledger_receipt, "error_code": "DURABLE_SIGNAL_KIND_PROJECTION_MISMATCH"}
                receipts.append(base)
                continue
            base.update({
                "replay_checksum": str(projection["checksum"]), "replay_identity": _history_identity(history),
                "read_back_evidence": f"sha256:{digest(read_back)}",
                "current_projection_result": {
                    "projection_version": projection.get("projection_version"), "input_revision": projection.get("input_revision"),
                    "ledger_watermark": projection.get("ledger_watermark"), "reducer_version": projection.get("reducer_version"),
                    "checksum": projection.get("checksum"), "signal_present": True,
                    "signal_kind": projected_signal.get("signal_kind"),
                },
                "write_status": "PERSISTED",
            })
            receipts.append(base)
        return {
            "bridge_schema": "RetrospectiveSignalIntakeBridgeResult/v1", "import_batch_id": parsed["import_batch_id"],
            "package_digest": parsed["package_digest"], "canonical_snapshot_or_main": reconciliation["canonical_snapshot_or_main"],
            "receipts": sorted(receipts, key=lambda item: item["candidate_id"]),
            "automatic_task_created": False, "automatic_work_claim_created": False,
            "domain_or_w3_written": False, "second_signal_truth_created": False,
        }
