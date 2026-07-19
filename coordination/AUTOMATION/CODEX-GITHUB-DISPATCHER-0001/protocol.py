"""
CODEX-GITHUB-DISPATCHER-0001 — GitHub Protocol (Pagination Fix 0005)
Per-issue cursor discovery + Link header pagination + safety caps.
"""
import os
import re
import requests
import subprocess
from datetime import datetime, timezone

TARGET_REPO = "vxz2datoubo/second-brain-coordination"
API_BASE = "https://api.github.com"
DISPATCH_LABEL = "codex-dispatch"
MAX_PAGES_PER_ISSUE = 10       # Safety cap
MAX_PAGES_LABELED_ISSUES = 5   # Safety cap for issue listing
MAX_PAGE_SIZE = 100


def _get_token() -> str:
    result = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True,
    )
    for line in result.stdout.split("\n"):
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("Cannot get GitHub token from git credential manager")


def _headers(token: str, etag: str | None = None) -> dict:
    h = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if etag:
        h["If-None-Match"] = etag
    return h


def _parse_link_header(link_str: str | None) -> dict[str, str]:
    """Parse RFC 5988 Link header. Returns {'next': url, ...}."""
    if not link_str:
        return {}
    links = {}
    for part in link_str.split(","):
        m = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', part.strip())
        if m:
            links[m.group(2)] = m.group(1)
    return links


# ---- Per-Issue Discovery (Pagination Fix 0005) ----

def fetch_labeled_issues(token: str) -> list[int]:
    """List open issues/PRs with codex-dispatch label. Returns issue numbers."""
    url = f"{API_BASE}/search/issues"
    params = {
        "q": f"repo:{TARGET_REPO} is:open label:{DISPATCH_LABEL}",
        "sort": "updated",
        "order": "desc",
        "per_page": 50,
    }
    issues = []
    for page in range(MAX_PAGES_LABELED_ISSUES):
        resp = requests.get(url, headers=_headers(token), params=params, timeout=15)
        if resp.status_code != 200:
            return issues  # Return whatever we have
        data = resp.json()
        for item in data.get("items", []):
            issues.append(item["number"])
        links = _parse_link_header(resp.headers.get("Link"))
        if "next" not in links:
            break
        url = links["next"]
        params = {}
    return issues


def fetch_issue_comments_paginated(token: str, issue_number: int,
                                     since_comment_id: int = 0,
                                     etag: str | None = None) -> tuple[list[dict], str | None, bool]:
    """
    Fetch all new comments on an issue, with Link header pagination.
    Returns (comments, new_etag, degraded).
    'degraded' = True if we hit a page cap or API failure mid-pagination.
    """
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    params = {
        "sort": "created",
        "direction": "asc",
        "per_page": MAX_PAGE_SIZE,
    }
    all_comments = []
    new_etag = etag
    degraded = False

    for page in range(MAX_PAGES_PER_ISSUE):
        resp = requests.get(url, headers=_headers(token, etag if page == 0 else None),
                            params=params if page == 0 else {}, timeout=15)
        if resp.status_code == 304:
            break  # No change
        if resp.status_code != 200:
            if page == 0:
                return [], etag, True  # First page failed → DEGRADED
            degraded = True
            break  # Subsequent page failed → use what we have
        if page == 0:
            new_etag = resp.headers.get("ETag", etag)
        comments = resp.json()
        for c in comments:
            if c["id"] > since_comment_id:
                all_comments.append(c)
        links = _parse_link_header(resp.headers.get("Link"))
        if "next" not in links:
            break
        url = links["next"]
        params = {}

    if page >= MAX_PAGES_PER_ISSUE - 1:
        degraded = True
    return all_comments, new_etag, degraded


# ---- Legacy helpers (keep for receipt/status) ----

def check_issue_labels(token: str, issue_number: int) -> list[str]:
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}"
    resp = requests.get(url, headers=_headers(token), timeout=10)
    if resp.status_code != 200:
        return []
    return [l["name"] for l in resp.json().get("labels", [])]


def post_comment(token: str, issue_number: int, body: str):
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    resp = requests.post(url, headers=_headers(token), json={"body": body}, timeout=15)
    if resp.status_code == 201:
        return resp.json().get("html_url", "")
    return f"ERROR_{resp.status_code}"


def format_receipt(task_id: str, idempotency_key: str, status: str, runner_id: str,
                    workspace: str, head_sha: str, codex_version: str,
                    execution_profile: str = "read-only") -> str:
    now = datetime.now(timezone.utc).isoformat()
    return f"""```yaml
CodexDispatchReceipt:
  agent_id: CODEX-DISPATCHER
  task_id: {task_id}
  idempotency_key: {idempotency_key}
  status: {status}
  execution_profile: {execution_profile}
  local_workspace: {workspace}
  detected_head: {head_sha}
  runner_id: {runner_id}
  codex_runtime: codex-cli-{codex_version}
  started_at: {now}
```"""


def format_completed(task_id: str, idempotency_key: str, summary: str, status: str = "COMPLETED") -> str:
    return f"""```yaml
CODEX_TASK_COMPLETED:
  agent_id: CODEX-DISPATCHER
  task_id: {task_id}
  idempotency_key: {idempotency_key}
  status: {status}
  completed_at: {datetime.now(timezone.utc).isoformat()}
  summary: |
    {summary}
```"""


def get_issue_comments(token: str, issue_number: int, per_page: int = 10) -> list[dict]:
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    resp = requests.get(url, headers=_headers(token), params={"per_page": per_page, "page": 1}, timeout=10)
    if resp.status_code != 200:
        return []
    return resp.json()


def get_current_comment_id(token: str) -> int:
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/comments"
    resp = requests.get(url, headers=_headers(token),
                        params={"sort": "created", "direction": "desc", "per_page": 1}, timeout=10)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]
    return 0
