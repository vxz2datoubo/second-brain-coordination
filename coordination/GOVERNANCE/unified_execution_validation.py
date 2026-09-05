"""Dependency-free trust-boundary validators for the unified execution fabric."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence
TRUSTED_CONTROL_PLANE_REPOSITORY = 'vxz2datoubo/second-brain-coordination'
TRUSTED_CONTROL_PLANE_URL = 'https://github.com/vxz2datoubo/second-brain-coordination.git'
ACTIVE_TASK_INDEX_REF = 'coordination/ACTIVE-WORKBUDDY-TASK.yaml'
PROJECT_ADAPTER_PATHS = ('coordination/EXECUTION/PROJECT-ADAPTERS/SECOND-BRAIN.yaml', 'coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml', 'coordination/EXECUTION/PROJECT-ADAPTERS/REALTIME-INTERACTIVE-FILM.yaml', 'coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml')

class ExecutionContractError(ValueError):
    """Raised when an execution contract fails closed."""
COMMON_IDENTITY_FIELDS = ('control_plane_repository', 'execution_repository', 'project_id', 'task_id', 'route_epoch', 'exact_base_sha', 'implementation_branch', 'collision_domain')
AUTHORITY_REF_FIELDS = ('active_task_index_ref', 'canonical_route_ref', 'work_claim_ref', 'task_lease_ref', 'executor_reservation_ref', 'prewrite_snapshot_ref', 'executable_batch_ref')
GLOBAL_CARRIERS = {'GPT_DIRECT', 'WORKBUDDY_CLI_HEADLESS', 'WORKBUDDY_CLI_WEBUI', 'WORKBUDDY_DESKTOP_INTERACTIVE', 'CODEX_FRONTIER_ESCALATION'}
NON_WEAKENABLE_INVARIANTS = {'single_writer_per_collision_domain', 'exact_head_review_identity', 'no_self_review', 'no_self_merge', 'credential_secret_exclusion', 'active_task_authority_required'}
PROJECT_ADAPTER_REQUIRED_FIELDS = ('project_id', 'global_protocol_id', 'inherits_global_invariants', 'control_plane_repository', 'execution_repository', 'repositories', 'canonical_entrypoints', 'authority', 'allowed_execution_carriers', 'default_model_profiles', 'collision_domains', 'tool_interfaces', 'hard_boundaries', 'acceptance', 'handoff')
KNOWN_PROJECT_IDS = {'SECOND_BRAIN', 'TRADING_SYSTEM', 'REALTIME_INTERACTIVE_FILM_GAME', 'AI_DIRECTOR'}
_ISSUER = object()

@dataclass(frozen=True)
class VerifiedCanonicalAuthority:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _ISSUER:
            raise ExecutionContractError('canonical_authority: untrusted issuer')
        return self._payload

@dataclass(frozen=True)
class VerifiedReleaseWitness:
    _payload: Mapping[str, Any]
    _issuer: object

    def as_mapping(self) -> Mapping[str, Any]:
        if self._issuer is not _ISSUER:
            raise ExecutionContractError('release_witness: untrusted issuer')
        return self._payload

def _freeze(mapping: Mapping[str, Any]) -> Mapping[str, Any]:

    def convert(value: Any) -> Any:
        if isinstance(value, Mapping):
            return MappingProxyType({k: convert(v) for k, v in value.items()})
        if isinstance(value, list):
            return tuple((convert(v) for v in value))
        return value
    return MappingProxyType({k: convert(v) for k, v in mapping.items()})

def _issue_authority(payload: Mapping[str, Any]) -> VerifiedCanonicalAuthority:
    return VerifiedCanonicalAuthority(_freeze(payload), _ISSUER)

def _issue_release(payload: Mapping[str, Any]) -> VerifiedReleaseWitness:
    return VerifiedReleaseWitness(_freeze(payload), _ISSUER)

def _require(mapping: Mapping[str, Any], fields: Sequence[str], label: str) -> None:
    missing = [field for field in fields if field not in mapping or mapping[field] in (None, '')]
    if missing:
        raise ExecutionContractError(f"{label}: missing required fields: {', '.join(missing)}")

def _same_identity(left: Mapping[str, Any], right: Mapping[str, Any], label: str) -> None:
    _require(left, COMMON_IDENTITY_FIELDS, f'{label}.left')
    _require(right, COMMON_IDENTITY_FIELDS, f'{label}.right')
    mismatched = [field for field in COMMON_IDENTITY_FIELDS if left[field] != right[field]]
    if mismatched:
        raise ExecutionContractError(f"{label}: identity mismatch: {', '.join(mismatched)}")

def _sha(data: bytes) -> str:
    return 'sha256:' + sha256(data).hexdigest()

def _json_ready(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    return value

def _json_digest(value: Any) -> str:
    encoded = json.dumps(_json_ready(value), sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return _sha(encoded)

def _scalar(text: str, key: str, *, required: bool=True) -> Any:
    match = re.search(f'(?m)^{re.escape(key)}:\\s*(.*?)\\s*$', text)
    if not match:
        if required:
            raise ExecutionContractError(f'yaml: missing top-level scalar {key}')
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in {'true', 'false'}:
        return raw == 'true'
    if raw in {'null', '~'}:
        return None
    if re.fullmatch('-?\\d+', raw):
        return int(raw)
    return raw

def _section(text: str, key: str, *, required: bool=True) -> str | None:
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if re.fullmatch(f'{re.escape(key)}:\\s*', line):
            start = idx + 1
            break
    if start is None:
        if required:
            raise ExecutionContractError(f'yaml: missing section {key}')
        return None
    end = len(lines)
    for idx in range(start, len(lines)):
        line = lines[idx]
        if line and (not line.startswith((' ', '\t', '#'))) and re.match('^[A-Za-z0-9_].*:\\s*', line):
            end = idx
            break
    return '\n'.join(lines[start:end])

def _nested_scalar(text: str, section: str, key: str, *, required: bool=True) -> Any:
    block = _section(text, section, required=required)
    if block is None:
        return None
    match = re.search(f'(?m)^\\s+{re.escape(key)}:\\s*(.*?)\\s*$', block)
    if not match:
        if required:
            raise ExecutionContractError(f'yaml: missing {section}.{key}')
        return None
    raw = match.group(1).strip()
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1]
    if raw in {'true', 'false'}:
        return raw == 'true'
    if raw in {'null', '~'}:
        return None
    if re.fullmatch('-?\\d+', raw):
        return int(raw)
    return raw

def _list(text: str, key: str, *, required: bool=True) -> list[str]:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        match = re.fullmatch(f'(\\s*){re.escape(key)}:\\s*', line)
        if not match:
            continue
        indent = len(match.group(1))
        values: list[str] = []
        for item in lines[idx + 1:]:
            if not item.strip():
                continue
            current = len(item) - len(item.lstrip(' '))
            if current <= indent:
                break
            if current == indent + 2 and item.lstrip().startswith('- '):
                raw = item.lstrip()[2:].strip()
                if ':' in raw and (not (raw.startswith('"') and raw.endswith('"'))):
                    continue
                if raw.startswith('"') and raw.endswith('"'):
                    raw = raw[1:-1]
                values.append(raw)
        if required and (not values):
            raise ExecutionContractError(f'yaml: empty list {key}')
        return values
    if required:
        raise ExecutionContractError(f'yaml: missing list {key}')
    return []

def _validate_ref(path: str) -> None:
    parsed = Path(path)
    if parsed.is_absolute() or '..' in parsed.parts or (not path.startswith('coordination/')):
        raise ExecutionContractError(f'authority: unsafe repository path {path}')

def _run_git(repo_path: str | Path, *args: str) -> str:
    proc = subprocess.run(['git', '-C', str(repo_path), *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    if proc.returncode != 0:
        raise ExecutionContractError(f"trusted git readback failed: {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()

def _open_trusted_main(repo_path: str | Path) -> tuple[str, Callable[[str], bytes]]:
    remote = _run_git(repo_path, 'ls-remote', TRUSTED_CONTROL_PLANE_URL, 'refs/heads/main')
    fields = remote.split()
    if len(fields) < 2 or not re.fullmatch('[0-9a-f]{40}', fields[0]):
        raise ExecutionContractError('trusted git readback: invalid main identity')
    observed = fields[0]
    _run_git(repo_path, 'fetch', '--quiet', '--no-tags', TRUSTED_CONTROL_PLANE_URL, 'refs/heads/main')
    fetched = _run_git(repo_path, 'rev-parse', 'FETCH_HEAD')
    if fetched != observed:
        raise ExecutionContractError('trusted git readback: main moved during readback')

    def read(path: str) -> bytes:
        _validate_ref(path)
        proc = subprocess.run(['git', '-C', str(repo_path), 'show', f'{observed}:{path}'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if proc.returncode != 0:
            raise ExecutionContractError(f'trusted git readback: cannot read {path}')
        return proc.stdout
    return (observed, read)

def _resolve_project(read: Callable[[str], bytes], canonical_project_key: str) -> tuple[str, str]:
    matches: list[tuple[str, str]] = []
    for path in PROJECT_ADAPTER_PATHS:
        text = read(path).decode('utf-8')
        aliases = _list(text, 'authority_project_aliases', required=False)
        project_id = _scalar(text, 'project_id')
        if canonical_project_key == project_id or canonical_project_key in aliases:
            matches.append((project_id, _scalar(text, 'execution_repository')))
    if len(matches) != 1:
        raise ExecutionContractError('canonical_authority: project alias did not resolve uniquely')
    return matches[0]

def _expect_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        raise ExecutionContractError(f'canonical_authority: {label} mismatch')

def _writer_lease_identity(identity: Mapping[str, Any], writer_lease_ref: str, writer_lease_digest: str) -> str:
    material = {field: identity[field] for field in COMMON_IDENTITY_FIELDS}
    material['writer_lease_ref'] = writer_lease_ref
    material['writer_lease_digest'] = writer_lease_digest
    return _json_digest(material)

def _path_within(child: str, parent: str) -> bool:
    if child == parent:
        return True
    if parent.endswith('/**'):
        prefix = parent[:-3].rstrip('/')
        return child.startswith(prefix + '/')
    return False

def _validate_authority_chain_semantics(active: str, route: str, claim: str, lease: str, reservation: str, prewrite: str, batch_raw: bytes, refs: Mapping[str, str], *, task_id: str, route_epoch: int, branch: str, exact_base_sha: str, canonical_project_key: str) -> list[str]:
    _expect_equal('claim.schema', _scalar(claim, 'schema'), 'TaskLeaseClaim/v1')
    _expect_equal('lease.schema', _scalar(lease, 'schema'), 'TaskLease/v1')
    _expect_equal('reservation.schema', _scalar(reservation, 'schema'), 'ExecutorReservation/v1')
    _expect_equal('prewrite.schema', _scalar(prewrite, 'schema'), 'WorkBuddyPrewriteReconciliationSnapshot/v1')
    _expect_equal('active.repository', _scalar(active, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    _expect_equal('route.repository', _scalar(route, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    _expect_equal('claim.repository', _scalar(claim, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    _expect_equal('lease.repository', _scalar(lease, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    _expect_equal('reservation.repository', _scalar(reservation, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    _expect_equal('prewrite.repository', _scalar(prewrite, 'repository'), TRUSTED_CONTROL_PLANE_REPOSITORY)
    for label, document in (('route', route), ('claim', claim), ('lease', lease), ('reservation', reservation), ('prewrite', prewrite)):
        _expect_equal(f'{label}.task_id', _scalar(document, 'task_id'), task_id)
        _expect_equal(f'{label}.route_epoch', _scalar(document, 'route_epoch'), route_epoch)
    _expect_equal('route.project', _scalar(route, 'project'), canonical_project_key)
    _expect_equal('lease.project', _scalar(lease, 'project'), canonical_project_key)
    _expect_equal('reservation.project', _scalar(reservation, 'project'), canonical_project_key)
    _expect_equal('prewrite.project', _scalar(prewrite, 'project'), canonical_project_key)
    if _scalar(active, 'status') != 'READY' or _scalar(active, 'execution_allowed') is not True:
        raise ExecutionContractError('canonical_authority: active route is not executable')
    if _scalar(route, 'status') != 'READY' or _scalar(route, 'execution_allowed') is not True:
        raise ExecutionContractError('canonical_authority: canonical route is not executable')
    if _scalar(claim, 'claim_state') != 'ACTIVE' or _scalar(claim, 'status_observed') != 'READY' or _scalar(claim, 'execution_allowed_observed') is not True:
        raise ExecutionContractError('canonical_authority: work claim is not ACTIVE/READY')
    if _scalar(lease, 'lease_state') != 'ACTIVE' or _scalar(lease, 'execution_allowed') is not True or _scalar(lease, 'substantive_write_allowed') is not True:
        raise ExecutionContractError('canonical_authority: task lease is not ACTIVE')
    if _scalar(reservation, 'reservation_state') != 'ACTIVE' or _nested_scalar(reservation, 'reservation_effect', 'execution_identity_reserved') is not True or _nested_scalar(reservation, 'reservation_effect', 'substantive_write_authorized_now') is not True:
        raise ExecutionContractError('canonical_authority: executor reservation is not ACTIVE')
    _expect_equal('active.implementation_branch', _scalar(active, 'implementation_branch'), branch)
    _expect_equal('route.execution.implementation_branch', _nested_scalar(route, 'execution', 'implementation_branch'), branch)
    _expect_equal('claim.branch', _scalar(claim, 'branch'), branch)
    _expect_equal('lease.implementation_branch', _scalar(lease, 'implementation_branch'), branch)
    _expect_equal('reservation.implementation_branch', _scalar(reservation, 'implementation_branch'), branch)
    _expect_equal('route.source_checkpoint.exact_head', _nested_scalar(route, 'source_checkpoint', 'exact_head'), exact_base_sha)
    _expect_equal('claim.reviewed_or_base_head', _scalar(claim, 'reviewed_or_base_head'), exact_base_sha)
    _expect_equal('claim.branch_parent_required', _scalar(claim, 'branch_parent_required'), exact_base_sha)
    _expect_equal('lease.source_checkpoint', _scalar(lease, 'source_checkpoint'), exact_base_sha)
    _expect_equal('prewrite.source_checkpoint.immutable_checkpoint_exact_head', _nested_scalar(prewrite, 'source_checkpoint', 'immutable_checkpoint_exact_head'), exact_base_sha)
    route_binding_map = {'work_claim': 'work_claim_ref', 'task_lease': 'task_lease_ref', 'executor_reservation': 'executor_reservation_ref', 'prewrite_snapshot': 'prewrite_snapshot_ref', 'active_task': 'active_task_index_ref'}
    for key, ref_key in route_binding_map.items():
        _expect_equal(f'route.bindings.{key}', _nested_scalar(route, 'bindings', key), refs[ref_key])
    _expect_equal('route.execution.executable_batch', _nested_scalar(route, 'execution', 'executable_batch'), refs['executable_batch_ref'])
    lease_freshness_map = {'route': 'canonical_route_ref', 'work_claim': 'work_claim_ref', 'executor_reservation': 'executor_reservation_ref', 'prewrite_snapshot': 'prewrite_snapshot_ref', 'executable_batch': 'executable_batch_ref', 'active_task': 'active_task_index_ref'}
    for key, ref_key in lease_freshness_map.items():
        _expect_equal(f'lease.freshness.{key}', _nested_scalar(lease, 'freshness', key), refs[ref_key])
    _expect_equal('prewrite.ordered_batch.executable_ref', _nested_scalar(prewrite, 'ordered_batch', 'executable_ref'), refs['executable_batch_ref'])
    _expect_equal('prewrite.current_codex_route.route_epoch', _nested_scalar(prewrite, 'current_codex_route', 'route_epoch'), route_epoch)
    if _nested_scalar(prewrite, 'current_codex_route', 'status') != 'READY' or _nested_scalar(prewrite, 'current_codex_route', 'execution_allowed') is not True:
        raise ExecutionContractError('canonical_authority: prewrite current route not READY')
    for key in ('snapshot_precedes_workbuddy_branch', 'requires_post_branch_fresh_readback', 'activation_commit_required'):
        if _nested_scalar(prewrite, 'activation_gate', key) is not True:
            raise ExecutionContractError(f'canonical_authority: prewrite activation gate {key} not true')
    surfaces = {'active': _list(active, 'authorized_paths'), 'route': _list(route, 'workbuddy_exclusive'), 'claim': _list(claim, 'authorized_paths'), 'lease': _list(lease, 'exclusive_write_surface'), 'reservation': _list(reservation, 'reservation_scope')}
    canonical_paths = surfaces['active']
    canonical_set = set(canonical_paths)
    for label, paths in surfaces.items():
        if set(paths) != canonical_set:
            raise ExecutionContractError(f'canonical_authority: write surface mismatch at {label}')
    try:
        batch = json.loads(batch_raw.decode('utf-8'))
    except Exception as exc:
        raise ExecutionContractError('canonical_authority: executable batch is not valid JSON') from exc
    _expect_equal('batch.schema', batch.get('schema'), 'CreativeExecutorWorkBatch/v1')
    _expect_equal('batch.project_id', batch.get('project_id'), canonical_project_key)
    _expect_equal('batch.authority', batch.get('authority'), 'CANONICAL_BOUND_BATCH_EXECUTABLE')
    source_checkpoint = batch.get('source_checkpoint')
    route_authority = batch.get('route_authority')
    if not isinstance(source_checkpoint, Mapping) or not isinstance(route_authority, Mapping):
        raise ExecutionContractError('canonical_authority: batch authority sections missing')
    _expect_equal('batch.source_checkpoint.exact_head', source_checkpoint.get('exact_head'), exact_base_sha)
    _expect_equal('batch.route_authority.task_id', route_authority.get('task_id'), task_id)
    _expect_equal('batch.route_authority.route_epoch', route_authority.get('route_epoch'), route_epoch)
    if route_authority.get('execution_allowed') is not True:
        raise ExecutionContractError('canonical_authority: batch execution is not allowed')
    for key, ref_key in (('route_ref', 'canonical_route_ref'), ('claim_ref', 'work_claim_ref'), ('lease_ref', 'task_lease_ref'), ('snapshot_ref', 'prewrite_snapshot_ref')):
        _expect_equal(f'batch.route_authority.{key}', route_authority.get(key), refs[ref_key])
    for item in batch.get('items', []):
        if not isinstance(item, Mapping):
            raise ExecutionContractError('canonical_authority: batch item is not an object')
        for write_path in item.get('write_paths', []):
            if not any((_path_within(str(write_path), parent) for parent in canonical_paths)):
                raise ExecutionContractError(f'canonical_authority: batch write path outside authority: {write_path}')
    return canonical_paths

def build_verified_canonical_authority(repo_path: str | Path) -> VerifiedCanonicalAuthority:
    """Fresh-read canonical main and issue a non-caller-constructible authority object."""
    canonical_main_sha, read = _open_trusted_main(repo_path)
    active_raw = read(ACTIVE_TASK_INDEX_REF)
    active = active_raw.decode('utf-8')
    refs = {'active_task_index_ref': ACTIVE_TASK_INDEX_REF, 'canonical_route_ref': _scalar(active, 'canonical_route'), 'work_claim_ref': _scalar(active, 'work_claim'), 'task_lease_ref': _scalar(active, 'task_lease'), 'executor_reservation_ref': _scalar(active, 'executor_reservation'), 'prewrite_snapshot_ref': _scalar(active, 'prewrite_snapshot'), 'executable_batch_ref': _scalar(active, 'executable_batch')}
    for path in refs.values():
        _validate_ref(path)
    raw_docs = {name: read(path) for name, path in refs.items()}
    digests = {name: _sha(data) for name, data in raw_docs.items()}
    route = raw_docs['canonical_route_ref'].decode('utf-8')
    claim = raw_docs['work_claim_ref'].decode('utf-8')
    lease = raw_docs['task_lease_ref'].decode('utf-8')
    reservation = raw_docs['executor_reservation_ref'].decode('utf-8')
    prewrite = raw_docs['prewrite_snapshot_ref'].decode('utf-8')
    task_id = _scalar(active, 'task_id')
    route_epoch = _scalar(active, 'route_epoch')
    branch = _scalar(active, 'implementation_branch')
    exact_base_sha = _nested_scalar(active, 'source_checkpoint', 'exact_head')
    canonical_project_key = _scalar(route, 'project')
    project_id, execution_repository = _resolve_project(read, canonical_project_key)
    authorized_paths = _validate_authority_chain_semantics(active, route, claim, lease, reservation, prewrite, raw_docs['executable_batch_ref'], refs, task_id=task_id, route_epoch=route_epoch, branch=branch, exact_base_sha=exact_base_sha, canonical_project_key=canonical_project_key)
    collision_domain = 'WRITESET_SHA256:' + sha256(json.dumps(sorted(authorized_paths), separators=(',', ':')).encode('utf-8')).hexdigest()
    common_identity = {'control_plane_repository': TRUSTED_CONTROL_PLANE_REPOSITORY, 'execution_repository': execution_repository, 'project_id': project_id, 'task_id': task_id, 'route_epoch': route_epoch, 'exact_base_sha': exact_base_sha, 'implementation_branch': branch, 'collision_domain': collision_domain}
    writer_lease_identity = _writer_lease_identity(common_identity, refs['task_lease_ref'], digests['task_lease_ref'])
    denials = sorted(set(_list(active, 'hard_boundaries') + _list(claim, 'hard_boundaries') + ['NO_DIRECT_MAIN_WRITE', 'NO_SELF_REVIEW', 'NO_SELF_MERGE']))
    grants = ['EXECUTE_TASK']
    if authorized_paths:
        grants.append('WRITE_AUTHORIZED_PATHS')
    payload: dict[str, Any] = {**common_identity, 'canonical_main_sha': canonical_main_sha, 'authority_refs': refs, 'authority_digests': digests, 'route_status': 'READY', 'execution_allowed': True, 'fresh_readback': True, 'authorized_paths': authorized_paths, 'authority_grants': grants, 'authority_denials': denials, 'writer_lease_identity': writer_lease_identity}
    receipt_material = {key: payload[key] for key in (*COMMON_IDENTITY_FIELDS, 'canonical_main_sha', 'authority_refs', 'authority_digests', 'route_status', 'execution_allowed', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity')}
    payload['authority_chain_receipt_digest'] = _json_digest(receipt_material)
    return _issue_authority(payload)

def build_verified_release_witness(repo_path: str | Path, release_ref: str) -> VerifiedReleaseWitness:
    """Fresh-read canonical release evidence and bind it to an immutable writer lease."""
    _validate_ref(release_ref)
    canonical_main_sha, read = _open_trusted_main(repo_path)
    raw = read(release_ref)
    text = raw.decode('utf-8')
    required = (*COMMON_IDENTITY_FIELDS, 'writer_lease_ref', 'released_lease_digest', 'writer_lease_identity', 'release_status')
    payload = {key: _scalar(text, key) for key in required}
    if payload['control_plane_repository'] != TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError('release_witness: wrong control-plane repository')
    if payload['release_status'] != 'RELEASED':
        raise ExecutionContractError('release_witness: release document is not RELEASED')
    _validate_ref(payload['writer_lease_ref'])
    computed_identity = _writer_lease_identity(payload, payload['writer_lease_ref'], payload['released_lease_digest'])
    if payload['writer_lease_identity'] != computed_identity:
        raise ExecutionContractError('release_witness: writer lease identity mismatch')
    payload['canonical_main_sha'] = canonical_main_sha
    payload['release_ref'] = release_ref
    payload['release_document_digest'] = _sha(raw)
    payload['release_receipt_digest'] = _json_digest(payload)
    return _issue_release(payload)

def _authority_mapping(authority: VerifiedCanonicalAuthority) -> Mapping[str, Any]:
    if not isinstance(authority, VerifiedCanonicalAuthority):
        raise ExecutionContractError('canonical_authority: caller-supplied mapping is not trusted authority')
    return authority.as_mapping()

def _release_mapping(witness: VerifiedReleaseWitness) -> Mapping[str, Any]:
    if not isinstance(witness, VerifiedReleaseWitness):
        raise ExecutionContractError('release_witness: caller-supplied mapping is not trusted release evidence')
    return witness.as_mapping()

def validate_canonical_authority(authority: VerifiedCanonicalAuthority) -> None:
    mapping = _authority_mapping(authority)
    _require(mapping, COMMON_IDENTITY_FIELDS + ('canonical_main_sha', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'route_status', 'execution_allowed', 'fresh_readback', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity'), 'canonical_authority')
    material = {key: mapping[key] for key in (*COMMON_IDENTITY_FIELDS, 'canonical_main_sha', 'authority_refs', 'authority_digests', 'route_status', 'execution_allowed', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity')}
    if mapping['authority_chain_receipt_digest'] != _json_digest(material):
        raise ExecutionContractError('canonical_authority: receipt recomputation failed')
    if mapping['route_status'] != 'READY' or mapping['execution_allowed'] is not True or mapping['fresh_readback'] is not True:
        raise ExecutionContractError('canonical_authority: inactive or stale')
    _require(mapping['authority_refs'], AUTHORITY_REF_FIELDS, 'canonical_authority.authority_refs')
    _require(mapping['authority_digests'], AUTHORITY_REF_FIELDS, 'canonical_authority.authority_digests')

def validate_dispatch(dispatch: Mapping[str, Any], canonical_authority: VerifiedCanonicalAuthority) -> None:
    validate_canonical_authority(canonical_authority)
    canonical = _authority_mapping(canonical_authority)
    _require(dispatch, COMMON_IDENTITY_FIELDS + ('canonical_main_sha', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity'), 'dispatch')
    _same_identity(dispatch, canonical, 'dispatch')
    for field in ('canonical_main_sha', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'writer_lease_identity'):
        if dispatch[field] != canonical[field]:
            raise ExecutionContractError(f'dispatch: {field} mismatch')
    if not set(dispatch['authorized_paths']) <= set(canonical['authorized_paths']):
        raise ExecutionContractError('dispatch: authorized paths exceed canonical authority')
    if not set(dispatch['authority_grants']) <= set(canonical['authority_grants']):
        raise ExecutionContractError('dispatch: authority grants exceed canonical authority')
    if not set(canonical['authority_denials']) <= set(dispatch['authority_denials']):
        raise ExecutionContractError('dispatch: canonical denials were weakened')

def validate_local_admission(admission: Mapping[str, Any], dispatch: Mapping[str, Any], canonical_authority: VerifiedCanonicalAuthority) -> None:
    validate_dispatch(dispatch, canonical_authority)
    canonical = _authority_mapping(canonical_authority)
    _require(admission, COMMON_IDENTITY_FIELDS + ('canonical_main_sha', 'route_status', 'execution_allowed', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity'), 'local_admission')
    _same_identity(admission, dispatch, 'local_admission.dispatch')
    _same_identity(admission, canonical, 'local_admission.canonical')
    if admission['route_status'] != 'READY' or admission['execution_allowed'] is not True:
        raise ExecutionContractError('local_admission: route not executable')
    for field in ('canonical_main_sha', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity'):
        if admission[field] != dispatch[field]:
            raise ExecutionContractError(f'local_admission: {field} does not match dispatch')
    if admission['writer_lease_identity'] != canonical['writer_lease_identity']:
        raise ExecutionContractError('local_admission: writer lease identity is not canonical')

def validate_carrier_handoff(handoff: Mapping[str, Any], old_dispatch: Mapping[str, Any], old_authority: VerifiedCanonicalAuthority, release_witness: VerifiedReleaseWitness, new_dispatch: Mapping[str, Any], new_admission: Mapping[str, Any], new_authority: VerifiedCanonicalAuthority) -> None:
    validate_dispatch(old_dispatch, old_authority)
    validate_local_admission(new_admission, new_dispatch, new_authority)
    old = _authority_mapping(old_authority)
    new = _authority_mapping(new_authority)
    release = _release_mapping(release_witness)
    _require(handoff, COMMON_IDENTITY_FIELDS + ('from_carrier', 'to_carrier', 'checkpoint_head_sha', 'old_writer_lease_identity', 'new_writer_admission_required'), 'carrier_handoff')
    _same_identity(handoff, old_dispatch, 'carrier_handoff.old_dispatch')
    _same_identity(new_dispatch, old_dispatch, 'carrier_handoff.new_dispatch')
    if handoff['new_writer_admission_required'] is not True:
        raise ExecutionContractError('carrier_handoff: new writer admission must be required')
    for field in COMMON_IDENTITY_FIELDS:
        if release[field] != handoff[field]:
            raise ExecutionContractError(f'carrier_handoff: release identity mismatch: {field}')
    if handoff['old_writer_lease_identity'] != old['writer_lease_identity']:
        raise ExecutionContractError('carrier_handoff: old writer lease identity mismatch')
    if release['writer_lease_identity'] != old['writer_lease_identity']:
        raise ExecutionContractError('carrier_handoff: release did not release old canonical writer')
    if release['writer_lease_ref'] != old['authority_refs']['task_lease_ref']:
        raise ExecutionContractError('carrier_handoff: released lease ref does not match old canonical authority')
    if release['released_lease_digest'] != old['authority_digests']['task_lease_ref']:
        raise ExecutionContractError('carrier_handoff: released lease digest does not match old canonical authority')
    if release['canonical_main_sha'] != new['canonical_main_sha']:
        raise ExecutionContractError('carrier_handoff: release witness is not from new admission main')
    if new['authority_digests']['task_lease_ref'] == old['authority_digests']['task_lease_ref']:
        raise ExecutionContractError('carrier_handoff: new writer reused old lease document')
    if new['writer_lease_identity'] == old['writer_lease_identity']:
        raise ExecutionContractError('carrier_handoff: old writer lease replayed')
    if new_admission['writer_lease_identity'] != new['writer_lease_identity']:
        raise ExecutionContractError('carrier_handoff: new admission is not bound to canonical new writer lease')

def validate_project_adapter(adapter: Mapping[str, Any], global_policy: Mapping[str, Any]) -> None:
    _require(adapter, PROJECT_ADAPTER_REQUIRED_FIELDS, 'project_adapter')
    _require(global_policy, ('protocol_id', 'allowed_execution_carriers', 'non_weakenable_invariants'), 'global_policy')
    if adapter['project_id'] not in KNOWN_PROJECT_IDS:
        raise ExecutionContractError('project_adapter: unregistered project id')
    if adapter['global_protocol_id'] != global_policy['protocol_id']:
        raise ExecutionContractError('project_adapter: wrong global protocol')
    if adapter['inherits_global_invariants'] is not True:
        raise ExecutionContractError('project_adapter: global invariants must be inherited')
    if adapter['control_plane_repository'] != TRUSTED_CONTROL_PLANE_REPOSITORY:
        raise ExecutionContractError('project_adapter: wrong control-plane repository')
    if not set(adapter['allowed_execution_carriers']) <= set(global_policy['allowed_execution_carriers']):
        raise ExecutionContractError('project_adapter: carrier set exceeds global policy')
    for field in ('repositories', 'canonical_entrypoints', 'authority', 'default_model_profiles', 'collision_domains', 'tool_interfaces', 'hard_boundaries', 'acceptance', 'handoff'):
        if not adapter[field]:
            raise ExecutionContractError(f'project_adapter: empty required semantic section: {field}')
    hard_boundaries = set(adapter['hard_boundaries'])
    for required in ('NO_SELF_REVIEW', 'NO_SELF_MERGE'):
        if required not in hard_boundaries:
            raise ExecutionContractError(f'project_adapter: missing inherited hard boundary {required}')
    overrides = adapter.get('global_invariant_overrides', {})
    for invariant in set(global_policy['non_weakenable_invariants']) | NON_WEAKENABLE_INVARIANTS:
        if invariant in overrides and overrides[invariant] is not True:
            raise ExecutionContractError(f'project_adapter: invariant weakened: {invariant}')
    if 'global_router' in adapter or 'global_task_router' in adapter:
        raise ExecutionContractError('project_adapter: second global router is forbidden')

def _require_hard_boundaries(adapter: Mapping[str, Any], required: set[str]) -> None:
    missing = sorted(required - set(adapter['hard_boundaries']))
    if missing:
        raise ExecutionContractError('project_adapter_document: missing project hard boundaries: ' + ', '.join(missing))

def _validate_project_semantic_floor(text: str, adapter: Mapping[str, Any]) -> None:
    project_id = adapter['project_id']
    authority = _section(text, 'authority') or ''
    tool_interfaces = _section(text, 'tool_interfaces') or ''
    if project_id == 'SECOND_BRAIN':
        _expect_equal('second_brain.authority.global_engineering_sync', _nested_scalar(text, 'authority', 'global_engineering_sync'), 'GitHub main')
        if _nested_scalar(text, 'authority', 'chat_history_is_sole_authority') is not False:
            raise ExecutionContractError('project_adapter_document: chat history cannot be sole authority')
        _require_hard_boundaries(adapter, {'NO_SECOND_W3', 'NO_SECOND_CONTROL_TOWER', 'NO_SELF_REVIEW', 'NO_SELF_MERGE', 'AUTHENTICATION_SECRET_VALUES_NEVER_PUBLIC'})
        if 'authority: "EXISTING_SOR_ONLY"' not in tool_interfaces:
            raise ExecutionContractError('project_adapter_document: W3 existing-SoR boundary missing')
    elif project_id == 'TRADING_SYSTEM':
        _expect_equal('trading.authority.order_authority', _nested_scalar(text, 'authority', 'order_authority'), 'SEPARATE_EXPLICIT_OWNER_GATE')
        if _nested_scalar(text, 'authority', 'engineering_execution_does_not_imply_order_authority') is not True:
            raise ExecutionContractError('project_adapter_document: engineering must not imply order authority')
        if 'default_authority: "READ_MARKET_DATA"' not in tool_interfaces:
            raise ExecutionContractError('project_adapter_document: market data default must be read-only')
        if 'place_order_allowed: false' not in tool_interfaces:
            raise ExecutionContractError('project_adapter_document: place_order_allowed must remain false')
        numeric = set(_list(text, 'numeric_and_research_invariants'))
        if not {'POINT_IN_TIME_ONLY', 'NO_LOOKAHEAD', 'SOURCE_AND_TIMESTAMP_PROVENANCE'} <= numeric:
            raise ExecutionContractError('project_adapter_document: trading research invariants weakened')
        _require_hard_boundaries(adapter, {'READ_MARKET_DATA_DOES_NOT_IMPLY_PLACE_ORDER', 'NO_ACCOUNT_OR_ORDER_AUTHORITY_FROM_GENERIC_ENGINEERING_ROUTE', 'NO_BROKER_CREDENTIALS_IN_GITHUB', 'NO_LIVE_TRADE_WITHOUT_SEPARATE_EXPLICIT_GATE', 'NO_SELF_REVIEW', 'NO_SELF_MERGE'})
    elif project_id == 'REALTIME_INTERACTIVE_FILM_GAME':
        for key in ('project_baton_is_navigation_not_execution_authority', 'ai_director_calls_require_explicit_adapter'):
            if _nested_scalar(text, 'authority', key) is not True:
                raise ExecutionContractError(f'project_adapter_document: {key} weakened')
        _expect_equal('interactive.global_factory_rule', _nested_scalar(text, 'authority', 'global_factory_rule'), 'INHERIT_UNIFIED_FABRIC_DO_NOT_REDEFINE')
        _require_hard_boundaries(adapter, {'NO_SECOND_GLOBAL_GPT_WORKBUDDY_FACTORY', 'NO_SILENT_AI_DIRECTOR_AUTHORITY_IMPORT', 'NO_ACCEPTANCE_ORACLE_DRIFT', 'NO_SELF_REVIEW', 'NO_SELF_MERGE'})
    elif project_id == 'AI_DIRECTOR':
        _expect_equal('ai_director.authority.source_authority', _nested_scalar(text, 'authority', 'source_authority'), 'vxz2datoubo/eustia-ai-film/PROJECT_INDEX.yaml')
        if _nested_scalar(text, 'authority', 'second_brain_may_not_silently_modify_domain_truth') is not True:
            raise ExecutionContractError('project_adapter_document: director domain truth boundary weakened')
        if 'engineering_model_choice_does_not_override: true' not in tool_interfaces:
            raise ExecutionContractError('project_adapter_document: director model-choice boundary missing')
        _require_hard_boundaries(adapter, {'PROJECT_INDEX_FIRST', 'NO_SECOND_DIRECTOR_AUTHORITY', 'GENERIC_ENGINEERING_MODEL_CANNOT_OVERRIDE_DIRECTOR_OR_PROMPT_AUTHORITY', 'BROWSER_GENERATION_REQUIRES_EXPLICIT_GENERATION_ROUTE', 'NO_SELF_REVIEW', 'NO_SELF_MERGE'})

def parse_and_validate_project_adapter(text: str, global_policy: Mapping[str, Any]) -> Mapping[str, Any]:
    """Parse and validate the governed adapter surface without PyYAML."""
    top_keys = set(re.findall('(?m)^([A-Za-z0-9_]+):', text))
    missing = [key for key in PROJECT_ADAPTER_REQUIRED_FIELDS if key not in top_keys]
    if missing:
        raise ExecutionContractError(f"project_adapter_document: missing sections: {', '.join(missing)}")
    adapter: dict[str, Any] = {'project_id': _scalar(text, 'project_id'), 'global_protocol_id': _scalar(text, 'global_protocol_id'), 'inherits_global_invariants': _scalar(text, 'inherits_global_invariants'), 'control_plane_repository': _scalar(text, 'control_plane_repository'), 'execution_repository': _scalar(text, 'execution_repository'), 'repositories': _section(text, 'repositories'), 'canonical_entrypoints': _list(text, 'canonical_entrypoints'), 'authority': _section(text, 'authority'), 'allowed_execution_carriers': _list(text, 'allowed_execution_carriers'), 'default_model_profiles': _section(text, 'default_model_profiles'), 'collision_domains': _list(text, 'collision_domains'), 'tool_interfaces': _section(text, 'tool_interfaces'), 'hard_boundaries': _list(text, 'hard_boundaries'), 'acceptance': _section(text, 'acceptance'), 'handoff': _section(text, 'handoff')}
    validate_project_adapter(adapter, global_policy)
    _validate_project_semantic_floor(text, adapter)
    return MappingProxyType(adapter)
