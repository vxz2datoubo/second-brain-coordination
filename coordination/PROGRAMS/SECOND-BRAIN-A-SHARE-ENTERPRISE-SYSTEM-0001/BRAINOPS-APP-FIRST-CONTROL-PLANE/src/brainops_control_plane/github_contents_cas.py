"""Fixed-scope GitHub Contents CAS semantics for E42.

This module deliberately has no default network transport and no credential
loader.  A host runtime may inject a bounded transport that already owns its
authentication policy.  Tests inject synthetic responses only.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Mapping, Protocol
from urllib.parse import quote

from .durable_authority import CasWriteResult, RevisionedObject
from .models import ValidationError, require_identifier, require_sha1, strict_json_loads
from .proofs import _git_blob_sha1


_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_REF = re.compile(r"^refs/heads/[A-Za-z0-9_.-]+$")
API_ROOT = "https://api.github.com"
MAX_BODY_BYTES = 1024 * 1024


class CasTransportStatus(str, Enum):
    APPLIED = "APPLIED"
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    UNPROCESSABLE = "UNPROCESSABLE"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    REDIRECT_REJECTED = "REDIRECT_REJECTED"
    RESPONSE_IDENTITY_MISMATCH = "RESPONSE_IDENTITY_MISMATCH"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    RETRY_EXHAUSTED = "RETRY_EXHAUSTED"
    WRITE_OUTCOME_UNKNOWN = "WRITE_OUTCOME_UNKNOWN"


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    body: bytes | None
    timeout_seconds: float
    follow_redirects: bool = False


@dataclass(frozen=True)
class HttpResponse:
    status: int
    url: str
    headers: Mapping[str, str]
    body: bytes


class BoundedHttpTransport(Protocol):
    """Credential ownership is outside this protocol and this package."""

    def request(self, request: HttpRequest) -> HttpResponse: ...


@dataclass(frozen=True)
class VerifiedContentObject:
    repository: str
    ref: str
    path: str
    commit_sha1: str
    tree_sha1: str
    blob_sha1: str
    content_sha256: str
    content: bytes


@dataclass(frozen=True)
class GitHubCasOutcome:
    status: CasTransportStatus
    content: VerifiedContentObject | None = None
    reason_code: str | None = None

    @property
    def successful(self) -> bool:
        return self.status in {CasTransportStatus.FOUND, CasTransportStatus.APPLIED}


class _CasFailure(Exception):
    def __init__(self, status: CasTransportStatus, reason_code: str) -> None:
        super().__init__(reason_code)
        self.status = status
        self.reason_code = reason_code


class FixedGitHubContentsCasClient:
    """Production-capable fixed repository/ref/path Contents CAS adapter.

    The adapter implements GitHub's create/update contract, but cannot retarget
    its repository, authority branch, or path prefix after construction.  It
    verifies ref -> commit -> tree -> exact path/blob/content both before and
    after a write.  No method exposes arbitrary URLs or generic GitHub writes.
    """

    def __init__(
        self,
        repository: str,
        authority_ref: str,
        path_prefix: str,
        transport: BoundedHttpTransport,
        *,
        timeout_seconds: float = 10.0,
        max_attempts: int = 2,
    ) -> None:
        if not isinstance(repository, str) or _REPOSITORY.fullmatch(repository) is None:
            raise ValidationError("CAS repository must be owner/name")
        if not isinstance(authority_ref, str) or _REF.fullmatch(authority_ref) is None:
            raise ValidationError("CAS authority_ref must be refs/heads/name")
        self._validate_prefix(path_prefix)
        if not isinstance(timeout_seconds, (int, float)) or not 0 < timeout_seconds <= 30:
            raise ValidationError("CAS timeout must be within 30 seconds")
        if not isinstance(max_attempts, int) or not 1 <= max_attempts <= 3:
            raise ValidationError("CAS attempts must be between one and three")
        self._repository = repository
        self._authority_ref = authority_ref
        self._branch = authority_ref.removeprefix("refs/heads/")
        self._path_prefix = path_prefix.rstrip("/")
        self._transport = transport
        self._timeout_seconds = float(timeout_seconds)
        self._max_attempts = max_attempts

    @staticmethod
    def _validate_prefix(path_prefix: str) -> None:
        if (
            not isinstance(path_prefix, str)
            or not path_prefix
            or path_prefix.startswith("/")
            or path_prefix.endswith("/")
            or any(part in {"", ".", ".."} for part in path_prefix.split("/"))
        ):
            raise ValidationError("CAS path prefix invalid")

    def _path(self, object_id: str) -> str:
        require_identifier(object_id, "CAS object_id")
        return f"{self._path_prefix}/{object_id}.json"

    def _url(self, suffix: str) -> str:
        return f"{API_ROOT}/repos/{self._repository}{suffix}"

    def _request(self, method: str, suffix: str, *, body: bytes | None = None) -> HttpResponse:
        url = self._url(suffix)
        request = HttpRequest(
            method=method,
            url=url,
            headers={
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "User-Agent": "brainops-e42-fixed-contents-cas",
            },
            body=body,
            timeout_seconds=self._timeout_seconds,
            follow_redirects=False,
        )
        last_timeout = False
        attempts = self._max_attempts if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = self._transport.request(request)
            except TimeoutError:
                last_timeout = True
                if attempt + 1 < attempts:
                    continue
                raise _CasFailure(CasTransportStatus.TIMEOUT, "github_cas_transport_timeout")
            except OSError:
                if attempt + 1 < attempts:
                    continue
                raise _CasFailure(CasTransportStatus.TRANSPORT_ERROR, "github_cas_transport_unavailable")
            except Exception as exc:
                raise _CasFailure(CasTransportStatus.TRANSPORT_ERROR, "github_cas_transport_unavailable") from exc
            if response.url != url or 300 <= response.status < 400:
                raise _CasFailure(CasTransportStatus.REDIRECT_REJECTED, "github_cas_redirect_rejected")
            if len(response.body) > MAX_BODY_BYTES:
                raise _CasFailure(CasTransportStatus.MALFORMED_RESPONSE, "github_cas_response_oversized")
            return response
        raise _CasFailure(
            CasTransportStatus.TIMEOUT if last_timeout else CasTransportStatus.RETRY_EXHAUSTED,
            "github_cas_retry_exhausted",
        )

    @staticmethod
    def _json(response: HttpResponse) -> dict[str, object]:
        try:
            payload = strict_json_loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, ValidationError) as exc:
            raise _CasFailure(CasTransportStatus.MALFORMED_RESPONSE, "github_cas_json_invalid") from exc
        if not isinstance(payload, dict):
            raise _CasFailure(CasTransportStatus.MALFORMED_RESPONSE, "github_cas_json_object_required")
        return payload

    def _head_commit(self) -> str:
        response = self._request("GET", f"/git/ref/heads/{quote(self._branch, safe='/')}")
        if response.status != 200:
            raise _CasFailure(CasTransportStatus.TRANSPORT_ERROR, "github_cas_ref_unavailable")
        payload = self._json(response)
        candidate = payload.get("object")
        if not isinstance(candidate, dict) or candidate.get("type") != "commit":
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_ref_identity_mismatch")
        sha = candidate.get("sha")
        try:
            return require_sha1(sha, "CAS ref commit")
        except ValidationError as exc:
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_ref_identity_mismatch") from exc

    def _tree_for_commit(self, commit_sha1: str) -> str:
        require_sha1(commit_sha1, "CAS commit")
        response = self._request("GET", f"/git/commits/{commit_sha1}")
        if response.status != 200:
            raise _CasFailure(CasTransportStatus.TRANSPORT_ERROR, "github_cas_commit_unavailable")
        payload = self._json(response)
        tree = payload.get("tree")
        if payload.get("sha") != commit_sha1 or not isinstance(tree, dict):
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_commit_identity_mismatch")
        try:
            return require_sha1(tree.get("sha"), "CAS commit tree")
        except ValidationError as exc:
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_commit_identity_mismatch") from exc

    def _content_at(self, path: str, commit_sha1: str, tree_sha1: str) -> GitHubCasOutcome:
        encoded_path = quote(path, safe="/")
        response = self._request("GET", f"/contents/{encoded_path}?ref={commit_sha1}")
        if response.status == 404:
            return GitHubCasOutcome(CasTransportStatus.NOT_FOUND, reason_code="github_cas_path_not_found")
        if response.status != 200:
            raise _CasFailure(CasTransportStatus.TRANSPORT_ERROR, "github_cas_content_read_failed")
        payload = self._json(response)
        encoded = payload.get("content")
        blob_sha1 = payload.get("sha")
        if payload.get("path") != path or payload.get("type") != "file" or payload.get("encoding") != "base64" or not isinstance(encoded, str):
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_content_identity_mismatch")
        try:
            require_sha1(blob_sha1, "CAS content blob")
            content = base64.b64decode("".join(encoded.split()), validate=True)
        except Exception as exc:
            raise _CasFailure(CasTransportStatus.MALFORMED_RESPONSE, "github_cas_content_invalid") from exc
        if _git_blob_sha1(content) != blob_sha1:
            raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_blob_content_mismatch")
        return GitHubCasOutcome(
            CasTransportStatus.FOUND,
            VerifiedContentObject(
                repository=self._repository,
                ref=self._authority_ref,
                path=path,
                commit_sha1=commit_sha1,
                tree_sha1=tree_sha1,
                blob_sha1=blob_sha1,
                content_sha256=hashlib.sha256(content).hexdigest(),
                content=content,
            ),
        )

    def read_verified(self, object_id: str) -> GitHubCasOutcome:
        path = self._path(object_id)
        try:
            commit = self._head_commit()
            tree = self._tree_for_commit(commit)
            return self._content_at(path, commit, tree)
        except _CasFailure as exc:
            return GitHubCasOutcome(exc.status, reason_code=exc.reason_code)
        except Exception:
            return GitHubCasOutcome(CasTransportStatus.TRANSPORT_ERROR, reason_code="github_cas_fail_closed")

    @staticmethod
    def _map_write_status(status: int) -> CasTransportStatus | None:
        return {
            409: CasTransportStatus.CONFLICT,
            412: CasTransportStatus.PRECONDITION_FAILED,
            422: CasTransportStatus.UNPROCESSABLE,
        }.get(status)

    def compare_and_set_verified(self, object_id: str, expected_revision: str | None, content: bytes) -> GitHubCasOutcome:
        if expected_revision is not None:
            require_sha1(expected_revision, "CAS expected blob")
        if not isinstance(content, bytes) or not content:
            raise ValidationError("CAS content must be non-empty bytes")
        path = self._path(object_id)
        current = self.read_verified(object_id)
        if current.status not in {CasTransportStatus.FOUND, CasTransportStatus.NOT_FOUND}:
            return current
        actual_revision = current.content.blob_sha1 if current.content is not None else None
        if actual_revision != expected_revision:
            return GitHubCasOutcome(CasTransportStatus.CONFLICT, current.content, "github_cas_expected_blob_mismatch")
        body: dict[str, object] = {
            "message": f"brainops authority CAS {object_id}",
            "content": base64.b64encode(content).decode("ascii"),
            "branch": self._branch,
        }
        if expected_revision is not None:
            body["sha"] = expected_revision
        try:
            try:
                response = self._request(
                    "PUT",
                    f"/contents/{quote(path, safe='/')}",
                    body=json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8"),
                )
            except _CasFailure as write_failure:
                if write_failure.status in {CasTransportStatus.TIMEOUT, CasTransportStatus.TRANSPORT_ERROR}:
                    observed = self.read_verified(object_id)
                    return GitHubCasOutcome(
                        CasTransportStatus.WRITE_OUTCOME_UNKNOWN,
                        observed.content,
                        "github_cas_write_outcome_unknown",
                    )
                raise
            mapped = self._map_write_status(response.status)
            if mapped is not None:
                return GitHubCasOutcome(mapped, reason_code=f"github_cas_http_{response.status}")
            if response.status not in {200, 201}:
                return GitHubCasOutcome(CasTransportStatus.TRANSPORT_ERROR, reason_code="github_cas_write_failed")
            payload = self._json(response)
            response_content = payload.get("content")
            response_commit = payload.get("commit")
            if not isinstance(response_content, dict) or not isinstance(response_commit, dict):
                raise _CasFailure(CasTransportStatus.MALFORMED_RESPONSE, "github_cas_write_response_incomplete")
            commit_sha1 = response_commit.get("sha")
            blob_sha1 = response_content.get("sha")
            require_sha1(commit_sha1, "CAS response commit")
            require_sha1(blob_sha1, "CAS response blob")
            if response_content.get("path") != path or blob_sha1 != _git_blob_sha1(content):
                raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_write_identity_mismatch")
            tree_sha1 = self._tree_for_commit(commit_sha1)
            verified = self._content_at(path, commit_sha1, tree_sha1)
            if verified.content is None or verified.content.content != content or verified.content.blob_sha1 != blob_sha1:
                raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_post_write_verification_failed")
            if self._head_commit() != commit_sha1:
                raise _CasFailure(CasTransportStatus.RESPONSE_IDENTITY_MISMATCH, "github_cas_authority_ref_drift")
            return GitHubCasOutcome(CasTransportStatus.APPLIED, verified.content)
        except _CasFailure as exc:
            return GitHubCasOutcome(exc.status, reason_code=exc.reason_code)
        except Exception:
            return GitHubCasOutcome(CasTransportStatus.TRANSPORT_ERROR, reason_code="github_cas_fail_closed")

    def read_content(self, repository: str, ref: str, path: str) -> RevisionedObject:
        if repository != self._repository or ref != self._authority_ref or path != self._path(path.rsplit("/", 1)[-1].removesuffix(".json")):
            raise OSError("github_cas_scope_mismatch")
        object_id = path.rsplit("/", 1)[-1].removesuffix(".json")
        result = self.read_verified(object_id)
        if result.status is CasTransportStatus.NOT_FOUND:
            return RevisionedObject(None, None)
        if result.status is not CasTransportStatus.FOUND or result.content is None:
            raise OSError(result.reason_code or result.status.value)
        return RevisionedObject(result.content.blob_sha1, result.content.content, result.content.content_sha256)

    def compare_and_set_content(
        self,
        repository: str,
        ref: str,
        path: str,
        expected_revision: str | None,
        payload: bytes,
    ) -> CasWriteResult:
        if repository != self._repository or ref != self._authority_ref or path != self._path(path.rsplit("/", 1)[-1].removesuffix(".json")):
            raise OSError("github_cas_scope_mismatch")
        object_id = path.rsplit("/", 1)[-1].removesuffix(".json")
        result = self.compare_and_set_verified(object_id, expected_revision, payload)
        if result.status is CasTransportStatus.APPLIED and result.content is not None:
            return CasWriteResult(True, result.content.blob_sha1)
        if result.status in {CasTransportStatus.CONFLICT, CasTransportStatus.PRECONDITION_FAILED, CasTransportStatus.UNPROCESSABLE}:
            revision = result.content.blob_sha1 if result.content is not None else None
            return CasWriteResult(False, revision)
        raise OSError(result.reason_code or result.status.value)
