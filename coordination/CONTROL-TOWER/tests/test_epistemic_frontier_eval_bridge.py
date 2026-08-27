from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest
import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
EPISTEMIC_DIR = (
    REPO_ROOT
    / "coordination"
    / "PROPOSALS"
    / "PROGRAM-LANES"
    / "LANE-A-HARNESS-INTEGRATION"
    / "EPISTEMIC-FRONTIER-MAPPING"
)
EVALS = EPISTEMIC_DIR / "EPISTEMIC-FRONTIER-EVALS-v1.0.yaml"
REFERENCE_TEST = EPISTEMIC_DIR / "tests" / "test_epistemic_frontier_contract.py"


def _load_reference_module():
    spec = importlib.util.spec_from_file_location("epistemic_frontier_contract_reference", REFERENCE_TEST)
    if spec is None or spec.loader is None:
        raise RuntimeError("EPISODIC_FRONTIER_REFERENCE_MODULE_UNLOADABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EpistemicFrontierFoundationBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = _load_reference_module()
        cls.evals = yaml.safe_load(EVALS.read_text(encoding="utf-8"))

    def _case(self, case_id):
        return deepcopy(next(case for case in self.evals["cases"] if case["case_id"] == case_id))

    def test_all_frozen_adversarial_cases_match_independent_reference_semantics(self):
        self.assertEqual(len(self.evals["cases"]), 15)
        for case in self.evals["cases"]:
            with self.subTest(case_id=case["case_id"]):
                self.assertEqual(self.reference._validate_case(case), {})

    def test_scope_forbidden_expected_flip_is_detected(self):
        case = self._case("EKM-EVAL-012-SCOPE-FORBIDDEN")
        case["expected"]["projection_authorized"] = True
        self.assertEqual(
            self.reference._validate_case(case)["projection_authorized"],
            (True, False),
        )

    def test_sensitive_profile_expected_flip_is_detected(self):
        case = self._case("EKM-EVAL-013-SENSITIVE-PROFILE-INFERENCE")
        case["expected"]["authorized"] = True
        self.assertEqual(
            self.reference._validate_case(case)["authorized"],
            (True, False),
        )

    def test_caller_threshold_expected_flip_is_detected(self):
        case = self._case("EKM-EVAL-014-CALLER-CONTROLLED-THRESHOLD")
        case["expected"]["cognitive_band_authorized"] = True
        self.assertEqual(
            self.reference._validate_case(case)["cognitive_band_authorized"],
            (True, False),
        )


if __name__ == "__main__":
    unittest.main()
