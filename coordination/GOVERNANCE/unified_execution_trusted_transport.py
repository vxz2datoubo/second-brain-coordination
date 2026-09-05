"""Protected Git transport for canonical trust-root reads.

The canonical control-plane trust root must not depend on caller repository config,
inherited Git/environment configuration, Git templates, or caller PATH lookup. Every
protected operation is executed with one bridge-selected absolute Git executable identity
and a minimal bridge-owned environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from typing import Callable

TRUSTED_CONTROL_PLANE_URL = "https://github.com/vxz2datoubo/second-brain-coordination.git"
TRUSTED_MAIN_REF = "refs/heads/main"

_ALLOWED_INIT_LOCAL_CONFIG_KEYS = {
    "core.repositoryformatversion",
    "core.filemode",
    "core.bare",
    "core.logallrefupdates",
    "core.ignorecase",
    "core.precomposeunicode",
    "core.symlinks",
    "extensions.objectformat",
    "extensions.refstorage",
}


class TrustedTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrustedGitExecutable:
    path: Path
    sha256: str
    provenance: str


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _posix_git_candidates() -> list[tuple[Path, str]]:
    # Deliberately do not consult PATH, HOME, package-manager environment variables,
    # aliases or shell initialization. These locations are OS-owned on supported
    # Linux/macOS hosts; absence fails closed rather than falling back to caller PATH.
    if sys.platform == "darwin":
        return [(Path("/usr/bin/git"), "OS_FIXED_PATH_MACOS")]
    return [
        (Path("/usr/bin/git"), "OS_FIXED_PATH_POSIX"),
        (Path("/bin/git"), "OS_FIXED_PATH_POSIX"),
    ]


def _windows_git_candidates() -> list[tuple[Path, str]]:
    """Resolve Git for Windows from HKLM, never from PATH or caller env."""
    candidates: list[tuple[Path, str]] = []
    try:
        import winreg  # type: ignore
    except ImportError:
        return candidates

    registry_keys = (
        r"SOFTWARE\GitForWindows",
        r"SOFTWARE\WOW6432Node\GitForWindows",
    )
    for key_name in registry_keys:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_name) as key:
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
        except OSError:
            continue
        root = Path(str(install_path))
        candidates.extend(
            [
                (root / "cmd" / "git.exe", "HKLM_GITFORWINDOWS_INSTALLPATH"),
                (root / "bin" / "git.exe", "HKLM_GITFORWINDOWS_INSTALLPATH"),
            ]
        )
    return candidates


def _assert_posix_path_not_world_writable(path: Path) -> None:
    if os.name == "nt":
        return
    for candidate in (path, path.parent):
        try:
            mode = candidate.stat().st_mode
        except OSError as exc:
            raise TrustedTransportError(
                f"protected git executable stat failed: {candidate}"
            ) from exc
        if mode & stat.S_IWOTH:
            raise TrustedTransportError(
                f"protected git executable path is world-writable: {candidate}"
            )


def _resolve_trusted_git_executable() -> TrustedGitExecutable:
    candidates = (
        _windows_git_candidates() if os.name == "nt" else _posix_git_candidates()
    )
    for candidate, provenance in candidates:
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if not resolved.is_absolute() or not resolved.is_file():
            continue
        _assert_posix_path_not_world_writable(resolved)
        return TrustedGitExecutable(
            path=resolved,
            sha256=_hash_file(resolved),
            provenance=provenance,
        )
    raise TrustedTransportError(
        "protected git read: no bridge-trusted Git executable identity available"
    )


def _assert_trusted_git_identity(identity: TrustedGitExecutable) -> None:
    try:
        resolved = identity.path.resolve(strict=True)
    except OSError as exc:
        raise TrustedTransportError(
            "protected git read: trusted Git executable disappeared"
        ) from exc
    if resolved != identity.path or not resolved.is_file():
        raise TrustedTransportError(
            "protected git read: trusted Git executable identity changed"
        )
    _assert_posix_path_not_world_writable(resolved)
    if _hash_file(resolved) != identity.sha256:
        raise TrustedTransportError(
            "protected git read: trusted Git executable digest changed"
        )


def _windows_system_root() -> Path | None:
    if os.name != "nt":
        return None
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(32768)
        length = ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if not length or length >= len(buffer):
            return None
        return Path(buffer.value)
    except Exception:
        return None


def _bridge_owned_path(identity: TrustedGitExecutable) -> str:
    """Return a non-caller-derived PATH for helpers needed by trusted Git."""
    if os.name == "nt":
        root = _windows_system_root()
        if root is None:
            raise TrustedTransportError(
                "protected git read: cannot resolve trusted Windows system directory"
            )
        entries = [identity.path.parent, root / "System32", root]
    else:
        entries = [identity.path.parent, Path("/usr/bin"), Path("/bin")]
    unique: list[str] = []
    for entry in entries:
        value = str(entry)
        if value not in unique:
            unique.append(value)
    return os.pathsep.join(unique)


def _sanitized_env(
    home: Path,
    template_dir: Path | None = None,
    identity: TrustedGitExecutable | None = None,
) -> dict[str, str]:
    """Build a minimal allowlisted environment for protected Git subprocesses.

    Nothing is copied from ``os.environ``. This excludes caller PATH, LD_*/DYLD_*,
    proxy/config helper variables, GIT_*, shell startup state and future unclassified
    execution-affecting variables by default.
    """
    git_identity = identity or _resolve_trusted_git_executable()
    _assert_trusted_git_identity(git_identity)

    home.mkdir(parents=True, exist_ok=True)
    (home / "xdg").mkdir(parents=True, exist_ok=True)
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    template = template_dir or (home / "empty-git-template")
    template.mkdir(parents=True, exist_ok=True)

    env = {
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / "xdg"),
        "PATH": _bridge_owned_path(git_identity),
        "TMPDIR": str(home / "tmp"),
        "TMP": str(home / "tmp"),
        "TEMP": str(home / "tmp"),
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TEMPLATE_DIR": str(template),
        "GIT_TERMINAL_PROMPT": "0",
    }
    if os.name == "nt":
        root = _windows_system_root()
        if root is None:
            raise TrustedTransportError(
                "protected git read: cannot resolve trusted Windows system directory"
            )
        env.update(
            {
                "SYSTEMROOT": str(root),
                "WINDIR": str(root),
                "COMSPEC": str(root / "System32" / "cmd.exe"),
            }
        )
    return env


def _run_git(
    cwd: Path,
    *args: str,
    text: bool = True,
    identity: TrustedGitExecutable | None = None,
):
    cwd.mkdir(parents=True, exist_ok=True)
    root = cwd.parent
    home = root / "home"
    template = root / "empty-git-template"
    git_identity = identity or _resolve_trusted_git_executable()
    _assert_trusted_git_identity(git_identity)

    proc = subprocess.run(
        [str(git_identity.path), "-C", str(cwd), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
        env=_sanitized_env(home, template, git_identity),
    )
    _assert_trusted_git_identity(git_identity)
    if proc.returncode != 0:
        stderr = proc.stderr if text else proc.stderr.decode("utf-8", "replace")
        raise TrustedTransportError(
            f"protected git read failed: {' '.join(args)}: {stderr.strip()}"
        )
    return proc.stdout


def _assert_bridge_owned_local_config(
    bare: Path, identity: TrustedGitExecutable
) -> None:
    output = _run_git(
        bare,
        "config",
        "--local",
        "--name-only",
        "--list",
        identity=identity,
    )
    keys = {line.strip().lower() for line in output.splitlines() if line.strip()}
    unexpected = sorted(keys - _ALLOWED_INIT_LOCAL_CONFIG_KEYS)
    if unexpected:
        raise TrustedTransportError(
            "protected git read: trust repo contains non bridge-owned local config: "
            + ", ".join(unexpected)
        )


def _init_bare_trust_repo(root: Path, identity: TrustedGitExecutable) -> Path:
    bare = root / "trust.git"
    bare.mkdir(parents=True, exist_ok=True)
    template = root / "empty-git-template"
    template.mkdir(parents=True, exist_ok=True)

    _run_git(
        bare,
        "init",
        "--bare",
        "--quiet",
        f"--template={template}",
        identity=identity,
    )
    _assert_bridge_owned_local_config(bare, identity)
    return bare


def _parse_ls_remote(output: str) -> str:
    fields = output.strip().split()
    if len(fields) < 2 or fields[1] != TRUSTED_MAIN_REF or not re.fullmatch(
        r"[0-9a-f]{40}", fields[0]
    ):
        raise TrustedTransportError("protected git read: invalid trusted main identity")
    return fields[0]


def remote_main_sha(_repo_path: str | Path | None = None) -> str:
    """Read canonical main using one absolute, digest-attested Git identity."""
    identity = _resolve_trusted_git_executable()
    with tempfile.TemporaryDirectory(prefix="uef-trust-root-") as raw:
        root = Path(raw)
        bare = _init_bare_trust_repo(root, identity)
        output = _run_git(
            bare,
            "ls-remote",
            TRUSTED_CONTROL_PLANE_URL,
            TRUSTED_MAIN_REF,
            identity=identity,
        )
        _assert_bridge_owned_local_config(bare, identity)
        return _parse_ls_remote(output)


def open_trusted_main(
    _repo_path: str | Path | None = None,
) -> tuple[str, Callable[[str], bytes]]:
    """Fetch canonical main into an isolated repo and return an exact-SHA reader."""
    identity = _resolve_trusted_git_executable()
    temp = tempfile.TemporaryDirectory(prefix="uef-trust-root-")
    root = Path(temp.name)
    bare = _init_bare_trust_repo(root, identity)

    observed = _parse_ls_remote(
        _run_git(
            bare,
            "ls-remote",
            TRUSTED_CONTROL_PLANE_URL,
            TRUSTED_MAIN_REF,
            identity=identity,
        )
    )
    _run_git(
        bare,
        "fetch",
        "--quiet",
        "--no-tags",
        TRUSTED_CONTROL_PLANE_URL,
        TRUSTED_MAIN_REF,
        identity=identity,
    )
    fetched = _run_git(
        bare, "rev-parse", "FETCH_HEAD", identity=identity
    ).strip()
    if fetched != observed:
        temp.cleanup()
        raise TrustedTransportError(
            "protected git read: canonical main moved during isolated fetch"
        )

    _assert_bridge_owned_local_config(bare, identity)

    def read(path: str) -> bytes:
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise TrustedTransportError(f"protected git read: unsafe path {path}")
        return _run_git(
            bare,
            "show",
            f"{observed}:{path}",
            text=False,
            identity=identity,
        )

    setattr(read, "_trusted_transport_tempdir", temp)
    setattr(read, "_trusted_transport_bare_repo", bare)
    setattr(read, "_trusted_git_executable", str(identity.path))
    setattr(read, "_trusted_git_sha256", identity.sha256)
    setattr(read, "_trusted_git_provenance", identity.provenance)
    return observed, read
