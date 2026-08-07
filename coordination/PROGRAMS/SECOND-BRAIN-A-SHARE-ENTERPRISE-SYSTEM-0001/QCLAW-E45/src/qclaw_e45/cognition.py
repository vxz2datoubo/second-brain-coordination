"""E45 Q4 — Evidence-derived Cognition and Memory Routing

KNOWN_AND_STATED requires exact verified user-message origin.
Generic documents cannot create personal/GLOBAL memory authority.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from qclaw_e45.authority import EvidenceBundle, EvidenceRecord, EvidenceRegistry
from qclaw_e45.capability import EvidenceOrigin, VerificationState, ConfidenceBand


class MemoryZone(Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    DO_NOT_PERSIST = "do_not_persist"


@dataclass(frozen=True)
class CognitionEntry:
    """Memory routing candidate — issued by CognitionEngine only."""
    entry_id: str
    content: str
    origin: EvidenceOrigin
    memory_zone: MemoryZone
    confidence: ConfidenceBand
    stability: str  # "stable"/"tentative"/"speculative"
    bundle_id: str

    def __post_init__(self):
        # Immutable; no caller modification
        pass


class CognitionEngine:
    """Memory routing engine. Callers cannot create CognitionEntry directly."""

    def __init__(self, registry: EvidenceRegistry):
        self._registry = registry
        self._entries: list = []

    def derive_entry(self, bundle: EvidenceBundle) -> CognitionEntry:
        """Derive memory routing from bundle evidence only."""
        records = list(bundle.records)
        content = " ".join(r.decoded_text for r in records)
        origin = bundle.derived_origin

        # KNOWN_AND_STATED: requires exact verified user-message origin
        # Generic documents / prose ("I believe") do not qualify
        has_user_origin = any(
            r.origin == EvidenceOrigin.USER_EXPLICIT_MESSAGE
            and r.verification_state == VerificationState.VERIFIED
            and "user_msg_" in r.source_identity
            for r in records
        )

        if has_user_origin:
            zone = MemoryZone.GLOBAL
            stability = "stable"
        elif origin == EvidenceOrigin.SOURCE_DOCUMENT and bundle.verification_state == VerificationState.VERIFIED:
            zone = MemoryZone.PROJECT
            stability = "stable"
        elif origin in (EvidenceOrigin.AUTHOR_CLAIM, EvidenceOrigin.INFERENCE):
            zone = MemoryZone.CANDIDATE
            stability = "tentative"
        elif origin in (EvidenceOrigin.HYPOTHESIS, EvidenceOrigin.VALUE_JUDGMENT):
            zone = MemoryZone.CANDIDATE
            stability = "speculative"
        else:
            zone = MemoryZone.CANDIDATE
            stability = "tentative"

        entry_id = f"cog-{bundle.bundle_id[:16]}"
        entry = CognitionEntry(
            entry_id=entry_id,
            content=content,
            origin=origin,
            memory_zone=zone,
            confidence=bundle.derived_confidence,
            stability=stability,
            bundle_id=bundle.bundle_id,
        )
        self._entries.append(entry)
        return entry

    @property
    def entries(self) -> list:
        return self._entries[:]
