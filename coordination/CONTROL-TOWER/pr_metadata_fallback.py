#!/usr/bin/env python3
"""Governed fallback for narrowly-scoped GitHub PR metadata transitions.

Primary path remains the native ChatGPT GitHub Connector. This module is a
fallback transport only. It does not create code authority, review authority,
merge authority, branch-write authority, or release authority.

V1 supports only mark_ready_for_review.
Fallback eligibility is read from a fixed incident registry on canonical main;
it is not supplied or minted by the caller.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

GOVERNANCE_REPOSITORY = "vxz2datoubo/second-brain-coordination"
INCIDENT_REGISTRY_PATH = "coordination/CONTROL-TOWER/PR-METADATA-FALLBACK-INCIDENTS.json"
INCIDENT_REGISTRY_SCHEMA = "PR_METADATA_FALLBACK_INCIDENT_REGISTRY/v1"

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
    incident_id: str
    incident_registry_ref: str
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


def _read_pr(repository: str, pr_number: int) -> dict[str, Any]:
    raw = _run_gh([
        "api",
        f"repos/{repository}/pulls/{pr_number}",
        "--jq",
        '{"head":.head.sha,"draft":.draft,"state":.state,"merged":.merged,"base":.base.ref}',
    ])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FallbackError("invalid PR readback JSON") from exc


def _read_incident_registry() -> dict[str, Any]:
    raw = _run_gh([
        "api",
        f"repos/{GOVERNANCE_REPOSITORY}/contents/{INCIDENT_REGISTRY_PATH}?ref=main",
        "--jq",
        ".content",
    ]).strip()
    if not raw:
        raise FallbackError("missing canonical primary-failure incident registry")
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        registry = json.loads(decoded)
    except Exception as exc:
        raise FallbackError("invalid canonical primary-failure incident registry") from exc
    if registry.get("schema") != INCIDENT_REGISTRY_SCHEMA:
        raise FallbackError("unexpected primary-failure incident registry schema")
    if not isinstance(registry.get("incidents"), list):
        raise FallbackError("invalid primary-failure incident registry entries")
    return registry


def _require_canonical_incident(
    repository: str,
    pr_number: int,
    expected_head: str,
    operation: str,
) -> dict[str, Any]:
    registry = _read_incident_registry()
    matches = [
        item
        for item in registry["incidents"]
        if item.get("status") == "ACTIVE"
        and item.get("scope") == "SINGLE_TARGET_EXACT_HEAD"
        and item.get("repository") == repository
        and item.get("pr_number") == pr_number
        and item.get("expected_head") == expected_head
        and item.get("operation") == operation
        and item.get("primary_transport") == "CHATGPT_GITHUB_CONNECTOR"
        and item.get("failure_fingerprint")
        and item.get("evidence_refs")
    ]
    if len(matches) != 1:
        raise FallbackError(
            "fallback not eligible: no unique ACTIVE canonical primary-failure incident "
            "for exact target/head/operation"
        )
    return matches[0]


def _node_id(repository: str, pr_number: int) -> str:
    raw = _run_gh([
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


def _validate_after(snapshot: dict[str, Any], expected_head: str, *, phase: str) -> None:
    if snapshot.get("head") != expected_head:
        raise FallbackError(f"exact-head fence failed {phase}")
    if snapshot.get("state") != "open" or snapshot.get("merged"):
        raise FallbackError(f"PR must be open and unmerged {phase}")
    if snapshot.get("draft"):
        raise FallbackError(f"postcondition failed {phase}: PR is draft")


def mark_ready_for_review(repository: str, pr_number: int, expected_head: str) -> Receipt:
    if len(expected_head) != 40 or any(c not in "0123456789abcdef" for c in expected_head.lower()):
        raise FallbackError("expected_head must be a 40-hex commit SHA")

    incident = _require_canonical_incident(
        repository,
        pr_number,
        expected_head,
        "mark_ready_for_review",
    )
    incident_id = str(incident["incident_id"])
    registry_ref = f"github://{GOVERNANCE_REPOSITORY}/main/{INCIDENT_REGISTRY_PATH}"

    before = _read_pr(repository, pr_number)
    if before.get("state") != "open" or before.get("merged"):
        raise FallbackError("PR must be open and unmerged before mutation")
    if before.get("head") != expected_head:
        raise FallbackError("exact-head fence failed before mutation")

    if not before.get("draft"):
        after = _read_pr(repository, pr_number)
        _validate_after(after, expected_head, phase="after idempotent readback")
        return Receipt(
            schema="PR_METADATA_FALLBACK_RECEIPT/v1",
            operation="mark_ready_for_review",
            repository=repository,
            pr_number=pr_number,
            expected_head=expected_head,
            before_head=before["head"],
            after_head=after["head"],
            before_draft=False,
            after_draft=False,
            transport="GH_OFFICIAL_GRAPHQL",
            status="ALREADY_READY",
            incident_id=incident_id,
            incident_registry_ref=registry_ref,
            authority=AUTHORITY,
        )

    node_id = _node_id(repository, pr_number)
    mutation = "mutation($id:ID!){markPullRequestReadyForReview(input:{pullRequestId:$id}){pullRequest{id isDraft headRefOid}}}"
    raw = _run_gh([
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

    after = _read_pr(repository, pr_number)
    _validate_after(after, expected_head, phase="after mutation")

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
        incident_id=incident_id,
        incident_registry_ref=registry_ref,
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
