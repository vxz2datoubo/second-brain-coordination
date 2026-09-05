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
del _extension_path
