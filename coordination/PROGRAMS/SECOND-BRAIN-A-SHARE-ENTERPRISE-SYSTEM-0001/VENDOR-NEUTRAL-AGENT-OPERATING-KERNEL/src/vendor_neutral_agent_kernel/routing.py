"""Provider-neutral capability scoring and fail-closed routing."""

from __future__ import annotations

from dataclasses import dataclass

from .canonical import canonical_sha256, seal_contract
from .contracts import (
    CapabilityAvailability,
    CapabilityDescriptor,
    ContractMeta,
    RouteCandidate,
    SideEffectClass,
    ToolRouteDecision,
)


@dataclass(frozen=True)
class CapabilityRequest:
    capability_id: str
    required_semantics: tuple[str, ...]
    maximum_freshness_ms: int | None = None
    maximum_latency_ms: int | None = None
    minimum_quota_remaining: int = 1
    maximum_cost_units: float | None = None
    allowed_side_effects: tuple[SideEffectClass, ...] = (SideEffectClass.READ_ONLY,)

    def __post_init__(self) -> None:
        if type(self.capability_id) is not str or not self.capability_id:
            raise ValueError("CAPABILITY_REQUEST_ID_REQUIRED")
        if len(set(self.required_semantics)) != len(self.required_semantics):
            raise ValueError("CAPABILITY_REQUEST_DUPLICATE_SEMANTIC")
        if self.maximum_freshness_ms is not None and self.maximum_freshness_ms < 0:
            raise ValueError("CAPABILITY_REQUEST_FRESHNESS_INVALID")
        if self.maximum_latency_ms is not None and self.maximum_latency_ms < 0:
            raise ValueError("CAPABILITY_REQUEST_LATENCY_INVALID")
        if self.minimum_quota_remaining < 0:
            raise ValueError("CAPABILITY_REQUEST_QUOTA_INVALID")
        if self.maximum_cost_units is not None and self.maximum_cost_units < 0:
            raise ValueError("CAPABILITY_REQUEST_COST_INVALID")


def _bounded_inverse(value: int | float | None, ceiling: int | float | None) -> float:
    if value is None or ceiling is None:
        return 0.5
    if ceiling == 0:
        return 1.0 if value == 0 else 0.0
    return max(0.0, min(1.0, 1.0 - float(value) / float(ceiling)))


def _candidate(
    request: CapabilityRequest,
    descriptor: CapabilityDescriptor,
) -> RouteCandidate:
    reasons: list[str] = []
    if descriptor.capability_id != request.capability_id:
        reasons.append("CAPABILITY_ID_MISMATCH")
    missing = tuple(sorted(set(request.required_semantics) - set(descriptor.semantics)))
    if missing:
        reasons.append("MISSING_SEMANTICS:" + ",".join(missing))
    if descriptor.availability not in (
        CapabilityAvailability.AVAILABLE,
        CapabilityAvailability.DEGRADED,
    ):
        reasons.append("AVAILABILITY:" + descriptor.availability.value)
    if (
        request.maximum_freshness_ms is not None
        and descriptor.freshness_ms is not None
        and descriptor.freshness_ms > request.maximum_freshness_ms
    ):
        reasons.append("STALE")
    if (
        request.maximum_latency_ms is not None
        and descriptor.latency_ms is not None
        and descriptor.latency_ms > request.maximum_latency_ms
    ):
        reasons.append("LATENCY_EXCEEDED")
    if descriptor.quota_remaining is not None and descriptor.quota_remaining < request.minimum_quota_remaining:
        reasons.append("QUOTA_INSUFFICIENT")
    if request.maximum_cost_units is not None and descriptor.cost_units > request.maximum_cost_units:
        reasons.append("COST_EXCEEDED")
    if descriptor.side_effect_class not in request.allowed_side_effects:
        reasons.append("SIDE_EFFECT_NOT_ALLOWED")

    semantic_fit = (
        len(set(request.required_semantics) & set(descriptor.semantics))
        / max(1, len(request.required_semantics))
    )
    availability_score = {
        CapabilityAvailability.AVAILABLE: 1.0,
        CapabilityAvailability.DEGRADED: 0.6,
        CapabilityAvailability.RATE_LIMITED: 0.2,
        CapabilityAvailability.UNAVAILABLE: 0.0,
        CapabilityAvailability.UNKNOWN: 0.0,
    }[descriptor.availability]
    quota_score = (
        0.5
        if descriptor.quota_remaining is None
        else min(1.0, descriptor.quota_remaining / max(1, request.minimum_quota_remaining))
    )
    side_effect_score = (
        1.0 if descriptor.side_effect_class in request.allowed_side_effects else 0.0
    )
    components = (
        ("authority_fit", descriptor.authority_fit * 0.20),
        ("semantic_fit", semantic_fit * 0.20),
        ("source_quality", descriptor.source_quality * 0.15),
        ("freshness_fit", _bounded_inverse(descriptor.freshness_ms, request.maximum_freshness_ms) * 0.10),
        ("availability", availability_score * 0.10),
        ("reliability", descriptor.reliability * 0.10),
        ("latency_fit", _bounded_inverse(descriptor.latency_ms, request.maximum_latency_ms) * 0.05),
        ("quota_fit", quota_score * 0.04),
        ("cost_fit", _bounded_inverse(descriptor.cost_units, request.maximum_cost_units) * 0.03),
        ("side_effect_fit", side_effect_score * 0.03),
    )
    score = round(sum(value for _name, value in components), 12)
    return RouteCandidate(
        provider_id=descriptor.provider_id,
        capability_id=descriptor.capability_id,
        accepted=not reasons,
        score=score,
        components=components,
        rejection_reasons=tuple(reasons),
    )


def route_capability(
    meta: ContractMeta,
    request: CapabilityRequest,
    descriptors: tuple[CapabilityDescriptor, ...],
) -> ToolRouteDecision:
    if not descriptors:
        raise ValueError("CAPABILITY_DESCRIPTORS_REQUIRED")
    rows = tuple(
        sorted(
            (_candidate(request, item) for item in descriptors),
            key=lambda item: (
                not item.accepted,
                -item.score,
                item.provider_id,
                item.capability_id,
            ),
        )
    )
    accepted = tuple(
        sorted(
            (item for item in rows if item.accepted),
            key=lambda item: (-item.score, item.provider_id, item.capability_id),
        )
    )
    selected = accepted[0] if accepted else None
    fallback_order = tuple(item.provider_id for item in accepted)
    payload = {
        "requested_capability": request.capability_id,
        "required_semantics": request.required_semantics,
        "candidates": rows,
        "selected_provider_id": selected.provider_id if selected else None,
        "selected_capability_id": selected.capability_id if selected else None,
        "fallback_order": fallback_order,
    }
    decision = ToolRouteDecision(
        meta=meta,
        requested_capability=request.capability_id,
        required_semantics=request.required_semantics,
        candidates=rows,
        selected_provider_id=selected.provider_id if selected else None,
        selected_capability_id=selected.capability_id if selected else None,
        fallback_order=fallback_order,
        decision_hash=canonical_sha256(payload),
    )
    return seal_contract(decision)
