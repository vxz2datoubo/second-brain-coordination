"""Executable E48 mutation harness.

Every mutation is applied only to a temporary copy.  The harness reports an
observed nonzero exit for each weakening; it never claims that GitHub executed
the locally mutated workflow.
"""

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
class MutationObservation:
    mutation_id: str
    target: str
    expected_gate: str
    exit_code: int
    output_sha256: str

    @property
    def killed(self) -> bool:
        return self.exit_code != 0


def _environment(program_root: Path) -> dict[str, str]:
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH", "")
    environment["PYTHONPATH"] = str(program_root / "src") + (
        os.pathsep + existing if existing else ""
    )
    return environment


def _run(command: list[str], *, cwd: Path, program_root: Path) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=_environment(program_root),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = completed.stdout + completed.stderr
    return completed.returncode, output


def _replace_once(path: Path, before: str, after: str) -> None:
    text = path.read_text(encoding="utf-8")
    if text.count(before) != 1:
        raise RuntimeError(f"mutation target not unique: {path.name}:{before[:48]}")
    path.write_text(text.replace(before, after, 1), encoding="utf-8")


def _replace_required(path: Path, replacements: tuple[tuple[str, str], ...]) -> None:
    """Apply a compound mutation only when each exact guard exists once."""

    text = path.read_text(encoding="utf-8")
    for before, after in replacements:
        if text.count(before) != 1:
            raise RuntimeError(f"mutation target not unique: {path.name}:{before[:48]}")
        text = text.replace(before, after, 1)
    path.write_text(text, encoding="utf-8")


