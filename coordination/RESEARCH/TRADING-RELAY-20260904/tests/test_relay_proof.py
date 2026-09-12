import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("proof", PACKAGE / "scripts" / "prove_replay.py")
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        for name in ("a", "b"):
            subprocess.run([sys.executable, "-X", "utf8", str(proof.P2 / "run_demo.py"),
                            "run-demo", "--output", str(cls.root / name)],
                           check=True, capture_output=True, timeout=60)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_subprocess_replay_equivalence(self):
        self.assertEqual(len(proof.verify_outputs(self.root / "a", self.root / "b")), 13)

    def test_source_or_fixture_hash_change_rejected(self):
        lock = json.loads(proof.LOCK.read_text(encoding="utf-8"))
        proof.validate_lock(lock)
        changed = copy.deepcopy(lock)
        changed["source_text_sha256"][next(iter(changed["source_text_sha256"]))] = "0" * 64
        with self.assertRaisesRegex(ValueError, "SOURCE_OR_FIXTURE_DRIFT"):
            proof.validate_lock(changed)

    def test_live_mode_and_time_change_rejected(self):
        lock = json.loads(proof.LOCK.read_text(encoding="utf-8"))
        for key, value in (("no_trade", False), ("mode", "live"), ("as_of", "2026-09-04T00:00:00Z")):
            changed = dict(lock, **{key: value})
            with self.assertRaises(ValueError):
                proof.validate_lock(changed)

    def test_output_tampering_rejected(self):
        path = self.root / "b" / "ValidationReport.json"
        original = path.read_bytes()
        try:
            value = json.loads(original)
            value["tampered"] = True
            path.write_bytes(proof.canonical(value))
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SET_OR_REPLAY_MISMATCH"):
                proof.verify_outputs(self.root / "a", self.root / "b")
        finally:
            path.write_bytes(original)

    def test_unexpected_artifact_rejected(self):
        path = self.root / "b" / "unexpected.json"
        try:
            path.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "ARTIFACT_SET_OR_REPLAY_MISMATCH"):
                proof.verify_outputs(self.root / "a", self.root / "b")
        finally:
            path.unlink()


if __name__ == "__main__":
    unittest.main()
