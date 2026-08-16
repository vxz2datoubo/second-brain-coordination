"""R138's one bounded, provider-owned executable capability boundary.

There is deliberately no command, image, environment, result, or proof input
in the public request.  The production provider can mint evidence only from
its fixed descriptor and its own ``docker --network none`` invocation.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import os
from pathlib import Path, PurePosixPath
import shutil
import secrets
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from typing import Mapping

from .gateway import GatewayError, digest, instant

PROVIDER_ID = "r138-bounded-exact-repository-execution-v2"
CONTRACT_REVISION = "BOUNDED_DOMAIN_CAPABILITY_EXECUTION_EVIDENCE_V1_R1"
AI_FILM_REPOSITORY = "vxz2datoubo/eustia-ai-film"
AI_FILM_COMMIT = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
MAX_TIMEOUT_SECONDS, MAX_OUTPUT_BYTES = 60, 65_536
_SEAL = object()
_BUNDLES: dict[str, "CapabilityExecutionEvidenceBundle"] = {}


def _now() -> datetime: return datetime.now(timezone.utc)
def _iso(value: datetime) -> str: return value.astimezone(timezone.utc).isoformat()
def _hash_bytes(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def _hash_file(path: Path) -> str: return _hash_bytes(path.read_bytes())
def _safe_sha(value: str) -> bool: return len(value) in {40, 64} and all(ch in "0123456789abcdef" for ch in value)


def _relative(value: str, code: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or "\\" in value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GatewayError(code)
    return path


def _inside(root: Path, item: Path) -> bool:
    try: item.resolve().relative_to(root.resolve()); return True
    except ValueError: return False


def _provider_code_digest() -> str:
    source = inspect.getsourcefile(_provider_code_digest)
    if source is None: raise GatewayError("PROVIDER_CODE_IDENTITY_UNAVAILABLE")
    return _hash_file(Path(source))


def _tree_digest(root: Path) -> str:
    if not root.exists() or root.is_symlink(): raise GatewayError("EXECUTOR_PATH_FORBIDDEN")
    entries: list[tuple[str, str]] = []
    for item in sorted(root.rglob("*")):
        if item.is_symlink(): raise GatewayError("SYMLINK_ESCAPE_FORBIDDEN")
        if item.is_file(): entries.append((item.relative_to(root).as_posix(), _hash_file(item)))
    return digest(entries)


def _bundle_digest(bundle: "CapabilityExecutionEvidenceBundle") -> str:
    """Canonical digest over every trusted bundle field except itself."""
    return digest({name: value for name, value in bundle.__dict__.items() if name != "bundle_digest"})


@dataclass(frozen=True)
class CapabilityExecutionRequest:
    request_id: str; execution_id: str; trace_id: str
    domain_id: str; capability_id: str; capability_class: str
    provider_contract_revision: str; source_repository: str; source_commit: str
    capability_contract_ref: str; executor_ref: str; input_refs: tuple[str, ...]
    result_schema_ref: str; resource_policy_ref: str; network_policy_ref: str
    write_policy_ref: str; privacy_scope_ref: str; source_root: str; requested_at: str
    timeout_seconds: int = 30; max_output_bytes: int = MAX_OUTPUT_BYTES


@dataclass(frozen=True)
class CapabilityDescriptor:
    domain_id: str; capability_id: str; source_repository: str; source_commit: str
    capability_contract_ref: str; executor_path: str; working_directory: str
    argv: tuple[str, ...]; input_paths: tuple[str, ...]; dependency_lock_path: str
    result_schema_ref: str; resource_policy_ref: str; network_policy_ref: str
    write_policy_ref: str; privacy_scope_ref: str; runtime_image: str
    network_enforcement_required: bool = True


@dataclass(frozen=True)
class CapabilityExecutionEvidenceBundle:
    provider_id: str; provider_contract_revision: str; provider_code_digest: str
    request_id: str; execution_id: str; trace_id: str; domain_id: str; capability_id: str; capability_class: str
    source_repository: str; source_commit: str; capability_contract_ref: str
    executor_ref: str; executor_digest: str; working_directory: str; working_directory_digest: str
    input_digests: Mapping[str, str]; dependency_lock_ref: str; dependency_lock_digest: str
    runtime_identity: Mapping[str, str]; invocation_digest: str; environment_digest: str
    resource_policy_ref: str; network_policy_ref: str; write_policy_ref: str; privacy_scope_ref: str
    boundary_enforcement: Mapping[str, bool]; started_at: str; completed_at: str; duration_ms: int
    execution_status: str; exit_code: int | None; timed_out: bool; output_bytes: int
    stdout_digest: str; stderr_digest: str; result_digest: str; source_clean_before: bool; source_clean_after: bool
    temp_write_isolated: bool; descendant_ownership_verified: bool; cleanup_complete: bool
    warnings: tuple[str, ...]; invalidation_fingerprints: Mapping[str, str]; bundle_digest: str

    def identity_ref(self) -> str: return f"provider://r138/evidence/{self.execution_id}#sha256={self.bundle_digest}"


@dataclass(frozen=True)
class CapabilityExecutionProof:
    provider_id: str; provider_contract_revision: str; evidence_ref: str; evidence_digest: str
    execution_id: str; trace_id: str; domain_id: str; capability_id: str; source_repository: str; source_commit: str
    capability_contract_ref: str; executor_digest: str; input_set_digest: str; dependency_lock_digest: str
    runtime_digest: str; result_digest: str; execution_status: str; boundary_enforcement_digest: str
    completed_at: str; fresh_until: str; invalidation_fingerprints: Mapping[str, str]; _seal: object

    def public_dict(self) -> Mapping[str, str]:
        return {"capability_id": self.capability_id, "execution_id": self.execution_id, "trace_id": self.trace_id,
                "evidence_ref": self.evidence_ref, "result_digest": self.result_digest}


class ExactRepositoryCapabilityProvider:
    """Static production mapping.  The Docker boundary is provider-derived."""
    _PRODUCTION_DESCRIPTOR = CapabilityDescriptor(
        "EUSTIA_AI_FILM", "AI_FILM_GOLDEN_CASE_INGESTOR_TEST_V1", AI_FILM_REPOSITORY, AI_FILM_COMMIT,
        "github://vxz2datoubo/eustia-ai-film@44c383afd2207a97caf45b1b0da6ee1dece43a76/tools/golden_case_ingestor/README.md",
        "tools/golden_case_ingestor", "tools/golden_case_ingestor",
        ("python", "-I", "-m", "unittest", "discover", "-s", "tests", "-v"),
        ("tools/golden_case_ingestor/requirements.txt",), "tools/golden_case_ingestor/requirements.txt",
        "golden_case_ingestor:test-report/v1", "r138://resource/single-worker-v1", "r138://network/docker-none-v1",
        "r138://write/readonly-source-task-output-v1", "PUBLIC_SAFE_EXECUTION_METADATA_ONLY", "r138-ai-film-golden-case:provisioned",
    )
    _in_flight = threading.Lock()

    def _descriptor(self, request: CapabilityExecutionRequest) -> CapabilityDescriptor:
        descriptor = self._PRODUCTION_DESCRIPTOR
        fields = ("domain_id", "capability_id", "capability_class", "provider_contract_revision", "source_repository", "source_commit", "capability_contract_ref", "executor_ref", "result_schema_ref", "resource_policy_ref", "network_policy_ref", "write_policy_ref", "privacy_scope_ref")
        expected = (descriptor.domain_id, descriptor.capability_id, "EXACT_REPOSITORY_EXECUTABLE", CONTRACT_REVISION, descriptor.source_repository, descriptor.source_commit, descriptor.capability_contract_ref, descriptor.executor_path, descriptor.result_schema_ref, descriptor.resource_policy_ref, descriptor.network_policy_ref, descriptor.write_policy_ref, descriptor.privacy_scope_ref)
        if tuple(getattr(request, item) for item in fields) != expected or tuple(request.input_refs) != descriptor.input_paths:
            raise GatewayError("CAPABILITY_DESCRIPTOR_MISMATCH")
        return descriptor

    def _git(self, root: Path, *args: str, binary: bool = False) -> bytes | str:
        result = subprocess.run(("git", "-C", str(root), *args), shell=False, capture_output=True, timeout=15, check=False)
        if result.returncode: raise GatewayError("EXACT_SOURCE_GIT_OPERATION_FAILED")
        return result.stdout if binary else result.stdout.decode("utf-8", "strict").strip()

    def _resolve_source(self, request: CapabilityExecutionRequest, descriptor: CapabilityDescriptor) -> tuple[Path, Mapping[str, str]]:
        root = Path(request.source_root).resolve()
        if not root.is_dir() or root.is_symlink() or str(self._git(root, "rev-parse", "HEAD")) != descriptor.source_commit:
            raise GatewayError("SOURCE_COMMIT_MISMATCH")
        if str(self._git(root, "status", "--porcelain")): raise GatewayError("SOURCE_WORKSPACE_NOT_CLEAN")
        inputs: dict[str, str] = {}
        for raw in descriptor.input_paths:
            path = root / _relative(raw, "INPUT_PATH_FORBIDDEN")
            if not _inside(root, path) or not path.is_file() or path.is_symlink(): raise GatewayError("INPUT_PATH_FORBIDDEN")
            inputs[raw] = _hash_file(path)
        return root, inputs

    def _materialize_exact_tree(self, root: Path, commit: str, destination: Path) -> str:
        archive = self._git(root, "archive", "--format=tar", commit, binary=True)
        assert isinstance(archive, bytes)
        archive_digest = _hash_bytes(archive)
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(archive); archive_path = Path(handle.name)
        try:
            with tarfile.open(archive_path) as contents:
                for member in contents.getmembers():
                    target = destination / member.name
                    if member.issym() or member.islnk() or not _inside(destination, target): raise GatewayError("EXACT_TREE_MEMBER_FORBIDDEN")
                contents.extractall(destination, filter="data")
        finally: archive_path.unlink(missing_ok=True)
        return archive_digest

    def _runtime_identity(self, descriptor: CapabilityDescriptor) -> Mapping[str, str]:
        """Accept only the CI-governed image attested by its immutable ID file."""
        attestation = os.environ.get("R138_GOVERNED_PROVISIONING_ATTESTATION")
        if not attestation or not Path(attestation).is_file(): raise GatewayError("GOVERNED_RUNTIME_ATTESTATION_REQUIRED")
        import json
        try: declared = json.loads(Path(attestation).read_text(encoding="utf-8"))
        except (OSError, ValueError): raise GatewayError("GOVERNED_RUNTIME_ATTESTATION_INVALID")
        result = subprocess.run(("docker", "image", "inspect", "--format", "{{.Id}}", descriptor.runtime_image), shell=False, capture_output=True, text=True, timeout=15, check=False)
        if result.returncode or not result.stdout.strip(): raise GatewayError("GOVERNED_RUNTIME_NOT_PROVISIONED")
        image_id = result.stdout.strip()
        wheels = declared.get("wheelhouse_sha256")
        required = ("workflow", "head_sha", "run_id", "provisioning_artifact_id", "provisioning_artifact_digest")
        if not isinstance(wheels, str) or not _safe_sha(wheels) or any(not declared.get(key) for key in required) or declared.get("image_id") != image_id or declared.get("image") != descriptor.runtime_image:
            raise GatewayError("GOVERNED_RUNTIME_ATTESTATION_MISMATCH")
        return {"runtime": "docker", "image": descriptor.runtime_image, "image_id": image_id, "wheelhouse_sha256": wheels, "workflow": str(declared["workflow"]), "head_sha": str(declared["head_sha"]), "run_id": str(declared["run_id"]), "provisioning_artifact_id": str(declared["provisioning_artifact_id"]), "provisioning_artifact_digest": str(declared["provisioning_artifact_digest"]), "attestation_file_digest": _hash_file(Path(attestation)), "host_python": sys.version.split()[0], "os": os.name}

    def _execute_boundary(self, descriptor: CapabilityDescriptor, source: Path, output: Path, request: CapabilityExecutionRequest) -> tuple[int | None, bool, bytes, bytes, Mapping[str, bool], Mapping[str, str], str]:
        runtime = self._runtime_identity(descriptor)
        container = f"r138-{secrets.token_hex(16)}"; cidfile = output / "r138.cid"
        command = ("docker", "run", "--rm", "--name", container, "--cidfile", str(cidfile), "--network", "none", "--read-only", "--pids-limit", "64", "--memory", "768m", "--cpus", "1.0", "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m", "--mount", f"type=bind,src={source},dst=/work,readonly", "--mount", f"type=bind,src={output},dst=/output", "--workdir", f"/work/{descriptor.working_directory}", "--env", "PYTHONNOUSERSITE=1", "--env", "PYTHONDONTWRITEBYTECODE=1", descriptor.runtime_image, *descriptor.argv)
        try:
            result = subprocess.run(command, shell=False, capture_output=True, timeout=request.timeout_seconds, env={"PATH": os.environ.get("PATH", "")}, check=False)
            return result.returncode, False, result.stdout, result.stderr, {"network": True, "read_only_source": True, "write_surface": True, "resource_limits": True, "no_shell": True}, runtime, str(cidfile)
        except subprocess.TimeoutExpired as error:
            # docker --rm owns the bounded container; absence after the command is checked by caller.
            return None, True, error.stdout or b"", error.stderr or b"", {"network": True, "read_only_source": True, "write_surface": True, "resource_limits": True, "no_shell": True}, runtime, str(cidfile)

    def _post_boundary_clean(self, workspace: Path, output: Path, descriptor: CapabilityDescriptor, cidfile: str) -> tuple[bool, bool]:
        # source is immutable to the container; all task-owned writes may only be in output.
        source_unchanged = _tree_digest(workspace / "source") == _tree_digest(workspace / "source-before")
        cid_path = Path(cidfile); cid = cid_path.read_text(encoding="utf-8").strip() if cid_path.is_file() else ""
        if cid and _safe_sha(cid):
            removal = subprocess.run(("docker", "rm", "-f", cid), shell=False, capture_output=True, text=True, timeout=15, check=False)
            query = subprocess.run(("docker", "ps", "-a", "--filter", f"id={cid}", "--format", "{{.ID}}"), shell=False, capture_output=True, text=True, timeout=15, check=False)
            descendants_clean = removal.returncode == 0 and query.returncode == 0 and not query.stdout.strip()
        else:
            descendants_clean = False
        allowed_output = _inside(workspace, output) and not any(item.is_symlink() for item in output.rglob("*"))
        return source_unchanged and allowed_output, descendants_clean

    def execute(self, request: CapabilityExecutionRequest) -> tuple[CapabilityExecutionEvidenceBundle, CapabilityExecutionProof | None]:
        if not self._in_flight.acquire(blocking=False): raise GatewayError("PROVIDER_EXECUTION_IN_FLIGHT")
        try: return self._execute_serial(request)
        finally: self._in_flight.release()

    def _execute_serial(self, request: CapabilityExecutionRequest) -> tuple[CapabilityExecutionEvidenceBundle, CapabilityExecutionProof | None]:
        if not all((request.request_id, request.execution_id, request.trace_id)) or not _safe_sha(request.source_commit): raise GatewayError("EXECUTION_IDENTITY_REQUIRED")
        if not 0 < request.timeout_seconds <= MAX_TIMEOUT_SECONDS or not 0 < request.max_output_bytes <= MAX_OUTPUT_BYTES: raise GatewayError("EXECUTION_BOUND_FORBIDDEN")
        instant(request.requested_at, "/requested_at")
        descriptor = self._descriptor(request); root, inputs = self._resolve_source(request, descriptor)
        source_before = str(self._git(root, "status", "--porcelain")) == ""; started, monotonic = _now(), time.monotonic()
        exit_code: int | None = None; timed_out = False; stdout = stderr = b""; runtime: Mapping[str, str] = {}; boundaries: Mapping[str, bool] = {}; write_isolated = descendants = cleanup = False; archive_digest = ""; container = ""
        parent = Path(tempfile.mkdtemp(prefix="r138-capability-")); workspace, output = parent / "source", parent / "output"
        executor_digest = cwd_digest = ""
        try:
            workspace.mkdir(); output.mkdir(); archive_digest = self._materialize_exact_tree(root, descriptor.source_commit, workspace)
            shutil.copytree(workspace, parent / "source-before")
            executor = workspace / _relative(descriptor.executor_path, "EXECUTOR_PATH_FORBIDDEN")
            cwd = workspace / _relative(descriptor.working_directory, "WORKING_DIRECTORY_FORBIDDEN")
            if not _inside(workspace, executor) or not _inside(workspace, cwd) or not executor.exists() or not cwd.is_dir() or executor.is_symlink() or cwd.is_symlink(): raise GatewayError("EXECUTOR_OR_WORKING_DIRECTORY_FORBIDDEN")
            executor_digest, cwd_digest = _tree_digest(executor), _tree_digest(cwd)
            exit_code, timed_out, stdout, stderr, boundaries, runtime, container = self._execute_boundary(descriptor, workspace, output, request)
            if len(stdout) + len(stderr) > request.max_output_bytes: raise GatewayError("EXECUTION_OUTPUT_TOO_LARGE")
            write_isolated, descendants = self._post_boundary_clean(parent, output, descriptor, container)
        finally:
            shutil.rmtree(parent, ignore_errors=False)
            cleanup = not parent.exists()
        source_after = str(self._git(root, "status", "--porcelain")) == "" and str(self._git(root, "rev-parse", "HEAD")) == descriptor.source_commit; completed = _now(); duration = int((time.monotonic() - monotonic) * 1000)
        output = stdout + b"\n" + stderr; result_digest = _hash_bytes(output)
        invocation = digest({"argv": descriptor.argv, "cwd": descriptor.working_directory, "env": ["PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"], "archive": archive_digest})
        warnings = tuple(code for code, failed in (("NETWORK_ISOLATION_UNENFORCED", not boundaries.get("network")), ("WRITE_ISOLATION_UNVERIFIED", not write_isolated), ("DESCENDANT_OWNERSHIP_UNVERIFIED", not descendants), ("CLEANUP_INCOMPLETE", not cleanup), ("SOURCE_MUTATION_DETECTED", not (source_before and source_after)), ("EXECUTION_TIMEOUT", timed_out), ("EXECUTION_NONZERO", exit_code not in {0, None})) if failed)
        invalidators = {"provider_code": _provider_code_digest(), "contract": descriptor.capability_contract_ref, "source_commit": request.source_commit, "executor": executor_digest, "working_directory": cwd_digest, "inputs": digest(inputs), "dependency_lock": inputs[descriptor.dependency_lock_path], "runtime": digest(runtime), "boundary": digest(boundaries), "resource_policy": descriptor.resource_policy_ref, "network_policy": descriptor.network_policy_ref, "write_policy": descriptor.write_policy_ref}
        bundle = CapabilityExecutionEvidenceBundle(PROVIDER_ID, CONTRACT_REVISION, _provider_code_digest(), request.request_id, request.execution_id, request.trace_id, request.domain_id, request.capability_id, request.capability_class, request.source_repository, request.source_commit, descriptor.capability_contract_ref, descriptor.executor_path, executor_digest, descriptor.working_directory, cwd_digest, inputs, descriptor.dependency_lock_path, inputs[descriptor.dependency_lock_path], runtime, invocation, digest(["PYTHONNOUSERSITE", "PYTHONDONTWRITEBYTECODE"]), descriptor.resource_policy_ref, descriptor.network_policy_ref, descriptor.write_policy_ref, descriptor.privacy_scope_ref, boundaries, _iso(started), _iso(completed), duration, "SUCCEEDED" if exit_code == 0 and not timed_out else "FAILED", exit_code, timed_out, len(output), _hash_bytes(stdout), _hash_bytes(stderr), result_digest, source_before, source_after, write_isolated, descendants, cleanup, warnings, invalidators, "")
        bundle = replace(bundle, bundle_digest=_bundle_digest(bundle))
        _BUNDLES[bundle.identity_ref()] = bundle
        if warnings: return bundle, None
        proof = CapabilityExecutionProof(PROVIDER_ID, CONTRACT_REVISION, bundle.identity_ref(), bundle.bundle_digest, request.execution_id, request.trace_id, request.domain_id, request.capability_id, request.source_repository, request.source_commit, descriptor.capability_contract_ref, executor_digest, digest(inputs), inputs[descriptor.dependency_lock_path], digest(runtime), result_digest, bundle.execution_status, digest(boundaries), bundle.completed_at, _iso(completed + timedelta(minutes=5)), invalidators, _SEAL)
        return bundle, proof


def verify_historical_capability_execution_proof(proof: object, *, at: str | None = None) -> bool:
    if not isinstance(proof, CapabilityExecutionProof) or proof._seal is not _SEAL or proof.provider_id != PROVIDER_ID or proof.provider_contract_revision != CONTRACT_REVISION: return False
    bundle = _BUNDLES.get(proof.evidence_ref)
    if bundle is None: return False
    try: checked, completed, fresh = instant(at or _iso(_now()), "/checked_at"), instant(bundle.completed_at, "/completed_at"), instant(proof.fresh_until, "/fresh_until")
    except GatewayError: return False
    required = all(bundle.boundary_enforcement.get(key) for key in ("network", "read_only_source", "write_surface", "resource_limits", "no_shell"))
    return bool(checked >= completed and bundle.bundle_digest == _bundle_digest(bundle) and bundle.bundle_digest == proof.evidence_digest and bundle.execution_status == "SUCCEEDED" and bundle.exit_code == 0 and not bundle.timed_out and bundle.source_clean_before and bundle.source_clean_after and bundle.temp_write_isolated and bundle.descendant_ownership_verified and bundle.cleanup_complete and not bundle.warnings and required and proof.execution_id == bundle.execution_id and proof.trace_id == bundle.trace_id and proof.domain_id == bundle.domain_id and proof.capability_id == bundle.capability_id and proof.source_repository == bundle.source_repository and proof.source_commit == bundle.source_commit and proof.capability_contract_ref == bundle.capability_contract_ref and proof.executor_digest == bundle.executor_digest and proof.input_set_digest == digest(bundle.input_digests) and proof.dependency_lock_digest == bundle.dependency_lock_digest and proof.runtime_digest == digest(bundle.runtime_identity) and proof.result_digest == bundle.result_digest and proof.execution_status == bundle.execution_status and proof.boundary_enforcement_digest == digest(bundle.boundary_enforcement) and proof.invalidation_fingerprints == bundle.invalidation_fingerprints)


def verify_capability_execution_proof(proof: object, *, at: str | None = None) -> bool:
    """Current-compliance validation: historical validity plus bounded freshness."""
    if not verify_historical_capability_execution_proof(proof, at=at): return False
    assert isinstance(proof, CapabilityExecutionProof)
    try:
        bundle = _BUNDLES[proof.evidence_ref]
        return instant(at or _iso(_now()), "/checked_at") <= instant(proof.fresh_until, "/fresh_until") and bundle.provider_code_digest == _provider_code_digest()
    except GatewayError: return False
