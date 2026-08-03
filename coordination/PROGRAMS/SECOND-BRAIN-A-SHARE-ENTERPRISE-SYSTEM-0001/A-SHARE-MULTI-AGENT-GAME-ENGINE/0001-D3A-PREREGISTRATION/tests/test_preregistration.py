from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from validate_preregistration import validate_text  # noqa: E402


class PreregistrationTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / "D3A-PREREGISTRATION.yaml").read_text(encoding="utf-8")

    def test_frozen_preregistration_passes(self): self.assertTrue(validate_text(self.text)[0])
    def test_missing_lockbox_fails(self): self.assertFalse(validate_text(self.text.replace("lockbox", "removed", 1))[0])
    def test_mutable_lockbox_fails(self): self.assertFalse(validate_text(self.text.replace("lockbox: {fixture_ids: [S005, S006], immutable_hash", "lockbox: {fixture_ids: [S005, S006], mutable_hash"))[0])
    def test_posthoc_tuning_fails(self): self.assertFalse(validate_text(self.text.replace("max_experiments: 0", "max_experiments: 10"))[0])
    def test_market_language_fails(self): self.assertFalse(validate_text(self.text + "\nprofit: claimed")[0])


if __name__ == "__main__": unittest.main(verbosity=2)
