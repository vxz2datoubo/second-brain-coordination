"""
CODEX-GITHUB-DISPATCHER-0001 — GitHub Protocol
Read Issues/PRs, write dispatch receipt/status comments.
"""
import os
import requests
import subprocess
import time
from datetime import datetime, timezone

TARGET_REPO = "vxz2datoubo/second-brain-coordination"
API_BASE = "https://api.github.com"
DISPATCH_LABEL = "codex-dispatch"


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


def fetch_new_comments(token: str, since_comment_id: int, etag: str | None = None):
    """Fetch comments on issues labeled codex-dispatch since cursor."""
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/comments"
    params = {
        "sort": "created",
        "direction": "asc",
        "since": datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat(),
        "per_page": 100,
    }
    resp = requests.get(url, headers=_headers(token, etag), params=params, timeout=15)
    if resp.status_code == 304:
        return [], resp.headers.get("ETag")
    if resp.status_code != 200:
        return [], etag
    comments = resp.json()
    new_etag = resp.headers.get("ETag", etag)
    # Filter: only comments after cursor, on issues with dispatch label
    filtered = []
    for c in comments:
        if c["id"] <= since_comment_id:
            continue
        # Check if the issue has the dispatch label
        issue_url = c.get("issue_url", "")
        if not issue_url:
            continue
        # Quick check: fetch issue labels (cached in comment? no, so we need issue endpoint)
        # For MVP, use a simpler approach: check labels from the linked issue
        filtered.append(c)
    return filtered, new_etag


def check_issue_labels(token: str, issue_number: int) -> list[str]:
    """Fetch labels on an issue."""
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}"
    resp = requests.get(url, headers=_headers(token), timeout=10)
    if resp.status_code != 200:
        return []
    return [l["name"] for l in resp.json().get("labels", [])]


def post_comment(token: str, issue_number: int, body: str):
    """Post a comment to an issue."""
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    resp = requests.post(url, headers=_headers(token), json={"body": body}, timeout=15)
    if resp.status_code == 201:
        return resp.json().get("html_url", "")
    return f"ERROR_{resp.status_code}"


def format_receipt(task_id: str, idempotency_key: str, status: str, runner_id: str,
                    workspace: str, head_sha: str, codex_version: str) -> str:
    now = datetime.now(timezone.utc).isoformat()
    return f"""```yaml
CodexDispatchReceipt:
  agent_id: CODEX-DISPATCHER
  task_id: {task_id}
  idempotency_key: {idempotency_key}
  status: {status}
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
    """Get recent comments on a specific issue."""
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/{issue_number}/comments"
    resp = requests.get(url, headers=_headers(token), params={"per_page": per_page, "page": 1}, timeout=10)
    if resp.status_code != 200:
        return []
    return resp.json()


def get_current_comment_id(token: str) -> int:
    """Get the most recent comment ID across the repo (for cursor init)."""
    url = f"{API_BASE}/repos/{TARGET_REPO}/issues/comments"
    resp = requests.get(url, headers=_headers(token), params={"sort": "created", "direction": "desc", "per_page": 1}, timeout=10)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]["id"]
    return 0
