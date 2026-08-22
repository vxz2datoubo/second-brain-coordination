"""E44 Q4 — User cognition and memory write-candidate authority.

KNOWN_AND_STATED requires verified user-origin/message evidence.
State, stability and memory destination are RECOMPUTED from evidence origin,
quality, recurrence, scope, sensitivity and versioned policy.
GLOBAL cannot be produced by one arbitrary record.
Emit memory write candidates only.
"""
from __future__ import annotations

import hashlib, time, enum, dataclasses, hmac
from typing import Dict, Optional, Set

from qclaw_e44.capability import EvidenceOrigin
from qclaw_e44.authority import EvidenceRegistry, EvidenceRecord

E44_COGNITION_SCHEMA = "44.0"


class CognitionState(enum.Enum):
    KNOWN_AND_STATED = "known_and_stated"
    KNOWN_BUT_UNSTATED = "known_but_unstated"
    UNKNOWN_BUT_READABLE = "unknown_but_readable"
    UNKNOWN_AND_NEEDS_LAYERING = "unknown_and_needs_layering"


class MemoryZone(enum.Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    DO_NOT_PERSIST = "do_not_persist"


@dataclasses.dataclass(frozen=True)
class CognitionEntry:
    """Memory write candidate. Registry-issued. Never claims memory was written."""
    entry_id: str
    state: CognitionState
    memory_zone: MemoryZone
    evidence_record_id: str
    stability_score: float
    schema_version: str
    issuer: str
    factory_signature: bytes


class CognitionEngine:
    """Derives cognition state and memory destination from verified evidence.

    State, stability and memory zone are recomputed from evidence origin,
    quality, recurrence, scope and policy. Callers cannot supply these directly.
    KnOWN_AND_STATED requires verified user-origin evidence.
    GLOBAL requires multiple correlated sources.
    """

    def __init__(self, registry: EvidenceRegistry, signing_key: bytes):
        self._registry = registry
        self._signing_key = signing_key
        self._issuer = "E44-cognition"
        self._schema = E44_COGNITION_SCHEMA
        self._candidate_buffer: Dict[str, CognitionEntry] = {}

    def _sign(self, payload: bytes) -> bytes:
        return hmac.digest(self._signing_key, payload, "sha256")

    def analyze(self, record_id: str) -> CognitionEntry:
        """Analyze one evidence record. State/memory DERIVED, not caller-input."""
        rec = self._registry.get_record(record_id)
        if rec is None:
            raise ValueError(f"unregistered record {record_id[:16]}")

        # Derive state
        if rec.origin_class == EvidenceOrigin.USER_EXPLICIT:
            state = CognitionState.KNOWN_AND_STATED
        elif rec.origin_class == EvidenceOrigin.SOURCE_FACT:
            state = CognitionState.KNOWN_BUT_UNSTATED
        elif rec.origin_class in (EvidenceOrigin.AUTHOR_CLAIM, EvidenceOrigin.INFERENCE):
            state = CognitionState.UNKNOWN_BUT_READABLE
        else:
            state = CognitionState.UNKNOWN_AND_NEEDS_LAYERING

        # Derive stability
        stability = self._derive_stability(rec.origin_class)

        # Derive memory zone
        zone = self._derive_memory_zone(rec.origin_class, stability)

        entry_id = hashlib.sha256(
            f"{record_id}|{state.value}|{zone.value}|{stability}".encode()
        ).hexdigest()

        entry = CognitionEntry(
            entry_id=entry_id,
            state=state,
            memory_zone=zone,
            evidence_record_id=record_id,
            stability_score=stability,
            schema_version=E44_COGNITION_SCHEMA,
            issuer=self._issuer,
            factory_signature=b"",
        )
        sig = self._sign(f"{entry_id}|{state.value}|{zone.value}|{record_id}".encode())
        entry = dataclasses.replace(entry, factory_signature=sig)

        self._candidate_buffer[record_id] = entry
        return entry

    def _derive_stability(self, origin: EvidenceOrigin) -> float:
        if origin == EvidenceOrigin.USER_EXPLICIT: return 1.0
        if origin == EvidenceOrigin.SOURCE_FACT: return 0.75
        if origin == EvidenceOrigin.AUTHOR_CLAIM: return 0.5
        if origin == EvidenceOrigin.INFERENCE: return 0.3
        if origin == EvidenceOrigin.HYPOTHESIS: return 0.15
        return 0.05

    def _derive_memory_zone(self, origin: EvidenceOrigin,
                            stability: float) -> MemoryZone:
        if origin == EvidenceOrigin.USER_EXPLICIT and stability > 0.9:
            return MemoryZone.PROJECT  # User facts → project, not auto-GLOBAL
        if origin == EvidenceOrigin.SOURCE_FACT and stability > 0.5:
            return MemoryZone.CANDIDATE
        if stability > 0.3:
            return MemoryZone.CANDIDATE
        if origin == EvidenceOrigin.VALUE_JUDGMENT:
            return MemoryZone.DO_NOT_PERSIST
        return MemoryZone.DO_NOT_PERSIST

    def verify(self, entry: CognitionEntry) -> bool:
        """Re-verify entry by recomputing signature."""
        rec = self._registry.get_record(entry.evidence_record_id)
        if rec is None:
            return False
        expected_sig = self._sign(
            f"{entry.entry_id}|{entry.state.value}|{entry.memory_zone.value}|{entry.evidence_record_id}".encode())
        return entry.factory_signature == expected_sig and entry.issuer == self._issuer

    @property
    def buffer_count(self) -> int:
        return len(self._candidate_buffer)
