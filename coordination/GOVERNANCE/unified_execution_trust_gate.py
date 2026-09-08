"""Canonical fresh execution trust-gate entrypoint with compute and canonicalization hardening."""
from pathlib import Path as _BootstrapPath

_extension_path = _BootstrapPath(__file__).with_name(
    "unified_execution_trust_gate_compute_extension.py"
)
exec(
    compile(
        _extension_path.read_text(encoding="utf-8"),
        str(_extension_path),
        "exec",
    ),
    globals(),
    globals(),
)

_compat_path = Path(__file__).with_name(
    "unified_execution_trust_gate_process_compat.py"
)
exec(
    compile(
        _compat_path.read_text(encoding="utf-8"),
        str(_compat_path),
        "exec",
    ),
    globals(),
    globals(),
)

_runtime_attestation_path = Path(__file__).with_name(
    "unified_execution_runtime_model_attestation_extension.py"
)
exec(
    compile(
        _runtime_attestation_path.read_text(encoding="utf-8"),
        str(_runtime_attestation_path),
        "exec",
    ),
    globals(),
    globals(),
)

# Canonicalization-effect validation is defined once by the canonical validator module loaded as
# ``base`` by the trust-gate substrate. Re-export the same types/functions rather than creating a
# second issuer/type universe. These functions remain side-effect free: the protected carrier is
# responsible for fresh identity/capability evidence and for any separately authorized GitHub effect.
VerifiedCanonicalizerEvidence = base.VerifiedCanonicalizerEvidence
CanonicalizerAdmission = base.CanonicalizerAdmission
build_contributor_conflict_set = base.build_contributor_conflict_set
admit_canonicalizer = base.admit_canonicalizer
canonicalization_state_transition = base.canonicalization_state_transition
canonicalizer_failure_recovery = base.canonicalizer_failure_recovery
validate_pre_merge_effect_gate = base.validate_pre_merge_effect_gate
reconcile_merge_effect = base.reconcile_merge_effect
validate_pr615_prospective_adjudication = base.validate_pr615_prospective_adjudication
CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS = (
    base.CANONICALIZATION_EFFECT_CORE_HAS_GITHUB_SIDE_EFFECTS
)
CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY = (
    base.CANONICALIZATION_EFFECT_CORE_CAN_MINT_MERGE_AUTHORITY
)

del _extension_path, _compat_path, _runtime_attestation_path
