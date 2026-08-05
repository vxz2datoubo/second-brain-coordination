from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from e53_authority.hygiene import scan_commit_range  # noqa: E402
from e53_authority.mutations import prove_timeout_kill_and_reap, run_product_mutations  # noqa: E402
from e53_authority.topology import TopologyError, validate_receipt_fields, verify_final_receipt  # noqa: E402


class TestProductMutations(unittest.TestCase):
    def test_mutations_are_real_and_killed(self) -> None:
        results = run_product_mutations(HERE / "src")
        self.assertEqual({item.mutation_id for item in results}, {"MUT-UTF8-STRICT", "MUT-ATOM-LEDGER", "MUT-JSON-NAN"})
        for result in results:
            with self.subTest(result.mutation_id):
                self.assertEqual(result.replacement_count, 1)
                self.assertNotEqual(result.original_sha256, result.mutated_sha256)
                self.assertTrue(result.detected)
                self.assertFalse(result.killed)

    def test_mutation_harness_restores_copied_sources(self) -> None:
        before = (HERE / "src" / "e53_authority" / "atoms.py").read_bytes()
        run_product_mutations(HERE / "src")
        self.assertEqual((HERE / "src" / "e53_authority" / "atoms.py").read_bytes(), before)

    def test_timeout_child_is_killed_and_reaped(self) -> None:
        result = prove_timeout_kill_and_reap(0.1)
        self.assertTrue(result.timed_out)
        self.assertTrue(result.reaped)


class TestHygiene(unittest.TestCase):
    def test_range_hygiene_reports_current_branch_paths(self) -> None:
        repository = HERE.parents[3]
        base = subprocess.check_output(["git", "-C", str(repository), "merge-base", "HEAD", "origin/main"], text=True).strip()
        report = scan_commit_range(repository, base)
        self.assertIn("coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-NIGHT-CLEAN-ATOMIZATION-AUTHORITY-0049-E53/PROJECT-PLAN.md", report.changed_paths)
        self.assertTrue(report.clean)

    def test_hygiene_detects_forbidden_paths_in_synthetic_repository(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e53-hygiene-") as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
            (repo / "safe.txt").write_text("safe", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
            base = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            (repo / "bad.pyc").write_bytes(b"x")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "bad"], check=True)
            report = scan_commit_range(repo, base)
            self.assertFalse(report.clean)
            self.assertEqual(report.forbidden_paths, ("bad.pyc",))


class TestReceiptTopology(unittest.TestCase):
    def test_premature_receipt_with_placeholders_is_rejected(self) -> None:
        with self.assertRaises(TopologyError):
            validate_receipt_fields({"task_id": "E53", "route_epoch": "55", "base_sha": "pending"})

    def test_complete_receipt_fields_are_accepted(self) -> None:
        receipt = {
            "task_id": "E53", "route_epoch": "55", "base_sha": "a", "plan_sha": "b", "tested_sha": "c", "receipt_sha": "d",
            "workflow": "workflow.yml", "tested_run_id": "1", "receipt_run_id": "2", "completion_signal": "ready",
        }
        validate_receipt_fields(receipt)

    def test_receipt_topology_detects_post_receipt_commit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e53-topology-") as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "test"], check=True)
            (repo / "base.txt").write_text("base", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "base"], check=True)
            (repo / "RECEIPT.md").write_text("receipt", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "receipt"], check=True)
            receipt_sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            (repo / "later.txt").write_text("later", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "later"], check=True)
            report = verify_final_receipt(repo, receipt_sha, ["RECEIPT.md"])
            self.assertTrue(report.receipt_only)
            self.assertFalse(report.final_head)
