"""GitHub adapter — READ-ONLY.

Uses the `gh` CLI (already authenticated on this machine) with a strict
read-only command surface. No token ever reaches the browser: the BFF is the
credential boundary.

If gh is unavailable/unauthenticated, returns UNAVAILABLE rather than faking data.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timezone

from ..schemas import Freshness, Meta, SourceRef, TrustBadge


def gh_available() -> bool:
    return shutil.which("gh") is not None


def _gh(args: list[str], timeout: int = 20) -> tuple[bool, str]:
    if not gh_available():
        return False, "gh_cli_not_found"
    try:
        out = subprocess.run(
            ["gh", *args], capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        if out.returncode != 0:
            return False, (out.stderr or "gh command failed").strip()[:300]
        return True, out.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "gh_timeout"
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:300]


def get_default_branch_sha(repo: str) -> tuple[str | None, str | None]:
    """Return (sha, error). Real remote main head."""
    ok, out = _gh(["api", f"repos/{repo}/commits/main", "--jq", ".sha"])
    if ok and out:
        return out.strip(), None
    return None, out


def get_repo_meta(repo: str) -> tuple[dict | None, str | None]:
    ok, out = _gh(["repo", "view", repo, "--json",
                   "name,defaultBranchRef,pushedAt,isPrivate,viewerPermission"])
    if ok and out:
        try:
            return json.loads(out), None
        except json.JSONDecodeError:
            return None, "json_decode_error"
    return None, out


def list_open_issues(repo: str, limit: int = 30) -> tuple[list[dict] | None, str | None]:
    ok, out = _gh(["issue", "list", "--repo", repo, "--state", "open",
                   "--limit", str(limit), "--json",
                   "number,title,labels,updatedAt,url"])
    if ok:
        try:
            return json.loads(out), None
        except json.JSONDecodeError:
            return None, "json_decode_error"
    return None, out


def list_open_prs(repo: str, limit: int = 30) -> tuple[list[dict] | None, str | None]:
    ok, out = _gh(["pr", "list", "--repo", repo, "--state", "open",
                   "--limit", str(limit), "--json",
                   "number,title,headRefName,headRefOid,isDraft,updatedAt,url,mergeStateStatus"])
    if ok:
        try:
            return json.loads(out), None
        except json.JSONDecodeError:
            return None, "json_decode_error"
    return None, out


def main_protected(repo: str) -> tuple[bool | None, str | None]:
    ok, out = _gh(["api", f"repos/{repo}/branches/main", "--jq", ".protected"])
    if ok:
        return out.strip().lower() == "true", None
    return None, out


def remote_meta(sources: list[SourceRef], error: str | None = None) -> Meta:
    return Meta(
        freshness=Freshness.FRESH if error is None else Freshness.UNKNOWN,
        authority="GITHUB",
        trust=TrustBadge.CANONICAL if error is None else TrustBadge.UNKNOWN,
        sources=sources,
        projection_status="COMPLETE" if error is None else "UNAVAILABLE",
        warnings=[f"github: {error}"] if error else [],
    )
