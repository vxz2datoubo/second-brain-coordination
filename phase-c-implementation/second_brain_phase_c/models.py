"""
Data models for PHASE_C: KnowledgeEpisode, KnowledgeAtom, and supporting structures.
All models are dataclasses for simplicity and W3 compatibility.
Serialization to/from dict is provided for W3 integration.
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "") -> str:
    return f"{prefix}{uuid.uuid4()}" if prefix else str(uuid.uuid4())


# ─── Enums ───────────────────────────────────────────────────────────────────

class AtomType(str, Enum):
    CONCEPT = "CONCEPT"
    DEFINITION = "DEFINITION"
    FACT_CLAIM = "FACT_CLAIM"
    AUTHOR_CLAIM = "AUTHOR_CLAIM"
    USER_ASSERTION = "USER_ASSERTION"
    USER_PREFERENCE = "USER_PREFERENCE"
    USER_DECISION = "USER_DECISION"
    USER_CORRECTION = "USER_CORRECTION"
    USER_GOAL = "USER_GOAL"
    USER_PLAN = "USER_PLAN"
    USER_COMMITMENT = "USER_COMMITMENT"
    USER_EVENT_REPORT = "USER_EVENT_REPORT"
    OWNER_STANCE = "OWNER_STANCE"
    EVIDENCE = "EVIDENCE"
    MECHANISM = "MECHANISM"
    CAUSAL_CHAIN = "CAUSAL_CHAIN"
    CONDITION = "CONDITION"
    EXCEPTION = "EXCEPTION"
    NEGATION = "NEGATION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    ALTERNATIVE_EXPLANATION = "ALTERNATIVE_EXPLANATION"
    INDICATOR = "INDICATOR"
    METRIC = "METRIC"
    DATA_SOURCE = "DATA_SOURCE"
    METHOD = "METHOD"
    PROCEDURE = "PROCEDURE"
    DECISION_RULE = "DECISION_RULE"
    FAILURE_MODE = "FAILURE_MODE"
    INVALIDATION_CONDITION = "INVALIDATION_CONDITION"
    CASE = "CASE"
    ANALOGY = "ANALOGY"
    OPEN_QUESTION = "OPEN_QUESTION"
    UNKNOWN = "UNKNOWN"
    SKILL_CANDIDATE = "SKILL_CANDIDATE"


class EpistemicRole(str, Enum):
    SOURCE_FACT = "SOURCE_FACT"
    SOURCE_CLAIM = "SOURCE_CLAIM"
    SOURCE_INTERPRETATION = "SOURCE_INTERPRETATION"
    SOURCE_VALUE_JUDGMENT = "SOURCE_VALUE_JUDGMENT"
    USER_ASSERTION = "USER_ASSERTION"
    USER_PREFERENCE = "USER_PREFERENCE"
    USER_DECISION = "USER_DECISION"
    USER_CORRECTION = "USER_CORRECTION"
    OWNER_STANCE = "OWNER_STANCE"
    ASSISTANT_ANALYSIS = "ASSISTANT_ANALYSIS"
    ASSISTANT_HYPOTHESIS = "ASSISTANT_HYPOTHESIS"
    MODEL_INFERENCE = "MODEL_INFERENCE"
    UNKNOWN = "UNKNOWN"


class EvidenceQuality(str, Enum):
    DIRECT = "DIRECT"
    INFERRED = "INFERRED"
    ANECDOTAL = "ANECDOTAL"
    UNVERIFIED = "UNVERIFIED"


class FreshnessClass(str, Enum):
    TRANSIENT = "TRANSIENT"
    SHORT_CYCLE = "SHORT_CYCLE"
    MEDIUM_CYCLE = "MEDIUM_CYCLE"
    STRUCTURAL = "STRUCTURAL"
    UNKNOWN = "UNKNOWN"


class AtomStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    CONFLICTED = "CONFLICTED"
    UNKNOWN = "UNKNOWN"


class PrivacyClass(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    PRIVATE = "PRIVATE"


class SourceType(str, Enum):
    ARTICLE = "ARTICLE"
    PARAGRAPH = "PARAGRAPH"
    CONVERSATION = "CONVERSATION"
    RESEARCH = "RESEARCH"
    CASE = "CASE"
    RULE = "RULE"
    EXPERIENCE = "EXPERIENCE"
    CORRECTION = "CORRECTION"
    WEB_PAGE = "WEB_PAGE"
    BOOK = "BOOK"
    PAPER = "PAPER"


class IngestionStatus(str, Enum):
    CAPTURED = "CAPTURED"
    EXTRACTED = "EXTRACTED"
    ATOMIZED = "ATOMIZED"
    CLASSIFIED = "CLASSIFIED"
    RECONCILED = "RECONCILED"
    WRITTEN = "WRITTEN"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class ParaCategory(str, Enum):
    PROJECT = "PROJECT"
    AREA = "AREA"
    RESOURCE = "RESOURCE"
    ARCHIVE = "ARCHIVE"


class ReconciliationAction(str, Enum):
    NEW = "NEW"
    DUPLICATE = "DUPLICATE"
    MERGE = "MERGE"
    REFINE = "REFINE"
    SUPPORT = "SUPPORT"
    WEAKEN = "WEAKEN"
    CONTRADICT = "CONTRADICT"
    SUPERSEDE = "SUPERSEDE"
    REVOKE = "REVOKE"
    REVALIDATE = "REVALIDATE"
    RESOLVE_UNKNOWN = "RESOLVE_UNKNOWN"
    UNKNOWN = "UNKNOWN"
    ROLLBACK = "ROLLBACK"


class RelationType(str, Enum):
    IS_A = "IS_A"
    PART_OF = "PART_OF"
    INSTANCE_OF = "INSTANCE_OF"
    ALIAS_OF = "ALIAS_OF"
    DEFINES = "DEFINES"
    EXPLAINS = "EXPLAINS"
    EXEMPLIFIES = "EXEMPLIFIES"
    ANALOGOUS_TO = "ANALOGOUS_TO"
    CAUSES = "CAUSES"
    CONTRIBUTES_TO = "CONTRIBUTES_TO"
    MEDIATES = "MEDIATES"
    MODERATES = "MODERATES"
    ENABLES = "ENABLES"
    INHIBITS = "INHIBITS"
    FEEDBACK_TO = "FEEDBACK_TO"
    DEPENDS_ON = "DEPENDS_ON"
    SUPPORTS = "SUPPORTS"
    WEAKENS = "WEAKENS"
    CONTRADICTS = "CONTRADICTS"
    EVIDENCE_FOR = "EVIDENCE_FOR"
    COUNTEREVIDENCE_FOR = "COUNTEREVIDENCE_FOR"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    ASSUMES = "ASSUMES"
    INVALID_IF = "INVALID_IF"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    OVERLAPS = "OVERLAPS"
    SAME_PERIOD = "SAME_PERIOD"
    UPDATES = "UPDATES"
    REFINES = "REFINES"
    SUPERSEDES = "SUPERSEDES"
    REVOKES = "REVOKES"
    REVALIDATES = "REVALIDATES"
    APPLIES_TO = "APPLIES_TO"
    REQUIRES = "REQUIRES"
    FAILS_UNDER = "FAILS_UNDER"
    VALIDATED_BY = "VALIDATED_BY"
    PRODUCES = "PRODUCES"
    TRIGGERS = "TRIGGERS"
    USER_KNOWS = "USER_KNOWS"
    USER_INFERRED_KNOWS = "USER_INFERRED_KNOWS"
    REQUIRES_TEACHING_BRIDGE = "REQUIRES_TEACHING_BRIDGE"
    REQUIRES_SCAFFOLD = "REQUIRES_SCAFFOLD"
    USER_PREFERS = "USER_PREFERS"
    USER_REJECTS = "USER_REJECTS"
    OWNER_EVALUATES = "OWNER_EVALUATES"


class EvidenceStrength(str, Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    ANECDOTAL = "ANECDOTAL"


class ConflictType(str, Enum):
    FACTUAL = "FACTUAL"
    VALUE = "VALUE"
    SCOPE = "SCOPE"
    TEMPORAL = "TEMPORAL"
    DEFINITIONAL = "DEFINITIONAL"


class ConflictResolutionStatus(str, Enum):
    OPEN = "OPEN"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"


class RelationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"


class AuditExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class RawContentStorage(str, Enum):
    INLINE = "INLINE"
    EXTERNAL_REF = "EXTERNAL_REF"
    HASH_ONLY = "HASH_ONLY"


# ─── Sub-structures ──────────────────────────────────────────────────────────

@dataclass
class Scope:
    user_scope: str = "global"
    project_scope: Optional[str] = None
    privacy_class: PrivacyClass = PrivacyClass.PUBLIC

    def matches(self, other: "Scope") -> bool:
        if self.user_scope != other.user_scope:
            return False
        if self.project_scope != other.project_scope:
            return False
        if self.privacy_class == PrivacyClass.PRIVATE and other.privacy_class == PrivacyClass.PUBLIC:
            return False
        return True


@dataclass
class SourceRef:
    episode_id: str
    span_locator: str = "full"
    confidence: float = 1.0


@dataclass
class CounterEvidenceRef:
    atom_id: str
    evidence_strength: EvidenceStrength = EvidenceStrength.MODERATE
    relation_type: RelationType = RelationType.COUNTEREVIDENCE_FOR
    source_ref: Optional[str] = None
    noted_at: str = field(default_factory=_now_iso)


@dataclass
class OrganizationalLayer:
    para_category: ParaCategory = ParaCategory.RESOURCE
    para_project_id: Optional[str] = None
    para_area_id: Optional[str] = None
    para_moved_at: Optional[str] = None
    para_moved_by: Optional[str] = None
    para_archive_reason: Optional[str] = None


@dataclass
class BoldSpan:
    span_id: str = field(default_factory=lambda: _new_id("bs_"))
    text: str = ""
    rationale: str = ""


@dataclass
class HighlightSpan:
    span_id: str = field(default_factory=lambda: _new_id("hs_"))
    text: str = ""
    parent_bold_span: Optional[str] = None


@dataclass
class RemixRef:
    output_type: str = ""
    output_ref: str = ""


@dataclass
class DistillationLayers:
    layer0_source_span_ref: str = ""
    layer1_full_note: Optional[str] = None
    layer2_bold_spans: List[BoldSpan] = field(default_factory=list)
    layer3_highlight_spans: List[HighlightSpan] = field(default_factory=list)
    layer4_executive_summary: Optional[str] = None
    layer5_remix_refs: List[RemixRef] = field(default_factory=list)
    distillation_progress: int = 0
    last_distilled_at: Optional[str] = None
    distilled_by: Optional[str] = None


@dataclass
class ZettelkastenRole:
    note_type: str = "PERMANENT"
    fleeting_expires_at: Optional[str] = None
    literature_source_ref: Optional[str] = None
    permanent_atomicity_check: str = "NOT_CHECKED"
    permanent_self_contained: Optional[bool] = None
    luhmann_branch_id: Optional[str] = None
    link_discovery_status: str = "PENDING"


@dataclass
class CognitiveMapping:
    known_said: List[str] = field(default_factory=list)
    known_unsaid_inferred: List[str] = field(default_factory=list)
    unknown_but_accessible: List[str] = field(default_factory=list)
    unknown_requires_scaffolding: List[str] = field(default_factory=list)


@dataclass
class HumanAnnotation:
    annotation_id: str = field(default_factory=lambda: _new_id("ha_"))
    target_atom_id: str = ""
    target_field: str = ""
    annotation_type: str = "ADDITION"
    content: str = ""
    created_at: str = field(default_factory=_now_iso)
    created_by: str = "USER"
    applied_to_canonical: bool = False
    merge_requested_at: Optional[str] = None


# ─── Main Models ─────────────────────────────────────────────────────────────

@dataclass
class KnowledgeEpisode:
    episode_id: str = field(default_factory=lambda: _new_id("ep_"))
    source_type: SourceType = SourceType.PARAGRAPH
    source_pointer: str = "inline"
    source_content_hash: str = ""
    source_span_or_locator: str = "full"
    captured_at: str = field(default_factory=_now_iso)
    published_at_if_known: Optional[str] = None
    available_at_if_decision_relevant: Optional[str] = None
    user_scope: str = "global"
    project_scope: Optional[str] = None
    privacy_class: PrivacyClass = PrivacyClass.PUBLIC
    license_or_publication_basis: Optional[str] = None
    source_agent_or_author: Optional[str] = None
    raw_content: str = ""
    raw_content_storage: RawContentStorage = RawContentStorage.INLINE
    raw_content_external_ref: Optional[str] = None
    content_language: str = "zh"
    derived_atom_ids: List[str] = field(default_factory=list)
    ingestion_status: IngestionStatus = IngestionStatus.CAPTURED
    ingestion_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["source_type"] = self.source_type.value if hasattr(self.source_type, 'value') else self.source_type
        d["privacy_class"] = self.privacy_class.value if hasattr(self.privacy_class, 'value') else self.privacy_class
        d["ingestion_status"] = self.ingestion_status.value if hasattr(self.ingestion_status, 'value') else self.ingestion_status
        d["raw_content_storage"] = self.raw_content_storage.value if hasattr(self.raw_content_storage, 'value') else self.raw_content_storage
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeEpisode":
        d = dict(d)
        d["source_type"] = SourceType(d.get("source_type", "PARAGRAPH"))
        d["privacy_class"] = PrivacyClass(d.get("privacy_class", "PUBLIC"))
        d["ingestion_status"] = IngestionStatus(d.get("ingestion_status", "CAPTURED"))
        d["raw_content_storage"] = RawContentStorage(d.get("raw_content_storage", "INLINE"))
        return cls(**d)


@dataclass
class KnowledgeAtom:
    atom_id: str = field(default_factory=lambda: _new_id("ka_"))
    canonical_statement: str = ""
    statement_language: str = "zh"
    atom_type: AtomType = AtomType.CONCEPT
    entities: List[str] = field(default_factory=list)
    topic_tags: List[str] = field(default_factory=list)
    epistemic_role: EpistemicRole = EpistemicRole.UNKNOWN
    source_refs: List[SourceRef] = field(default_factory=list)
    evidence_quality: EvidenceQuality = EvidenceQuality.UNVERIFIED
    confidence: float = 0.5
    scope: Scope = field(default_factory=Scope)
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    recorded_at: str = field(default_factory=_now_iso)
    freshness_class: FreshnessClass = FreshnessClass.UNKNOWN
    current_status: AtomStatus = AtomStatus.CANDIDATE
    assumptions: List[str] = field(default_factory=list)
    conditions: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    counterevidence: List[CounterEvidenceRef] = field(default_factory=list)
    invalidation_conditions: List[str] = field(default_factory=list)
    validation_method: Optional[str] = None
    cognitive_mapping_relevance: Optional[CognitiveMapping] = None
    organizational_layer: Optional[OrganizationalLayer] = None
    distillation_layers: Optional[DistillationLayers] = None
    zettelkasten_role: Optional[ZettelkastenRole] = None
    lineage_head: bool = True
    predecessor_atom_ids: List[str] = field(default_factory=list)
    successor_atom_ids: List[str] = field(default_factory=list)
    conflict_set_id: Optional[str] = None
    relation_ids: List[str] = field(default_factory=list)
    last_reconciled_at: Optional[str] = None
    last_reconciliation_action: Optional[str] = None
    last_reconciliation_audit_id: Optional[str] = None
    reconciliation_evidence: str = ""
    migrated_from_legacy: bool = False
    legacy_atom_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["atom_type"] = self.atom_type.value
        d["epistemic_role"] = self.epistemic_role.value
        d["evidence_quality"] = self.evidence_quality.value
        d["freshness_class"] = self.freshness_class.value
        d["current_status"] = self.current_status.value
        d["scope"] = {
            "user_scope": self.scope.user_scope,
            "project_scope": self.scope.project_scope,
            "privacy_class": self.scope.privacy_class.value,
        }
        d["counterevidence"] = [
            {
                "atom_id": ce.atom_id,
                "evidence_strength": ce.evidence_strength.value,
                "relation_type": ce.relation_type.value,
                "source_ref": ce.source_ref,
                "noted_at": ce.noted_at,
            }
            for ce in self.counterevidence
        ]
        d["source_refs"] = [asdict(sr) for sr in self.source_refs]
        if self.organizational_layer:
            d["organizational_layer"]["para_category"] = self.organizational_layer.para_category.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "KnowledgeAtom":
        d = dict(d)
        d["atom_type"] = AtomType(d.get("atom_type", "CONCEPT"))
        d["epistemic_role"] = EpistemicRole(d.get("epistemic_role", "UNKNOWN"))
        d["evidence_quality"] = EvidenceQuality(d.get("evidence_quality", "UNVERIFIED"))
        d["freshness_class"] = FreshnessClass(d.get("freshness_class", "UNKNOWN"))
        d["current_status"] = AtomStatus(d.get("current_status", "CANDIDATE"))
        scope_data = d.pop("scope", {})
        d["scope"] = Scope(
            user_scope=scope_data.get("user_scope", "global"),
            project_scope=scope_data.get("project_scope"),
            privacy_class=PrivacyClass(scope_data.get("privacy_class", "PUBLIC")),
        )
        d["source_refs"] = [SourceRef(**sr) for sr in d.get("source_refs", [])]
        d["counterevidence"] = [
            CounterEvidenceRef(
                atom_id=ce["atom_id"],
                evidence_strength=EvidenceStrength(ce.get("evidence_strength", "MODERATE")),
                relation_type=RelationType(ce.get("relation_type", "COUNTEREVIDENCE_FOR")),
                source_ref=ce.get("source_ref"),
                noted_at=ce.get("noted_at", _now_iso()),
            )
            for ce in d.get("counterevidence", [])
        ]
        ol = d.get("organizational_layer")
        if ol:
            d["organizational_layer"] = OrganizationalLayer(
                para_category=ParaCategory(ol.get("para_category", "RESOURCE")),
                para_project_id=ol.get("para_project_id"),
                para_area_id=ol.get("para_area_id"),
                para_moved_at=ol.get("para_moved_at"),
                para_moved_by=ol.get("para_moved_by"),
                para_archive_reason=ol.get("para_archive_reason"),
            )
        dl = d.get("distillation_layers")
        if dl:
            d["distillation_layers"] = DistillationLayers(
                layer0_source_span_ref=dl.get("layer0_source_span_ref", ""),
                layer1_full_note=dl.get("layer1_full_note"),
                layer2_bold_spans=[BoldSpan(**bs) for bs in dl.get("layer2_bold_spans", [])],
                layer3_highlight_spans=[HighlightSpan(**hs) for hs in dl.get("layer3_highlight_spans", [])],
                layer4_executive_summary=dl.get("layer4_executive_summary"),
                layer5_remix_refs=[RemixRef(**rr) for rr in dl.get("layer5_remix_refs", [])],
                distillation_progress=dl.get("distillation_progress", 0),
                last_distilled_at=dl.get("last_distilled_at"),
                distilled_by=dl.get("distilled_by"),
            )
        cm = d.get("cognitive_mapping_relevance")
        if cm:
            d["cognitive_mapping_relevance"] = CognitiveMapping(**cm)
        zr = d.get("zettelkasten_role")
        if zr:
            d["zettelkasten_role"] = ZettelkastenRole(**zr)
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        d = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**d)

    def is_expired(self, at: Optional[str] = None) -> bool:
        if not self.valid_to:
            return False
        check_time = at or _now_iso()
        return self.valid_to < check_time

    def is_current(self) -> bool:
        return (
            self.lineage_head
            and self.current_status not in (AtomStatus.REVOKED, AtomStatus.SUPERSEDED)
            and not self.is_expired()
        )
