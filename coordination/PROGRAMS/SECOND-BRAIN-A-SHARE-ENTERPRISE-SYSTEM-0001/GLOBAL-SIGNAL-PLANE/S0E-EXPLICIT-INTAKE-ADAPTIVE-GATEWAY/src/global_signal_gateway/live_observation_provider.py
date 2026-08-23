"""R137's bounded, public GitHub, on-demand observation provider.

This module is deliberately an evidence producer, not a release, merge, or
Control Tower implementation.  Its network surface is fixed to public GitHub
GET observations.  R145 adaptively reuses the same provider to attest an
owner-domain authority object only when an exact canonical coordinator task
brief governs the requested domain/repository/authority surface.  No domain
registry or second provider is introduced.

Observed source bodies remain transient while they are validated.  Evidence
bundles persist only public-safe identities, hashes and opaque refs.
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
from typing import Any, Mapping
import yaml
from .gateway import AuthorityBoundLiveObservationProof, GatewayError, _LIVE_OBSERVATION_ISSUER_SEAL, digest, instant
from .semantic_authority import SEMANTIC_AUTHORITY_FIELDS, governed_semantic_authority_ref, native_semantic_authority_identity
PROVIDER_ID = 'r137-public-github-on-demand-v1'
CONTRACT_REVISION = 'PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1'
API_HOST = 'api.github.com'
API_VERSION = '2026-03-10'
TARGET_REPOSITORY = 'vxz2datoubo/second-brain-coordination'
DOMAIN_REPOSITORY = 'vxz2datoubo/eustia-ai-film'
MAX_RESPONSE_BYTES = 1000000
MAX_PAGES = 20
MAX_AGE_SECONDS = 300
REQUEST_TIMEOUT_SECONDS = 10
ACTIVE_TASK_PATH = 'coordination/ACTIVE-CODEX-TASK.yaml'
CONTROL_PATHS = (ACTIVE_TASK_PATH, 'coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml', 'coordination/ACTIVE-PROGRAM-LANES.yaml', 'coordination/PROGRAM-CONTROL-TOWER.md')
_SAFE_SHA = re.compile('^[0-9a-f]{40,64}$')
_SAFE_PATH = re.compile('^[A-Za-z0-9_./-]+$')
_SAFE_REPOSITORY = re.compile('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')
_ALLOWED_ENDPOINTS = (re.compile('^/repos/vxz2datoubo/(?:second-brain-coordination|eustia-ai-film)/git/ref/heads/main$'), re.compile('^/repos/vxz2datoubo/second-brain-coordination/git/commits/[0-9a-f]{40,64}$'), re.compile('^/repos/vxz2datoubo/second-brain-coordination/git/trees/[0-9a-f]{40,64}\\?recursive=1$'), re.compile('^/repos/vxz2datoubo/second-brain-coordination/git/blobs/[0-9a-f]{40,64}$'), re.compile('^/repos/vxz2datoubo/second-brain-coordination/pulls/[1-9][0-9]*$'), re.compile('^/repos/vxz2datoubo/second-brain-coordination/pulls/[1-9][0-9]*/reviews\\?per_page=100&page=[1-9][0-9]*$'))
_REQUIRED_AUTHORITY_BINDING_FIELDS = frozenset({'domain_id', 'project_id', 'repository', 'canonical_commit', 'authority_path_or_contract_ref', 'provenance_or_exact_read_proof'})
_BUNDLES: dict[str, 'LiveObservationEvidenceBundle'] = {}

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()

def _git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(payload)).encode('ascii') + b'\x00' + payload).hexdigest()

def _provider_code_digest() -> str:
    source = inspect.getsourcefile(_provider_code_digest)
    if source is None:
        raise GatewayError('PROVIDER_CODE_IDENTITY_UNAVAILABLE')
    return hashlib.sha256(Path(source).read_bytes()).hexdigest()

def _require_sha(value: Any, code: str) -> str:
    if not isinstance(value, str) or not _SAFE_SHA.fullmatch(value):
        raise GatewayError(code)
    return value

def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise GatewayError(code)
    return value

def _safe_contract_path(path: Any) -> str:
    if not isinstance(path, str) or not path:
        raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_INVALID')
    pure = PurePosixPath(path)
    if '\\' in path or '//' in path or pure.is_absolute() or any((part in {'', '.', '..'} for part in pure.parts)) or (not path.startswith('coordination/TASK-BRIEFS/')) or (not path.endswith('.yaml')) or (not _SAFE_PATH.fullmatch(path)):
        raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_INVALID')
    return path

def _canonical_route_path(active: Mapping[str, Any], tree: Mapping[str, str]) -> str:
    """Resolve only the active task's exact-main route pointer, fail-closed."""
    path = active.get('canonical_route')
    if not isinstance(path, str) or not path:
        raise GatewayError('CANONICAL_ROUTE_POINTER_INVALID')
    pure_path = PurePosixPath(path)
    if '\\' in path or '//' in path or (not path.startswith('coordination/ROUTES/')) or (not path.endswith('.yaml')) or pure_path.is_absolute() or any((part in {'', '.', '..'} for part in pure_path.parts)) or (not _SAFE_PATH.fullmatch(path)):
        raise GatewayError('CANONICAL_ROUTE_POINTER_INVALID')
    if path not in tree:
        raise GatewayError('CANONICAL_ROUTE_POINTER_MISSING')
    return path

