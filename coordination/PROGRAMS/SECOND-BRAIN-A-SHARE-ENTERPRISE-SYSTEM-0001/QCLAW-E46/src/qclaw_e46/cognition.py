"""E46 Cognition — Evidence-derived memory routing, NO prose heuristics.

Memory destinations (GLOBAL/PROJECT/CANDIDATE/NO_PERSIST) are derived
from evidence quality/stability/scope/sensitivity — never from caller booleans.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from qclaw_e46.capability import VerifiedEvidenceCapabilityView, EvidenceOrigin
from qclaw_e46.authority import EvidenceRegistry, EvidenceBundle, ConfidenceBand


class MemoryZone(str, Enum):
    GLOBAL = "GLOBAL"
    PROJECT = "PROJECT"
    CANDIDATE = "CANDIDATE"
    NO_PERSIST = "NO_PERSIST"


class FactOrigin(str, Enum):
    EXPLICIT_USER_FACT = "EXPLICIT_USER_FACT"
    HIGH_PROBABILITY_INFERENCE = "HIGH_PROBABILITY_INFERENCE"
    LOW_CONFIDENCE_GUESS = "LOW_CONFIDENCE_GUESS"
    EXTERNAL_SOURCE = "EXTERNAL_SOURCE"
    UNTRUSTED = "UNTRUSTED"


@dataclass(frozen=True)
class CognitionEntry:
    """Evidence-derived cognition entry. Registry-issued only."""
    entry_id: str
    statement: str
    fact_origin: FactOrigin
    memory_zone: MemoryZone
    evidence_bundle_id: str
    confidence: ConfidenceBand
    scope: str = ""
    invalidation_trigger: str = ""


class CognitionRouter:
    """Derives memory destinations from evidence — no prose heuristics."""
    
    def __init__(self, evidence_registry: EvidenceRegistry):
        self._evidence = evidence_registry
        self._entries = {}
    
    def derive_memory_zone(
        self,
        bundle: EvidenceBundle,
        user_origin_verified: bool = False,
    ) -> MemoryZone:
        """Derive memory zone from evidence quality + user-origin verification.
        
        Pre-E59: user_origin_verified is always False (no E59 capability yet).
        GLOBAL memory requires VERIFIED user-origin evidence — blocked pre-E59.
        """
        if bundle.derived_confidence == ConfidenceBand.UNTRUSTED:
            return MemoryZone.NO_PERSIST
        
        if user_origin_verified and bundle.derived_confidence == ConfidenceBand.HIGH:
            return MemoryZone.GLOBAL
        
        if bundle.derived_confidence in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM):
            return MemoryZone.PROJECT
        
        if bundle.derived_confidence == ConfidenceBand.LOW:
            return MemoryZone.CANDIDATE
        
        return MemoryZone.NO_PERSIST
    
    def classify_fact_origin(
        self,
        bundle: EvidenceBundle,
        user_origin_verified: bool = False,
    ) -> FactOrigin:
        """Classify fact origin from bundle evidence.
        
        Pre-E59 heuristics:
        - user_origin_verified=True only if E59 capability confirms it
        - No prose/name-based inference
        """
        if bundle.derived_confidence == ConfidenceBand.UNTRUSTED:
            return FactOrigin.UNTRUSTED
        
        if user_origin_verified:
            return FactOrigin.EXPLICIT_USER_FACT
        
        if bundle.derived_confidence == ConfidenceBand.HIGH:
            return FactOrigin.EXTERNAL_SOURCE
        
        if bundle.derived_confidence == ConfidenceBand.MEDIUM:
            return FactOrigin.HIGH_PROBABILITY_INFERENCE
        
        return FactOrigin.LOW_CONFIDENCE_GUESS
    
    def produce_entry(
        self,
        statement: str,
        bundle: EvidenceBundle,
        user_origin_verified: bool = False,
    ) -> CognitionEntry:
        """Produce a memory candidate — never claims memory is written."""
        import hashlib
        zone = self.derive_memory_zone(bundle, user_origin_verified)
        origin = self.classify_fact_origin(bundle, user_origin_verified)
        
        entry_id = hashlib.sha256(
            f"COG:{statement}:{zone.value}:{bundle.bundle_id}".encode()
        ).hexdigest()[:12]
        
        entry = CognitionEntry(
            entry_id=entry_id,
            statement=statement,
            fact_origin=origin,
            memory_zone=zone,
            evidence_bundle_id=bundle.bundle_id,
            confidence=bundle.derived_confidence,
        )
        self._entries[entry_id] = entry
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[CognitionEntry]:
        return self._entries.get(entry_id)
    
    def _classify_from_confidence(self, confidence: ConfidenceBand,
                                    user_origin_verified: bool = False) -> FactOrigin:
        """Classify fact origin directly from confidence band."""
        if confidence == ConfidenceBand.UNTRUSTED:
            return FactOrigin.UNTRUSTED
        if user_origin_verified:
            return FactOrigin.EXPLICIT_USER_FACT
        if confidence == ConfidenceBand.HIGH:
            return FactOrigin.EXTERNAL_SOURCE
        if confidence == ConfidenceBand.MEDIUM:
            return FactOrigin.HIGH_PROBABILITY_INFERENCE
        return FactOrigin.LOW_CONFIDENCE_GUESS
    
    def _derive_zone_from_confidence(self, confidence: ConfidenceBand,
                                       user_origin_verified: bool = False) -> MemoryZone:
        """Derive memory zone directly from confidence band."""
        if confidence == ConfidenceBand.UNTRUSTED:
            return MemoryZone.NO_PERSIST
        if user_origin_verified and confidence == ConfidenceBand.HIGH:
            return MemoryZone.GLOBAL
        if confidence in (ConfidenceBand.HIGH, ConfidenceBand.MEDIUM):
            return MemoryZone.PROJECT
        if confidence == ConfidenceBand.LOW:
            return MemoryZone.CANDIDATE
        return MemoryZone.NO_PERSIST
