"""Public-safe in-memory GitHub API fixtures for BrainOps authority tests."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from brainops_control_plane.github_transport import API_BASE, PublicGitHubTransport
from brainops_control_plane.models import BoundCanaryApproval, RouteRef
from brainops_control_plane.proofs import (
    CANONICAL_ACTIVE_TASK_PATH,
    CANONICAL_COORDINATION_PATH,
    CANONICAL_REPOSITORY,
    CanonicalApprovalBinding,
    ReadOnlyApprovalVerifier,
    ReadOnlyRouteProofVerifier,
    canonical_approval_ref,
)


NOW = "2026-08-02T00:00:00Z"
FUTURE = "2026-08-02T01:00:00Z"
MAIN_COMMIT = "d" * 40
MAIN_TREE = "e" * 40
ISSUE_NUMBER = 114
COMMENT_ID = 114038
ACTOR = "gpt"


class FakeResponse:
    def __init__(self, url: str, payload: object, *, status: int = 200, content_type: str = "application/json") -> None:
        self.status = status
        self.headers = {"Content-Type": content_type}
        self._url = url
        self._payload = json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8")

    def read(self, amount: int = -1) -> bytes:
        return self._payload if amount < 0 else self._payload[:amount]

    def geturl(self) -> str:
        return self._url

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeGitHubOpener:
    def __init__(self, responses: dict[str, list[FakeResponse]]) -> None:
        self.responses = responses
        self.requests: list[str] = []

    def __call__(self, request: object, _timeout: float) -> FakeResponse:
        url = getattr(request, "full_url")
        self.requests.append(url)
        candidates = self.responses.get(url)
        if not candidates:
            raise OSError(f"unexpected URL: {url}")
        return candidates.pop(0)


def blob_sha1(content: bytes) -> str:
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


def route_documents(
    task_id: str,
    epoch: int,
    *,
    actors: tuple[str, ...] = (ACTOR,),
    marker: str = "one",
    status: str = "READY",
    execution_allowed: bool = True,
    automatic_dispatch_allowed: bool = False,
    canary_execution_allowed: bool = False,
) -> tuple[bytes, bytes]:
    actor_list = ",".join(actors)
    active = (
        f'task_id: "{task_id}"\nroute_epoch: {epoch}\nstatus: {status}\nexecution_allowed: {str(execution_allowed).lower()}\n'
        f'automatic_dispatch_allowed: {str(automatic_dispatch_allowed).lower()}\ncanary_execution_allowed: {str(canary_execution_allowed).lower()}\n'
        f'authorized_approval_actors: [{actor_list}]\nmarker: "{marker}"\n'
    ).encode("utf-8")
    coordination = (
        'agents:\n  CODEX:\n'
        f'    task_id: "{task_id}"\n    route_epoch: {epoch}\n    status: {status}\n    execution_allowed: {str(execution_allowed).lower()}\n'
        f'    automatic_dispatch_allowed: {str(automatic_dispatch_allowed).lower()}\n    canary_execution_allowed: {str(canary_execution_allowed).lower()}\n'
        f'    authorized_approval_actors: [{actor_list}]\n    marker: "{marker}"\n'
    ).encode("utf-8")
    return active, coordination


def approval_body(bound: BoundCanaryApproval) -> str:
    binding = CanonicalApprovalBinding(
        task_id=bound.task_id,
        route_epoch=bound.route_epoch,
        canary_id=bound.canary_id,
        scope=bound.scope,
        expires_at=bound.expires_at,
        nonce=bound.nonce,
    )
    return f"approved\n```brainops-approval-v1\n{binding.canonical_json()}\n```\n"


def bound_approval(
    *,
    canary_id: str,
    task_id: str,
    epoch: int,
    scope: str,
    nonce: str,
    actor: str = ACTOR,
    expires_at: str = FUTURE,
    comment_id: int = COMMENT_ID,
    body: str | None = None,
) -> BoundCanaryApproval:
    provisional = BoundCanaryApproval(
        canary_id,
        task_id,
        epoch,
        scope,
        expires_at,
        nonce,
        canonical_approval_ref(CANONICAL_REPOSITORY, ISSUE_NUMBER, comment_id),
        CANONICAL_REPOSITORY,
        ISSUE_NUMBER,
        comment_id,
        actor,
        NOW,
        "a" * 64,
    )
    body = body if body is not None else approval_body(provisional)
    return BoundCanaryApproval(
        canary_id,
        task_id,
        epoch,
        scope,
        expires_at,
        nonce,
        canonical_approval_ref(CANONICAL_REPOSITORY, ISSUE_NUMBER, comment_id),
        CANONICAL_REPOSITORY,
        ISSUE_NUMBER,
        comment_id,
        actor,
        NOW,
        hashlib.sha256(body.encode("utf-8")).hexdigest(),
    )


def transport_for(
    *,
    task_id: str,
    epoch: int,
    body: str,
    actor: str = ACTOR,
    actors: tuple[str, ...] = (ACTOR,),
    marker: str = "one",
    main_ref_values: tuple[str, str] = (MAIN_COMMIT, MAIN_COMMIT),
    issue_url: str | None = None,
    omit_tree_path: str | None = None,
    status: str = "READY",
    execution_allowed: bool = True,
    automatic_dispatch_allowed: bool = False,
    canary_execution_allowed: bool = False,
) -> tuple[PublicGitHubTransport, FakeGitHubOpener]:
    active, coordination = route_documents(
        task_id,
        epoch,
        actors=actors,
        marker=marker,
        status=status,
        execution_allowed=execution_allowed,
        automatic_dispatch_allowed=automatic_dispatch_allowed,
        canary_execution_allowed=canary_execution_allowed,
    )
    active_blob = blob_sha1(active)
    coordination_blob = blob_sha1(coordination)
    ref_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/git/ref/heads/main"
    commit_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/git/commits/{MAIN_COMMIT}"
    tree_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/git/trees/{MAIN_TREE}?recursive=1"
    active_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/git/blobs/{active_blob}"
    coordination_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/git/blobs/{coordination_blob}"
    comment_url = f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/issues/comments/{COMMENT_ID}"
    tree_entries = [
        {"path": CANONICAL_ACTIVE_TASK_PATH, "type": "blob", "sha": active_blob},
        {"path": CANONICAL_COORDINATION_PATH, "type": "blob", "sha": coordination_blob},
    ]
    if omit_tree_path is not None:
        tree_entries = [entry for entry in tree_entries if entry["path"] != omit_tree_path]
    responses = {
        ref_url: [
            FakeResponse(ref_url, {"object": {"type": "commit", "sha": main_ref_values[0]}}),
            FakeResponse(ref_url, {"object": {"type": "commit", "sha": main_ref_values[1]}}),
        ],
        commit_url: [FakeResponse(commit_url, {"sha": MAIN_COMMIT, "tree": {"sha": MAIN_TREE}})],
        tree_url: [
            FakeResponse(
                tree_url,
                {
                    "sha": MAIN_TREE,
                    "truncated": False,
                    "tree": tree_entries,
                },
            )
        ],
        active_url: [FakeResponse(active_url, {"sha": active_blob, "encoding": "base64", "content": base64.b64encode(active).decode("ascii")})],
        coordination_url: [FakeResponse(coordination_url, {"sha": coordination_blob, "encoding": "base64", "content": base64.b64encode(coordination).decode("ascii")})],
        comment_url: [
            FakeResponse(
                comment_url,
                {
                    "id": COMMENT_ID,
                    "issue_url": issue_url or f"{API_BASE}/repos/{CANONICAL_REPOSITORY}/issues/{ISSUE_NUMBER}",
                    "user": {"login": actor},
                    "created_at": NOW,
                    "body": body,
                },
            )
        ],
    }
    opener = FakeGitHubOpener(responses)
    return PublicGitHubTransport(opener=opener), opener


def trusted_route_proof(route: RouteRef, task_id: str, *, actors: tuple[str, ...] = (ACTOR,), marker: str = "one") -> object:
    transport, _ = transport_for(task_id=task_id, epoch=route.route_epoch, body="irrelevant", actors=actors, marker=marker)
    snapshot = transport.fetch_main_route_snapshot(NOW)
    return ReadOnlyRouteProofVerifier().verify(route, task_id, snapshot, NOW)


def trusted_approval_verification(bound: BoundCanaryApproval, route: RouteRef, *, actor: str = ACTOR, actors: tuple[str, ...] = (ACTOR,)) -> object:
    body = approval_body(bound)
    transport, _ = transport_for(task_id=bound.task_id, epoch=route.route_epoch, body=body, actor=actor, actors=actors)
    proof = ReadOnlyRouteProofVerifier().verify(route, bound.task_id, transport.fetch_main_route_snapshot(NOW), NOW)
    comment = transport.fetch_approval_comment(ISSUE_NUMBER, COMMENT_ID)
    return ReadOnlyApprovalVerifier().verify(bound, comment, proof, NOW)
