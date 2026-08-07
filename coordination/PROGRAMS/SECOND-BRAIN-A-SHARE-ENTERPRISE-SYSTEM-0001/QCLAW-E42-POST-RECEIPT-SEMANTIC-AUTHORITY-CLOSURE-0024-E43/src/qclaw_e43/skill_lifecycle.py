"""E43 Q5 — Evidence-Bound Skill Lifecycle

Skills, TransitionReceipts and promotion gates are factory-issued.
Separate evidence thresholds for candidate→experimental and experimental→formal.
Direct FORMAL/EXPERIMENTAL construction is non-authoritative.
"""
from __future__ import annotations

import hashlib, hmac, enum, dataclasses, time
from typing import Dict, List, Optional, Tuple

__all__ = ["SkillState", "Skill", "TransitionReceipt", "SkillFactory", "SkillPromotionGate"]

class SkillState(enum.Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    DEMOTED = "demoted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclasses.dataclass(frozen=True)
class TransitionReceipt:
    receipt_id: str
    from_state: SkillState
    to_state: SkillState
    evidence_record_ids: Tuple[str, ...]  # must be in AuthorityRegistry
    test_run_id: str  # reproducible test identifier
    case_count: int
    counterexample_count: int
    scope_definition: str
    failure_conditions: Tuple[str, ...]
    rollback_defined: bool
    timestamp_ns: int

    @staticmethod
    def compute_receipt_id(skill_id: str, from_state: SkillState, to_state: SkillState,
                           test_run_id: str, timestamp_ns: int) -> str:
        h = hashlib.sha256()
        h.update(f"{skill_id}|{from_state.value}|{to_state.value}|{test_run_id}|{timestamp_ns}".encode())
        return h.hexdigest()[:32]


@dataclasses.dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    state: SkillState
    description: str
    transitions: Tuple[TransitionReceipt, ...]
    created_ns: int
    factory_signature: bytes


class SkillPromotionGate:
    """Encodes evidence thresholds for each promotion step."""

    @staticmethod
    def can_promote_to_experimental(receipt: TransitionReceipt) -> bool:
        return (
            receipt.from_state == SkillState.CANDIDATE
            and receipt.to_state == SkillState.EXPERIMENTAL
            and receipt.case_count >= 3
            and receipt.counterexample_count == 0
            and len(receipt.evidence_record_ids) >= 2
            and receipt.rollback_defined
            and bool(receipt.scope_definition)
        )

    @staticmethod
    def can_promote_to_formal(receipt: TransitionReceipt) -> bool:
        return (
            receipt.from_state == SkillState.EXPERIMENTAL
            and receipt.to_state == SkillState.FORMAL
            and receipt.case_count >= 5
            and receipt.counterexample_count == 0
            and len(receipt.evidence_record_ids) >= 3
            and receipt.rollback_defined
            and len(receipt.failure_conditions) >= 2
        )

    @staticmethod
    def single_sample_not_formal(receipt: TransitionReceipt) -> bool:
        """Single sample cannot become formal. False = gate blocks."""
        return receipt.case_count >= 2


class SkillFactory:
    """Only path to create Skills and TransitionReceipts."""

    def __init__(self, secret_key: bytes):
        self._key = bytes(secret_key)
        self._skills: Dict[str, Skill] = {}
        self._receipts: Dict[str, TransitionReceipt] = {}

    def create_skill(self, name: str, description: str) -> Skill:
        sid = hashlib.sha256(f"{name}|{description}|{time.time_ns()}".encode()).hexdigest()[:32]
        payload = f"{sid}|{name}|{SkillState.CANDIDATE.value}"
        sig = hmac.digest(self._key, payload.encode(), "sha256")
        skill = Skill(skill_id=sid, name=name, state=SkillState.CANDIDATE,
                       description=description, transitions=(),
                       created_ns=time.time_ns(), factory_signature=sig)
        self._skills[sid] = skill
        return skill

    def promote(self, skill: Skill, to_state: SkillState,
                evidence_ids: Tuple[str, ...], test_run_id: str,
                case_count: int, counterexample_count: int,
                scope: str, failure_conditions: Tuple[str, ...],
                rollback: bool) -> Skill:
        if skill.skill_id not in self._skills:
            raise ValueError("REGISTRY_REJECTED: skill not in factory")
        ts = time.time_ns()
        rid = TransitionReceipt.compute_receipt_id(skill.skill_id, skill.state, to_state, test_run_id, ts)
        receipt = TransitionReceipt(
            receipt_id=rid, from_state=skill.state, to_state=to_state,
            evidence_record_ids=evidence_ids, test_run_id=test_run_id,
            case_count=case_count, counterexample_count=counterexample_count,
            scope_definition=scope, failure_conditions=failure_conditions,
            rollback_defined=rollback, timestamp_ns=ts)

        # Gate check
        gate = SkillPromotionGate()
        if to_state == SkillState.EXPERIMENTAL:
            if not gate.can_promote_to_experimental(receipt):
                raise ValueError(f"PROMOTION_REJECTED: gate not satisfied for candidate→experimental")
        elif to_state == SkillState.FORMAL:
            if not gate.can_promote_to_formal(receipt):
                raise ValueError(f"PROMOTION_REJECTED: gate not satisfied for experimental→formal")

        self._receipts[rid] = receipt
        payload = f"{skill.skill_id}|{skill.name}|{to_state.value}"
        sig = hmac.digest(self._key, payload.encode(), "sha256")
        new_skill = Skill(skill_id=skill.skill_id, name=skill.name, state=to_state,
                          description=skill.description,
                          transitions=skill.transitions + (receipt,),
                          created_ns=skill.created_ns, factory_signature=sig)
        self._skills[skill.skill_id] = new_skill
        return new_skill

    def demote(self, skill: Skill, reason_evidence_id: str) -> Skill:
        payload = f"{skill.skill_id}|{skill.name}|{SkillState.DEMOTED.value}"
        sig = hmac.digest(self._key, payload.encode(), "sha256")
        new_skill = Skill(skill_id=skill.skill_id, name=skill.name, state=SkillState.DEMOTED,
                          description=skill.description, transitions=skill.transitions,
                          created_ns=skill.created_ns, factory_signature=sig)
        self._skills[skill.skill_id] = new_skill
        return new_skill

    def verify(self, skill: Skill) -> bool:
        if skill.skill_id not in self._skills:
            return False
        payload = f"{skill.skill_id}|{skill.name}|{skill.state.value}"
        expected = hmac.digest(self._key, payload.encode(), "sha256")
        return hmac.compare_digest(expected, skill.factory_signature)
