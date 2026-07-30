"""Checkpoint and idempotent recovery helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .canonical import seal_contract
from .contracts import ContractMeta, ExecutionCheckpoint, SideEffectRecord


@dataclass(frozen=True)
class ResumeDecision:
    status: str
    already_completed: tuple[str, ...]
    next_steps: tuple[str, ...]
    protected_idempotency_keys: tuple[str, ...]
    findings: tuple[str, ...]


def build_checkpoint(
    meta: ContractMeta,
    *,
    intent_hash: str,
    context_hash: str,
    authority_hash: str,
    completed_steps: tuple[str, ...],
    remaining_steps: tuple[str, ...],
    artifact_refs: tuple[str, ...] = (),
    side_effect_ledger: tuple[SideEffectRecord, ...] = (),
    test_state: tuple[str, ...] = (),
    resume_instructions: tuple[str, ...] = (),
    external_anchors: tuple[str, ...] = (),
) -> ExecutionCheckpoint:
    checkpoint = ExecutionCheckpoint(
        meta=meta,
        intent_hash=intent_hash,
        context_hash=context_hash,
        authority_hash=authority_hash,
        completed_steps=completed_steps,
        remaining_steps=remaining_steps,
        artifact_refs=artifact_refs,
        side_effect_ledger=side_effect_ledger,
        test_state=test_state,
        resume_instructions=resume_instructions,
        external_anchors=external_anchors,
    )
    return seal_contract(checkpoint)


def record_side_effect(
    checkpoint: ExecutionCheckpoint,
    *,
    meta: ContractMeta,
    effect: SideEffectRecord,
) -> ExecutionCheckpoint:
    if effect.idempotency_key in {
        item.idempotency_key for item in checkpoint.side_effect_ledger
    }:
        raise ValueError("DUPLICATE_SIDE_EFFECT_IDEMPOTENCY_KEY")
    updated = replace(
        checkpoint,
        meta=meta,
        side_effect_ledger=checkpoint.side_effect_ledger + (effect,),
    )
    return seal_contract(updated)


def resume_checkpoint(
    checkpoint: ExecutionCheckpoint,
    *,
    current_authority_hash: str,
    observed_external_anchors: tuple[str, ...],
) -> ResumeDecision:
    findings: list[str] = []
    blocking_states: list[str] = []
    if current_authority_hash != checkpoint.authority_hash:
        blocking_states.append("REVALIDATE_AUTHORITY")
        findings.append("AUTHORITY_CHANGED")
    missing_anchors = tuple(
        anchor
        for anchor in checkpoint.external_anchors
        if anchor not in observed_external_anchors
    )
    if missing_anchors:
        blocking_states.append("EXTERNAL_DRIFT")
        findings.append("MISSING_EXTERNAL_ANCHORS:" + ",".join(missing_anchors))
    status = "READY" if not blocking_states else "_AND_".join(blocking_states)
    return ResumeDecision(
        status=status,
        already_completed=checkpoint.completed_steps,
        next_steps=checkpoint.remaining_steps,
        protected_idempotency_keys=tuple(
            item.idempotency_key for item in checkpoint.side_effect_ledger
        ),
        findings=tuple(findings),
    )
