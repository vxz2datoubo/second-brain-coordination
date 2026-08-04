"""Active E50 mutation evidence for trusted-release validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


@dataclass(frozen=True)
class E50MutationObservation:
    mutation_id: str
    target: str
    expected_test: str
    exit_code: int
    output_sha256: str

    @property
    def killed(self) -> bool:
        return self.exit_code != 0


def _environment(program_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    inherited = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(program_root / "src") + (
        os.pathsep + inherited if inherited else ""
    )
    return environment


def _copy_program(program_root: Path, destination: Path) -> Path:
    copied = destination / "program"
    shutil.copytree(program_root, copied, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return copied


def _replace_once(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        raise RuntimeError(f"mutation target not unique: {path.name}:{before[:56]}")
    path.write_text(text.replace(before, after, 1), encoding="utf-8")


def _named_test(test_name: str) -> list[str]:
    script = (
        "import sys, unittest; "
        "sys.path.insert(0, 'tests'); "
        f"suite=unittest.defaultTestLoader.loadTestsFromName({test_name!r}); "
        "result=unittest.TextTestRunner(verbosity=0).run(suite); "
        "raise SystemExit(0 if result.wasSuccessful() else 1)"
    )
    return [sys.executable, "-c", script]


def _observe(
    mutation_id: str,
    target: str,
    expected_test: str,
    copied: Path,
) -> E50MutationObservation:
    completed = subprocess.run(
        _named_test(expected_test),
        cwd=copied,
        env=_environment(copied),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = completed.stdout + completed.stderr
    return E50MutationObservation(
        mutation_id=mutation_id,
        target=target,
        expected_test=expected_test,
        exit_code=completed.returncode,
        output_sha256=hashlib.sha256(output.encode("utf-8")).hexdigest(),
    )


def run_e50_mutation_harness(program_root: Path) -> tuple[E50MutationObservation, ...]:
    """Require genuine E50 weakening to make its named proof fail."""

    source_relative = Path("src/brainops_control_plane/e50_release_verifier.py")
    mutations = (
        (
            "ancestry_zero_exit_not_accepted",
            "evaluate_git_ancestry:returncode_zero",
            "if completed.returncode == 0:",
            "if False:",
            "test_e50_release_closure.E50ReleaseClosureTests.test_exit_status_drives_real_positive_and_negative_git_graphs",
        ),
        (
            "ancestry_one_exit_not_classified",
            "evaluate_git_ancestry:returncode_one",
            "if completed.returncode == 1:",
            "if False:",
            "test_e50_release_closure.E50ReleaseClosureTests.test_exit_status_drives_real_positive_and_negative_git_graphs",
        ),
        (
            "caller_provider_document_accepted",
            "reject_caller_provider_document",
            "return E50ProviderAuthorityResult(E50ProviderAuthorityCode.UNTRUSTED_CALLER_DOCUMENT)",
            "return E50ProviderAuthorityResult(E50ProviderAuthorityCode.TRUSTED_MAIN_ATTESTATION)",
            "test_e50_release_closure.E50ReleaseClosureTests.test_fully_forged_provider_document_is_not_provider_authority",
        ),
        (
            "external_envelope_extra_field_accepted",
            "load_trusted_main_attestation:envelope_shape",
            "if set(envelope) != required or not isinstance(envelope.get(\"payload\"), dict):",
            "if False:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "non_main_attestation_source_accepted",
            "load_trusted_main_attestation:source_ancestry",
            "ancestry = evaluate_git_ancestry(repository_root, envelope[\"source_commit\"], remote_main)\n    if ancestry.code is not E50GitGraphCode.ANCESTOR:\n        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None\n    try:",
            "ancestry = evaluate_git_ancestry(repository_root, envelope[\"source_commit\"], remote_main)\n    if False:\n        return E50ProviderAuthorityResult(E50ProviderAuthorityCode.ATTESTATION_INVALID), None\n    try:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "attestation_blob_or_payload_mismatch_accepted",
            "load_trusted_main_attestation:blob_and_payload",
            "if blob_sha1 != envelope[\"source_blob_sha1\"] or source_bytes != _canonical_payload_bytes(document):",
            "if False:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "unexecutable_documented_command_accepted",
            "receipt_schema:command_prefix",
            "if command[:3] != [\"python\", \"-m\", \"brainops_control_plane.e50_release_verifier\"]:",
            "if False:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "completion_signal_mismatch_accepted",
            "receipt_schema:common_metadata",
            "if any(value.get(key) != expected for key, expected in metadata.items()):",
            "if False:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "provider_receipt_field_change_accepted",
            "validate_e50_release:provider_crosscheck",
            "or provider_document != trusted_evidence.get(\"tested\")",
            "or False",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "post_receipt_commit_accepted",
            "validate_e50_release:head_guard",
            "if _git_output(repository_root, \"rev-parse\", \"HEAD\") != receipt_head:",
            "if False:",
            "test_e50_clean_clone_reproduction.E50CleanCloneReproductionTests.test_exact_documented_command_runs_in_clean_clone_and_tamper_fails",
        ),
        (
            "wrong_provider_job_head_accepted",
            "validate_provider_run:job_head",
            "or job.get(\"head_sha\") != head",
            "or False",
            "test_e50_release_closure.E50ReleaseClosureTests.test_provider_run_rejects_wrong_job_head",
        ),
        (
            "expired_provider_artifact_accepted",
            "validate_provider_run:artifact_expiry",
            "or artifact.get(\"expired\") is not False",
            "or False",
            "test_e50_release_closure.E50ReleaseClosureTests.test_provider_run_rejects_expired_artifact",
        ),
    )
    observations: list[E50MutationObservation] = []
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)
        for mutation_id, target, before, after, test_name in mutations:
            copied = _copy_program(program_root, temporary / mutation_id)
            _replace_once(copied / source_relative, before, after)
            observations.append(_observe(mutation_id, target, test_name, copied))
    if not all(item.killed for item in observations):
        survivors = ",".join(item.mutation_id for item in observations if not item.killed)
        raise RuntimeError(f"E50 mutations unexpectedly survived: {survivors}")
    return tuple(observations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    observations = run_e50_mutation_harness(Path(arguments.program_root))
    payload = json.dumps(
        {"mutations": [asdict(item) | {"killed": item.killed} for item in observations]},
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    if arguments.output:
        Path(arguments.output).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
