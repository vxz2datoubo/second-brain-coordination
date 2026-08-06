from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError
from e57_authority.provider import DualProviderEvidence, E57_PROVIDER_CONTRACT
from e57_authority.receipt import required_anchor_values, verify_literal_post_receipt_anchor
from test_provider_topology import evidence


class ReceiptAnchorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signal = "CODEX_E57_CAPABILITY_REGISTRY_SEMANTIC_RECORD_DUAL_PROVIDER_RECEIPT_AUTHORITY_READY_FOR_GPT_REVIEW"
        self.receipt_head = "2" * 40
        self.pair = DualProviderEvidence(evidence("TESTED", "1" * 40, 1001, 0), evidence("RECEIPT", self.receipt_head, 1002, 1000))

    def _text(self) -> str:
        return "\n".join(required_anchor_values(completion_signal=self.signal, receipt_head=self.receipt_head, provider_evidence=self.pair))

    def test_literal_anchor_accepts_all_required_values(self) -> None:
        verify_literal_post_receipt_anchor(self._text(), completion_signal=self.signal, receipt_head=self.receipt_head, provider_evidence=self.pair)

    def test_missing_completion_signal_is_rejected(self) -> None:
        with self.assertRaises(AuthorityError):
            verify_literal_post_receipt_anchor(self._text().replace(self.signal, ""), completion_signal=self.signal, receipt_head=self.receipt_head, provider_evidence=self.pair)

    def test_escaped_identifier_is_rejected(self) -> None:
        with self.assertRaises(AuthorityError):
            verify_literal_post_receipt_anchor(self._text() + "\\f", completion_signal=self.signal, receipt_head=self.receipt_head, provider_evidence=self.pair)

    def test_control_character_is_rejected(self) -> None:
        with self.assertRaises(AuthorityError):
            verify_literal_post_receipt_anchor(self._text() + "\x08", completion_signal=self.signal, receipt_head=self.receipt_head, provider_evidence=self.pair)
