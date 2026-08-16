"""E39 pre-canary readiness proof without approval consumption.

This module composes E38's sealed public route proof into a pre-canary
readiness decision.  It deliberately has no API for fetching comments,
creating approvals, dispatching canaries, invoking Codex CLI, or performing
automation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .models import RouteRef, ValidationError, parse_rfc3339_utc, require_identifier
from .proofs import (
    ApprovalVerificationResult,
    ReadOnlyRouteProofVerifier,
    RouteProofVerification,
    VerificationStatus,
)


E39_TASK_ID = "CODEX-BRAINOPS-LIVE-ROUTE-ACTOR-POLICY-AND-PRE-CANARY-READINESS-PROOF-0034-E39"
E39_ROUTE_EPOCH = 40
E39_ROUTE = RouteRef("brainops.e39", "CODEX", E39_ROUTE_EPOCH)
E39_COMPLETION_SIGNAL = "CODEX_BRAINOPS_E39_LIVE_ROUTE_ACTOR_POLICY_PRE_CANARY_READINESS_READY_FOR_GPT_REVIEW"
E39_EXPECTED_AUTHORIZED_ACTORS = ("vxz2datoubo",)


class PreCanaryReadinessCode(str, Enum):
    ROUTE_AUTHORITY_UNVERIFIED = "ROUTE_AUTHORITY_UNVERIFIED"
    ROUTE_ACTOR_POLICY_MISMATCH = "ROUTE_ACTOR_POLICY_MISMATCH"
    APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED = "APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED"
    APPROVAL_PRESENT_BUT_CANARY_STILL_DISABLED = "APPROVAL_PRESENT_BUT_CANARY_STILL_DISABLED"


@dataclass(frozen=True)
class PreCanaryReadinessProof:
    route: RouteRef
    checked_at: str
    result_code: PreCanaryReadinessCode
    route_proof_status: VerificationStatus
    route_reason_code: str
    main_commit_sha1: str | None
    main_tree_sha1: str | None
    active_task_blob_sha1: str | None
    active_task_content_sha256: str | None
    coordination_blob_sha1: str | None
    coordination_content_sha256: str | None
    authorized_approval_actors: tuple[str, ...]
    approval_supplied: bool
    automatic_dispatch_allowed: bool
    canary_execution_allowed: bool
    canary_executed: bool = False
    trust_boundary: str = (
        "Python process is the trusted execution boundary; underscore names and sealed constructors "
        "are API integrity controls, not cryptographic isolation from hostile same-process code."
    )

    def __post_init__(self) -> None:
        parse_rfc3339_utc(self.checked_at, "pre-canary readiness checked_at")
        require_identifier(self.route.route_id, "pre-canary route id")
        require_identifier(self.route.target_agent, "pre-canary target agent")
        require_identifier(self.route_reason_code, "pre-canary route reason")
        if self.canary_executed:
            raise ValidationError("E39 never executes a canary")
        if self.automatic_dispatch_allowed or self.canary_execution_allowed:
            raise ValidationError("E39 pre-canary readiness must keep execution switches disabled")


class LiveRoutePreCanaryReadinessObserver:
    """Observe route authority and return a fail-closed pre-canary result."""

    def __init__(self, *, expected_actors: tuple[str, ...] = E39_EXPECTED_AUTHORIZED_ACTORS) -> None:
        if not expected_actors:
            raise ValidationError("expected actors must not be empty")
        for actor in expected_actors:
            require_identifier(actor, "expected authorized actor")
        self._expected_actors = expected_actors
        self._route_verifier = ReadOnlyRouteProofVerifier()

    def observe_snapshot(self, snapshot: object, checked_at: str) -> PreCanaryReadinessProof:
        route_proof = self._route_verifier.verify(E39_ROUTE, E39_TASK_ID, snapshot, checked_at)  # type: ignore[arg-type]
        return self.evaluate(route_proof, checked_at, approval_verification=None)

    def evaluate(
        self,
        route_proof: RouteProofVerification,
        checked_at: str,
        *,
        approval_verification: ApprovalVerificationResult | None = None,
    ) -> PreCanaryReadinessProof:
        parse_rfc3339_utc(checked_at, "pre-canary readiness checked_at")
        if route_proof.status is not VerificationStatus.READ_ONLY_FETCH_VERIFIED or route_proof.evidence is None:
            return self._proof(
                checked_at,
                PreCanaryReadinessCode.ROUTE_AUTHORITY_UNVERIFIED,
                route_proof,
                (),
                approval_verification is not None,
            )
        if route_proof.evidence.route != E39_ROUTE:
            return self._proof(
                checked_at,
                PreCanaryReadinessCode.ROUTE_AUTHORITY_UNVERIFIED,
                route_proof,
                route_proof.evidence.authority.authorized_approval_actors,
                approval_verification is not None,
            )
        authority = route_proof.evidence.authority
        if authority.authorized_approval_actors != self._expected_actors:
            return self._proof(
                checked_at,
                PreCanaryReadinessCode.ROUTE_ACTOR_POLICY_MISMATCH,
                route_proof,
                authority.authorized_approval_actors,
                approval_verification is not None,
            )
        if approval_verification is None:
            return self._proof(
                checked_at,
                PreCanaryReadinessCode.APPROVAL_NOT_SUPPLIED_CANARY_BLOCKED,
                route_proof,
                authority.authorized_approval_actors,
                False,
            )
        return self._proof(
            checked_at,
            PreCanaryReadinessCode.APPROVAL_PRESENT_BUT_CANARY_STILL_DISABLED,
            route_proof,
            authority.authorized_approval_actors,
            True,
        )

    @staticmethod
    def _proof(
        checked_at: str,
        result_code: PreCanaryReadinessCode,
        route_proof: RouteProofVerification,
        actors: tuple[str, ...],
        approval_supplied: bool,
    ) -> PreCanaryReadinessProof:
        evidence = route_proof.evidence
        return PreCanaryReadinessProof(
            route=E39_ROUTE,
            checked_at=checked_at,
            result_code=result_code,
            route_proof_status=route_proof.status,
            route_reason_code=route_proof.reason_code,
            main_commit_sha1=evidence.main_commit_sha1 if evidence else None,
            main_tree_sha1=evidence.main_tree_sha1 if evidence else None,
            active_task_blob_sha1=evidence.active_task.blob_sha1 if evidence else None,
            active_task_content_sha256=evidence.active_task.content_sha256 if evidence else None,
            coordination_blob_sha1=evidence.coordination.blob_sha1 if evidence else None,
            coordination_content_sha256=evidence.coordination.content_sha256 if evidence else None,
            authorized_approval_actors=actors,
            approval_supplied=approval_supplied,
            automatic_dispatch_allowed=False,
            canary_execution_allowed=False,
        )
