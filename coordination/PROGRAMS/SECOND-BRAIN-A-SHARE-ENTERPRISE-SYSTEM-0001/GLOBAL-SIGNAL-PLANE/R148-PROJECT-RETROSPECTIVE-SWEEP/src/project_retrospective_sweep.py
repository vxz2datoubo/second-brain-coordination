"""R148 Project-level retrospective sweep orchestration.

R148 is intentionally candidate-only before canonical R142 reconciliation.
It does not own Signal truth, domain truth, R142 disposition semantics, R147
admission semantics, or S0C persistence.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import re
import unicodedata
from typing import Any, Callable, Mapping, Sequence

from global_signal_gateway.retrospective_intake import reconcile_package, validate_import_package
from r147_ingress import REQUEST_SCHEMA, validate_transport_request


SOURCE_SCHEMA = "ProjectRetrospectiveSourceSnapshot/v1"
PLAN_SCHEMA = "ProjectRetrospectiveSweepPlan/v1"
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
SEMANTIC_IDENTITY_FIELDS = (
    "kind", "subject", "predicate", "object", "scope", "polarity",
)
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


class ProjectRetrospectiveSweepError(ValueError):
    """Stable R148 fail-closed error without raw/private body echo."""

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
    text = _string(value, path)
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def _string_list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise ProjectRetrospectiveSweepError("R148_INVALID_STRING_ARRAY", path)
    return [item.strip() for item in value]


def _normalize_semantic_identity(value: Any, path: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != set(SEMANTIC_IDENTITY_FIELDS):
        raise ProjectRetrospectiveSweepError("R148_SEMANTIC_IDENTITY_INVALID", path)
    return {
        field: _normalize_text(value[field], f"{path}/{field}")
        for field in SEMANTIC_IDENTITY_FIELDS
    }


def _semantic_ref(project_ref: str, identity: Mapping[str, str]) -> str:
    return f"semantic://r148/{_digest({'project_ref': project_ref, 'identity': identity})[:40]}"


def _project_complete(coverage_status: str) -> bool:
    return coverage_status in COMPLETE_COVERAGE_STATUSES


def validate_source_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
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
    out["omitted_or_unavailable_refs"] = _string_list(
        out["omitted_or_unavailable_refs"], "/source/omitted_or_unavailable_refs"
    )
    if not isinstance(out["window_count_observed"], int) or out["window_count_observed"] < 0:
        raise ProjectRetrospectiveSweepError("R148_WINDOW_COUNT_INVALID", "/source/window_count_observed")
    if out["window_count_observed"] != len(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_WINDOW_COUNT_MISMATCH", "/source/window_count_observed")
    if len(set(out["window_refs"])) != len(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_DUPLICATE_WINDOW_REF", "/source/window_refs")
    if not isinstance(out["windows"], list):
        raise ProjectRetrospectiveSweepError("R148_WINDOWS_INVALID", "/source/windows")
    if sorted(item.get("window_ref") for item in out["windows"] if isinstance(item, Mapping)) != sorted(out["window_refs"]):
        raise ProjectRetrospectiveSweepError("R148_WINDOW_MANIFEST_MISMATCH", "/source/windows")

    complete = _project_complete(out["coverage_status"])
    if complete:
        if not out["coverage_evidence_refs"]:
            raise ProjectRetrospectiveSweepError("R148_COMPLETE_COVERAGE_EVIDENCE_REQUIRED", "/source/coverage_evidence_refs")
        if out["omitted_or_unavailable_refs"]:
            raise ProjectRetrospectiveSweepError("R148_COMPLETE_WITH_OMISSIONS_FORBIDDEN", "/source/omitted_or_unavailable_refs")
    if out["coverage_status"] == "ENUMERATION_UNAVAILABLE" and out["window_count_observed"] != 0:
        raise ProjectRetrospectiveSweepError("R148_ENUMERATION_UNAVAILABLE_WITH_WINDOWS", "/source/window_count_observed")

    normalized_windows = []
    for wi, window in enumerate(out["windows"]):
        path = f"/source/windows/{wi}"
        if not isinstance(window, Mapping) or set(window) != {"window_ref", "items"}:
            raise ProjectRetrospectiveSweepError("R148_WINDOW_INVALID", path)
        window_ref = _string(window["window_ref"], f"{path}/window_ref")
        if not isinstance(window["items"], list):
            raise ProjectRetrospectiveSweepError("R148_WINDOW_ITEMS_INVALID", f"{path}/items")
        normalized_windows.append({"window_ref": window_ref, "items": window["items"]})
    out["windows"] = normalized_windows
    out["project_scan_complete"] = complete
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
    refs = out["model_tool_version_work_item_refs"]
    if refs != "UNKNOWN" and not isinstance(refs, Mapping):
        raise ProjectRetrospectiveSweepError("R148_MODEL_TOOL_REFS_INVALID", f"{path}/model_tool_version_work_item_refs")
    return out


def prepare_project_sweep(
    source_snapshot: Mapping[str, Any],
    *,
    generated_at: str,
    expected_canonical_main: str,
) -> dict[str, Any]:
    source = validate_source_snapshot(source_snapshot)
    generated_at = _timestamp(generated_at, "/generated_at")
    expected_canonical_main = _string(expected_canonical_main, "/expected_canonical_main")

    groups: dict[str, dict[str, Any]] = {}
    excluded: list[dict[str, str]] = []
    identity_refs_seen: dict[str, dict[str, str]] = {}

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
            prior_identity = identity_refs_seen.get(identity_ref)
            if prior_identity is not None and prior_identity != identity:
                raise ProjectRetrospectiveSweepError("R148_SEMANTIC_IDENTITY_COLLISION", f"{path}/semantic_identity")
            identity_refs_seen[identity_ref] = identity

            if directive != "CAPTURE_ALLOWED":
                excluded.append({
                    "semantic_identity_ref": identity_ref,
                    "source_message_ref": message_ref,
                    "reason": directive,
                })
                continue

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
            group = groups.setdefault(identity_ref, {
                "candidate_id": candidate_id,
                "semantic_identity": identity,
                "records": [],
            })
            group["records"].append(record)

    candidates: list[dict[str, Any]] = []
    identity_to_candidate = {ref: group["candidate_id"] for ref, group in groups.items()}
    for identity_ref in sorted(groups):
        group = groups[identity_ref]
        records = sorted(group["records"], key=lambda rec: (rec["source_message_ref"], rec["window_ref"]))
        primary = records[0]
        payload = primary["candidate"]
        core = (payload["signal_kind"], payload["proposed_primary_domain"], payload["epistemic_state"])
        for record in records[1:]:
            other = record["candidate"]
            if (other["signal_kind"], other["proposed_primary_domain"], other["epistemic_state"]) != core:
                raise ProjectRetrospectiveSweepError("R148_SEMANTIC_GROUP_CORE_DRIFT", f"/semantic_groups/{identity_ref}")

        evidence_refs = sorted({
            ref for record in records for ref in record["source_evidence_refs"]
        } | {
            f"source-message://sha256/{_digest(record['source_message_ref'])}"
            for record in records
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
                if not isinstance(relation, Mapping):
                    raise ProjectRetrospectiveSweepError("R148_RELATION_INVALID", f"/relations/{ri}")
                if set(relation) != {"relation", "target_semantic_identity", "evidence_refs"}:
                    raise ProjectRetrospectiveSweepError("R148_RELATION_INVALID", f"/relations/{ri}")
                target_identity = _normalize_semantic_identity(
                    relation["target_semantic_identity"], f"/relations/{ri}/target_semantic_identity"
                )
                target_ref = _semantic_ref(source["project_ref"], target_identity)
                if target_ref not in identity_to_candidate:
                    raise ProjectRetrospectiveSweepError("R148_RELATION_TARGET_UNRESOLVED", f"/relations/{ri}/target_semantic_identity")
                relations.append({
                    "relation": _string(relation["relation"], f"/relations/{ri}/relation"),
                    "target_ref": identity_to_candidate[target_ref],
                    "evidence_refs": _string_list(relation["evidence_refs"], f"/relations/{ri}/evidence_refs"),
                })
        relations = sorted(relations, key=_canonical)

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
            "candidate_relations": relations,
            "model_tool_version_work_item_refs": payload["model_tool_version_work_item_refs"],
        }
        candidates.append(candidate)

    if not candidates:
        raise ProjectRetrospectiveSweepError("R148_NO_CAPTURE_CANDIDATES", "/source/windows")

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
            "r148_omitted_or_unavailable_refs": source["omitted_or_unavailable_refs"],
        },
        "candidates": candidates,
    }
    parsed = validate_import_package(package)
    if parsed["candidate_errors"]:
        first = parsed["candidate_errors"][0]
        raise ProjectRetrospectiveSweepError(
            "R148_R142_PACKAGE_REJECTED", f"/candidates/{first['candidate_id']}:{first['code']}"
        )
    return {
        "schema_version": PLAN_SCHEMA,
        "sweep_id": sweep_id,
        "project_ref": source["project_ref"],
        "snapshot_ref": source["snapshot_ref"],
        "coverage_status": source["coverage_status"],
        "project_scan_complete": source["project_scan_complete"],
        "window_count_observed": source["window_count_observed"],
        "source_snapshot_digest": source["source_snapshot_digest"],
        "candidate_count": len(candidates),
        "candidate_ids": [item["candidate_id"] for item in candidates],
        "excluded_items": sorted(excluded, key=lambda item: (item["source_message_ref"], item["reason"])),
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
        plan["package"],
        current_snapshot,
        expected_canonical_main=expected_canonical_main,
        live_observation_proof=live_observation_proof,
        exact_read_proofs=exact_read_proofs,
        ledger=ledger,
    )
    if not isinstance(result, Mapping) or not isinstance(result.get("results"), list):
        raise ProjectRetrospectiveSweepError("R148_R142_RECONCILIATION_INVALID", "/reconciliation")
    counts: dict[str, int] = {}
    for decision in result["results"]:
        disposition = _string(decision.get("disposition"), "/reconciliation/disposition")
        counts[disposition] = counts.get(disposition, 0) + 1
    return {
        "schema_version": "ProjectRetrospectiveReconciliation/v1",
        "sweep_id": plan["sweep_id"],
        "canonical_snapshot_or_main": result.get("canonical_snapshot_or_main", "UNKNOWN"),
        "snapshot_digest": result.get("snapshot_digest", "UNKNOWN"),
        "package_digest": result.get("package_digest", "UNKNOWN"),
        "disposition_counts": dict(sorted(counts.items())),
        "results": list(result["results"]),
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
        if decision.get("candidate_digest") not in (None, "UNKNOWN", candidate["candidate_digest"]):
            raise ProjectRetrospectiveSweepError("R148_R142_CANDIDATE_DIGEST_MISMATCH", f"/reconciliation/{candidate_id}")
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


def finalize_sweep_receipt(
    plan: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    admission_receipts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected_requests = build_r147_requests(plan, reconciliation)
    expected_identities = {item["capture_identity"] for item in expected_requests}
    receipts_by_identity: dict[str, Mapping[str, Any]] = {}
    for receipt in admission_receipts:
        if not isinstance(receipt, Mapping):
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_INVALID", "/admission_receipts")
        capture_identity = receipt.get("capture_identity")
        if capture_identity is None:
            capture_identity = receipt.get("r148_capture_identity")
        capture_identity = _string(capture_identity, "/admission_receipts/capture_identity")
        if capture_identity not in expected_identities or capture_identity in receipts_by_identity:
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_BINDING_INVALID", "/admission_receipts/capture_identity")
        receipts_by_identity[capture_identity] = receipt

    missing = sorted(expected_identities - set(receipts_by_identity))
    admitted_refs = []
    failures = []
    replay_checksums = []
    for request in expected_requests:
        identity = request["capture_identity"]
        receipt = receipts_by_identity.get(identity)
        if receipt is None:
            failures.append({"capture_identity": identity, "reason": "R147_RECEIPT_MISSING"})
            continue
        status = receipt.get("status")
        durable = receipt.get("durable_success") is True
        readback = receipt.get("readback_verification_status") == "VERIFIED_SAME_LEDGER"
        replay = receipt.get("fresh_replay_verification_status") == "VERIFIED_FRESH_S0C_REPLAY"
        side_effect_free = all(receipt.get(field) is False for field in (
            "task_created", "route_created", "work_claim_created", "write_permission_created"
        ))
        if status not in {"ADMITTED", "IDEMPOTENT_DUPLICATE"} or not (durable and readback and replay and side_effect_free):
            failures.append({"capture_identity": identity, "reason": "R147_DURABLE_VERIFICATION_FAILED"})
            continue
        admitted_refs.append({
            "capture_identity": identity,
            "status": status,
            "signal_id": receipt.get("signal_id", "UNKNOWN"),
            "event_id": receipt.get("event_id", "UNKNOWN"),
            "receipt_id": receipt.get("receipt_id", "UNKNOWN"),
            "receipt_offset": receipt.get("receipt_offset", "UNKNOWN"),
        })
        replay_after = receipt.get("transport_replay_after")
        if isinstance(replay_after, Mapping) and isinstance(replay_after.get("projection_checksum"), str):
            replay_checksums.append(replay_after["projection_checksum"])

    disposition_counts = reconciliation.get("disposition_counts", {})
    new_count = int(disposition_counts.get("NEW_DURABLE_SIGNAL", 0)) if isinstance(disposition_counts, Mapping) else 0
    return {
        "schema_version": RECEIPT_SCHEMA,
        "project_ref": plan["project_ref"],
        "sweep_id": plan["sweep_id"],
        "snapshot_ref": plan["snapshot_ref"],
        "coverage_status": plan["coverage_status"],
        "project_scan_complete": bool(plan["project_scan_complete"]),
        "window_count_observed": plan["window_count_observed"],
        "candidate_count": plan["candidate_count"],
        "disposition_counts": disposition_counts,
        "new_durable_signal_count": new_count,
        "new_durable_signal_ids": sorted(
            item["candidate_id"] for item in reconciliation.get("results", [])
            if item.get("disposition") == "NEW_DURABLE_SIGNAL"
        ),
        "admitted_signal_refs": sorted(admitted_refs, key=lambda item: item["capture_identity"]),
        "admission_failures": failures,
        "missing_receipt_identities": missing,
        "durable_admission_complete_for_observed_new": not failures and not missing and len(admitted_refs) == new_count,
        "replay_projection_checksums": sorted(set(replay_checksums)),
        "automatic_task_created": False,
        "automatic_route_created": False,
        "automatic_work_claim_created": False,
        "automatic_write_permission_created": False,
        "second_signal_truth_created": False,
        "coverage_caveat": (
            "NONE"
            if plan["project_scan_complete"]
            else "PARTIAL_OR_UNAVAILABLE_PROJECT_ENUMERATION; THIS RECEIPT DOES NOT CLAIM COMPLETE PROJECT COVERAGE"
        ),
    }


def execute_r147_admissions(
    plan: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
    *,
    admit_fn: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> dict[str, Any]:
    """Execute only R142-approved NEW candidates through an injected canonical R147 path."""
    wrapped: list[dict[str, Any]] = []
    for request in build_r147_requests(plan, reconciliation):
        receipt = admit_fn(request)
        if not isinstance(receipt, Mapping):
            raise ProjectRetrospectiveSweepError("R148_R147_RECEIPT_INVALID", "/admission_receipts")
        bound = dict(receipt)
        bound["r148_capture_identity"] = request["capture_identity"]
        wrapped.append(bound)
    return finalize_sweep_receipt(plan, reconciliation, wrapped)
