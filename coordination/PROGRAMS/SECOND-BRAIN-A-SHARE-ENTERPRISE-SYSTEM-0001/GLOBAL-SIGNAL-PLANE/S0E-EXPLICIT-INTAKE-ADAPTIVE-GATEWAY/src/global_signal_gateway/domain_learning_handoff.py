"""R139 Stage-A, public-safe domain-learning handoff contracts.

This module deliberately does not contain a domain writer.  It can preserve a
verified handoff, route it inside the Signal Tower, and perform a read-only
AI-Film authority smoke.  A domain receipt remains unverified unless a future
domain-owned processor supplies attributable evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import subprocess
import yaml

from .gateway import (
    AI_FILM_COMMIT,
    AI_FILM_REPOSITORY,
    GatewayError,
    digest,
    exact_git_read_proofs,
    instant,
    public_safe,
)


PACKET_REQUIRED = frozenset({
    "schema_version", "handoff_id", "idempotency_key", "source_trace_ref", "source_scope", "source_ref",
    "observed_at", "domain_id", "domain_repository", "domain_source_revision", "feedback_kind", "user_intent",
    "user_verdict", "work_item_id", "model_or_tool", "model_version", "prompt_or_input_evidence_refs",
    "result_evidence_refs", "asset_refs", "observed_effects", "candidate_goal", "privacy_class",
    "public_safe_summary", "confidence_of_source_interpretation", "requested_domain_action", "materiality",
    "risk_flags", "unknowns",
})
RECEIPT_REQUIRED = frozenset({
    "schema_version", "receipt_id", "handoff_id", "handoff_digest", "domain_id", "domain_source_revision",
    "processor_capability_id", "processor_code_identity", "decision", "domain_classification",
    "affected_object_refs", "maturity_before", "maturity_after", "writeback_status", "eval_refs",
    "regression_refs", "counterexample_refs", "unknowns", "limitations", "needs_revalidation",
    "process_compliance", "outcome_quality",
})
FEEDBACK = frozenset({
    "EXPLICIT_EXCELLENT_CASE", "POSITIVE_USER_VERDICT", "NEGATIVE_USER_VERDICT", "REVISION_DELTA",
    "REAL_GENERATION_EVIDENCE", "USER_CORRECTION", "STABLE_PREFERENCE_CANDIDATE",
    "SYSTEM_DEFECT_CANDIDATE", "CONFLICT_OR_COUNTEREXAMPLE", "UNKNOWN_LEARNING_RELEVANCE",
})
ACTIONS = frozenset({"CLASSIFY_ONLY", "LEARNING_CANDIDATE", "TARGETED_EVAL", "REGRESSION_CANDIDATE", "CORRECTION_RECONCILIATION"})
DECISIONS = frozenset({"ACCEPTED", "REJECTED", "DUPLICATE", "NEEDS_MORE_EVIDENCE", "CONFLICT", "NEEDS_HIGHER_GATE"})
WRITEBACK = frozenset({"NONE", "CANDIDATE_RECORDED", "DOMAIN_PR_OPENED", "DOMAIN_COMMIT_VERIFIED", "WAITING_GATE"})
RELATIONS = frozenset({"REFINES", "SUPERSEDES", "REVOKES", "CONTRADICTS"})
FORBIDDEN_KEYS = frozenset({
    "raw_source_body", "raw_private_body", "raw_private_media", "raw_media", "password", "api_key", "token",
    "cookie", "session_credential", "private_key", "raw_chain_of_thought", "mfa_or_recovery_code",
})

# These are domain-owned selector aliases, resolved only for the two bounded
# Stage-A read-set smokes.  They are paths in the exact checked-out AI Film tree,
# not writable target routes.
AI_FILM_SELECTOR_PATHS = {
    "PROJECT_INDEX.yaml": "PROJECT_INDEX.yaml",
    "AI\u7535\u5f71\u7cfb\u7edf": "01_AI\u7535\u5f71\u7cfb\u7edf/AI\u7535\u5f71\u7cfb\u7edf.md",
    "\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5b66\u4e60\u534f\u8bae": "08_\u7cfb\u7edf\u5b66\u4e60/\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5b66\u4e60\u534f\u8bae.md",
    "\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce": "08_\u7cfb\u7edf\u5b66\u4e60/\u53cd\u9988\u53cd\u63a8\u4e0e\u7cfb\u7edf\u53cd\u54fa\u5f15\u64ce.md",
    "\u5b98\u65b9\u8d44\u6599\u4e0e\u8bc1\u636e\u7d22\u5f15": "09_\u8d44\u6599\u8bc1\u636e/\u5b98\u65b9\u8d44\u6599\u4e0e\u8bc1\u636e\u7d22\u5f15.md",
    "\u4f18\u79c0\u63d0\u793a\u8bcd\u6848\u4f8b\u5e93": "11_\u9a8c\u6536/golden_prompt_cases.yaml",
    "golden_case_director_pull_schema": "10_\u8fd0\u884c\u65f6/golden_case_director_pull_schema.yaml",
    "maturity_model": "10_\u8fd0\u884c\u65f6/maturity_model.yaml",
    "UNKNOWN_REGISTRY": "12_\u672a\u77e5\u9879/UNKNOWN_REGISTRY.yaml",
    "C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93": "08_\u7cfb\u7edf\u5b66\u4e60/C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93.md",
}


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
        raise GatewayError("HANDOFF_NOT_OBJECT", path)
    value = _thaw(payload)
    public_safe(value, path)
    forbidden = FORBIDDEN_KEYS & {str(key).casefold() for key in value}
    if forbidden:
        raise GatewayError("PRIVATE_OR_SECRET_FIELD_FORBIDDEN", path)
    missing = sorted(required - set(value))
    if missing:
        raise GatewayError("HANDOFF_REQUIRED_FIELD_MISSING", f"{path}/{missing[0]}")
    value.pop(digest_key, None)
    return value


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GatewayError("HANDOFF_NONEMPTY_STRING_REQUIRED", path)
    return value


def _array(value: Any, path: str) -> None:
    if not isinstance(value, (list, tuple)):
        raise GatewayError("HANDOFF_ARRAY_REQUIRED", path)


@dataclass(frozen=True)
class DomainLearningHandoffPacket:
    data: Mapping[str, Any]
    packet_digest: str

    @classmethod
    def build(cls, payload: Mapping[str, Any]) -> "DomainLearningHandoffPacket":
        value = _checked(payload, PACKET_REQUIRED, "packet_digest", "/packet")
        for name in ("handoff_id", "idempotency_key", "source_trace_ref", "source_scope", "source_ref", "domain_id",
                     "domain_repository", "domain_source_revision", "user_intent", "user_verdict", "work_item_id",
                     "model_or_tool", "model_version", "candidate_goal", "privacy_class", "public_safe_summary",
                     "confidence_of_source_interpretation"):
            _nonempty(value[name], f"/packet/{name}")
        instant(str(value["observed_at"]), "/packet/observed_at")
        if value["feedback_kind"] not in FEEDBACK:
            raise GatewayError("HANDOFF_FEEDBACK_KIND_INVALID", "/packet/feedback_kind")
        if value["requested_domain_action"] not in ACTIONS:
            raise GatewayError("HANDOFF_ACTION_INVALID", "/packet/requested_domain_action")
        if value["materiality"] not in {"TRACE_ONLY", "DURABLE_SIGNAL"}:
            raise GatewayError("HANDOFF_MATERIALITY_INVALID", "/packet/materiality")
        for name in ("prompt_or_input_evidence_refs", "result_evidence_refs", "asset_refs", "observed_effects", "risk_flags", "unknowns"):
            _array(value[name], f"/packet/{name}")
        return cls(_freeze(value), digest(value))

    def public_dict(self) -> dict[str, Any]:
        return {**_thaw(self.data), "packet_digest": self.packet_digest}


def verify_packet(packet: Any) -> bool:
    if not isinstance(packet, DomainLearningHandoffPacket):
        return False
    try:
        return DomainLearningHandoffPacket.build(packet.public_dict()).packet_digest == packet.packet_digest
    except (GatewayError, TypeError, ValueError):
        return False


@dataclass(frozen=True)
class DomainLearningReceipt:
    data: Mapping[str, Any]
    receipt_digest: str

    @classmethod
    def build(cls, payload: Mapping[str, Any]) -> "DomainLearningReceipt":
        value = _checked(payload, RECEIPT_REQUIRED, "receipt_digest", "/receipt")
        for name in ("receipt_id", "handoff_id", "handoff_digest", "domain_id", "domain_source_revision",
                     "processor_capability_id", "processor_code_identity", "domain_classification", "maturity_before",
                     "maturity_after", "process_compliance", "outcome_quality"):
            _nonempty(value[name], f"/receipt/{name}")
        if value["decision"] not in DECISIONS or value["writeback_status"] not in WRITEBACK:
            raise GatewayError("RECEIPT_ENUM_INVALID")
        for name in ("affected_object_refs", "eval_refs", "regression_refs", "counterexample_refs", "unknowns", "limitations"):
            _array(value[name], f"/receipt/{name}")
        if not isinstance(value["needs_revalidation"], bool):
            raise GatewayError("RECEIPT_BOOLEAN_REQUIRED", "/receipt/needs_revalidation")
        if value["writeback_status"] != "NONE":
            evidence = value.get("writeback_evidence_refs")
            if not isinstance(evidence, (list, tuple)) or not evidence:
                raise GatewayError("DOMAIN_WRITEBACK_EVIDENCE_REQUIRED")
        return cls(_freeze(value), digest(value))

    def public_dict(self) -> dict[str, Any]:
        return {**_thaw(self.data), "receipt_digest": self.receipt_digest}


def verify_receipt(receipt: Any, packet: DomainLearningHandoffPacket | None = None) -> bool:
    if not isinstance(receipt, DomainLearningReceipt):
        return False
    try:
        rebuilt = DomainLearningReceipt.build(receipt.public_dict())
        bound = packet is None or (
            verify_packet(packet)
            and receipt.data["handoff_id"] == packet.data["handoff_id"]
            and receipt.data["handoff_digest"] == packet.packet_digest
            and receipt.data["domain_id"] == packet.data["domain_id"]
            and receipt.data["domain_source_revision"] == packet.data["domain_source_revision"]
        )
        return rebuilt.receipt_digest == receipt.receipt_digest and bound
    except (GatewayError, KeyError, TypeError, ValueError):
        return False


def route_packet(packet: DomainLearningHandoffPacket) -> dict[str, Any]:
    if not verify_packet(packet):
        raise GatewayError("HANDOFF_PACKET_INVALID")
    durable = packet.data["materiality"] == "DURABLE_SIGNAL"
    return {
        "packet_ref": f"handoff:{packet.packet_digest}",
        "persistence_class": "DURABLE_SIGNAL" if durable else "TRACE_ONLY",
        "execution_class": "GOVERNED_MISSION" if durable else "DOMAIN_WORKFLOW",
        "domain_write_authorized": False,
        "formal_task_authorized": False,
        "domain_maturity_authorized": False,
        "retrieval_metadata": {
            "source_scope": packet.data["source_scope"],
            "work_item_id": packet.data["work_item_id"],
            "model_or_tool": packet.data["model_or_tool"],
            "model_version": packet.data["model_version"],
            "applicable_context": packet.data.get("applicable_context", []),
            "non_applicable_context": packet.data.get("non_applicable_context", []),
            "failure_conditions": packet.data.get("failure_conditions", []),
            "revalidation_state": "NEEDS_REVALIDATION" if packet.data.get("needs_revalidation") else "CURRENT_AT_PACKET_REVISION",
            "risk_flags": packet.data["risk_flags"],
            "unknowns": packet.data["unknowns"],
        },
    }


def require_exact_domain_revision(packet: DomainLearningHandoffPacket, observed_revision: str) -> None:
    if not verify_packet(packet) or packet.data["domain_source_revision"] != observed_revision:
        raise GatewayError("STALE_DOMAIN_REVISION")


def stage_a_receipt(packet: DomainLearningHandoffPacket, *, processor_capability_id: str = "UNKNOWN", processor_code_identity: str = "UNKNOWN") -> DomainLearningReceipt:
    """Return an explicitly non-attributable receipt candidate, never a domain writeback."""
    if not verify_packet(packet):
        raise GatewayError("HANDOFF_PACKET_INVALID")
    return DomainLearningReceipt.build({
        "schema_version": "DomainLearningReceipt/v1", "receipt_id": f"dry-run:{packet.packet_digest[:24]}",
        "handoff_id": packet.data["handoff_id"], "handoff_digest": packet.packet_digest,
        "domain_id": packet.data["domain_id"], "domain_source_revision": packet.data["domain_source_revision"],
        "processor_capability_id": processor_capability_id, "processor_code_identity": processor_code_identity,
        "decision": "NEEDS_MORE_EVIDENCE", "domain_classification": "UNKNOWN", "affected_object_refs": [],
        "maturity_before": "UNKNOWN", "maturity_after": "UNKNOWN", "writeback_status": "NONE", "eval_refs": [],
        "regression_refs": [], "counterexample_refs": [], "unknowns": ["DOMAIN_PROCESSOR_NOT_ATTRIBUTABLE"],
        "limitations": ["STAGE_A_DRY_RUN"], "needs_revalidation": True, "process_compliance": "UNVERIFIED",
        "outcome_quality": "NOT_YET_OBSERVED",
    })


class DomainLearningHandoffLedger:
    """In-memory Stage-A idempotency index; it is neither a domain store nor a writer."""
    def __init__(self) -> None:
        self._packets: dict[str, DomainLearningHandoffPacket] = {}
        self._keys: dict[str, str] = {}
        self._relations: list[dict[str, str]] = []

    def ingest(self, packet: DomainLearningHandoffPacket) -> dict[str, Any]:
        if not verify_packet(packet):
            raise GatewayError("HANDOFF_PACKET_INVALID")
        key = str(packet.data["idempotency_key"])
        prior = self._keys.get(key)
        if prior:
            existing = self._packets[prior]
            if existing.packet_digest != packet.packet_digest:
                raise GatewayError("IDEMPOTENCY_COLLISION_FAIL_CLOSED")
            return {"status": "DUPLICATE", "existing_packet_ref": prior, "domain_write_authorized": False}
        ref = f"handoff:{packet.packet_digest}"
        self._packets[ref] = packet
        self._keys[key] = ref
        return {"status": "ROUTED", "packet_ref": ref, **route_packet(packet)}

    def correct(self, original_ref: str, packet: DomainLearningHandoffPacket, relation: str) -> dict[str, Any]:
        if original_ref not in self._packets or relation not in RELATIONS:
            raise GatewayError("HANDOFF_CORRECTION_INVALID")
        result = self.ingest(packet)
        if result["status"] != "ROUTED":
            raise GatewayError("HANDOFF_CORRECTION_REPLAY_REJECTED")
        self._relations.append({"from": str(result["packet_ref"]), "to": original_ref, "relation": relation})
        return {**result, "history_preserved": True, "relation": relation}

    def relations(self) -> tuple[Mapping[str, str], ...]:
        return tuple(MappingProxyType(dict(item)) for item in self._relations)


def _selector_path(selector: str) -> str:
    key = str(selector).split("#", 1)[0]
    path = AI_FILM_SELECTOR_PATHS.get(key)
    if path is None:
        raise GatewayError("DOMAIN_READ_SET_SELECTOR_UNRESOLVED")
    return path


def _read_set_paths(read_sets: Mapping[str, Any], name: str, flags: Mapping[str, bool]) -> tuple[str, ...]:
    entry = read_sets.get("read_sets", {}).get(name)
    if not isinstance(entry, Mapping) or not isinstance(entry.get("always"), list) or not isinstance(entry.get("conditional", {}), Mapping):
        raise GatewayError("DOMAIN_READ_SET_UNRESOLVED")
    selectors = [str(item) for item in entry["always"]]
    selectors.extend(str(selector) for flag, selector in entry.get("conditional", {}).items() if flags.get(str(flag), False))
    return tuple(sorted({_selector_path(selector) for selector in selectors}))


def _git_show_text(source: Path, revision: str, path: str) -> str:
    result = subprocess.run(["git", "-C", str(source), "show", f"{revision}:{path}"], capture_output=True, check=False)
    if result.returncode:
        raise GatewayError("EXACT_SOURCE_READ_FAILED")
    return result.stdout.decode("utf-8", errors="strict")


def ai_film_domain_learning_read_only_smoke(
    root: str | Path,
    packet: DomainLearningHandoffPacket,
    *,
    read_set: str,
    exact_object: str,
    conditional_flags: Mapping[str, bool] = MappingProxyType({}),
) -> dict[str, Any]:
    """Execute only exact, read-only AI Film authority reads for an R139 Stage-A handoff.

    The read-set is the authority for this smoke.  A missing director-route match
    is intentionally represented as not required, rather than invented or treated
    as a hidden Stage-B block.
    """
    if not verify_packet(packet):
        raise GatewayError("HANDOFF_PACKET_INVALID")
    if packet.data["domain_id"] != "AI_FILM" or packet.data["domain_repository"] != AI_FILM_REPOSITORY:
        raise GatewayError("UNSUPPORTED_DOMAIN_PROCESSOR")
    require_exact_domain_revision(packet, AI_FILM_COMMIT)
    source = Path(root).resolve()
    before = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True, encoding="utf-8")
    if before:
        raise GatewayError("AI_FILM_SOURCE_NOT_CLEAN")
    execution_id = f"r139-domain-learning:{packet.packet_digest[:24]}"
    seed = exact_git_read_proofs(source, repository=AI_FILM_REPOSITORY, commit=AI_FILM_COMMIT,
                                 paths=("PROJECT_INDEX.yaml", "10_\u8fd0\u884c\u65f6/read_sets.yaml"), execution_id=execution_id)
    read_sets = yaml.safe_load(_git_show_text(source, AI_FILM_COMMIT, "10_\u8fd0\u884c\u65f6/read_sets.yaml"))
    if not isinstance(read_sets, Mapping):
        raise GatewayError("DOMAIN_READ_SET_UNRESOLVED")
    required_paths = _read_set_paths(read_sets, read_set, conditional_flags)
    extra = [path for path in required_paths if path not in {proof.path for proof in seed}]
    proofs = seed + exact_git_read_proofs(source, repository=AI_FILM_REPOSITORY, commit=AI_FILM_COMMIT,
                                          paths=extra, execution_id=execution_id)
    object_path = "11_\u9a8c\u6536/golden_prompt_cases.yaml" if read_set == "golden_prompt_ingestion" else "08_\u7cfb\u7edf\u5b66\u4e60/C-DANCE2.5\u771f\u5b9e\u751f\u6210\u53cd\u9988\u5e93.md"
    object_text = _git_show_text(source, AI_FILM_COMMIT, object_path)
    if object_path not in {proof.path for proof in proofs} or exact_object not in object_text:
        raise GatewayError("DOMAIN_OBJECT_UNRESOLVED")
    if read_set == "golden_prompt_ingestion":
        required_terms = ("golden_user_approved", "prompt_only")
        observed_constraints = {
            "verdict_basis": "prompt_only",
            "approval_status": "golden_user_approved",
            "promotion": "NOT_AUTHORIZED",
        }
    elif read_set == "system_research":
        required_terms = ("candidate", "confounded_inconclusive")
        observed_constraints = {
            "reusable_rule_maturity": "candidate",
            "soac_comparison_result": "confounded_inconclusive",
            "soac_superiority": "NOT_CLAIMED",
        }
    else:
        required_terms, observed_constraints = (), {}
    if any(term not in object_text for term in required_terms):
        raise GatewayError("DOMAIN_EVIDENCE_CONSTRAINT_UNRESOLVED")
    after = subprocess.check_output(["git", "-C", str(source), "status", "--porcelain"], text=True, encoding="utf-8")
    if after != before:
        raise GatewayError("AI_FILM_ZERO_MUTATION_VIOLATION")
    receipt = stage_a_receipt(packet)
    return {
        "packet_ref": f"handoff:{packet.packet_digest}", "receipt_candidate": receipt.public_dict(),
        "read_set": read_set, "exact_object": exact_object,
        "read_proofs": [proof.public_dict() for proof in proofs],
        "observed_evidence_constraints": observed_constraints,
        "director_route_requirement": "NOT_REQUIRED_FOR_THIS_READ_SET_SMOKE",
        "domain_write_authorized": False, "writeback_status": "NONE", "source_status_before": "CLEAN",
        "source_status_after": "CLEAN", "route": route_packet(packet),
    }
