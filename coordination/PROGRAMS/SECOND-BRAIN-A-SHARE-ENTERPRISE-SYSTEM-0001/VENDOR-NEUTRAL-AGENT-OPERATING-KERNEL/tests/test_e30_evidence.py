from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import yaml

from vendor_neutral_agent_kernel.evidence import validate_archive_manifest, validate_e30_evidence


ROOT = Path(__file__).resolve().parents[1]


class E30EvidenceTests(unittest.TestCase):
    def _evidence(self) -> dict:
        return json.loads((ROOT / "E30-COMPLETION-EVIDENCE.json").read_text(encoding="utf-8"))

    def _archive(self) -> dict:
        return yaml.safe_load((ROOT / "E30-ARCHIVE-PROVENANCE-MATRIX.yaml").read_text(encoding="utf-8"))

    def _copy_fixture(self, evidence: dict, archive: dict | None = None) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="e30-evidence-"))
        (directory / "E30-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").write_text(
            (ROOT / "E30-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (directory / "E30-COMPLETION-EVIDENCE.json").write_text(json.dumps(evidence), encoding="utf-8")
        (directory / "E30-ARCHIVE-PROVENANCE-MATRIX.yaml").write_text(
            yaml.safe_dump(archive if archive is not None else self._archive(), sort_keys=False),
            encoding="utf-8",
        )
        return directory

    def test_in_progress_evidence_has_current_route_and_no_stale_primary(self):
        evidence = self._evidence()
        evidence["status"] = "IN_PROGRESS"
        evidence["primary_tested_identity"] = {
            "authority": "E30_PRIMARY_TESTED_HEAD",
            "tested_commit": "UNRESOLVED_PRIMARY_COMMIT",
            "tested_tree": "UNRESOLVED_PRIMARY_TREE",
        }
        self.assertEqual(evidence["status"], "IN_PROGRESS")
        primary = evidence["primary_tested_identity"]
        self.assertTrue(primary["tested_commit"].startswith("UNRESOLVED_"))
        self.assertNotIn("216ff0e", primary["tested_commit"])
        self.assertNotIn("663e7392", primary["tested_tree"])

    def test_final_evidence_requires_exact_tested_identity(self):
        evidence = self._evidence()
        evidence["status"] = "FINAL"
        evidence["primary_tested_identity"] = {
            "authority": "E30_PRIMARY_TESTED_HEAD",
            "tested_commit": "a" * 40,
            "tested_tree": "b" * 40,
        }
        root = self._copy_fixture(evidence)
        result = validate_e30_evidence(root, current_commit="a" * 40, current_tree="b" * 40)
        self.assertEqual(result["status"], "FINAL")

    def test_final_evidence_rejects_wrong_tested_commit(self):
        evidence = self._evidence()
        evidence["status"] = "FINAL"
        evidence["primary_tested_identity"] = {
            "authority": "E30_PRIMARY_TESTED_HEAD",
            "tested_commit": "a" * 40,
            "tested_tree": "b" * 40,
        }
        root = self._copy_fixture(evidence)
        with self.assertRaisesRegex(ValueError, "COMMIT_MISMATCH"):
            validate_e30_evidence(root, current_commit="c" * 40, current_tree="b" * 40)

    def test_archive_manifest_rejects_repeated_root_identity(self):
        archive = self._archive()
        archive["roots"][1]["root_id"] = archive["roots"][0]["root_id"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ROOT_ID_DUPLICATE"):
                validate_archive_manifest(path)

    def test_archive_manifest_rejects_external_root_path(self):
        archive = self._archive()
        archive["roots"][0]["root_locator"] = "C:\\private\\archive"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "EXTERNAL_PATH"):
                validate_archive_manifest(path)

    def test_archive_manifest_rejects_artifact_drift(self):
        archive = self._archive()
        archive["roots"][1]["artifacts"][0]["sha256"] = "c" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SET_DRIFT"):
                validate_archive_manifest(path)

    def test_archive_manifest_rejects_missing_stream_hash(self):
        archive = self._archive()
        del archive["roots"][0]["stdout_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "REQUIRED_FIELD_MISSING"):
                validate_archive_manifest(path)

    def test_archive_manifest_rejects_nonzero_exit(self):
        archive = self._archive()
        archive["roots"][0]["exit_code"] = 1
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "NONZERO_EXIT"):
                validate_archive_manifest(path)

    def test_wpdcr_requires_autonomy_overlay(self):
        evidence = self._evidence()
        root = self._copy_fixture(evidence)
        wpdcr_path = root / "E30-WORK-PROCESS-AND-COORDINATION-REPORT.yaml"
        wpdcr = yaml.safe_load(wpdcr_path.read_text(encoding="utf-8"))
        wpdcr["autonomous_remediation_ledger"] = []
        wpdcr_path.write_text(yaml.safe_dump(wpdcr, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "OVERLAY_EMPTY:autonomous_remediation_ledger"):
            validate_e30_evidence(root)

    def test_wpdcr_requires_model_profile_overlay(self):
        evidence = self._evidence()
        root = self._copy_fixture(evidence)
        wpdcr_path = root / "E30-WORK-PROCESS-AND-COORDINATION-REPORT.yaml"
        wpdcr = yaml.safe_load(wpdcr_path.read_text(encoding="utf-8"))
        wpdcr["model_reasoning_and_execution_profile"] = None
        wpdcr_path.write_text(yaml.safe_dump(wpdcr, sort_keys=False), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "OVERLAY_EMPTY:model_reasoning_and_execution_profile"):
            validate_e30_evidence(root)

    def test_wrong_completion_signal_is_rejected(self):
        evidence = self._evidence()
        evidence["completion_signal"] = "WRONG"
        root = self._copy_fixture(evidence)
        with self.assertRaisesRegex(ValueError, "COMPLETION_SIGNAL_INVALID"):
            validate_e30_evidence(root)

    def test_in_progress_evidence_does_not_promote_runtime(self):
        evidence = self._evidence()
        self.assertEqual(evidence["authority"], "CANDIDATE_ONLY")
        self.assertEqual(evidence["activation"], "DISABLED")
        self.assertEqual(evidence["boundary"], "PUBLIC_SAFE / CANDIDATE_ONLY / DISABLED / research_only / NO_TRADE")


if __name__ == "__main__":
    unittest.main()
