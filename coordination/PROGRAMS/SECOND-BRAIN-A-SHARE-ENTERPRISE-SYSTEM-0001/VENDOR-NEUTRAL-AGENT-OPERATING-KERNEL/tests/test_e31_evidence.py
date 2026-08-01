from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

import yaml

from vendor_neutral_agent_kernel.evidence import validate_e31_archive_manifest, validate_e31_evidence


ROOT = Path(__file__).resolve().parents[1]


class E31EvidenceTests(unittest.TestCase):
    def _evidence(self) -> dict:
        return json.loads((ROOT / "E31-COMPLETION-EVIDENCE.json").read_text(encoding="utf-8"))

    def _archive(self) -> dict:
        return yaml.safe_load((ROOT / "E31-ARCHIVE-PROVENANCE-MATRIX.yaml").read_text(encoding="utf-8"))

    def _write_fixture(self, evidence: dict | None = None, archive: dict | None = None, wpdcr: dict | None = None) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="e31-evidence-"))
        (directory / "E31-COMPLETION-EVIDENCE.json").write_text(
            json.dumps(evidence or self._evidence(), indent=2), encoding="utf-8"
        )
        (directory / "E31-ARCHIVE-PROVENANCE-MATRIX.yaml").write_text(
            yaml.safe_dump(archive or self._archive(), sort_keys=False), encoding="utf-8"
        )
        (directory / "E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").write_text(
            yaml.safe_dump(
                wpdcr
                or yaml.safe_load(
                    (ROOT / "E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").read_text(encoding="utf-8")
                ),
                sort_keys=False,
            ),
            encoding="utf-8",
        )
        return directory

    def test_current_in_progress_contract_is_semantically_valid(self):
        result = validate_e31_evidence(ROOT)
        self.assertEqual(result["status"], "IN_PROGRESS")
        self.assertEqual(result["archive"]["root_count"], 3)
        self.assertGreaterEqual(result["archive"]["artifact_count"], 2)

    def test_wpdcr_list_only_sections_fail_closed(self):
        wpdcr = yaml.safe_load((ROOT / "E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").read_text(encoding="utf-8"))
        wpdcr["base_sections"] = ["task_result_and_current_scope"]
        root = self._write_fixture(wpdcr=wpdcr)
        with self.assertRaisesRegex(ValueError, "SECTIONS_MUST_BE_PAYLOADS"):
            validate_e31_evidence(root)

    def test_wpdcr_semantically_empty_section_fails_closed(self):
        wpdcr = yaml.safe_load((ROOT / "E31-WORK-PROCESS-AND-COORDINATION-REPORT.yaml").read_text(encoding="utf-8"))
        wpdcr["base_sections"]["discoveries_and_opportunities"] = {"summary": "", "evidence": []}
        root = self._write_fixture(wpdcr=wpdcr)
        with self.assertRaisesRegex(ValueError, "SEMANTICALLY_EMPTY:discoveries_and_opportunities"):
            validate_e31_evidence(root)

    def test_non_final_archive_fails_closed(self):
        archive = self._archive()
        archive["status"] = "IN_PROGRESS"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "STATUS_NOT_FINAL"):
                validate_e31_archive_manifest(path)

    def test_missing_root_path_hash_fails_closed(self):
        archive = self._archive()
        del archive["roots"][0]["root_path_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "REQUIRED_FIELD_MISSING"):
                validate_e31_archive_manifest(path)

    def test_singleton_artifact_inventory_fails_closed(self):
        archive = self._archive()
        archive["declared_artifact_surface"]["path_count"] = 1
        archive["declared_artifact_surface"]["paths"] = archive["declared_artifact_surface"]["paths"][:1]
        for root in archive["roots"]:
            root["artifacts"] = root["artifacts"][:1]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "TOO_SMALL_OR_DUPLICATE"):
                validate_e31_archive_manifest(path)

    def test_artifact_set_hash_is_recomputed(self):
        archive = self._archive()
        archive["roots"][0]["artifact_set_sha256"] = "9" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SET_HASH_INVALID"):
                validate_e31_archive_manifest(path)

    def test_artifact_drift_between_roots_fails_closed(self):
        archive = self._archive()
        archive["roots"][1]["artifacts"][0]["sha256"] = "a" * 64
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SET_HASH_INVALID|ARTIFACT_SET_DRIFT"):
                validate_e31_archive_manifest(path)

    def test_duplicate_root_path_identity_fails_closed(self):
        archive = self._archive()
        archive["roots"][1]["root_path_sha256"] = archive["roots"][0]["root_path_sha256"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ROOT_PATH_IDENTITY_NOT_DISTINCT"):
                validate_e31_archive_manifest(path)

    def test_root_command_placeholder_fails_closed(self):
        archive = self._archive()
        archive["roots"][0]["command"] = archive["roots"][0]["command"].replace("d9b0bfdd72485b0aea73cdc6d29ba0b0cbb41a1b", "PLACEHOLDER")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "archive.yaml"
            path.write_text(yaml.safe_dump(archive, sort_keys=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "UNRESOLVED_MARKER"):
                validate_e31_archive_manifest(path)

    def test_final_receipt_binds_to_current_head_and_tested_parent(self):
        evidence = self._evidence()
        evidence["status"] = "FINAL"
        evidence["tested_parent_identity"] = {
            "authority": "E31_TESTED_SUBSTANTIVE_COMMIT",
            "tested_commit": "a" * 40,
            "tested_tree": "b" * 40,
            "source_run": "30680000000",
        }
        evidence["receipt_head_identity"] = {
            "authority": "E31_RECEIPT_HEAD",
            "binding": "CURRENT_PR_HEAD",
            "parent_commit": "a" * 40,
        }
        evidence["external_anchor"]["observed_commit"] = "c" * 40
        evidence["external_anchor"]["observed_tree"] = "d" * 40
        archive = self._archive()
        archive["tested_identity"]["tested_commit"] = "a" * 40
        archive["tested_identity"]["tested_tree"] = "b" * 40
        root = self._write_fixture(evidence=evidence, archive=archive)
        result = validate_e31_evidence(root, current_commit="c" * 40, current_tree="d" * 40, tested_commit="a" * 40, tested_tree="b" * 40)
        self.assertEqual(result["status"], "FINAL")

    def test_final_receipt_rejects_wrong_current_head(self):
        evidence = self._evidence()
        evidence["status"] = "FINAL"
        evidence["receipt_head_identity"] = {
            "authority": "E31_RECEIPT_HEAD",
            "binding": "CURRENT_PR_HEAD",
            "parent_commit": evidence["tested_parent_identity"]["tested_commit"],
        }
        evidence["external_anchor"]["observed_commit"] = "c" * 40
        evidence["external_anchor"]["observed_tree"] = "d" * 40
        root = self._write_fixture(evidence=evidence)
        with self.assertRaisesRegex(ValueError, "RECEIPT_EXTERNAL_COMMIT_MISMATCH"):
            validate_e31_evidence(root, current_commit="e" * 40, current_tree="d" * 40, tested_commit="d9b0bfdd72485b0aea73cdc6d29ba0b0cbb41a1b", tested_tree="746a0318cbbc773c975d327bb7bff8636752030d")

    def test_final_receipt_rejects_tested_parent_mismatch(self):
        evidence = self._evidence()
        evidence["status"] = "FINAL"
        evidence["receipt_head_identity"] = {
            "authority": "E31_RECEIPT_HEAD",
            "binding": "CURRENT_PR_HEAD",
            "parent_commit": evidence["tested_parent_identity"]["tested_commit"],
        }
        root = self._write_fixture(evidence=evidence)
        with self.assertRaisesRegex(ValueError, "TESTED_COMMIT_MISMATCH"):
            validate_e31_evidence(root, current_commit="c" * 40, current_tree="d" * 40, tested_commit="a" * 40, tested_tree="b" * 40)


if __name__ == "__main__":
    unittest.main()
