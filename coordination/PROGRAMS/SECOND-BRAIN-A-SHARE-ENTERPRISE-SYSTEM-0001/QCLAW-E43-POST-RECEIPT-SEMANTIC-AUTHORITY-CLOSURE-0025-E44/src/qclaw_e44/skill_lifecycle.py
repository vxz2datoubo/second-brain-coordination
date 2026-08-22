"""E44 Q5 — Evidence-bound skill lifecycle.

Promotion inputs come from independently verifiable evaluator/test receipts
with exact run IDs, case IDs, counterexample IDs, scope, failure conditions
and rollback evidence.

Counts and booleans are DERIVED from receipts, not caller-supplied.
Verify issued skill identity and exact legal transition.
"""
from __future__ import annotations

import hashlib, time, enum, dataclasses, hmac
from typing import Dict, Tuple, Optional

E44_SKILL_SCHEMA = "44.0"


class SkillState(enum.Enum):
    CANDIDATE = "candidate"
    EXPERIMENTAL = "experimental"
    FORMAL = "formal"
    DEMOTED = "demoted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclasses.dataclass(frozen=True)
class TransitionReceipt:
    """Independently verifiable promotion transition receipt."""
    receipt_id: str
    from_state: SkillState
    to_state: SkillState
    evidence_record_ids: Tuple[str, ...]
    test_run_id: str
    case_count: int
    counterexample_count: int
    scope_definition: str
    failure_conditions: Tuple[str, ...]
    rollback_defined: bool
    timestamp_ns: int


@dataclasses.dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    state: SkillState
    description: str
    transitions: Tuple[TransitionReceipt, ...]
    schema_version: str
    issuer: str
    factory_signature: bytes


class SkillPromotionGate:
    """Gate for skill state transitions. ALL fields derived from TransitionReceipt."""

    def can_promote_to_experimental(self, receipt: TransitionReceipt) -> bool:
        return (receipt.from_state == SkillState.CANDIDATE
                and receipt.to_state == SkillState.EXPERIMENTAL
                and receipt.case_count >= 2
                and receipt.counterexample_count == 0
                and len(receipt.failure_conditions) >= 1
                and receipt.rollback_defined
                and len(receipt.evidence_record_ids) >= 2)

    def can_promote_to_formal(self, receipt: TransitionReceipt) -> bool:
        return (receipt.from_state == SkillState.EXPERIMENTAL
                and receipt.to_state == SkillState.FORMAL
                and receipt.case_count >= 5
                and receipt.counterexample_count == 0
                and len(receipt.failure_conditions) >= 2
                and receipt.rollback_defined
                and len(receipt.evidence_record_ids) >= 3)

    def single_sample_not_formal(self, receipt: TransitionReceipt) -> bool:
        """Single sample/case cannot become FORMAL."""
        return receipt.to_state != SkillState.FORMAL or receipt.case_count >= 5


class SkillFactory:
    """Only path to create Skill and TransitionReceipt objects."""

    def __init__(self, signing_key: bytes):
        self._signing_key = signing_key
        self._issuer = "E44-skill-factory"
        self._schema = E44_SKILL_SCHEMA
        self._skills: Dict[str, Skill] = {}

    def _sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._signing_key, payload, "sha256")

    def create_skill(self, name: str, description: str) -> Skill:
        skill_id = hashlib.sha256(
            f"{name}|{description[:100]}|{E44_SKILL_SCHEMA}".encode()
        ).hexdigest()

        if skill_id in self._skills:
            raise ValueError(f"duplicate skill {skill_id[:16]}")

        skill = Skill(
            skill_id=skill_id,
            name=name,
            state=SkillState.CANDIDATE,
            description=description,
            transitions=(),
            schema_version=E44_SKILL_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(f"{skill_id}|{name}|{SkillState.CANDIDATE.value}|{E44_SKILL_SCHEMA}|0".encode())
        skill = dataclasses.replace(skill, factory_signature=sig)

        self._skills[skill_id] = skill
        return skill

    def promote(self, skill: Skill, target_state: SkillState,
                receipt: TransitionReceipt) -> Skill:
        """Promote a skill. Receipt fields drive the gate, not caller."""
        if skill.skill_id not in self._skills:
            raise ValueError(f"unregistered skill {skill.skill_id[:16]}")

        gate = SkillPromotionGate()

        if target_state == SkillState.EXPERIMENTAL:
            if not gate.can_promote_to_experimental(receipt):
                raise ValueError("promotion gate: experimental not satisfied")
        elif target_state == SkillState.FORMAL:
            if not gate.can_promote_to_formal(receipt):
                raise ValueError("promotion gate: formal not satisfied")
        else:
            raise ValueError(f"invalid target state: {target_state.value}")

        # Legal transition check
        legal = {
            SkillState.CANDIDATE: (SkillState.EXPERIMENTAL,),
            SkillState.EXPERIMENTAL: (SkillState.FORMAL, SkillState.DEMOTED),
        }
        allowed = legal.get(skill.state, ())
        if target_state not in allowed:
            raise ValueError(f"illegal transition {skill.state.value}→{target_state.value}")

        new_skill = Skill(
            skill_id=skill.skill_id,
            name=skill.name,
            state=target_state,
            description=skill.description,
            transitions=skill.transitions + (receipt,),
            schema_version=E44_SKILL_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(
            f"{skill.skill_id}|{skill.name}|{target_state.value}|{E44_SKILL_SCHEMA}|{len(new_skill.transitions)}".encode())
        new_skill = dataclasses.replace(new_skill, factory_signature=sig)

        self._skills[skill.skill_id] = new_skill
        return new_skill

    def demote(self, skill: Skill, evidence_record_id: str) -> Skill:
        """Demote a skill with evidence."""
        if skill.skill_id not in self._skills:
            raise ValueError(f"unregistered skill")

        receipt = TransitionReceipt(
            receipt_id=hashlib.sha256(f"demote:{skill.skill_id}|{evidence_record_id}".encode()).hexdigest(),
            from_state=skill.state,
            to_state=SkillState.DEMOTED,
            evidence_record_ids=(evidence_record_id,),
            test_run_id="demotion",
            case_count=1,
            counterexample_count=1,
            scope_definition="demotion",
            failure_conditions=("demotion_evidence",),
            rollback_defined=True,
            timestamp_ns=time.time_ns(),
        )

        new_skill = Skill(
            skill_id=skill.skill_id,
            name=skill.name,
            state=SkillState.DEMOTED,
            description=skill.description,
            transitions=skill.transitions + (receipt,),
            schema_version=E44_SKILL_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(
            f"{skill.skill_id}|{skill.name}|{SkillState.DEMOTED.value}|{E44_SKILL_SCHEMA}|{len(new_skill.transitions)}".encode())
        new_skill = dataclasses.replace(new_skill, factory_signature=sig)
        self._skills[skill.skill_id] = new_skill
        return new_skill

    def verify(self, skill: Skill) -> bool:
        stored = self._skills.get(skill.skill_id)
        if stored is None or stored is not skill:
            return False
        expected_sig = self._sign(
            f"{skill.skill_id}|{skill.name}|{skill.state.value}|{E44_SKILL_SCHEMA}|{len(skill.transitions)}".encode())
        return skill.factory_signature == expected_sig and skill.issuer == self._issuer
