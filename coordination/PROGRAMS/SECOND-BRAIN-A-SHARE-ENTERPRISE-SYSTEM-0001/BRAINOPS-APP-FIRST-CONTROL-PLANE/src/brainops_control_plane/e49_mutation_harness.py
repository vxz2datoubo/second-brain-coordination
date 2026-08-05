"""Active E49 mutation evidence for hard-crash and release validators."""

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
class E49MutationObservation:
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


def _run(program_root: Path, command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=program_root,
        env=_environment(program_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.returncode, completed.stdout + completed.stderr


def _observe(
    mutation_id: str,
    target: str,
    expected_test: str,
    copied: Path,
    command: list[str],
) -> E49MutationObservation:
    exit_code, output = _run(copied, command)
    return E49MutationObservation(
        mutation_id,
        target,
        expected_test,
        exit_code,
        hashlib.sha256(output.encode("utf-8")).hexdigest(),
    )


def run_e49_mutation_harness(program_root: Path) -> tuple[E49MutationObservation, ...]:
    """Require every E49 weakening to turn its named validator red."""

    observations: list[E49MutationObservation] = []
    source = program_root / "src" / "brainops_control_plane"
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)

        hard_cuts = (
            (
                "effect_hard_crash_cut_removed",
                'self._after_lease_mutation("effect_lease_cas_before_stage_journal")',
                "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_effect_lease_cas_recovers_without_second_lease_write",
            ),
            (
                "claim_hard_crash_cut_removed",
                'self._after_lease_mutation("claim_invocation_cas_before_stage_journal")',
                "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_claim_invocation_cas_recovers_only_missing_phases",
            ),
            (
                "invocation_hard_crash_cut_removed",
                'self._after_lease_mutation("invocation_lease_cas_before_stage_journal")',
                "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_invocation_lease_cas_recovers_journal_without_second_mutation",
            ),
            (
                "journal_lease_phase_hard_crash_cut_removed",
                'self._after_lease_mutation(\n                    "invocation_stage_journal_lease_mutation_before_complete"\n                )',
                "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_journal_lease_phase_completes_without_second_mutation",
            ),
        )
        for mutation_id, before, test_name in hard_cuts:
            copied = _copy_program(program_root, temporary / mutation_id)
            _replace_once(
                copied / "src" / "brainops_control_plane" / "execution_lease.py",
                before,
                "pass",
            )
            observations.append(
                _observe(
                    mutation_id,
                    "execution_lease.py",
                    test_name,
                    copied,
                    _named_test(test_name),
                )
            )

        completion = _copy_program(program_root, temporary / "journal-completion")
        _replace_once(
            completion / "src" / "brainops_control_plane" / "execution_lease.py",
            "if journal.phase in {\n            LeaseStageOperationPhase.LEASE_MUTATION_APPLIED,\n            LeaseStageOperationPhase.RECONCILED,\n        }:",
            "if False:",
        )
        observations.append(
            _observe(
                "lease_journal_completion_removed",
                "execution_lease.py:_recover_stage_completion",
                "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_effect_lease_cas_recovers_without_second_lease_write",
                completion,
                _named_test(
                    "test_e49_hard_crash_recovery.E49HardCrashRecoveryTests.test_hard_kill_after_effect_lease_cas_recovers_without_second_lease_write"
                ),
            )
        )

        provider_mutations = (
            (
                "caller_declared_success_bypass",
                "if evidence.declared_success:",
                "if False:",
                "test_e49_provider_release.E49ProviderReleaseTests.test_caller_declared_success_is_not_provider_evidence",
            ),
            (
                "receipt_placeholder_bypass",
                "if any(token in combined for token in _FORBIDDEN_RECEIPT_TOKENS):",
                "if False:",
                "test_e49_provider_release.E49ProviderReleaseTests.test_placeholder_and_invalid_reproduction_command_fail_closed",
            ),
            (
                "required_evidence_family_bypass",
                "missing = tuple(sorted(required - names))",
                "missing = ()",
                "test_e49_provider_release.E49ProviderReleaseTests.test_missing_evidence_family_is_rejected",
            ),
            (
                "reproduction_command_bypass",
                "if command not in combined or tested_head not in combined:",
                "if False:",
                "test_e49_provider_release.E49ProviderReleaseTests.test_invalid_reproduction_command_is_rejected_after_identity_marker",
            ),
            (
                "remote_receipt_head_bypass",
                "or evidence.remote_branch_head != receipt_head",
                "or False",
                "test_e49_provider_release.E49ProviderReleaseTests.test_changed_remote_branch_head_is_not_accepted_as_receipt_head",
            ),
            (
                "expired_artifact_bypass",
                "or artifact.expired",
                "or False",
                "test_e49_provider_release.E49ProviderReleaseTests.test_expired_provider_artifacts_are_rejected",
            ),
            (
                "wrong_provider_job_head_bypass",
                "or job.head_sha != head",
                "or False",
                "test_e49_provider_release.E49ProviderReleaseTests.test_wrong_provider_job_head_is_rejected",
            ),
            (
                "receipt_topology_bypass",
                "return bool(checked) and all(",
                "return True or all(",
                "test_e49_provider_release.E49ProviderReleaseTests.test_receipt_topology_allows_only_nonempty_evidence_paths",
            ),
        )
        for mutation_id, before, after, test_name in provider_mutations:
            copied = _copy_program(program_root, temporary / mutation_id)
            _replace_once(
                copied / "src" / "brainops_control_plane" / "release_verifier.py",
                before,
                after,
            )
            observations.append(
                _observe(
                    mutation_id,
                    "release_verifier.py",
                    test_name,
                    copied,
                    _named_test(test_name),
                )
            )

    if not all(item.killed for item in observations):
        survivors = ",".join(item.mutation_id for item in observations if not item.killed)
        raise RuntimeError(f"E49 mutations unexpectedly survived: {survivors}")
    return tuple(observations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    observations = run_e49_mutation_harness(Path(arguments.program_root))
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
