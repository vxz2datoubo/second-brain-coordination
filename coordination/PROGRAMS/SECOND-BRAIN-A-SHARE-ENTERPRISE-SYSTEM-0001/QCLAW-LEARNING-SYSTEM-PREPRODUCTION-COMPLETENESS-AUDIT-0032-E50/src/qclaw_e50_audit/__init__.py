"""qclaw_e50_audit — Learning-system preproduction completeness audit.

Audits the second-brain learning system across D1-D12 dimensions:
  D1 source ingestion / privacy / provenance
  D2 semantic reconstruction
  D3 atom taxonomy + epistemic separation
  D4 cross-source mastering
  D5 evidence verification
  D6 verified user-origin cognition
  D7 skill promotion + rollback
  D8 retrieval / reuse / correction round-trip
  D9 Codex candidate/formal promotion boundary
  D10 generalization / adversarial
  D11 determinism + CI
  D12 resource + rollback

Source policy: PUBLIC_SAFE_GENERALIZATION_ONLY.
No private/high-value user source ingestion.
No authoritative PROJECT/GLOBAL persistence.
No automatic formal skill/trading-rule promotion.
"""

from .source_policy import (
    SourcePolicy,
    SourceClass,
    PrivateSourceRefused,
    refuse_if_private,
)

from .ingestion import (
    SourceArtifact,
    SourceRefused,
    ingest_source,
    ingest_article,
    ingest_asr,
    ingest_chat,
    ingest_ocr,
    ingest_contradiction_pair,
    ingest_method,
)

from .corpus import (
    PublicSafeCorpus,
    CorpusFixture,
    ADVERSARIAL_FIXTURES,
    make_corpus,
)

from .cross_source import (
    SemanticObjectIdentity,
    CrossSourceMaster,
    canonical_id,
    CONTRADICTS,
    SUPERSEDES,
    DUPLICATE_OF,
    NEAR_DUPLICATE_OF,
)

from .cognition import (
    CognitionOrigin,
    CognitionMap,
    VerifiedUserOriginRequired,
    classify_cognition_origin,
)

from .skill_promotion import (
    SkillStage,
    SkillCandidate,
    PromotionReceipt,
    PromotionRefused,
    no_caller_authored_promotion,
)

from .retrieval import (
    CanonicalW3QueryPath,
    RetrievalResult,
    RetrievalRoundTrip,
)

from .codex_boundary import (
    CandidatePackageShape,
    CodexBoundaryGate,
    BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY,
)

from .audit_runner import (
    DimensionVerdict,
    EvidenceMatrix,
    CoverageEntry,
    CoverageReport,
    PostflightReceipt,
    Verdict,
    run_d1,
    run_d2,
    run_d3,
    run_d4,
    run_d5,
    run_d6,
    run_d7,
    run_d8,
    run_d9,
    run_d10,
    run_d11,
    run_d12,
    run_all_dimensions,
)

from .recommendation import (
    ReadinessRecommendation,
    compute_recommendation,
)

__all__ = [
    # source policy
    "SourcePolicy", "SourceClass", "PrivateSourceRefused", "refuse_if_private",
    # ingestion
    "SourceArtifact", "SourceRefused", "ingest_source",
    "ingest_article", "ingest_asr", "ingest_chat", "ingest_ocr",
    "ingest_contradiction_pair", "ingest_method",
    # corpus
    "PublicSafeCorpus", "CorpusFixture", "ADVERSARIAL_FIXTURES", "make_corpus",
    # cross_source
    "SemanticObjectIdentity", "CrossSourceMaster", "canonical_id",
    "CONTRADICTS", "SUPERSEDES", "DUPLICATE_OF", "NEAR_DUPLICATE_OF",
    # cognition
    "CognitionOrigin", "CognitionMap", "VerifiedUserOriginRequired",
    "classify_cognition_origin",
    # skill_promotion
    "SkillStage", "SkillCandidate", "PromotionReceipt", "PromotionRefused",
    "no_caller_authored_promotion",
    # retrieval
    "CanonicalW3QueryPath", "RetrievalResult", "RetrievalRoundTrip",
    # codex_boundary
    "CandidatePackageShape", "CodexBoundaryGate",
    "BLOCKED_PENDING_REAL_PRODUCTION_AUTHORITY",
    # audit_runner
    "DimensionVerdict", "EvidenceMatrix", "CoverageEntry", "CoverageReport",
    "PostflightReceipt", "Verdict",
    "run_d1", "run_d2", "run_d3", "run_d4", "run_d5", "run_d6",
    "run_d7", "run_d8", "run_d9", "run_d10", "run_d11", "run_d12",
    "run_all_dimensions",
    # recommendation
    "ReadinessRecommendation", "compute_recommendation",
]