"""
E43 Q4 — Evidence-Derived Cognition and Memory Routing

No authoritative caller booleans (has_user_origin_evidence, is_known, is_stated).
All cognition states derived from verified evidence only.
Memory destinations computed from evidence quality, stability, scope.
Direct CognitionEntry construction fails registry verification.
"""
from __future__ import annotations

import hashlib, enum, dataclasses, time
from typing import Dict, List, Optional, Tuple

__all__ = ["CognitionEngine", "CognitionEntry", "MemoryZone", "CognitionState"]

class MemoryZone(enum.Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    DO_NOT_PERSIST = "do_not_persist"

class CognitionState(enum.Enum):
    KNOWN_AND_STATED = "known_and_stated"      # user-origin evidence confirms
    KNOWN_BUT_UNSTATED = "known_but_unstated"  # high-prob inference
    UNKNOWN_BUT_READABLE = "unknown_but_readable"
    UNKNOWN_AND_NEEDS_LAYERING = "unknown_and_needs_layering"


@dataclasses.dataclass(frozen=True)
class CognitionEntry:
    """Write-candidate record, factory-issued."""
    entry_id: str
    state: CognitionState
    memory_zone: MemoryZone
    evidence_record_id: str  # must exist in AuthorityRegistry
    stability_score: float  # 0.0 - 1.0
    factory_signature: bytes


class CognitionEngine:
    """Derives cognition state and memory zone purely from evidence."""

    SCHEMA = "43.0"

    def __init__(self, registry, signature_key: bytes):
        """
        registry: AuthorityRegistry for evidence verification.
        signature_key: HMAC key held by factory.
        """
        self._registry = registry
        self._key = bytes(signature_key)
        import hmac as _hmac
        self._hmac = _hmac
        self._entries: Dict[str, CognitionEntry] = {}

    def analyze(self, evidence_record_id: str, atom_id: Optional[str] = None) -> CognitionEntry:
        """Derive cognition purely from evidence. No caller booleans."""
        # Verify evidence exists in registry
        record = self._registry.get_record(evidence_record_id)
        if record is None:
            raise ValueError("REGISTRY_REJECTED: evidence record not in registry")

        # Derive state from evidence layer
        layer = record.evidence_layer.value
        if layer == "source_fact":
            state = CognitionState.KNOWN_AND_STATED
            stability = 0.95
        elif layer in ("author_claim", "inference"):
            state = CognitionState.KNOWN_BUT_UNSTATED
            stability = 0.50
        elif layer == "hypothesis":
            state = CognitionState.UNKNOWN_BUT_READABLE
            stability = 0.20
        else:
            state = CognitionState.UNKNOWN_AND_NEEDS_LAYERING
            stability = 0.05

        # Derive memory zone from stability
        if stability >= 0.90:
            zone = MemoryZone.GLOBAL
        elif stability >= 0.40:
            zone = MemoryZone.PROJECT
        elif stability > 0.10:
            zone = MemoryZone.CANDIDATE
        else:
            zone = MemoryZone.DO_NOT_PERSIST

        entry_id = hashlib.sha256(
            f"{evidence_record_id}|{state.value}|{zone.value}|{stability}".encode()
        ).hexdigest()[:32]

        payload = f"{entry_id}|{evidence_record_id}|{state.value}|{zone.value}|{stability}"
        sig = self._hmac.digest(self._key, payload.encode(), "sha256")

        entry = CognitionEntry(entry_id=entry_id, state=state, memory_zone=MemoryZone(zone),
                                evidence_record_id=evidence_record_id,
                                stability_score=stability, factory_signature=sig)
        self._entries[entry_id] = entry
        return entry

    def verify(self, entry: CognitionEntry) -> bool:
        """Verify entry was issued by this engine."""
        if entry.entry_id not in self._entries:
            return False
        payload = f"{entry.entry_id}|{entry.evidence_record_id}|{entry.state.value}|{entry.memory_zone.value}|{entry.stability_score}"
        expected = self._hmac.digest(self._key, payload.encode(), "sha256")
        return self._hmac.compare_digest(expected, entry.factory_signature)

    def get_entry(self, entry_id: str) -> Optional[CognitionEntry]:
        return self._entries.get(entry_id)
