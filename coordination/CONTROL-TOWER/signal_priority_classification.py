from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from idle_signal_scheduler import P3, P4


EVIDENCE_SCHEMA = "TrustedIdlePriorityClassificationEvidence/v1"
POLICY_VERSION = "R156/v1"

ACTION_CAPABLE_EPISTEMIC_STATES = frozenset(
    {"USER_EXPLICIT", "CONFIRMED_FACT", "HIGH_CONFIDENCE_INFERENCE"}
)
RESEARCH_EPISTEMIC_STATE = "CANDIDATE_HYPOTHESIS"
INELIGIBLE_EPISTEMIC_STATES = frozenset({"UNKNOWN", "NEEDS_REVALIDATION"})
R154_RANKING_PREFIX = "r154://ranking/"
R155_UPGRADE_PREFIX = "r155://ranking-upgrade/"


class PriorityClassificationError(ValueError):
    """Stable fail-closed error for R156 priority evidence derivation."""

    def __init__(self, code: str, path: str = "/") -> None:
        super().__init__(code)
        self.code = code
        self.path = path


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _nonempty(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PriorityClassificationError("INVALID_STRING", path)
    return value.strip()


def _sha256(value: Any, path: str) -> str:
    text = _nonempty(value, path)
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise PriorityClassificationError("INVALID_SHA256", path)
    return text


def _refs(value: Sequence[str]) -> list[str]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise PriorityClassificationError("SOURCE_EVIDENCE_REFS_INVALID", "/source_evidence_refs")
    refs = [
        _nonempty(item, f"/source_evidence_refs/{index}")
        for index, item in enumerate(value)
    ]
    if not refs:
        raise PriorityClassificationError("SOURCE_EVIDENCE_REQUIRED", "/source_evidence_refs")
    return sorted(set(refs))


def derive_trusted_priority_evidence(
    *,
    signal_ref: str,
    epistemic_state: str,
    base_opportunity_digest: str,
    source_evidence_refs: Sequence[str],
) -> dict[str, Any]:
    """Classify only from canonical S0C epistemic state already proven by R153.

    R156 does not become a second S0C replay/proof parser. The sealed current
    materializer supplies the post-R155 opportunity, while this evidence layer
    requires the retained R154 and R155 evidence chain plus that exact base
    digest. It has no free-text, signal-kind, caller-priority, sentiment or
    model-classification input and cannot select or release work.
    """
    signal = _nonempty(signal_ref, "/signal_ref")
    state = _nonempty(epistemic_state, "/epistemic_state").upper()
    base_digest = _sha256(base_opportunity_digest, "/base_opportunity_digest")
    refs = _refs(source_evidence_refs)

    if not any(ref.startswith(R154_RANKING_PREFIX) for ref in refs):
        raise PriorityClassificationError(
            "R154_RANKING_EVIDENCE_REQUIRED", "/source_evidence_refs"
        )
    if not any(ref.startswith(R155_UPGRADE_PREFIX) for ref in refs):
        raise PriorityClassificationError(
            "R155_RANKING_UPGRADE_EVIDENCE_REQUIRED", "/source_evidence_refs"
        )

    if state in INELIGIBLE_EPISTEMIC_STATES:
        raise PriorityClassificationError(
            "INELIGIBLE_EPISTEMIC_STATE_MUST_REMAIN_BLOCKED", "/epistemic_state"
        )
    if state == RESEARCH_EPISTEMIC_STATE:
        priority = P4
        reason = "CANONICAL_CANDIDATE_HYPOTHESIS_REQUIRES_RESEARCH"
    elif state in ACTION_CAPABLE_EPISTEMIC_STATES:
        priority = P3
        reason = "CANONICAL_ACTION_CAPABLE_EPISTEMIC_STATE_PRESERVES_P3"
    else:
        raise PriorityClassificationError(
            "UNRECOGNIZED_EPISTEMIC_STATE", "/epistemic_state"
        )

    value: dict[str, Any] = {
        "schema_version": EVIDENCE_SCHEMA,
        "policy_version": POLICY_VERSION,
        "signal_ref": signal,
        "base_opportunity_digest": base_digest,
        "epistemic_state": state,
        "priority_class": priority,
        "reason": reason,
        "source_evidence_refs": refs,
        "authority_boundary": {
            "selects_opportunity": False,
            "releases_task": False,
            "creates_task": False,
            "creates_issue": False,
            "creates_route": False,
            "creates_work_claim": False,
            "creates_worker_slot": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_w3_write": False,
            "grants_merge_authority": False,
        },
    }
    value["evidence_digest"] = _digest(value)
    return value


def priority_evidence_ref(value: Mapping[str, Any]) -> str:
    if value.get("schema_version") != EVIDENCE_SCHEMA:
        raise PriorityClassificationError("PRIORITY_EVIDENCE_SCHEMA_INVALID")
    if value.get("policy_version") != POLICY_VERSION:
        raise PriorityClassificationError("PRIORITY_POLICY_VERSION_INVALID")
    digest = _sha256(value.get("evidence_digest"), "/evidence_digest")
    base = _sha256(value.get("base_opportunity_digest"), "/base_opportunity_digest")
    priority = value.get("priority_class")
    if priority not in {P3, P4}:
        raise PriorityClassificationError("PRIORITY_CLASS_INVALID", "/priority_class")
    return (
        f"r156://priority/{digest}#policy={POLICY_VERSION};"
        f"priority={priority};base={base}"
    )