def _route_binding(route: Mapping[str, Any]) -> tuple[str, int]:
    """Read legacy top-level or current nested route identity without ambiguity."""
    nested_value = route.get('binding')
    if nested_value is None:
        nested: Mapping[str, Any] = {}
    elif isinstance(nested_value, Mapping):
        nested = nested_value
    else:
        raise GatewayError('ACTIVE_ROUTE_BINDING_INVALID')
    top_task = route.get('task_id')
    top_epoch = route.get('route_epoch')
    nested_task = nested.get('task_id')
    nested_epoch = nested.get('route_epoch')
    if top_task is not None and nested_task is not None and (top_task != nested_task):
        raise GatewayError('ACTIVE_ROUTE_BINDING_AMBIGUOUS')
    if top_epoch is not None and nested_epoch is not None and (top_epoch != nested_epoch):
        raise GatewayError('ACTIVE_ROUTE_BINDING_AMBIGUOUS')
    task_id = top_task if top_task is not None else nested_task
    route_epoch = top_epoch if top_epoch is not None else nested_epoch
    if not isinstance(task_id, str) or not task_id or (not isinstance(route_epoch, int)):
        raise GatewayError('ACTIVE_ROUTE_BINDING_INVALID')
    return (task_id, route_epoch)

def _domain_authority_spec(contract: Mapping[str, Any], *, domain_id: str, repository: str) -> tuple[str, bool]:
    """Resolve one domain authority path only from a canonical task brief.

    The caller selects a domain to observe but cannot define its authority path,
    project identity, write owner or schema.  The exact-main task brief must
    independently bind that domain to the repository and read-only policy.
    """
    release = _mapping(contract.get('release_preflight'), 'DOMAIN_AUTHORITY_CONTRACT_INVALID')
    if release.get('strategy') != 'ADAPT_EXISTING / NO_NEW_PARALLEL_DOMAIN_AUTHORITY':
        raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_INVALID')
    required = contract.get('required_domain_authority_binding')
    if not isinstance(required, list) or not _REQUIRED_AUTHORITY_BINDING_FIELDS <= set(map(str, required)):
        raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_INVALID')
    domains = _mapping(contract.get('mandatory_domain_regressions'), 'DOMAIN_AUTHORITY_CONTRACT_INVALID')
    spec = _mapping(domains.get(domain_id), 'DOMAIN_AUTHORITY_TARGET_UNGOVERNED')
    if spec.get('repository') != repository:
        raise GatewayError('DOMAIN_AUTHORITY_REPOSITORY_MISMATCH')
    if spec.get('write_policy') != 'READ_ONLY_FROM_SIGNAL_TOWER':
        raise GatewayError('DOMAIN_AUTHORITY_READ_ONLY_POLICY_REQUIRED')
    hints = [value for value in (spec.get('authority_hint'), spec.get('architecture_hint')) if isinstance(value, str) and value.strip()]
    if len(hints) != 1:
        raise GatewayError('DOMAIN_AUTHORITY_PATH_UNRESOLVED')
    path = hints[0]
    pure = PurePosixPath(path)
    if '\\' in path or '//' in path or pure.is_absolute() or any((part in {'', '.', '..'} for part in pure.parts)):
        raise GatewayError('DOMAIN_AUTHORITY_PATH_INVALID')
    private = str(spec.get('repository_visibility', 'PUBLIC')).upper() == 'PRIVATE'
    return (path, private)

