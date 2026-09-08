"""Canonical unified execution validation entrypoint.

The pre-R185 validator body is preserved as an implementation substrate and executed into this
module's namespace. R185 compute-lane hardening remains in that canonical namespace for backward
compatibility. Issue #619 canonicalization-effect validation is imported into an isolated module
namespace and only its explicit public contracts are re-exported, preventing private helper-name
collisions from mutating legacy validator semantics.
"""
import importlib.util as _bootstrap_importlib_util
from pathlib import Path as _BootstrapPath
import sys as _bootstrap_sys

# Capture both paths before executing the legacy/compute extension. That extension intentionally
# executes into this module's globals and may delete bootstrap helper names such as _BootstrapPath.
_compute_bootstrap_path = str(
    _BootstrapPath(__file__).with_name("unified_execution_compute_lane_extension.py")
)
_canonicalization_bootstrap_path = str(
    _BootstrapPath(__file__).with_name("unified_execution_canonicalization_extension.py")
)

exec(
    compile(
        _BootstrapPath(_compute_bootstrap_path).read_text(encoding="utf-8"),
        _compute_bootstrap_path,
        "exec",
    ),
    globals(),
    globals(),
)

# Do not rely on _BootstrapPath after the compute extension executes. Load the canonicalization
# module from the pre-captured string path into an isolated namespace.
_canonicalization_spec = _bootstrap_importlib_util.spec_from_file_location(
    "unified_execution_canonicalization_extension",
    _canonicalization_bootstrap_path,
)
if _canonicalization_spec is None or _canonicalization_spec.loader is None:
    raise ImportError("unable to load canonicalization effect-isolation extension")
_canonicalization_ext = _bootstrap_importlib_util.module_from_spec(_canonicalization_spec)
_bootstrap_sys.modules.setdefault(_canonicalization_spec.name, _canonicalization_ext)
_canonicalization_spec.loader.exec_module(_canonicalization_ext)

# Make all public canonicalization validators raise the canonical validator's existing error type
# without executing the extension into this module's globals.
_canonicalization_ext.ExecutionContractError = ExecutionContractError

VerifiedCanonicalizerEvidence = _canonicalization_ext.VerifiedCanonicalizerEvidence
CanonicalizerAdmission = _canonicalization_ext.CanonicalizerAdmission
CANONICALIZATION_STATES = _canonicalization_ext.CANONICALIZATION_STATES
CANONICALIZATION_FAILURE_STATES = _canonicalization_ext.CANONICALIZATION_FAILURE_STATES
CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS = (
    _canonicalization_ext.CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS
)
CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY = (
    _canonicalization_ext.CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY
)
build_contributor_conflict_set = _canonicalization_ext.build_contributor_conflict_set
admit_canonicalizer = _canonicalization_ext.admit_canonicalizer
canonicalization_state_transition = _canonicalization_ext.canonicalization_state_transition
canonicalizer_failure_recovery = _canonicalization_ext.canonicalizer_failure_recovery
validate_pre_merge_effect_gate = _canonicalization_ext.validate_pre_merge_effect_gate
reconcile_merge_effect = _canonicalization_ext.reconcile_merge_effect
validate_pr615_prospective_adjudication = _canonicalization_ext.validate_pr615_prospective_adjudication

# Avoid brittle ``del`` cleanup across exec-layered modules. These names are private bootstrap
# implementation details and carry no authority.
globals().pop("_canonicalization_spec", None)
globals().pop("_canonicalization_ext", None)
globals().pop("_bootstrap_importlib_util", None)
globals().pop("_bootstrap_sys", None)
globals().pop("_compute_bootstrap_path", None)
globals().pop("_canonicalization_bootstrap_path", None)
