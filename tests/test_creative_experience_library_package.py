from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_experience_library_verifier", ROOT / "tools" / "verify_experience_library.py")
assert SPEC and SPEC.loader
library_verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(library_verifier)


class CreativeExperienceLibraryPackageTests(unittest.TestCase):
    def _head(self) -> str:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()

    def test_builder_and_clean_rebuild_verify_the_fixed_library_package(self) -> None:
        head = self._head()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "library-package"
            result = subprocess.run(
                [sys.executable, "tools/build_experience_library_package.py", "--expected-head", head, "--output-dir", str(package)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            library = json.loads((package / "experience_library.json").read_text(encoding="utf-8"))
            receipt = library_verifier.verify_library_package(package, head, require_clean_worktree=False)
        self.assertEqual(library["entry_count"], 2)
        self.assertEqual(receipt["status"], "experience_library_package_exactly_verified")
        self.assertEqual(receipt["scenario_count"], 2)
        self.assertEqual(receipt["package_member_count"], 3)

    def test_verifier_rejects_a_library_member_changed_after_its_manifest(self) -> None:
        head = self._head()
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / "library-package"
            result = subprocess.run(
                [sys.executable, "tools/build_experience_library_package.py", "--expected-head", head, "--output-dir", str(package)],
                cwd=ROOT,
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            (package / "experience_library.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "manifest"):
                library_verifier.verify_library_package(package, head, require_clean_worktree=False)


if __name__ == "__main__":
    unittest.main()
