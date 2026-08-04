"""Provider-observable E51 verification for the frozen E50 receipt.

This module is deliberately self-contained and only runs on an ephemeral
Windows CI worker.  It reads the E50 manifest from a disposable clone and
executes its argv exactly as committed.  It never writes to E50's branch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Sequence


CANONICAL_REPOSITORY = "https://github.com/vxz2datoubo/second-brain-coordination.git"
E50_BRANCH = "refs/heads/codex/brainops-trusted-provider-release-validation-0046-e50"
E50_RECEIPT_HEAD = "9e87bc2f6e705b65a35b92f09d7e7848abc5768a"
E50_BASE_HEAD = "7481fb645e8fd7b032fab6451128eecfadfedfaa"
E50_PLAN_HEAD = "1ca2e59283c154f5256132e0b25f2e5544116d51"
E50_TESTED_HEAD = "49ee251ed33c1f33e336bc59b0c485c279e9eaa3"
ATTESTATION_COMMIT = "edf9708360fb8d05a94f8a7711017db33ea8c342"
ATTESTATION_PATH = "coordination/PROVIDER-ATTESTATIONS/CODEX-E50-POST-RUN-PROVIDER-ATTESTATION.json"
ATTESTATION_BLOB_SHA1 = "e1ecdf118ae5be51486b15516c497bc596bb9a6f"
ATTESTATION_PAYLOAD_SHA256 = "00125ad915a4a2723d60195115d5114a75cab4f18626e10429137f82e3bf0b02"
PROGRAM_RELATIVE = Path(
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "BRAINOPS-APP-FIRST-CONTROL-PLANE"
)
RECEIPT_MANIFEST_RELATIVE = PROGRAM_RELATIVE / "E50" / "RECEIPT" / "RECEIPT-MANIFEST.json"
EXTERNAL_ENVELOPE = Path(r"C:\Users\Administrator\AppData\Local\Temp\e50-trusted-main-attestation-envelope.json")
EXPECTED_STDOUT = b'{"code":"READY_FOR_INDEPENDENT_REVIEW","findings":[]}\n'
EXPECTED_STDOUT_SHA256 = "0e1c50869dd3818fa98794f6de671daefc11df3e5a19a161428c75fc1beee7e0"


class VerificationError(RuntimeError):
    """A fail-closed provider verification condition."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalized_stdout(raw: bytes) -> bytes:
    """Normalize only Windows pipe line endings for the fixed output digest."""

    return raw.replace(b"\r\n", b"\n")


