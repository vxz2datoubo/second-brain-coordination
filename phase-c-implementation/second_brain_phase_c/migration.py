"""
Compatibility Migration Layer: Memory Palace old atom -> KnowledgeAtom.
Provides lossless, reversible migration from existing Memory Palace
atoms to the new KnowledgeAtom schema.
"""
from typing import Dict, Any, Optional, List, Tuple

from .models import (
    KnowledgeAtom, KnowledgeEpisode, AtomType, EpistemicRole,
    EvidenceQuality, FreshnessClass, AtomStatus, PrivacyClass,
    Scope, SourceRef, SourceType, CounterEvidenceRef, EvidenceStrength,
    _now_iso, _new_id,
)


class CompatibilityMigrator:
    LEGACY_TYPE_MAP = {
        "concept": AtomType.CONCEPT, "fact": AtomType.FACT_CLAIM,
        "claim": AtomType.AUTHOR_CLAIM, "memory": AtomType.USER_EVENT_REPORT,
        "preference": AtomType.USER_PREFERENCE, "goal": AtomType.USER_GOAL,
        "plan": AtomType.USER_PLAN, "decision": AtomType.USER_DECISION,
        "correction": AtomType.USER_CORRECTION, "evidence": AtomType.EVIDENCE,
        "mechanism": AtomType.MECHANISM, "method": AtomType.METHOD,
        "case": AtomType.CASE, "question": AtomType.OPEN_QUESTION,
        "unknown": AtomType.UNKNOWN,
    }
    LEGACY_ROLE_MAP = {
        "fact": EpistemicRole.SOURCE_FACT, "claim": EpistemicRole.SOURCE_CLAIM,
        "interpretation": EpistemicRole.SOURCE_INTERPRETATION,
        "opinion": EpistemicRole.SOURCE_VALUE_JUDGMENT,
        "user": EpistemicRole.USER_ASSERTION,
        "assistant": EpistemicRole.ASSISTANT_ANALYSIS,
        "inference": EpistemicRole.MODEL_INFERENCE,
    }
    LEGACY_STATUS_MAP = {
        "active": AtomStatus.ACTIVE, "candidate": AtomStatus.CANDIDATE,
        "superseded": AtomStatus.SUPERSEDED, "revoked": AtomStatus.REVOKED,
        "conflicted": AtomStatus.CONFLICTED, "unknown": AtomStatus.UNKNOWN,
    }
    LEGACY_FRESHNESS_MAP = {
        "transient": FreshnessClass.TRANSIENT,
        "short": FreshnessClass.SHORT_CYCLE,
        "medium": FreshnessClass.MEDIUM_CYCLE,
        "structural": FreshnessClass.STRUCTURAL,
    }

    def __init__(self):
        self._migration_log: List[Dict[str, str]] = []
        self._reverse_map: Dict[str, Dict[str, Any]] = {}

    def migrate_atom(self, legacy_atom, legacy_source=None):
        legacy_id = legacy_atom.get("id", legacy_atom.get("atom_id", ""))
        legacy_type = str(legacy_atom.get("type", "concept")).lower()
        atom_type = self.LEGACY_TYPE_MAP.get(legacy_type, AtomType.CONCEPT)
        legacy_role = str(legacy_atom.get("epistemic_role", legacy_atom.get("role", "fact"))).lower()
        epistemic_role = self.LEGACY_ROLE_MAP.get(legacy_role, EpistemicRole.UNKNOWN)
        legacy_status = str(legacy_atom.get("status", "candidate")).lower()
        current_status = self.LEGACY_STATUS_MAP.get(legacy_status, AtomStatus.CANDIDATE)
        legacy_freshness = str(legacy_atom.get("freshness", "unknown")).lower()
        freshness_class = self.LEGACY_FRESHNESS_MAP.get(legacy_freshness, FreshnessClass.UNKNOWN)
        scope = Scope(
            user_scope=legacy_atom.get("user_scope", "global"),
            project_scope=legacy_atom.get("project_scope"),
            privacy_class=PrivacyClass(legacy_atom.get("privacy_class", "PUBLIC").upper()),
        )
        source_refs = []
        if legacy_source:
            source_refs.append(SourceRef(
                episode_id=legacy_source.get("id", legacy_source.get("episode_id", "legacy")),
                span_locator=legacy_source.get("span", "full"),
                confidence=float(legacy_source.get("confidence", 1.0)),
            ))
        elif legacy_atom.get("source_id"):
            source_refs.append(SourceRef(
                episode_id=legacy_atom["source_id"],
                span_locator=legacy_atom.get("source_span", "full"),
            ))
        entities = legacy_atom.get("entities", legacy_atom.get("entity_ids", []))
        topic_tags = legacy_atom.get("tags", legacy_atom.get("topic_tags", []))
        counterevidence = []
        for ce in legacy_atom.get("counterevidence", []):
            if isinstance(ce, str):
                counterevidence.append(CounterEvidenceRef(atom_id=ce))
            elif isinstance(ce, dict):
                counterevidence.append(CounterEvidenceRef(
                    atom_id=ce.get("atom_id", ""),
                    evidence_strength=EvidenceStrength(ce.get("evidence_strength", "MODERATE")),
                ))
        new_atom = KnowledgeAtom(
            canonical_statement=legacy_atom.get("statement", legacy_atom.get("content", legacy_atom.get("text", ""))),
            atom_type=atom_type, entities=list(entities), topic_tags=list(topic_tags),
            epistemic_role=epistemic_role, source_refs=source_refs,
            evidence_quality=EvidenceQuality(legacy_atom.get("evidence_quality", "UNVERIFIED").upper()),
            confidence=float(legacy_atom.get("confidence", 0.5)), scope=scope,
            valid_from=legacy_atom.get("valid_from"), valid_to=legacy_atom.get("valid_to"),
            recorded_at=legacy_atom.get("created_at", legacy_atom.get("recorded_at", _now_iso())),
            freshness_class=freshness_class, current_status=current_status,
            assumptions=list(legacy_atom.get("assumptions", [])),
            conditions=list(legacy_atom.get("conditions", [])),
            exceptions=list(legacy_atom.get("exceptions", [])),
            counterevidence=counterevidence,
            invalidation_conditions=list(legacy_atom.get("invalidation_conditions", [])),
            lineage_head=bool(legacy_atom.get("lineage_head", True)),
            predecessor_atom_ids=list(legacy_atom.get("predecessors", [])),
            successor_atom_ids=list(legacy_atom.get("successors", [])),
            conflict_set_id=legacy_atom.get("conflict_set_id"),
            migrated_from_legacy=True, legacy_atom_ref=legacy_id,
        )
        self._reverse_map[new_atom.atom_id] = {
            "legacy_atom": legacy_atom, "legacy_source": legacy_source,
            "legacy_id": legacy_id, "migrated_at": _now_iso(),
        }
        self._migration_log.append({
            "legacy_id": legacy_id, "new_atom_id": new_atom.atom_id,
            "migrated_at": _now_iso(), "type_mapping": f"{legacy_type} -> {atom_type.value}",
        })
        return new_atom

    def migrate_episode(self, legacy_source):
        return KnowledgeEpisode(
            source_type=SourceType(legacy_source.get("type", "PARAGRAPH").upper()),
            source_pointer=legacy_source.get("pointer", legacy_source.get("url", "inline")),
            source_content_hash=legacy_source.get("content_hash", ""),
            source_span_or_locator=legacy_source.get("span", "full"),
            captured_at=legacy_source.get("captured_at", legacy_source.get("created_at", _now_iso())),
            user_scope=legacy_source.get("user_scope", "global"),
            project_scope=legacy_source.get("project_scope"),
            privacy_class=PrivacyClass(legacy_source.get("privacy_class", "PUBLIC").upper()),
            raw_content=legacy_source.get("content", legacy_source.get("raw_content", "")),
            content_language=legacy_source.get("language", "zh"),
        )

    def reverse_migrate(self, new_atom):
        if not new_atom.migrated_from_legacy:
            return None
        if new_atom.atom_id not in self._reverse_map:
            return None
        original = self._reverse_map[new_atom.atom_id]["legacy_atom"].copy()
        original["statement"] = new_atom.canonical_statement
        original["confidence"] = new_atom.confidence
        original["status"] = new_atom.current_status.value.lower()
        original["entities"] = new_atom.entities
        original["tags"] = new_atom.topic_tags
        return original

    def batch_migrate(self, legacy_atoms, legacy_sources=None):
        legacy_sources = legacy_sources or {}
        result = []
        for legacy in legacy_atoms:
            source_id = legacy.get("source_id", "")
            source = legacy_sources.get(source_id)
            result.append(self.migrate_atom(legacy, source))
        return result

    def get_migration_log(self):
        return list(self._migration_log)

    def get_migration_stats(self):
        type_mappings = {}
        for entry in self._migration_log:
            mapping = entry["type_mapping"]
            type_mappings[mapping] = type_mappings.get(mapping, 0) + 1
        return {
            "total_migrated": len(self._migration_log),
            "type_mappings": type_mappings,
            "reversible_count": len(self._reverse_map),
        }

    def verify_lossless(self, new_atom, legacy_atom):
        missing = []
        legacy_statement = legacy_atom.get("statement", legacy_atom.get("content", legacy_atom.get("text", "")))
        if legacy_statement and legacy_statement not in new_atom.canonical_statement:
            missing.append("statement/content")
        legacy_entities = set(legacy_atom.get("entities", legacy_atom.get("entity_ids", [])))
        if legacy_entities and not legacy_entities.issubset(set(new_atom.entities)):
            missing.append("entities")
        legacy_confidence = legacy_atom.get("confidence")
        if legacy_confidence is not None and abs(new_atom.confidence - float(legacy_confidence)) > 0.01:
            missing.append("confidence")
        if new_atom.legacy_atom_ref != legacy_atom.get("id", legacy_atom.get("atom_id", "")):
            missing.append("legacy_atom_ref")
        return len(missing) == 0, missing
