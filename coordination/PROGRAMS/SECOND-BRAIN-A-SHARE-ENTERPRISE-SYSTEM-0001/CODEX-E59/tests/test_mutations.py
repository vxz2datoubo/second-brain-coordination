from __future__ import annotations

from pathlib import Path
import sys
import unittest


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.mutations import MUTATION_SPECS, _select_unique_byte_mutation, catalog_digest  # noqa: E402


class MutationRegistryTests(unittest.TestCase):
    def test_all_e58_audit_blockers_have_unique_mutations(self) -> None:
        blockers = {spec.blocker for spec in MUTATION_SPECS}
        self.assertEqual(len(MUTATION_SPECS), 9)
        self.assertEqual(len(blockers), 9)
        self.assertTrue(all(spec.mutation_id.startswith("E59-M") for spec in MUTATION_SPECS))

    def test_every_mutation_has_an_exact_target_and_named_oracle(self) -> None:
        for spec in MUTATION_SPECS:
            self.assertTrue(spec.original)
            self.assertTrue(spec.replacement)
            self.assertTrue(spec.test_selector.startswith("test_"))
            self.assertTrue(spec.invariant)

    def test_catalog_digest_is_deterministic(self) -> None:
        self.assertEqual(catalog_digest(), catalog_digest())

    def test_crlf_target_is_selected_without_permitting_ambiguous_bytes(self) -> None:
        spec = MUTATION_SPECS[1]
        payload = spec.original.replace("\n", "\r\n").encode("utf-8")
        original, replacement = _select_unique_byte_mutation(payload, spec)
        self.assertEqual(original, payload)
        self.assertEqual(replacement, spec.replacement.replace("\n", "\r\n").encode("utf-8"))

    def test_two_line_ending_spellings_fail_closed(self) -> None:
        spec = MUTATION_SPECS[1]
        payload = spec.original.encode("utf-8") + spec.original.replace("\n", "\r\n").encode("utf-8")
        with self.assertRaisesRegex(RuntimeError, "MUTATION_TARGET_NOT_UNIQUE"):
            _select_unique_byte_mutation(payload, spec)

    def test_single_line_target_is_not_double_counted_as_two_line_endings(self) -> None:
        spec = MUTATION_SPECS[0]
        original, replacement = _select_unique_byte_mutation(spec.original.encode("utf-8"), spec)
        self.assertEqual(original, spec.original.encode("utf-8"))
        self.assertEqual(replacement, spec.replacement.encode("utf-8"))
