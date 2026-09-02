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
    DirectorBriefV2ContentSelection,
    DirectorBriefV2CompiledContent,
    GenerationRequest,
    GenerationResult,
    PlayerAction,
    ShotPlan,
    StoryBeat,
    StoryState,
    ScriptPackage,
    ScriptCatalogEntry,
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
from .script_catalog import (
    PersistentScriptCatalog,
    ScriptCatalogViolation,
    load_catalog,
    materialize_catalog,
    serialize_catalog,
)
from .director_v2 import (
    DirectorBriefV2Violation,
    MultiScriptDirectorCompiler,
    compile_director_brief_v2,
    inspect_director_brief_v2,
)
from .story_graph import (
    ChoiceOption,
    ConsequenceCoverage,
    ImmutableStoryGraph,
    MajorChoicePoint,
    StaticConsequence,
    StoryAct,
    StoryChapter,
    StoryGraphViolation,
    compile_consequence_coverage,
    validate_graph_for_package,
    validate_story_graph,
)
from .story_bibles import (
    CharacterBible,
    SceneBible,
    StoryBibleBundle,
    StoryBibleViolation,
    validate_story_bibles,
)
from .flagship_story_fixture import flagship_story_fixture

__all__ = [
    "CreativeArtifact",
    "CreativeEvent",
    "CreativeLedger",
    "DirectorCompilation",
    "DirectorBrief",
    "DirectorBriefV2ContentSelection",
    "DirectorBriefV2CompiledContent",
    "DirectorBriefV2Violation",
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
    "ScriptCatalogEntry",
    "ScriptCatalogViolation",
    "ScriptPackageRegistry",
    "ScriptRegistryViolation",
    "StoryBeat",
    "StoryState",
    "StyleProfile",
    "PersistentScriptCatalog",
    "MultiScriptDirectorCompiler",
    "SourceProvenance",
    "TaskGovernance",
    "canonical_json",
    "adapter_for",
    "approved_synthetic_script_packages",
    "build_script_package",
    "compile_director",
    "compile_director_brief_v2",
    "create_artifact",
    "compute_package_hash",
    "parse_script_package_json",
    "require_reusable_source",
    "load_task_governance",
    "load_catalog",
    "materialize_catalog",
    "inspect_director_brief_v2",
    "serialize_catalog",
    "style_profiles_v1",
    "ChoiceOption",
    "ConsequenceCoverage",
    "ImmutableStoryGraph",
    "MajorChoicePoint",
    "StaticConsequence",
    "StoryAct",
    "StoryChapter",
    "StoryGraphViolation",
    "CharacterBible",
    "SceneBible",
    "StoryBibleBundle",
    "StoryBibleViolation",
    "compile_consequence_coverage",
    "validate_graph_for_package",
    "validate_story_graph",
    "validate_story_bibles",
    "flagship_story_fixture",
]
