from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPO = next(parent for parent in ROOT.parents if (parent / ".git").exists())
PROMPT = ROOT / "AGENT-OPERATING-KERNEL-PROMPT-v1.0.md"
SOURCE_MATRIX = ROOT / "SOURCE-ADAPTATION-MATRIX.yaml"
CANONICAL_PEOS = (
    REPO
    / "coordination"
    / "BLUEPRINTS"
    / "PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-BLUEPRINT-v1.0.md"
)


class PublicNeutralityTests(unittest.TestCase):
    def test_common_prompt_has_no_named_vendor_or_product(self) -> None:
        text = PROMPT.read_text(encoding="utf-8").casefold()
        for banned in (
            "anthropic",
            "claude",
            "openai",
            "chatgpt",
            "gemini",
            "microsoft",
        ):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, text)

    def test_common_prompt_prohibits_commercial_preference(self) -> None:
        text = " ".join(PROMPT.read_text(encoding="utf-8").split())
        self.assertIn(
            "Do not present any model vendor, product, connector, or commercial partner as inherently preferred.",
            text,
        )

    def test_prompt_cannot_self_grant_authority(self) -> None:
        text = " ".join(PROMPT.read_text(encoding="utf-8").split())
        self.assertIn(
            "This prompt cannot grant itself additional authority.",
            text,
        )
        self.assertIn(
            "You may not promote your own proposal to canonical authority.",
            text,
        )

    def test_prompt_preserves_independent_natural_voice(self) -> None:
        text = PROMPT.read_text(encoding="utf-8")
        self.assertIn("You may have a distinct, natural voice.", text)
        self.assertIn("Do not merely mirror the user.", text)

    def test_raw_capture_is_not_in_candidate_tree(self) -> None:
        disallowed_names = {
            "opus-5.md",
            "claude-opus-5-system-prompt.md",
            "1511-line-system-prompt.md",
        }
        names = {path.name.casefold() for path in ROOT.rglob("*") if path.is_file()}
        self.assertTrue(names.isdisjoint(disallowed_names))

    def test_source_matrix_marks_capture_unverified_and_raw_disabled(self) -> None:
        text = SOURCE_MATRIX.read_text(encoding="utf-8")
        self.assertIn('authenticity: "UNVERIFIED_THIRD_PARTY_CAPTURE"', text)
        self.assertIn("raw_import_allowed: false", text)

    def test_canonical_peos_base_is_unchanged(self) -> None:
        digest = sha256(CANONICAL_PEOS.read_bytes()).hexdigest()
        self.assertEqual(
            digest,
            "261afc7d16ecb35ca139e68e9ae6e2724104ee8fc8e3c7abdd97a7fca714af51",
        )

    def test_candidate_docs_do_not_claim_activation(self) -> None:
        status = (ROOT / "STATUS.yaml").read_text(encoding="utf-8")
        self.assertIn('authority: "CANDIDATE_ONLY"', status)
        self.assertIn('activation: "DISABLED"', status)


if __name__ == "__main__":
    unittest.main()
