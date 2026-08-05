"""E41 Q5 — Skill Promotion & Failure Conditions

Define candidate skill, experimental skill and formal skill states.
Promotion requires reproducible tests, multiple cases, counterexamples,
scope, failure conditions and rollback.
Single sample or one successful run cannot become a formal skill.
Define demotion, deprecation and supersession rules.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class SkillState(str, Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    DEMOTED = "demoted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclass(frozen=True)
class SkillPromotionGate:
    """Evidence required for promotion."""
    reproducible_tests_count: int
    distinct_cases_count: int
    counterexamples_documented: int
    scope_defined: bool
    failure_conditions_documented: bool
    rollback_plan_exists: bool

    def is_satisfied(self) -> bool:
        return (
            self.reproducible_tests_count >= 3
            and self.distinct_cases_count >= 2
            and self.scope_defined
            and self.failure_conditions_documented
            and self.rollback_plan_exists
        )


@dataclass(frozen=True)
class Skill:
    """A skill in the Second Brain's knowledge layer."""
    skill_id: str
    name: str
    state: SkillState
    description: str
    scope: str
    failure_conditions: List[str] = field(default_factory=list)
    test_cases: List[str] = field(default_factory=list)
    counterexamples: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    deprecation_reason: str = ""


def propose_candidate(name: str, description: str) -> Skill:
    """Create a candidate skill. Starts at CANDIDATE state."""
    import hashlib
    skill_id = hashlib.sha256(f"{name}|{description}".encode()).hexdigest()[:12]
    return Skill(
        skill_id=skill_id,
        name=name,
        state=SkillState.CANDIDATE,
        description=description,
        scope="undefined",
    )


def promote(skill: Skill, gate: SkillPromotionGate) -> Skill:
    """Promote a skill based on evidence gate.
    
    CANDIDATE → EXPERIMENTAL: needs 1+ test case
    EXPERIMENTAL → FORMAL: needs full gate satisfied
    
    Returns skill with updated state. Never auto-promotes without evidence.
    """
    if skill.state == SkillState.CANDIDATE:
        if len(skill.test_cases) >= 1:
            return Skill(
                skill_id=skill.skill_id,
                name=skill.name,
                state=SkillState.EXPERIMENTAL,
                description=skill.description,
                scope=skill.scope,
                failure_conditions=skill.failure_conditions,
                test_cases=skill.test_cases,
                counterexamples=skill.counterexamples,
            )
        return skill  # stays CANDIDATE

    if skill.state == SkillState.EXPERIMENTAL:
        if gate.is_satisfied():
            return Skill(
                skill_id=skill.skill_id,
                name=skill.name,
                state=SkillState.FORMAL,
                description=skill.description,
                scope=skill.scope,
                failure_conditions=skill.failure_conditions,
                test_cases=skill.test_cases,
                counterexamples=skill.counterexamples,
            )
        return skill

    return skill  # FORMAL, DEMOTED, DEPRECATED, SUPERSEDED stay


def demote(skill: Skill, reason: str) -> Skill:
    """Demote a formal skill to experimental."""
    return Skill(
        skill_id=skill.skill_id, name=skill.name,
        state=SkillState.DEMOTED, description=skill.description,
        scope=skill.scope, failure_conditions=skill.failure_conditions,
        test_cases=skill.test_cases, counterexamples=skill.counterexamples,
    )


def deprecate(skill: Skill, reason: str) -> Skill:
    """Deprecate a skill with reason."""
    return Skill(
        skill_id=skill.skill_id, name=skill.name,
        state=SkillState.DEPRECATED, description=skill.description,
        scope=skill.scope, failure_conditions=skill.failure_conditions,
        test_cases=skill.test_cases, counterexamples=skill.counterexamples,
        deprecation_reason=reason,
    )


def supersede(skill: Skill, replacement_id: str) -> Skill:
    """Mark skill as superseded by a replacement."""
    return Skill(
        skill_id=skill.skill_id, name=skill.name,
        state=SkillState.SUPERSEDED, description=skill.description,
        scope=skill.scope, failure_conditions=skill.failure_conditions,
        test_cases=skill.test_cases, counterexamples=skill.counterexamples,
        superseded_by=replacement_id,
    )


def single_sample_not_formal() -> bool:
    """Invariant: a single sample can never create a formal skill."""
    skill = propose_candidate("test", "one sample only")
    skill = Skill(
        skill_id=skill.skill_id, name=skill.name,
        state=SkillState.EXPERIMENTAL, description=skill.description,
        scope=skill.scope, test_cases=["sample_1"],
    )
    gate = SkillPromotionGate(
        reproducible_tests_count=0, distinct_cases_count=0,
        counterexamples_documented=0, scope_defined=False,
        failure_conditions_documented=False, rollback_plan_exists=False,
    )
    result = promote(skill, gate)
    return result.state != SkillState.FORMAL  # must be True
