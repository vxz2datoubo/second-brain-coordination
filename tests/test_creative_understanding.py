from __future__ import annotations

import hashlib
import unittest

from creative_runtime.continuity import default_story_graph, verified_director_input
from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger
from creative_runtime.knowledge import KnowledgeReviewBridge, correct_from_verified_timeline
from creative_runtime.understanding import (
    MetricAnchor,
    UnderstandingCard,
    UnderstandingMap,
    UnderstandingViolation,
    assess_anchor,
    bind_verified_timeline,
)


class CreativeUnderstandingTests(unittest.TestCase):
    def verified_timeline(self):
        ledger = CreativeLedger()
        ledger.append(
            "story_initialized",
            {"state": StoryState("synthetic_archive", "arrival", {"mira": 0}).to_dict()},
            "2030-01-01T00:00:00Z",
        )
        transition = default_story_graph().transition_for(ledger.replay(), "listen")
        ledger.append(
            "player_action",
            {
                "action": PlayerAction("listen", "choice", transition.label).to_dict(),
                "resulting_patch": dict(transition.resulting_patch),
                "transition_id": transition.transition_id,
                "graph_revision": default_story_graph().revision,
            },
            "2030-01-01T00:01:00Z",
        )
        return ledger, verified_director_input(ledger)

    def test_invalid_layers_and_unsupported_blocking_claims_fail_closed(self) -> None:
        with self.assertRaisesRegex(UnderstandingViolation, "Unsupported understanding layer"):
            UnderstandingCard("UC-bad", "subject", "guessed", "statement", "issue:1", "E1_deterministic", 0.5, "2030-01-01T00:00:00Z", human_explanation="说明")
        with self.assertRaisesRegex(UnderstandingViolation, "blocking card"):
            UnderstandingCard("UC-unverified", "subject", "explicit_known", "statement", "issue:1", "E0_observed", 1.0, "2030-01-01T00:00:00Z", decision_impact="blocks", human_explanation="说明")

    def test_exact_hash_drift_is_a_hard_failure_not_a_score(self) -> None:
        anchor = MetricAnchor(
            "M-identity", "Exact head", "sha256", "exact_match", "a", "b", "a", "commit:a", "2030-01-01T00:00:00Z", True
        )
        assessment = assess_anchor(anchor)
        self.assertEqual(assessment.status, "fail")

    def test_verified_timeline_binds_to_understanding_card_and_round_trips(self) -> None:
        ledger, timeline = self.verified_timeline()
        mapped = bind_verified_timeline(timeline, len(ledger.events), "2030-01-01T00:02:00Z")
        self.assertEqual([assessment.status for assessment in mapped.assess()], ["pass", "pass", "pass", "pass"])
        restored = UnderstandingMap.from_dict(mapped.to_dict())
        self.assertEqual(canonical_json(restored.to_dict()), canonical_json(mapped.to_dict()))
        self.assertEqual({card.layer for card in restored.cards.values()}, {"explicit_known", "implicit_known", "explainable_unknown", "opaque_unknown"})
        card = restored.cards["UC-verified-timeline-" + timeline.timeline_hash[:16]]
        self.assertEqual(card.evidence_tier, "E1_deterministic")
        self.assertIn("每一步", card.human_explanation)
        self.assertTrue(all(assessment.status == "pass" for assessment in restored.assess()))

    def test_understanding_map_makes_director_quality_drift_a_visible_hard_failure(self) -> None:
        ledger, timeline = self.verified_timeline()
        mapped = bind_verified_timeline(
            timeline,
            len(ledger.events),
            "2030-01-01T00:02:00Z",
            director_can_generate=False,
        )
        assessment = next(item for item in mapped.assess() if item.metric_id.startswith("M-director-quality-"))
        self.assertEqual(assessment.status, "fail")

    def test_card_cannot_reference_missing_metric_or_unknown_superseded_record(self) -> None:
        mapped = UnderstandingMap()
        card = UnderstandingCard(
            "UC-orphan", "subject", "explicit_known", "statement", "issue:1", "E1_deterministic", 1.0,
            "2030-01-01T00:00:00Z", numeric_anchor_ids=("M-missing",), human_explanation="说明"
        )
        with self.assertRaisesRegex(UnderstandingViolation, "missing numeric anchor"):
            mapped.add_card(card)

    def test_knowledge_candidate_can_bind_to_verified_timeline_only(self) -> None:
        ledger, timeline = self.verified_timeline()
        bridge = KnowledgeReviewBridge()
        derived = correct_from_verified_timeline(
            bridge,
            "Listening first can reveal a cautious next step.",
            ledger,
            default_story_graph(),
        )
        self.assertEqual(derived.final_event_id, timeline.final_event_id)
        self.assertEqual(derived.timeline_hash, timeline.timeline_hash)
        self.assertEqual(derived.candidate.source_event_ids, (timeline.final_event_id,))
        self.assertEqual(derived.candidate.source_artifact_ids, ("timeline_sha256:" + timeline.timeline_hash,))
        self.assertEqual(
            derived.candidate.source_evidence_refs,
            (
                "graph_revision:" + timeline.graph_revision,
                "final_transition:" + str(timeline.final_transition_id),
                "final_state_sha256:" + derived.final_state_hash,
            ),
        )
        self.assertEqual(derived.final_state_hash, hashlib.sha256(canonical_json(timeline.state.to_dict()).encode("utf-8")).hexdigest())
        self.assertEqual(derived.candidate.status, "pending_human_review")


if __name__ == "__main__":
    unittest.main()
