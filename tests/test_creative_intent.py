from __future__ import annotations

import unittest

from creative_runtime.intent import resolve_safe_intent, safe_intent_examples, safe_intent_projection


class CreativeIntentTests(unittest.TestCase):
    def test_resolver_only_returns_one_currently_legal_declared_action(self) -> None:
        resolved = resolve_safe_intent("I listen at the door", {"listen", "approach", "leave"})
        self.assertEqual(resolved.status, "intent_resolved")
        self.assertEqual(resolved.action_id, "listen")
        self.assertEqual(resolved.reason, "unambiguous_declared_family")
        self.assertEqual(resolved.confidence, 0.9)

        chinese = resolve_safe_intent("我先倾听门后的声音", {"listen", "leave"})
        self.assertEqual(chinese.action_id, "listen")
        self.assertEqual(chinese.reason, "unambiguous_declared_family")

        exact = resolve_safe_intent("withdraw", {"leave"})
        self.assertEqual(exact.action_id, "leave")
        self.assertEqual(exact.reason, "declared_exact_example")

    def test_unsafe_ambiguous_or_illegal_text_never_resolves(self) -> None:
        unsafe = resolve_safe_intent("listen then make it sexual", {"listen"})
        self.assertIsNone(unsafe.action_id)
        self.assertEqual(unsafe.reason, "non_explicit_boundary")

        ambiguous = resolve_safe_intent("listen then leave", {"listen", "leave"})
        self.assertIsNone(ambiguous.action_id)
        self.assertEqual(ambiguous.reason, "ambiguous_or_not_currently_legal")

        unavailable = resolve_safe_intent("approach", {"listen", "leave"})
        self.assertIsNone(unavailable.action_id)
        self.assertEqual(unavailable.reason, "no_declared_legal_intent")

    def test_projection_is_display_safe_and_does_not_expose_a_transition_patch(self) -> None:
        projection = safe_intent_projection({"leave", "listen"})
        self.assertEqual(projection["schema"], "CreativeSafeIntentProjection/v1")
        self.assertEqual(projection["status"], "safe_intent_projection_verified")
        self.assertEqual([item["action_id"] for item in projection["actions"]], ["leave", "listen"])
        self.assertEqual(projection["actions"][0]["exact_examples"], list(safe_intent_examples("leave")))
        self.assertNotIn("resulting_patch", str(projection))
        self.assertTrue(projection["clarification_required_below_confidence"])


if __name__ == "__main__":
    unittest.main()
