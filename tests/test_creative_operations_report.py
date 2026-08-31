from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_operations", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeOperationsReportTests(unittest.TestCase):
    def test_empty_workspace_is_read_only_and_safe_for_a_future_first_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            report = creativectl.run(["--workspace", str(workspace), "operations"])
        self.assertEqual(report["schema"], "CreativeRuntimeOperationsReport/v1")
        self.assertEqual(report["status"], "operations_report_verified")
        self.assertTrue(report["read_only"])
        self.assertTrue(report["mutation_safe"])
        self.assertEqual(report["metrics"], {
            "discovered_slot_count": 0,
            "verified_slot_count": 0,
            "invalid_slot_count": 0,
            "active_lock_count": 0,
            "stranded_atomic_temp_count": 0,
            "path_finding_count": 0,
        })

    def test_report_verifies_each_confined_slot_without_mutating_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "init", "--scenario", "three_scene"])
            creativectl.run(["--workspace", str(workspace), "--slot", "route_b", "choose", "listen"])
            before_default = (workspace / "session.json").read_bytes()
            before_route = (workspace / "slots" / "route_b.json").read_bytes()
            report = creativectl.run(["--workspace", str(workspace), "operations"])
            self.assertEqual((workspace / "session.json").read_bytes(), before_default)
            self.assertEqual((workspace / "slots" / "route_b.json").read_bytes(), before_route)
        self.assertTrue(report["mutation_safe"])
        self.assertEqual(report["metrics"]["discovered_slot_count"], 2)
        self.assertEqual(report["metrics"]["verified_slot_count"], 2)
        self.assertEqual({item["slot_id"] for item in report["slots"]}, {"default", "route_b"})
        self.assertTrue(all(item["timeline_hash"] for item in report["slots"]))

    def test_report_fails_closed_for_invalid_slot_and_interrupted_mutation_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            slots = workspace / "slots"
            slots.mkdir()
            (slots / "UPPER.json").write_text("{}", encoding="utf-8")
            locks = workspace / ".creative-runtime-locks"
            locks.mkdir(exist_ok=True)
            (locks / "default.lock").write_text("slot=default\n", encoding="ascii")
            (workspace / "session.json.replace-tmp").write_text("interrupted", encoding="utf-8")
            report = creativectl.run(["--workspace", str(workspace), "operations"])
        self.assertEqual(report["status"], "operations_attention_required")
        self.assertFalse(report["mutation_safe"])
        self.assertEqual(report["metrics"]["verified_slot_count"], 1)
        self.assertEqual(report["metrics"]["active_lock_count"], 1)
        self.assertEqual(report["metrics"]["stranded_atomic_temp_count"], 1)
        self.assertEqual(report["metrics"]["path_finding_count"], 1)
        self.assertEqual(report["path_findings"][0]["reason"], "invalid_slot_filename")
        self.assertEqual(report["active_locks"][0]["slot_id"], "default")

    def test_report_rejects_a_second_default_slot_path_instead_of_counting_it_twice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            slots = workspace / "slots"
            slots.mkdir()
            (slots / "default.json").write_text((workspace / "session.json").read_text(encoding="utf-8"), encoding="utf-8")
            report = creativectl.run(["--workspace", str(workspace), "operations"])
        self.assertEqual(report["status"], "operations_attention_required")
        self.assertFalse(report["mutation_safe"])
        self.assertEqual(report["metrics"]["discovered_slot_count"], 1)
        self.assertEqual(report["metrics"]["verified_slot_count"], 1)
        self.assertEqual(report["metrics"]["path_finding_count"], 1)
        self.assertEqual(report["path_findings"][0]["reason"], "default_slot_must_use_root_session_path")


if __name__ == "__main__":
    unittest.main()