@dataclass(frozen=True)
class DomainFreshnessTarget:
    repository: str
    branch: str = 'main'
    domain_id: str | None = None
    authority_contract_path: str | None = None

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
        if not self.request_id or self.provider_contract_revision != CONTRACT_REVISION or self.target_repository != TARGET_REPOSITORY or (self.target_branch != 'main'):
            raise GatewayError('LIVE_OBSERVATION_REQUEST_FORBIDDEN')
        if not isinstance(self.pull_request_number, int) or self.pull_request_number <= 0:
            raise GatewayError('PULL_REQUEST_REQUIRED')
        if not self.expected_task_id or not isinstance(self.expected_route_epoch, int):
            raise GatewayError('EXPECTED_ROUTE_BINDING_REQUIRED')
        if tuple(self.required_control_plane_paths) != CONTROL_PATHS:
            raise GatewayError('CONTROL_PLANE_PATH_SET_FORBIDDEN')
        if self.required_review_scope != 'ALL_RAW_REVIEWS':
            raise GatewayError('REVIEW_SCOPE_FORBIDDEN')
        if not 0 < self.requested_max_age_seconds <= MAX_AGE_SECONDS:
            raise GatewayError('OBSERVATION_AGE_OUT_OF_POLICY')
        instant(self.requested_at, '/requested_at')
        if not self.required_domain_freshness_targets:
            raise GatewayError('DOMAIN_FRESHNESS_TARGET_REQUIRED')
        for target in self.required_domain_freshness_targets:
            if not isinstance(target.repository, str) or not _SAFE_REPOSITORY.fullmatch(target.repository):
                raise GatewayError('DOMAIN_TARGET_FORBIDDEN')
            if target.branch != 'main':
                raise GatewayError('DOMAIN_TARGET_FORBIDDEN')
            governed = target.domain_id is not None or target.authority_contract_path is not None
            if not governed:
                if target.repository != DOMAIN_REPOSITORY:
                    raise GatewayError('DOMAIN_TARGET_FORBIDDEN')
                continue
            if not isinstance(target.domain_id, str) or not target.domain_id.strip() or target.authority_contract_path is None:
                raise GatewayError('DOMAIN_AUTHORITY_TARGET_INVALID')
            _safe_contract_path(target.authority_contract_path)

@dataclass(frozen=True)
class ExactObjectRecord:
    repository: str
    commit_sha: str
    tree_sha: str
    path: str
    blob_sha: str
    content_sha256: str

    def ref(self) -> str:
        return f'github://{self.repository}@{self.commit_sha}/{self.path}#blob={self.blob_sha};sha256={self.content_sha256}'

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
    domain_authority_refs: tuple[str, ...]
    bundle_digest: str

    def identity_ref(self) -> str:
        return f'provider://r137/evidence/{self.observation_id}#sha256={self.bundle_digest}'

    def exact_refs(self) -> tuple[str, ...]:
        return (self.identity_ref(),) + tuple((record.ref() for record in self.exact_objects)) + tuple(self.domain_authority_refs)

