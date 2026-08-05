from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "e51_provider_verifier.py"
SPEC = importlib.util.spec_from_file_location("e51_provider_verifier", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
E51 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E51)


class E51ProviderVerifierUnitTests(unittest.TestCase):
    def test_expected_manifest_argv_is_literal_and_contains_unexpanded_head(self):
        argv = E51.expected_manifest_argv()
        self.assertEqual(argv[0:3], ["python", "-m", "brainops_control_plane.e50_release_verifier"])
        self.assertEqual(argv[-2:], ["--receipt-head", "@HEAD"])
        self.assertIn(str(E51.EXTERNAL_ENVELOPE), argv)

    def test_normalized_stdout_matches_canonical_e50_digest_without_changing_raw_bytes(self):
        raw = E51.EXPECTED_STDOUT.replace(b"\n", b"\r\n")
        self.assertNotEqual(raw, E51.EXPECTED_STDOUT)
        self.assertEqual(E51.normalized_stdout(raw), E51.EXPECTED_STDOUT)
        self.assertEqual(hashlib.sha256(E51.normalized_stdout(raw)).hexdigest(), E51.EXPECTED_STDOUT_SHA256)

    def test_envelope_has_exact_five_fields_and_canonical_digest(self):
        payload = {"z": "value", "a": 1}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "outside" / "envelope.json"
            digest = E51.write_envelope(payload, destination)
            value = json.loads(destination.read_text(encoding="utf-8"))
            observed_digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        self.assertEqual(
            set(value),
            {"source_commit", "source_path", "source_blob_sha1", "payload_sha256", "payload"},
        )
        self.assertEqual(value["payload"], payload)
        self.assertEqual(digest, observed_digest)

    def test_existing_semantically_identical_envelope_is_normalized_but_unknown_content_is_rejected(self):
        payload = {"a": 1}
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "envelope.json"
            E51.write_envelope(payload, destination)
            exact = json.loads(destination.read_text(encoding="utf-8"))
            destination.write_text(json.dumps(exact, indent=2) + "\n", encoding="utf-8")
            E51.write_envelope(payload, destination)
            destination.write_text('{"unexpected":true}\n', encoding="utf-8")
            with self.assertRaises(E51.VerificationError):
                E51.write_envelope(payload, destination)

    def test_positive_assertion_rejects_nonempty_stderr_and_wrong_output(self):
        result = type("Result", (), {"returncode": 0, "stdout": E51.EXPECTED_STDOUT, "stderr": b"unexpected"})()
        with self.assertRaises(E51.VerificationError):
            E51.assert_positive(result)
        result = type("Result", (), {"returncode": 0, "stdout": b"wrong\n", "stderr": b""})()
        with self.assertRaises(E51.VerificationError):
            E51.assert_positive(result)
