"""Canonical fresh execution trust-gate entrypoint with compute-lane hardening."""
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
del _extension_path, _compat_path, _runtime_attestation_path
