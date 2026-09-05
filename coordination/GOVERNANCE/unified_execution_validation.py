"""Canonical unified execution validation entrypoint.

The pre-R185 validator body is preserved as an implementation substrate and executed into this
module's namespace. R185 compute-lane hardening is then layered in the same namespace so there
remains one public validator authority and existing monkey-patch based trust tests keep working.
"""
from pathlib import Path as _BootstrapPath

_extension_path = _BootstrapPath(__file__).with_name("unified_execution_compute_lane_extension.py")
exec(compile(_extension_path.read_text(encoding="utf-8"), str(_extension_path), "exec"), globals(), globals())
del _extension_path
