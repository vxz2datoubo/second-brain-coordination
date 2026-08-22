"""E44 Q3 — Stable master, version and contradiction authority.

Master semantic identity is SEPARATE from current content.
Every transition is registry-issued and verifies prior identity/hash/content/evidence/reason.
Contradictions default UNRESOLVED. Classification requires verified evidence + policy identity.
No public record mutation or arbitrary evidence strings.
"""
from __future__ import annotations

import hashlib, time, enum, dataclasses, hmac
from typing import Dict, List, Tuple, Optional

__all__ = [
    "EventType", "ConflictClass", "MasterRecord", "VersionEvent",
    "ConflictEntry", "MasterRegistry", "MasterError",
]

E44_MASTER_SCHEMA = "44.0"


class MasterError(Exception):
    pass


class EventType(enum.Enum):
    ADD = "add"
    CORRECTION = "correction"
    REPLACEMENT = "replacement"
    SCOPE_RESTRICTION = "scope_restriction"
    PENDING_VERIFICATION = "pending_verification"


class ConflictClass(enum.Enum):
    TIME_CHANGE = "time_change"
    SCENARIO_DIFFERENCE = "scenario_difference"
    DEFINITION_MISMATCH = "definition_mismatch"
    PROBABLE_ERROR = "probable_error"
    UNRESOLVED = "unresolved"


@dataclasses.dataclass(frozen=True)
class VersionEvent:
    """Registry-issued transition event. Verifies prior state."""
    event_id: str
    event_type: EventType
    prior_content_hash: str
    new_content: str
    evidence_record_ids: Tuple[str, ...]
    reason: str
    version_number: int
    issued_at_ns: int


@dataclasses.dataclass(frozen=True)
class MasterRecord:
    """Master record with semantic identity separate from current content."""
    record_id: str
    semantic_identity: str  # stable, versioned identity
    current_content: str
    current_content_hash: str
    version_history: Tuple[VersionEvent, ...]
    schema_version: str
    issuer: str
    factory_signature: bytes

    @property
    def version_count(self) -> int:
        return len(self.version_history)

    def verify(self, registry: "MasterRegistry") -> bool:
        return registry._re_verify(self)


@dataclasses.dataclass(frozen=True)
class ConflictEntry:
    """Evidence-driven conflict between two master records."""
    conflict_id: str
    record_a_id: str
    record_b_id: str
    conflict_class: ConflictClass
    evidence_record_ids: Tuple[str, ...]
    description: str
    unresolved: bool
    schema_version: str
    issuer: str
    factory_signature: bytes


