"""R138 bounded exact-repository capability execution evidence.

This module is deliberately not a command runner.  Production resolution has a
single static descriptor; tests may subclass the resolver without creating a
caller-facing provider registry.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

from .gateway import GatewayError, canonical, digest, instant, public_safe

PROVIDER_ID = "r138-bounded-exact-repository-execution-v1"
CONTRACT_REVISION = "BOUNDED_DOMAIN_CAPABILITY_EXECUTION_EVIDENCE_V1"
AI_FILM_REPOSITORY = "vxz2datoubo/eustia-ai-film"
AI_FILM_COMMIT = "44c383afd2207a97caf45b1b0da6ee1dece43a76"
MAX_TIMEOUT_SECONDS = 60
MAX_OUTPUT_BYTES = 65_536
_SEAL = object()
_BUNDLES: dict[str, "CapabilityExecutionEvidenceBundle"] = {}


def _now() -> datetime: return datetime.now(timezone.utc)
def _iso(value: datetime) -> str: return value.astimezone(timezone.utc).isoformat()
def _sha256_file(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()
def _safe_sha(value: object) -> bool: return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _safe_relative(value: str, code: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or "\\" in value or path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise GatewayError(code)
    return path


def _provider_code_digest() -> str:
    source = inspect.getsourcefile(_provider_code_digest)
    if source is None: raise GatewayError("PROVIDER_CODE_IDENTITY_UNAVAILABLE")
    return hashlib.sha256(Path(source).read_bytes()).hexdigest()


def _executor_digest(path: Path) -> str:
    if path.is_file(): return _sha256_file(path)
    if not path.is_dir(): raise GatewayError("EXECUTOR_PATH_FORBIDDEN")
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink(): raise GatewayError("EXECUTOR_PATH_FORBIDDEN")
        if item.is_file(): entries.append((item.relative_to(path).as_posix(), _sha256_file(item)))
    return digest(entries)


@dataclass(frozen=True)
class CapabilityExecutionRequest:
    request_id: str; execution_id: str; trace_id: str
    domain_id: str; capability_id: str; capability_class: str
    source_repository: str; source_commit: str; source_root: str
    input_paths: tuple[str, ...]; requested_at: str
    timeout_seconds: int = 30; max_output_bytes: int = MAX_OUTPUT_BYTES


@dataclass(frozen=True)
class CapabilityDescriptor:
    domain_id: str; capability_id: str; source_repository: str; source_commit: str
    executor_path: str; argv: tuple[str, ...]; capability_contract_ref: str
    network_enforcement_required: bool = True


@dataclass(frozen=True)
class CapabilityExecutionEvidenceBundle:
    provider_id: str; provider_contract_revision: str; provider_code_digest: str
    request_id: str; execution_id: str; trace_id: str
    domain_id: str; capability_id: str; capability_class: str
    source_repository: str; source_commit: str; executor_path: str; executor_digest: str
    input_digests: Mapping[str, str]; invocation_digest: str
    started_at: str; completed_at: str; exit_code: int | None; timed_out: bool
    stdout_digest: str; stderr_digest: str; output_bytes: int
    result_digest: str; source_clean_before: bool; source_clean_after: bool
    cleanup_complete: bool; network_enforced: bool; warnings: tuple[str, ...]
    invalidation_fingerprints: Mapping[str, str]; bundle_digest: str

    def identity_ref(self) -> str:
        return f"provider://r138/evidence/{self.execution_id}#sha256={self.bundle_digest}"


@dataclass(frozen=True)
class CapabilityExecutionProof:
    provider_id: str; evidence_ref: str; evidence_digest: str
    execution_id: str; trace_id: str; domain_id: str; capability_id: str
    source_repository: str; source_commit: str; executor_digest: str
    input_set_digest: str; result_digest: str; completed_at: str; fresh_until: str
    invalidation_fingerprints: Mapping[str, str]
    _seal: object

    def public_dict(self) -> Mapping[str, str]:
        return {"capability_id": self.capability_id, "execution_id": self.execution_id, "trace_id": self.trace_id,
                "evidence_ref": self.evidence_ref, "result_digest": self.result_digest}


class ExactRepositoryCapabilityProvider:
    """One serial, static production provider; no registration or generic argv."""

    _PRODUCTION_DESCRIPTOR = CapabilityDescriptor(
        "EUSTIA_AI_FILM", "AI_FILM_GOLDEN_CASE_INGESTOR_TEST_V1", AI_FILM_REPOSITORY, AI_FILM_COMMIT,
        "tools/golden_case_ingestor", ("-m", "unittest", "discover", "-s", "tests", "-v"),
        "github://vxz2datoubo/eustia-ai-film@44c383afd2207a97caf45b1b0da6ee1dece43a76/tools/golden_case_ingestor/README.md",
    )

    def _descriptor(self, request: CapabilityExecutionRequest) -> CapabilityDescriptor:
        descriptor = self._PRODUCTION_DESCRIPTOR
        if (request.domain_id, request.capability_id, request.capability_class, request.source_repository, request.source_commit) != (
            descriptor.domain_id, descriptor.capability_id, "EXACT_REPOSITORY_EXECUTABLE", descriptor.source_repository, descriptor.source_commit):
            raise GatewayError("CAPABILITY_DESCRIPTOR_MISMATCH")
        return descriptor

    def _network_enforced(self, _workspace: Path, descriptor: CapabilityDescriptor) -> bool:
        # The host provides no approved network namespace primitive.  Never
        # report this boundary as enforced merely because the command succeeded.
        return not descriptor.network_enforcement_required

    def _resolve_source(self, request: CapabilityExecutionRequest, descriptor: CapabilityDescriptor) -> tuple[Path, Mapping[str, str]]:
        root = Path(request.source_root).resolve()
        if not root.is_dir() or root.is_symlink(): raise GatewayError("SOURCE_ROOT_FORBIDDEN")
        completed = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], shell=False, capture_output=True, text=True, timeout=10, check=False)
        if completed.returncode != 0 or completed.stdout.strip() != descriptor.source_commit: raise GatewayError("SOURCE_COMMIT_MISMATCH")
        status = subprocess.run(["git", "-C", str(root), "status", "--porcelain"], shell=False, capture_output=True, text=True, timeout=10, check=False)
        if status.returncode != 0 or status.stdout: raise GatewayError("SOURCE_WORKSPACE_NOT_CLEAN")
        inputs: dict[str, str] = {}
        for raw in request.input_paths:
            relative = _safe_relative(raw, "INPUT_PATH_FORBIDDEN")
            item = (root / relative).resolve()
            if root not in item.parents or not item.is_file() or item.is_symlink(): raise GatewayError("INPUT_PATH_FORBIDDEN")
            inputs[relative.as_posix()] = _sha256_file(item)
        executor = (root / _safe_relative(descriptor.executor_path, "EXECUTOR_PATH_FORBIDDEN")).resolve()
        if root not in executor.parents or not executor.exists() or executor.is_symlink(): raise GatewayError("EXECUTOR_PATH_FORBIDDEN")
        return root, inputs

    def execute(self, request: CapabilityExecutionRequest) -> tuple[CapabilityExecutionEvidenceBundle, CapabilityExecutionProof | None]:
        if not request.request_id or not request.execution_id or not request.trace_id: raise GatewayError("EXECUTION_IDENTITY_REQUIRED")
        if not 0 < request.timeout_seconds <= MAX_TIMEOUT_SECONDS or not 0 < request.max_output_bytes <= MAX_OUTPUT_BYTES: raise GatewayError("EXECUTION_BOUND_FORBIDDEN")
        instant(request.requested_at, "/requested_at")
        descriptor = self._descriptor(request)
        source_root, inputs = self._resolve_source(request, descriptor)
        before = subprocess.run(["git", "-C", str(source_root), "status", "--porcelain"], shell=False, capture_output=True, text=True, timeout=10, check=False)
        started = _now(); exit_code: int | None = None; timed_out = False; stdout = stderr = b""; cleanup = False
        with tempfile.TemporaryDirectory(prefix="r138-capability-") as temporary:
            workspace = Path(temporary) / "source"
            shutil.copytree(source_root, workspace, ignore=shutil.ignore_patterns(".git", "__pycache__", ".venv"), symlinks=False)
            command = (sys.executable, *descriptor.argv)
            try:
                result = subprocess.run(command, cwd=(workspace / descriptor.executor_path).parent, shell=False, capture_output=True,
                                        timeout=request.timeout_seconds, env={"PATH": os.environ.get("PATH", ""), "PYTHONDONTWRITEBYTECODE": "1"})
                exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired as exc:
                timed_out, stdout, stderr = True, exc.stdout or b"", exc.stderr or b""
            if len(stdout) + len(stderr) > request.max_output_bytes: raise GatewayError("EXECUTION_OUTPUT_TOO_LARGE")
            cleanup = not workspace.exists() or workspace.is_dir()
            network_enforced = self._network_enforced(workspace, descriptor)
        after = subprocess.run(["git", "-C", str(source_root), "status", "--porcelain"], shell=False, capture_output=True, text=True, timeout=10, check=False)
        completed = _now(); source_clean = before.returncode == after.returncode == 0 and not before.stdout and not after.stdout
        executor_digest = _executor_digest(source_root / descriptor.executor_path)
        invocation = digest({"argv": command, "cwd": descriptor.executor_path, "env": ["PATH", "PYTHONDONTWRITEBYTECODE"]})
        output = stdout + b"\n" + stderr
        invalidators = {"source_commit": request.source_commit, "executor_digest": executor_digest, "input_set_digest": digest(inputs), "contract": descriptor.capability_contract_ref}
        warnings = tuple(item for item, present in (("NETWORK_ISOLATION_UNENFORCED", not network_enforced), ("SOURCE_MUTATION_DETECTED", not source_clean), ("EXECUTION_TIMEOUT", timed_out), ("EXECUTION_NONZERO", exit_code not in (0, None))) if present)
        material = {"provider": PROVIDER_ID, "request": request.request_id, "execution": request.execution_id, "trace": request.trace_id, "domain": request.domain_id, "capability": request.capability_id, "source": request.source_commit, "executor": executor_digest, "inputs": inputs, "invocation": invocation, "stdout": hashlib.sha256(stdout).hexdigest(), "stderr": hashlib.sha256(stderr).hexdigest(), "result": hashlib.sha256(output).hexdigest(), "exit": exit_code, "warnings": warnings}
        bundle = CapabilityExecutionEvidenceBundle(PROVIDER_ID, CONTRACT_REVISION, _provider_code_digest(), request.request_id, request.execution_id, request.trace_id, request.domain_id, request.capability_id, request.capability_class, request.source_repository, request.source_commit, descriptor.executor_path, executor_digest, inputs, invocation, _iso(started), _iso(completed), exit_code, timed_out, hashlib.sha256(stdout).hexdigest(), hashlib.sha256(stderr).hexdigest(), len(output), hashlib.sha256(output).hexdigest(), source_clean, source_clean, cleanup, network_enforced, warnings, invalidators, digest(material))
        _BUNDLES[bundle.identity_ref()] = bundle
        if warnings or not cleanup: return bundle, None
        proof = CapabilityExecutionProof(PROVIDER_ID, bundle.identity_ref(), bundle.bundle_digest, request.execution_id, request.trace_id, request.domain_id, request.capability_id, request.source_repository, request.source_commit, executor_digest, digest(inputs), bundle.result_digest, bundle.completed_at, _iso(completed + timedelta(minutes=5)), invalidators, _SEAL)
        return bundle, proof


def verify_capability_execution_proof(proof: object, *, at: str | None = None) -> bool:
    if not isinstance(proof, CapabilityExecutionProof) or proof._seal is not _SEAL or proof.provider_id != PROVIDER_ID: return False
    bundle = _BUNDLES.get(proof.evidence_ref)
    if bundle is None: return False
    try: checked = instant(at or _iso(_now()), "/checked_at"); completed = instant(bundle.completed_at, "/completed_at"); fresh = instant(proof.fresh_until, "/fresh_until")
    except GatewayError: return False
    return bool(checked >= completed and checked <= fresh and bundle.bundle_digest == proof.evidence_digest and bundle.provider_code_digest == _provider_code_digest() and not bundle.warnings and bundle.cleanup_complete and bundle.network_enforced and bundle.exit_code == 0 and not bundle.timed_out and proof.execution_id == bundle.execution_id and proof.trace_id == bundle.trace_id and proof.domain_id == bundle.domain_id and proof.capability_id == bundle.capability_id and proof.source_repository == bundle.source_repository and proof.source_commit == bundle.source_commit and proof.executor_digest == bundle.executor_digest and proof.input_set_digest == digest(bundle.input_digests) and proof.result_digest == bundle.result_digest and proof.invalidation_fingerprints == bundle.invalidation_fingerprints)
