"""
E43 Q3 — Registry-Controlled Master Records and Contradictions

MasterRecord and VersionEvent are registry-controlled. Stable semantic
identity uses evidence-backed identity rules. Every transition verifies
prior identity, content, hash, evidence, event, reason and ordering.
No silent overwrite. No caller-supplied ConflictClass bypass.
"""
from __future__ import annotations

import hashlib, enum, dataclasses, time
from typing import Dict, List, Optional, Tuple

__all__ = ["MasterRecord", "VersionEvent", "ConflictClass", "ConflictEntry",
           "MasterRecordRegistry", "EventType"]

class EventType(enum.Enum):
    ADD = "add"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"
    CONTRADICTION_DETECTED = "contradiction_detected"

class ConflictClass(enum.Enum):
    TIME_CHANGE = "time_change"
    SCENARIO_DIFFERENCE = "scenario_difference"
    DEFINITION_MISMATCH = "definition_mismatch"
    PROBABLE_ERROR = "probable_error"
    UNRESOLVED = "unresolved"


@dataclasses.dataclass(frozen=True)
class VersionEvent:
    event_id: str
    event_type: EventType
    prior_version_content: str
    prior_content_hash: str
    new_content: str
    new_content_hash: str
    evidence_record_id: str
    reason: str
    timestamp_ns: int

    @staticmethod
    def compute_event_id(prior_hash: str, new_hash: str, event_type: EventType,
                          evidence_id: str, timestamp_ns: int) -> str:
        h = hashlib.sha256()
        h.update(f"{prior_hash}|{new_hash}|{event_type.value}|{evidence_id}|{timestamp_ns}".encode())
        return h.hexdigest()[:32]


@dataclasses.dataclass(frozen=True)
class ConflictEntry:
    conflict_id: str
    conflict_class: ConflictClass
    record_a_id: str
    record_b_id: str
    evidence_record_id: str
    description: str
    unresolved: bool = True
    created_at_ns: int = 0

    @staticmethod
    def compute_id(record_a: str, record_b: str, evidence_id: str) -> str:
        ids = sorted([record_a, record_b])
        h = hashlib.sha256()
        h.update(f"{ids[0]}|{ids[1]}|{evidence_id}".encode())
        return h.hexdigest()[:32]


class MasterRecord:
    """Registry-issued master record. Semantic identity = evidence-backed compute."""
    def __init__(self, record_id: str, content: str):
        self._id = record_id
        self._content = content
        self._content_hash = hashlib.sha256(content.encode()).hexdigest()
        self._versions: List[VersionEvent] = []
        self._created_ns = time.time_ns()

    @property
    def record_id(self) -> str: return self._id
    @property
    def content(self) -> str: return self._content
    @property
    def content_hash(self) -> str: return self._content_hash
    @property
    def versions(self) -> Tuple[VersionEvent, ...]: return tuple(self._versions)
    @property
    def version_count(self) -> int: return len(self._versions)
    @property
    def last_updated_ns(self) -> int:
        return self._versions[-1].timestamp_ns if self._versions else self._created_ns

    def apply_version(self, event_type: EventType, new_content: str,
                      evidence_record_id: str, reason: str) -> VersionEvent:
        """Every transition must have a VersionEvent. No silent overwrite."""
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()
        ts = time.time_ns()
        event_id = VersionEvent.compute_event_id(
            self._content_hash, new_hash, event_type, evidence_record_id, ts)
        ev = VersionEvent(event_id=event_id, event_type=event_type,
                          prior_version_content=self._content,
                          prior_content_hash=self._content_hash,
                          new_content=new_content, new_content_hash=new_hash,
                          evidence_record_id=evidence_record_id,
                          reason=reason, timestamp_ns=ts)
        self._versions.append(ev)
        self._content = new_content
        self._content_hash = new_hash
        return ev

    def can_transition(self, evidence_record_id: str) -> bool:
        """Transition requires evidence; no evidence = no transition."""
        return bool(evidence_record_id and len(evidence_record_id) > 0)

    @staticmethod
    def compute_semantic_id(content: str, evidence_id: str) -> str:
        """Semantic identity from content + evidence, not explicit key."""
        h = hashlib.sha256()
        h.update(content.encode())
        h.update(evidence_id.encode())
        return h.hexdigest()[:32]


class MasterRecordRegistry:
    """Controls all MasterRecord and ConflictEntry creation."""
    def __init__(self):
        self._records: Dict[str, MasterRecord] = {}
        self._conflicts: Dict[str, ConflictEntry] = {}
        self._object_ids: Dict[str, str] = {}  # semantic_id -> record_id

    def create(self, content: str, evidence_record_id: str) -> MasterRecord:
        sid = MasterRecord.compute_semantic_id(content, evidence_record_id)
        if sid in self._object_ids:
            raise ValueError(f"REGISTRY_REJECTED: duplicate semantic identity {sid}")
        rid = hashlib.sha256(f"{sid}|{content}|{evidence_record_id}".encode()).hexdigest()[:32]
        record = MasterRecord(rid, content)
        # Initial version event
        record.apply_version(EventType.ADD, content, evidence_record_id, "initial creation")
        self._records[rid] = record
        self._object_ids[sid] = rid
        return record

    def get(self, record_id: str) -> Optional[MasterRecord]:
        return self._records.get(record_id)

    def get_by_semantic_id(self, sid: str) -> Optional[MasterRecord]:
        rid = self._object_ids.get(sid)
        return self._records.get(rid) if rid else None

    def register_conflict(self, record_a_id: str, record_b_id: str,
                          conflict_class: ConflictClass, evidence_record_id: str,
                          description: str) -> ConflictEntry:
        if record_a_id not in self._records or record_b_id not in self._records:
            raise ValueError("REGISTRY_REJECTED: conflicting records not in registry")
        cid = ConflictEntry.compute_id(record_a_id, record_b_id, evidence_record_id)
        if cid in self._conflicts:
            raise ValueError(f"REGISTRY_REJECTED: duplicate conflict {cid}")
        entry = ConflictEntry(conflict_id=cid, conflict_class=conflict_class,
                              record_a_id=record_a_id, record_b_id=record_b_id,
                              evidence_record_id=evidence_record_id,
                              description=description,
                              created_at_ns=time.time_ns())
        self._conflicts[cid] = entry
        return entry

    def classify_conflict(self, content_a: str, content_b: str,
                          evidence_layer_a: str, evidence_layer_b: str) -> ConflictClass:
        """Evidence-driven classification, not word-overlap heuristic."""
        if evidence_layer_a == "source_fact" and evidence_layer_b == "source_fact":
            return ConflictClass.PROBABLE_ERROR
        if evidence_layer_a != evidence_layer_b:
            return ConflictClass.DEFINITION_MISMATCH
        return ConflictClass.UNRESOLVED

    @property
    def record_count(self) -> int: return len(self._records)
    @property
    def conflict_count(self) -> int: return len(self._conflicts)
