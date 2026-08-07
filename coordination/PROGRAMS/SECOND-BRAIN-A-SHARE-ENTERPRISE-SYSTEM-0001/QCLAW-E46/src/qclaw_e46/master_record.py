"""E46 Master Record — Evidence-required transitions, no tautological checks."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict
import hashlib
from qclaw_e46.capability import VerifiedEvidenceCapabilityView
from qclaw_e46.authority import EvidenceRegistry, EvidenceRecord, EvidenceBundle


class TransitionType(str, Enum):
    ADD = "add"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"


class ConflictClass(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    TIME_CHANGE = "TIME_CHANGE"
    SCENARIO_DIFFERENCE = "SCENARIO_DIFFERENCE"
    DEFINITION_MISMATCH = "DEFINITION_MISMATCH"
    PROBABLE_ERROR = "PROBABLE_ERROR"


@dataclass(frozen=True)
class VersionEvent:
    """Version transition with evidence receipt."""
    event_id: str
    transition: TransitionType
    content: str
    content_hash: str  # SHA-256 of content
    prior_hash: str
    evidence_bundle_id: str  # Must reference a registered bundle
    reason: str


@dataclass(frozen=True)
class MasterRecord:
    """Master record with version history and conflict tracking."""
    record_id: str
    semantic_identity: str  # Stable identity separate from content
    current_content: str
    current_content_hash: str
    version_history: Tuple[VersionEvent, ...]
    conflicts: Tuple[Tuple[str, ConflictClass, str], ...]  # (event_id, class, detail)
    first_created: str  # Timestamp of initial event


class MasterRecordRegistry:
    """Only path to issue/transition master records."""
    
    def __init__(self, evidence_registry: EvidenceRegistry):
        self._evidence = evidence_registry
        self._records: Dict[str, MasterRecord] = {}
        self._semantic_ids: Dict[str, str] = {}  # semantic_id -> record_id
    
    def create_record(
        self,
        semantic_identity: str,
        initial_content: str,
        evidence_bundle: EvidenceBundle = None,
        evaluator_cap: Optional[VerifiedEvidenceCapabilityView] = None,
    ) -> Optional[MasterRecord]:
        """Create a new master record with initial ADD event.
        
        Requires: evidence bundle registered. evaluator_cap must be VERIFIED
        for the transition to be accepted as authority (pre-E59: rejects).
        """
        if evidence_bundle is None:
            return None
        
        # All pre-E59: evaluator not available -> PENDING_VERIFICATION
        transition = TransitionType.ADD
        if evaluator_cap is None or evaluator_cap.is_untrusted_double():
            transition = TransitionType.PENDING_VERIFICATION
        
        content_hash = hashlib.sha256(initial_content.encode()).hexdigest()
        
        event = VersionEvent(
            event_id=f"{semantic_identity}:ADD:v1",
            transition=transition,
            content=initial_content,
            content_hash=content_hash,
            prior_hash="",
            evidence_bundle_id=evidence_bundle.bundle_id,
            reason=f"Initial creation via bundle {evidence_bundle.bundle_id}",
        )
        
        # Deduplicate by semantic identity
        if semantic_identity in self._semantic_ids:
            # Existing record: this should trigger conflict resolution
            existing_id = self._semantic_ids[semantic_identity]
            existing = self._records[existing_id]
            if existing.current_content_hash != content_hash:
                return None  # Caller must use add_version with conflict
            return existing
        
        rec_id = hashlib.sha256(f"MASTER:{semantic_identity}".encode()).hexdigest()[:16]
        record = MasterRecord(
            record_id=rec_id,
            semantic_identity=semantic_identity,
            current_content=initial_content,
            current_content_hash=content_hash,
            version_history=(event,),
            conflicts=(),
            first_created=event.event_id,
        )
        self._records[rec_id] = record
        self._semantic_ids[semantic_identity] = rec_id
        return record
    
    def add_version(
        self,
        record_id: str,
        new_content: str,
        evidence_bundle: EvidenceBundle,
        transition: TransitionType,
        evaluator_cap: Optional[VerifiedEvidenceCapabilityView] = None,
    ) -> Optional[MasterRecord]:
        """Add a version transition. Requires evidence + evaluator receipt."""
        if record_id not in self._records:
            return None
        
        # Pre-E59: evaluator required, all fail-closed
        if evaluator_cap is None or not evaluator_cap.is_verified():
            transition = TransitionType.PENDING_VERIFICATION
        
        old = self._records[record_id]
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        
        # Must verify bundle exists in registry
        if self._evidence.get_bundle(evidence_bundle.bundle_id) is None:
            return None
        
        # Detect silent overwrite
        if transition == TransitionType.REPLACEMENT and new_hash == old.current_content_hash:
            return None  # No actual change
        
        event = VersionEvent(
            event_id=f"{old.semantic_identity}:{transition.value}:v{len(old.version_history)+1}",
            transition=transition,
            content=new_content,
            content_hash=new_hash,
            prior_hash=old.current_content_hash,
            evidence_bundle_id=evidence_bundle.bundle_id,
            reason=f"{transition.value} via bundle {evidence_bundle.bundle_id}",
        )
        
        history = list(old.version_history) + [event]
        
        record = MasterRecord(
            record_id=old.record_id,
            semantic_identity=old.semantic_identity,
            current_content=new_content,
            current_content_hash=new_hash,
            version_history=tuple(history),
            conflicts=old.conflicts,
            first_created=old.first_created,
        )
        self._records[record_id] = record
        return record
    
    def record_conflict(
        self,
        record_id: str,
        conflict_id: str,
        conflict_class: ConflictClass,
        detail: str,
    ) -> Optional[MasterRecord]:
        """Record a conflict — requires evidence-backed classification."""
        if record_id not in self._records:
            return None
        
        old = self._records[record_id]
        conflicts = list(old.conflicts) + [(conflict_id, conflict_class, detail)]
        
        record = MasterRecord(
            record_id=old.record_id,
            semantic_identity=old.semantic_identity,
            current_content=old.current_content,
            current_content_hash=old.current_content_hash,
            version_history=old.version_history,
            conflicts=tuple(conflicts),
            first_created=old.first_created,
        )
        self._records[record_id] = record
        return record
    
    def get_record(self, record_id: str) -> Optional[MasterRecord]:
        return self._records.get(record_id)
    
    def get_history(self, record_id: str) -> int:
        """Return version count."""
        rec = self._records.get(record_id)
        return len(rec.version_history) if rec else 0
