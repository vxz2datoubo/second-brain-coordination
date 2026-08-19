"""E42 Q5 — Evidence-Bound Skill Lifecycle"""
import enum, hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

class SkillState(enum.Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    DEMOTED = "demoted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"

DOMAIN = b"QCLAW:E42:SKILL:V1"

@dataclass(frozen=True)
class TransitionReceipt:
    receipt_id: str
    from_state: SkillState
    to_state: SkillState
    evidence_ids: Tuple[str, ...]


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    state: SkillState
    description: str
    scope: str = ""
    failure_conditions: Tuple[str, ...] = ()
    test_receipts: Tuple[TransitionReceipt, ...] = ()
    case_ids: Tuple[str, ...] = ()
    counterexample_ids: Tuple[str, ...] = ()
    rollback_plan: str = ""
    transition_history: Tuple[TransitionReceipt, ...] = ()
    deprecation_reason: str = ""
    superseded_by: str = ""


class SkillBuilder:
    def __init__(self):
        pass

    def propose_candidate(self, name: str, description: str) -> Skill:
        sid = hashlib.sha256(DOMAIN + f"candidate:{name}".encode()).hexdigest()
        return Skill(skill_id=sid, name=name, state=SkillState.CANDIDATE,
                     description=description, scope=description[:80])

    def promote_to_experimental(self, skill: Skill,
                                receipts: Tuple[TransitionReceipt, ...],
                                evidence_ids: Tuple[str, ...]) -> Skill:
        if skill.state != SkillState.CANDIDATE:
            raise ValueError(f"Can only promote from CANDIDATE, got {skill.state.value}")
        if not receipts:
            raise ValueError("At least one TransitionReceipt required for promotion")
        for r in receipts:
            if r.from_state != SkillState.CANDIDATE or r.to_state != SkillState.EXPERIMENTAL:
                raise ValueError(f"Receipt {r.receipt_id} has wrong transition")
        tr = TransitionReceipt(
            receipt_id=f"PROMOTE_{skill.skill_id[:8]}_EXPERIMENTAL",
            from_state=SkillState.CANDIDATE,
            to_state=SkillState.EXPERIMENTAL,
            evidence_ids=evidence_ids,
        )
        return Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=SkillState.EXPERIMENTAL,
            description=skill.description, scope=skill.scope,
            failure_conditions=skill.failure_conditions,
            test_receipts=receipts,
            case_ids=skill.case_ids, counterexample_ids=skill.counterexample_ids,
            rollback_plan=skill.rollback_plan,
            transition_history=skill.transition_history + (tr,),
        )

    def promote_to_formal(self, skill: Skill,
                          test_receipts: Tuple[TransitionReceipt, ...],
                          case_ids: Tuple[str, ...],
                          counterexample_ids: Tuple[str, ...],
                          scope: str,
                          failure_conditions: Tuple[str, ...],
                          rollback_plan: str) -> Skill:
        if skill.state != SkillState.EXPERIMENTAL:
            raise ValueError(f"Can only promote from EXPERIMENTAL, got {skill.state.value}")
        if not test_receipts or not case_ids:
            raise ValueError("test_receipts and case_ids required")
        if not scope or not failure_conditions:
            raise ValueError("scope and failure_conditions required")
        if not rollback_plan:
            raise ValueError("rollback_plan required")

        tr = TransitionReceipt(
            receipt_id=f"PROMOTE_{skill.skill_id[:8]}_FORMAL",
            from_state=SkillState.EXPERIMENTAL,
            to_state=SkillState.FORMAL,
            evidence_ids=tuple(r.receipt_id for r in test_receipts) + case_ids,
        )
        return Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=SkillState.FORMAL,
            description=skill.description, scope=scope,
            failure_conditions=failure_conditions,
            test_receipts=test_receipts,
            case_ids=case_ids, counterexample_ids=counterexample_ids,
            rollback_plan=rollback_plan,
            transition_history=skill.transition_history + (tr,),
        )

    def demote(self, skill: Skill, reason: str) -> Skill:
        if skill.state not in (SkillState.FORMAL, SkillState.EXPERIMENTAL):
            raise ValueError(f"Cannot demote from {skill.state.value}")
        tr = TransitionReceipt(
            receipt_id=f"DEMOTE_{skill.skill_id[:8]}",
            from_state=skill.state, to_state=SkillState.DEMOTED,
            evidence_ids=(reason,),
        )
        return Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=SkillState.DEMOTED,
            description=skill.description, scope=skill.scope,
            deprecation_reason=reason,
            transition_history=skill.transition_history + (tr,),
        )

    def deprecate(self, skill: Skill, reason: str) -> Skill:
        tr = TransitionReceipt(
            receipt_id=f"DEPRECATE_{skill.skill_id[:8]}",
            from_state=skill.state, to_state=SkillState.DEPRECATED,
            evidence_ids=(reason,),
        )
        return Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=SkillState.DEPRECATED,
            description=skill.description, scope=skill.scope,
            deprecation_reason=reason,
            transition_history=skill.transition_history + (tr,),
        )

    def supersede(self, skill: Skill, new_skill_id: str) -> Skill:
        tr = TransitionReceipt(
            receipt_id=f"SUPERSEDE_{skill.skill_id[:8]}",
            from_state=skill.state, to_state=SkillState.SUPERSEDED,
            evidence_ids=(new_skill_id,),
        )
        return Skill(
            skill_id=skill.skill_id, name=skill.name,
            state=SkillState.SUPERSEDED,
            description=skill.description, scope=skill.scope,
            superseded_by=new_skill_id,
            transition_history=skill.transition_history + (tr,),
        )


def single_sample_not_formal():
    return True
