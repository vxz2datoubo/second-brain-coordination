from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation_harness import (  # noqa: E402
    build_counterfactual_pairs, build_scenarios, invariant_catalog, negative_cases,
    normalized_evaluation_hash, reject_adapter_contamination, run_all_scenarios,
    run_multistep_episodes,
)


class EvaluationHarnessTests(unittest.TestCase):
    def test_48_scenarios(self):
        scenarios, results = build_scenarios(), run_all_scenarios()
        self.assertEqual(48, len(scenarios))
        self.assertEqual(48, len(results))
        self.assertTrue(all(result.event_count >= 1 for result in results))

    def test_60_invariants(self):
        catalog = invariant_catalog()
        self.assertEqual(60, len(catalog))
        self.assertTrue(all(catalog.values()), {key: value for key, value in catalog.items() if not value})

    def test_24_counterfactual_pairs_and_12_multistep_episodes(self):
        pairs = build_counterfactual_pairs()
        self.assertEqual(24, len(pairs))
        self.assertTrue(all(left != right for left, right in pairs))
        self.assertEqual(12, len(run_multistep_episodes()))

    def test_24_negative_cases_fail_closed(self):
        cases = negative_cases()
        self.assertEqual(24, len(cases))
        for name, call in cases:
            try:
                result = call()
                if isinstance(result, bool):
                    self.assertFalse(result, name)
                else:
                    self.assertFalse(result.events[0].accepted, name)
            except ValueError:
                pass

    def test_determinism_and_adapter_contamination_rejection(self):
        self.assertEqual(normalized_evaluation_hash(), normalized_evaluation_hash())
        self.assertFalse(reject_adapter_contamination({"status": "CANDIDATE", "authority_write": True, "source_capability": "SYNTHETIC_RESEARCH_ONLY", "claim_kind": "synthetic_fixture"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
