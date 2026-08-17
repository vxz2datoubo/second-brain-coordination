"""R140 read-only, evidence-bound domain learning recall.

This module consumes structured, domain-owned metadata at one exact revision.
It deliberately stores only object references and public-safe metadata: it never
copies a canonical lesson body, writes to the domain, or treats retrieval as a
creative-outcome claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import subprocess
import yaml

from .gateway import ExactReadProof, GatewayError, _PROOF_SEAL, digest, exact_git_read_proofs, instant, public_safe


REQUEST_REQUIRED = frozenset({
    "schema_version", "request_id", "source_trace_ref", "domain_id", "domain_repository",
    "domain_source_revision", "problem_signatures", "scene_or_work_item", "model_or_tool",
    "model_version", "constraints", "requested_evidence_classes", "privacy_class", "observed_at",
})
BUNDLE_REQUIRED = frozenset({
    "schema_version", "bundle_id", "request_id", "request_digest", "domain_source_revision",
    "matched_object_refs", "match_dimensions", "applicability_state", "failure_condition_hits",
    "counterexample_hits", "maturity_observations", "revalidation_state", "exact_read_proofs",
    "abstentions", "unknowns",
})
RECEIPT_REQUIRED = frozenset({
    "schema_version", "receipt_id", "request_digest", "bundle_digest", "provider_code_identity",
    "exact_domain_revision", "decision", "process_compliance", "limitations",
})
DECISIONS = frozenset({"RECALLED", "ABSTAINED", "NEEDS_REVALIDATION", "CONFLICTED", "UNSUPPORTED"})
PRIVACY = frozenset({"PUBLIC_SAFE", "PRIVATE_OR_SENSITIVE", "SECRET_CREDENTIAL"})
FORBIDDEN_KEYS = frozenset({
    "body", "lesson_body", "raw_source_body", "raw_private_body", "raw_media", "private_key", "token",
    "password", "api_key", "cookie", "session_credential", "raw_chain_of_thought",
})
_RECALL_ISSUANCE_SEAL = object()
AI_FILM_GOLDEN_CASES_PATH = "11_\u9a8c\u6536/golden_prompt_cases.yaml"
AI_FILM_REGRESSION_CASES_PATH = "11_\u9a8c\u6536/director_regression_cases.yaml"


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(child) for key, child in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(child) for child in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _thaw(child) for key, child in value.items()}
    if isinstance(value, tuple):
        return [_thaw(child) for child in value]
    return value


def _checked(payload: Mapping[str, Any], required: frozenset[str], digest_key: str, path: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise GatewayError("DOMAIN_RECALL_NOT_OBJECT", path)
    value = _thaw(payload)
    public_safe(value, path)
    forbidden = FORBIDDEN_KEYS & {str(key).casefold() for key in value}
    if forbidden:
        raise GatewayError("DOMAIN_LESSON_BODY_OR_SECRET_FORBIDDEN", path)
    missing = sorted(required - set(value))
    if missing:
        raise GatewayError("DOMAIN_RECALL_REQUIRED_FIELD_MISSING", f"{path}/{missing[0]}")
    value.pop(digest_key, None)
    return value


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GatewayError("DOMAIN_RECALL_NONEMPTY_STRING_REQUIRED", path)
    return value


def _array(value: Any, path: str) -> None:
    if not isinstance(value, (list, tuple)):
        raise GatewayError("DOMAIN_RECALL_ARRAY_REQUIRED", path)


def _proof_records(proofs: Sequence[Any], *, repository: str, revision: str, execution_id: str) -> tuple[dict[str, str], ...]:
    accepted: list[dict[str, str]] = []
    for proof in proofs:
        if not isinstance(proof, ExactReadProof) or proof._seal is not _PROOF_SEAL:
            raise GatewayError("DOMAIN_RECALL_EXACT_PROOF_REQUIRED")
        if proof.repository != repository or proof.commit != revision or proof.execution_id != execution_id:
            raise GatewayError("DOMAIN_RECALL_EXACT_PROOF_BINDING_MISMATCH")
        accepted.append(proof.public_dict())
    if not accepted:
        raise GatewayError("DOMAIN_RECALL_EXACT_PROOF_REQUIRED")
    return tuple(accepted)


@dataclass(frozen=True)
class DomainLearningRecallRequest:
    data: Mapping[str, Any]
    request_digest: str

    @classmethod
    def build(cls, payload: Mapping[str, Any]) -> "DomainLearningRecallRequest":
        value = _checked(payload, REQUEST_REQUIRED, "request_digest", "/request")
        for name in ("request_id", "source_trace_ref", "domain_id", "domain_repository", "domain_source_revision",
                     "scene_or_work_item", "model_or_tool", "model_version", "privacy_class"):
            _nonempty(value[name], f"/request/{name}")
        instant(str(value["observed_at"]), "/request/observed_at")
        if value["privacy_class"] not in PRIVACY:
            raise GatewayError("DOMAIN_RECALL_PRIVACY_CLASS_INVALID", "/request/privacy_class")
        if value["privacy_class"] == "SECRET_CREDENTIAL":
            raise GatewayError("DOMAIN_RECALL_SECRET_SCOPE_FORBIDDEN", "/request/privacy_class")
        for name in ("problem_signatures", "constraints", "requested_evidence_classes"):
            _array(value[name], f"/request/{name}")
        if not value["problem_signatures"]:
            raise GatewayError("DOMAIN_RECALL_PROBLEM_SIGNATURE_REQUIRED")
        return cls(_freeze(value), digest(value))

    def public_dict(self) -> dict[str, Any]:
        return {**_thaw(self.data), "request_digest": self.request_digest}


def verify_request(request: Any) -> bool:
    if not isinstance(request, DomainLearningRecallRequest):
        return False
    try:
        return DomainLearningRecallRequest.build(request.public_dict()).request_digest == request.request_digest
    except (GatewayError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class DomainLearningRecallBundle:
    data: Mapping[str, Any]
    bundle_digest: str
    _issuance: object | None = field(default=None, repr=False, compare=False)

    @classmethod
    def build(cls, payload: Mapping[str, Any]) -> "DomainLearningRecallBundle":
        value = _checked(payload, BUNDLE_REQUIRED, "bundle_digest", "/bundle")
        for name in ("bundle_id", "request_id", "request_digest", "domain_source_revision", "applicability_state", "revalidation_state"):
            _nonempty(value[name], f"/bundle/{name}")
        for name in ("matched_object_refs", "match_dimensions", "failure_condition_hits", "counterexample_hits",
                     "maturity_observations", "exact_read_proofs", "abstentions", "unknowns"):
            _array(value[name], f"/bundle/{name}")
        for ref in value["matched_object_refs"]:
            if not isinstance(ref, str) or not ref.startswith("domain-object:"):
                raise GatewayError("DOMAIN_RECALL_OBJECT_REF_INVALID")
        return cls(_freeze(value), digest(value))

    @classmethod
    def _issue(cls, payload: Mapping[str, Any]) -> "DomainLearningRecallBundle":
        structural = cls.build(payload)
        return cls(structural.data, structural.bundle_digest, _RECALL_ISSUANCE_SEAL)

    def public_dict(self) -> dict[str, Any]:
        return {**_thaw(self.data), "bundle_digest": self.bundle_digest}


def validate_bundle_structure(bundle: Any, request: DomainLearningRecallRequest | None = None) -> bool:
    if not isinstance(bundle, DomainLearningRecallBundle):
        return False
    try:
        rebuilt = DomainLearningRecallBundle.build(bundle.public_dict())
        bound = request is None or (verify_request(request) and bundle.data["request_id"] == request.data["request_id"]
                                    and bundle.data["request_digest"] == request.request_digest
                                    and bundle.data["domain_source_revision"] == request.data["domain_source_revision"])
        return rebuilt.bundle_digest == bundle.bundle_digest and bound
    except (GatewayError, TypeError, ValueError, KeyError):
        return False


def verify_bundle(bundle: Any, request: DomainLearningRecallRequest | None = None) -> bool:
    """Verify provider issuance as well as structural/digest validity.

    This is intentionally distinct from ``validate_bundle_structure``: ordinary
    public dictionaries can be structurally valid but cannot recreate a provider
    issuance token.
    """
    return isinstance(bundle, DomainLearningRecallBundle) and bundle._issuance is _RECALL_ISSUANCE_SEAL and validate_bundle_structure(bundle, request)


@dataclass(frozen=True)
class DomainLearningRecallReceipt:
    data: Mapping[str, Any]
    receipt_digest: str
    _issuance: object | None = field(default=None, repr=False, compare=False)

    @classmethod
    def build(cls, payload: Mapping[str, Any]) -> "DomainLearningRecallReceipt":
        value = _checked(payload, RECEIPT_REQUIRED, "receipt_digest", "/receipt")
        for name in ("receipt_id", "request_digest", "bundle_digest", "provider_code_identity", "exact_domain_revision", "process_compliance"):
            _nonempty(value[name], f"/receipt/{name}")
        if value["decision"] not in DECISIONS:
            raise GatewayError("DOMAIN_RECALL_DECISION_INVALID", "/receipt/decision")
        _array(value["limitations"], "/receipt/limitations")
        return cls(_freeze(value), digest(value))

    @classmethod
    def _issue(cls, payload: Mapping[str, Any]) -> "DomainLearningRecallReceipt":
        structural = cls.build(payload)
        return cls(structural.data, structural.receipt_digest, _RECALL_ISSUANCE_SEAL)

    def public_dict(self) -> dict[str, Any]:
        return {**_thaw(self.data), "receipt_digest": self.receipt_digest}


def validate_receipt_structure(receipt: Any, request: DomainLearningRecallRequest | None = None,
                               bundle: DomainLearningRecallBundle | None = None) -> bool:
    if not isinstance(receipt, DomainLearningRecallReceipt):
        return False
    try:
        rebuilt = DomainLearningRecallReceipt.build(receipt.public_dict())
        request_ok = request is None or (verify_request(request) and receipt.data["request_digest"] == request.request_digest
                                         and receipt.data["exact_domain_revision"] == request.data["domain_source_revision"])
        bundle_ok = bundle is None or (validate_bundle_structure(bundle, request) and receipt.data["bundle_digest"] == bundle.bundle_digest)
        return rebuilt.receipt_digest == receipt.receipt_digest and request_ok and bundle_ok
    except (GatewayError, TypeError, ValueError, KeyError):
        return False


def verify_receipt(receipt: Any, request: DomainLearningRecallRequest | None = None,
                   bundle: DomainLearningRecallBundle | None = None) -> bool:
    """Verify a provider-issued receipt, never merely a self-signed digest."""
    return (isinstance(receipt, DomainLearningRecallReceipt) and receipt._issuance is _RECALL_ISSUANCE_SEAL
            and (bundle is None or verify_bundle(bundle, request))
            and validate_receipt_structure(receipt, request, bundle))


def _strings(value: Any, path: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise GatewayError("DOMAIN_AUTHORITY_METADATA_ARRAY_REQUIRED", path)
    return frozenset(str(item) for item in value)


def _object_metadata(value: Mapping[str, Any], *, revision: str) -> Mapping[str, Any]:
    """Validate public, structured authority metadata without retaining lesson text."""
    if not isinstance(value, Mapping):
        raise GatewayError("DOMAIN_AUTHORITY_OBJECT_INVALID")
    public_safe(value, "/authority-object")
    forbidden = FORBIDDEN_KEYS & {str(key).casefold() for key in value}
    if forbidden:
        raise GatewayError("DOMAIN_LESSON_BODY_OR_SECRET_FORBIDDEN")
    required = {"object_id", "source_ref", "domain_source_revision", "problem_signatures", "scene_classes",
                "model_or_tool", "model_versions", "constraints", "maturity", "applicability", "non_applicability",
                "failure_conditions", "counterexamples", "revalidation_state", "evidence_refs", "authority_unknowns"}
    missing = sorted(required - set(value))
    if missing:
        raise GatewayError("DOMAIN_AUTHORITY_METADATA_MISSING", f"/authority-object/{missing[0]}")
    for name in ("object_id", "source_ref", "domain_source_revision", "model_or_tool", "maturity", "revalidation_state"):
        _nonempty(value[name], f"/authority-object/{name}")
    if value["domain_source_revision"] != revision:
        raise GatewayError("STALE_DOMAIN_REVISION")
    normalized = dict(value)
    for name in ("problem_signatures", "scene_classes", "model_versions", "constraints", "applicability",
                 "non_applicability", "failure_conditions", "counterexamples", "evidence_refs"):
        normalized[name] = sorted(_strings(value[name], f"/authority-object/{name}"))
    normalized["authority_unknowns"] = sorted(_strings(value["authority_unknowns"], "/authority-object/authority_unknowns"))
    return MappingProxyType(normalized)


def _intersection(left: Sequence[str], right: Sequence[str]) -> list[str]:
    return sorted(set(map(str, left)) & set(map(str, right)))


def _evaluate(request: DomainLearningRecallRequest, item: Mapping[str, Any]) -> tuple[dict[str, Any], str, list[str], list[str], list[str]]:
    signatures = _intersection(request.data["problem_signatures"], item["problem_signatures"])
    scene_match = request.data["scene_or_work_item"] in item["scene_classes"]
    tool_match = request.data["model_or_tool"] == item["model_or_tool"]
    version_match = request.data["model_version"] in item["model_versions"] or "*" in item["model_versions"]
    compatibility_unknown = item["model_or_tool"] == "UNKNOWN" or "UNKNOWN" in item["model_versions"]
    requested_constraints = set(map(str, request.data["constraints"]))
    allowed_constraints = set(item["constraints"])
    constraint_misses = sorted(requested_constraints - allowed_constraints)
    applicability = set(item["applicability"])
    blocked_context = sorted(set(map(str, request.data["constraints"])) & (set(item["non_applicability"]) | set(item["failure_conditions"])))
    counterexamples = sorted(set(map(str, request.data["problem_signatures"])) & set(item["counterexamples"]))
    dimensions = {
        "problem_or_symptom_signature": {"matched": signatures, "status": "MATCH" if signatures else "NO_MATCH"},
        "scene_or_work_item_class": {"matched": scene_match, "status": "MATCH" if scene_match else "NO_MATCH"},
        "model_tool_version_compatibility": {"tool": tool_match, "version": version_match, "status": "UNKNOWN" if compatibility_unknown else ("MATCH" if tool_match and version_match else "MISMATCH")},
        "explicit_constraints": {"misses": constraint_misses, "status": "MATCH" if not constraint_misses else "MISMATCH"},
        "domain_maturity_state": {"observed": item["maturity"]},
        "applicability_and_non_applicability": {"declared": sorted(applicability), "blocked": blocked_context},
        "failure_conditions_and_counterexamples": {"failure_hits": blocked_context, "counterexample_hits": counterexamples},
        "revalidation_conflict_deprecation_state": {"observed": item["revalidation_state"]},
        "provenance_and_evidence_availability": {"evidence_refs": list(item["evidence_refs"]), "status": "AVAILABLE" if item["evidence_refs"] else "UNKNOWN"},
    }
    failures = blocked_context
    reasons: list[str] = []
    if not signatures or not scene_match:
        reasons.append("STRUCTURAL_MATCH_INSUFFICIENT")
    if not tool_match or not version_match:
        reasons.append("MODEL_OR_VERSION_MISMATCH")
    if constraint_misses:
        reasons.append("CONSTRAINT_NOT_APPLICABLE")
    if failures or counterexamples:
        reasons.append("FAILURE_OR_COUNTEREXAMPLE_HIT")
    if item["revalidation_state"] in {"CONFLICTED", "DEPRECATED", "NEEDS_REVALIDATION"}:
        reasons.append(f"DOMAIN_STATE_{item['revalidation_state']}")
    if not item["evidence_refs"]:
        reasons.append("DOMAIN_EVIDENCE_UNAVAILABLE")
    if item["authority_unknowns"]:
        reasons.extend(f"DOMAIN_AUTHORITY_UNKNOWN:{item}" for item in item["authority_unknowns"])
    if failures or counterexamples or item["revalidation_state"] in {"CONFLICTED", "DEPRECATED"}:
        decision = "CONFLICTED"
    elif not tool_match or not version_match or compatibility_unknown or item["authority_unknowns"] or item["revalidation_state"] == "NEEDS_REVALIDATION":
        decision = "NEEDS_REVALIDATION"
    elif reasons:
        decision = "ABSTAINED"
    else:
        decision = "RECALLED"
    return dimensions, decision, failures, counterexamples, reasons


class DomainLearningRecallProvider:
    """Pure orchestration over validated structured authority metadata; no domain writer exists."""

    provider_code_identity = "R140_DOMAIN_LEARNING_RECALL_PROVIDER_V1"

    def recall(self, request: DomainLearningRecallRequest, *, authority_metadata: Sequence[Mapping[str, Any]],
               exact_read_proofs: Sequence[Any], execution_id: str) -> tuple[DomainLearningRecallBundle, DomainLearningRecallReceipt]:
        if not verify_request(request):
            raise GatewayError("DOMAIN_RECALL_REQUEST_INVALID")
        proofs = _proof_records(exact_read_proofs, repository=str(request.data["domain_repository"]),
                                revision=str(request.data["domain_source_revision"]), execution_id=execution_id)
        objects = [_object_metadata(item, revision=str(request.data["domain_source_revision"])) for item in authority_metadata]
        evaluated = [_evaluate(request, item) for item in objects]
        ranked = sorted(zip(objects, evaluated), key=lambda pair: (pair[1][1] == "RECALLED", pair[1][1] == "NEEDS_REVALIDATION", bool(pair[1][0]["problem_or_symptom_signature"]["matched"])), reverse=True)
        selected = ranked[:1]
        if not selected:
            decision, selected = "UNSUPPORTED", []
        else:
            decision = selected[0][1][1]
        refs = [f"domain-object:{item['object_id']}@{request.data['domain_source_revision']}" for item, _ in selected]
        dimensions = [result[0] for _, result in selected]
        failures = sorted({hit for _, result in selected for hit in result[2]})
        counters = sorted({hit for _, result in selected for hit in result[3]})
        abstentions = sorted({reason for _, result in selected for reason in result[4]})
        maturity = [{"object_ref": ref, "observed": item["maturity"]} for ref, (item, _) in zip(refs, selected)]
        revalidation = "CURRENT" if decision == "RECALLED" else decision
        bundle = DomainLearningRecallBundle._issue({
            "schema_version": "DomainLearningRecallBundle/v1", "bundle_id": f"recall:{request.request_digest[:24]}",
            "request_id": request.data["request_id"], "request_digest": request.request_digest,
            "domain_source_revision": request.data["domain_source_revision"], "matched_object_refs": refs,
            "match_dimensions": dimensions, "applicability_state": decision, "failure_condition_hits": failures,
            "counterexample_hits": counters, "maturity_observations": maturity, "revalidation_state": revalidation,
            "exact_read_proofs": list(proofs), "abstentions": abstentions,
            "unknowns": sorted({unknown for item, _ in selected for unknown in item["authority_unknowns"]}) if selected else ["NO_DOMAIN_OBJECT_AVAILABLE"],
        })
        receipt = DomainLearningRecallReceipt._issue({
            "schema_version": "DomainLearningRecallReceipt/v1", "receipt_id": f"recall-receipt:{bundle.bundle_digest[:24]}",
            "request_digest": request.request_digest, "bundle_digest": bundle.bundle_digest,
            "provider_code_identity": self.provider_code_identity, "exact_domain_revision": request.data["domain_source_revision"],
            "decision": decision, "process_compliance": "PASS" if verify_bundle(bundle, request) else "UNVERIFIED",
            "limitations": ["RECALL_IS_NOT_CREATIVE_OUTCOME_PROOF", "DOMAIN_WRITE_NOT_AUTHORIZED"],
        })
        return bundle, receipt


def _git_show_text(source: Path, revision: str, path: str) -> str:
    result = subprocess.run(["git", "-C", str(source), "show", f"{revision}:{path}"], capture_output=True, check=False)
    if result.returncode:
        raise GatewayError("EXACT_SOURCE_READ_FAILED")
    return result.stdout.decode("utf-8", errors="strict")


def _list(value: Any, path: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise GatewayError("DOMAIN_AUTHORITY_PROJECTION_INVALID", path)
    return list(value)


def _ai_film_authority_projection(source: Path, revision: str, object_id: str) -> tuple[dict[str, Any], str]:
    """Derive replay decision metadata only from exact AI Film structured bytes."""
    if object_id == "AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY":
        path, pointer = AI_FILM_GOLDEN_CASES_PATH, "GPC-20260813-001"
        document = yaml.safe_load(_git_show_text(source, revision, path))
        cases = document.get("cases") if isinstance(document, Mapping) else None
        case = next((item for item in cases or [] if isinstance(item, Mapping) and item.get("case_id") == pointer), None)
        if not isinstance(case, Mapping):
            raise GatewayError("DOMAIN_OBJECT_UNRESOLVED")
        task_class = _nonempty(case.get("task_class"), "/ai-film/golden/task_class")
        applicable = _list(case.get("applicable_context"), "/ai-film/golden/applicable_context")
        non_applicable = _list(case.get("non_applicable_context"), "/ai-film/golden/non_applicable_context")
        failures = _list(case.get("failure_boundaries"), "/ai-film/golden/failure_boundaries")
        triggers = _list(case.get("revalidation_triggers"), "/ai-film/golden/revalidation_triggers")
        maturity = ":".join((_nonempty(case.get("case_status"), "/ai-film/golden/case_status"),
                              _nonempty(case.get("verdict_scope"), "/ai-film/golden/verdict_scope"),
                              _nonempty(case.get("verdict_basis"), "/ai-film/golden/verdict_basis")))
        dependency = case.get("model_or_tool_dependency")
        if not isinstance(dependency, Mapping) or dependency.get("status") != "unknown":
            raise GatewayError("DOMAIN_AUTHORITY_PROJECTION_INVALID", "/ai-film/golden/model_or_tool_dependency")
        return ({"object_id": object_id, "source_ref": f"domain-object:{path}#case_id={pointer}", "domain_source_revision": revision,
                 "problem_signatures": [task_class], "scene_classes": applicable, "model_or_tool": "UNKNOWN", "model_versions": ["UNKNOWN"],
                 "constraints": applicable, "maturity": maturity, "applicability": applicable, "non_applicability": non_applicable,
                 "failure_conditions": failures, "counterexamples": [], "revalidation_state": "NEEDS_REVALIDATION" if triggers else "CURRENT",
                 "evidence_refs": [f"domain-object:{path}#case_id={pointer}"], "authority_unknowns": ["MODEL_OR_TOOL_VERSION_COMPATIBILITY_UNKNOWN"]}, path)
    if object_id == "CD25-KAIM-WINDOW-AB-20260815":
        path, pointer = AI_FILM_REGRESSION_CASES_PATH, "REG-CDANCE25-TEMPORAL-EXCLUSIVITY-001"
        document = yaml.safe_load(_git_show_text(source, revision, path))
        cases = document.get("cases") if isinstance(document, Mapping) else None
        case = next((item for item in cases or [] if isinstance(item, Mapping) and item.get("id") == pointer), None)
        evidence = case.get("scene_evidence") if isinstance(case, Mapping) else None
        if not isinstance(evidence, Mapping) or evidence.get("experiment_id") != object_id:
            raise GatewayError("DOMAIN_OBJECT_UNRESOLVED")
        work_item = _nonempty(evidence.get("work_item"), "/ai-film/cd25/work_item")
        maturity = _nonempty(case.get("maturity"), "/ai-film/cd25/maturity")
        status = _nonempty(evidence.get("evidence_status"), "/ai-film/cd25/evidence_status")
        return ({"object_id": object_id, "source_ref": f"domain-object:{path}#id={pointer}", "domain_source_revision": revision,
                 "problem_signatures": [work_item], "scene_classes": [work_item], "model_or_tool": "UNKNOWN", "model_versions": ["UNKNOWN"],
                 "constraints": [], "maturity": maturity, "applicability": [], "non_applicability": [], "failure_conditions": [],
                 "counterexamples": [], "revalidation_state": "NEEDS_REVALIDATION", "evidence_refs": [f"domain-object:{path}#id={pointer}"],
                 "authority_unknowns": ["MODEL_OR_TOOL_VERSION_COMPATIBILITY_UNKNOWN", f"EVIDENCE_STATUS:{status}"]}, path)
    raise GatewayError("DOMAIN_OBJECT_UNRESOLVED")


def ai_film_domain_learning_recall_read_only_smoke(root: str | Path, request: DomainLearningRecallRequest, *, object_id: str) -> dict[str, Any]:
    """Bounded public AI Film replay with exact reads and zero mutation verification.

    The function owns the projection: caller-supplied metadata is deliberately
    not accepted. Missing canonical fields remain explicit UNKNOWN/revalidation
    rather than being inferred by the caller.
    """
    if not verify_request(request):
        raise GatewayError("DOMAIN_RECALL_REQUEST_INVALID")
    source = Path(root).resolve()
    before = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True, encoding="utf-8")
    if before:
        raise GatewayError("AI_FILM_SOURCE_NOT_CLEAN")
    revision = str(request.data["domain_source_revision"])
    execution_id = f"r140-recall:{request.request_digest[:24]}"
    metadata, source_path = _ai_film_authority_projection(source, revision, object_id)
    proofs = exact_git_read_proofs(source, repository=str(request.data["domain_repository"]), commit=revision,
                                   paths=("PROJECT_INDEX.yaml", source_path), execution_id=execution_id)
    bundle, receipt = DomainLearningRecallProvider().recall(request, authority_metadata=(metadata,), exact_read_proofs=proofs,
                                                              execution_id=execution_id)
    after = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True, encoding="utf-8")
    if after != before:
        raise GatewayError("AI_FILM_ZERO_MUTATION_VIOLATION")
    return {"bundle": bundle.public_dict(), "receipt": receipt.public_dict(), "read_proofs": [proof.public_dict() for proof in proofs],
            "authority_projection": "DOMAIN_OWNED_EXACT_STRUCTURED_PROJECTION", "authority_projection_ref": metadata["source_ref"],
            "source_status_before": "CLEAN", "source_status_after": "CLEAN", "domain_write_authorized": False,
            "formal_skill_promotion_authorized": False, "raw_domain_body_returned": False}


def route_recall(request: Any) -> dict[str, Any]:
    if not isinstance(request, DomainLearningRecallRequest) or not verify_request(request):
        raise GatewayError("DOMAIN_RECALL_REQUEST_REQUIRED")
    return {"request_ref": f"domain-recall:{request.request_digest}", "execution_class": "DOMAIN_WORKFLOW",
            "domain_write_authorized": False, "domain_maturity_authorized": False,
            "formal_skill_promotion_authorized": False, "generic_cross_repo_writer_authorized": False}
