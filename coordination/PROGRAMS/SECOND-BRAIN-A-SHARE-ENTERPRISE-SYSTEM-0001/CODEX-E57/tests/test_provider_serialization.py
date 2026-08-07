from __future__ import annotations

from pathlib import Path
import json
import sys
import tempfile
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError
from e57_authority.provider import provider_evidence_from_mapping, provider_evidence_to_mapping
from e57_authority.provider_verify import verify_evidence_files
from tests.e57_fixtures import provider_evidence as evidence


class ProviderSerializationTests(unittest.TestCase):
    def test_provider_evidence_round_trip_is_lossless(self) -> None:
        original = evidence("TESTED", "1" * 40, 1001, 0)
        restored = provider_evidence_from_mapping(provider_evidence_to_mapping(original))
        self.assertEqual(provider_evidence_to_mapping(restored), provider_evidence_to_mapping(original))

    def test_provider_evidence_rejects_incomplete_mapping(self) -> None:
        with self.assertRaises(AuthorityError):
            provider_evidence_from_mapping({"evidence_role": "TESTED"})

    def test_two_downloaded_evidence_files_reconstruct_independently(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tested_path, receipt_path = root / "tested.json", root / "receipt.json"
            tested = evidence("TESTED", "1" * 40, 1001, 0)
            receipt = evidence("RECEIPT", "2" * 40, 1002, 1000)
            tested_path.write_text(json.dumps(provider_evidence_to_mapping(tested)), encoding="utf-8")
            receipt_path.write_text(json.dumps(provider_evidence_to_mapping(receipt)), encoding="utf-8")
            result = verify_evidence_files(
                tested_path=tested_path,
                receipt_path=receipt_path,
                tested_head="1" * 40,
                receipt_head="2" * 40,
                expected_tested_evidence_digest=tested.digest(),
                expected_receipt_evidence_digest=receipt.digest(),
            )
            self.assertEqual(result["tested_run_id"], 1001)
            self.assertEqual(result["receipt_run_id"], 1002)

    def test_tampered_downloaded_evidence_is_rejected_when_external_digest_is_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tested_path, receipt_path = root / "tested.json", root / "receipt.json"
            tested = evidence("TESTED", "1" * 40, 1001, 0)
            receipt = evidence("RECEIPT", "2" * 40, 1002, 1000)
            altered = dict(provider_evidence_to_mapping(tested))
            altered_artifacts = [dict(item) for item in altered["artifacts"]]
            altered_artifacts[0]["archive_sha256"] = "0" * 64
            altered["artifacts"] = altered_artifacts
            tested_path.write_text(json.dumps(altered), encoding="utf-8")
            receipt_path.write_text(json.dumps(provider_evidence_to_mapping(receipt)), encoding="utf-8")
            with self.assertRaises(AuthorityError):
                verify_evidence_files(
                    tested_path=tested_path,
                    receipt_path=receipt_path,
                    tested_head="1" * 40,
                    receipt_head="2" * 40,
                    expected_tested_evidence_digest=tested.digest(),
                    expected_receipt_evidence_digest=receipt.digest(),
                )

    def test_one_external_digest_without_the_other_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tested_path, receipt_path = root / "tested.json", root / "receipt.json"
            tested_path.write_text(json.dumps(provider_evidence_to_mapping(evidence("TESTED", "1" * 40, 1001, 0))), encoding="utf-8")
            receipt_path.write_text(json.dumps(provider_evidence_to_mapping(evidence("RECEIPT", "2" * 40, 1002, 1000))), encoding="utf-8")
            with self.assertRaises(AuthorityError):
                verify_evidence_files(
                    tested_path=tested_path,
                    receipt_path=receipt_path,
                    tested_head="1" * 40,
                    receipt_head="2" * 40,
                    expected_tested_evidence_digest="0" * 64,
                )

    def test_missing_external_digests_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tested_path, receipt_path = root / "tested.json", root / "receipt.json"
            tested_path.write_text(json.dumps(provider_evidence_to_mapping(evidence("TESTED", "1" * 40, 1001, 0))), encoding="utf-8")
            receipt_path.write_text(json.dumps(provider_evidence_to_mapping(evidence("RECEIPT", "2" * 40, 1002, 1000))), encoding="utf-8")
            with self.assertRaises(AuthorityError):
                verify_evidence_files(
                    tested_path=tested_path,
                    receipt_path=receipt_path,
                    tested_head="1" * 40,
                    receipt_head="2" * 40,
                )
