"""Offline-first building blocks for the governed creative runtime.

The package deliberately contains no provider, credential, network, or canonical
knowledge-store integration.  Those boundaries are checked before later slices
are allowed to add their own deterministic behavior.
"""

from .governance import GovernanceViolation, TaskGovernance, load_task_governance
from .contracts import (
    CreativeArtifact,
    CreativeEvent,
    DirectorBrief,
    GenerationRequest,
    GenerationResult,
    PlayerAction,
    ShotPlan,
    StoryBeat,
    StoryState,
    canonical_json,
)
from .ledger import CreativeLedger, LedgerViolation, create_artifact
from .director import DirectorCompilation, QualityFinding, QualityReport, VerifiedDirectorCompilation, compile_director, compile_verified_director
from .knowledge import KnowledgeBridgeViolation, KnowledgeCandidate, KnowledgeReviewBridge, VerifiedKnowledgeCandidate, correct_from_verified_timeline
from .generation import ExternalGenerationGuard, GenerationViolation, OfflineGenerationAdapter, adapter_for
from .provenance import ProvenanceViolation, SourceProvenance, require_reusable_source
from .continuity import (
    GraphBeat,
    GraphTransition,
    StoryGraph,
    TimelineEntry,
    TimelineViolation,
    VerifiedDirectorInput,
    default_story_graph,
    graph_for_initial_state,
    graph_for_ledger,
    replay_timeline,
    three_scene_story_graph,
    timeline_hash,
    verified_director_input,
)
from .understanding import (
    DriftAssessment,
    MetricAnchor,
    UnderstandingCard,
    UnderstandingMap,
    UnderstandingViolation,
    assess_anchor,
    bind_verified_timeline,
)
from .session import (
    LoadedV2Session,
    MigrationResult,
    SessionViolation,
    legacy_session_path,
    load_v2_session,
    migrate_legacy_session,
    v2_session_path,
)

__all__ = [
    "CreativeArtifact",
    "CreativeEvent",
    "CreativeLedger",
    "DirectorCompilation",
    "DirectorBrief",
    "DriftAssessment",
    "GenerationRequest",
    "GenerationResult",
    "GenerationViolation",
    "GraphBeat",
    "GraphTransition",
    "GovernanceViolation",
    "LedgerViolation",
    "LoadedV2Session",
    "KnowledgeBridgeViolation",
    "KnowledgeCandidate",
    "KnowledgeReviewBridge",
    "MetricAnchor",
    "MigrationResult",
    "ExternalGenerationGuard",
    "OfflineGenerationAdapter",
    "PlayerAction",
    "QualityFinding",
    "QualityReport",
    "ProvenanceViolation",
    "ShotPlan",
    "StoryBeat",
    "StoryGraph",
    "StoryState",
    "SourceProvenance",
    "SessionViolation",
    "TaskGovernance",
    "TimelineEntry",
    "TimelineViolation",
    "UnderstandingCard",
    "UnderstandingMap",
    "UnderstandingViolation",
    "VerifiedDirectorInput",
    "VerifiedDirectorCompilation",
    "VerifiedKnowledgeCandidate",
    "canonical_json",
    "adapter_for",
    "assess_anchor",
    "bind_verified_timeline",
    "compile_director",
    "compile_verified_director",
    "correct_from_verified_timeline",
    "create_artifact",
    "default_story_graph",
    "graph_for_initial_state",
    "graph_for_ledger",
    "require_reusable_source",
    "load_task_governance",
    "legacy_session_path",
    "load_v2_session",
    "migrate_legacy_session",
    "replay_timeline",
    "timeline_hash",
    "three_scene_story_graph",
    "verified_director_input",
    "v2_session_path",
]
