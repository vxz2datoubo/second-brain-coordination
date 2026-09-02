"""Offline-first building blocks for the governed creative runtime.

The package deliberately contains no provider, credential, network, or canonical
knowledge-store integration.  Those boundaries are checked before later slices
are allowed to add their own deterministic behavior.
"""

from .governance import GovernanceViolation, TaskGovernance, load_task_governance
from .contracts import (
    CreativeArtifact,
    CreativeEvent,
    DirectorScriptSelection,
    DirectorBrief,
    GenerationRequest,
    GenerationResult,
    PlayerAction,
    ShotPlan,
    StoryBeat,
    StoryState,
    ScriptPackage,
    StyleProfile,
    canonical_json,
)
from .ledger import CreativeLedger, LedgerViolation, create_artifact
from .director import DirectorCompilation, QualityFinding, QualityReport, compile_director
from .knowledge import KnowledgeBridgeViolation, KnowledgeCandidate, KnowledgeReviewBridge
from .generation import ExternalGenerationGuard, GenerationViolation, OfflineGenerationAdapter, adapter_for
from .provenance import ProvenanceViolation, SourceProvenance, require_reusable_source
from .script_fixtures import approved_synthetic_script_packages
from .script_registry import (
    ScriptPackageRegistry,
    ScriptRegistryViolation,
    build_script_package,
    compute_package_hash,
    parse_script_package_json,
    style_profiles_v1,
)

__all__ = [
    "CreativeArtifact",
    "CreativeEvent",
    "CreativeLedger",
    "DirectorCompilation",
    "DirectorBrief",
    "DirectorScriptSelection",
    "GenerationRequest",
    "GenerationResult",
    "GenerationViolation",
    "GovernanceViolation",
    "LedgerViolation",
    "KnowledgeBridgeViolation",
    "KnowledgeCandidate",
    "KnowledgeReviewBridge",
    "ExternalGenerationGuard",
    "OfflineGenerationAdapter",
    "PlayerAction",
    "QualityFinding",
    "QualityReport",
    "ProvenanceViolation",
    "ShotPlan",
    "ScriptPackage",
    "ScriptPackageRegistry",
    "ScriptRegistryViolation",
    "StoryBeat",
    "StoryState",
    "StyleProfile",
    "SourceProvenance",
    "TaskGovernance",
    "canonical_json",
    "adapter_for",
    "approved_synthetic_script_packages",
    "build_script_package",
    "compile_director",
    "create_artifact",
    "compute_package_hash",
    "parse_script_package_json",
    "require_reusable_source",
    "load_task_governance",
    "style_profiles_v1",
]
