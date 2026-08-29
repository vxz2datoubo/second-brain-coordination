#!/usr/bin/env python3
"""Governed fallback for narrowly-scoped GitHub PR metadata transitions.

Primary path remains the native ChatGPT GitHub Connector. This module is a
fallback transport only. It does not create code authority, review authority,
merge authority, branch-write authority, or release authority.

Supported operation in V1:
- mark_ready_for_review

The command fails closed unless the caller supplies an exact expected PR head
SHA and the live PR readback matches it before and after the mutation.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any, Callable


AUTHORITY = {
    "creates_task": False,
    "creates_route": False,
    "creates_work_claim": False,
    "grants_execution": False,
    "grants_code_write": False,
    "grants_branch_write": False,
    "grants_review_accept": False,
    "grants_merge": False,
    "grants_release": False,
    "expands_permissions": False,
}


class FallbackError(RuntimeError):
    pass


@dataclass(frozen=True)
class Receipt:
    schema: str
    operation: str
    repository: str
    pr_number: int
    expected_head: str
    before_head: str
    after_head: str
    before_draft: bool
    after_draft: bool
    transport: str
    status: str
    authority: dict[str, bool]

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":"))

    def digest(self) -> str:
        return sha256(self.canonical_json().encode()).hexdigest()


def _run_gh(args: list[str], *, input_text: str | None = None) -> str:
    env = os.environ.copy()
    proc = subprocess.run(
        ["gh", *args],
        input=input_text,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )
    if proc.returncode != 0:
        raise FallbackError(proc.stderr.strip() or proc.stdout.strip() or "gh failed")
    return proc.stdout


def _read_pr(repository: str, pr_number: int, runner: Callable[..., str] = _run_gh) -> dict[str, Any]:
    raw = runner([
        "api",
        f"repos/{repository}/pulls/{pr_number}",
        "--jq",
        '{"head":.head.sha,"draft":.draft,"state":.state,"merged":.merged,"base":.base.ref}',
    ])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FallbackError("invalid PR readback JSON") from exc


def _node_id(repository: str, pr_number: int, runner: Callable[..., str] = _run_gh) -> str:
    raw = runner([
        "api",
        "graphql",
        "-f",
        "query=query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){pullRequest(number:$number){id}}}",
        "-F",
        f"owner={repository.split('/', 1)[0]}",
        "-F",
        f"name={repository.split('/', 1)[1]}",
        "-F",
        f"number={pr_number}",
        "--jq",
        ".data.repository.pullRequest.id",
    ])
    node = raw.strip()
    if not node:
        raise FallbackError("missing PR node id")
    return node


def mark_ready_for_review(
    repository: str,
    pr_number: int,
    expected_head: str,
    *,
    runner: Callable[..., str] = _run_gh,
) -> Receipt:
    if len(expected_head) != 40 or any(c not in "0123456789abcdef" for c in expected_head.lower()):
        raise FallbackError("expected_head must be a 40-hex commit SHA")

    before = _read_pr(repository, pr_number, runner)
    if before.get("state") != "open" or before.get("merged"):
        raise FallbackError("PR must be open and unmerged")
    if before.get("head") != expected_head:
        raise FallbackError("exact-head fence failed before mutation")

    if not before.get("draft"):
        after = _read_pr(repository, pr_number, runner)
        return Receipt(
            schema="PR_METADATA_FALLBACK_RECEIPT/v1",
            operation="mark_ready_for_review",
            repository=repository,
            pr_number=pr_number,
            expected_head=expected_head,
            before_head=before["head"],
            after_head=after["head"],
            before_draft=False,
            after_draft=bool(after["draft"]),
            transport="GH_OFFICIAL_GRAPHQL",
            status="ALREADY_READY",
            authority=AUTHORITY,
        )

    node_id = _node_id(repository, pr_number, runner)
    mutation = "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){pullRequest{id isDraft headRefOid}}}"
    raw = runner([
        "api",
        "graphql",
        "-f",
        f"query={mutation}",
        "-F",
        f"id={node_id}",
    ])
    try:
        response = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FallbackError("invalid mutation response JSON") from exc
    if response.get("errors"):
        raise FallbackError(f"GraphQL mutation failed: {response['errors']}")

    after = _read_pr(repository, pr_number, runner)
    if after.get("head") != expected_head:
        raise FallbackError("exact-head fence failed after mutation")
    if after.get("draft"):
        raise FallbackError("postcondition failed: PR remains draft")

    return Receipt(
        schema="PR_METADATA_FALLBACK_RECEIPT/v1",
        operation="mark_ready_for_review",
        repository=repository,
        pr_number=pr_number,
        expected_head=expected_head,
        before_head=before["head"],
        after_head=after["head"],
        before_draft=True,
        after_draft=False,
        transport="GH_OFFICIAL_GRAPHQL",
        status="SUCCESS",
        authority=AUTHORITY,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--operation", choices=["mark_ready_for_review"], required=True)
    args = parser.parse_args(argv)

    try:
        receipt = mark_ready_for_review(args.repo, args.pr, args.expected_head)
    except FallbackError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc), "authority": AUTHORITY}, sort_keys=True))
        return 2

    payload = asdict(receipt)
    payload["receipt_digest"] = receipt.digest()
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
