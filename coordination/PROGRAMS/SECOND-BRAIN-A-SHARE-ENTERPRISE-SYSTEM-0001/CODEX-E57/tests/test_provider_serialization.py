from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.core import AuthorityError
from e57_authority.provider import provider_evidence_from_mapping, provider_evidence_to_mapping
from test_provider_topology import evidence


class ProviderSerializationTests(unittest.TestCase):
    def test_provider_evidence_round_trip_is_lossless(self) -> None:
        original = evidence("TESTED", "1" * 40, 1001, 0)
        restored = provider_evidence_from_mapping(provider_evidence_to_mapping(original))
        self.assertEqual(provider_evidence_to_mapping(restored), provider_evidence_to_mapping(original))

    def test_provider_evidence_rejects_incomplete_mapping(self) -> None:
        with self.assertRaises(AuthorityError):
            provider_evidence_from_mapping({"evidence_role": "TESTED"})
