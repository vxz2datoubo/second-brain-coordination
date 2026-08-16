"""R137's bounded, public GitHub, on-demand observation provider.

This module is deliberately an evidence producer, not a release, merge, or
Control Tower implementation.  Its network surface is fixed to public GitHub
GET observations.  It records only public-safe identities and digests in its
evidence bundles; observed source bodies remain transient while they are
validated.
"""
from __future__ import annotations

from base64 import b64decode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import inspect
import json
from pathlib import Path, PurePosixPath
import re
from typing import Any, Mapping, Sequence

import yaml

from .gateway import (
    AuthorityBoundLiveObservationProof,
    GatewayError,
    _LIVE_OBSERVATION_ISSUER_SEAL,
    canonical,
    digest,
    instant,
)

PROVIDER_ID = "r137-public-github-on-demand-v1"
CONTRACT_REVISION = "PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1"
API_HOST = "api.github.com"
API_VERSION = "2026-03-10"
TARGET_REPOSITORY = "vxz2datoubo/second-brain-coordination"
DOMAIN_REPOSITORY = "vxz2datoubo/eustia-ai-film"
MAX_RESPONSE_BYTES = 1_000_000
MAX_PAGES = 20
MAX_AGE_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 10

ACTIVE_TASK_PATH = "coordination/ACTIVE-CODEX-TASK.yaml"
CONTROL_PATHS = (
    ACTIVE_TASK_PATH,
    "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
    "coordination/ACTIVE-PROGRAM-LANES.yaml",
    "coordination/PROGRAM-CONTROL-TOWER.md",
)
_SAFE_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_SAFE_PATH = re.compile(r"^[A-Za-z0-9_./-]+$")
_ALLOWED_ENDPOINTS = (
    re.compile(r"^/repos/vxz2datoubo/(?:second-brain-coordination|eustia-ai-film)/git/ref/heads/main$"),
    re.compile(r"^/repos/vxz2datoubo/second-brain-coordination/git/commits/[0-9a-f]{40,64}$"),
    re.compile(r"^/repos/vxz2datoubo/second-brain-coordination/git/trees/[0-9a-f]{40,64}\?recursive=1$"),
    re.compile(r"^/repos/vxz2datoubo/second-brain-coordination/git/blobs/[0-9a-f]{40,64}$"),
    re.compile(r"^/repos/vxz2datoubo/second-brain-coordination/pulls/[1-9][0-9]*$"),
    re.compile(r"^/repos/vxz2datoubo/second-brain-coordination/pulls/[1-9][0-9]*/reviews\?per_page=100&page=[1-9][0-9]*$"),
)
_BUNDLES: dict[str, "LiveObservationEvidenceBundle"] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()


def _provider_code_digest() -> str:
    # The verifier recomputes this, so replacement of provider code invalidates
    # old proof material even if a caller retained a compact proof object.
    source = inspect.getsourcefile(_provider_code_digest)
    if source is None:
        raise GatewayError("PROVIDER_CODE_IDENTITY_UNAVAILABLE")
    return hashlib.sha256(Path(source).read_bytes()).hexdigest()


