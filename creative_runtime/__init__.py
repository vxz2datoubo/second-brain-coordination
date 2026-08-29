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
from .director import DirectorCompilation, QualityFinding, QualityReport, compile_director
from .knowledge import KnowledgeBridgeViolation, KnowledgeCandidate, KnowledgeReviewBridge

__all__ = [
    "CreativeArtifact",
    "CreativeEvent",
    "CreativeLedger",
    "DirectorCompilation",
    "DirectorBrief",
    "GenerationRequest",
    "GenerationResult",
    "GovernanceViolation",
    "LedgerViolation",
    "KnowledgeBridgeViolation",
    "KnowledgeCandidate",
    "KnowledgeReviewBridge",
    "PlayerAction",
    "QualityFinding",
    "QualityReport",
    "ShotPlan",
    "StoryBeat",
    "StoryState",
    "TaskGovernance",
    "canonical_json",
    "compile_director",
    "create_artifact",
    "load_task_governance",
]
