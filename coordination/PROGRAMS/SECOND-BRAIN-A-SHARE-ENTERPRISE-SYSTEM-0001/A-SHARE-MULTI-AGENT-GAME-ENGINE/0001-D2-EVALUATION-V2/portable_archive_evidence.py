"""Run Evaluation V2 from three clean, exact-commit Git archives.

The carrier never executes the live working tree.  Git writes the archive as a
ZIP file directly, avoiding Windows text-pipe corruption of binary tar output.
Only synthetic, public-safe test output and SHA-256 receipts are emitted.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


REPOSITORY_ROOT = Path(__file__).resolve().parents[5]
EVALUATION_RELATIVE_ROOT = Path(
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "A-SHARE-MULTI-AGENT-GAME-ENGINE/0001-D2-EVALUATION-V2"
)
COMMANDS = (
    ("focused_tests", ("tests/test_evaluation_v2.py",)),
    ("public_runner", ("tests/run_evaluation_v2.py",)),
)


@dataclass(frozen=True)
class CommandReceipt:
    name: str
    command: tuple[str, ...]
    working_directory_relative: str
    script_relative_path: str
    exit_code: int
    stdout_sha256: str
    stderr_sha256: str


@dataclass(frozen=True)
class ArtifactReceipt:
    relative_path: str
    sha256: str
    size_bytes: int


@dataclass(frozen=True)
class ArchiveReceipt:
    archive_run_id: str
    commit: str
    archive_sha256: str
    archive_size_bytes: int
    extracted_file_count: int
    root_id: str
    root_path_sha256: str
    artifacts: tuple[ArtifactReceipt, ...]
    commands: tuple[CommandReceipt, ...]


def _sha256_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _run_checked(command: list[str], *, cwd: Path) -> bytes:
    result = subprocess.run(command, cwd=cwd, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            "E26_GIT_COMMAND_FAILED:%s:stdout=%s:stderr=%s" % (
                result.returncode,
                _sha256_bytes(result.stdout),
                _sha256_bytes(result.stderr),
            )
        )
    return result.stdout


def resolve_commit(reference: str, *, repository_root: Path = REPOSITORY_ROOT) -> str:
    resolved = _run_checked(
        ["git", "rev-parse", "--verify", reference + "^{commit}"],
        cwd=repository_root,
    ).decode("ascii").strip()
    if len(resolved) != 40 or any(character not in "0123456789abcdef" for character in resolved):
        raise RuntimeError("E26_INVALID_RESOLVED_COMMIT")
    return resolved


def require_within_archive_root(archive_root: Path, candidate: Path) -> Path:
    resolved_root = archive_root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise RuntimeError("E26_ARCHIVE_EXECUTION_ESCAPES_ROOT") from error
    return resolved_candidate


def _run_archive_command(archive_root: Path, script_relative_path: str) -> CommandReceipt:
    evaluation_root = require_within_archive_root(archive_root, archive_root / EVALUATION_RELATIVE_ROOT)
    script_path = require_within_archive_root(evaluation_root, evaluation_root / script_relative_path)
    command = (sys.executable, "-B", script_path.relative_to(evaluation_root).as_posix())
    result = subprocess.run(command, cwd=evaluation_root, capture_output=True, check=False)
    receipt = CommandReceipt(
        next(name for name, scripts in COMMANDS if scripts == (script_relative_path,)),
        command,
        EVALUATION_RELATIVE_ROOT.as_posix(),
        script_relative_path,
        result.returncode,
        _sha256_bytes(result.stdout),
        _sha256_bytes(result.stderr),
    )
    if receipt.exit_code != 0:
        raise RuntimeError("E26_ARCHIVE_COMMAND_FAILED:%s:%s" % (receipt.name, receipt.exit_code))
    return receipt


def _artifact_receipts(extraction_root: Path) -> tuple[ArtifactReceipt, ...]:
    """Return a complete, root-relative manifest for independent archive comparison."""
    records = []
    for path in sorted((item for item in extraction_root.rglob("*") if item.is_file()), key=lambda item: item.as_posix()):
        relative_path = path.relative_to(extraction_root).as_posix()
        contents = path.read_bytes()
        records.append(ArtifactReceipt(relative_path, _sha256_bytes(contents), len(contents)))
    return tuple(records)


def _archive_once(commit: str, *, run_index: int, temporary_root: Path) -> ArchiveReceipt:
    archive_path = temporary_root / ("evaluation-v2-%03d.zip" % run_index)
    _run_checked(
        ["git", "archive", "--format=zip", "--output", str(archive_path), commit],
        cwd=REPOSITORY_ROOT,
    )
    archive_bytes = archive_path.read_bytes()
    extraction_root = temporary_root / ("archive-run-%03d" % run_index)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(extraction_root)
    if (extraction_root / ".git").exists():
        raise RuntimeError("E26_ARCHIVE_CONTAINS_GIT_METADATA")
    evaluation_root = require_within_archive_root(extraction_root, extraction_root / EVALUATION_RELATIVE_ROOT)
    if not evaluation_root.is_dir():
        raise RuntimeError("E26_ARCHIVE_EVALUATION_ROOT_MISSING")
    commands = tuple(_run_archive_command(extraction_root, scripts[0]) for _name, scripts in COMMANDS)
    return ArchiveReceipt(
        "archive-run-%03d" % run_index,
        commit,
        _sha256_bytes(archive_bytes),
        len(archive_bytes),
        sum(1 for path in extraction_root.rglob("*") if path.is_file()),
        "archive-root-%03d" % run_index,
        _sha256_bytes(str(extraction_root.resolve()).encode("utf-8")),
        _artifact_receipts(extraction_root),
        commands,
    )


def validate_archive_receipts(receipts: tuple[ArchiveReceipt, ...], expected_commit: str) -> None:
    if len(receipts) != 3:
        raise AssertionError("E26_ARCHIVE_RECEIPT_COUNT_MISMATCH")
    if len({receipt.archive_run_id for receipt in receipts}) != len(receipts):
        raise AssertionError("E26_ARCHIVE_ROOT_NOT_DISTINCT")
    if any(not receipt.root_id or not receipt.root_path_sha256 for receipt in receipts):
        raise AssertionError("E28_ARCHIVE_ROOT_IDENTITY_MISSING")
    if len({receipt.root_id for receipt in receipts}) != len(receipts):
        raise AssertionError("E28_ARCHIVE_ROOT_ID_NOT_DISTINCT")
    if len({receipt.root_path_sha256 for receipt in receipts}) != len(receipts):
        raise AssertionError("E28_ARCHIVE_ROOT_PATH_NOT_DISTINCT")
    if any(receipt.commit != expected_commit for receipt in receipts):
        raise AssertionError("E26_ARCHIVE_COMMIT_MISMATCH")
    if any(not receipt.archive_sha256 or receipt.extracted_file_count < 1 for receipt in receipts):
        raise AssertionError("E26_ARCHIVE_RECEIPT_INCOMPLETE")
    if len({receipt.archive_sha256 for receipt in receipts}) != 1 or len({receipt.archive_size_bytes for receipt in receipts}) != 1:
        raise AssertionError("E28_ARCHIVE_BYTES_NOT_IDENTICAL")
    if any(not receipt.artifacts for receipt in receipts):
        raise AssertionError("E28_ARCHIVE_ARTIFACT_MANIFEST_MISSING")
    baseline_artifacts = receipts[0].artifacts
    if not baseline_artifacts:
        raise AssertionError("E28_ARCHIVE_ARTIFACT_MANIFEST_MISSING")
    if any(receipt.artifacts != baseline_artifacts for receipt in receipts[1:]):
        raise AssertionError("E28_ARCHIVE_ARTIFACT_MANIFEST_DRIFT")
    artifact_paths = tuple(item.relative_path for item in baseline_artifacts)
    if len(set(artifact_paths)) != len(artifact_paths):
        raise AssertionError("E28_ARCHIVE_ARTIFACT_PATH_DUPLICATE")
    if any(
        not item.relative_path
        or Path(item.relative_path).is_absolute()
        or ".." in Path(item.relative_path).parts
        or not item.sha256
        or item.size_bytes < 0
        for item in baseline_artifacts
    ):
        raise AssertionError("E28_ARCHIVE_ARTIFACT_MANIFEST_INVALID")
    for receipt in receipts:
        if tuple(command.name for command in receipt.commands) != tuple(name for name, _scripts in COMMANDS):
            raise AssertionError("E26_ARCHIVE_COMMAND_SET_MISMATCH")
        if any(command.exit_code != 0 for command in receipt.commands):
            raise AssertionError("E26_ARCHIVE_COMMAND_NOT_GREEN")
        for command in receipt.commands:
            if command.working_directory_relative != EVALUATION_RELATIVE_ROOT.as_posix():
                raise AssertionError("E28_ARCHIVE_COMMAND_WORKING_DIRECTORY_INVALID")
            if command.script_relative_path not in tuple(scripts[0] for _name, scripts in COMMANDS):
                raise AssertionError("E28_ARCHIVE_COMMAND_SCRIPT_INVALID")
            if not command.command or Path(command.command[-1]).is_absolute() or command.command[-1] != command.script_relative_path:
                raise AssertionError("E28_ARCHIVE_COMMAND_ESCAPES_ROOT")
    runner_hashes = {
        command.stdout_sha256
        for receipt in receipts
        for command in receipt.commands
        if command.name == "public_runner"
    }
    if len(runner_hashes) != 1:
        raise AssertionError("E26_ARCHIVE_RUNNER_NOT_DETERMINISTIC")


def run_portable_archive_evidence(reference: str) -> dict[str, object]:
    commit = resolve_commit(reference)
    with tempfile.TemporaryDirectory(prefix="e26-evaluation-archive-") as temporary:
        receipts = tuple(
            _archive_once(commit, run_index=index, temporary_root=Path(temporary))
            for index in (1, 2, 3)
        )
    validate_archive_receipts(receipts, commit)
    return {
        "boundary": "PUBLIC_SAFE_SYNTHETIC_ONLY_CANDIDATE_ONLY",
        "exact_commit": commit,
        "archive_receipts": [asdict(receipt) for receipt in receipts],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", required=True, help="Exact Git commit or resolvable commit reference.")
    arguments = parser.parse_args()
    print(json.dumps(run_portable_archive_evidence(arguments.commit), ensure_ascii=True, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
