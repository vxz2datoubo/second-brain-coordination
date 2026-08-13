"""Authoritative audit access (E50 R3).

R3 mandatory (from GPT review id 4922729153):
- Audit authoritative repository modules/paths DIRECTLY from the checked-out
  tree. Copied snapshots (the old src/qclaw_e50_audit/canonical/**) cannot
  earn canonical PASS credit and are treated as NON_AUTHORITY_FROZEN_FIXTURE.
- Bind exact audited commit/ref PLUS exact source file/blob SHA for each
  canonical dependency group.
- No hard-coded local Windows clone paths in E50 runtime / D11 / D12. CI must
  operate from checked-out repository state and provider metadata only.

Strategy:
- Walk up from this file to the repository root (directory containing `.git`).
- Add the authoritative `src/` roots to `sys.path` so the real canonical
  modules (integrated_offline_memory, local_adapter, offline_research,
  e66_promotion) are imported from the checked-out tree — no copies.
- Bind the exact HEAD commit (via `git rev-parse HEAD`, with a `.git`-file
  fallback) and exact git blob SHAs (computed with the deterministic
  `git hash-object` algorithm — `sha1(b"blob <len>\\0" + data)`), which needs
  no external git binary and is identical across Python 3.11/3.13 and OSes.
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path


def _repo_root() -> Path:
    here = Path(__file__).resolve().parent  # .../src/qclaw_e50_audit
    for parent in here.parents:
        if (parent / ".git").exists():
            return parent
        # Some checkouts use a bare .git file (worktree / CI). Accept a
        # directory that has both a .git file AND the coordination marker.
        if (parent / ".git").is_file() and (parent / "coordination").is_dir():
            return parent
        # Fallback structural marker: canonical coordination tree.
        if (parent / "coordination" / "ACTIVE-QCLAW-TASK.yaml").exists():
            return parent
    raise RuntimeError("could not locate repository root from audit package")


REPO_ROOT = _repo_root()
_PROG = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001"

# Authoritative src roots (top-level packages they expose).
PHASE3_SRC = REPO_ROOT / _PROG / "PHASE-3-INTEGRATED-OFFLINE-MEMORY" / "src"
LOCAL_ADAPTER_SRC = REPO_ROOT / _PROG / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src"
PHASE2_SRC = REPO_ROOT / _PROG / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src"
CODEX_E66_SRC = REPO_ROOT / _PROG / "CODEX-E66" / "src"

SRC_ROOTS: list[Path] = [
    PHASE3_SRC,          # integrated_offline_memory (W3 MemoryStore/retrieval/...)
    LOCAL_ADAPTER_SRC,   # local_adapter (contracts)
    PHASE2_SRC,          # offline_research (engine; replay_bridge dependency)
    CODEX_E66_SRC,       # e66_promotion (top-level module)
]

# Canonical dependency groups -> key files (relative to REPO_ROOT) for exact
# blob-SHA binding. Each is a real authoritative source file on canonical main.
CANONICAL_GROUPS: dict[str, list[str]] = {
    "phase3_integrated_offline_memory": [
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/memory_store.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/retrieval.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/learning_packet.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/conversation_memory.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/canonical.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/contracts.py",
        f"{_PROG}/PHASE-3-INTEGRATED-OFFLINE-MEMORY/src/integrated_offline_memory/private_candidate_ingestion.py",
    ],
    "phase3_local_adapter": [
        f"{_PROG}/PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION/src/local_adapter/contracts.py",
    ],
    "phase2_offline_research": [
        f"{_PROG}/PHASE-2-OFFLINE-VERTICAL-SLICE/src/offline_research/engine.py",
    ],
    "codex_e66_promotion": [
        f"{_PROG}/CODEX-E66/src/e66_promotion.py",
    ],
}


def setup_import_path() -> dict[str, str]:
    """Insert authoritative src roots into sys.path (no copies, no hard-coded
    absolute paths). Returns the resolved root map for evidence/diagnostics."""
    for root in SRC_ROOTS:
        s = str(root)
        if s not in sys.path:
            sys.path.insert(0, s)
    return {
        "phase3_src": str(PHASE3_SRC),
        "local_adapter_src": str(LOCAL_ADAPTER_SRC),
        "phase2_src": str(PHASE2_SRC),
        "codex_e66_src": str(CODEX_E66_SRC),
        "repo_root": str(REPO_ROOT),
    }


def git_blob_sha(path: Path) -> str:
    """Deterministic git blob SHA (== `git hash-object`). No git binary needed."""
    data = path.read_bytes()
    header = b"blob " + str(len(data)).encode("ascii") + b"\x00"
    return hashlib.sha1(header + data).hexdigest()


def get_head_sha() -> str:
    """Exact HEAD commit SHA. Prefers `git rev-parse HEAD` (CI checkout has
    git on PATH); falls back to reading .git/HEAD + refs/packed-refs, which
    needs no git binary and no hard-coded path."""
    # 1) git on PATH (Linux CI, dev machines)
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(REPO_ROOT), capture_output=True, timeout=20,
        )
        sha = out.stdout.decode("utf-8", "replace").strip()
        if out.returncode == 0 and len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
            return sha
    except Exception:
        pass

    # 2) .git/HEAD (direct SHA or symbolic ref)
    try:
        dotgit = REPO_ROOT / ".git"
        head_file = dotgit / "HEAD"
        content = head_file.read_text(encoding="utf-8", errors="replace").strip()
        if content.startswith("ref:"):
            ref = content.split(":", 1)[1].strip()
            ref_path = dotgit / ref
            if ref_path.exists():
                sha = ref_path.read_text(encoding="utf-8", errors="replace").strip()
                if len(sha) == 40:
                    return sha
            packed = dotgit / "packed-refs"
            if packed.exists():
                for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line.startswith("#"):
                        continue
                    if line.endswith(" " + ref):
                        sha = line.split()[0]
                        if len(sha) == 40:
                            return sha
        elif len(content) == 40 and all(c in "0123456789abcdef" for c in content):
            return content
    except Exception:
        pass

    return "UNKNOWN"


def canonical_ref_bindings() -> dict:
    """Exact ref + per-file blob SHA binding for every canonical group.

    Returns a deterministically-ordered dict suitable for direct JSON
    serialization and cross-version (3.11 vs 3.13) comparison."""
    bindings = {
        "audited_head_sha": get_head_sha(),
        "audited_head_source": "git rev-parse HEAD (checked-out repository tree)",
        "groups": {},
    }
    for group in sorted(CANONICAL_GROUPS):
        files = {}
        for rel in CANONICAL_GROUPS[group]:
            p = REPO_ROOT / rel
            if p.exists():
                files[rel] = git_blob_sha(p)
            else:
                files[rel] = "MISSING"
        bindings["groups"][group] = {
            "files": files,
        }
    return bindings
