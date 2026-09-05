from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "coordination" / "GOVERNANCE" / "CANONICAL-PYTHON-VALIDATION-RUNTIME-POLICY-v1.0.yaml"
WORKFLOW = ROOT / ".github" / "workflows" / "unified-execution-fabric.yml"


class SingleCanonicalPythonRuntimeTests(unittest.TestCase):
    def test_policy_declares_one_canonical_runtime(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn('version: "3.11"', text)
        self.assertIn('required_python_versions: 1', text)
        self.assertIn('multi_version_matrix_by_default: false', text)
        self.assertIn('NO_DEFAULT_MULTI_VERSION_MATRIX', text)

    def test_workflow_uses_only_canonical_python(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python-version: '3.11'", text)
        self.assertNotIn("matrix:", text)
        self.assertNotIn("3.13", text)

    def test_policy_keeps_multi_version_testing_as_bounded_exception(self):
        text = POLICY.read_text(encoding="utf-8")
        self.assertIn("multi_version_exception:", text)
        self.assertIn("canonical Python runtime migration", text)
        self.assertIn("declared compatibility support across Python versions", text)
        self.assertIn("NO_WEAKENING_OF_TEST_CONTENT_OR_INDEPENDENT_REVIEW", text)


if __name__ == "__main__":
    unittest.main()
