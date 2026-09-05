"""Protected Git transport for canonical trust-root reads.

This module deliberately ignores executor/user repository Git configuration when
reading the canonical control-plane remote. In particular, repo/global/system/env
`url.*.insteadOf` rewrites must not be able to redefine the trusted repository.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Callable

TRUSTED_CONTROL_PLANE_URL = "https://github.com/vxz2datoubo/second-brain-coordination.git"
TRUSTED_MAIN_REF = "refs/heads/main"


class TrustedTransportError(RuntimeError):
    pass


def _sanitized_env(home: Path) -> dict[str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("GIT_CONFIG_") or key in {
            "GIT_DIR",
            "GIT_WORK_TREE",
            "GIT_COMMON_DIR",
            "GIT_OBJECT_DIRECTORY",
            "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        }:
            env.pop(key, None)
    env["HOME"] = str(home)
    env["XDG_CONFIG_HOME"] = str(home / "xdg")
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _run_git(cwd: Path, *args: str, text: bool = True):
    cwd.mkdir(parents=True, exist_ok=True)
    home = cwd.parent / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / "xdg").mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
        env=_sanitized_env(home),
    )
    if proc.returncode != 0:
        stderr = proc.stderr if text else proc.stderr.decode("utf-8", "replace")
        raise TrustedTransportError(
            f"protected git read failed: {' '.join(args)}: {stderr.strip()}"
        )
    return proc.stdout


def _parse_ls_remote(output: str) -> str:
    fields = output.strip().split()
    if len(fields) < 2 or fields[1] != TRUSTED_MAIN_REF or not re.fullmatch(
        r"[0-9a-f]{40}", fields[0]
    ):
        raise TrustedTransportError("protected git read: invalid trusted main identity")
    return fields[0]


def remote_main_sha(_repo_path: str | Path | None = None) -> str:
    """Read canonical main in a fresh bridge-owned Git context."""
    with tempfile.TemporaryDirectory(prefix="uef-trust-root-") as raw:
        root = Path(raw)
        bare = root / "trust.git"
        bare.mkdir(parents=True, exist_ok=True)
        _run_git(bare, "init", "--bare", "--quiet")
        output = _run_git(
            bare, "ls-remote", TRUSTED_CONTROL_PLANE_URL, TRUSTED_MAIN_REF
        )
        return _parse_ls_remote(output)


def open_trusted_main(
    _repo_path: str | Path | None = None,
) -> tuple[str, Callable[[str], bytes]]:
    """Fetch canonical main into an isolated bare repo and return exact-SHA reader.

    The caller's repo path is intentionally ignored for trust-root transport so local
    `.git/config`, worktree config, global config, system config and inherited Git config
    environment cannot redirect the canonical URL.
    """
    temp = tempfile.TemporaryDirectory(prefix="uef-trust-root-")
    root = Path(temp.name)
    bare = root / "trust.git"
    bare.mkdir(parents=True, exist_ok=True)
    _run_git(bare, "init", "--bare", "--quiet")

    observed = _parse_ls_remote(
        _run_git(bare, "ls-remote", TRUSTED_CONTROL_PLANE_URL, TRUSTED_MAIN_REF)
    )
    _run_git(
        bare,
        "fetch",
        "--quiet",
        "--no-tags",
        TRUSTED_CONTROL_PLANE_URL,
        TRUSTED_MAIN_REF,
    )
    fetched = _run_git(bare, "rev-parse", "FETCH_HEAD").strip()
    if fetched != observed:
        temp.cleanup()
        raise TrustedTransportError(
            "protected git read: canonical main moved during isolated fetch"
        )

    def read(path: str) -> bytes:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise TrustedTransportError(f"protected git read: unsafe path {path}")
        proc = subprocess.run(
            ["git", "-C", str(bare), "show", f"{observed}:{path}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            check=False,
            env=_sanitized_env(root / "home"),
        )
        if proc.returncode != 0:
            raise TrustedTransportError(
                f"protected git read: cannot read canonical path {path}"
            )
        return proc.stdout

    # Keep the temporary bare repository alive as long as the reader is alive.
    setattr(read, "_trusted_transport_tempdir", temp)
    setattr(read, "_trusted_transport_bare_repo", bare)
    return observed, read
