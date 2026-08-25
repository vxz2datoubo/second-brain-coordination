"""R148 Project-level retrospective sweep orchestration.

R148 is candidate-only before canonical R142 reconciliation. It does not own
Signal truth, domain truth, R142 disposition semantics, R147 admission
semantics, relation truth, or S0C persistence.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any, Callable, Mapping, Sequence

from global_signal_gateway.retrospective_intake import reconcile_package, validate_import_package
from r147_ingress import (
    REQUEST_SCHEMA,
    RECEIPT_SCHEMA as R147_RECEIPT_SCHEMA,
    TRANSPORT_SCHEMA as R147_TRANSPORT_SCHEMA,
    validate_transport_request,
)

SOURCE_SCHEMA = "ProjectRetrospectiveSourceSnapshot/v1"
PLAN_SCHEMA = "ProjectRetrospectiveSweepPlan/v1"
RECONCILIATION_SCHEMA = "ProjectRetrospectiveReconciliation/v1"
RECEIPT_SCHEMA = "ProjectRetrospectiveSweepReceipt/v1"

COVERAGE_STATUSES = frozenset({
    "COMPLETE_ENUMERATION_PROVEN",
    "PARTIAL_ENUMERATION",
    "CALLER_SUPPLIED_EXPORT_COMPLETE",
    "CALLER_SUPPLIED_EXPORT_PARTIAL",
    "ENUMERATION_UNAVAILABLE",
})
COMPLETE_COVERAGE_STATUSES = frozenset({
    "COMPLETE_ENUMERATION_PROVEN",
    "CALLER_SUPPLIED_EXPORT_COMPLETE",
})
CAPTURE_DIRECTIVES = frozenset({"CAPTURE_ALLOWED", "DO_NOT_CAPTURE", "DISCUSSION_ONLY"})
PUBLIC_TRANSPORT_SCOPE = "PUBLIC_SAFE_METADATA_ONLY"
SEMANTIC_IDENTITY_FIELDS = ("kind", "subject", "predicate", "object", "scope", "polarity")
CANDIDATE_SEMANTIC_FIELDS = (
    "public_safe_summary", "signal_kind", "epistemic_state", "desired_effect",
    "problem_to_solve", "success_condition", "expected_problems", "risks",
    "assumptions", "unknowns", "dependencies", "counterevidence_refs",
    "proposed_primary_domain", "related_domains", "privacy_scope",
    "historical_status", "model_tool_version_work_item_refs",
)
ARRAY_FIELDS = frozenset({
    "expected_problems", "risks", "assumptions", "unknowns", "dependencies",
    "counterevidence_refs", "related_domains",
})
FORBIDDEN_KEYS = frozenset({
    "raw_source_body", "private_chain_of_thought", "password", "private_key",
    "secret", "token", "access_token", "api_key", "credential",
})
SECRET_MARKERS = ("ghp_", "password=", "-----begin private key", "api_key=", "bearer ")
SK_SECRET_PATTERN = re.compile(r"(?<![a-z0-9])sk-[a-z0-9_-]+", re.IGNORECASE)
HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class ProjectRetrospectiveSweepError(ValueError):
    """Stable fail-closed R148 error that never echoes private source bodies."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectRetrospectiveSweepError("R148_INVALID_STRING", path)
    return value.strip()


def _timestamp(value: Any, path: str) -> str:
    text = _string(value, path)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ProjectRetrospectiveSweepError("R148_INVALID_TIMESTAMP", path) from exc
    if parsed.tzinfo is None:
        raise ProjectRetrospectiveSweepError("R148_NAIVE_TIMESTAMP_FORBIDDEN", path)
    return text


def _safe(value: Any, path: str = "/") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}{key}"
            if str(key).casefold() in FORBIDDEN_KEYS:
                raise ProjectRetrospectiveSweepError("R148_PRIVATE_OR_UNSAFE", child_path)
            _safe(child, f"{child_path}/")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _safe(child, f"{path}{index}/")
    elif isinstance(value, str):
        folded = value.casefold()
        if any(marker in folded for marker in SECRET_MARKERS) or SK_SECRET_PATTERN.search(value):
            raise ProjectRetrospectiveSweepError("R148_PRIVATE_OR_UNSAFE", path)


