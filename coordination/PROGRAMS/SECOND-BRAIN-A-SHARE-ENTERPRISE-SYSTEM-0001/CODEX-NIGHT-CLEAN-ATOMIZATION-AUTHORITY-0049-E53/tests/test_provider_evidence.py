from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
WRITER = HERE / "tools" / "write_provider_evidence.py"
COMPARATOR = HERE / "tools" / "compare_provider_artifacts.py"


class TestProviderEvidence(unittest.TestCase):
    def test_three_hash_seeds_produce_same_canonical_bytes(self) -> None:
        digests = []
        with tempfile.TemporaryDirectory(prefix="e53-provider-") as raw:
            root = Path(raw)
            for seed in ("0", "1", "777"):
                output = root / seed
                result = subprocess.run([sys.executable, str(WRITER), "--output", str(output)], cwd=HERE.parents[3], env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONDONTWRITEBYTECODE": "1"}, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                digests.append(sha256((output / "canonical-evidence.json").read_bytes()).hexdigest())
            self.assertEqual(len(set(digests)), 1)

    def test_comparator_rejects_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e53-provider-") as raw:
            root = Path(raw)
            result = subprocess.run([sys.executable, str(COMPARATOR), "--artifact-root", str(root), "--output", str(root / "out.json")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_comparator_rejects_byte_difference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e53-provider-") as raw:
            root = Path(raw)
            for index in range(6):
                path = root / str(index)
                path.mkdir()
                (path / "canonical-evidence.json").write_bytes(b"left" if index < 5 else b"right")
            result = subprocess.run([sys.executable, str(COMPARATOR), "--artifact-root", str(root), "--output", str(root / "out.json")], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)

    def test_comparator_writes_exact_six_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="e53-provider-") as raw:
            root = Path(raw)
            for index in range(6):
                path = root / str(index)
                path.mkdir()
                (path / "canonical-evidence.json").write_bytes(b"same")
            output = root / "out.json"
            result = subprocess.run([sys.executable, str(COMPARATOR), "--artifact-root", str(root), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(b'"artifact_count":6', output.read_bytes())
