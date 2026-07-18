"""
CODEX-GITHUB-DISPATCHER-0001 — Codex CLI Wrapper
Fixed-prompt wrapper. Phase 1: read-only tasks only.
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
CODEX_VERSION = "0.141.0"
MAX_RUNTIME_SECONDS = 900  # 15 minutes


class CodexError(Exception):
    pass


class CodexTimeout(CodexError):
    pass


def build_prompt(task_id: str, mode: str, repo: str, issue_or_pr: str,
                 workspace_alias: str, instruction_location: str | None = None) -> str:
    """Build the fixed wrapper prompt for Codex."""
    lines = [
        f"You are executing task `{task_id}` dispatched via GitHub.",
        f"Mode: {mode}",
        f"Repository: {repo}",
        f"Issue/PR: {issue_or_pr}",
        f"Workspace alias: {workspace_alias}",
        f"",
        f"CRITICAL RULES:",
        f"1. This is a READ-ONLY task. Do NOT create, modify, or delete any files.",
        f"2. Do NOT write to any file, database, or configuration.",
        f"3. Do NOT execute git commit, git push, git stash, git reset, or git checkout.",
        f"4. Do NOT install software, create services, or modify system settings.",
        f"5. Do NOT access production credentials, API keys, or financial data.",
        f"6. Read only: read files from the workspace and GitHub to complete your task.",
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


def run_codex(prompt: str, cwd: str, timeout: int = MAX_RUNTIME_SECONDS) -> tuple[str, int]:
    """Run codex exec with the given prompt. Returns (output, exit_code)."""
    env = os.environ.copy()
    # Override sandbox to read-only
    cmd = [
        CODEX_CMD, "exec",
        "-c", "sandbox_mode=read-only",
        "-c", 'sandbox_permissions=["read-only"]',
        "-C", cwd,
        prompt,
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            # Kill the whole process tree
            if sys.platform == "win32":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
            raise CodexTimeout(f"Codex task timed out after {timeout}s")
        output = (stdout or "") + "\n" + (stderr or "")
        return output.strip(), proc.returncode
    except FileNotFoundError:
        raise CodexError(f"Codex CLI not found at {CODEX_CMD}")
    except Exception as e:
        raise CodexError(f"Codex execution failed: {e}")