class LiveObservationProvider:
    """Serial, fixed-host observer. Subclassing ``_get_json`` is test-only."""

    def __init__(self) -> None:
        self._governed_domain_repositories: set[str] = set()

    def _dynamic_domain_endpoint_allowed(self, path: str) -> bool:
        repositories = getattr(self, '_governed_domain_repositories', set())
        for repository in repositories:
            prefix = f'/repos/{repository}'
            if path == f'{prefix}/git/ref/heads/main':
                return True
            if re.fullmatch(re.escape(prefix) + '/git/commits/[0-9a-f]{40,64}', path):
                return True
            if re.fullmatch(re.escape(prefix) + '/git/trees/[0-9a-f]{40,64}\\?recursive=1', path):
                return True
            if re.fullmatch(re.escape(prefix) + '/git/blobs/[0-9a-f]{40,64}', path):
                return True
        return False

    def _get_json(self, path: str) -> tuple[Mapping[str, str], Any, Mapping[str, Any]]:
        allowed = any((pattern.fullmatch(path) for pattern in _ALLOWED_ENDPOINTS)) or self._dynamic_domain_endpoint_allowed(path)
        if not path.startswith('/repos/') or '//' in path or '..' in PurePosixPath(path).parts or (not allowed):
            raise GatewayError('GITHUB_ENDPOINT_FORBIDDEN')
        connection = http.client.HTTPSConnection(API_HOST, timeout=REQUEST_TIMEOUT_SECONDS)
        try:
            connection.request("GET", path, headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': API_VERSION, 'User-Agent': 'second-brain-r137-public-observer'})
            response = connection.getresponse()
            headers = {key.casefold(): value for key, value in response.getheaders()}
            if response.status < 200 or response.status >= 300:
                raise GatewayError('GITHUB_TRANSPORT_OR_STATUS_UNVERIFIED')
            if 300 <= response.status < 400 or 'location' in headers:
                raise GatewayError('GITHUB_REDIRECT_FORBIDDEN')
            media_type = headers.get('content-type', '').split(';', 1)[0].strip().casefold()
            if media_type != 'application/json':
                raise GatewayError('GITHUB_MEDIA_TYPE_FORBIDDEN')
            declared = headers.get('content-length')
            if declared is not None and (not declared.isdigit() or int(declared) > MAX_RESPONSE_BYTES):
                raise GatewayError('GITHUB_RESPONSE_TOO_LARGE')
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise GatewayError('GITHUB_RESPONSE_TOO_LARGE')
            try:
                decoded = payload.decode('utf-8')
                value = json.loads(decoded)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise GatewayError('GITHUB_JSON_INVALID') from exc
            metadata: Mapping[str, Any] = {'path': path, 'status': response.status, 'content_sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload)}
            return (headers, value, metadata)
        except (OSError, http.client.HTTPException) as exc:
            raise GatewayError('GITHUB_TRANSPORT_OR_STATUS_UNVERIFIED') from exc
        finally:
            connection.close()

    def _ref(self, repository: str, branch: str) -> tuple[str, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f'/repos/{repository}/git/ref/heads/{branch}')
        obj = _mapping(value, 'GITHUB_BRANCH_RESPONSE_INVALID')
        return (_require_sha(_mapping(obj.get('object'), 'GITHUB_BRANCH_RESPONSE_INVALID').get('sha'), 'GITHUB_BRANCH_RESPONSE_INVALID'), metadata)

    def _commit_tree(self, repository: str, commit: str) -> tuple[str, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f'/repos/{repository}/git/commits/{commit}')
        obj = _mapping(value, 'GITHUB_COMMIT_RESPONSE_INVALID')
        return (_require_sha(_mapping(obj.get('tree'), 'GITHUB_COMMIT_RESPONSE_INVALID').get('sha'), 'GITHUB_COMMIT_RESPONSE_INVALID'), metadata)

    def _tree(self, repository: str, tree_sha: str) -> tuple[Mapping[str, str], Mapping[str, Any]]:
        _, value, metadata = self._get_json(f'/repos/{repository}/git/trees/{tree_sha}?recursive=1')
        tree_response = _mapping(value, 'GITHUB_TREE_RESPONSE_INVALID')
        if tree_response.get('truncated') is not False:
            raise GatewayError('GITHUB_TREE_TRUNCATED_OR_INVALID')
        entries = tree_response.get('tree')
        if not isinstance(entries, list):
            raise GatewayError('GITHUB_TREE_RESPONSE_INVALID')
        result: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, Mapping):
                raise GatewayError('GITHUB_TREE_RESPONSE_INVALID')
            path, kind, sha = (entry.get('path'), entry.get('type'), entry.get('sha'))
            if isinstance(path, str) and kind == 'blob' and isinstance(sha, str):
                result[path] = sha
        return (result, metadata)

    def _blob(self, repository: str, blob_sha: str) -> tuple[bytes, Mapping[str, Any]]:
        _, value, metadata = self._get_json(f'/repos/{repository}/git/blobs/{blob_sha}')
        obj = _mapping(value, 'GITHUB_BLOB_RESPONSE_INVALID')
        if obj.get('encoding') != 'base64' or not isinstance(obj.get('content'), str):
            raise GatewayError('GITHUB_BLOB_RESPONSE_INVALID')
        try:
            payload = b64decode(obj['content'].replace('\n', ''), validate=True)
        except (ValueError, TypeError) as exc:
            raise GatewayError('GITHUB_BLOB_RESPONSE_INVALID') from exc
        if len(payload) > MAX_RESPONSE_BYTES or _git_blob_sha(payload) != blob_sha:
            raise GatewayError('GITHUB_BLOB_IDENTITY_MISMATCH')
        return (payload, metadata)

    def _reviews(self, repository: str, number: int) -> tuple[tuple[RawReviewRecord, ...], tuple[Mapping[str, Any], ...]]:
        page, records, evidence = (1, [], [])
        while page <= MAX_PAGES:
            headers, value, metadata = self._get_json(f'/repos/{repository}/pulls/{number}/reviews?per_page=100&page={page}')
            if not isinstance(value, list):
                raise GatewayError('GITHUB_REVIEWS_RESPONSE_INVALID')
            evidence.append(metadata)
            for item in value:
                item = _mapping(item, 'GITHUB_REVIEWS_RESPONSE_INVALID')
                actor = _mapping(item.get('user'), 'GITHUB_REVIEWS_RESPONSE_INVALID')
                review_id, state = (item.get('id'), item.get('state'))
                if not isinstance(review_id, int) or not isinstance(state, str):
                    raise GatewayError('GITHUB_REVIEWS_RESPONSE_INVALID')
                records.append(RawReviewRecord(review_id, state, item.get('commit_id') if isinstance(item.get('commit_id'), str) else None, item.get('submitted_at') if isinstance(item.get('submitted_at'), str) else None, f"github-user://{actor.get('id')}"))
            link = headers.get('link', '')
            has_next = 'rel="next"' in link
            if not has_next:
                return (tuple(records), tuple(evidence))
            expected = f'page={page + 1}'
            if expected not in link:
                raise GatewayError('GITHUB_PAGINATION_INCOMPLETE')
            page += 1
        raise GatewayError('GITHUB_PAGINATION_INCOMPLETE')

    def _pr(self, repository: str, number: int) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
        _, value, metadata = self._get_json(f'/repos/{repository}/pulls/{number}')
        pr = _mapping(value, 'GITHUB_PR_RESPONSE_INVALID')
        head = _require_sha(_mapping(pr.get('head'), 'GITHUB_PR_RESPONSE_INVALID').get('sha'), 'GITHUB_PR_RESPONSE_INVALID')
        base = _require_sha(_mapping(pr.get('base'), 'GITHUB_PR_RESPONSE_INVALID').get('sha'), 'GITHUB_PR_RESPONSE_INVALID')
        state = pr.get('state')
        if not isinstance(state, str) or not isinstance(pr.get('merged'), bool):
            raise GatewayError('GITHUB_PR_RESPONSE_INVALID')
        merge_sha = pr.get('merge_commit_sha')
        if merge_sha is not None and (not _SAFE_SHA.fullmatch(merge_sha)):
            raise GatewayError('GITHUB_PR_RESPONSE_INVALID')
        if pr['merged'] and merge_sha is None:
            raise GatewayError('GITHUB_PR_RESPONSE_INVALID')
        return ({'number': number, 'state': state, 'head_sha': head, 'base_sha': base, 'merged': pr['merged'], 'merge_commit_sha': merge_sha}, metadata)

    def _coordinator_yaml_object(self, *, path: str, commit: str, tree_sha: str, tree: Mapping[str, str], records: list[ExactObjectRecord], metadata: list[Mapping[str, Any]]) -> Mapping[str, Any]:
        if path not in tree:
            raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_MISSING')
        blob_sha = _require_sha(tree[path], 'GITHUB_TREE_RESPONSE_INVALID')
        payload, item = self._blob(TARGET_REPOSITORY, blob_sha)
        metadata.append(item)
        record = ExactObjectRecord(TARGET_REPOSITORY, commit, tree_sha, path, blob_sha, hashlib.sha256(payload).hexdigest())
        if not any((prior.repository == record.repository and prior.commit_sha == record.commit_sha and (prior.path == record.path) and (prior.blob_sha == record.blob_sha) for prior in records)):
            records.append(record)
        try:
            parsed = yaml.safe_load(payload.decode('utf-8'))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise GatewayError('DOMAIN_AUTHORITY_CONTRACT_INVALID') from exc
        return _mapping(parsed, 'DOMAIN_AUTHORITY_CONTRACT_INVALID')

    def observe(self, request: LiveObservationRequest) -> tuple[LiveObservationEvidenceBundle, AuthorityBoundLiveObservationProof]:
        request.validate()
        started = _utc_now()
        metadata: list[Mapping[str, Any]] = []
        initial_main, item = self._ref(request.target_repository, request.target_branch)
        metadata.append(item)
        main_tree, item = self._commit_tree(request.target_repository, initial_main)
        metadata.append(item)
        tree, item = self._tree(request.target_repository, main_tree)
        metadata.append(item)
        records: list[ExactObjectRecord] = []
        parsed: dict[str, Any] = {}
        for path in request.required_control_plane_paths:
            if not _SAFE_PATH.fullmatch(path) or path not in tree:
                raise GatewayError('GITHUB_REQUIRED_PATH_MISSING')
            blob_sha = _require_sha(tree[path], 'GITHUB_TREE_RESPONSE_INVALID')
            payload, item = self._blob(request.target_repository, blob_sha)
            metadata.append(item)
            record = ExactObjectRecord(request.target_repository, initial_main, main_tree, path, blob_sha, hashlib.sha256(payload).hexdigest())
            records.append(record)
            if path.endswith('.yaml'):
                try:
                    parsed[path] = yaml.safe_load(payload.decode('utf-8'))
                except (UnicodeDecodeError, yaml.YAMLError) as exc:
                    raise GatewayError('CONTROL_PLANE_YAML_INVALID') from exc
        active = _mapping(parsed[ACTIVE_TASK_PATH], 'ACTIVE_TASK_INVALID')
        if active.get('task_id') != request.expected_task_id or active.get('route_epoch') != request.expected_route_epoch:
            raise GatewayError('ACTIVE_TASK_BINDING_MISMATCH')
        route_path = _canonical_route_path(active, tree)
        route_blob_sha = _require_sha(tree[route_path], 'GITHUB_TREE_RESPONSE_INVALID')
        route_payload, item = self._blob(request.target_repository, route_blob_sha)
        metadata.append(item)
        records.append(ExactObjectRecord(request.target_repository, initial_main, main_tree, route_path, route_blob_sha, hashlib.sha256(route_payload).hexdigest()))
        try:
            route = _mapping(yaml.safe_load(route_payload.decode('utf-8')), 'ACTIVE_ROUTE_INVALID')
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise GatewayError('CONTROL_PLANE_YAML_INVALID') from exc
        route_task_id, route_epoch = _route_binding(route)
        if route_task_id != active.get('task_id') or route_epoch != active.get('route_epoch') or route_task_id != request.expected_task_id or (route_epoch != request.expected_route_epoch):
            raise GatewayError('ACTIVE_ROUTE_BINDING_MISMATCH')
        pr_first, item = self._pr(request.target_repository, request.pull_request_number)
        metadata.append(item)
        reviews, review_metadata = self._reviews(request.target_repository, request.pull_request_number)
        metadata.extend(review_metadata)
        domain_refs: list[str] = []
        domain_authority_refs: list[str] = []
        domain_states: list[tuple[str, str, str]] = []
        for target in request.required_domain_freshness_targets:
            authority_path: str | None = None
            governed_identity: dict[str, str] | None = None
            if target.authority_contract_path is not None:
                contract_path = _safe_contract_path(target.authority_contract_path)
                contract = self._coordinator_yaml_object(path=contract_path, commit=initial_main, tree_sha=main_tree, tree=tree, records=records, metadata=metadata)
                assert target.domain_id is not None
                authority_path, private = _domain_authority_spec(contract, domain_id=target.domain_id, repository=target.repository)
                if private:
                    raise GatewayError('DOMAIN_AUTHORITY_PRIVATE_SOURCE_UNAVAILABLE')
                self._governed_domain_repositories.add(target.repository)
            domain_sha, item = self._ref(target.repository, target.branch)
            metadata.append(item)
            domain_refs.append(f'github://{target.repository}@{domain_sha}:refs/heads/{target.branch}')
            domain_states.append((target.repository, target.branch, domain_sha))
            if authority_path is not None:
                domain_tree_sha, item = self._commit_tree(target.repository, domain_sha)
                metadata.append(item)
                domain_tree, item = self._tree(target.repository, domain_tree_sha)
                metadata.append(item)
                if authority_path not in domain_tree:
                    raise GatewayError('DOMAIN_AUTHORITY_SOURCE_MISSING')
                authority_blob = _require_sha(domain_tree[authority_path], 'GITHUB_TREE_RESPONSE_INVALID')
                authority_payload, item = self._blob(target.repository, authority_blob)
                metadata.append(item)
                authority_record = ExactObjectRecord(target.repository, domain_sha, domain_tree_sha, authority_path, authority_blob, hashlib.sha256(authority_payload).hexdigest())
                records.append(authority_record)
                native = native_semantic_authority_identity(authority_payload, path=authority_path)
                assert target.domain_id is not None
                governed_identity = {'domain_id': target.domain_id, 'project_id': native['project_id'], 'authority_schema_version': native['authority_schema_version'], 'writeback_owner': target.domain_id, 'observation_mode': 'READ_ONLY'}
                for field_name in ('domain_id', 'writeback_owner', 'observation_mode'):
                    native_value = native.get(field_name)
                    if native_value is not None and native_value != governed_identity[field_name]:
                        raise GatewayError('DOMAIN_AUTHORITY_NATIVE_IDENTITY_CONFLICT')
                if set(governed_identity) != set(SEMANTIC_AUTHORITY_FIELDS):
                    raise GatewayError('DOMAIN_AUTHORITY_SEMANTIC_IDENTITY_INCOMPLETE')
                domain_authority_refs.append(governed_semantic_authority_ref(authority_record.ref(), governed_identity))
        for repository, branch, expected_sha in domain_states:
            final_domain_sha, item = self._ref(repository, branch)
            metadata.append(item)
            if final_domain_sha != expected_sha:
                raise GatewayError('DOMAIN_AUTHORITY_SOURCE_DRIFT_DETECTED')
        final_main, item = self._ref(request.target_repository, request.target_branch)
        metadata.append(item)
        pr_final, item = self._pr(request.target_repository, request.pull_request_number)
        metadata.append(item)
        if final_main != initial_main or pr_final != pr_first:
            raise GatewayError('GITHUB_OBSERVATION_DRIFT_DETECTED')
        completed = _utc_now()
        fresh_until = completed + timedelta(seconds=request.requested_max_age_seconds)
        route_fp = digest(route)
        claim_fp = digest(parsed[CONTROL_PATHS[1]])
        lane_fp = digest(parsed[CONTROL_PATHS[2]])
        lease_fp = digest({'active': active, 'control_tower': next((record.content_sha256 for record in records if record.path == CONTROL_PATHS[3]))})
        pending = digest({'active': active.get('pending_approvals', []), 'route': route.get('pending_approvals', [])})
        invalidators = {'pr_number': pr_first['number'], 'pr_state': pr_first['state'], 'head_sha': pr_first['head_sha'], 'base_sha': pr_first['base_sha'], 'current_main_sha': initial_main, 'review_state_ref': digest([record.__dict__ for record in reviews]), 'merged': pr_first['merged'], 'merge_commit_sha': pr_first['merge_commit_sha'], 'route_fingerprint': route_fp, 'claim_fingerprint': claim_fp, 'lane_fingerprint': lane_fp, 'lease_fingerprint': lease_fp, 'domain_freshness_ref': digest(domain_refs), 'pending_approval_ref': pending}
        observation_basis = {'request': request.request_id, 'main': initial_main, 'pr': pr_first, 'at': _iso(completed)}
        observation_id = f'r137:{digest(observation_basis)[:24]}'
        code_digest = _provider_code_digest()
        payload = {'provider_id': PROVIDER_ID, 'contract': CONTRACT_REVISION, 'code_ref': 'global_signal_gateway/live_observation_provider.py', 'code_digest': code_digest, 'observation_id': observation_id, 'request_id': request.request_id, 'started_at': _iso(started), 'completed_at': _iso(completed), 'api': API_VERSION, 'repository': request.target_repository, 'initial_main': initial_main, 'final_main': final_main, 'tree': main_tree, 'objects': [record.__dict__ for record in records], 'domain_authority_refs': list(domain_authority_refs), 'pr': pr_first, 'reviews': [record.__dict__ for record in reviews], 'route': route_fp, 'claim': claim_fp, 'lane': lane_fp, 'lease': lease_fp, 'domain': digest(domain_refs), 'pending': pending, 'metadata': list(metadata), 'pagination_complete': True, 'fresh_until': _iso(fresh_until), 'invalidators': invalidators}
        bundle = LiveObservationEvidenceBundle(PROVIDER_ID, CONTRACT_REVISION, 'global_signal_gateway/live_observation_provider.py', code_digest, observation_id, request.request_id, _iso(started), _iso(completed), API_VERSION, request.target_repository, initial_main, final_main, main_tree, tuple(records), pr_first, reviews, route_fp, claim_fp, lane_fp, lease_fp, digest(domain_refs), pending, tuple(metadata), True, (), (), _iso(fresh_until), invalidators, tuple(domain_authority_refs), digest(payload))
        _BUNDLES[bundle.identity_ref()] = bundle
        proof = AuthorityBoundLiveObservationProof(bundle.target_repository, request.pull_request_number, str(pr_first['state']), str(pr_first['head_sha']), str(pr_first['base_sha']), initial_main, bool(pr_first['merged']), pr_first['merge_commit_sha'], invalidators['review_state_ref'], bundle.completed_at, route_fp, claim_fp, lane_fp, lease_fp, bundle.domain_freshness_ref, pending, bundle.exact_refs(), PROVIDER_ID, bundle.identity_ref(), bundle.bundle_digest, bundle.fresh_until, invalidators, _LIVE_OBSERVATION_ISSUER_SEAL)
        return (bundle, proof)

def verify_r137_proof(proof: AuthorityBoundLiveObservationProof, checked_at: datetime) -> bool:
    """Static production verifier. No registration API and no network call."""
    if proof.provider_id != PROVIDER_ID or not proof.provider_attribution_ref.startswith('provider://r137/evidence/'):
        return False
    bundle = _BUNDLES.get(proof.provider_attribution_ref)
    if bundle is None or bundle.bundle_digest != proof.evidence_digest:
        return False
    try:
        completed = instant(bundle.completed_at, '/completed_at')
        fresh_until = instant(bundle.fresh_until, '/fresh_until')
    except GatewayError:
        return False
    return bool(bundle.provider_contract_revision == CONTRACT_REVISION and bundle.provider_code_digest == _provider_code_digest() and (bundle.initial_main_sha == bundle.final_main_sha) and (completed <= checked_at <= fresh_until) and bundle.pagination_complete and (not bundle.warnings) and (tuple(proof.exact_refs) == bundle.exact_refs()) and (proof.invalidation_fingerprints == bundle.invalidation_fingerprints) and (proof.repository == bundle.target_repository) and (proof.current_main_sha == bundle.initial_main_sha) and (proof.pr_number == bundle.pr['number']) and (proof.pr_state == bundle.pr['state']) and (proof.head_sha == bundle.pr['head_sha']) and (proof.base_sha == bundle.pr['base_sha']) and (proof.merged == bundle.pr['merged']) and (proof.merge_commit_sha == bundle.pr['merge_commit_sha']) and (proof.review_state_ref == bundle.invalidation_fingerprints['review_state_ref']) and (proof.route_fingerprint == bundle.route_fingerprint) and (proof.claim_fingerprint == bundle.claim_fingerprint) and (proof.lane_fingerprint == bundle.lane_fingerprint) and (proof.lease_fingerprint == bundle.lease_fingerprint) and (proof.domain_freshness_ref == bundle.domain_freshness_ref) and (proof.pending_approval_ref == bundle.pending_approval_ref))
