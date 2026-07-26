"""D2 core regression tests: synthetic inputs only, no market interfaces."""
from __future__ import annotations

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d2_game_core import (  # noqa: E402
    ActionLabel, AgentInformationSet, AgentState, CandidateAction, HiddenTypePosterior,
    ParticipantArchetypeHypothesis, ParticipantFamily, ParticipantSubtype, SYNTHETIC_CAPABILITY,
    arbitrate, run_bounded_counterfactual_episode, run_one_step_counterfactual,
    total_system_conserved,
)
from synthetic_engine.fixtures import INVENTORY, market, order  # noqa: E402
from synthetic_engine.types import InventoryState, OrderSide, SyntheticLot  # noqa: E402


def posterior(subtype=ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, weight=1.0):
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(
        subtype, weight, ("synthetic:evidence",), ("synthetic:counter",), "synthetic alternative",
    ),))


def agent(name, subtype=ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, inventory=INVENTORY, available=100, unknowns=()):
    return AgentState(name, posterior(subtype), AgentInformationSet(available, ("synthetic:observable",), tuple(unknowns), (), SYNTHETIC_CAPABILITY), inventory)


def action(name, agent_id, sequence, *, side=OrderSide.BUY, qty=1, conflict=None, assumptions=("assumption:one",), label=ActionLabel.FEASIBLE, **kwargs):
    return CandidateAction(name, agent_id, label, order(name, side=side, qty=qty), tuple(assumptions), ("synthetic:evidence",), conflict, arrival_sequence=sequence, **kwargs)


