"""Bounded, unauthenticated GitHub API reader for E38 trust verification.

The transport has one fixed public repository and only constructs allowlisted
GitHub API paths.  It never reads credentials, follows redirects, or exposes a
generic URL fetch method.
"""

from __future__ import annotations

import base64
import hashlib
from http.client import HTTPMessage
from typing import Any, Callable, Protocol
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import ValidationError, require_sha1, strict_json_loads
from .proofs import (
    CANONICAL_ACTIVE_TASK_PATH,
    CANONICAL_COORDINATION_PATH,
    CANONICAL_MAIN_REF,
    CANONICAL_REPOSITORY,
    FetchedRouteSnapshot,
    ReadOnlyApprovalDocument,
    RouteFileIdentity,
    _fetched_approval_document,
    _fetched_route_snapshot,
    _git_blob_sha1,
)


API_HOST = "api.github.com"
API_BASE = f"https://{API_HOST}"
MAX_COMMENT_BYTES = 256 * 1024
MAX_METADATA_BYTES = 512 * 1024
MAX_TREE_BYTES = 2 * 1024 * 1024
MAX_BLOB_BYTES = 512 * 1024
DEFAULT_TIMEOUT_SECONDS = 10.0


class ReadOnlyTransportError(ValidationError):
    """A public-safe reason code for a rejected remote observation."""


class _Response(Protocol):
    status: int
    headers: HTTPMessage

    def read(self, amount: int = -1) -> bytes: ...

    def geturl(self) -> str: ...

    def __enter__(self) -> "_Response": ...

    def __exit__(self, *args: object) -> object: ...


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request: Request, *_args: object, **_kwargs: object) -> Request:
        raise HTTPError(request.full_url, 302, "redirects are rejected", request.headers, None)


OpenFunction = Callable[[Request, float], _Response]


def _default_open(request: Request, timeout: float) -> _Response:
    return build_opener(_NoRedirect()).open(request, timeout=timeout)  # type: ignore[return-value]


