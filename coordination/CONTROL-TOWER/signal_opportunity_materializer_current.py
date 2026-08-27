from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from idle_signal_scheduler import P3, validate_opportunity
from signal_opportunity_materializer import (
    _decision,
    materialize_signal_opportunity as _materialize_r153,
)
from signal_priority_classification import (
    PriorityClassificationError,
    derive_trusted_priority_evidence,
    priority_evidence_ref,
)
from signal_user_value import (
    ExplicitUserValueError,
    explicit_user_value_ref,
    observe_explicit_user_value,
)


UPGRADE_SCHEMA = "ExplicitUserValueRankingUpgrade/v1"
POLICY_VERSION = "R155/v1"
R154_RANKING_PREFIX = "r154://ranking/"
R155_RANKING_UPGRADE_PREFIX = "r155://ranking-upgrade/"
R154_NEUTRAL_USER_VALUE = 50


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


def _owner_binding_stub(base: Mapping[str, Any]) -> Mapping[str, Any] | None:
    binding_digest = base.get("owner_binding_digest")
    if isinstance(binding_digest, str) and binding_digest:
        return {"valid": True, "binding_digest": binding_digest}
    return None


def _upgrade_ref(
    *,
    base_opportunity_digest: str,
    user_value_evidence_digest: str,
    user_value_score: int,
) -> str:
    payload = {
        "schema_version": UPGRADE_SCHEMA,
        "policy_version": POLICY_VERSION,
        "base_opportunity_digest": base_opportunity_digest,
        "user_value_evidence_digest": user_value_evidence_digest,
        "user_value_score": user_value_score,
        "authority_boundary": {
            "selects_opportunity": False,
            "releases_task": False,
            "grants_execution_authority": False,
            "grants_domain_write": False,
            "grants_merge_authority": False,
        },
    }
    digest = _digest(payload)
    return (
        f"r155://ranking-upgrade/{digest}#policy={POLICY_VERSION};"
        f"base={base_opportunity_digest};user_value={user_value_score}"
    )


