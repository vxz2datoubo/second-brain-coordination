"""E42 Q4 — Evidence-Derived Cognition & Memory Routing"""
import enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

class CognitionLayer(enum.Enum):
    KNOWN_AND_STATED = "known_and_stated"
    KNOWN_BUT_UNSTATED = "known_but_unstated"
    UNKNOWN_BUT_READABLE = "unknown_but_readable"
    UNKNOWN_AND_NEEDS_LAYERING = "unknown_and_needs_layering"

class InferenceQuality(enum.Enum):
    EXPLICIT_USER_FACT = "explicit_user_fact"
    HIGH_PROBABILITY_INFERENCE = "high_probability_inference"
    LOW_CONFIDENCE_GUESS = "low_confidence_guess"

class MemoryZone(enum.Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    UNPERSISTED = "unpersisted"

@dataclass(frozen=True)
class CognitionEntry:
    entry_id: str
    subject: str
    layer: CognitionLayer
    quality: InferenceQuality
    content: str
    evidence_ids: Tuple[str, ...]
    memory_zone: MemoryZone
    source_document_id: Optional[str] = None
    evaluator_id: Optional[str] = None

class CognitionEngine:
    def __init__(self, engine_id: str = "E42_COGNITION_V1"):
        self._engine_id = engine_id

    def classify_layer(self, is_stated: bool, is_known: bool, is_readable: bool) -> CognitionLayer:
        if is_stated and is_known:
            return CognitionLayer.KNOWN_AND_STATED
        if is_known and not is_stated:
            return CognitionLayer.KNOWN_BUT_UNSTATED
        if is_readable:
            return CognitionLayer.UNKNOWN_BUT_READABLE
        return CognitionLayer.UNKNOWN_AND_NEEDS_LAYERING

    def classify_quality(self, has_user_origin_evidence: bool,
                         has_corroboration: bool,
                         has_direct_evidence: bool) -> InferenceQuality:
        if has_user_origin_evidence and has_corroboration and has_direct_evidence:
            return InferenceQuality.EXPLICIT_USER_FACT
        if has_direct_evidence and has_corroboration:
            return InferenceQuality.HIGH_PROBABILITY_INFERENCE
        return InferenceQuality.LOW_CONFIDENCE_GUESS

    def create(self, entry_id: str, subject: str, content: str,
               is_stated: bool, is_known: bool, is_readable: bool,
               has_user_origin_evidence: bool, has_corroboration: bool,
               has_direct_evidence: bool,
               evidence_ids: Tuple[str, ...],
               source_document_id: Optional[str] = None,
               evaluator_id: Optional[str] = None) -> CognitionEntry:
        layer = self.classify_layer(is_stated, is_known, is_readable)
        quality = self.classify_quality(has_user_origin_evidence, has_corroboration, has_direct_evidence)
        zone = self._derive_memory_zone(layer, quality, evidence_ids)
        return CognitionEntry(
            entry_id=entry_id, subject=subject, layer=layer,
            quality=quality, content=content, evidence_ids=evidence_ids,
            memory_zone=zone, source_document_id=source_document_id,
            evaluator_id=evaluator_id,
        )

    def _derive_memory_zone(self, layer: CognitionLayer,
                            quality: InferenceQuality,
                            evidence_ids: Tuple[str, ...]) -> MemoryZone:
        # HIGH confidence + evidence → global or project
        if quality == InferenceQuality.EXPLICIT_USER_FACT and len(evidence_ids) >= 1:
            return MemoryZone.GLOBAL
        if quality == InferenceQuality.HIGH_PROBABILITY_INFERENCE and evidence_ids:
            return MemoryZone.PROJECT
        if quality == InferenceQuality.HIGH_PROBABILITY_INFERENCE:
            return MemoryZone.CANDIDATE
        return MemoryZone.UNPERSISTED

    def validate(self, entry: CognitionEntry) -> List[str]:
        violations = []
        if entry.memory_zone == MemoryZone.GLOBAL:
            if entry.quality != InferenceQuality.EXPLICIT_USER_FACT:
                violations.append(f"GLOBAL memory requires EXPLICIT_USER_FACT quality, got {entry.quality.value}")
            if not entry.evidence_ids:
                violations.append("GLOBAL memory requires evidence_ids")
        if entry.memory_zone == MemoryZone.PROJECT:
            if entry.quality == InferenceQuality.LOW_CONFIDENCE_GUESS:
                violations.append("PROJECT memory cannot store LOW_CONFIDENCE_GUESS")
        return violations
