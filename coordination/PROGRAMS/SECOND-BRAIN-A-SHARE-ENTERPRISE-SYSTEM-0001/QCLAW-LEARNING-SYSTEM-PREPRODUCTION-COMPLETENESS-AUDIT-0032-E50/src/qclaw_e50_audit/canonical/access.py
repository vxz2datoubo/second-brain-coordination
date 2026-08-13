"""Helper to access vendored canonical code from E50 audit modules.

The canonical vendored snapshot lives under qclaw_e50_audit/canonical/.
Some vendored modules have inter-package dependencies that the original
repo resolved via sys.path conventions. This module exposes a single
`setup_import_path()` function that E50 audit code calls once before
importing the canonical modules.
"""
import os
import sys


CANONICAL_ROOT = os.path.dirname(os.path.abspath(__file__))
PHASE3_PATH = os.path.join(CANONICAL_ROOT, "phase3")  # local_adapter + integrated_offline_memory
PHASE2_PATH = os.path.join(CANONICAL_ROOT, "phase2")  # offline_research
CODEX_E66_PATH = os.path.join(CANONICAL_ROOT, "codex_e66")  # e66_promotion


def setup_import_path():
    """Insert canonical package roots into sys.path so vendored imports work.

    The vendored snapshot uses absolute imports within phase3 (local_adapter,
    integrated_offline_memory) and across (offline_research). codex_e66 is
    its own package. To make all top-level imports work we put:

    - phase3/  -> exposes local_adapter, integrated_offline_memory as top-level
    - phase2/  -> exposes offline_research as top-level
    - canonical/ -> exposes codex_e66 as top-level

    The canonical code is read-only so this is just a path trick; no module
    duplication.
    """
    # Insert in this order so phase3 wins for local_adapter/integrated_offline_memory,
    # phase2 for offline_research, canonical for codex_e66.
    paths_in_order = [PHASE3_PATH, PHASE2_PATH, CANONICAL_ROOT]
    for p in paths_in_order:
        if p not in sys.path:
            sys.path.insert(0, p)
    return {
        "phase2_path": PHASE2_PATH,
        "phase3_path": PHASE3_PATH,
        "codex_e66_path": CODEX_E66_PATH,
        "canonical_root": CANONICAL_ROOT,
    }


def get_head_sha():
    """Return the SHA of origin/main that this snapshot was vendored from.

    Used by D11 evidence to bind the audit to the exact canonical head.
    """
    import subprocess
    SRC_REPO = os.environ.get(
        "E50_SOURCE_REPO",
        r"C:\Users\Administrator\.openclaw\workspace\coordination-canonical",
    )
    out = subprocess.check_output(
        ["git", "-C", SRC_REPO, "rev-parse", "origin/main"],
        stderr=subprocess.STDOUT)
    return out.decode("utf-8").strip()