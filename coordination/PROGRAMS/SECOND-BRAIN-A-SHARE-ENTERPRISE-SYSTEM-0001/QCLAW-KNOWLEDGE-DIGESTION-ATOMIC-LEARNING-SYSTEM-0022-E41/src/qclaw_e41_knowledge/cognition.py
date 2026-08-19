"""E41 Q4 — User Cognition Mapping

Represent known-and-stated, known-but-unstated, unknown-but-readable,
unknown-and-needs-layering.
Separate explicit user facts from high-probability inference and low-confidence guess.
Define what may enter global memory, project memory, candidate zone or remain unpersisted.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class CognitionLayer(str, Enum):
    KNOWN_AND_STATED = "known_and_stated"
    KNOWN_BUT_UNSTATED = "known_but_unstated"
    UNKNOWN_BUT_READABLE = "unknown_but_readable"
    UNKNOWN_AND_NEEDS_LAYERING = "unknown_and_needs_layering"


class InferenceQuality(str, Enum):
    EXPLICIT_USER_FACT = "explicit_user_fact"
    HIGH_PROBABILITY_INFERENCE = "high_probability_inference"
    LOW_CONFIDENCE_GUESS = "low_confidence_guess"


class MemoryZone(str, Enum):
    GLOBAL = "global"
    PROJECT = "project"
    CANDIDATE = "candidate"
    UNPERSISTED = "unpersisted"


@dataclass(frozen=True)
class CognitionEntry:
    """A single cognition mapping entry."""
    entry_id: str
    subject: str
    layer: CognitionLayer
    quality: InferenceQuality
    content: str
    memory_zone: MemoryZone
    supporting_evidence: List[str] = field(default_factory=list)
    caveat: str = ""


def classify_layer(is_stated: bool, is_known: bool, is_readable: bool) -> CognitionLayer:
    """Classify a piece of knowledge into the appropriate cognition layer."""
    if is_stated and is_known:
        return CognitionLayer.KNOWN_AND_STATED
    if not is_stated and is_known:
        return CognitionLayer.KNOWN_BUT_UNSTATED
    if not is_known and is_readable:
        return CognitionLayer.UNKNOWN_BUT_READABLE
    return CognitionLayer.UNKNOWN_AND_NEEDS_LAYERING


def classify_quality(has_direct_evidence: bool, has_corroboration: bool, 
                     source_is_user: bool) -> InferenceQuality:
    """Classify the quality of an inference."""
    if source_is_user and has_direct_evidence:
        return InferenceQuality.EXPLICIT_USER_FACT
    if has_direct_evidence and has_corroboration:
        return InferenceQuality.HIGH_PROBABILITY_INFERENCE
    return InferenceQuality.LOW_CONFIDENCE_GUESS


def route_to_memory(entry: CognitionEntry) -> MemoryZone:
    """Determine memory destination based on cognition layer and quality."""
    if entry.quality == InferenceQuality.EXPLICIT_USER_FACT:
        if entry.layer in (CognitionLayer.KNOWN_AND_STATED, CognitionLayer.KNOWN_BUT_UNSTATED):
            return MemoryZone.GLOBAL
        return MemoryZone.PROJECT
    if entry.quality == InferenceQuality.HIGH_PROBABILITY_INFERENCE:
        return MemoryZone.CANDIDATE
    return MemoryZone.UNPERSISTED


def validate_memory_route(entry: CognitionEntry) -> List[str]:
    """Validate that memory routing is correct. Returns violations."""
    violations = []
    if entry.quality == InferenceQuality.LOW_CONFIDENCE_GUESS and entry.memory_zone == MemoryZone.GLOBAL:
        violations.append("low-confidence guess routed to GLOBAL memory")
    if entry.layer == CognitionLayer.UNKNOWN_AND_NEEDS_LAYERING and entry.memory_zone == MemoryZone.GLOBAL:
        violations.append("unknown-needs-layering routed to GLOBAL memory")
    if not entry.supporting_evidence and entry.memory_zone in (MemoryZone.GLOBAL, MemoryZone.PROJECT):
        violations.append(f"no supporting evidence for {entry.memory_zone} routing")
    return violations
