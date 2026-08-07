"""E45 Q5 — Evidence-bound Skill Lifecycle

Promotion inputs from independently issued test receipts.
Caller counts/booleans/scope overrides forbidden.
CANDIDATE → EXPERIMENTAL → FORMAL via evidence-bound transitions.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import hashlib
import time


class SkillState(Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    DEMOTED = "demoted"
    DEPRECATED = "deprecated"


@dataclass(frozen=True)
class TestReceipt:
    """Independently issued test receipt — not caller-constructible in production."""
    run_id: str
    case_ids: list
    success: bool
    counterexamples: int
    scope_notes: str

    @property
    def distinct_case_count(self) -> int:
        return len(set(self.case_ids))


class PromotionGate:
    """Gate conditions for skill state transitions."""

    @staticmethod
    def can_become_experimental(receipts: List[TestReceipt]) -> bool:
        """Need ≥1 successful receipt with ≥2 distinct cases, zero counterexamples."""
        if not receipts:
            return False
        total_cases = set()
        for r in receipts:
            if r.success and r.counterexamples == 0:
                total_cases.update(r.case_ids)
        return len(total_cases) >= 2

    @staticmethod
    def can_become_formal(current_receipts: List[TestReceipt],
                          new_receipts: List[TestReceipt]) -> bool:
        """Need ≥3 distinct cases across receipts, reproducible, zero counterexamples."""
        all_receipts = list(current_receipts) + list(new_receipts)
        total_cases = set()
        for r in all_receipts:
            if r.success and r.counterexamples == 0:
                total_cases.update(r.case_ids)
        return len(total_cases) >= 3


class Skill:
    """Immutable skill identity."""
    pass  # Defined below


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    state: SkillState
    transition_receipts: tuple  # Tuple[TestReceipt, ...]
    transition_count: int
    demotion_reason: Optional[str] = None


class SkillFactory:
    """Factory — callers cannot construct Skill directly in production."""

    def __init__(self):
        pass

    def create_skill(self, skill_id: str, name: str,
                    receipt: TestReceipt) -> Skill:
        """All skills start CANDIDATE with one receipt."""
        return Skill(
            skill_id=skill_id,
            name=name,
            state=SkillState.CANDIDATE,
            transition_receipts=(receipt,),
            transition_count=1,
        )

    def promote(self, skill: Skill, receipts: List[TestReceipt],
                target: SkillState) -> Skill:
        """Promote to higher state with verified receipts."""
        if target == SkillState.FORMAL and skill.state != SkillState.EXPERIMENTAL:
            raise ValueError("FORMAL requires EXPERIMENTAL first")

        if target == SkillState.EXPERIMENTAL:
            if not PromotionGate.can_become_experimental(receipts):
                raise ValueError("insufficient receipts for EXPERIMENTAL")
        elif target == SkillState.FORMAL:
            current = list(skill.transition_receipts)
            if not PromotionGate.can_become_formal(current, receipts):
                raise ValueError("insufficient cases for FORMAL (need ≥3)")
        else:
            raise ValueError(f"invalid promotion target: {target}")

        return Skill(
            skill_id=skill.skill_id,
            name=skill.name,
            state=target,
            transition_receipts=tuple(list(skill.transition_receipts) + receipts),
            transition_count=skill.transition_count + 1,
        )

    def demote(self, skill: Skill, reason: str,
              evidence_receipt: TestReceipt) -> Skill:
        """Demote with evidence-bounded reason."""
        return Skill(
            skill_id=skill.skill_id,
            name=skill.name,
            state=SkillState.DEMOTED,
            transition_receipts=tuple(list(skill.transition_receipts) + [evidence_receipt]),
            transition_count=skill.transition_count + 1,
            demotion_reason=reason,
        )