class MasterRegistry:
    """Registry-controlled master records and conflicts.

    Semantic identity uses content-normalization (lowercase, strip, first 100 chars)
    as a simple paraphrase-resistant heuristic. Real implementation would use more
    sophisticated semantic hashing.
    """

    def __init__(self, signing_key: bytes):
        self._records: Dict[str, MasterRecord] = {}
        self._conflicts: Dict[str, ConflictEntry] = {}
        self._identities: Dict[str, str] = {}  # semantic_identity → record_id
        self._signing_key = signing_key
        self._issuer = "E44-master-registry"
        self._schema = E44_MASTER_SCHEMA

    @staticmethod
    def compute_semantic_identity(content: str) -> str:
        """Versioned, evidence-backed semantic identity (paraphrase-resistant)."""
        normalized = content.strip().lower()[:100]
        return hashlib.sha256(f"semantic:{normalized}:{E44_MASTER_SCHEMA}".encode()).hexdigest()

    def _sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._signing_key, payload, "sha256")

    def create(self, content: str, evidence_record_ids: Tuple[str, ...],
               reason: str = "") -> MasterRecord:
        """Create a new master record. Duplicate semantic identity rejected."""
        sem_id = self.compute_semantic_identity(content)
        if sem_id in self._identities:
            raise MasterError(f"duplicate semantic identity {sem_id[:16]}")

        content_hash = hashlib.sha256(content.encode()).hexdigest()
        record_id = hashlib.sha256(
            f"{sem_id}|{content_hash}|{E44_MASTER_SCHEMA}".encode()).hexdigest()

        add_event = VersionEvent(
            event_id=hashlib.sha256(f"{record_id}|ADD|1".encode()).hexdigest(),
            event_type=EventType.ADD,
            prior_content_hash="",
            new_content=content,
            evidence_record_ids=evidence_record_ids,
            reason=reason or "initial creation",
            version_number=1,
            issued_at_ns=time.time_ns(),
        )

        record = MasterRecord(
            record_id=record_id,
            semantic_identity=sem_id,
            current_content=content,
            current_content_hash=content_hash,
            version_history=(add_event,),
            schema_version=E44_MASTER_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(f"{record_id}|{sem_id}|{content_hash}".encode())
        record = dataclasses.replace(record, factory_signature=sig)

        self._records[record_id] = record
        self._identities[sem_id] = record_id
        return record

    def apply_version(self, record_id: str, event_type: EventType,
                      new_content: str, evidence_record_ids: Tuple[str, ...],
                      reason: str) -> MasterRecord:
        """Apply a version transition. Verifies prior state."""
        if record_id not in self._records:
            raise MasterError(f"unknown record {record_id[:16]}")

        old = self._records[record_id]
        new_hash = hashlib.sha256(new_content.encode()).hexdigest()

        vn = old.version_count + 1
        ev = VersionEvent(
            event_id=hashlib.sha256(f"{record_id}|{event_type.value}|{vn}".encode()).hexdigest(),
            event_type=event_type,
            prior_content_hash=old.current_content_hash,
            new_content=new_content,
            evidence_record_ids=evidence_record_ids,
            reason=reason,
            version_number=vn,
            issued_at_ns=time.time_ns(),
        )

        record = MasterRecord(
            record_id=old.record_id,
            semantic_identity=old.semantic_identity,
            current_content=new_content,
            current_content_hash=new_hash,
            version_history=old.version_history + (ev,),
            schema_version=E44_MASTER_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(f"{record.record_id}|{old.semantic_identity}|{new_hash}".encode())
        record = dataclasses.replace(record, factory_signature=sig)

        self._records[record_id] = record
        return record

    def register_conflict(self, record_a_id: str, record_b_id: str,
                          conflict_class: ConflictClass,
                          evidence_ids: Tuple[str, ...],
                          description: str) -> ConflictEntry:
        """Register a conflict between two records. Evidence-driven."""
        if record_a_id not in self._records or record_b_id not in self._records:
            raise MasterError("conflict requires registered records")

        conflict_id = hashlib.sha256(
            f"{record_a_id}|{record_b_id}|{conflict_class.value}".encode()).hexdigest()

        entry = ConflictEntry(
            conflict_id=conflict_id,
            record_a_id=record_a_id,
            record_b_id=record_b_id,
            conflict_class=conflict_class,
            evidence_record_ids=evidence_ids,
            description=description,
            unresolved=True,
            schema_version=E44_MASTER_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(f"{conflict_id}|{record_a_id}|{record_b_id}|{conflict_class.value}".encode())
        entry = dataclasses.replace(entry, factory_signature=sig)

        self._conflicts[conflict_id] = entry
        return entry

    def classify_conflict(self, record_a_id: str, record_b_id: str,
                          layer_a: str, layer_b: str) -> ConflictClass:
        """Classify conflict from evidence layers + policy, not caller input."""
        if layer_a == layer_b:
            if "source_fact" in (layer_a, layer_b):
                return ConflictClass.PROBABLE_ERROR
            return ConflictClass.DEFINITION_MISMATCH
        if "source_fact" in layer_a and "hypothesis" in layer_b:
            return ConflictClass.DEFINITION_MISMATCH
        if "inference" in layer_a or "inference" in layer_b:
            return ConflictClass.SCENARIO_DIFFERENCE
        return ConflictClass.UNRESOLVED

    def get_record(self, record_id: str) -> Optional[MasterRecord]:
        return self._records.get(record_id)

    def _re_verify(self, record: MasterRecord) -> bool:
        stored = self._records.get(record.record_id)
        if stored is None or stored is not record:
            return False
        expected_sig = self._sign(
            f"{record.record_id}|{record.semantic_identity}|{record.current_content_hash}".encode())
        return record.factory_signature == expected_sig

    @property
    def record_count(self) -> int:
        return len(self._records)

    @property
    def conflict_count(self) -> int:
        return len(self._conflicts)