def _normalize_text(value: Any, path: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", _string(value, path)).casefold().split())


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ProjectRetrospectiveSweepError("R148_INVALID_STRING_ARRAY", path)
    return [item.strip() for item in value]


def _normalize_semantic_identity(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != set(SEMANTIC_IDENTITY_FIELDS):
        raise ProjectRetrospectiveSweepError("R148_SEMANTIC_IDENTITY_INVALID", path)
    return {field: _normalize_text(value[field], f"{path}/{field}") for field in SEMANTIC_IDENTITY_FIELDS}


def _semantic_ref(project_ref: str, identity: Mapping[str, str]) -> str:
    return f"semantic://r148/{_digest({'project_ref': project_ref, 'identity': identity})[:40]}"


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64_PATTERN.fullmatch(value) is not None


def _coverage_manifest(source: Mapping[str, Any]) -> dict[str, Any]:
    windows = []
    for window in source["windows"]:
        windows.append({
            "window_ref": window["window_ref"],
            "item_count": len(window["items"]),
            "item_refs": sorted(
                item.get("source_message_ref", "UNKNOWN")
                for item in window["items"]
                if isinstance(item, Mapping)
            ),
        })
    return {
        "project_ref": source["project_ref"],
        "snapshot_ref": source["snapshot_ref"],
        "enumeration_mode": source["enumeration_mode"],
        "source_provider_version": source["source_provider_version"],
        "window_refs": sorted(source["window_refs"]),
        "windows": sorted(windows, key=lambda item: item["window_ref"]),
    }


def _verify_complete_coverage(
    source: Mapping[str, Any],
    verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    if verifier is None:
        raise ProjectRetrospectiveSweepError(
            "R148_TRUSTED_COMPLETE_COVERAGE_VERIFIER_REQUIRED", "/source/coverage_status"
        )
    manifest = _coverage_manifest(source)
    request = {
        "schema_version": "ProjectCoverageVerificationRequest/v1",
        "project_ref": source["project_ref"],
        "snapshot_ref": source["snapshot_ref"],
        "coverage_status": source["coverage_status"],
        "window_manifest_digest": _digest(manifest),
        "coverage_evidence_refs": list(source["coverage_evidence_refs"]),
    }
    attestation = verifier(json.loads(_canonical(request)))
    if not isinstance(attestation, Mapping):
        raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_ATTESTATION_INVALID", "/coverage_verifier")
    required = {
        "schema_version", "verification_status", "project_ref", "snapshot_ref",
        "coverage_status", "window_manifest_digest", "coverage_evidence_refs",
        "verifier_ref", "attestation_digest",
    }
    if set(attestation) != required:
        raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_ATTESTATION_INVALID", "/coverage_verifier")
    expected_body = {
        "schema_version": "ProjectCoverageVerificationAttestation/v1",
        "verification_status": "VERIFIED_COMPLETE_ENUMERATION",
        "project_ref": request["project_ref"],
        "snapshot_ref": request["snapshot_ref"],
        "coverage_status": request["coverage_status"],
        "window_manifest_digest": request["window_manifest_digest"],
        "coverage_evidence_refs": request["coverage_evidence_refs"],
        "verifier_ref": attestation.get("verifier_ref"),
    }
    if any(attestation.get(key) != value for key, value in expected_body.items()):
        raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_ATTESTATION_MISMATCH", "/coverage_verifier")
    if not isinstance(attestation.get("verifier_ref"), str) or not attestation["verifier_ref"].strip():
        raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_ATTESTATION_INVALID", "/coverage_verifier/verifier_ref")
    if attestation.get("attestation_digest") != _digest(expected_body):
        raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_ATTESTATION_DIGEST_MISMATCH", "/coverage_verifier")
    return json.loads(_canonical(dict(attestation)))


def validate_source_snapshot(
    value: Mapping[str, Any],
    *,
    complete_coverage_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectRetrospectiveSweepError("R148_SOURCE_NOT_OBJECT")
    _safe(value, "/source/")
    required = {
        "schema_version", "project_ref", "source_project", "snapshot_ref",
        "enumeration_mode", "enumeration_started_at", "enumeration_completed_at",
        "window_refs", "window_count_observed", "coverage_status",
        "coverage_evidence_refs", "omitted_or_unavailable_refs",
        "source_provider_version", "windows",
    }
    missing = sorted(required - set(value))
    if missing:
        raise ProjectRetrospectiveSweepError("R148_SOURCE_FIELD_REQUIRED", f"/source/{missing[0]}")
    extra = sorted(set(value) - required)
    if extra:
        raise ProjectRetrospectiveSweepError("R148_SOURCE_FIELD_UNRECOGNIZED", f"/source/{extra[0]}")
    if value["schema_version"] != SOURCE_SCHEMA:
        raise ProjectRetrospectiveSweepError("R148_SOURCE_SCHEMA_INVALID", "/source/schema_version")

    out = json.loads(_canonical(dict(value)))
    for field in ("project_ref", "source_project", "snapshot_ref", "enumeration_mode", "source_provider_version"):
        out[field] = _string(out[field], f"/source/{field}")
    out["enumeration_started_at"] = _timestamp(out["enumeration_started_at"], "/source/enumeration_started_at")
    out["enumeration_completed_at"] = _timestamp(out["enumeration_completed_at"], "/source/enumeration_completed_at")
    if out["coverage_status"] not in COVERAGE_STATUSES:
        raise ProjectRetrospectiveSweepError("R148_COVERAGE_STATUS_INVALID", "/source/coverage_status")
    out["window_refs"] = _string_list(out["window_refs"], "/source/window_refs")
    out["coverage_evidence_refs"] = _string_list(out["coverage_evidence_refs"], "/source/coverage_evidence_refs")
    out["omitted_or_unavailable_refs"] = _string_list(out["omitted_or_unavailable_refs"], "/source/omitted_or_unavailable_refs")
    if not isinstance(out["window_count_observed"], int) or isinstance(out["window_count_observed"], bool) or out["window_count_observed"] < 0:
        raise ProjectRetrospectiveSweepError("R148_WINDOW_COUNT_INVALID", "/source/window_count_observed")
    if out["window_count_observed"] != len(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_WINDOW_COUNT_MISMATCH", "/source/window_count_observed")
    if len(set(out["window_refs"])) != len(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_DUPLICATE_WINDOW_REF", "/source/window_refs")
    if not isinstance(out["windows"], list):
        raise ProjectRetrospectiveSweepError("R148_WINDOWS_INVALID", "/source/windows")
    normalized_windows = []
    for wi, window in enumerate(out["windows"]):
        path = f"/source/windows/{wi}"
        if not isinstance(window, Mapping) or set(window) != {"window_ref", "items"}:
            raise ProjectRetrospectiveSweepError("R148_WINDOW_INVALID", path)
        window_ref = _string(window["window_ref"], f"{path}/window_ref")
        if not isinstance(window["items"], list):
            raise ProjectRetrospectiveSweepError("R148_WINDOW_ITEMS_INVALID", f"{path}/items")
        normalized_windows.append({"window_ref": window_ref, "items": window["items"]})
    if sorted(window["window_ref"] for window in normalized_windows) != sorted(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_WINDOW_MANIFEST_MISMATCH", "/source/windows")
    out["windows"] = normalized_windows

    complete = out["coverage_status"] in COMPLETE_COVERAGE_STATUSES
    attestation = None
    if complete:
        if not out["coverage_evidence_refs"]:
            raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_EVIDENCE_REQUIRED", "/source/coverage_evidence_refs")
        if out["omitted_or_unavailable_refs"]:
            raise ProjectRetrospectiveSweepError("R148_COMPLETE_WITH_OMISSIONS_FORBIDDEN", "/source/omitted_or_unavailable_refs")
        attestation = _verify_complete_coverage(out, complete_coverage_verifier)
    if out["coverage_status"] == "ENUMERATION_UNAVAILABLE" and out["window_count_observed"] != 0:
        raise ProjectRetrospectiveSweepError("R148_ENUMERATION_UNAVAILABLE_WITH_WINDOWS", "/source/window_count_observed")

    out["project_scan_complete"] = complete and attestation is not None
    out["coverage_attestation"] = attestation
    out["source_snapshot_digest"] = _digest({k: out[k] for k in out if k != "source_snapshot_digest"})
    return out


def _normalize_candidate_payload(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ProjectRetrospectiveSweepError("R148_CANDIDATE_PAYLOAD_INVALID", path)
    _safe(value, f"{path}/")
    missing = sorted(set(CANDIDATE_SEMANTIC_FIELDS) - set(value))
    if missing:
        raise ProjectRetrospectiveSweepError("R148_CANDIDATE_FIELD_REQUIRED", f"{path}/{missing[0]}")
    extra = sorted(set(value) - set(CANDIDATE_SEMANTIC_FIELDS))
    if extra:
        raise ProjectRetrospectiveSweepError("R148_CANDIDATE_FIELD_UNRECOGNIZED", f"{path}/{extra[0]}")
    out = json.loads(_canonical(dict(value)))
    for field in CANDIDATE_SEMANTIC_FIELDS:
        if field in ARRAY_FIELDS:
            out[field] = _string_list(out[field], f"{path}/{field}")
    for field in (
        "public_safe_summary", "signal_kind", "epistemic_state", "desired_effect",
        "problem_to_solve", "success_condition", "proposed_primary_domain",
        "privacy_scope", "historical_status",
    ):
        out[field] = _string(out[field], f"{path}/{field}")
    if out["privacy_scope"] != PUBLIC_TRANSPORT_SCOPE:
        raise ProjectRetrospectiveSweepError("R148_PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED", f"{path}/privacy_scope")
    refs = out["model_tool_version_work_item_refs"]
    if refs != "UNKNOWN" and not isinstance(refs, Mapping):
        raise ProjectRetrospectiveSweepError("R148_MODEL_TOOL_REFS_INVALID", f"{path}/model_tool_version_work_item_refs")
    return out


def prepare_project_sweep(
    source_snapshot: Mapping[str, Any],
    *,
    generated_at: str,
    expected_canonical_main: str,
    complete_coverage_verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source = validate_source_snapshot(source_snapshot, complete_coverage_verifier=complete_coverage_verifier)
    generated_at = _timestamp(generated_at, "/generated_at")
    expected_canonical_main = _string(expected_canonical_main, "/expected_canonical_main")

    groups: dict[str, dict[str, Any]] = {}
    blocked_identities: set[str] = set()
    excluded: list[dict[str, str]] = []

    for wi, window in enumerate(source["windows"]):
        for ii, item in enumerate(window["items"]):
            path = f"/source/windows/{wi}/items/{ii}"
            if not isinstance(item, Mapping):
                raise ProjectRetrospectiveSweepError("R148_SOURCE_ITEM_INVALID", path)
            required = {
                "source_message_ref", "source_time_range", "source_evidence_refs",
                "original_intent_ref", "capture_directive", "semantic_identity", "candidate",
            }
            allowed = required | {"semantic_identity_ref", "relations"}
            missing = sorted(required - set(item))
            if missing:
                raise ProjectRetrospectiveSweepError("R148_SOURCE_ITEM_FIELD_REQUIRED", f"{path}/{missing[0]}")
            extra = sorted(set(item) - allowed)
            if extra:
                raise ProjectRetrospectiveSweepError("R148_SOURCE_ITEM_FIELD_UNRECOGNIZED", f"{path}/{extra[0]}")
            _safe(item, f"{path}/")
            message_ref = _string(item["source_message_ref"], f"{path}/source_message_ref")
            original_intent_ref = _string(item["original_intent_ref"], f"{path}/original_intent_ref")
            evidence_refs = _string_list(item["source_evidence_refs"], f"{path}/source_evidence_refs")
            if not evidence_refs:
                raise ProjectRetrospectiveSweepError("R148_SOURCE_EVIDENCE_REQUIRED", f"{path}/source_evidence_refs")
            time_range = item["source_time_range"]
            if time_range != "UNKNOWN":
                if not isinstance(time_range, Mapping) or set(time_range) - {"start", "end"}:
                    raise ProjectRetrospectiveSweepError("R148_SOURCE_TIME_RANGE_INVALID", f"{path}/source_time_range")
                for bound, timestamp in time_range.items():
                    if timestamp != "UNKNOWN":
                        _timestamp(timestamp, f"{path}/source_time_range/{bound}")
            directive = _string(item["capture_directive"], f"{path}/capture_directive")
            if directive not in CAPTURE_DIRECTIVES:
                raise ProjectRetrospectiveSweepError("R148_CAPTURE_DIRECTIVE_INVALID", f"{path}/capture_directive")
            identity = _normalize_semantic_identity(item["semantic_identity"], f"{path}/semantic_identity")
            identity_ref = _semantic_ref(source["project_ref"], identity)
            supplied_ref = item.get("semantic_identity_ref")
            if supplied_ref is not None and _string(supplied_ref, f"{path}/semantic_identity_ref") != identity_ref:
                raise ProjectRetrospectiveSweepError("R148_SEMANTIC_IDENTITY_REF_MISMATCH", f"{path}/semantic_identity_ref")
            payload = _normalize_candidate_payload(item["candidate"], f"{path}/candidate")
            candidate_id = f"r148-{identity_ref.rsplit('/', 1)[-1][:32]}"
            record = {
                "window_ref": window["window_ref"],
                "source_message_ref": message_ref,
                "source_time_range": time_range,
                "source_evidence_refs": evidence_refs,
                "original_intent_ref": original_intent_ref,
                "semantic_identity": identity,
                "semantic_identity_ref": identity_ref,
                "candidate_id": candidate_id,
                "candidate": payload,
                "relations": item.get("relations", []),
            }
            group = groups.setdefault(identity_ref, {"candidate_id": candidate_id, "semantic_identity": identity, "records": []})
            if group["semantic_identity"] != identity:
                raise ProjectRetrospectiveSweepError("R148_SEMANTIC_IDENTITY_COLLISION", f"{path}/semantic_identity")
            group["records"].append(record)
            if directive != "CAPTURE_ALLOWED":
                blocked_identities.add(identity_ref)
                excluded.append({
                    "semantic_identity_ref": identity_ref,
                    "source_message_ref": message_ref,
                    "reason": directive,
                })

    for identity_ref in blocked_identities:
        groups.pop(identity_ref, None)

    if not groups:
        raise ProjectRetrospectiveSweepError("R148_NO_CAPTURE_CANDIDATES", "/source/windows")

    identity_to_candidate = {ref: group["candidate_id"] for ref, group in groups.items()}
    candidates: list[dict[str, Any]] = []
    for identity_ref in sorted(groups):
        group = groups[identity_ref]
        records = sorted(group["records"], key=lambda rec: (rec["source_message_ref"], rec["window_ref"]))
        primary = records[0]
        payload = primary["candidate"]
        core = (
            payload["signal_kind"], payload["proposed_primary_domain"],
            payload["epistemic_state"], payload["privacy_scope"],
        )
        for record in records[1:]:
            other = record["candidate"]
            if (
                other["signal_kind"], other["proposed_primary_domain"],
                other["epistemic_state"], other["privacy_scope"],
            ) != core:
                raise ProjectRetrospectiveSweepError("R148_SEMANTIC_GROUP_CORE_DRIFT", f"/semantic_groups/{identity_ref}")
        evidence_refs = sorted({
            ref for record in records for ref in record["source_evidence_refs"]
        } | {
            f"source-message://sha256/{_digest(record['source_message_ref'])}" for record in records
        })
        counterevidence = sorted({
            ref for record in records for ref in record["candidate"]["counterevidence_refs"]
        })
        relations: list[dict[str, Any]] = []
        for record in records:
            raw_relations = record["relations"]
            if not isinstance(raw_relations, list):
                raise ProjectRetrospectiveSweepError("R148_RELATIONS_INVALID", "/relations")
            for ri, relation in enumerate(raw_relations):
                if not isinstance(relation, Mapping) or set(relation) != {"relation", "target_semantic_identity", "evidence_refs"}:
                    raise ProjectRetrospectiveSweepError("R148_RELATION_INVALID", f"/relations/{ri}")
                target_identity = _normalize_semantic_identity(relation["target_semantic_identity"], f"/relations/{ri}/target_semantic_identity")
                target_ref = _semantic_ref(source["project_ref"], target_identity)
                if target_ref in blocked_identities:
                    raise ProjectRetrospectiveSweepError("R148_RELATION_TARGET_EXCLUDED", f"/relations/{ri}/target_semantic_identity")
                if target_ref not in identity_to_candidate:
                    raise ProjectRetrospectiveSweepError("R148_RELATION_TARGET_UNRESOLVED", f"/relations/{ri}/target_semantic_identity")
                relations.append({
                    "relation": _string(relation["relation"], f"/relations/{ri}/relation"),
                    "target_ref": identity_to_candidate[target_ref],
                    "evidence_refs": _string_list(relation["evidence_refs"], f"/relations/{ri}/evidence_refs"),
                })
        candidate = {
            "candidate_id": group["candidate_id"],
            "source_window_ref": primary["window_ref"],
            "source_message_ref": primary["source_message_ref"],
            "source_project": source["source_project"],
            "source_time_range": primary["source_time_range"],
            "public_safe_summary": payload["public_safe_summary"],
            "original_intent_ref": primary["original_intent_ref"],
            "signal_kind": payload["signal_kind"],
            "epistemic_state": payload["epistemic_state"],
            "desired_effect": payload["desired_effect"],
            "problem_to_solve": payload["problem_to_solve"],
            "success_condition": payload["success_condition"],
            "expected_problems": payload["expected_problems"],
            "risks": payload["risks"],
            "assumptions": payload["assumptions"],
            "unknowns": payload["unknowns"],
            "dependencies": payload["dependencies"],
            "evidence_refs": evidence_refs,
            "counterevidence_refs": counterevidence,
            "proposed_primary_domain": payload["proposed_primary_domain"],
            "related_domains": payload["related_domains"],
            "privacy_scope": payload["privacy_scope"],
            "historical_status": payload["historical_status"],
            "candidate_relations": sorted(relations, key=_canonical),
            "model_tool_version_work_item_refs": payload["model_tool_version_work_item_refs"],
        }
        candidates.append(candidate)

    sweep_basis = {
        "project_ref": source["project_ref"],
        "snapshot_ref": source["snapshot_ref"],
        "source_snapshot_digest": source["source_snapshot_digest"],
        "candidate_ids": [item["candidate_id"] for item in candidates],
    }
    sweep_id = f"r148-sweep-{_digest(sweep_basis)[:24]}"
    package = {
        "schema_version": "SignalImportPackage/v1",
        "import_batch_id": sweep_id,
        "generated_at": generated_at,
        "source_window_ref": f"project-sweep://{_digest({'project_ref': source['project_ref'], 'snapshot_ref': source['snapshot_ref']})[:32]}",
        "expected_canonical_main": expected_canonical_main,
        "package_metadata": {
            "r148_project_ref": source["project_ref"],
            "r148_snapshot_ref": source["snapshot_ref"],
            "r148_coverage_status": source["coverage_status"],
            "r148_project_scan_complete": source["project_scan_complete"],
            "r148_window_count_observed": source["window_count_observed"],
            "r148_source_snapshot_digest": source["source_snapshot_digest"],
            "r148_coverage_evidence_refs": source["coverage_evidence_refs"],
            "r148_coverage_attestation": source["coverage_attestation"],
            "r148_omitted_or_unavailable_refs": source["omitted_or_unavailable_refs"],
        },
        "candidates": candidates,
    }
    parsed = validate_import_package(package)
    if parsed["candidate_errors"]:
        first = parsed["candidate_errors"][0]
        raise ProjectRetrospectiveSweepError("R148_R142_PACKAGE_REJECTED", f"/candidates/{first['candidate_id']}:{first['code']}")
    return {
        "schema_version": PLAN_SCHEMA,
        "sweep_id": sweep_id,
        "project_ref": source["project_ref"],
        "snapshot_ref": source["snapshot_ref"],
        "coverage_status": source["coverage_status"],
        "project_scan_complete": source["project_scan_complete"],
        "coverage_attestation": source["coverage_attestation"],
        "window_count_observed": source["window_count_observed"],
        "source_snapshot_digest": source["source_snapshot_digest"],
        "candidate_count": len(candidates),
        "candidate_ids": [item["candidate_id"] for item in candidates],
        "excluded_items": sorted(excluded, key=lambda item: (item["semantic_identity_ref"], item["source_message_ref"])),
        "package": package,
        "no_second_signal_truth_created": True,
        "r142_disposition_authority_preserved": True,
    }


def reconcile_project_sweep(
    plan: Mapping[str, Any],
    current_snapshot: Mapping[str, Any],
    *,
    expected_canonical_main: str,
    live_observation_proof: Any = None,
    exact_read_proofs: Sequence[Any] = (),
    ledger: Any = None,
    reconcile_fn: Callable[..., Mapping[str, Any]] = reconcile_package,
) -> dict[str, Any]:
    if plan.get("schema_version") != PLAN_SCHEMA:
        raise ProjectRetrospectiveSweepError("R148_PLAN_SCHEMA_INVALID", "/schema_version")
    if plan.get("package", {}).get("expected_canonical_main") != expected_canonical_main:
        raise ProjectRetrospectiveSweepError("R148_PLAN_CANONICAL_BINDING_MISMATCH", "/package/expected_canonical_main")
    result = reconcile_fn(
        plan["package"], current_snapshot,
        expected_canonical_main=expected_canonical_main,
        live_observation_proof=live_observation_proof,
        exact_read_proofs=exact_read_proofs,
        ledger=ledger,
    )
    if not isinstance(result, Mapping) or not isinstance(result.get("results"), list):
        raise ProjectRetrospectiveSweepError("R148_R142_RECONCILIATION_INVALID", "/reconciliation")
    parsed = validate_import_package(plan["package"])
    expected = {item["candidate_id"]: item["candidate_digest"] for item in parsed["candidates"]}
    seen: set[str] = set()
    counts: dict[str, int] = {}
    normalized_results = []
    for index, decision in enumerate(result["results"]):
        if not isinstance(decision, Mapping):
            raise ProjectRetrospectiveSweepError("R148_R142_RECONCILIATION_INVALID", f"/reconciliation/results/{index}")
        candidate_id = _string(decision.get("candidate_id"), f"/reconciliation/results/{index}/candidate_id")
        if candidate_id not in expected or candidate_id in seen:
            raise ProjectRetrospectiveSweepError("R148_R142_RESULT_BINDING_INVALID", f"/reconciliation/results/{index}/candidate_id")
        if decision.get("candidate_digest") != expected[candidate_id]:
            raise ProjectRetrospectiveSweepError("R148_R142_CANDIDATE_DIGEST_MISMATCH", f"/reconciliation/{candidate_id}")
        disposition = _string(decision.get("disposition"), f"/reconciliation/results/{index}/disposition")
        seen.add(candidate_id)
        counts[disposition] = counts.get(disposition, 0) + 1
        normalized_results.append(dict(decision))
    if seen != set(expected):
        raise ProjectRetrospectiveSweepError("R148_R142_RESULT_SET_INCOMPLETE", "/reconciliation/results")
    return {
        "schema_version": RECONCILIATION_SCHEMA,
        "sweep_id": plan["sweep_id"],
        "canonical_snapshot_or_main": result.get("canonical_snapshot_or_main", "UNKNOWN"),
        "snapshot_digest": result.get("snapshot_digest", "UNKNOWN"),
        "package_digest": result.get("package_digest", "UNKNOWN"),
        "disposition_counts": dict(sorted(counts.items())),
        "results": normalized_results,
    }


def build_r147_requests(plan: Mapping[str, Any], reconciliation: Mapping[str, Any]) -> list[dict[str, Any]]:
    if plan.get("schema_version") != PLAN_SCHEMA:
        raise ProjectRetrospectiveSweepError("R148_PLAN_SCHEMA_INVALID", "/schema_version")
    if reconciliation.get("sweep_id") != plan.get("sweep_id"):
        raise ProjectRetrospectiveSweepError("R148_RECONCILIATION_SWEEP_MISMATCH", "/reconciliation/sweep_id")
    parsed = validate_import_package(plan["package"])
    candidates = {item["candidate_id"]: item for item in parsed["candidates"]}
    requests = []
    for decision in reconciliation.get("results", []):
        if decision.get("disposition") != "NEW_DURABLE_SIGNAL":
            continue
        candidate_id = _string(decision.get("candidate_id"), "/reconciliation/candidate_id")
        candidate = candidates.get(candidate_id)
        if candidate is None:
            raise ProjectRetrospectiveSweepError("R148_NEW_CANDIDATE_MISSING", f"/reconciliation/{candidate_id}")
        if decision.get("candidate_digest") != candidate["candidate_digest"]:
            raise ProjectRetrospectiveSweepError("R148_R142_CANDIDATE_DIGEST_MISMATCH", f"/reconciliation/{candidate_id}")
        if candidate.get("privacy_scope") != PUBLIC_TRANSPORT_SCOPE:
            raise ProjectRetrospectiveSweepError("R148_PUBLIC_SAFE_PRIVACY_SCOPE_REQUIRED", f"/candidates/{candidate_id}/privacy_scope")
        if candidate.get("candidate_relations"):
            raise ProjectRetrospectiveSweepError(
                "R148_RELATION_CAPABLE_CANONICAL_ADMISSION_REQUIRED",
                f"/candidates/{candidate_id}/candidate_relations",
            )
        request = {
            "schema_version": REQUEST_SCHEMA,
            "attempt_id": f"{plan['sweep_id']}-{candidate_id[-12:]}",
            "capture_identity": f"r148:{candidate_id}",
            "capture_command": "把这个录入信号塔",
            "source_project": candidate["source_project"],
            "source_window_ref": candidate["source_window_ref"],
            "public_safe_summary": candidate["public_safe_summary"],
            "desired_effect": candidate["desired_effect"],
            "problem_to_solve": candidate["problem_to_solve"],
            "success_condition": candidate["success_condition"],
            "expected_problems": candidate["expected_problems"],
            "risks": candidate["risks"],
            "assumptions": candidate["assumptions"],
            "unknowns": candidate["unknowns"],
            "dependencies": candidate["dependencies"],
            "evidence_refs": candidate["evidence_refs"],
            "counterevidence_refs": candidate["counterevidence_refs"],
            "proposed_primary_domain": candidate["proposed_primary_domain"],
            "proposed_related_domains": candidate["related_domains"],
            "epistemic_state": candidate["epistemic_state"],
            "signal_kind": candidate["signal_kind"],
        }
        requests.append(validate_transport_request(request))
    return sorted(requests, key=lambda item: item["capture_identity"])


def _require_replay_evidence(value: Any, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema_version") != R147_TRANSPORT_SCHEMA:
        raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_EVIDENCE_INVALID", path)
    for field in ("history_digest", "projection_checksum", "journal_digest"):
        if not _hex64(value.get(field)):
            raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_EVIDENCE_INVALID", f"{path}/{field}")
    event_count = value.get("event_count")
    if not isinstance(event_count, int) or isinstance(event_count, bool) or event_count < 0:
        raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_EVIDENCE_INVALID", f"{path}/event_count")
    if value.get("input_revision") is None or isinstance(value.get("input_revision"), bool):
        raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_EVIDENCE_INVALID", f"{path}/input_revision")
    return dict(value)


def _validate_r147_receipt(request: Mapping[str, Any], receipt: Mapping[str, Any]) -> dict[str, Any]:
    if receipt.get("schema_version") != R147_RECEIPT_SCHEMA:
        raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_SCHEMA_INVALID", "/admission_receipts/schema_version")
    if receipt.get("attempt_id") != request["attempt_id"]:
        raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_ATTEMPT_MISMATCH", "/admission_receipts/attempt_id")
    if receipt.get("status") not in {"ADMITTED", "IDEMPOTENT_DUPLICATE"} or receipt.get("durable_success") is not True:
        raise ProjectRetrospectiveSweepError("R148_R147_DURABLE_VERIFICATION_FAILED", "/admission_receipts/status")
    if receipt.get("primary_domain") != request["proposed_primary_domain"]:
        raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_DOMAIN_MISMATCH", "/admission_receipts/primary_domain")
    for field in ("signal_id", "event_id", "receipt_id"):
        _string(receipt.get(field), f"/admission_receipts/{field}")
    offset = receipt.get("receipt_offset")
    if not isinstance(offset, int) or isinstance(offset, bool) or offset < 1:
        raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_OFFSET_INVALID", "/admission_receipts/receipt_offset")
    if receipt.get("input_revision") is None or isinstance(receipt.get("input_revision"), bool):
        raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_REVISION_INVALID", "/admission_receipts/input_revision")
    if not _hex64(receipt.get("authority_binding_digest")):
        raise ProjectRetrospectiveSweepError("R148_R147_AUTHORITY_BINDING_INVALID", "/admission_receipts/authority_binding_digest")
    authority_refs = receipt.get("authority_refs")
    if not isinstance(authority_refs, list) or not authority_refs or not all(isinstance(ref, str) and ref for ref in authority_refs):
        raise ProjectRetrospectiveSweepError("R148_R147_AUTHORITY_BINDING_INVALID", "/admission_receipts/authority_refs")
    for field in ("content_digest", "event_digest"):
        if not _hex64(receipt.get(field)):
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_DIGEST_INVALID", f"/admission_receipts/{field}")
    if receipt.get("readback_verification_status") != "VERIFIED_SAME_LEDGER":
        raise ProjectRetrospectiveSweepError("R148_R147_DURABLE_VERIFICATION_FAILED", "/admission_receipts/readback_verification_status")
    if receipt.get("fresh_replay_verification_status") != "VERIFIED_FRESH_S0C_REPLAY":
        raise ProjectRetrospectiveSweepError("R148_R147_DURABLE_VERIFICATION_FAILED", "/admission_receipts/fresh_replay_verification_status")
    if not all(receipt.get(field) is False for field in (
        "task_created", "route_created", "work_claim_created", "write_permission_created"
    )):
        raise ProjectRetrospectiveSweepError("R148_R147_SIDE_EFFECT_ASSERTION_FAILED", "/admission_receipts")
    before = _require_replay_evidence(receipt.get("transport_replay_before"), "/admission_receipts/transport_replay_before")
    after = _require_replay_evidence(receipt.get("transport_replay_after"), "/admission_receipts/transport_replay_after")
    if after["input_revision"] != receipt["input_revision"] or after["event_count"] < offset:
        raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_BINDING_MISMATCH", "/admission_receipts/transport_replay_after")
    if receipt["status"] == "ADMITTED":
        if after["event_count"] != before["event_count"] + 1 or offset != after["event_count"]:
            raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_BINDING_MISMATCH", "/admission_receipts/transport_replay_after")
    else:
        if after["event_count"] != before["event_count"]:
            raise ProjectRetrospectiveSweepError("R148_R147_REPLAY_BINDING_MISMATCH", "/admission_receipts/transport_replay_after")
    return dict(receipt)


def finalize_sweep_receipt(
    plan: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    admission_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected_requests = build_r147_requests(plan, reconciliation)
    requests_by_attempt = {item["attempt_id"]: item for item in expected_requests}
    receipts_by_attempt: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    for receipt in admission_receipts:
        if not isinstance(receipt, Mapping):
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_INVALID", "/admission_receipts")
        attempt_id = receipt.get("attempt_id")
        if not isinstance(attempt_id, str) or attempt_id not in requests_by_attempt or attempt_id in receipts_by_attempt:
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_BINDING_INVALID", "/admission_receipts/attempt_id")
        request = requests_by_attempt[attempt_id]
        wrapped_identity = receipt.get("r148_capture_identity")
        if wrapped_identity is not None and wrapped_identity != request["capture_identity"]:
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_BINDING_INVALID", "/admission_receipts/r148_capture_identity")
        try:
            receipts_by_attempt[attempt_id] = _validate_r147_receipt(request, receipt)
        except ProjectRetrospectiveSweepError as exc:
            failures.append({"capture_identity": request["capture_identity"], "reason": exc.code})

    missing_attempts = sorted(set(requests_by_attempt) - set(receipts_by_attempt))
    admitted_refs = []
    replay_checksums = []
    for attempt_id, receipt in sorted(receipts_by_attempt.items()):
        request = requests_by_attempt[attempt_id]
        admitted_refs.append({
            "capture_identity": request["capture_identity"],
            "attempt_id": attempt_id,
            "status": receipt["status"],
            "signal_id": receipt["signal_id"],
            "event_id": receipt["event_id"],
            "receipt_id": receipt["receipt_id"],
            "receipt_offset": receipt["receipt_offset"],
        })
        replay_checksums.append(receipt["transport_replay_after"]["projection_checksum"])
    disposition_counts = reconciliation.get("disposition_counts", {})
    new_count = int(disposition_counts.get("NEW_DURABLE_SIGNAL", 0)) if isinstance(disposition_counts, Mapping) else 0
    return {
        "schema_version": RECEIPT_SCHEMA,
        "project_ref": plan["project_ref"],
        "sweep_id": plan["sweep_id"],
        "snapshot_ref": plan["snapshot_ref"],
        "coverage_status": plan["coverage_status"],
        "project_scan_complete": bool(plan["project_scan_complete"]),
        "coverage_attestation": plan.get("coverage_attestation"),
        "window_count_observed": plan["window_count_observed"],
        "candidate_count": plan["candidate_count"],
        "disposition_counts": disposition_counts,
        "new_durable_signal_count": new_count,
        "new_durable_signal_ids": sorted(
            item["candidate_id"] for item in reconciliation.get("results", [])
            if item.get("disposition") == "NEW_DURABLE_SIGNAL"
        ),
        "admitted_signal_refs": admitted_refs,
        "admission_failures": failures,
        "missing_receipt_attempt_ids": missing_attempts,
        "durable_admission_complete_for_observed_new": (
            not failures and not missing_attempts and len(admitted_refs) == new_count
        ),
        "replay_projection_checksums": sorted(set(replay_checksums)),
        "automatic_task_created": False,
        "automatic_route_created": False,
        "automatic_work_claim_created": False,
        "automatic_write_permission_created": False,
        "second_signal_truth_created": False,
        "coverage_caveat": (
            "NONE" if plan["project_scan_complete"]
            else "PARTIAL_OR_UNAVAILABLE_PROJECT_ENUMERATION; THIS RECEIPT DOES NOT CLAIM COMPLETE PROJECT COVERAGE"
        ),
    }


def execute_r147_admissions(
    plan: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    *,
    admit_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute only R142-approved, relation-safe NEW candidates through R147."""
    wrapped: list[dict[str, Any]] = []
    for request in build_r147_requests(plan, reconciliation):
        receipt = admit_fn(request)
        if not isinstance(receipt, Mapping):
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_INVALID", "/admission_receipts")
        bound = dict(receipt)
        bound["r148_capture_identity"] = request["capture_identity"]
        wrapped.append(bound)
    return finalize_sweep_receipt(plan, reconciliation, wrapped)
