"""Typed provenance and candidate-only memory write helpers."""

from __future__ import annotations

from dataclasses import replace

from .canonical import canonical_sha256, seal_contract
from .contracts import (
    ContractMeta,
    EpistemicClaim,
    EpistemicLane,
    MemoryWriteProposal,
    QualityStatus,
)


def revise_claim(
    original: EpistemicClaim,
    *,
    meta: ContractMeta,
    canonical_statement: str,
    provenance_lane: EpistemicLane,
    supporting_evidence: tuple[str, ...],
    opposing_evidence: tuple[str, ...],
    alternative_explanations: tuple[str, ...],
    confidence: float,
    confidence_basis: str,
    freshness: str,
    invalidation_conditions: tuple[str, ...],
    review_after: str | None = None,
    quality_status: QualityStatus = QualityStatus.CANDIDATE,
) -> EpistemicClaim:
    if meta.object_id == original.meta.object_id:
        raise ValueError("CLAIM_REVISION_REQUIRES_NEW_OBJECT_ID")
    revised_meta = replace(
        meta,
        supersedes=original.meta.object_id,
        quality_status=quality_status,
        content_hash="",
    )
    claim = EpistemicClaim(
        meta=revised_meta,
        canonical_statement=canonical_statement,
        provenance_lane=provenance_lane,
        supporting_evidence=supporting_evidence,
        opposing_evidence=opposing_evidence,
        alternative_explanations=alternative_explanations,
        confidence=confidence,
        confidence_basis=confidence_basis,
        freshness=freshness,
        invalidation_conditions=invalidation_conditions,
        review_after=review_after,
    )
    return seal_contract(claim)


def propose_memory_write(
    meta: ContractMeta,
    *,
    candidate_claims: tuple[EpistemicClaim, ...],
    destination_scope: str,
    source_provenance: tuple[str, ...],
    validation_status: str = "CANDIDATE",
) -> MemoryWriteProposal:
    key = canonical_sha256(
        {
            "destination_scope": destination_scope,
            "claims": tuple(claim.meta.content_hash for claim in candidate_claims),
            "source_provenance": source_provenance,
            "validation_status": validation_status,
        }
    )
    proposal = MemoryWriteProposal(
        meta=meta,
        candidate_claims=candidate_claims,
        destination_scope=destination_scope,
        source_provenance=source_provenance,
        validation_status=validation_status,
        authority_write=False,
        idempotency_key=key,
    )
    return seal_contract(proposal)


def reject_authority_promotion(_proposal: MemoryWriteProposal) -> None:
    raise PermissionError("KERNEL_MEMORY_PROPOSAL_CANNOT_PROMOTE_CANONICAL_AUTHORITY")