def materialize_signal_opportunity(
    repo_root: str | Path,
    ledger: Any,
    draft_value: Mapping[str, Any],
    *,
    expected_coordinator_main: str,
    domain_authority_descriptors: Sequence[Mapping[str, Any]],
    domain_authority_observations: Sequence[Mapping[str, Any]],
    authority_exact_read_proofs: Sequence[Any] = (),
    authority_live_observation_proof: Any = None,
    owner_observer: Any = None,
) -> dict[str, Any]:
    """Current materializer: R153 + R154 + R155 + bounded R156 evidence.

    R153 remains responsible for S0C replay, owner reconciliation and R150/R149.
    R155 may alter only R154's neutral user-value feature using the sealed explicit
    user declaration path. R156 then classifies P3/P4 only from the canonical
    epistemic state already replay-proven by R153. Neither successor selects or
    releases work; retained R151 remains the sole selector/release authority.
    """
    base = _materialize_r153(
        repo_root,
        ledger,
        draft_value,
        expected_coordinator_main=expected_coordinator_main,
        domain_authority_descriptors=domain_authority_descriptors,
        domain_authority_observations=domain_authority_observations,
        authority_exact_read_proofs=authority_exact_read_proofs,
        authority_live_observation_proof=authority_live_observation_proof,
        owner_observer=owner_observer,
    )
    if base.get("disposition") != "MATERIALIZED_FOR_R151":
        return base

    signal_ref = str(base.get("signal_ref") or draft_value.get("signal_ref") or "")
    opportunity_raw = base.get("opportunity")
    if not isinstance(opportunity_raw, Mapping):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_BASE_OPPORTUNITY_MISSING",
            evidence_refs=list(base.get("evidence_refs", [])),
            owner_binding=_owner_binding_stub(base),
        )

    supplied_base_digest = opportunity_raw.get("opportunity_digest")
    if not isinstance(supplied_base_digest, str) or len(supplied_base_digest) != 64:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_BASE_OPPORTUNITY_DIGEST_INVALID",
            evidence_refs=list(base.get("evidence_refs", [])),
            owner_binding=_owner_binding_stub(base),
        )

    opportunity_input = dict(opportunity_raw)
    opportunity_input.pop("opportunity_digest", None)
    try:
        opportunity = validate_opportunity(opportunity_input)
    except Exception as exc:
        code = getattr(exc, "code", "R155_BASE_OPPORTUNITY_INVALID")
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R155_BASE_OPPORTUNITY_INVALID:{code}",
            evidence_refs=list(base.get("evidence_refs", [])),
            owner_binding=_owner_binding_stub(base),
        )
    if opportunity.get("opportunity_digest") != supplied_base_digest:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_BASE_OPPORTUNITY_DIGEST_MISMATCH",
            evidence_refs=list(opportunity.get("source_evidence_refs", [])),
            owner_binding=_owner_binding_stub(base),
        )

    evidence_refs = list(opportunity.get("source_evidence_refs", []))
    if not any(ref.startswith(R154_RANKING_PREFIX) for ref in evidence_refs):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_R154_RANKING_EVIDENCE_REQUIRED",
            evidence_refs=evidence_refs,
            owner_binding=_owner_binding_stub(base),
        )
    if opportunity.get("user_value_score") != R154_NEUTRAL_USER_VALUE:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_BASE_USER_VALUE_NOT_NEUTRAL",
            evidence_refs=evidence_refs,
            owner_binding=_owner_binding_stub(base),
        )

    try:
        user_value = observe_explicit_user_value(repo_root, signal_ref)
        user_value_ref = explicit_user_value_ref(user_value)
    except ExplicitUserValueError as exc:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R155_USER_VALUE_FAILED:{exc.code}",
            evidence_refs=evidence_refs,
            owner_binding=_owner_binding_stub(base),
        )

    score = user_value.get("user_value_score")
    digest = user_value.get("evidence_digest")
    if (
        isinstance(score, bool)
        or not isinstance(score, int)
        or not 0 <= score <= 100
        or not isinstance(digest, str)
        or len(digest) != 64
    ):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R155_USER_VALUE_EVIDENCE_INVALID",
            evidence_refs=evidence_refs,
            owner_binding=_owner_binding_stub(base),
        )

    upgrade_ref = _upgrade_ref(
        base_opportunity_digest=supplied_base_digest,
        user_value_evidence_digest=digest,
        user_value_score=score,
    )

    upgraded = dict(opportunity)
    upgraded.pop("opportunity_digest", None)
    upgraded["user_value_score"] = score
    upgraded["source_evidence_refs"] = sorted(
        set(evidence_refs)
        | set(map(str, user_value.get("source_evidence_refs", [])))
        | {user_value_ref, upgrade_ref}
    )
    try:
        upgraded = validate_opportunity(upgraded)
    except Exception as exc:
        code = getattr(exc, "code", "R155_UPGRADED_OPPORTUNITY_INVALID")
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R155_UPGRADED_OPPORTUNITY_INVALID:{code}",
            evidence_refs=upgraded.get("source_evidence_refs", evidence_refs),
            owner_binding=_owner_binding_stub(base),
        )

    r155_refs = list(upgraded.get("source_evidence_refs", []))
    r155_digest = upgraded.get("opportunity_digest")
    if upgraded.get("priority_class") != P3:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R156_BASE_PRIORITY_NOT_R154_P3",
            evidence_refs=r155_refs,
            owner_binding=_owner_binding_stub(base),
        )
    if not any(ref.startswith(R155_RANKING_UPGRADE_PREFIX) for ref in r155_refs):
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R156_R155_RANKING_UPGRADE_EVIDENCE_REQUIRED",
            evidence_refs=r155_refs,
            owner_binding=_owner_binding_stub(base),
        )
    if not isinstance(r155_digest, str) or len(r155_digest) != 64:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason="R156_R155_OPPORTUNITY_DIGEST_INVALID",
            evidence_refs=r155_refs,
            owner_binding=_owner_binding_stub(base),
        )

    try:
        priority_evidence = derive_trusted_priority_evidence(
            signal_ref=signal_ref,
            epistemic_state=str(upgraded.get("epistemic_state") or ""),
            base_opportunity_digest=r155_digest,
            source_evidence_refs=r155_refs,
        )
        priority_ref = priority_evidence_ref(priority_evidence)
    except PriorityClassificationError as exc:
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R156_PRIORITY_CLASSIFICATION_FAILED:{exc.code}",
            evidence_refs=r155_refs,
            owner_binding=_owner_binding_stub(base),
        )

    final = dict(upgraded)
    final.pop("opportunity_digest", None)
    final["priority_class"] = priority_evidence["priority_class"]
    final["source_evidence_refs"] = sorted(set(r155_refs) | {priority_ref})
    try:
        final = validate_opportunity(final)
    except Exception as exc:
        code = getattr(exc, "code", "R156_UPGRADED_OPPORTUNITY_INVALID")
        return _decision(
            signal_ref=signal_ref,
            disposition="NEEDS_REVALIDATION",
            reason=f"R156_UPGRADED_OPPORTUNITY_INVALID:{code}",
            evidence_refs=final.get("source_evidence_refs", r155_refs),
            owner_binding=_owner_binding_stub(base),
        )

    return _decision(
        signal_ref=signal_ref,
        disposition="MATERIALIZED_FOR_R151",
        reason="R153_R154_R155_R156_TRUSTED_PRIORITY_BOUND",
        evidence_refs=final["source_evidence_refs"],
        owner_binding=_owner_binding_stub(base),
        opportunity=final,
    )
