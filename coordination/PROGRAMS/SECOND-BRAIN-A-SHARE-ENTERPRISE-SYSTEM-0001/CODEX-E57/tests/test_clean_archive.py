from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(os.environ.get("E57_REPO_ROOT", str(TASK_ROOT.parents[3])))
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.clean_archive import TASK_RELATIVE, verify_from_clean_archive
from e57_authority.provider import provider_evidence_to_mapping
from test_provider_topology import evidence


class CleanArchiveTests(unittest.TestCase):
    def test_exact_head_archive_reconstructs_the_provider_verifier(self) -> None:
        import subprocess

        head = subprocess.check_output(["git", "-C", str(REPOSITORY), "rev-parse", "HEAD"], text=True).strip()
        tested = evidence("TESTED", "1" * 40, 1001, 0)
        receipt = evidence("RECEIPT", "2" * 40, 1002, 1000)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tested_path, receipt_path = root / "tested.json", root / "receipt.json"
            tested_path.write_text(json.dumps(provider_evidence_to_mapping(tested)), encoding="utf-8")
            receipt_path.write_text(json.dumps(provider_evidence_to_mapping(receipt)), encoding="utf-8")
            result = verify_from_clean_archive(
                repo=REPOSITORY,
                head=head,
                tested_path=tested_path,
                receipt_path=receipt_path,
                tested_head="1" * 40,
                receipt_head="2" * 40,
                expected_tested_evidence_digest=tested.digest(),
                expected_receipt_evidence_digest=receipt.digest(),
            )
        self.assertEqual(result["verified_head"], head)
        self.assertEqual(result["verification"]["tested_run_id"], 1001)
        self.assertIn(f"{TASK_RELATIVE}/tools/verify_provider_evidence.py", result["source_sha256"])
