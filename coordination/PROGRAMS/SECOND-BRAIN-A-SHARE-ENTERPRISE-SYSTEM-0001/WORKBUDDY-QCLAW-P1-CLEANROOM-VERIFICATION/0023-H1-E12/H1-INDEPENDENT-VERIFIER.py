"""Independent, public-safe reproduction verifier for the frozen QCLAW P1 package.

Run ``python H1-INDEPENDENT-VERIFIER.py normal|nt1|nt2|nt3`` from a Git worktree.
The verifier reads only Git objects and temporary copies.  It never calls a service,
uses credentials, or modifies the frozen source commit.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


FROZEN_QCLAW_HEAD = "63c344084d9af86cb26c1cc65a30d409fefa872f"
EXPECTED_RESULT = "Results: 37 PASS / 0 FAIL / 0 SKIP"
EXPECTED_HASHED_FILE_COUNT = 14
TIMEOUT_SECONDS = 30

FROZEN_ARTIFACTS = (
    "P1-AI-HANDOFF.yaml",
    "P1-AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "P1-AMED-RESEARCH-LEDGER.yaml",
    "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml",
    "P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
    "P1-BLOCKING-FAILURE-ASSESSMENT.yaml",
    "P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
    "P1-DIMENSION-SCORECARD.yaml",
    "P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml",
    "P1-FROZEN-MANIFEST.yaml",
    "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml",
    "P1-TEST-RUN-RECEIPT.md",
    "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml",
    "P1-VALIDATE-AUDIT.py",
    "P1-VERDICT-AND-GPT-RECOMMENDATION.yaml",
)
VALIDATOR_NAME = "P1-VALIDATE-AUDIT.py"

H1_FILES = (
    "H1-AI_HANDOFF.yaml",
    "H1-INDEPENDENT-VERIFIER.py",
    "H1-PUBLIC-SAFETY-REPORT.yaml",
    "H1-TEST-RUN-RECEIPT.md",
    "H1-WORKBUDDY-EXECUTION-FEEDBACK-v2.yaml",
)


class VerifierFailure(RuntimeError):
    """Expected controlled verifier failure."""


@dataclass
class Outcome:
    mode: str
    status: str = "PASS"
    findings: list[dict[str, str]] = field(default_factory=list)
    artifact_hashes: dict[str, str] = field(default_factory=dict)
    child_exit: int | None = None
    stdout_sha256: str | None = None
    stderr_sha256: str | None = None
    validator_result: str | None = None
    files_hashed: int | None = None
    cleanup_status: str = "NOT_APPLICABLE"

    def fail(self, code: str, detail: str) -> None:
        self.status = "FAIL"
        self.findings.append({"code": code, "detail": detail})

    def emit(self) -> None:
        print("OUTCOME|" + json.dumps({
            "mode": self.mode,
            "status": self.status,
            "findings": self.findings,
            "artifact_hashes": self.artifact_hashes,
            "child_exit": self.child_exit,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "validator_result": self.validator_result,
            "files_hashed": self.files_hashed,
            "cleanup_status": self.cleanup_status,
        }, ensure_ascii=True, sort_keys=True))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def strict_text(value: bytes, context: str) -> str:
    try:
        return value.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise VerifierFailure(f"unicode_decode_error:{context}:{exc.start}") from exc


def run_git(repo: Path, args: Iterable[str]) -> bytes:
    command = ["git", *args]
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise VerifierFailure(f"git_timeout:{' '.join(args)}") from exc
    except OSError as exc:
        raise VerifierFailure(f"git_io_error:{exc.__class__.__name__}") from exc
    if completed.returncode != 0:
        stderr_hash = sha256_bytes(completed.stderr)
        raise VerifierFailure(f"git_failed:{completed.returncode}:{stderr_hash}")
    return completed.stdout


def repository_root(package: Path) -> Path:
    root = strict_text(run_git(package, ("rev-parse", "--show-toplevel")), "repo_root").strip()
    if not root:
        raise VerifierFailure("empty_repo_root")
    return Path(root)


def expected_h1_file_set() -> set[str]:
    return set(H1_FILES)


def compiled_public_safety_patterns() -> tuple[tuple[str, re.Pattern[bytes]], ...]:
    """Construct narrow byte patterns without embedding a credential-shaped literal."""
    return (
        ("absolute_windows_path", re.compile(rb"[A-Za-z]:[/\\\\][^\r\n]{2,}")),
        ("absolute_unix_path", re.compile(bytes.fromhex("2f686f6d652f") + rb"[^\r\n]{2,}")),
        ("pem_block", re.compile(bytes.fromhex("2d2d2d2d2d424547494e") + rb"[^\r\n]{0,40}KEY")),
        ("github_pat", re.compile(bytes.fromhex("6768705f") + rb"[A-Za-z0-9]{30,}")),
        ("generic_assignment", re.compile(
            bytes.fromhex("2870617373776f72647c7365637265747c746f6b656e7c6170695f6b657929")
            + rb"\s*[:=]\s*[^\s#]{8,}",
            re.IGNORECASE,
        )),
    )


def scan_public_safety(directory: Path) -> list[dict[str, str]]:
    actual = {item.name for item in directory.iterdir() if item.is_file()}
    if actual != expected_h1_file_set():
        missing = ",".join(sorted(expected_h1_file_set() - actual)) or "-"
        extra = ",".join(sorted(actual - expected_h1_file_set())) or "-"
        raise VerifierFailure(f"h1_manifest_mismatch:missing={missing}:extra={extra}")

    findings: list[dict[str, str]] = []
    for name in sorted(expected_h1_file_set()):
        try:
            content = (directory / name).read_bytes()
        except OSError as exc:
            raise VerifierFailure(f"h1_read_error:{name}:{exc.__class__.__name__}") from exc
        for pattern_name, pattern in compiled_public_safety_patterns():
            for match in pattern.finditer(content):
                findings.append({
                    "file": name,
                    "kind": pattern_name,
                    "offset": str(match.start()),
                })
    return findings


def assert_frozen_tree(repo: Path) -> None:
    names = strict_text(
        run_git(repo, ("ls-tree", "--name-only", FROZEN_QCLAW_HEAD)),
        "frozen_tree",
    ).splitlines()
    actual = {name for name in names if name.startswith("P1-")}
    expected = set(FROZEN_ARTIFACTS)
    if actual != expected:
        missing = ",".join(sorted(expected - actual)) or "-"
        extra = ",".join(sorted(actual - expected)) or "-"
        raise VerifierFailure(f"frozen_manifest_mismatch:missing={missing}:extra={extra}")


def source_bytes(repo: Path, artifact: str) -> bytes:
    return run_git(repo, ("show", f"{FROZEN_QCLAW_HEAD}:{artifact}"))


def parse_validator_output(outcome: Outcome, stdout: bytes, stderr: bytes, child_exit: int) -> None:
    text = strict_text(stdout, "validator_stdout")
    strict_text(stderr, "validator_stderr")
    outcome.child_exit = child_exit
    outcome.stdout_sha256 = sha256_bytes(stdout)
    outcome.stderr_sha256 = sha256_bytes(stderr)
    for line in text.splitlines():
        if line.startswith("Results:"):
            outcome.validator_result = line.strip()
        if line.startswith("Files hashed:"):
            try:
                outcome.files_hashed = int(line.rsplit(":", 1)[1].strip())
            except ValueError as exc:
                raise VerifierFailure("invalid_files_hashed_line") from exc


def execute_frozen_validator(
    repo: Path,
    outcome: Outcome,
    *,
    omit_after_identity_check: str | None = None,
    replacement_validator: bytes | None = None,
) -> None:
    assert_frozen_tree(repo)
    temporary_root = Path(tempfile.mkdtemp(prefix="h1-qclaw-"))
    try:
        for artifact in FROZEN_ARTIFACTS:
            raw = source_bytes(repo, artifact)
            destination = temporary_root / artifact
            try:
                destination.write_bytes(raw)
                extracted = destination.read_bytes()
            except OSError as exc:
                raise VerifierFailure(f"extract_io_error:{artifact}:{exc.__class__.__name__}") from exc
            source_hash = sha256_bytes(raw)
            extracted_hash = sha256_bytes(extracted)
            if source_hash != extracted_hash:
                raise VerifierFailure(f"byte_identity_failed:{artifact}")
            outcome.artifact_hashes[artifact] = source_hash

        if omit_after_identity_check:
            try:
                (temporary_root / omit_after_identity_check).unlink()
            except OSError as exc:
                raise VerifierFailure(f"negative_remove_error:{omit_after_identity_check}:{exc.__class__.__name__}") from exc
        if replacement_validator is not None:
            try:
                (temporary_root / VALIDATOR_NAME).write_bytes(replacement_validator)
            except OSError as exc:
                raise VerifierFailure(f"negative_replace_error:{exc.__class__.__name__}") from exc

        try:
            child = subprocess.run(
                [sys.executable, VALIDATOR_NAME],
                cwd=temporary_root,
                capture_output=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise VerifierFailure("validator_timeout") from exc
        except OSError as exc:
            raise VerifierFailure(f"validator_io_error:{exc.__class__.__name__}") from exc
        parse_validator_output(outcome, child.stdout, child.stderr, child.returncode)
    finally:
        try:
            shutil.rmtree(temporary_root)
        except OSError as exc:
            outcome.cleanup_status = "FAILED"
            raise VerifierFailure(f"cleanup_error:{exc.__class__.__name__}") from exc
        if temporary_root.exists():
            outcome.cleanup_status = "FAILED"
            raise VerifierFailure("cleanup_persisted")
        outcome.cleanup_status = "PASS"


def normal(repo: Path, package: Path, outcome: Outcome) -> None:
    findings = scan_public_safety(package)
    if findings:
        outcome.findings.extend(findings)
        raise VerifierFailure("public_safety_findings")
    execute_frozen_validator(repo, outcome)
    if outcome.child_exit != 0:
        raise VerifierFailure(f"validator_exit:{outcome.child_exit}")
    if outcome.validator_result != EXPECTED_RESULT:
        raise VerifierFailure("validator_result_mismatch")
    if outcome.files_hashed != EXPECTED_HASHED_FILE_COUNT:
        raise VerifierFailure("validator_hashed_file_count_mismatch")


def nt1(package: Path, outcome: Outcome) -> None:
    temporary_root = Path(tempfile.mkdtemp(prefix="h1-nt1-"))
    try:
        for name in H1_FILES:
            shutil.copyfile(package / name, temporary_root / name)
        injected = temporary_root / "H1-PUBLIC-SAFETY-REPORT.yaml"
        injected.write_bytes(
            injected.read_bytes()
            + b"\nproof_path: "
            + bytes((67, 58, 92))
            + b"synthetic-only"
            + bytes((92,))
            + b"not-for-publication\n"
        )
        findings = scan_public_safety(temporary_root)
        if not findings:
            raise VerifierFailure("negative_safety_injection_not_detected")
        outcome.findings.extend(findings)
        outcome.child_exit = None
        outcome.cleanup_status = "PASS"
    finally:
        try:
            shutil.rmtree(temporary_root)
        except OSError as exc:
            outcome.cleanup_status = "FAILED"
            raise VerifierFailure(f"nt1_cleanup_error:{exc.__class__.__name__}") from exc
        if temporary_root.exists():
            outcome.cleanup_status = "FAILED"
            raise VerifierFailure("nt1_cleanup_persisted")


def nt2(repo: Path, outcome: Outcome) -> None:
    execute_frozen_validator(
        repo,
        outcome,
        omit_after_identity_check="P1-TEST-RUN-RECEIPT.md",
    )
    if outcome.child_exit == 0:
        raise VerifierFailure("negative_missing_artifact_not_rejected")


def nt3(repo: Path, outcome: Outcome) -> None:
    execute_frozen_validator(repo, outcome, replacement_validator=b"import sys\nsys.exit(7)\n")
    if outcome.child_exit != 7:
        raise VerifierFailure("negative_child_exit_not_preserved")


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) == 2 else "normal"
    outcome = Outcome(mode=mode)
    package = Path(__file__).resolve().parent
    try:
        repo = repository_root(package)
        if mode == "normal":
            normal(repo, package, outcome)
        elif mode == "nt1":
            nt1(package, outcome)
            outcome.status = "EXPECTED_NEGATIVE_FAILURE"
        elif mode == "nt2":
            nt2(repo, outcome)
            outcome.status = "EXPECTED_NEGATIVE_FAILURE"
        elif mode == "nt3":
            nt3(repo, outcome)
            outcome.status = "EXPECTED_NEGATIVE_FAILURE"
        else:
            raise VerifierFailure(f"unsupported_mode:{mode}")
    except VerifierFailure as exc:
        outcome.fail("controlled_failure", str(exc))
    except Exception as exc:  # Defensive top-level boundary for all unexpected failures.
        outcome.fail("unexpected_failure", f"{exc.__class__.__name__}:{str(exc)[:160]}")
        traceback.print_exc(file=sys.stderr)
    outcome.emit()
    if mode == "normal":
        return 0 if outcome.status == "PASS" else 1
    return 1 if outcome.status == "EXPECTED_NEGATIVE_FAILURE" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