def _require_sha(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _SAFE_SHA.fullmatch(value):
        raise GatewayError(code)
    return value


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GatewayError(code)
    return value


def _canonical_route_path(active: Mapping[str, Any], tree: Mapping[str, str]) -> str:
    """Resolve only the active task's exact-main route pointer, fail-closed."""
    path = active.get("canonical_route")
    if not isinstance(path, str) or not path:
        raise GatewayError("CANONICAL_ROUTE_POINTER_INVALID")
    pure_path = PurePosixPath(path)
    if (
        "\\" in path
        or "//" in path
        or not path.startswith("coordination/ROUTES/")
        or not path.endswith(".yaml")
        or pure_path.is_absolute()
        or any(part in {"", ".", ".."} for part in pure_path.parts)
        or not _SAFE_PATH.fullmatch(path)
    ):
        raise GatewayError("CANONICAL_ROUTE_POINTER_INVALID")
    if path not in tree:
        raise GatewayError("CANONICAL_ROUTE_POINTER_MISSING")
    return path


@dataclass(frozen=True)
class DomainFreshnessTarget:
    repository: str
    branch: str = "main"


@dataclass(frozen=True)
class LiveObservationRequest:
    request_id: str
    provider_contract_revision: str
    target_repository: str
    target_branch: str
    pull_request_number: int | None
    expected_task_id: str | None
    expected_route_epoch: int | None
    required_control_plane_paths: tuple[str, ...]
    required_domain_freshness_targets: tuple[DomainFreshnessTarget, ...]
    required_review_scope: str
    requested_max_age_seconds: int
    requested_at: str

    def validate(self) -> None:
        if (not self.request_id or self.provider_contract_revision != CONTRACT_REVISION
                or self.target_repository != TARGET_REPOSITORY or self.target_branch != "main"):
            raise GatewayError("LIVE_OBSERVATION_REQUEST_FORBIDDEN")
        if not isinstance(self.pull_request_number, int) or self.pull_request_number <= 0:
            raise GatewayError("PULL_REQUEST_REQUIRED")
        if not self.expected_task_id or not isinstance(self.expected_route_epoch, int):
            raise GatewayError("EXPECTED_ROUTE_BINDING_REQUIRED")
        if tuple(self.required_control_plane_paths) != CONTROL_PATHS:
            raise GatewayError("CONTROL_PLANE_PATH_SET_FORBIDDEN")
        if self.required_review_scope != "ALL_RAW_REVIEWS":
            raise GatewayError("REVIEW_SCOPE_FORBIDDEN")
        if not 0 < self.requested_max_age_seconds <= MAX_AGE_SECONDS:
            raise GatewayError("OBSERVATION_AGE_OUT_OF_POLICY")
        instant(self.requested_at, "/requested_at")
        if not self.required_domain_freshness_targets:
            raise GatewayError("DOMAIN_FRESHNESS_TARGET_REQUIRED")
        for target in self.required_domain_freshness_targets:
            if target.repository != DOMAIN_REPOSITORY or target.branch != "main":
                raise GatewayError("DOMAIN_TARGET_FORBIDDEN")


@dataclass(frozen=True)
class ExactObjectRecord:
    repository: str
    commit_sha: str
    tree_sha: str
    path: str
    blob_sha: str
    content_sha256: str

    def ref(self) -> str:
        return f"github://{self.repository}@{self.commit_sha}/{self.path}#blob={self.blob_sha};sha256={self.content_sha256}"


@dataclass(frozen=True)
class RawReviewRecord:
    review_id: int
    state: str
    commit_id: str | None
    submitted_at: str | None
    actor_ref: str


@dataclass(frozen=True)
class LiveObservationEvidenceBundle:
    provider_id: str
    provider_contract_revision: str
    provider_code_ref: str
    provider_code_digest: str
    observation_id: str
    request_id: str
    started_at: str
    completed_at: str
    github_api_version: str
    target_repository: str
    initial_main_sha: str
    final_main_sha: str
    main_tree_sha: str
    exact_objects: tuple[ExactObjectRecord, ...]
    pr: Mapping[str, Any]
    reviews: tuple[RawReviewRecord, ...]
    route_fingerprint: str
    claim_fingerprint: str
    lane_fingerprint: str
    lease_fingerprint: str
    domain_freshness_ref: str
    pending_approval_ref: str
    request_response_metadata: tuple[Mapping[str, Any], ...]
    pagination_complete: bool
    warnings: tuple[str, ...]
    unknowns: tuple[str, ...]
    fresh_until: str
    invalidation_fingerprints: Mapping[str, Any]
    bundle_digest: str

    def identity_ref(self) -> str:
        return f"provider://r137/evidence/{self.observation_id}#sha256={self.bundle_digest}"

    def exact_refs(self) -> tuple[str, ...]:
        return (self.identity_ref(),) + tuple(record.ref() for record in self.exact_objects)


class LiveObservationProvider:
    """Serial, fixed-host observer.  Subclassing `_get_json` is test-only."""

    def _get_json(self, path: str) -> tuple[Mapping[str, str], Any, Mapping[str, Any]]:
        if (not path.startswith("/repos/") or "//" in path or ".." in PurePosixPath(path).parts
                or not any(pattern.fullmatch(path) for pattern in _ALLOWED_ENDPOINTS)):
            raise GatewayError("GITHUB_ENDPOINT_FORBIDDEN")
        connection = http.client.HTTPSConnection(API_HOST, timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            connection.request("GET", path, headers={
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": API_VERSION,
                "User-Agent": "second-brain-r137-public-observer",
            })
            response = connection.getresponse()
            headers = {key.casefold(): value for key, value in response.getheaders()}
            if response.status < 200 or response.status >= 300:
                raise GatewayError("GITHUB_TRANSPORT_OR_STATUS_UNVERIFIED")
            if 300 <= response.status < 400 or "location" in headers:
                raise GatewayError("GITHUB_REDIRECT_FORBIDDEN")
            media_type = headers.get("content-type", "").split(";", 1)[0].strip().casefold()
            if media_type != "application/json":
                raise GatewayError("GITHUB_MEDIA_TYPE_FORBIDDEN")
            declared = headers.get("content-length")
            if declared is not None and (not declared.isdigit() or int(declared) > MAX_RESPONSE_BYTES):
                raise GatewayError("GITHUB_RESPONSE_TOO_LARGE")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise GatewayError("GITHUB_RESPONSE_TOO_LARGE")
            try:
                decoded = payload.decode("utf-8")
                value = json.loads(decoded)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GatewayError("GITHUB_JSON_INVALID") from exc
            metadata: Mapping[str, Any] = {"path": path, "status": response.status, "content_sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}
            return headers, value, metadata
        except (OSError, http.client.HTTPException) as exc:
            raise GatewayError("GITHUB_TRANSPORT_OR_STATUS_UNVERIFIED") from exc
        finally:
            connection.close()

    def _ref(self, repository: str, branch: str) -> tuple[str, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f"/repos/{repository}/git/ref/heads/{branch}")
        obj = _mapping(value, "GITHUB_BRANCH_RESPONSE_INVALID")
        return _require_sha(_mapping(obj.get("object"), "GITHUB_BRANCH_RESPONSE_INVALID").get("sha"), "GITHUB_BRANCH_RESPONSE_INVALID"), metadata

    def _commit_tree(self, repository: str, commit: str) -> tuple[str, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f"/repos/{repository}/git/commits/{commit}")
        obj = _mapping(value, "GITHUB_COMMIT_RESPONSE_INVALID")
        return _require_sha(_mapping(obj.get("tree"), "GITHUB_COMMIT_RESPONSE_INVALID").get("sha"), "GITHUB_COMMIT_RESPONSE_INVALID"), metadata

    def _tree(self, repository: str, tree_sha: str) -> tuple[Mapping[str, str], Mapping[str, Any]]:
        _, value, metadata = self._get_json(f"/repos/{repository}/git/trees/{tree_sha}?recursive=1")
        tree_response = _mapping(value, "GITHUB_TREE_RESPONSE_INVALID")
        if tree_response.get("truncated") is not False:
            raise GatewayError("GITHUB_TREE_TRUNCATED_OR_INVALID")
        entries = tree_response.get("tree")
        if not isinstance(entries, list):
            raise GatewayError("GITHUB_TREE_RESPONSE_INVALID")
        result: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise GatewayError("GITHUB_TREE_RESPONSE_INVALID")
            path, kind, sha = entry.get("path"), entry.get("type"), entry.get("sha")
            if isinstance(path, str) and kind == "blob" and isinstance(sha, str):
                result[path] = sha
        return result, metadata

    def _blob(self, repository: str, blob_sha: str) -> tuple[bytes, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f"/repos/{repository}/git/blobs/{blob_sha}")
        obj = _mapping(value, "GITHUB_BLOB_RESPONSE_INVALID")
        if obj.get("encoding") != "base64" or not isinstance(obj.get("content"), str):
            raise GatewayError("GITHUB_BLOB_RESPONSE_INVALID")
        try:
            payload = b64decode(obj["content"].replace("\n", ""), validate=True)
        except (ValueError, TypeError) as exc:
            raise GatewayError("GITHUB_BLOB_RESPONSE_INVALID") from exc
        if len(payload) > MAX_RESPONSE_BYTES or _git_blob_sha(payload) != blob_sha:
            raise GatewayError("GITHUB_BLOB_IDENTITY_MISMATCH")
        return payload, metadata

    def _reviews(self, repository: str, number: int) -> tuple[tuple[RawReviewRecord, ...], tuple[Mapping[str, Any], ...]]:
        page, records, evidence = 1, [], []
        while page <= MAX_PAGES:
            headers, value, metadata = self._get_json(f"/repos/{repository}/pulls/{number}/reviews?per_page=100&page={page}")
            if not isinstance(value, list):
                raise GatewayError("GITHUB_REVIEWS_RESPONSE_INVALID")
            evidence.append(metadata)
            for item in value:
                item = _mapping(item, "GITHUB_REVIEWS_RESPONSE_INVALID")
                actor = _mapping(item.get("user"), "GITHUB_REVIEWS_RESPONSE_INVALID")
                review_id, state = item.get("id"), item.get("state")
                if not isinstance(review_id, int) or not isinstance(state, str):
                    raise GatewayError("GITHUB_REVIEWS_RESPONSE_INVALID")
                records.append(RawReviewRecord(review_id, state, item.get("commit_id") if isinstance(item.get("commit_id"), str) else None,
                                               item.get("submitted_at") if isinstance(item.get("submitted_at"), str) else None,
                                               f"github-user://{actor.get('id')}"))
            link = headers.get("link", "")
            has_next = 'rel="next"' in link
            if not has_next:
                return tuple(records), tuple(evidence)
            # Never follow a caller supplied URL; the next page is mechanically
            # derived and the Link header may only authorize the next integer.
            expected = f"page={page + 1}"
            if expected not in link:
                raise GatewayError("GITHUB_PAGINATION_INCOMPLETE")
            page += 1
        raise GatewayError("GITHUB_PAGINATION_INCOMPLETE")

    def _pr(self, repository: str, number: int) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        _, value, metadata = self._get_json(f"/repos/{repository}/pulls/{number}")
        pr = _mapping(value, "GITHUB_PR_RESPONSE_INVALID")
        head = _require_sha(_mapping(pr.get("head"), "GITHUB_PR_RESPONSE_INVALID").get("sha"), "GITHUB_PR_RESPONSE_INVALID")
        base = _require_sha(_mapping(pr.get("base"), "GITHUB_PR_RESPONSE_INVALID").get("sha"), "GITHUB_PR_RESPONSE_INVALID")
        state = pr.get("state")
        if not isinstance(state, str) or not isinstance(pr.get("merged"), bool):
            raise GatewayError("GITHUB_PR_RESPONSE_INVALID")
        merge_sha = pr.get("merge_commit_sha")
        if merge_sha is not None and not _SAFE_SHA.fullmatch(merge_sha):
            raise GatewayError("GITHUB_PR_RESPONSE_INVALID")
        if pr["merged"] and merge_sha is None:
            raise GatewayError("GITHUB_PR_RESPONSE_INVALID")
        return {"number": number, "state": state, "head_sha": head, "base_sha": base, "merged": pr["merged"], "merge_commit_sha": merge_sha}, metadata

    def observe(self, request: LiveObservationRequest) -> tuple[LiveObservationEvidenceBundle, AuthorityBoundLiveObservationProof]:
        request.validate()
        started = _utc_now(); metadata: list[Mapping[str, Any]] = []
        initial_main, item = self._ref(request.target_repository, request.target_branch); metadata.append(item)
        main_tree, item = self._commit_tree(request.target_repository, initial_main); metadata.append(item)
        tree, item = self._tree(request.target_repository, main_tree); metadata.append(item)
        records: list[ExactObjectRecord] = []
        parsed: dict[str, Any] = {}
        for path in request.required_control_plane_paths:
            if not _SAFE_PATH.fullmatch(path) or path not in tree:
                raise GatewayError("GITHUB_REQUIRED_PATH_MISSING")
            blob_sha = _require_sha(tree[path], "GITHUB_TREE_RESPONSE_INVALID")
            payload, item = self._blob(request.target_repository, blob_sha); metadata.append(item)
            record = ExactObjectRecord(request.target_repository, initial_main, main_tree, path, blob_sha, hashlib.sha256(payload).hexdigest())
            records.append(record)
            if path.endswith(".yaml"):
                try:
                    parsed[path] = yaml.safe_load(payload.decode("utf-8"))
                except (UnicodeDecodeError, yaml.YAMLError) as exc:
                    raise GatewayError("CONTROL_PLANE_YAML_INVALID") from exc
        active = _mapping(parsed[ACTIVE_TASK_PATH], "ACTIVE_TASK_INVALID")
        if active.get("task_id") != request.expected_task_id or active.get("route_epoch") != request.expected_route_epoch:
            raise GatewayError("ACTIVE_TASK_BINDING_MISMATCH")
        route_path = _canonical_route_path(active, tree)
        route_blob_sha = _require_sha(tree[route_path], "GITHUB_TREE_RESPONSE_INVALID")
        route_payload, item = self._blob(request.target_repository, route_blob_sha); metadata.append(item)
        records.append(ExactObjectRecord(
            request.target_repository, initial_main, main_tree, route_path, route_blob_sha,
            hashlib.sha256(route_payload).hexdigest(),
        ))
        try:
            route = _mapping(yaml.safe_load(route_payload.decode("utf-8")), "ACTIVE_ROUTE_INVALID")
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise GatewayError("CONTROL_PLANE_YAML_INVALID") from exc
        if (
            route.get("task_id") != active.get("task_id")
            or route.get("route_epoch") != active.get("route_epoch")
            or route.get("task_id") != request.expected_task_id
            or route.get("route_epoch") != request.expected_route_epoch
        ):
            raise GatewayError("ACTIVE_ROUTE_BINDING_MISMATCH")
        pr_first, item = self._pr(request.target_repository, request.pull_request_number); metadata.append(item)
        reviews, review_metadata = self._reviews(request.target_repository, request.pull_request_number); metadata.extend(review_metadata)
        domain_refs: list[str] = []
        for target in request.required_domain_freshness_targets:
            domain_sha, item = self._ref(target.repository, target.branch); metadata.append(item)
            domain_refs.append(f"github://{target.repository}@{domain_sha}:refs/heads/{target.branch}")
        final_main, item = self._ref(request.target_repository, request.target_branch); metadata.append(item)
        pr_final, item = self._pr(request.target_repository, request.pull_request_number); metadata.append(item)
        if final_main != initial_main or pr_final != pr_first:
            raise GatewayError("GITHUB_OBSERVATION_DRIFT_DETECTED")
        completed = _utc_now(); fresh_until = completed + timedelta(seconds=request.requested_max_age_seconds)
        route_fp, claim_fp, lane_fp = digest(route), digest(parsed[CONTROL_PATHS[1]]), digest(parsed[CONTROL_PATHS[2]])
        lease_fp = digest({"active": active, "control_tower": next(record.content_sha256 for record in records if record.path == CONTROL_PATHS[3])})
        pending = digest({"active": active.get("pending_approvals", []), "route": route.get("pending_approvals", [])})
        invalidators = {"pr_number": pr_first["number"], "pr_state": pr_first["state"], "head_sha": pr_first["head_sha"], "base_sha": pr_first["base_sha"], "current_main_sha": initial_main,
                        "review_state_ref": digest([record.__dict__ for record in reviews]), "merged": pr_first["merged"], "merge_commit_sha": pr_first["merge_commit_sha"],
                        "route_fingerprint": route_fp, "claim_fingerprint": claim_fp, "lane_fingerprint": lane_fp, "lease_fingerprint": lease_fp,
                        "domain_freshness_ref": digest(domain_refs), "pending_approval_ref": pending}
        observation_basis = {"request": request.request_id, "main": initial_main, "pr": pr_first, "at": _iso(completed)}
        observation_id = f"r137:{digest(observation_basis)[:24]}"
        payload = {"provider_id": PROVIDER_ID, "contract": CONTRACT_REVISION, "code_ref": "global_signal_gateway/live_observation_provider.py", "code_digest": _provider_code_digest(),
                   "observation_id": observation_id, "request_id": request.request_id, "started_at": _iso(started), "completed_at": _iso(completed), "api": API_VERSION,
                   "repository": request.target_repository, "initial_main": initial_main, "final_main": final_main, "tree": main_tree,
                   "objects": [record.__dict__ for record in records], "pr": pr_first, "reviews": [record.__dict__ for record in reviews],
                   "route": route_fp, "claim": claim_fp, "lane": lane_fp, "lease": lease_fp, "domain": digest(domain_refs), "pending": pending,
                   "metadata": list(metadata), "pagination_complete": True, "fresh_until": _iso(fresh_until), "invalidators": invalidators}
        bundle = LiveObservationEvidenceBundle(PROVIDER_ID, CONTRACT_REVISION, "global_signal_gateway/live_observation_provider.py", _provider_code_digest(), observation_id, request.request_id,
            _iso(started), _iso(completed), API_VERSION, request.target_repository, initial_main, final_main, main_tree, tuple(records), pr_first, reviews,
            route_fp, claim_fp, lane_fp, lease_fp, digest(domain_refs), pending, tuple(metadata), True, (), (), _iso(fresh_until), invalidators, digest(payload))
        _BUNDLES[bundle.identity_ref()] = bundle
        proof = AuthorityBoundLiveObservationProof(bundle.target_repository, request.pull_request_number, str(pr_first["state"]), str(pr_first["head_sha"]), str(pr_first["base_sha"]), initial_main,
            bool(pr_first["merged"]), pr_first["merge_commit_sha"], invalidators["review_state_ref"], bundle.completed_at, route_fp, claim_fp, lane_fp, lease_fp,
            bundle.domain_freshness_ref, pending, bundle.exact_refs(), PROVIDER_ID, bundle.identity_ref(), bundle.bundle_digest, bundle.fresh_until, invalidators, _LIVE_OBSERVATION_ISSUER_SEAL)
        return bundle, proof


def verify_r137_proof(proof: AuthorityBoundLiveObservationProof, checked_at: datetime) -> bool:
    """Static production verifier.  No registration API and no network call."""
    if proof.provider_id != PROVIDER_ID or not proof.provider_attribution_ref.startswith("provider://r137/evidence/"):
        return False
    bundle = _BUNDLES.get(proof.provider_attribution_ref)
    if bundle is None or bundle.bundle_digest != proof.evidence_digest:
        return False
    try:
        completed, fresh_until = instant(bundle.completed_at, "/completed_at"), instant(bundle.fresh_until, "/fresh_until")
    except GatewayError:
        return False
    return bool(
        bundle.provider_contract_revision == CONTRACT_REVISION and bundle.provider_code_digest == _provider_code_digest()
        and bundle.initial_main_sha == bundle.final_main_sha and completed <= checked_at <= fresh_until
        and bundle.pagination_complete and not bundle.warnings
        and tuple(proof.exact_refs) == bundle.exact_refs() and proof.invalidation_fingerprints == bundle.invalidation_fingerprints
        and proof.repository == bundle.target_repository and proof.current_main_sha == bundle.initial_main_sha
        and proof.pr_number == bundle.pr["number"] and proof.pr_state == bundle.pr["state"]
        and proof.head_sha == bundle.pr["head_sha"] and proof.base_sha == bundle.pr["base_sha"]
        and proof.merged == bundle.pr["merged"] and proof.merge_commit_sha == bundle.pr["merge_commit_sha"]
        and proof.review_state_ref == bundle.invalidation_fingerprints["review_state_ref"]
        and proof.route_fingerprint == bundle.route_fingerprint and proof.claim_fingerprint == bundle.claim_fingerprint
        and proof.lane_fingerprint == bundle.lane_fingerprint and proof.lease_fingerprint == bundle.lease_fingerprint
        and proof.domain_freshness_ref == bundle.domain_freshness_ref and proof.pending_approval_ref == bundle.pending_approval_ref
    )
