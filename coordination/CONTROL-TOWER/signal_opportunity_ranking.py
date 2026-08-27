from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from idle_signal_scheduler import P3


RANKING_SCHEMA = "TrustedSignalOpportunityRankingEvidence/v1"
POLICY_VERSION = "R154/v1"
MAX_AGE_CYCLES = 20
NEUTRAL_USER_VALUE = 50
NEUTRAL_MATERIALITY = 50

SIGNAL_MATERIALITY_SCORES = {
    "LOW": 25,
    "MATERIAL": 50,
}

CHANGE_SURFACE_WEIGHTS = {
    "write_paths": 15,
    "read_paths": 5,
    "interfaces": 10,
    "read_domains": 5,
    "write_domains": 15,
    "authority_claims": 20,
}


class RankingEvidenceError(ValueError):
    """Stable fail-closed error for R154 evidence derivation."""

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
        raise RankingEvidenceError("INVALID_STRING", path)
    return value.strip()


def _nonnegative_int(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RankingEvidenceError("INVALID_NONNEGATIVE_INTEGER", path)
    return value


def _string_set(value: Any, path: str) -> set[str]:
    if value is None:
        return set()
    if not isinstance(value, list):
        raise RankingEvidenceError("INVALID_STRING_LIST", path)
    result: set[str] = set()
    for index, item in enumerate(value):
        result.add(_nonempty(item, f"{path}/{index}"))
    return result


def _interface_key(value: Any, path: str) -> str:
    if isinstance(value, str):
        return _nonempty(value, path)
    if not isinstance(value, Mapping):
        raise RankingEvidenceError("INVALID_INTERFACE", path)
    name = _nonempty(value.get("name"), f"{path}/name")
    mode = value.get("mode")
    if mode is not None:
        mode = _nonempty(mode, f"{path}/mode").lower()
        if mode not in {"read", "write"}:
            raise RankingEvidenceError("INVALID_INTERFACE_MODE", f"{path}/mode")
    frozen = value.get("frozen")
    if frozen is not None and not isinstance(frozen, bool):
        raise RankingEvidenceError("INVALID_INTERFACE_FROZEN", f"{path}/frozen")
    return _canonical({"name": name, "mode": mode, "frozen": frozen})


def _surface_breadth(proposal: Mapping[str, Any]) -> tuple[int, dict[str, int], str]:
    if proposal.get("schema_version") != "TaskReleaseProposal/v1":
        raise RankingEvidenceError("TASK_RELEASE_PROPOSAL_SCHEMA_INVALID", "/proposal/schema_version")
    surface = proposal.get("proposed_write_surface")
    if not isinstance(surface, Mapping):
        raise RankingEvidenceError("PROPOSED_WRITE_SURFACE_REQUIRED", "/proposal/proposed_write_surface")

    allowed = set(CHANGE_SURFACE_WEIGHTS)
    extra = sorted(set(surface) - allowed)
    if extra:
        raise RankingEvidenceError(
            "UNRECOGNIZED_WRITE_SURFACE_FIELD",
            f"/proposal/proposed_write_surface/{extra[0]}",
        )

    counts: dict[str, int] = {}
    for field in ("write_paths", "read_paths", "read_domains", "write_domains", "authority_claims"):
        counts[field] = len(_string_set(surface.get(field, []), f"/proposal/proposed_write_surface/{field}"))

    interfaces = surface.get("interfaces", [])
    if not isinstance(interfaces, list):
        raise RankingEvidenceError("INVALID_INTERFACE_LIST", "/proposal/proposed_write_surface/interfaces")
    interface_keys = {
        _interface_key(item, f"/proposal/proposed_write_surface/interfaces/{index}")
        for index, item in enumerate(interfaces)
    }
    counts["interfaces"] = len(interface_keys)

    raw_score = sum(counts[field] * CHANGE_SURFACE_WEIGHTS[field] for field in CHANGE_SURFACE_WEIGHTS)
    score = min(100, raw_score)
    surface_digest = _digest(
        {
            "counts": counts,
            "weights": CHANGE_SURFACE_WEIGHTS,
            "score": score,
        }
    )
    return score, counts, surface_digest


def derive_trusted_ranking_evidence(
    *,
    signal_ref: str,
    signal_proof_ref: str,
    signal_kind: str,
    materiality_class: str | None,
    origin_ledger_offset: int,
    ledger_watermark: int,
    dependency_ready: bool,
    task_release_proposal: Mapping[str, Any],
    source_evidence_refs: Sequence[str] = (),
) -> dict[str, Any]:
    """Derive one rebuildable ranking evidence object from already-trusted facts.

    R154 does not select or release work.  It only computes the numeric fields
    consumed by the retained R151 rank key.  Unknown value dimensions remain
    neutral instead of being guessed from prose or caller claims.
    """
    signal = _nonempty(signal_ref, "/signal_ref")
    proof = _nonempty(signal_proof_ref, "/signal_proof_ref")
    if not proof.startswith(f"s0c://signal/{signal}#"):
        raise RankingEvidenceError("S0C_SIGNAL_PROOF_BINDING_INVALID", "/signal_proof_ref")
    _nonempty(signal_kind, "/signal_kind")

    origin_offset = _nonnegative_int(origin_ledger_offset, "/origin_ledger_offset")
    watermark = _nonnegative_int(ledger_watermark, "/ledger_watermark")
    if origin_offset <= 0 or watermark <= 0 or origin_offset > watermark:
        raise RankingEvidenceError("S0C_LEDGER_POSITION_INVALID", "/origin_ledger_offset")

    if dependency_ready is not True:
        raise RankingEvidenceError("TRUSTED_DEPENDENCY_READINESS_REQUIRED", "/dependency_ready")

    materiality = "UNKNOWN" if materiality_class is None else _nonempty(materiality_class, "/materiality_class").upper()
    if materiality == "HIGH_RISK":
        raise RankingEvidenceError("HIGH_RISK_SIGNAL_NOT_IDLE_RANKABLE", "/materiality_class")
    if materiality == "UNKNOWN":
        materiality_score = NEUTRAL_MATERIALITY
        materiality_reason = "CANONICAL_MATERIALITY_ABSENT_NEUTRAL"
    elif materiality in SIGNAL_MATERIALITY_SCORES:
        materiality_score = SIGNAL_MATERIALITY_SCORES[materiality]
        materiality_reason = "CANONICAL_SIGNAL_MATERIALITY_MAPPING"
    else:
        raise RankingEvidenceError("CANONICAL_MATERIALITY_UNRECOGNIZED", "/materiality_class")

    age_cycles = min(MAX_AGE_CYCLES, watermark - origin_offset)
    cost_score, surface_counts, surface_digest = _surface_breadth(task_release_proposal)

    evidence_refs = sorted(
        {
            proof,
            *(
                _nonempty(item, f"/source_evidence_refs/{index}")
                for index, item in enumerate(source_evidence_refs)
            ),
        }
    )

    rank_vector = {
        "priority_class": P3,
        "user_value_score": NEUTRAL_USER_VALUE,
        "materiality_score": materiality_score,
        "dependency_readiness_score": 100,
        "age_cycles": age_cycles,
        "estimated_cost_score": cost_score,
    }
    value: dict[str, Any] = {
        "schema_version": RANKING_SCHEMA,
        "policy_version": POLICY_VERSION,
        "signal_ref": signal,
        "source_evidence_refs": evidence_refs,
        "rank_vector": rank_vector,
        "feature_provenance": {
            "priority_class": {
                "source": "R154_POLICY_DEFAULT",
                "reason": "NO_CANONICAL_RESEARCH_PRIORITY_CLASSIFIER_IN_V1",
            },
            "user_value_score": {
                "source": "R154_POLICY_NEUTRAL",
                "reason": "NO_CANONICAL_USER_VALUE_AUTHORITY_IN_V1",
            },
            "materiality_score": {
                "source": "S0C_CANONICAL_SIGNAL_ROUTE",
                "materiality_class": materiality,
                "reason": materiality_reason,
            },
            "dependency_readiness_score": {
                "source": "R153_TRUSTED_OWNER_RECONCILIATION",
                "dependency_ready": True,
            },
            "age_cycles": {
                "source": "S0C_CANONICAL_LEDGER_POSITION",
                "origin_ledger_offset": origin_offset,
                "ledger_watermark": watermark,
                "cap": MAX_AGE_CYCLES,
            },
            "estimated_cost_score": {
                "source": "R149_PROPOSED_CHANGE_SURFACE_BREADTH_PROXY",
                "surface_counts": surface_counts,
                "weights": dict(CHANGE_SURFACE_WEIGHTS),
                "surface_digest": surface_digest,
                "cap": 100,
            },
        },
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
            "grants_merge_authority": False,
        },
    }
    value["ranking_digest"] = _digest(value)
    return value


def ranking_evidence_ref(value: Mapping[str, Any]) -> str:
    if value.get("schema_version") != RANKING_SCHEMA:
        raise RankingEvidenceError("RANKING_EVIDENCE_SCHEMA_INVALID")
    digest = value.get("ranking_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise RankingEvidenceError("RANKING_EVIDENCE_DIGEST_INVALID")
    vector = value.get("rank_vector")
    if not isinstance(vector, Mapping):
        raise RankingEvidenceError("RANK_VECTOR_INVALID")
    return (
        f"r154://ranking/{digest}#policy={POLICY_VERSION};"
        f"priority={vector.get('priority_class')};materiality={vector.get('materiality_score')};"
        f"age={vector.get('age_cycles')};cost={vector.get('estimated_cost_score')}"
    )