class StatefulMultiAgentCoreTests(unittest.TestCase):
    def setUp(self):
        self.market = market()
        self.retail = agent("retail", ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, INVENTORY)
        self.quant = agent("quant", ParticipantSubtype.SYSTEMATIC_REBALANCER, InventoryState((SyntheticLot("quant-seasoned", "2026-07-25", 7),), settled_trade_date="2026-07-26"))
        self.active = agent("active", ParticipantSubtype.EVENT_DRIVEN_ACTIVE, INVENTORY)

    def test_canonical_four_families_and_nine_subtypes_remain_defined(self):
        self.assertEqual(len(ParticipantFamily), 4)
        self.assertEqual(len(ParticipantSubtype), 9)

    def test_each_agent_has_independent_evolving_portfolio(self):
        result = arbitrate("independent", self.market, (self.retail, self.quant), (
            action("r-buy", "retail", 10, qty=2),
            action("q-sell", "quant", 20, side=OrderSide.SELL, qty=3),
        ))
        states = {state.agent_id: state for state in result.final_agent_portfolios}
        self.assertNotEqual(states["retail"].initial_inventory, states["retail"].final_inventory)
        self.assertNotEqual(states["quant"].initial_inventory, states["quant"].final_inventory)
        self.assertEqual(states["retail"].net_filled_quantity, 2)
        self.assertEqual(states["quant"].net_filled_quantity, -3)
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertIsNone(result.final_inventory)

    def test_action_never_mutates_non_owner_portfolio(self):
        result = arbitrate("ownership", self.market, (self.retail, self.quant), (action("r-only", "retail", 1, qty=2),))
        states = {state.agent_id: state for state in result.final_agent_portfolios}
        self.assertNotEqual(states["retail"].pre_state_hash, states["retail"].post_state_hash)
        self.assertEqual(states["quant"].pre_state_hash, states["quant"].post_state_hash)

    def test_declared_arrival_sequence_not_agent_id_controls_conflict(self):
        result = arbitrate("conflict", self.market, (self.retail, self.quant), (
            action("z-first", "quant", 1, conflict="scarce-resource"),
            action("a-second", "retail", 2, conflict="scarce-resource"),
        ))
        self.assertTrue(result.events[0].accepted)
        self.assertFalse(result.events[1].accepted)
        self.assertIn("CONFLICT_RESOURCE_ALREADY_CLAIMED", result.events[1].rejected_reason_codes)
        self.assertEqual(result.shared_market_state.claimed_conflict_keys, ("scarce-resource",))

    def test_duplicate_arrival_sequence_fails_closed_before_sorting(self):
        with self.assertRaisesRegex(ValueError, "AMBIGUOUS_ACTION_ARRIVAL_SEQUENCE"):
            arbitrate("arrival", self.market, (self.retail, self.quant), (
                action("one", "retail", 1), action("two", "quant", 1),
            ))

    def test_duplicate_action_replay_is_explicitly_rejected(self):
        duplicate = action("same", "retail", 1)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ACTION_ID"):
            arbitrate("duplicate", self.market, (self.retail,), (duplicate, replace(duplicate, arrival_sequence=2)))

    def test_malformed_top_level_collection_fails_before_attribute_access(self):
        with self.assertRaisesRegex(ValueError, "INVALID_TOP_LEVEL_COLLECTION"):
            arbitrate("bad-collection", self.market, "not-agents", ())
        with self.assertRaisesRegex(ValueError, "INVALID_ACTION_OBJECT"):
            arbitrate("bad-action", self.market, (self.retail,), (object(),))
        with self.assertRaisesRegex(ValueError, "INVALID_AGENT_OBJECT"):
            arbitrate("bad-agent", self.market, (object(),), ())

    def test_family_subtype_and_posterior_validation_fail_closed(self):
        invalid = AgentState("invalid", posterior(), self.retail.information, self.retail.inventory)
        invalid = replace(invalid, posterior=HiddenTypePosterior((ParticipantArchetypeHypothesis(
            "not-subtype", 1.0, ("synthetic:evidence",), (), "alternative",
        ),)))
        result = arbitrate("invalid-posterior", self.market, (invalid,), (action("bad", "invalid", 1),))
        self.assertFalse(result.events[0].accepted)
        self.assertIn("UNKNOWN_PARTICIPANT_SUBTYPE", result.events[0].rejected_reason_codes)

    def test_unknown_agent_blocked_and_existing_owner_preserved(self):
        result = arbitrate("unknown-agent", self.market, (self.retail,), (action("unknown", "nobody", 1),))
        self.assertFalse(result.events[0].accepted)
        self.assertIn("UNKNOWN_AGENT", result.events[0].rejected_reason_codes)
        self.assertEqual(result.final_agent_portfolios[0].pre_state_hash, result.final_agent_portfolios[0].post_state_hash)

    def test_incomplete_information_abstains_without_state_change(self):
        incomplete = agent("incomplete", inventory=INVENTORY, unknowns=("unknown:availability",))
        candidate = action("wait", "incomplete", 1, requires_complete_information=True)
        result = arbitrate("unknowns", self.market, (incomplete,), (candidate,))
        self.assertEqual(result.events[0].outcome_status, "ABSTAINED")
        self.assertEqual(result.final_agent_portfolios[0].pre_state_hash, result.final_agent_portfolios[0].post_state_hash)

    def test_future_information_is_blocked(self):
        future = agent("future", available=101)
        result = arbitrate("future", self.market, (future,), (action("future-action", "future", 1),))
        self.assertIn("AGENT_FUTURE_INFORMATION", result.events[0].rejected_reason_codes)

    def test_causal_parent_rejects_unknown_and_accepts_prior(self):
        unknown = action("unknown-parent", "retail", 1, causal_parent_event_ids=("not-a-real-event",))
        blocked = arbitrate("parents", self.market, (self.retail,), (unknown,))
        self.assertIn("UNKNOWN_OR_FORWARD_CAUSAL_PARENT", blocked.events[0].rejected_reason_codes)
        first = action("first", "retail", 1)
        initial = arbitrate("parents-ok", self.market, (self.retail,), (first,))
        second = action("second", "retail", 2, causal_parent_event_ids=(initial.events[0].event_id,))
        continued = arbitrate("parents-ok-next", self.market, (self.retail,), (second,), prior_events=initial.events)
        self.assertNotIn("UNKNOWN_OR_FORWARD_CAUSAL_PARENT", continued.events[0].rejected_reason_codes)
        self.assertEqual(continued.causal_history_event_ids, (initial.events[0].event_id,))

    def test_per_agent_pre_and_post_and_system_hashes_are_recorded(self):
        result = arbitrate("hashes", self.market, (self.retail, self.quant), (
            action("one", "retail", 1), action("two", "quant", 2),
        ))
        self.assertEqual(len(result.total_system_state_hash), 64)
        self.assertEqual(len(result.ledger_hash), 64)
        self.assertEqual(len(result.events[0].system_pre_state_hash), 64)
        self.assertEqual(len(result.events[1].system_post_state_hash), 64)
        self.assertNotEqual(result.events[0].system_pre_state_hash, result.events[1].system_post_state_hash)

    def test_one_step_counterfactual_changes_exactly_one_action(self):
        candidate = action("affected", "retail", 1, assumptions=("assumption:changed",))
        result = run_one_step_counterfactual("cf", self.market, (self.retail,), (candidate,), "assumption:changed")
        self.assertEqual(result.changed_action_ids, ("affected",))
        self.assertNotEqual(result.baseline.ledger_hash, result.alternative.ledger_hash)

    def test_stateful_episode_carries_prior_portfolios_and_causal_history(self):
        actions = (
            action("retail-buy", "retail", 1, assumptions=("a1",)),
            action("quant-buy", "quant", 2, assumptions=("a2",)),
        )
        episode = run_bounded_counterfactual_episode("episode", self.market, (self.retail, self.quant), actions, ("a1", "a2"))
        self.assertEqual(len(episode.runs), 2)
        self.assertGreater(len(episode.runs[1].causal_history_event_ids), 0)
        prior_states = {state.agent_id: state.post_state_hash for state in episode.runs[0].final_agent_portfolios}
        next_states = {state.agent_id: state.pre_state_hash for state in episode.runs[1].final_agent_portfolios}
        self.assertEqual(prior_states, next_states)
        self.assertEqual(episode.final_state_hash, episode.runs[-1].total_system_state_hash)

    def test_episode_bound_and_duplicate_assumptions_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "INVALID_COUNTERFACTUAL_ASSUMPTION_SEQUENCE"):
            run_bounded_counterfactual_episode("bad", self.market, (self.retail,), (action("one", "retail", 1),), ("x", "x"))
        with self.assertRaisesRegex(ValueError, "INVALID_COUNTERFACTUAL_MAX_STEPS"):
            run_bounded_counterfactual_episode("bad-limit", self.market, (self.retail,), (action("one", "retail", 1),), ("assumption:one",), max_steps=13)

    def test_determinism_same_inputs_same_complete_hashes(self):
        actions = (action("one", "retail", 1), action("two", "quant", 2))
        one = arbitrate("stable", self.market, (self.retail, self.quant), actions)
        two = arbitrate("stable", self.market, (self.retail, self.quant), actions)
        self.assertEqual(one.ledger_hash, two.ledger_hash)
        self.assertEqual(one.total_system_state_hash, two.total_system_state_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
