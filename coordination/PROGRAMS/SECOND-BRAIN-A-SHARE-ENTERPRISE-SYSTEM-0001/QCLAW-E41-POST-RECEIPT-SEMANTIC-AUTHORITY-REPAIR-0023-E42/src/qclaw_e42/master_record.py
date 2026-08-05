"""E42 Q3 — Master Record & Contradiction Governance

- Stable semantic object identity separate from mutable version content
- One master with immutable chronological version history
- Every content change requires version event with exact prev/current identity + evidence
- Conflict classification evidence-based; default UNRESOLVED
- Silent overwrite rejected on EVERY transition
"""
import hashlib, enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

DOMAIN = b"QCLAW:E42:MASTER:V1"

class VersionEventType(enum.Enum):
    ADDITION = "addition"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"

class ConflictClass(enum.Enum):
    UNRESOLVED = "unresolved"
    TIME_CHANGE = "time_change"
    SCENARIO_DIFFERENCE = "scenario_difference"
    DEFINITION_MISMATCH = "definition_mismatch"
    PROBABLE_ERROR = "probable_error"

@dataclass(frozen=True)
class VersionEvent:
    event_type: VersionEventType
    previous_content: str
    new_content: str
    evidence_id: str
    reason: str
    timestamp: str
    event_id: str = ""

    def __post_init__(self):
        if not self.event_id:
            h = hashlib.sha256(
                f"{self.event_type.value}|{self.previous_content}|{self.new_content}|{self.evidence_id}|{self.timestamp}".encode()
            ).hexdigest()
            object.__setattr__(self, "event_id", h)


@dataclass(frozen=True)
class MasterRecord:
    object_id: str
    current_content: str
    provenance_list: Tuple[str, ...] = ()
    version_history: Tuple[VersionEvent, ...] = ()
    conflict_classifications: Tuple[Tuple[str, str, ConflictClass], ...] = ()
    # (conflicting_content, evidence_id, classification)

    def with_version_event(self, event: VersionEvent) -> "MasterRecord":
        if event.previous_content != self.current_content:
            raise ValueError(
                f"Version event previous_content does not match current: "
                f"'{event.previous_content[:30]}' vs '{self.current_content[:30]}'"
            )
        return MasterRecord(
            object_id=self.object_id,
            current_content=event.new_content,
            provenance_list=self.provenance_list + (event.evidence_id,),
            version_history=self.version_history + (event,),
            conflict_classifications=self.conflict_classifications,
        )

    def with_conflict(self, conflicting_content: str, evidence_id: str,
                      classification: ConflictClass) -> "MasterRecord":
        return MasterRecord(
            object_id=self.object_id,
            current_content=self.current_content,
            provenance_list=self.provenance_list,
            version_history=self.version_history,
            conflict_classifications=self.conflict_classifications + (
                (conflicting_content, evidence_id, classification),
            ),
        )


def compute_object_id(semantic_key: str) -> str:
    """Stable semantic object identity — NOT content-hash based.

    Uses a stable semantic key so the same knowledge object is
    referenced across versions even as content changes.
    """
    return hashlib.sha256(DOMAIN + semantic_key.encode("utf-8")).hexdigest()


def classify_conflict(original: str, conflicting: str,
                      evidence: Optional[Dict] = None) -> ConflictClass:
    """Classify conflict based on EVIDENCE, not word overlap heuristics.

    Returns UNRESOLVED by default unless evidence proves otherwise.
    """
    if not evidence:
        return ConflictClass.UNRESOLVED

    if evidence.get("time_change"):
        return ConflictClass.TIME_CHANGE
    if evidence.get("scenario_difference"):
        return ConflictClass.SCENARIO_DIFFERENCE
    if evidence.get("definition_mismatch"):
        return ConflictClass.DEFINITION_MISMATCH
    if evidence.get("probable_error"):
        return ConflictClass.PROBABLE_ERROR

    return ConflictClass.UNRESOLVED


def prohibit_silent_overwrite(
    current: MasterRecord,
    new_content: str,
    evidence_id: str,
    event_type: VersionEventType,
    timestamp: str,
) -> Tuple[MasterRecord, VersionEvent]:
    """Enforce version-event requirement on EVERY content transition.

    Always creates a version event. Never silently overwrites.
    Rejects transitions without evidence.
    """
    if not evidence_id:
        raise ValueError("evidence_id required for content transition")

    if not timestamp:
        raise ValueError("timestamp required for content transition")

    event = VersionEvent(
        event_type=event_type,
        previous_content=current.current_content,
        new_content=new_content,
        evidence_id=evidence_id,
        reason=f"{event_type.value}: {new_content[:50]}",
        timestamp=timestamp,
    )

    return current.with_version_event(event), event


class MasterRecordRegistry:
    """Manages the set of master records by semantic object ID."""

    def __init__(self):
        self._records: Dict[str, MasterRecord] = {}

    def get_or_create(self, semantic_key: str, initial_content: str,
                      provenance: str) -> Tuple[MasterRecord, bool]:
        obj_id = compute_object_id(semantic_key)
        if obj_id in self._records:
            return self._records[obj_id], False

        rec = MasterRecord(
            object_id=obj_id,
            current_content=initial_content,
            provenance_list=(provenance,),
        )
        self._records[obj_id] = rec
        return rec, True

    def update(self, record: MasterRecord):
        self._records[record.object_id] = record

    def get(self, semantic_key: str) -> Optional[MasterRecord]:
        return self._records.get(compute_object_id(semantic_key))

    def __len__(self):
        return len(self._records)
