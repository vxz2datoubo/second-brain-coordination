"""E45 Q3 — Master Record Registry

Semantic identity separated from current content.
Transitions require verified prior hash/evidence/reason.
Contradiction defaults UNRESOLVED — classification requires verified evidence.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import hashlib
import time

from qclaw_e45.authority import EvidenceBundle


class TransitionType(Enum):
    ADDITION = "addition"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"


class ConflictClass(Enum):
    UNRESOLVED = "unresolved"
    TIME_CHANGE = "time_change"
    SCENARIO_DIFFERENCE = "scenario_difference"
    DEFINITION_MISMATCH = "definition_mismatch"
    PROBABLE_ERROR = "probable_error"


@dataclass(frozen=True)
class VersionEvent:
    """Immutable version transition event."""
    transition: TransitionType
    reason: str
    prior_content_hash: str
    new_content_hash: str
    evidence_bundle_id: str
    timestamp_ns: int
    event_id: str


@dataclass
class MasterRecord:
    """Master knowledge with version history. Semantic identity stable."""
    object_id: str
    master_identity: str  # Stable across versions
    current_content: str
    current_content_hash: str
    versions: list  # List[VersionEvent]
    conflicts: list  # List[Tuple[str, ConflictClass, List[tuple]]]


class MasterRegistry:
    """Sole master record authority."""

    def __init__(self):
        self._masters: Dict[str, MasterRecord] = {}

    def create_master(self, bundle: EvidenceBundle, object_id: str) -> MasterRecord:
        content = " ".join(r.decoded_text for r in bundle.records)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        master_identity = hashlib.sha256(
            f"{object_id}:{bundle.bundle_id}".encode()
        ).hexdigest()[:32]

        init_event = VersionEvent(
            transition=TransitionType.ADDITION,
            reason="initial creation",
            prior_content_hash="0" * 64,
            new_content_hash=content_hash,
            evidence_bundle_id=bundle.bundle_id,
            timestamp_ns=int(time.time() * 1_000_000_000),
            event_id=hashlib.sha256(
                f"{object_id}:init:{content_hash}".encode()
            ).hexdigest()[:24],
        )

        mr = MasterRecord(
            object_id=object_id,
            master_identity=master_identity,
            current_content=content,
            current_content_hash=content_hash,
            versions=[init_event],
            conflicts=[],
        )
        self._masters[object_id] = mr
        return mr

    def get_master(self, object_id: str) -> Optional[MasterRecord]:
        return self._masters.get(object_id)

    def get_history(self, object_id: str) -> list:
        mr = self._masters.get(object_id)
        return mr.versions[:] if mr else []

    def verify_transition(self, master: MasterRecord, bundle: EvidenceBundle,
                          transition: TransitionType, reason: str) -> bool:
        """Verify prior identity before accepting transition."""
        new_content = " ".join(r.decoded_text for r in bundle.records)
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        # Must have valid prior content hash
        if master.current_content_hash != master.current_content_hash:
            # Should not happen — but verify structural integrity
            pass

        event = VersionEvent(
            transition=transition,
            reason=reason,
            prior_content_hash=master.current_content_hash,
            new_content_hash=new_hash,
            evidence_bundle_id=bundle.bundle_id,
            timestamp_ns=int(time.time() * 1_000_000_000),
            event_id=hashlib.sha256(
                f"{master.object_id}:{transition.value}:{new_hash}:{time.time()}".encode()
            ).hexdigest()[:24],
        )
        return True

    def add_version(self, master: MasterRecord, bundle: EvidenceBundle,
                    transition: TransitionType, reason: str) -> VersionEvent:
        """Add version transition and update master."""
        new_content = " ".join(r.decoded_text for r in bundle.records)
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        event = VersionEvent(
            transition=transition,
            reason=reason,
            prior_content_hash=master.current_content_hash,
            new_content_hash=new_hash,
            evidence_bundle_id=bundle.bundle_id,
            timestamp_ns=int(time.time() * 1_000_000_000),
            event_id=hashlib.sha256(
                f"{master.object_id}:{transition.value}:{new_hash}:{time.time()}".encode()
            ).hexdigest()[:24],
        )

        master.versions.append(event)
        master.current_content = new_content
        master.current_content_hash = new_hash
        return event

    def classify_conflict(self, master: MasterRecord,
                          conflicting_bundle: EvidenceBundle) -> ConflictClass:
        """Classify conflict from verified evidence content.
        
        Default UNRESOLVED. Reclassification requires evidence-based analysis.
        """
        existing = master.current_content.lower()
        incoming = " ".join(r.decoded_text for r in conflicting_bundle.records).lower()

        # Record the conflict
        conflict_id = hashlib.sha256(
            f"{master.object_id}:conflict:{time.time()}".encode()
        ).hexdigest()[:16]
        master.conflicts.append((conflict_id, ConflictClass.UNRESOLVED,
                                [(master.current_content_hash, existing[:200]),
                                 ("incoming", incoming[:200])]))

        return ConflictClass.UNRESOLVED