class PublicGitHubTransport:
    """Allowlisted public GitHub reader with a two-read main-ref drift check."""

    def __init__(
        self,
        *,
        opener: OpenFunction | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0 or timeout_seconds > 30:
            raise ValidationError("transport timeout must be within the bounded public-read window")
        self._open = opener or _default_open
        self._timeout_seconds = float(timeout_seconds)

    @staticmethod
    def _path(suffix: str) -> str:
        return f"/repos/{CANONICAL_REPOSITORY}{suffix}"

    def _get_json(self, path: str, max_bytes: int) -> dict[str, Any]:
        if not path.startswith(f"/repos/{CANONICAL_REPOSITORY}/"):
            raise ReadOnlyTransportError("github_path_not_allowlisted")
        url = f"{API_BASE}{path}"
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != API_HOST or parsed.username or parsed.password:
            raise ReadOnlyTransportError("github_host_not_allowlisted")
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "brainops-control-plane-e38-public-read-only",
            },
        )
        try:
            with self._open(request, self._timeout_seconds) as response:
                if response.geturl() != url:
                    raise ReadOnlyTransportError("github_redirect_rejected")
                if response.status != 200:
                    raise ReadOnlyTransportError("github_unexpected_http_status")
                content_type = response.headers.get("Content-Type", "")
                if not content_type.lower().startswith("application/json"):
                    raise ReadOnlyTransportError("github_unexpected_media_type")
                length = response.headers.get("Content-Length")
                if length is not None and (not length.isdigit() or int(length) > max_bytes):
                    raise ReadOnlyTransportError("github_response_oversized")
                payload = response.read(max_bytes + 1)
        except ReadOnlyTransportError:
            raise
        except Exception as exc:
            raise ReadOnlyTransportError("trusted_transport_unavailable") from exc
        if len(payload) > max_bytes:
            raise ReadOnlyTransportError("github_response_oversized")
        try:
            decoded = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReadOnlyTransportError("github_response_not_utf8_json") from exc
        parsed_json = strict_json_loads(decoded)
        if not isinstance(parsed_json, dict):
            raise ReadOnlyTransportError("github_json_object_required")
        return parsed_json

    def _main_ref(self) -> str:
        payload = self._get_json(self._path("/git/ref/heads/main"), MAX_METADATA_BYTES)
        candidate = payload.get("object")
        if not isinstance(candidate, dict) or candidate.get("type") != "commit":
            raise ReadOnlyTransportError("github_main_ref_not_commit")
        sha = candidate.get("sha")
        require_sha1(sha, "github main ref commit")
        return sha

    def _commit_tree(self, commit_sha1: str) -> str:
        require_sha1(commit_sha1, "github commit")
        payload = self._get_json(self._path(f"/git/commits/{commit_sha1}"), MAX_METADATA_BYTES)
        if payload.get("sha") != commit_sha1:
            raise ReadOnlyTransportError("github_commit_identity_mismatch")
        tree = payload.get("tree")
        if not isinstance(tree, dict):
            raise ReadOnlyTransportError("github_commit_tree_missing")
        tree_sha1 = tree.get("sha")
        require_sha1(tree_sha1, "github tree")
        return tree_sha1

    def _tree_entries(self, tree_sha1: str) -> dict[str, str]:
        require_sha1(tree_sha1, "github tree")
        payload = self._get_json(self._path(f"/git/trees/{tree_sha1}?recursive=1"), MAX_TREE_BYTES)
        if payload.get("sha") != tree_sha1 or payload.get("truncated") is True:
            raise ReadOnlyTransportError("github_tree_incomplete_or_mismatched")
        tree = payload.get("tree")
        if not isinstance(tree, list):
            raise ReadOnlyTransportError("github_tree_entries_missing")
        desired = {CANONICAL_ACTIVE_TASK_PATH, CANONICAL_COORDINATION_PATH}
        entries: dict[str, str] = {}
        for entry in tree:
            if not isinstance(entry, dict):
                raise ReadOnlyTransportError("github_tree_entry_invalid")
            path = entry.get("path")
            if path not in desired:
                continue
            if entry.get("type") != "blob" or path in entries:
                raise ReadOnlyTransportError("github_tree_path_substitution")
            sha = entry.get("sha")
            require_sha1(sha, "github tree blob")
            entries[path] = sha
        if set(entries) != desired:
            raise ReadOnlyTransportError("github_tree_route_path_missing")
        return entries

    def _blob(self, blob_sha1: str) -> bytes:
        require_sha1(blob_sha1, "github blob")
        payload = self._get_json(self._path(f"/git/blobs/{blob_sha1}"), MAX_BLOB_BYTES)
        if payload.get("sha") != blob_sha1 or payload.get("encoding") != "base64" or not isinstance(payload.get("content"), str):
            raise ReadOnlyTransportError("github_blob_identity_or_encoding_mismatch")
        try:
            content = base64.b64decode("".join(payload["content"].split()), validate=True)
        except Exception as exc:
            raise ReadOnlyTransportError("github_blob_invalid_base64") from exc
        if len(content) > MAX_BLOB_BYTES or _git_blob_sha1(content) != blob_sha1:
            raise ReadOnlyTransportError("github_blob_content_mismatch")
        return content

    def fetch_approval_comment(self, issue_number: int, comment_id: int) -> ReadOnlyApprovalDocument:
        if not isinstance(issue_number, int) or issue_number < 1 or not isinstance(comment_id, int) or comment_id < 1:
            raise ValidationError("issue_number and comment_id must be positive")
        payload = self._get_json(self._path(f"/issues/comments/{comment_id}"), MAX_COMMENT_BYTES)
        user = payload.get("user")
        if not isinstance(user, dict):
            raise ReadOnlyTransportError("github_comment_actor_missing")
        actor = user.get("login")
        issued_at = payload.get("created_at")
        body = payload.get("body")
        expected_issue_url = f"{API_BASE}{self._path(f'/issues/{issue_number}')}"
        if (
            payload.get("id") != comment_id
            or payload.get("issue_url") != expected_issue_url
            or not isinstance(actor, str)
            or not isinstance(issued_at, str)
            or not isinstance(body, str)
        ):
            raise ReadOnlyTransportError("github_comment_identity_or_body_missing")
        # GitHub returns RFC3339 timestamps with Z; no client-supplied comment is accepted.
        return _fetched_approval_document(CANONICAL_REPOSITORY, issue_number, comment_id, actor, issued_at, body)

    def fetch_main_route_snapshot(self, observed_at: str) -> FetchedRouteSnapshot:
        first_main = self._main_ref()
        tree_sha1 = self._commit_tree(first_main)
        entries = self._tree_entries(tree_sha1)
        active_content = self._blob(entries[CANONICAL_ACTIVE_TASK_PATH])
        coordination_content = self._blob(entries[CANONICAL_COORDINATION_PATH])
        if self._main_ref() != first_main:
            raise ReadOnlyTransportError("github_main_ref_drift")
        return _fetched_route_snapshot(
            CANONICAL_REPOSITORY,
            CANONICAL_MAIN_REF,
            first_main,
            tree_sha1,
            RouteFileIdentity(CANONICAL_ACTIVE_TASK_PATH, entries[CANONICAL_ACTIVE_TASK_PATH], hashlib.sha256(active_content).hexdigest()),
            RouteFileIdentity(CANONICAL_COORDINATION_PATH, entries[CANONICAL_COORDINATION_PATH], hashlib.sha256(coordination_content).hexdigest()),
            active_content,
            coordination_content,
            observed_at,
        )
