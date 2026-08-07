"""E46 Skill Lifecycle — Evidence-bound transitions, verifier-only receipt view.

Skill promotion requires independently verifiable evaluator/test receipts.
Caller-constructible TestReceipt(success=True, ...) is not authority.
Pre-E59: FORMAL promotion always fails closed.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
import hashlib
from qclaw_e46.capability import VerifiedEvidenceCapabilityView
from qclaw_e46.authority import EvidenceRegistry, EvidenceBundle, ConfidenceBand


class SkillState(str, Enum):
    CANDIDATE = "CANDIDATE"
    EXPERIMENTAL = "EXPERIMENTAL"
    FORMAL = "FORMAL"
    DEMOTED = "DEMOTED"
    DEPRECATED = "DEPRECATED"
    SUPERSEDED = "SUPERSEDED"


class TransitionOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    REJECTED_INSUFFICIENT_EVIDENCE = "REJECTED_INSUFFICIENT_EVIDENCE"
    REJECTED_NO_E59_AUTHORITY = "REJECTED_NO_E59_AUTHORITY"
    REJECTED_COUNTEREXAMPLE_FAILED = "REJECTED_COUNTEREXAMPLE_FAILED"


@dataclass(frozen=True)
class TestReceiptView:
    """Verifier-only view of a test/evaluator receipt. NOT caller-constructible.
    
    Pre-E59: all receipts are UNTRUSTED. After E59, receipts come from
    the canonical evaluator and carry verifiable run IDs."""
    receipt_id: str
    evaluator_identity: str
    run_id: str  # E59 provider run ID
    case_ids: Tuple[str, ...]
    counterexample_ids: Tuple[str, ...]
    success: bool
    scope: str = ""
    failure_conditions: str = ""
    rollback_evidence: str = ""
    
    def is_trusted(self) -> bool:
        """Only E59-issued receipts are trusted."""
        return self.evaluator_identity == "E59_CANONICAL_EVALUATOR"


@dataclass(frozen=True)
class Skill:
    """Skill with evidence-bound lifecycle."""
    skill_id: str
    name: str
    state: SkillState
    description: str
    transition_history: Tuple[dict, ...]  # List of transition records
    current_evidence_bundle_id: str = ""
    reproducible_tests: Tuple[str, ...] = ()  # case IDs
    counterexamples: Tuple[str, ...] = ()
    failure_conditions: str = ""
    rollback_plan: str = ""


class SkillRegistry:
    """Only path to issue/transition skills."""
    
    def __init__(self, evidence_registry: EvidenceRegistry):
        self._evidence = evidence_registry
        self._skills: Dict[str, Skill] = {}
    
    def create_skill(
        self,
        name: str,
        description: str,
        evidence_bundle: EvidenceBundle,
        transition_count: int = 0,
    ) -> Optional[Skill]:
        """Create skill starting at CANDIDATE. Requires evidence bundle."""
        if evidence_bundle.derived_confidence == ConfidenceBand.UNTRUSTED:
            return None
        
        skill_id = hashlib.sha256(f"SKILL:{name}".encode()).hexdigest()[:16]
        if skill_id in self._skills:
            return None
        
        skill = Skill(
            skill_id=skill_id,
            name=name,
            state=SkillState.CANDIDATE,
            description=description,
            transition_history=({
                "from": None, "to": SkillState.CANDIDATE,
                "reason": f"Created with bundle {evidence_bundle.bundle_id}",
                "bundle_id": evidence_bundle.bundle_id,
            },),
            current_evidence_bundle_id=evidence_bundle.bundle_id,
        )
        self._skills[skill_id] = skill
        return skill
    
    def promote(
        self,
        skill_id: str,
        target_state: SkillState,
        test_receipt: TestReceiptView,
        evidence_bundle: EvidenceBundle,
        evaluator_cap: Optional[VerifiedEvidenceCapabilityView] = None,
    ) -> Tuple[Optional[Skill], TransitionOutcome]:
        """Promote skill. Pre-E59: FORMAL always fails closed."""
        if skill_id not in self._skills:
            return None, TransitionOutcome.REJECTED_INSUFFICIENT_EVIDENCE
        
        skill = self._skills[skill_id]
        
        if target_state == SkillState.FORMAL:
            # Pre-E59: no E59 canonical evaluator -> FORMAL blocked
            if evaluator_cap is None or evaluator_cap.is_untrusted_double():
                return None, TransitionOutcome.REJECTED_NO_E59_AUTHORITY
            
            if not test_receipt.is_trusted():
                return None, TransitionOutcome.REJECTED_NO_E59_AUTHORITY
            
            if not test_receipt.success:
                return None, TransitionOutcome.REJECTED_COUNTEREXAMPLE_FAILED
        
        # CANDIDATE -> EXPERIMENTAL
        if target_state == SkillState.EXPERIMENTAL:
            if evidence_bundle.derived_confidence == ConfidenceBand.UNTRUSTED:
                return None, TransitionOutcome.REJECTED_INSUFFICIENT_EVIDENCE
            if not test_receipt.success:
                return None, TransitionOutcome.REJECTED_COUNTEREXAMPLE_FAILED
        
        history = list(skill.transition_history) + [{
            "from": skill.state, "to": target_state,
            "receipt_id": test_receipt.receipt_id,
            "bundle_id": evidence_bundle.bundle_id,
            "reason": f"Promoted to {target_state.value}",
        }]
        
        updated = Skill(
            skill_id=skill.skill_id,
            name=skill.name,
            state=target_state,
            description=skill.description,
            transition_history=tuple(history),
            current_evidence_bundle_id=evidence_bundle.bundle_id,
            reproducible_tests=test_receipt.case_ids,
            counterexamples=test_receipt.counterexample_ids,
            failure_conditions=test_receipt.failure_conditions,
            rollback_plan=test_receipt.rollback_evidence,
        )
        self._skills[skill_id] = updated
        return updated, TransitionOutcome.ACCEPTED
    
    def verify(self, skill: Skill) -> bool:
        """Verify skill is registry-issued."""
        return skill.skill_id in self._skills and self._skills[skill.skill_id] == skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)
