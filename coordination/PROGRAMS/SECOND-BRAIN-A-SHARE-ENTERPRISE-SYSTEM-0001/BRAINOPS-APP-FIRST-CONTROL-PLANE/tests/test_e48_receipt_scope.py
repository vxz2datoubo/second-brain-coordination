"""Receipt scope remains evidence-only even when a runtime path looks related."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.receipt_scope import receipt_paths_are_evidence_only  # noqa: E402


class E48ReceiptScopeTests(unittest.TestCase):
    def test_evidence_only_paths_are_accepted(self):
        self.assertTrue(
            receipt_paths_are_evidence_only(
                (
                    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                    "BRAINOPS-APP-FIRST-CONTROL-PLANE/E48/RECEIPT/AMED-RECEIPT.md",
                )
            )
        )

    def test_runtime_file_in_receipt_is_rejected(self):
        self.assertFalse(
            receipt_paths_are_evidence_only(
                (
                    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                    "BRAINOPS-APP-FIRST-CONTROL-PLANE/src/brainops_control_plane/execution_lease.py",
                )
            )
        )
