from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e57_authority.canonical import ProductRun, build_canonical_payload, build_environment_payload
from e57_authority.core import AuthorityError
from e57_authority.mutations import MutationResult


def mutation(identifier: str = "MUT-ONE") -> MutationResult:
    return MutationResult(identifier, True, True, True, "1" * 64, "2" * 64, "1" * 64, 1, "3" * 64, "4" * 64)


class CanonicalEvaluatorTests(unittest.TestCase):
    def test_canonical_payload_is_stable_without_environment_streams(self) -> None:
        product = ProductRun(("python",), 0, 36, b"stdout-a", b"stderr-a")
        first = build_canonical_payload(TASK_ROOT, product, (mutation(),))
        second = build_canonical_payload(TASK_ROOT, ProductRun(("python",), 0, 36, b"stdout-b", b"stderr-b"), (mutation(),))
        self.assertEqual(first, second)

    def test_environment_payload_retains_execution_stream_hashes(self) -> None:
        payload = build_environment_payload(ProductRun(("python",), 0, 36, b"stdout", b"stderr"), (mutation(),))
        self.assertIn("stdout_sha256", payload)
        self.assertIn("stderr_sha256", payload)
        self.assertIn("stdout_sha256", payload["mutations"][0])

    def test_failed_product_cannot_be_canonicalized(self) -> None:
        with self.assertRaises(AuthorityError):
            build_canonical_payload(TASK_ROOT, ProductRun(("python",), 1, 36, b"", b""), (mutation(),))

    def test_surviving_mutation_cannot_be_canonicalized(self) -> None:
        survivor = MutationResult("MUT-SURVIVOR", True, False, True, "1" * 64, "2" * 64, "1" * 64, 0, "3" * 64, "4" * 64)
        with self.assertRaises(AuthorityError):
            build_canonical_payload(TASK_ROOT, ProductRun(("python",), 0, 36, b"", b""), (survivor,))
