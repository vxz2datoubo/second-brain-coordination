from __future__ import annotations

from dataclasses import replace

from vendor_neutral_agent_kernel.canonical import seal_contract
from vendor_neutral_agent_kernel.contracts import (
    CapabilityAvailability,
    CapabilityDescriptor,
    ContractMeta,
    EpistemicClaim,
    EpistemicLane,
    QualityStatus,
    SideEffectClass,
)


def meta(
    object_id: str,
    *,
    lane: EpistemicLane = EpistemicLane.UNKNOWN,
) -> ContractMeta:
    return ContractMeta(
        schema_version="1.0",
        object_id=object_id,
        run_id="run-test",
        trace_id="trace-test",
        created_at="2026-07-30T09:00:00+08:00",
        source_refs=("fixture:public",),
        epistemic_status=lane,
        authority_class="CANDIDATE_ONLY",
        quality_status=QualityStatus.CANDIDATE,
    )


def claim(
    object_id: str = "claim-1",
    *,
    lane: EpistemicLane = EpistemicLane.USER_ASSERTED,
    statement: str = "The user selected the candidate approach.",
) -> EpistemicClaim:
    supporting = ("evidence:1",) if lane in (EpistemicLane.INFERRED, EpistemicLane.HYPOTHESIS) else ()
    confidence = 0.0 if lane is EpistemicLane.UNKNOWN else 0.8
    value = EpistemicClaim(
        meta=meta(object_id, lane=lane),
        canonical_statement=statement,
        provenance_lane=lane,
        supporting_evidence=supporting,
        opposing_evidence=(),
        alternative_explanations=(),
        confidence=confidence,
        confidence_basis="synthetic fixture",
        freshness="CURRENT",
        invalidation_conditions=("user correction",),
    )
    return seal_contract(value)


def capability(
    provider_id: str,
    *,
    display_name: str | None = None,
    semantics: tuple[str, ...] = ("snapshot", "source_time"),
    quality: float = 0.9,
    authority: float = 0.9,
    freshness_ms: int | None = 100,
    reliability: float = 0.9,
    latency_ms: int | None = 50,
    quota: int | None = 100,
    cost: float = 1.0,
    side_effect: SideEffectClass = SideEffectClass.READ_ONLY,
    availability: CapabilityAvailability = CapabilityAvailability.AVAILABLE,
) -> CapabilityDescriptor:
    value = CapabilityDescriptor(
        meta=meta("capability-" + provider_id),
        provider_id=provider_id,
        provider_display_name=display_name or provider_id,
        capability_id="market.snapshot",
        semantics=semantics,
        field_semantics_version="1.0",
        source_quality=quality,
        authority_fit=authority,
        freshness_ms=freshness_ms,
        reliability=reliability,
        latency_ms=latency_ms,
        quota_remaining=quota,
        cost_units=cost,
        side_effect_class=side_effect,
        availability=availability,
    )
    return seal_contract(value)


def with_display_name(
    descriptor: CapabilityDescriptor,
    display_name: str,
) -> CapabilityDescriptor:
    return replace(
        descriptor,
        meta=replace(descriptor.meta, content_hash=""),
        provider_display_name=display_name,
    )
