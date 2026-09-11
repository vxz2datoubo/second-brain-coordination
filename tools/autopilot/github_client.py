"""gh CLI 封装 —— Autopilot 与 GitHub 交互的底层。

所有 GitHub 操作通过已认证的 `gh` CLI 完成（本地最高权限），不在此模块内
硬编码 token。方法保持幂等、可重试，失败时抛 GhError 并携带 stderr。

注意：本模块只提供「机械动作原语」，不包含任何治理判断。merge / review 的
策略判断在上层 auto_merge / autopilot 里做。
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


class GhError(RuntimeError):
    """gh CLI 调用失败。"""


@dataclass
class PrInfo:
    number: int
    title: str
    head_ref: str
    base_ref: str
    head_sha: str
    state: str
    merged: bool
    draft: bool
    url: str


@dataclass
class CheckStatus:
    conclusion: Optional[str]
    status: str
    total: int
    passed: int
    failed: int


def _run(args: list[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["gh", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if check and proc.returncode != 0:
        raise GhError(f"gh {' '.join(args)} failed ({proc.returncode}): {proc.stderr.strip()}")
    return proc


def _json(args: list[str], cwd: Optional[Path] = None) -> Any:
    proc = _run([*args, "--json", ".*"], cwd=cwd) if False else _run(args, cwd=cwd)
    return json.loads(proc.stdout)


def auth_ok() -> bool:
    try:
        _run(["auth", "status"])
        return True
    except GhError:
        return False


def whoami() -> str:
    proc = _run(["api", "user", "--jq", ".login"])
    return proc.stdout.strip()


def fetch_default(cwd: Path, branch: str = "main") -> None:
    _run(["fetch", "origin", branch], cwd=cwd)


def merge_upstream(cwd: Path, branch: str = "main") -> None:
    """Fast-forward local branch to origin/<branch> (never overwrites dirty worktree)."""
    _run(["merge", "--ff-only", f"origin/{branch}"], cwd=cwd)


def current_sha(cwd: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise GhError(f"git rev-parse failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def worktree_dirty(cwd: Path) -> bool:
    proc = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    return proc.returncode == 0 and bool(proc.stdout.strip())


def create_branch(cwd: Path, name: str) -> None:
    _run(["checkout", "-b", name], cwd=cwd)


def list_local_branches(cwd: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "branch", "--format", "%(refname:short)"],
        cwd=str(cwd), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        raise GhError(f"git branch failed: {proc.stderr.strip()}")
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def switch_branch(cwd: Path, name: str) -> None:
    _run(["checkout", name], cwd=cwd)


def commit_all(cwd: Path, message: str) -> bool:
    """Stage + commit; returns False if nothing to commit."""
    if not worktree_dirty(cwd):
        return False
    _run(["add", "-A"], cwd=cwd)
    _run(["commit", "-m", message], cwd=cwd)
    return True


def push(cwd: Path, branch: str, force: bool = False) -> None:
    args = ["push", "-u", "origin", branch]
    if force:
        args.insert(1, "--force")
    _run(args, cwd=cwd)


def create_pr(cwd: Path, title: str, body: str, base: str, head: str, draft: bool = False) -> PrInfo:
    args = ["pr", "create", "--base", base, "--head", head, "--title", title, "--body", body]
    if draft:
        args.append("--draft")
    proc = _run(args, cwd=cwd)
    url = proc.stdout.strip()
    number = int(url.rstrip("/").split("/")[-1])
    return get_pr(cwd, number)


def get_pr(cwd: Path, number: int) -> PrInfo:
    data = _json([
        "pr", "view", str(number),
        "--json", "number,title,headRefName,baseRefName,headRefOid,state,isDraft,url",
    ], cwd=cwd)
    return PrInfo(
        number=int(data["number"]),
        title=str(data["title"]),
        head_ref=str(data["headRefName"]),
        base_ref=str(data["baseRefName"]),
        head_sha=str(data["headRefOid"]),
        state=str(data["state"]),
        merged=False,
        draft=bool(data.get("isDraft")),
        url=str(data["url"]),
    )


def list_open_prs(cwd: Path, head_prefix: str = "") -> list[PrInfo]:
    args = ["pr", "list", "--state", "open", "--limit", "100"]
    data = _json(args, cwd=cwd)
    out: list[PrInfo] = []
    for d in data:
        pr = PrInfo(
            number=int(d["number"]),
            title=str(d.get("title", "")),
            head_ref=str(d.get("headRefName", "")),
            base_ref=str(d.get("baseRefName", "main")),
            head_sha=str(d.get("headRefOid", "")),
            state=str(d.get("state", "")),
            merged=False,
            draft=bool(d.get("isDraft", False)),
            url=str(d.get("url", "")),
        )
        if not head_prefix or pr.head_ref.startswith(head_prefix):
            out.append(pr)
    return out


def pr_checks(cwd: Path, number: int) -> CheckStatus:
    proc = _run([
        "api", f"repos/{{repo}}/pulls/{number}/commits",
    ], cwd=cwd) if False else _run([
        "pr", "checks", str(number),
    ], cwd=cwd, check=False)
    # gh pr checks outputs a table; parse via api instead for reliability
    return _pr_checks_via_api(cwd, number)


def _pr_checks_via_api(cwd: Path, number: int) -> CheckStatus:
    repo = _run(["repo", "view", "--json", "nameWithOwner"], cwd=cwd)
    owner_repo = json.loads(repo.stdout)["nameWithOwner"]
    head = _run(["api", f"repos/{owner_repo}/pulls/{number}", "--jq", ".head.sha"], cwd=cwd)
    sha = head.stdout.strip()
    proc = _run([
        "api", f"repos/{owner_repo}/commits/{sha}/check-runs",
        "-H", "Accept: application/vnd.github+json",
        "-H", "X-GitHub-Api-Version: 2022-11-28",
        "--paginate",
    ], cwd=cwd)
    runs = json.loads(proc.stdout).get("check_runs", [])
    total = len(runs)
    passed = sum(1 for r in runs if r.get("conclusion") == "success")
    failed = sum(1 for r in runs if r.get("conclusion") in ("failure", "timed_out", "action_required"))
    pending = any(r.get("status") in ("queued", "in_progress") for r in runs)
    if failed:
        conclusion = "failure"
        status = "completed"
    elif pending or total == 0:
        conclusion = None
        status = "in_progress" if pending else "pending"
    else:
        conclusion = "success"
        status = "completed"
    return CheckStatus(conclusion=conclusion, status=status, total=total, passed=passed, failed=failed)


def pr_approve(cwd: Path, number: int, body: str = "") -> None:
    args = ["pr", "review", str(number), "--approve"]
    if body:
        args += ["--body", body]
    _run(args, cwd=cwd)


def pr_merge(cwd: Path, number: int, method: str = "merge", body: str = "") -> None:
    args = ["pr", "merge", str(number), f"--{method}"]
    if body:
        args += ["--body", body]
    _run(args, cwd=cwd)


def list_issues(cwd: Path, state: str = "open", labels: list[str] | None = None) -> list[dict[str, Any]]:
    args = ["issue", "list", "--state", state, "--limit", "200", "--json", "number,title,labels,state"]
    data = _json(args, cwd=cwd)
    if labels:
        wanted = set(labels)
        data = [d for d in data if wanted & {lbl.get("name", "") for lbl in d.get("labels", [])}]
    return data


def get_issue(cwd: Path, number: int) -> dict[str, Any]:
    return _json(["issue", "view", str(number), "--json", "number,title,body,state,labels,comments"], cwd=cwd)


def repo_owner_name(cwd: Path) -> str:
    repo = _run(["repo", "view", "--json", "nameWithOwner"], cwd=cwd)
    return json.loads(repo.stdout)["nameWithOwner"]
