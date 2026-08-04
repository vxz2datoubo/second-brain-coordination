"""E50 executes its final verifier in an ephemeral clean clone."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_RELATIVE = Path(
    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
    "BRAINOPS-APP-FIRST-CONTROL-PLANE"
)
TASK_ID = "CODEX-BRAINOPS-TRUSTED-PROVIDER-ATTESTATION-CORRECT-GIT-GRAPH-CLEAN-CLONE-REPRODUCTION-AND-STRICT-RECEIPT-VALIDATION-CLOSURE-0046-E50"
SIGNAL = "CODEX_BRAINOPS_E50_TRUSTED_PROVIDER_RELEASE_VALIDATION_READY_FOR_GPT_REVIEW"
ATTESTATION_PATH = "coordination/PROVIDER-ATTESTATIONS/CODEX-E50-POST-RUN-PROVIDER-ATTESTATION.json"


class E50CleanCloneReproductionTests(unittest.TestCase):
    def _git(self, repository: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return completed.stdout.strip()

    def _commit_all(self, repository: Path, message: str) -> str:
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-m", message)
        return self._git(repository, "rev-parse", "HEAD")

    @staticmethod
    def _metadata(base: str, plan: str, tested: str) -> dict[str, object]:
        return {
            "task_id": TASK_ID,
            "route_epoch": 52,
            "agent_id": "CODEX",
            "completion_signal": SIGNAL,
            "base_head": base,
            "plan_head": plan,
            "tested_head": tested,
        }

    @staticmethod
    def _run(head: str, offset: int) -> dict[str, object]:
        def artifact(version: str, sequence: int) -> dict[str, object]:
            return {
                "artifact_id": offset + sequence,
                "name": f"e50-release-evidence-{version}",
                "head_sha": head,
                "digest": "sha256:" + (str(sequence) * 64)[:64],
                "expired": False,
            }

        return {
            "run_id": offset,
            "head_sha": head,
            "status": "completed",
            "conclusion": "success",
            "jobs": [
                {"job_id": offset + 11, "python_version": "3.11", "head_sha": head, "conclusion": "success"},
                {"job_id": offset + 13, "python_version": "3.13", "head_sha": head, "conclusion": "success"},
            ],
            "artifacts": [artifact("3.11", 17), artifact("3.13", 19)],
        }

    def _receipt_documents(
        self, repository: Path, base: str, plan: str, tested: str, external_attestation: Path
    ) -> dict[str, object]:
        metadata = self._metadata(base, plan, tested)
        provider = metadata | {"run": self._run(tested, 101)}
        receipt = repository / PROGRAM_RELATIVE / "E50" / "RECEIPT"
        receipt.mkdir(parents=True)
        structured = {
            "AMED-EXECUTION-RECEIPT.yaml": metadata,
            "TEST-RUN-RECEIPT.json": metadata | {"test_count": 2},
            "PROVIDER-EVIDENCE-TESTED-HEAD.json": provider,
            "UNKNOWN-REGISTRY.yaml": metadata | {"items": []},
            "AI_HANDOFF.yaml": metadata | {"source_agent": "CODEX", "target_agent": "GPT"},
            "RECEIPT-MANIFEST.json": metadata
            | {
                "receipt_commit_identity": "EXTERNAL_POST_COMMIT_PROVIDER_FACT",
                "reproduction_command": [
                    "python",
                    "-m",
                    "brainops_control_plane.e50_release_verifier",
                    "--repository-root",
                    ".",
                    "--trusted-attestation",
                    str(external_attestation),
                    "--base-head",
                    base,
                    "--plan-head",
                    plan,
                    "--tested-head",
                    tested,
                    "--receipt-head",
                    "@HEAD",
                ],
            },
        }
        for name, value in structured.items():
            (receipt / name).write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
        for name in (
            "RESEARCH-LEDGER.md",
            "UNPLANNED-IMPROVEMENT-LEDGER.md",
            "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
            "WORK-PROCESS-AND-COORDINATION-REPORT.md",
        ):
            header = "\n".join(f"{key}: {value}" for key, value in metadata.items())
            (receipt / name).write_text(header + "\n\npublic-safe evidence body\n", encoding="utf-8")
        return provider

    def test_exact_documented_command_runs_in_clean_clone_and_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            remote = root / "remote.git"
            author = root / "author"
            external = root / "external-attestation.json"
            self._git(root, "init", "--bare", "-q", str(remote))
            self._git(root, "init", "-q", "-b", "main", str(author))
            self._git(author, "config", "user.email", "e50@example.invalid")
            self._git(author, "config", "user.name", "E50 Test")
            shutil.copytree(PROGRAM_ROOT / "src", author / PROGRAM_RELATIVE / "src")
            (author / "base.txt").write_text("base\n", encoding="utf-8")
            base = self._commit_all(author, "base")
            self._git(author, "remote", "add", "origin", str(remote))
            self._git(author, "push", "-u", "origin", "main")
            self._git(author, "checkout", "-q", "-b", "e50")
            plan_file = author / PROGRAM_RELATIVE / "E50" / "E50-EXECUTION-PLAN.md"
            plan_file.parent.mkdir(parents=True)
            plan_file.write_text("plan\n", encoding="utf-8")
            plan = self._commit_all(author, "plan")
            (author / "tested.txt").write_text("tested\n", encoding="utf-8")
            tested = self._commit_all(author, "tested")
            provider = self._receipt_documents(author, base, plan, tested, external)
            receipt = self._commit_all(author, "receipt")
            self._git(author, "push", "-u", "origin", "e50")
            self._git(author, "checkout", "-q", "main")
            payload = {
                "schema_version": "E50_TRUSTED_MAIN_ATTESTATION_V1",
                "task_id": TASK_ID,
                "route_epoch": 52,
                "agent_id": "CODEX",
                "completion_signal": SIGNAL,
                "provider_evidence": {
                    "tested": provider,
                    "receipt": {
                        "receipt_head": receipt,
                        "remote_branch_head": receipt,
                        "run": self._run(receipt, 201),
                    },
                },
            }
            payload_path = author / ATTESTATION_PATH
            payload_path.parent.mkdir(parents=True)
            payload_path.write_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
            attestation_commit = self._commit_all(author, "trusted attestation")
            self._git(author, "push", "origin", "main")
            blob = self._git(author, "rev-parse", f"{attestation_commit}:{ATTESTATION_PATH}")
            self._git(author, "checkout", "-q", "-b", "forged-attestation", receipt)
            forged_payload_path = author / ATTESTATION_PATH
            forged_payload_path.parent.mkdir(parents=True)
            forged_payload_path.write_bytes(
                json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            )
            forged_attestation_commit = self._commit_all(author, "forged non-main attestation")
            self._git(author, "push", "origin", "forged-attestation")
            forged_blob = self._git(author, "rev-parse", f"{forged_attestation_commit}:{ATTESTATION_PATH}")
            envelope = {
                "source_commit": attestation_commit,
                "source_path": ATTESTATION_PATH,
                "source_blob_sha1": blob,
                "payload_sha256": hashlib.sha256(
                    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "payload": payload,
            }
            external.write_text(json.dumps(envelope, sort_keys=True) + "\n", encoding="utf-8")
            clone = root / "clean-clone"
            self._git(root, "clone", "-q", "--branch", "e50", str(remote), str(clone))
            self._git(clone, "fetch", "-q", "origin", "forged-attestation")
            manifest = json.loads(
                (clone / PROGRAM_RELATIVE / "E50" / "RECEIPT" / "RECEIPT-MANIFEST.json").read_text(encoding="utf-8")
            )
            command = list(manifest["reproduction_command"])
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(clone / PROGRAM_RELATIVE / "src")
            valid = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            tampered = list(command)
            tampered[-1] = tested
            invalid = subprocess.run(tampered, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            provider_file = clone / PROGRAM_RELATIVE / "E50" / "RECEIPT" / "PROVIDER-EVIDENCE-TESTED-HEAD.json"
            provider_file.unlink()
            missing_provider = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            self._git(clone, "reset", "--hard", "-q", receipt)
            (clone / "post-receipt.txt").write_text("forbidden\n", encoding="utf-8")
            post_receipt = self._commit_all(clone, "post receipt")
            post_receipt_result = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            declared_receipt = list(command)
            declared_receipt[-1] = receipt
            post_receipt_declared = subprocess.run(
                declared_receipt, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8"
            )
            self._git(clone, "reset", "--hard", "-q", receipt)
            extra_field_envelope = dict(envelope)
            extra_field_envelope["caller_claim"] = "not-authority"
            external.write_text(json.dumps(extra_field_envelope, sort_keys=True) + "\n", encoding="utf-8")
            extra_field = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            external.write_text(json.dumps(envelope, sort_keys=True) + "\n", encoding="utf-8")
            forged_envelope = dict(envelope)
            forged_envelope["source_commit"] = forged_attestation_commit
            forged_envelope["source_blob_sha1"] = forged_blob
            external.write_text(json.dumps(forged_envelope, sort_keys=True) + "\n", encoding="utf-8")
            forged_provider = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            external.write_text(json.dumps(envelope, sort_keys=True) + "\n", encoding="utf-8")
            manifest_path = clone / PROGRAM_RELATIVE / "E50" / "RECEIPT" / "RECEIPT-MANIFEST.json"
            bad_command = json.loads(manifest_path.read_text(encoding="utf-8"))
            bad_command["reproduction_command"][0] = "definitely-not-python"
            manifest_path.write_text(json.dumps(bad_command, sort_keys=True) + "\n", encoding="utf-8")
            unexecutable = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            self._git(clone, "reset", "--hard", "-q", receipt)
            signal_path = clone / PROGRAM_RELATIVE / "E50" / "RECEIPT" / "AMED-EXECUTION-RECEIPT.yaml"
            bad_signal = json.loads(signal_path.read_text(encoding="utf-8"))
            bad_signal["completion_signal"] = "OTHER_SIGNAL"
            signal_path.write_text(json.dumps(bad_signal, sort_keys=True) + "\n", encoding="utf-8")
            signal_mismatch = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            self._git(clone, "reset", "--hard", "-q", receipt)
            changed_provider = json.loads(provider_file.read_text(encoding="utf-8"))
            changed_provider["run"]["jobs"][0]["head_sha"] = "0" * 40
            provider_file.write_text(json.dumps(changed_provider, sort_keys=True) + "\n", encoding="utf-8")
            provider_changed = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            self._git(clone, "reset", "--hard", "-q", receipt)
            bad_blob = dict(envelope)
            bad_blob["source_blob_sha1"] = "0" * 40
            external.write_text(json.dumps(bad_blob, sort_keys=True) + "\n", encoding="utf-8")
            blob_mismatch = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")
            changed_payload = dict(payload)
            changed_payload["public_note"] = "tampered"
            changed_payload_envelope = dict(envelope)
            changed_payload_envelope["payload"] = changed_payload
            changed_payload_envelope["payload_sha256"] = hashlib.sha256(
                json.dumps(changed_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            external.write_text(json.dumps(changed_payload_envelope, sort_keys=True) + "\n", encoding="utf-8")
            payload_mismatch = subprocess.run(command, cwd=clone, env=environment, capture_output=True, text=True, encoding="utf-8")

        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertIn("READY_FOR_INDEPENDENT_REVIEW", valid.stdout)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertNotEqual(missing_provider.returncode, 0)
        self.assertNotEqual(post_receipt, receipt)
        self.assertNotEqual(post_receipt_result.returncode, 0)
        self.assertNotEqual(post_receipt_declared.returncode, 0)
        self.assertNotEqual(forged_provider.returncode, 0)
        self.assertNotEqual(extra_field.returncode, 0)
        self.assertNotEqual(unexecutable.returncode, 0)
        self.assertNotEqual(signal_mismatch.returncode, 0)
        self.assertNotEqual(provider_changed.returncode, 0)
        self.assertNotEqual(blob_mismatch.returncode, 0)
        self.assertNotEqual(payload_mismatch.returncode, 0)