def _copy_program(program_root: Path, destination: Path) -> Path:
    copied = destination / "program"
    shutil.copytree(
        program_root,
        copied,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return copied


def _single_test_command(test_name: str) -> list[str]:
    """Run the named test through an explicit loader, not an import accident."""

    script = (
        "import sys, unittest; "
        "sys.path.insert(0, 'tests'); "
        f"suite = unittest.defaultTestLoader.loadTestsFromName({test_name!r}); "
        "result = unittest.TextTestRunner(verbosity=0).run(suite); "
        "raise SystemExit(0 if result.wasSuccessful() else 1)"
    )
    return [sys.executable, "-c", script]


def _observation(
    mutation_id: str,
    target: str,
    expected_gate: str,
    command: list[str],
    *,
    cwd: Path,
    program_root: Path,
) -> MutationObservation:
    exit_code, output = _run(command, cwd=cwd, program_root=program_root)
    return MutationObservation(
        mutation_id,
        target,
        expected_gate,
        exit_code,
        hashlib.sha256(output.encode("utf-8")).hexdigest(),
    )


def run_active_mutation_harness(
    program_root: Path,
    repository_root: Path,
    base_head: str,
    expected_head: str,
) -> tuple[MutationObservation, ...]:
    """Apply all required mutations and require each validator/test to turn red."""

    observations: list[MutationObservation] = []
    with tempfile.TemporaryDirectory() as directory:
        temporary = Path(directory)

        observations.append(
            _observation(
                "wrong_exact_head",
                "release_gate.py",
                "repository_exact_head",
                [
                    sys.executable,
                    "-m",
                    "brainops_control_plane.release_gate",
                    "--repository-root",
                    str(repository_root),
                    "--program-root",
                    str(program_root),
                    "--expected-head",
                    "0" * 40,
                    "--base-head",
                    base_head,
                ],
                cwd=repository_root,
                program_root=program_root,
            )
        )

        expiry = _copy_program(program_root, temporary / "expiry")
        _replace_required(
            expiry / "src" / "brainops_control_plane" / "execution_lease.py",
            (
                (
                    "return parse_rfc3339_utc(checked_at, \"lease checked_at\") >= parse_rfc3339_utc(record.expires_at, \"lease expires_at\")",
                    "return False",
                ),
                (
                    'if checked >= parse_rfc3339_utc(current.expires_at, "lease expires_at"):',
                    'if False and checked >= parse_rfc3339_utc(current.expires_at, "lease expires_at"):',
                ),
            ),
        )
        observations.append(
            _observation(
                "removed_expiry_check",
                "execution_lease.py:_transition",
                "terminal_expiry_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_terminal_commit_at_expiry_fails_closed_without_claim_mutation"
                ),
                cwd=expiry,
                program_root=expiry,
            )
        )

        terminal = _copy_program(program_root, temporary / "terminal")
        _replace_once(
            terminal / "src" / "brainops_control_plane" / "execution_lease.py",
            "if not isinstance(evidence, AttestedTerminalEvidence):",
            "if False:",
        )
        observations.append(
            _observation(
                "plain_terminal_evidence",
                "execution_lease.py:attest_terminal",
                "raw_terminal_rejection_test",
                _single_test_command(
                    "test_e46_execution_lease.E46ExecutionLeaseTests.test_raw_terminal_cannot_advance_lease"
                ),
                cwd=terminal,
                program_root=terminal,
            )
        )

        mirror = _copy_program(program_root, temporary / "mirror")
        _replace_once(
            mirror / "src" / "brainops_control_plane" / "execution_lease.py",
            "self._claim_authority.attach_invocation_with_effect_permit(",
            "self._mirror_claim.attach_invocation_with_effect_permit(",
        )
        observations.append(
            _observation(
                "mirror_claim_substitution",
                "execution_lease.py:actual_claim_invocation",
                "authority_surface_validator",
                [
                    sys.executable,
                    "-m",
                    "brainops_control_plane.authority_surface",
                    "--program-root",
                    str(mirror),
                ],
                cwd=mirror,
                program_root=mirror,
            )
        )

        binding = _copy_program(program_root, temporary / "binding")
        _replace_once(
            binding / "src" / "brainops_control_plane" / "execution_lease.py",
            'request_digest = canonical_hash(\n            {\n                "provenance_digest": claim.provenance.digest,\n                "storage_id": claim.key.storage_id,\n                "claim_id": claim.claim_id,\n                "holder": _holder_document(holder),\n                "target": target.value,\n                "decision_digest": decision_digest,\n            }\n        )\n        existing_result',
            'request_digest = canonical_hash(\n            {\n                "provenance_digest": claim.provenance.digest,\n                "storage_id": claim.key.storage_id,\n                "claim_id": claim.claim_id,\n                "holder": _holder_document(holder),\n                "target": target.value,\n                "decision_digest": "unbound",\n            }\n        )\n        existing_result',
        )
        observations.append(
            _observation(
                "weakened_request_digest",
                "execution_lease.py:capability_request_digest",
                "authority_surface_validator",
                [
                    sys.executable,
                    "-m",
                    "brainops_control_plane.authority_surface",
                    "--program-root",
                    str(binding),
                ],
                cwd=binding,
                program_root=binding,
            )
        )

        recovery = _copy_program(program_root, temporary / "recovery")
        _replace_once(
            recovery / "src" / "brainops_control_plane" / "execution_lease.py",
            "return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED)\n\n    def _transition",
            "return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE)\n\n    def _transition",
        )
        observations.append(
            _observation(
                "removed_capability_recovery",
                "execution_lease.py:attest_capability",
                "capability_response_loss_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_capability_lease_response_loss_reconciles_without_second_write"
                ),
                cwd=recovery,
                program_root=recovery,
            )
        )

        effect_recovery = _copy_program(program_root, temporary / "effect-recovery")
        _replace_once(
            effect_recovery / "src" / "brainops_control_plane" / "execution_lease.py",
            'if transitioned.code is ExecutionLeaseCode.AUTHORITY_UNAVAILABLE:\n                self._record_stage_response_loss(\n                    journal, authorized_at, "effect_lease_write_or_response_unknown"\n                )\n                return ExecutionLeaseResult(ExecutionLeaseCode.RECONCILIATION_REQUIRED, record)',
            'if transitioned.code is ExecutionLeaseCode.AUTHORITY_UNAVAILABLE:\n                return ExecutionLeaseResult(ExecutionLeaseCode.AUTHORITY_UNAVAILABLE, record)',
        )
        observations.append(
            _observation(
                "effect_response_loss_recovery_removed",
                "execution_lease.py:authorize_effect",
                "effect_response_loss_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_effect_response_loss_recovers_same_permit_without_second_lease_write"
                ),
                cwd=effect_recovery,
                program_root=effect_recovery,
            )
        )

        claim_only = _copy_program(program_root, temporary / "claim-only")
        _replace_once(
            claim_only / "src" / "brainops_control_plane" / "execution_lease.py",
            "elif claim.invocation_id != invocation_id:",
            "elif True:",
        )
        observations.append(
            _observation(
                "claim_only_invocation_recovery_removed",
                "execution_lease.py:attach_invocation",
                "claim_applied_lease_missing_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_claim_applied_invocation_recovers_lease_without_second_claim_mutation"
                ),
                cwd=claim_only,
                program_root=claim_only,
            )
        )

        lease_response = _copy_program(program_root, temporary / "lease-response")
        _replace_once(
            lease_response / "src" / "brainops_control_plane" / "execution_lease.py",
            "if record.state is ExecutionLeaseState.INVOCATION_ATTACHED:",
            "if False:",
        )
        observations.append(
            _observation(
                "lease_invocation_response_recovery_removed",
                "execution_lease.py:attach_invocation",
                "lease_applied_response_loss_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_lease_applied_invocation_response_loss_recovers_without_second_claim_mutation"
                ),
                cwd=lease_response,
                program_root=lease_response,
            )
        )

        delayed_capability = _copy_program(program_root, temporary / "delayed-capability")
        _replace_once(
            delayed_capability / "src" / "brainops_control_plane" / "execution_lease.py",
            "return ExecutionLeaseResult(existing_result.code, existing_result.record)",
            "return ExecutionLeaseResult(ExecutionLeaseCode.BINDING_MISMATCH, existing_result.record)",
        )
        observations.append(
            _observation(
                "delayed_capability_recovery_removed",
                "execution_lease.py:attest_capability",
                "delayed_capability_replay_test",
                _single_test_command(
                    "test_e48_preintegration_failures.E48PreIntegrationFailures.test_delayed_identical_capability_retry_returns_current_continuation"
                ),
                cwd=delayed_capability,
                program_root=delayed_capability,
            )
        )

        receipt = _copy_program(program_root, temporary / "receipt")
        _replace_once(
            receipt / "src" / "brainops_control_plane" / "receipt_scope.py",
            "path.startswith(_RECEIPT_PREFIX) and path.endswith(_EVIDENCE_SUFFIXES)",
            "True",
        )
        observations.append(
            _observation(
                "runtime_file_in_receipt",
                "receipt_scope.py:receipt_paths_are_evidence_only",
                "receipt_scope_test",
                _single_test_command(
                    "test_e48_receipt_scope.E48ReceiptScopeTests.test_runtime_file_in_receipt_is_rejected"
                ),
                cwd=receipt,
                program_root=receipt,
            )
        )

        provider = _copy_program(program_root, temporary / "provider")
        _replace_once(
            provider / "src" / "brainops_control_plane" / "release_gate.py",
            '"workflow": "brainops-e48.yml",',
            '"workflow": "fabricated.yml",',
        )
        provider_evidence = provider / "fabricated-provider.json"
        provider_evidence.write_text(
            json.dumps(
                {
                    "workflow": "fabricated.yml",
                    "head_sha": expected_head,
                    "required_python_versions": ["3.11", "3.13"],
                    "job_python_version": "3.13",
                    "evidence_class": "IN_JOB_POLICY_AND_CURRENT_JOB_OBSERVATION_ONLY",
                }
            ),
            encoding="utf-8",
        )
        check = provider / "provider_check.py"
        check.write_text(
            "from pathlib import Path\n"
            "from brainops_control_plane.release_gate import ReleaseGateCode, validate_repository_release_gate\n"
            f"result = validate_repository_release_gate(Path({str(repository_root)!r}), Path({str(program_root)!r}), {expected_head!r}, {base_head!r}, Path('fabricated-provider.json'))\n"
            "raise SystemExit(0 if result.code is ReleaseGateCode.PROVIDER_PRE_EVIDENCE_INVALID else 1)\n",
            encoding="utf-8",
        )
        observations.append(
            _observation(
                "fabricated_provider_evidence",
                "release_gate.py:_provider_pre_evidence",
                "provider_pre_evidence_rejection",
                [sys.executable, "provider_check.py"],
                cwd=provider,
                program_root=provider,
            )
        )

        workflow = _copy_program(program_root, temporary / "workflow")
        workflow_file = temporary / "workflow" / "brainops-e48.yml"
        original_workflow = repository_root / ".github" / "workflows" / "brainops-e48.yml"
        shutil.copyfile(original_workflow, workflow_file)
        _replace_once(
            workflow_file,
            "ref: ${{ github.event.pull_request.head.sha || github.sha }}",
            "ref: refs/pull/154/merge",
        )
        observations.append(
            _observation(
                "merge_ref_workflow_checkout",
                "brainops-e48.yml:checkout_ref",
                "workflow_policy_validator",
                [
                    sys.executable,
                    "-m",
                    "brainops_control_plane.workflow_policy",
                    "--workflow",
                    str(workflow_file),
                ],
                cwd=workflow,
                program_root=workflow,
            )
        )

        generated_output = _copy_program(program_root, temporary / "generated-output")
        generated_workflow = temporary / "generated-output" / "brainops-e48.yml"
        shutil.copyfile(original_workflow, generated_workflow)
        _replace_once(
            generated_workflow,
            "E48_EVIDENCE_DIR=$RUNNER_TEMP/e48-",
            "E48_EVIDENCE_DIR=.",
        )
        observations.append(
            _observation(
                "repository_generated_evidence",
                "brainops-e48.yml:evidence_directory",
                "workflow_policy_validator",
                [
                    sys.executable,
                    "-m",
                    "brainops_control_plane.workflow_policy",
                    "--workflow",
                    str(generated_workflow),
                ],
                cwd=generated_output,
                program_root=generated_output,
            )
        )

    if not all(item.killed for item in observations):
        failed = ",".join(item.mutation_id for item in observations if not item.killed)
        raise RuntimeError(f"mutation unexpectedly survived: {failed}")
    return tuple(observations)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--program-root", required=True)
    parser.add_argument("--repository-root", required=True)
    parser.add_argument("--base-head", required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output")
    arguments = parser.parse_args(argv)
    observations = run_active_mutation_harness(
        Path(arguments.program_root),
        Path(arguments.repository_root),
        arguments.base_head,
        arguments.expected_head,
    )
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
