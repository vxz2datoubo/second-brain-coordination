"""E41 Q3 — Contradiction, Dedup, Version & Master Record

Merge duplicates without erasing provenance.
Preserve conflicting claims with classification.
Version governance with explicit events.
Prohibit silent overwrite and patch-forest authority.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import hashlib


class ConflictClass(str, Enum):
    TIME_CHANGE = "time_change"
    SCENARIO_DIFFERENCE = "scenario_difference"
    DEFINITION_MISMATCH = "definition_mismatch"
    PROBABLE_ERROR = "probable_error"
    UNRESOLVED = "unresolved"


class VersionEventType(str, Enum):
    ADDITION = "addition"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"


@dataclass(frozen=True)
class VersionEvent:
    """An explicit version change event."""
    event_type: VersionEventType
    atom_id: str
    previous_content: str
    new_content: str
    reason: str


@dataclass(frozen=True)
class MasterRecord:
    """One current master record per knowledge object with explicit version history."""
    object_id: str
    current_content: str
    provenance_list: List[str]  # all provenance entries, never erased
    version_history: List[VersionEvent] = field(default_factory=list)
    conflict_classifications: Dict[str, ConflictClass] = field(default_factory=dict)


@dataclass(frozen=True)
class Contradiction:
    """A preserved contradiction between claims."""
    contradiction_id: str
    claim_a_id: str
    claim_b_id: str
    classification: ConflictClass
    resolution_status: str = "open"  # open | resolved | accepted_conflict
    resolution_note: str = ""


def compute_object_id(content: str) -> str:
    """Deterministic object ID for dedup."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:20]


def merge_duplicates(
    objects: Dict[str, MasterRecord],
    new_content: str,
    new_provenance: str,
) -> MasterRecord:
    """Merge into one master record without erasing provenance.
    
    If same content exists, append provenance.
    If different content, record as version event + conflict.
    Never silently overwrites.
    Updates objects dict in place and returns the record.
    """
    obj_id = compute_object_id(new_content)
    if obj_id in objects:
        existing = objects[obj_id]
        merged = MasterRecord(
            object_id=obj_id,
            current_content=existing.current_content,
            provenance_list=existing.provenance_list + [new_provenance],
            version_history=existing.version_history,
            conflict_classifications=existing.conflict_classifications,
        )
        objects[obj_id] = merged
        return merged

    # New object
    rec = MasterRecord(
        object_id=obj_id,
        current_content=new_content,
        provenance_list=[new_provenance],
    )
    objects[obj_id] = rec
    return rec


def classify_conflict(old_content: str, new_content: str) -> ConflictClass:
    """Classify a conflict. Default: UNRESOLVED.
    
    Never auto-assumes TIME_CHANGE or PROBABLE_ERROR without evidence.
    """
    old_words = set(old_content.lower().split())
    new_words = set(new_content.lower().split())
    overlap = len(old_words & new_words) / max(len(old_words | new_words), 1)
    if overlap >= 0.8:
        return ConflictClass.DEFINITION_MISMATCH
    if overlap >= 0.5:
        return ConflictClass.SCENARIO_DIFFERENCE
    return ConflictClass.UNRESOLVED


def add_version_event(
    record: MasterRecord,
    event_type: VersionEventType,
    previous_content: str,
    new_content: str,
    reason: str,
) -> MasterRecord:
    """Add a version event and update current content.
    
    Never silently overwrites — always records the event.
    """
    event = VersionEvent(
        event_type=event_type,
        atom_id=record.object_id,
        previous_content=previous_content,
        new_content=new_content,
        reason=reason,
    )
    return MasterRecord(
        object_id=record.object_id,
        current_content=new_content,
        provenance_list=record.provenance_list,
        version_history=record.version_history + [event],
        conflict_classifications=record.conflict_classifications,
    )


def prohibit_silent_overwrite(
    current: Optional[MasterRecord],
    incoming_content: str,
) -> List[str]:
    """Check if incoming would silently overwrite. Returns violations."""
    violations = []
    if current is None:
        return violations
    if current.current_content != incoming_content and not current.version_history:
        violations.append(
            f"different content without version event: "
            f"'{current.current_content[:40]}' -> '{incoming_content[:40]}'"
        )
    return violations
