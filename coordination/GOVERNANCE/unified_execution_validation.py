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

_extension_path = _BootstrapPath(__file__).with_name("unified_execution_compute_lane_extension.py")
exec(compile(_extension_path.read_text(encoding="utf-8"), str(_extension_path), "exec"), globals(), globals())

_canonicalization_extension_path = _BootstrapPath(__file__).with_name(
    "unified_execution_canonicalization_extension.py"
)
_canonicalization_spec = _bootstrap_importlib_util.spec_from_file_location(
    "unified_execution_canonicalization_extension",
    _canonicalization_extension_path,
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

del (
    _extension_path,
    _canonicalization_extension_path,
    _canonicalization_spec,
    _canonicalization_ext,
    _bootstrap_importlib_util,
    _bootstrap_sys,
)
