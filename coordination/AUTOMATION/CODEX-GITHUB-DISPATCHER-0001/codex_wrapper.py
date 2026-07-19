"""
CODEX-GITHUB-DISPATCHER-0001 — Codex CLI Wrapper (UTF-8 Integrity Fix 0009)
Fixed-prompt wrapper. Phase 1: read-only tasks only.
UTF-8 policy: strict decode — illegal bytes → CodexOutputIntegrityError → BLOCKED.
Empty output with exit_code=0 also raises CodexOutputIntegrityError.
"""
import subprocess
import os
import signal
import sys
from pathlib import Path

CODEX_CMD = str(
    Path(os.environ.get("USERPROFILE", ""))
    / ".workbuddy"
    / "binaries"
    / "node"
    / "versions"
    / "22.22.2"
    / "codex.cmd"
)
MAX_RUNTIME_SECONDS = 900  # 15 minutes

# Cache for dynamic version detection
_cached_codex_version = None


def get_codex_version() -> str:
    """Dynamically detect Codex CLI version. Cached after first call."""
    global _cached_codex_version
    if _cached_codex_version is not None:
        return _cached_codex_version
    try:
        result = subprocess.run([CODEX_CMD, "--version"], capture_output=True, timeout=15,
                                encoding="utf-8", errors="replace")
        out = result.stdout.strip()
        if "codex-cli" in out:
            _cached_codex_version = out.split()[-1] if out.split() else out
        else:
            _cached_codex_version = out
    except Exception:
        _cached_codex_version = "unknown"
    return _cached_codex_version


CODEX_VERSION = get_codex_version()  # Dynamic, not hardcoded


class CodexError(Exception):
    pass


class CodexTimeout(CodexError):
    pass


class CodexOutputIntegrityError(CodexError):
    """Output contains illegal UTF-8 bytes, is empty, truncated, or corrupt.
    Raised when output cannot be decoded as strict UTF-8, or when exit_code=0
    but stdout+stderr is empty. The dispatcher must NOT report COMPLETED when
    this is raised — it writes BLOCKED instead."""
    pass


def build_prompt(task_id: str, mode: str, repo: str, issue_or_pr: str,
                 workspace_alias: str, instruction_location: str | None = None,
                 execution_profile: str = "read-only") -> str:
    """Build the fixed wrapper prompt for Codex, profile-aware."""
    profile_label = f"{execution_profile.upper()}" if execution_profile != "read-only" else "READ-ONLY"
    lines = [
        f"You are executing task `{task_id}` dispatched via GitHub.",
        f"Mode: {mode}",
        f"Execution profile: {profile_label}",
        f"Repository: {repo}",
        f"Issue/PR: {issue_or_pr}",
        f"Workspace alias: {workspace_alias}",
        f"",
        f"CRITICAL RULES:",
    ]
    if execution_profile == "read-only":
        lines += [
            f"1. This is a READ-ONLY task. Do NOT create, modify, or delete any files.",
            f"2. Do NOT write to any file, database, or configuration.",
            f"3. Do NOT execute git commit, git push, git stash, git reset, or git checkout.",
            f"4. Do NOT install software, create services, or modify system settings.",
        ]
    elif execution_profile == "workspace-write":
        lines += [
            f"1. You may modify files within this workspace ONLY. Do NOT write outside it.",
            f"2. You may commit changes but must NOT force-push, rewrite history, or merge.",
            f"3. Do NOT execute git push --force, git reset --hard, or destructive operations.",
            f"4. Do NOT touch git config, remotes, hooks, or the .git directory directly.",
        ]
    lines += [
        f"5. Do NOT access production credentials, API keys, or financial data.",
        f"6. Do NOT access real trading interfaces, accounts, or order systems.",
        f"7. Output your findings as plain text — do not write .md files.",
        f"",
        f"TASK: Read all dispatch instructions from the GitHub issue/PR at the URL below.",
    ]
    if instruction_location:
        lines.append(f"Primary instruction location: {instruction_location}")
    else:
        lines.append(f"Primary instruction location: https://github.com/{repo}/issues/{issue_or_pr}")
    lines.extend([
        "",
        "After reading the full instructions from GitHub:",
        "1. Execute the requested read-only analysis in this workspace.",
        "2. Report your findings clearly in your response.",
        "3. Include: what you read, what you found, any recommendations.",
        "4. End with: CODEX_TASK_COMPLETED: <brief status>",
    ])
    return "\n".join(lines)


def run_codex(prompt: str, cwd: str, timeout: int = MAX_RUNTIME_SECONDS,
              execution_profile: str = "read-only") -> tuple[str, int]:
    """Run codex exec with explicit UTF-8 encoding. Returns (output, exit_code).
    Raises CodexOutputIntegrityError if exit_code=0 but output is empty or corrupt.
    
    execution_profile: 'read-only' or 'workspace-write'.
    read-only → sandbox_mode=read-only, sandbox_permissions=[read-only]
    workspace-write → sandbox_mode=workspace-write, sandbox_permissions=[write-file]"""
    env = os.environ.copy()
    cmd = [
        CODEX_CMD, "exec",
    ]
    if execution_profile == "read-only":
        cmd += ["-c", "sandbox_mode=read-only",
                "-c", 'sandbox_permissions=["read-only"]']
    elif execution_profile == "workspace-write":
        cmd += ["-c", "sandbox_mode=workspace-write",
                "-c", 'sandbox_permissions=["write-file","read-only"]']
    else:
        cmd += ["-c", "sandbox_mode=read-only",
                "-c", 'sandbox_permissions=["read-only"]']
    cmd += ["-C", cwd, prompt]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        try:
            stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise CodexTimeout(f"Codex task timed out after {timeout}s")

        # Decode with strict UTF-8. Illegal bytes → CodexOutputIntegrityError.
        # Policy: NEVER silently replace or skip bad bytes; the dispatcher
        # must write BLOCKED instead of falsely reporting COMPLETED.
        try:
            stdout_str = stdout_bytes.decode("utf-8") if stdout_bytes else ""
        except UnicodeDecodeError as e:
            raise CodexOutputIntegrityError(f"stdout contains illegal UTF-8 bytes: {e}")
        try:
            stderr_str = stderr_bytes.decode("utf-8") if stderr_bytes else ""
        except UnicodeDecodeError as e:
            raise CodexOutputIntegrityError(f"stderr contains illegal UTF-8 bytes: {e}")

        output = stdout_str + "\n" + stderr_str
        output_stripped = output.strip()

        # Integrity check: exit_code=0 but empty output = FAIL, not COMPLETED
        if proc.returncode == 0 and not output_stripped:
            raise CodexOutputIntegrityError("exit_code=0 but output is empty — refusing to report COMPLETED")

        return output_stripped, proc.returncode

    except FileNotFoundError:
        raise CodexError(f"Codex CLI not found at {CODEX_CMD}")
    except (CodexTimeout, CodexOutputIntegrityError):
        raise
    except Exception as e:
        raise CodexError(f"Codex execution failed: {e}")