def completed(
    argv: Sequence[str], *, cwd: Path | None = None, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(list(argv), cwd=cwd, env=env, check=False, capture_output=True)


def require_success(argv: Sequence[str], *, cwd: Path | None = None) -> bytes:
    result = completed(argv, cwd=cwd)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace").strip() or result.stdout.decode("utf-8", "replace").strip()
        raise VerificationError(f"command_failed:{' '.join(argv[:4])}:{detail}")
    return result.stdout


def git_text(repository: Path, *arguments: str) -> str:
    return require_success(("git", "-C", str(repository), *arguments)).decode("utf-8", "strict").strip()


def remote_ref(repository_url: str, ref: str) -> str:
    output = require_success(("git", "ls-remote", repository_url, ref)).decode("utf-8", "strict").strip()
    fields = output.split()
    if len(fields) != 2 or fields[1] != ref or len(fields[0]) != 40:
        raise VerificationError(f"remote_ref_unavailable:{ref}")
    return fields[0]


def expected_manifest_argv() -> list[str]:
    return [
        "python",
        "-m",
        "brainops_control_plane.e50_release_verifier",
        "--repository-root",
        ".",
        "--trusted-attestation",
        str(EXTERNAL_ENVELOPE),
        "--base-head",
        E50_BASE_HEAD,
        "--plan-head",
        E50_PLAN_HEAD,
        "--tested-head",
        E50_TESTED_HEAD,
        "--receipt-head",
        "@HEAD",
    ]


def read_exact_manifest(clone: Path) -> tuple[dict[str, Any], list[str]]:
    raw = (clone / RECEIPT_MANIFEST_RELATIVE).read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("receipt_manifest_not_valid_json") from error
    argv = manifest.get("reproduction_command") if isinstance(manifest, dict) else None
    if not isinstance(argv, list) or not all(isinstance(part, str) and part for part in argv):
        raise VerificationError("receipt_manifest_argv_invalid")
    if argv != expected_manifest_argv():
        raise VerificationError("receipt_manifest_argv_not_exact_frozen_command")
    return manifest, list(argv)


def read_and_verify_attestation(workspace: Path) -> tuple[dict[str, Any], bytes, str]:
    require_success(("git", "-C", str(workspace), "fetch", "--no-tags", "origin", "main"))
    fetched_main = git_text(workspace, "rev-parse", "FETCH_HEAD")
    ancestry = completed(("git", "-C", str(workspace), "merge-base", "--is-ancestor", ATTESTATION_COMMIT, fetched_main))
    if ancestry.returncode != 0:
        raise VerificationError("attestation_commit_not_on_canonical_main")
    blob = git_text(workspace, "rev-parse", f"{ATTESTATION_COMMIT}:{ATTESTATION_PATH}")
    if blob != ATTESTATION_BLOB_SHA1:
        raise VerificationError("attestation_blob_sha1_mismatch")
    source = require_success(("git", "-C", str(workspace), "show", f"{ATTESTATION_COMMIT}:{ATTESTATION_PATH}"))
    try:
        payload = json.loads(source.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("attestation_payload_invalid_json") from error
    if not isinstance(payload, dict):
        raise VerificationError("attestation_payload_not_object")
    canonical = canonical_payload_bytes(payload)
    if source != canonical + b"\n" or sha256_bytes(canonical) != ATTESTATION_PAYLOAD_SHA256:
        raise VerificationError("attestation_payload_digest_mismatch")
    return payload, source, fetched_main


def write_envelope(payload: dict[str, Any], destination: Path, *, replace_existing: bool = False) -> str:
    envelope = {
        "source_commit": ATTESTATION_COMMIT,
        "source_path": ATTESTATION_PATH,
        "source_blob_sha1": ATTESTATION_BLOB_SHA1,
        "payload_sha256": ATTESTATION_PAYLOAD_SHA256,
        "payload": payload,
    }
    if set(envelope) != {"source_commit", "source_path", "source_blob_sha1", "payload_sha256", "payload"}:
        raise VerificationError("envelope_shape_invalid")
    encoded = json.dumps(envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.read_bytes() != encoded and not replace_existing:
        try:
            existing = json.loads(destination.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError("external_envelope_path_already_contains_unexpected_bytes") from error
        # A prior byte formatting of the exact same public five-field envelope
        # is safe to normalize. Any different document remains fail-closed.
        if not isinstance(existing, dict) or set(existing) != set(envelope) or existing != envelope:
            raise VerificationError("external_envelope_path_already_contains_unexpected_bytes")
    destination.write_bytes(encoded)
    return sha256_bytes(encoded)


def clone_frozen_e50(repository_url: str, clone: Path) -> None:
    if clone.exists():
        shutil.rmtree(clone)
    require_success(("git", "-c", "core.longpaths=true", "clone", "--no-checkout", repository_url, str(clone)))
    require_success(("git", "-C", str(clone), "config", "core.longpaths", "true"))
    if git_text(clone, "config", "--get", "core.longpaths").lower() != "true":
        raise VerificationError("disposable_clone_longpaths_not_enabled")
    require_success(("git", "-c", "core.longpaths=true", "-C", str(clone), "fetch", "--no-tags", "origin", "main", E50_BRANCH))
    require_success(("git", "-c", "core.longpaths=true", "-C", str(clone), "checkout", "--detach", E50_RECEIPT_HEAD))
    if git_text(clone, "rev-parse", "HEAD") != E50_RECEIPT_HEAD:
        raise VerificationError("disposable_clone_head_mismatch")


def e50_environment(clone: Path) -> dict[str, str]:
    environment = dict(os.environ)
    source = clone / PROGRAM_RELATIVE / "src"
    environment["PYTHONPATH"] = str(source) + os.pathsep + environment.get("PYTHONPATH", "")
    environment["PYTHONUTF8"] = "1"
    return environment


def execute_exact_manifest(clone: Path, argv: list[str]) -> subprocess.CompletedProcess[bytes]:
    # `argv` was loaded from the frozen manifest and is passed through unchanged.
    return completed(argv, cwd=clone, env=e50_environment(clone))


def result_record(result: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    normalized = normalized_stdout(result.stdout)
    return {
        "exit_code": result.returncode,
        "stdout_sha256_raw": sha256_bytes(result.stdout),
        "stdout_sha256_normalized": sha256_bytes(normalized),
        "stderr_sha256": sha256_bytes(result.stderr),
        "stdout_bytes": len(result.stdout),
        "stderr_bytes": len(result.stderr),
    }


def assert_positive(result: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    record = result_record(result)
    if (
        result.returncode != 0
        or result.stderr != b""
        or normalized_stdout(result.stdout) != EXPECTED_STDOUT
        or record["stdout_sha256_normalized"] != EXPECTED_STDOUT_SHA256
    ):
        raise VerificationError("exact_e50_manifest_command_did_not_produce_canonical_ready_output")
    return record


def _replace_envelope_for_case(payload: dict[str, Any], *, case: str) -> None:
    if case == "modified_blob":
        envelope = {
            "source_commit": ATTESTATION_COMMIT,
            "source_path": ATTESTATION_PATH,
            "source_blob_sha1": "0" * 40,
            "payload_sha256": ATTESTATION_PAYLOAD_SHA256,
            "payload": payload,
        }
    elif case == "modified_payload":
        changed = dict(payload)
        changed["e51_negative_payload_marker"] = "modified"
        envelope = {
            "source_commit": ATTESTATION_COMMIT,
            "source_path": ATTESTATION_PATH,
            "source_blob_sha1": ATTESTATION_BLOB_SHA1,
            "payload_sha256": sha256_bytes(canonical_payload_bytes(changed)),
            "payload": changed,
        }
    else:
        raise VerificationError(f"unsupported_envelope_case:{case}")
    EXTERNAL_ENVELOPE.write_bytes(
        json.dumps(envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    )


def run_negative_cases(repository_url: str, scratch: Path, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for case in ("modified_blob", "modified_payload", "modified_receipt_head", "modified_completion_signal", "post_receipt_commit"):
        clone = scratch / f"negative-{case}"
        clone_frozen_e50(repository_url, clone)
        # The first materialization has already rejected unrelated bytes. Each
        # case now restores the known canonical envelope before its mutation.
        write_envelope(payload, EXTERNAL_ENVELOPE, replace_existing=True)
        _manifest, argv = read_exact_manifest(clone)
        if case in {"modified_blob", "modified_payload"}:
            _replace_envelope_for_case(payload, case=case)
        elif case == "modified_receipt_head":
            manifest_path = clone / RECEIPT_MANIFEST_RELATIVE
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["reproduction_command"][-1] = E50_TESTED_HEAD
            manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
            _changed_manifest, argv = read_exact_manifest_for_negative(clone)
        elif case == "modified_completion_signal":
            receipt = clone / PROGRAM_RELATIVE / "E50" / "RECEIPT" / "AMED-EXECUTION-RECEIPT.yaml"
            document = json.loads(receipt.read_text(encoding="utf-8"))
            document["completion_signal"] = "E51_NEGATIVE_SIGNAL"
            receipt.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
        else:
            require_success(("git", "-C", str(clone), "config", "user.email", "e51-negative@example.invalid"))
            require_success(("git", "-C", str(clone), "config", "user.name", "E51 Negative"))
            (clone / "e51-post-receipt-negative.txt").write_text("negative-only\n", encoding="utf-8")
            require_success(("git", "-C", str(clone), "add", "e51-post-receipt-negative.txt"))
            require_success(("git", "-C", str(clone), "commit", "-m", "E51 negative post-receipt state"))
        result = execute_exact_manifest(clone, argv)
        if result.returncode == 0:
            raise VerificationError(f"negative_case_unexpected_success:{case}")
        records[case] = result_record(result)
    return records


def read_exact_manifest_for_negative(clone: Path) -> tuple[dict[str, Any], list[str]]:
    """Load a deliberately corrupted manifest without treating it as positive argv."""

    manifest = json.loads((clone / RECEIPT_MANIFEST_RELATIVE).read_text(encoding="utf-8"))
    argv = manifest.get("reproduction_command") if isinstance(manifest, dict) else None
    if not isinstance(argv, list) or not all(isinstance(part, str) and part for part in argv):
        raise VerificationError("negative_receipt_manifest_not_executable")
    return manifest, list(argv)


def write_artifact(
    artifact: Path,
    *,
    remote_before: str,
    remote_after: str,
    canonical_main: str,
    clone: Path,
    manifest: dict[str, Any],
    argv: list[str],
    envelope_sha256: str,
    positive: subprocess.CompletedProcess[bytes],
    positive_record: dict[str, Any],
    negatives: dict[str, dict[str, Any]],
) -> None:
    artifact.mkdir(parents=True, exist_ok=True)
    (artifact / "e50-receipt-manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")
    (artifact / "exact-argv.json").write_text(json.dumps(argv) + "\n", encoding="utf-8")
    (artifact / "positive-stdout.bin").write_bytes(positive.stdout)
    (artifact / "positive-stderr.bin").write_bytes(positive.stderr)
    report = {
        "schema_version": "E51_PROVIDER_OBSERVABLE_EVIDENCE_V1",
        "repository": CANONICAL_REPOSITORY,
        "e50_remote_head_before": remote_before,
        "e50_remote_head_after": remote_after,
        "e50_receipt_head": E50_RECEIPT_HEAD,
        "clone_head": git_text(clone, "rev-parse", "HEAD"),
        "canonical_main_after_fetch": canonical_main,
        "attestation": {
            "commit": ATTESTATION_COMMIT,
            "path": ATTESTATION_PATH,
            "blob_sha1": ATTESTATION_BLOB_SHA1,
            "payload_sha256": ATTESTATION_PAYLOAD_SHA256,
            "external_envelope_sha256": envelope_sha256,
            "external_envelope_path": str(EXTERNAL_ENVELOPE),
        },
        "exact_argv": argv,
        "positive": positive_record,
        "negative_cases": negatives,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "git": require_success(("git", "--version")).decode("utf-8", "replace").strip(),
            "core_longpaths": git_text(clone, "config", "--get", "core.longpaths"),
        },
    }
    (artifact / "provider-observable-evidence.json").write_text(
        json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def verify(workspace: Path, artifact: Path, repository_url: str) -> None:
    remote_before = remote_ref(repository_url, E50_BRANCH)
    if remote_before != E50_RECEIPT_HEAD:
        raise VerificationError("frozen_e50_remote_head_changed_before_execution")
    payload, _source, canonical_main = read_and_verify_attestation(workspace)
    scratch = artifact / "scratch"
    clone = scratch / "positive"
    clone_frozen_e50(repository_url, clone)
    manifest, argv = read_exact_manifest(clone)
    envelope_sha256 = write_envelope(payload, EXTERNAL_ENVELOPE)
    positive = execute_exact_manifest(clone, argv)
    positive_record = assert_positive(positive)
    negatives = run_negative_cases(repository_url, scratch, payload)
    write_envelope(payload, EXTERNAL_ENVELOPE, replace_existing=True)
    remote_after = remote_ref(repository_url, E50_BRANCH)
    if remote_after != E50_RECEIPT_HEAD:
        raise VerificationError("frozen_e50_remote_head_changed_after_execution")
    write_artifact(
        artifact,
        remote_before=remote_before,
        remote_after=remote_after,
        canonical_main=canonical_main,
        clone=clone,
        manifest=manifest,
        argv=argv,
        envelope_sha256=envelope_sha256,
        positive=positive,
        positive_record=positive_record,
        negatives=negatives,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--artifact-dir", required=True)
    parser.add_argument("--repository-url", default=CANONICAL_REPOSITORY)
    arguments = parser.parse_args(argv)
    artifact = Path(arguments.artifact_dir)
    try:
        verify(Path(arguments.workspace_root), artifact, arguments.repository_url)
    except (OSError, VerificationError, subprocess.SubprocessError) as error:
        artifact.mkdir(parents=True, exist_ok=True)
        (artifact / "failure.txt").write_text(f"{type(error).__name__}:{error}\n", encoding="utf-8")
        print(f"E51_PROVIDER_VERIFICATION_FAILED:{type(error).__name__}:{error}", file=sys.stderr)
        return 1
    print("E51_PROVIDER_VERIFICATION_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
