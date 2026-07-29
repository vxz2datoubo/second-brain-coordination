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
    ActionLabel, ConflictTransition, LiquidityMode, AgentInformationSet, AgentState, CandidateAction, HiddenTypePosterior,
    ParticipantArchetypeHypothesis, ParticipantFamily, ParticipantSubtype, SYNTHETIC_CAPABILITY,
    arbitrate, run_bounded_counterfactual_episode, run_one_step_counterfactual,
    total_system_accounted, total_system_conserved, verify_episode_ledger, _episode_state_hash,
    ExternalLiquidityFlowEvent, SharedMarketState, _sha, _system_hash,
)
from synthetic_engine.fixtures import INVENTORY, market, order  # noqa: E402
from synthetic_engine.types import InventoryState, MatchMode, OrderSide, SyntheticLot  # noqa: E402


def posterior(subtype=ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, weight=1.0):
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(
        subtype, weight, ("synthetic:evidence",), ("synthetic:counter",), "synthetic alternative",
    ),))


def agent(name, subtype=ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, inventory=INVENTORY, available=100, unknowns=()):
    return AgentState(name, posterior(subtype), AgentInformationSet(available, ("synthetic:observable",), tuple(unknowns), (), SYNTHETIC_CAPABILITY), inventory)


def action(name, agent_id, sequence, *, side=OrderSide.BUY, qty=1, conflict=None, assumptions=("assumption:one",), label=ActionLabel.FEASIBLE, **kwargs):
    return CandidateAction(name, agent_id, label, order(name, side=side, qty=qty), tuple(assumptions), ("synthetic:evidence",), conflict, arrival_sequence=sequence, **kwargs)


def rehashed_episode(episode, **changes):
    candidate = replace(episode, **changes)
    return replace(candidate, state_hash=_episode_state_hash(
        step_index=candidate.step_index, initial_agents=candidate.initial_agents, current_agents=candidate.current_agents,
        shared_market_state=candidate.shared_market_state, executed_action_ids=candidate.executed_action_ids,
        executed_order_ids=candidate.executed_order_ids, executed_invocation_ids=candidate.executed_invocation_ids,
        event_dag=candidate.event_dag, action_registry=candidate.action_registry,
        external_liquidity_flows=candidate.external_liquidity_flows,
        root_run_id=candidate.root_run_id, episode_id=candidate.episode_id,
        step_boundaries=candidate.step_boundaries,
    ))


class StatefulMultiAgentCoreTests(unittest.TestCase):
    def setUp(self):
        self.market = market()
        self.retail = agent("retail", ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, INVENTORY)
        self.quant = agent("quant", ParticipantSubtype.SYSTEMATIC_REBALANCER, InventoryState((SyntheticLot("quant-seasoned", "2026-07-25", 7),), settled_trade_date="2026-07-26"))
        self.active = agent("active", ParticipantSubtype.EVENT_DRIVEN_ACTIVE, INVENTORY)

    def peer_pair(self, transfer_id, *, first_options=None, second_options=None, qty=2):
        first_options = dict(first_options or {})
        second_options = dict(second_options or {})
        buy = action(
            "peer-buy-" + transfer_id, "retail", 1, qty=qty,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id=transfer_id,
            **first_options,
        )
        sell = action(
            "peer-sell-" + transfer_id, "quant", 2, side=OrderSide.SELL, qty=qty,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="retail", peer_transfer_id=transfer_id,
            **second_options,
        )
        return buy, sell

    def assert_atomic_peer_abort(self, result, reason):
        self.assertEqual(len(result.events), 2)
        self.assertTrue(all(not event.accepted and event.filled_quantity == 0 for event in result.events))
        self.assertTrue(all(reason in event.rejected_reason_codes for event in result.events))
        self.assertEqual(result.episode_state.external_liquidity_flows, ())
        states = {state.agent_id: state for state in result.final_agent_portfolios}
        self.assertEqual(states["retail"].initial_inventory, states["retail"].final_inventory)
        self.assertEqual(states["quant"].initial_inventory, states["quant"].final_inventory)
        self.assertTrue(verify_episode_ledger(result.episode_state).valid)
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))

    def assert_declaration_abort(self, result, reason):
        self.assertTrue(result.events)
        self.assertTrue(all(not event.accepted and event.filled_quantity == 0 for event in result.events))
        self.assertTrue(all(event.label is ActionLabel.BLOCKED for event in result.events))
        self.assertTrue(all(reason in event.rejected_reason_codes for event in result.events))
        self.assertEqual(result.episode_state.external_liquidity_flows, ())
        for state in result.final_agent_portfolios:
            self.assertEqual(state.initial_inventory, state.final_inventory)
        self.assertTrue(verify_episode_ledger(result.episode_state).valid)
        self.assertTrue(total_system_conserved(result.episode_state.initial_agents, result))
        self.assertTrue(total_system_accounted(result.episode_state.initial_agents, result))

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
        self.assertFalse(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))
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

    def test_episode_state_preserves_dag_without_reemitting_prior_abstention(self):
        actions = (
            action("abstain-once", "retail", 1, assumptions=("a1",), label=ActionLabel.ABSTAIN),
            action("change-quant", "quant", 2, assumptions=("a2",)),
        )
        episode = run_bounded_counterfactual_episode("episode-dag", self.market, (self.retail, self.quant), actions, ("a1", "a2"))
        first, second = episode.runs
        self.assertIsNotNone(second.episode_state)
        self.assertEqual(len(second.episode_state.event_dag), len(first.events) + len(second.events))
        self.assertEqual(tuple(event.action_id for event in second.events), ("change-quant",))
        self.assertEqual(len(second.episode_state.executed_action_ids), 2)
        self.assertTrue(verify_episode_ledger(second.episode_state).valid)

    def test_claim_release_and_reclaim_follow_explicit_lifecycle(self):
        first = arbitrate("claim", self.market, (self.retail,), (action("claim", "retail", 1, conflict="scarce"),))
        release = action("release", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.RELEASE)
        second = arbitrate("release", self.market, (self.retail,), (release,), prior_episode_state=first.episode_state)
        self.assertNotIn("scarce", second.shared_market_state.claimed_conflict_keys)
        reclaim = action("reclaim", "retail", 1, conflict="scarce")
        third = arbitrate("reclaim", self.market, (self.retail,), (reclaim,), prior_episode_state=second.episode_state)
        self.assertIn("scarce", third.shared_market_state.claimed_conflict_keys)

    def test_release_of_unclaimed_resource_fails_closed(self):
        release = action("release", "retail", 1, conflict="missing", conflict_transition=ConflictTransition.RELEASE)
        result = arbitrate("release-missing", self.market, (self.retail,), (release,))
        self.assertIn("CONFLICT_RESOURCE_NOT_CLAIMED", result.events[0].rejected_reason_codes)

    def test_expire_releases_resource_and_permits_a_later_claim(self):
        first = arbitrate("claim-expire", self.market, (self.retail,), (action("claim", "retail", 1, conflict="scarce"),))
        expire = action("expire", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.EXPIRE)
        second = arbitrate("expire", self.market, (self.retail,), (expire,), prior_episode_state=first.episode_state)
        self.assertNotIn("scarce", second.shared_market_state.claimed_conflict_keys)
        self.assertTrue(verify_episode_ledger(second.episode_state).valid)

    def test_tampered_episode_hash_is_detected(self):
        run = arbitrate("tamper", self.market, (self.retail,), (action("once", "retail", 1),))
        self.assertFalse(verify_episode_ledger(replace(run.episode_state, state_hash="0" * 64)).valid)

    def test_tampered_forward_parent_is_detected(self):
        run = arbitrate("dag", self.market, (self.retail,), (action("once", "retail", 1),))
        forged_event = replace(run.episode_state.event_dag[0], causal_parent_event_ids=("future",))
        forged = replace(run.episode_state, event_dag=(forged_event,))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_replayed_action_is_rejected_before_a_second_event_is_emitted(self):
        first_action = action("retail-conflict", "retail", 1, conflict="one-resource")
        first = arbitrate("cross-step", self.market, (self.retail,), (first_action,))
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("cross-step-next", self.market, (self.retail,), (first_action,), prior_episode_state=first.episode_state)
        self.assertEqual(len(first.episode_state.event_dag), 1)

    def test_blocked_label_is_non_executable_even_with_valid_order(self):
        result = arbitrate("blocked", self.market, (self.retail,), (
            action("blocked-action", "retail", 1, label=ActionLabel.BLOCKED),
        ))
        self.assertFalse(result.events[0].accepted)
        self.assertIn("DECLARED_BLOCKED_ACTION", result.events[0].rejected_reason_codes)

    def test_conservation_recomputes_immutable_actions_not_mutable_net_field(self):
        result = arbitrate("conservation", self.market, (self.retail,), (action("buy", "retail", 1, qty=2),))
        forged = tuple(replace(portfolio, net_filled_quantity=999) for portfolio in result.final_agent_portfolios)
        self.assertTrue(total_system_accounted((self.retail,), replace(result, final_agent_portfolios=forged)))

    def test_duplicate_prior_event_ids_fail_closed(self):
        first = arbitrate("prior", self.market, (self.retail,), (action("first", "retail", 1),))
        with self.assertRaisesRegex(ValueError, "DUPLICATE_PRIOR_EVENT_ID"):
            arbitrate("prior-next", self.market, (self.retail,), (action("second", "retail", 2),), prior_events=(first.events[0], first.events[0]))

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

    def test_external_liquidity_has_explicit_offsetting_flow_event(self):
        result = arbitrate("external-flow", self.market, (self.retail,), (action("buy", "retail", 1, qty=2),))
        flows = result.episode_state.external_liquidity_flows
        self.assertEqual(len(flows), 1)
        self.assertEqual(flows[0].agent_inventory_delta, 2)
        self.assertEqual(flows[0].external_inventory_delta, -2)
        self.assertFalse(total_system_conserved((self.retail,), result))
        self.assertTrue(total_system_accounted((self.retail,), result))

    def test_matched_peer_transfer_conserves_local_inventory_without_external_flow(self):
        buy = action("peer-buy", "retail", 1, qty=2, liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                     counterparty_agent_id="quant", peer_transfer_id="transfer-1")
        sell = action("peer-sell", "quant", 2, side=OrderSide.SELL, qty=2,
                      liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                      counterparty_agent_id="retail", peer_transfer_id="transfer-1")
        result = arbitrate("peer", self.market, (self.retail, self.quant), (buy, sell))
        self.assertTrue(all(event.accepted for event in result.events))
        self.assertEqual(result.episode_state.external_liquidity_flows, ())
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))

    def test_unpaired_peer_transfer_fails_closed(self):
        lone = action("lone-peer", "retail", 1, liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                      counterparty_agent_id="quant", peer_transfer_id="transfer-lone")
        result = arbitrate("unpaired", self.market, (self.retail, self.quant), (lone,))
        self.assertFalse(result.events[0].accepted)
        self.assertIn("PEER_TRANSFER_REQUIRES_EXACTLY_TWO_ACTIONS", result.events[0].rejected_reason_codes)
        self.assertEqual(result.episode_state.external_liquidity_flows, ())

    def test_mismatched_peer_quantities_block_both_actions(self):
        buy = action("peer-buy", "retail", 1, qty=2, liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                     counterparty_agent_id="quant", peer_transfer_id="transfer-quantity")
        sell = action("peer-sell", "quant", 2, side=OrderSide.SELL, qty=1,
                      liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                      counterparty_agent_id="retail", peer_transfer_id="transfer-quantity")
        result = arbitrate("peer-mismatch", self.market, (self.retail, self.quant), (buy, sell))
        self.assertTrue(all(not event.accepted for event in result.events))
        self.assertTrue(all("INVALID_PEER_TRANSFER_PAIR" in event.rejected_reason_codes for event in result.events))

    def test_duplicate_invocation_is_rejected_before_any_event(self):
        first = action("first", "retail", 1, invocation_id="same-invocation")
        second = action("second", "quant", 2, invocation_id="same-invocation")
        with self.assertRaisesRegex(ValueError, "DUPLICATE_INVOCATION_ID"):
            arbitrate("invocation", self.market, (self.retail, self.quant), (first, second))

    def test_duplicate_order_is_rejected_before_any_event(self):
        first = action("first", "retail", 1)
        second = replace(action("second", "quant", 2), order=first.order)
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ORDER_ID"):
            arbitrate("order", self.market, (self.retail, self.quant), (first, second))

    def test_coordinated_portfolio_and_hash_tampering_is_reconstructed_and_rejected(self):
        result = arbitrate("tamper-coordinated", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged_agent = replace(result.episode_state.current_agents[0], inventory=INVENTORY)
        forged = rehashed_episode(result.episode_state, current_agents=(forged_agent,))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("FORGED_STORED_EPISODE_STATE", verification.reason_codes)

    def test_forged_filled_quantity_is_rejected_even_when_flow_and_hash_are_recomputed(self):
        result = arbitrate("tamper-delta", self.market, (self.retail,), (action("buy", "retail", 1),))
        event = replace(result.episode_state.event_dag[0], filled_quantity=2)
        flow = replace(result.episode_state.external_liquidity_flows[0], agent_inventory_delta=2, external_inventory_delta=-2)
        forged = rehashed_episode(result.episode_state, event_dag=(event,), external_liquidity_flows=(flow,))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("FORGED_EVENT_OUTCOME", verification.reason_codes)

    def test_swapped_agent_portfolios_are_rejected_even_when_state_hash_is_recomputed(self):
        result = arbitrate("tamper-swap", self.market, (self.retail, self.quant), (
            action("retail-buy", "retail", 1), action("quant-buy", "quant", 2),
        ))
        swapped = rehashed_episode(result.episode_state, current_agents=tuple(reversed(result.episode_state.current_agents)))
        verification = verify_episode_ledger(swapped)
        self.assertFalse(verification.valid)
        self.assertIn("FORGED_STORED_EPISODE_STATE", verification.reason_codes)

    # E16-B01: stored acceptance must never decide whether the reducer runs.
    def test_e16_coordinated_accepted_to_noop_forgery_is_rejected(self):
        result = arbitrate("e16-noop", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged_event = replace(
            result.episode_state.event_dag[0], label=ActionLabel.BLOCKED, accepted=False,
            outcome_status="INVALID_OR_BLOCKED", filled_quantity=0, rejected_reason_codes=(),
            owner_post_state_hash=result.episode_state.event_dag[0].owner_pre_state_hash,
            system_post_state_hash=result.episode_state.event_dag[0].system_pre_state_hash,
        )
        forged_agent = replace(result.episode_state.current_agents[0], inventory=INVENTORY)
        forged = rehashed_episode(
            result.episode_state, current_agents=(forged_agent,), event_dag=(forged_event,),
            executed_action_ids=(), executed_order_ids=(), executed_invocation_ids=(), external_liquidity_flows=(),
        )
        self.assertFalse(verify_episode_ledger(forged).valid)

    # E16-B02: a coordinated replacement of the ID and its claim references is not enough.
    def test_e16_replaced_event_id_with_recomputed_claim_state_is_rejected(self):
        result = arbitrate("e16-id", self.market, (self.retail,), (action("claim", "retail", 1, conflict="scarce"),))
        original = result.episode_state.event_dag[0]
        replacement_id = "f" * 64
        claim_map = {"scarce": replacement_id}
        forged_event = replace(original, event_id=replacement_id)
        forged_event = replace(
            forged_event,
            system_post_state_hash=_system_hash(
                {"retail": result.final_agent_portfolios[0]}, self.market, claim_map, (replacement_id,),
            ),
        )
        forged_shared = SharedMarketState(
            self.market, ("scarce",), (("scarce", replacement_id),),
            _sha({"market": self.market, "claims": sorted(claim_map.items())}),
        )
        original_flow = result.episode_state.external_liquidity_flows[0]
        forged_flow = replace(
            original_flow, ledger_event_id=replacement_id,
            flow_id=_sha({"ledger_event_id": replacement_id, "agent_id": original_flow.agent_id,
                          "agent_delta": original_flow.agent_inventory_delta}),
        )
        forged = rehashed_episode(
            result.episode_state, event_dag=(forged_event,), shared_market_state=forged_shared,
            external_liquidity_flows=(forged_flow,),
        )
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_EVENT_ID_MISMATCH", verification.reason_codes)

    def test_e16_event_id_replacement_with_causal_reference_rewrite_is_rejected(self):
        first = arbitrate("e16-id-causal", self.market, (self.retail,), (action("seed", "retail", 1),))
        claim = action("claim", "retail", 1, conflict="scarce", causal_parent_event_ids=(first.events[0].event_id,))
        second = arbitrate("e16-id-causal-next", self.market, (self.retail,), (claim,), prior_episode_state=first.episode_state)
        replacement_id = "e" * 64
        original_first, original_claim = second.episode_state.event_dag
        rewritten_first = replace(original_first, event_id=replacement_id)
        rewritten_claim = replace(original_claim, causal_parent_event_ids=(replacement_id,))
        rewritten_flows = tuple(
            replace(
                flow, ledger_event_id=replacement_id,
                flow_id=_sha({"ledger_event_id": replacement_id, "agent_id": flow.agent_id,
                              "agent_delta": flow.agent_inventory_delta}),
            ) if flow.ledger_event_id == original_first.event_id else flow
            for flow in second.episode_state.external_liquidity_flows
        )
        forged = rehashed_episode(
            second.episode_state, event_dag=(rewritten_first, rewritten_claim),
            external_liquidity_flows=rewritten_flows,
        )
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_EVENT_ID_MISMATCH", verification.reason_codes)
        self.assertIn("EVENT_CAUSAL_PARENT_EVENT_IDS_MISMATCH", verification.reason_codes)

    # E16-B03: action semantics on the stored event are evidence, not authority.
    def test_e16_event_label_substitution_is_rejected(self):
        result = arbitrate("e16-label", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, event_dag=(replace(result.episode_state.event_dag[0], label=ActionLabel.ABSTAIN),))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e16_event_reason_substitution_is_rejected(self):
        result = arbitrate("e16-reason", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, event_dag=(replace(result.episode_state.event_dag[0], rejected_reason_codes=("FORGED",)),))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e16_event_cause_reference_substitution_is_rejected(self):
        result = arbitrate("e16-cause", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, event_dag=(replace(result.episode_state.event_dag[0], cause_refs=("forged:source",)),))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e16_event_invocation_substitution_is_rejected(self):
        result = arbitrate("e16-invocation", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, event_dag=(replace(result.episode_state.event_dag[0], invocation_id="forged-invocation"),))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e16_event_liquidity_and_peer_substitution_is_rejected(self):
        result = arbitrate("e16-liquidity", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged_event = replace(
            result.episode_state.event_dag[0], liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="forged", peer_transfer_id="forged-transfer",
        )
        forged = rehashed_episode(result.episode_state, event_dag=(forged_event,))
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e16_event_status_substitution_is_rejected(self):
        result = arbitrate("e16-status", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, event_dag=(replace(result.episode_state.event_dag[0], outcome_status="ABSTAINED"),))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_OUTCOME_STATUS_MISMATCH", verification.reason_codes)

    def test_e16_event_conflict_transition_substitution_is_rejected(self):
        result = arbitrate("e16-transition", self.market, (self.retail,), (action("claim", "retail", 1, conflict="scarce"),))
        forged_event = replace(result.episode_state.event_dag[0], conflict_transition=ConflictTransition.EXPIRE)
        verification = verify_episode_ledger(rehashed_episode(result.episode_state, event_dag=(forged_event,)))
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_CONFLICT_TRANSITION_MISMATCH", verification.reason_codes)

    def test_e16_event_counterparty_substitution_is_rejected(self):
        result = arbitrate("e16-counterparty", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged_event = replace(result.episode_state.event_dag[0], counterparty_agent_id="forged-counterparty")
        verification = verify_episode_ledger(rehashed_episode(result.episode_state, event_dag=(forged_event,)))
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_COUNTERPARTY_AGENT_ID_MISMATCH", verification.reason_codes)

    def test_e16_peer_transfer_id_substitution_is_rejected(self):
        buy = action("peer-buy", "retail", 1, qty=2, liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                     counterparty_agent_id="quant", peer_transfer_id="transfer-1")
        sell = action("peer-sell", "quant", 2, side=OrderSide.SELL, qty=2,
                      liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
                      counterparty_agent_id="retail", peer_transfer_id="transfer-1")
        result = arbitrate("e16-peer-id", self.market, (self.retail, self.quant), (buy, sell))
        forged_event = replace(result.episode_state.event_dag[0], peer_transfer_id="forged-transfer")
        forged = rehashed_episode(result.episode_state, event_dag=(forged_event,) + result.episode_state.event_dag[1:])
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("EVENT_PEER_TRANSFER_ID_MISMATCH", verification.reason_codes)

    # E16-B05: a different valid historical parent cannot substitute for the declared parent.
    def test_e16_existing_causal_parent_substitution_is_rejected(self):
        first = action("first", "retail", 1)
        second = action("second", "retail", 2, causal_parent_event_ids=())
        initial = arbitrate("e16-parent", self.market, (self.retail,), (first, second))
        third = action("third", "retail", 1, causal_parent_event_ids=(initial.events[0].event_id,))
        continued = arbitrate("e16-parent-next", self.market, (self.retail,), (third,), prior_episode_state=initial.episode_state)
        forged_event = replace(continued.episode_state.event_dag[-1], causal_parent_event_ids=(initial.events[1].event_id,))
        forged = rehashed_episode(continued.episode_state, event_dag=continued.episode_state.event_dag[:-1] + (forged_event,))
        self.assertFalse(verify_episode_ledger(forged).valid)

    # E16-B04: every generated terminal block consumes action, invocation, and supplied order identity.
    def test_e16_generated_blocked_invocation_is_reserved_across_steps(self):
        blocked = action("blocked", "nobody", 1, invocation_id="blocked-invocation")
        first = arbitrate("e16-blocked-invocation", self.market, (self.retail,), (blocked,))
        replay = action("different-action", "retail", 1, invocation_id="blocked-invocation")
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e16-blocked-invocation-next", self.market, (self.retail,), (replay,), prior_episode_state=first.episode_state)

    def test_e16_generated_blocked_order_is_reserved_across_steps(self):
        blocked = action("blocked", "nobody", 1)
        first = arbitrate("e16-blocked-order", self.market, (self.retail,), (blocked,))
        replay = replace(action("different-action", "retail", 1), order=blocked.order)
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e16-blocked-order-next", self.market, (self.retail,), (replay,), prior_episode_state=first.episode_state)

    def test_e16_generated_unknown_agent_block_is_independently_reconstructable(self):
        result = arbitrate("e16-unknown", self.market, (self.retail,), (action("unknown", "nobody", 1),))
        verification = verify_episode_ledger(result.episode_state)
        self.assertTrue(verification.valid)
        self.assertEqual(result.episode_state.executed_action_ids, ("unknown",))
        self.assertEqual(result.episode_state.executed_invocation_ids, ("unknown",))
        self.assertEqual(result.episode_state.executed_order_ids, ("unknown",))

    def test_e16_release_and_expire_semantics_are_reconstructed_not_trusted(self):
        first = arbitrate("e16-resource", self.market, (self.retail,), (action("claim", "retail", 1, conflict="scarce"),))
        release = action("release", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.RELEASE)
        second = arbitrate("e16-resource-release", self.market, (self.retail,), (release,), prior_episode_state=first.episode_state)
        self.assertTrue(verify_episode_ledger(second.episode_state).valid)
        forged_event = replace(second.episode_state.event_dag[-1], accepted=False, outcome_status="INVALID_OR_BLOCKED")
        self.assertFalse(verify_episode_ledger(rehashed_episode(
            second.episode_state, event_dag=second.episode_state.event_dag[:-1] + (forged_event,),
        )).valid)
        expire = action("expire", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.EXPIRE)
        third = arbitrate("e16-resource-expire", self.market, (self.retail,), (expire,), prior_episode_state=first.episode_state)
        self.assertTrue(verify_episode_ledger(third.episode_state).valid)

    def test_e16_recomputed_episode_step_tampering_is_rejected(self):
        result = arbitrate("e16-step", self.market, (self.retail,), (action("buy", "retail", 1),))
        forged = rehashed_episode(result.episode_state, step_index=result.episode_state.step_index + 1)
        self.assertFalse(verify_episode_ledger(forged).valid)

    # E17: peer transfer groups settle over a shared pre-state or abort together.
    def test_e17_unknown_parent_on_second_leg_aborts_both_peer_legs(self):
        result = arbitrate(
            "e17-parent-second", self.market, (self.retail, self.quant),
            self.peer_pair("parent-second", second_options={"causal_parent_event_ids": ("missing-parent",)}),
        )
        self.assert_atomic_peer_abort(result, "PEER_GROUP_UNKNOWN_OR_FORWARD_CAUSAL_PARENT")

    def test_e17_unknown_parent_on_first_leg_aborts_both_peer_legs_symmetrically(self):
        result = arbitrate(
            "e17-parent-first", self.market, (self.retail, self.quant),
            self.peer_pair("parent-first", first_options={"causal_parent_event_ids": ("missing-parent",)}),
        )
        self.assert_atomic_peer_abort(result, "PEER_GROUP_UNKNOWN_OR_FORWARD_CAUSAL_PARENT")

    def test_e17_release_on_one_peer_leg_aborts_both_before_resource_mutation(self):
        result = arbitrate(
            "e17-release", self.market, (self.retail, self.quant),
            self.peer_pair("release", second_options={"conflict": "scarce", "conflict_transition": ConflictTransition.RELEASE}),
        )
        self.assert_atomic_peer_abort(result, "UNSUPPORTED_PEER_CONFLICT_RESOURCE")
        self.assertEqual(result.shared_market_state.claimed_conflict_keys, ())

    def test_e17_expire_on_one_peer_leg_aborts_both_before_resource_mutation(self):
        result = arbitrate(
            "e17-expire", self.market, (self.retail, self.quant),
            self.peer_pair("expire", first_options={"conflict": "scarce", "conflict_transition": ConflictTransition.EXPIRE}),
        )
        self.assert_atomic_peer_abort(result, "UNSUPPORTED_PEER_CONFLICT_RESOURCE")

    def test_e17_claim_on_one_peer_leg_aborts_both_before_resource_mutation(self):
        result = arbitrate(
            "e17-claim", self.market, (self.retail, self.quant),
            self.peer_pair("claim", first_options={"conflict": "scarce"}),
        )
        self.assert_atomic_peer_abort(result, "UNSUPPORTED_PEER_CONFLICT_RESOURCE")

    def test_e17_valid_peer_commit_has_shared_pre_and_post_system_state(self):
        result = arbitrate("e17-commit", self.market, (self.retail, self.quant), self.peer_pair("commit"))
        self.assertEqual(len(result.events), 2)
        self.assertTrue(all(event.accepted for event in result.events))
        self.assertEqual({event.system_pre_state_hash for event in result.events}, {result.events[0].system_pre_state_hash})
        self.assertEqual({event.system_post_state_hash for event in result.events}, {result.events[0].system_post_state_hash})
        self.assertEqual(result.episode_state.external_liquidity_flows, ())
        self.assertTrue(verify_episode_ledger(result.episode_state).valid)
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))

    def test_e17_valid_no_fill_peer_pair_commits_zero_complementary_delta(self):
        buy, sell = self.peer_pair("no-fill")
        buy = replace(buy, order=replace(buy.order, match_mode=MatchMode.NO_FILL_CANCEL))
        sell = replace(sell, order=replace(sell.order, match_mode=MatchMode.NO_FILL_CANCEL))
        result = arbitrate("e17-no-fill", self.market, (self.retail, self.quant), (buy, sell))
        self.assertTrue(all(event.accepted and event.filled_quantity == 0 for event in result.events))
        self.assertTrue(verify_episode_ledger(result.episode_state).valid)
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))

    def test_e17_valid_partial_fill_peer_pair_commits_complementary_delta(self):
        buy, sell = self.peer_pair("partial", qty=3)
        buy = replace(buy, order=replace(buy.order, match_mode=MatchMode.PARTIAL, partial_fill_quantity=1))
        sell = replace(sell, order=replace(sell.order, match_mode=MatchMode.PARTIAL, partial_fill_quantity=1))
        result = arbitrate("e17-partial", self.market, (self.retail, self.quant), (buy, sell))
        self.assertEqual(tuple(event.filled_quantity for event in result.events), (1, 1))
        self.assertTrue(all(event.accepted for event in result.events))
        self.assertTrue(verify_episode_ledger(result.episode_state).valid)
        self.assertTrue(total_system_conserved((self.retail, self.quant), result))
        self.assertTrue(total_system_accounted((self.retail, self.quant), result))

    def test_e17_declared_blocked_peer_leg_aborts_both(self):
        result = arbitrate(
            "e17-declared-blocked", self.market, (self.retail, self.quant),
            self.peer_pair("declared-blocked", second_options={"label": ActionLabel.BLOCKED}),
        )
        self.assert_atomic_peer_abort(result, "PEER_GROUP_NONEXECUTABLE_ACTION")

    def test_e17_incomplete_information_on_one_peer_leg_aborts_both(self):
        unknown_quant = agent(
            "quant", ParticipantSubtype.SYSTEMATIC_REBALANCER,
            InventoryState((SyntheticLot("quant-seasoned", "2026-07-25", 7),), settled_trade_date="2026-07-26"),
            unknowns=("opaque-context",),
        )
        result = arbitrate(
            "e17-information", self.market, (self.retail, unknown_quant),
            self.peer_pair("information", second_options={"requires_complete_information": True}),
        )
        self.assert_atomic_peer_abort(result, "PEER_GROUP_INCOMPLETE_INFORMATION")

    def test_e17_aborted_peer_invocation_and_order_identities_cannot_be_reused(self):
        pair = self.peer_pair("abort-identities", second_options={"causal_parent_event_ids": ("missing-parent",)})
        first = arbitrate("e17-identities", self.market, (self.retail, self.quant), pair)
        reused = replace(action("later", "retail", 1, invocation_id=pair[0].effective_invocation_id), order=pair[1].order)
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e17-identities-next", self.market, (self.retail, self.quant), (reused,), prior_episode_state=first.episode_state)

    def test_e17_aborted_peer_transfer_id_cannot_be_reused_across_steps(self):
        pair = self.peer_pair("abort-transfer", second_options={"causal_parent_event_ids": ("missing-parent",)})
        first = arbitrate("e17-transfer", self.market, (self.retail, self.quant), pair)
        next_pair = tuple(replace(item, peer_transfer_id="abort-transfer") for item in self.peer_pair("new-transfer"))
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e17-transfer-next", self.market, (self.retail, self.quant), next_pair, prior_episode_state=first.episode_state)

    def test_e17_verifier_rejects_coordinated_one_leg_peer_commit(self):
        result = arbitrate("e17-forge-one-leg", self.market, (self.retail, self.quant), self.peer_pair("forge-one-leg"))
        first, second = result.episode_state.event_dag
        forged_second = replace(
            second, label=ActionLabel.BLOCKED, accepted=False, outcome_status="INVALID_OR_BLOCKED",
            filled_quantity=0, rejected_reason_codes=("PEER_GROUP_ABORTED",),
            owner_post_state_hash=second.owner_pre_state_hash,
        )
        forged = rehashed_episode(result.episode_state, event_dag=(first, forged_second))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_PARTIAL_COMMIT", verification.reason_codes)

    def test_e17_verifier_rejects_deleted_peer_terminal_event(self):
        result = arbitrate("e17-forge-delete", self.market, (self.retail, self.quant), self.peer_pair("forge-delete"))
        forged = rehashed_episode(result.episode_state, event_dag=result.episode_state.event_dag[:1])
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_EVENT_MEMBERSHIP_MISMATCH", verification.reason_codes)

    def test_e17_verifier_rejects_duplicated_peer_terminal_event(self):
        result = arbitrate("e17-forge-duplicate", self.market, (self.retail, self.quant), self.peer_pair("forge-duplicate"))
        first, second = result.episode_state.event_dag
        forged = rehashed_episode(result.episode_state, event_dag=(first, second, second))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_EVENT_MEMBERSHIP_MISMATCH", verification.reason_codes)

    def test_e17_verifier_rejects_noncomplementary_peer_delta(self):
        result = arbitrate("e17-forge-delta", self.market, (self.retail, self.quant), self.peer_pair("forge-delta"))
        first, second = result.episode_state.event_dag
        forged = rehashed_episode(result.episode_state, event_dag=(first, replace(second, filled_quantity=1)))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_NONCOMPLEMENTARY_DELTA", verification.reason_codes)

    def test_e17_verifier_rejects_peer_counterparty_or_step_binding_change(self):
        result = arbitrate("e17-forge-binding", self.market, (self.retail, self.quant), self.peer_pair("forge-binding"))
        first, second = result.episode_state.event_dag
        forged_first = replace(first, counterparty_agent_id="forged-counterparty")
        forged_second = replace(second, step_index=second.step_index + 1)
        verification = verify_episode_ledger(rehashed_episode(result.episode_state, event_dag=(forged_first, forged_second)))
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_EVENT_ACTION_BINDING_MISMATCH", verification.reason_codes)

    def test_e17_verifier_rejects_nonreciprocal_peer_action_sides(self):
        result = arbitrate("e17-forge-sides", self.market, (self.retail, self.quant), self.peer_pair("forge-sides"))
        first_action, second_action = result.episode_state.action_registry
        forged_second_action = replace(second_action, order=replace(second_action.order, side=OrderSide.BUY))
        verification = verify_episode_ledger(rehashed_episode(
            result.episode_state, action_registry=(first_action, forged_second_action),
        ))
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_INVALID_RECIPROCAL_ACTIONS", verification.reason_codes)

    def test_e17_verifier_rejects_external_flow_attached_to_peer_event(self):
        result = arbitrate("e17-forge-flow", self.market, (self.retail, self.quant), self.peer_pair("forge-flow"))
        event = result.episode_state.event_dag[0]
        forged_flow = ExternalLiquidityFlowEvent("forged-flow", event.event_id, event.agent_id, 2, -2)
        forged = rehashed_episode(result.episode_state, external_liquidity_flows=(forged_flow,))
        verification = verify_episode_ledger(forged)
        self.assertFalse(verification.valid)
        self.assertIn("PEER_GROUP_EXTERNAL_FLOW_PRESENT", verification.reason_codes)

    def test_e17_peer_commit_preserves_prior_claim_then_release_lineage(self):
        claimed = arbitrate(
            "e17-lineage-claim", self.market, (self.retail, self.quant),
            (action("claim", "retail", 1, conflict="scarce"),),
        )
        peer = arbitrate(
            "e17-lineage-peer", self.market, (self.retail, self.quant), self.peer_pair("lineage-peer"),
            prior_episode_state=claimed.episode_state,
        )
        released = arbitrate(
            "e17-lineage-release", self.market, (self.retail, self.quant),
            (action("release", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.RELEASE),),
            prior_episode_state=peer.episode_state,
        )
        self.assertNotIn("scarce", released.shared_market_state.claimed_conflict_keys)
        self.assertTrue(verify_episode_ledger(released.episode_state).valid)

    def test_e17_existing_claim_is_preserved_when_peer_resource_attempt_aborts(self):
        claimed = arbitrate(
            "e17-existing-claim", self.market, (self.retail, self.quant),
            (action("claim", "retail", 1, conflict="scarce"),),
        )
        peer = arbitrate(
            "e17-existing-claim-peer", self.market, (self.retail, self.quant),
            self.peer_pair("existing-claim", second_options={"conflict": "scarce", "conflict_transition": ConflictTransition.RELEASE}),
            prior_episode_state=claimed.episode_state,
        )
        self.assertTrue(all(not event.accepted and event.filled_quantity == 0 for event in peer.events))
        self.assertTrue(all("UNSUPPORTED_PEER_CONFLICT_RESOURCE" in event.rejected_reason_codes for event in peer.events))
        self.assertTrue(verify_episode_ledger(peer.episode_state).valid)
        self.assertEqual(len(peer.episode_state.external_liquidity_flows), 1)
        self.assertEqual(peer.shared_market_state.claimed_conflict_keys, ("scarce",))

    def test_e17_peer_commit_preserves_prior_claim_then_expire_lineage(self):
        claimed = arbitrate(
            "e17-expire-lineage-claim", self.market, (self.retail, self.quant),
            (action("claim", "retail", 1, conflict="scarce"),),
        )
        peer = arbitrate(
            "e17-expire-lineage-peer", self.market, (self.retail, self.quant), self.peer_pair("expire-lineage-peer"),
            prior_episode_state=claimed.episode_state,
        )
        expired = arbitrate(
            "e17-expire-lineage-expire", self.market, (self.retail, self.quant),
            (action("expire", "retail", 1, conflict="scarce", conflict_transition=ConflictTransition.EXPIRE),),
            prior_episode_state=peer.episode_state,
        )
        self.assertNotIn("scarce", expired.shared_market_state.claimed_conflict_keys)
        self.assertTrue(verify_episode_ledger(expired.episode_state).valid)

    # E18: malformed peer declarations are deterministic, verifier-valid aborts.
    def test_e18_lone_peer_declaration_abort_is_composable(self):
        lone = action(
            "e18-lone", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-lone-transfer",
        )
        blocked = arbitrate("e18-lone", self.market, (self.retail, self.quant), (lone,))
        self.assert_declaration_abort(blocked, "PEER_TRANSFER_REQUIRES_EXACTLY_TWO_ACTIONS")
        external = arbitrate(
            "e18-lone-external", self.market, (self.retail, self.quant),
            (action("e18-after-lone-external", "retail", 1),),
            prior_episode_state=blocked.episode_state,
        )
        self.assertTrue(verify_episode_ledger(external.episode_state).valid)
        peer = arbitrate(
            "e18-lone-peer", self.market, (self.retail, self.quant), self.peer_pair("e18-after-lone-peer"),
            prior_episode_state=external.episode_state,
        )
        self.assertTrue(verify_episode_ledger(peer.episode_state).valid)
        self.assertTrue(total_system_accounted(peer.episode_state.initial_agents, peer))

    def test_e18_mismatched_quantity_declaration_abort_is_composable(self):
        buy, sell = self.peer_pair("e18-mismatch", qty=2)
        sell = replace(sell, order=replace(sell.order, quantity=1))
        blocked = arbitrate("e18-mismatch", self.market, (self.retail, self.quant), (buy, sell))
        self.assert_declaration_abort(blocked, "INVALID_PEER_TRANSFER_PAIR")
        continued = arbitrate(
            "e18-mismatch-next", self.market, (self.retail, self.quant), self.peer_pair("e18-mismatch-next"),
            prior_episode_state=blocked.episode_state,
        )
        self.assertTrue(verify_episode_ledger(continued.episode_state).valid)

    def test_e18_missing_transfer_id_is_verifier_valid_declaration_abort(self):
        missing = action(
            "e18-missing-transfer", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="placeholder",
        )
        result = arbitrate(
            "e18-missing-transfer", self.market, (self.retail, self.quant),
            (replace(missing, peer_transfer_id=None),),
        )
        self.assert_declaration_abort(result, "PEER_TRANSFER_REQUIRES_TRANSFER_ID")

    def test_e18_missing_counterparty_is_verifier_valid_declaration_abort(self):
        missing = action(
            "e18-missing-counterparty", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-missing-counterparty-transfer",
        )
        result = arbitrate(
            "e18-missing-counterparty", self.market, (self.retail, self.quant),
            (replace(missing, counterparty_agent_id=None),),
        )
        self.assert_declaration_abort(result, "PEER_TRANSFER_REQUIRES_COUNTERPARTY")

    def test_e18_three_member_peer_declaration_is_verifier_valid_abort(self):
        buy, sell = self.peer_pair("e18-three")
        third = action(
            "e18-third", "active", 3, side=OrderSide.BUY,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="retail", peer_transfer_id="e18-three",
        )
        result = arbitrate("e18-three", self.market, (self.retail, self.quant, self.active), (buy, sell, third))
        self.assert_declaration_abort(result, "PEER_TRANSFER_REQUIRES_EXACTLY_TWO_ACTIONS")

    def test_e18_same_side_peer_declaration_is_verifier_valid_abort(self):
        buy, sell = self.peer_pair("e18-same-side")
        sell = replace(sell, order=replace(sell.order, side=OrderSide.BUY))
        result = arbitrate("e18-same-side", self.market, (self.retail, self.quant), (buy, sell))
        self.assert_declaration_abort(result, "INVALID_PEER_TRANSFER_PAIR")

    def test_e18_nonreciprocal_counterparty_is_verifier_valid_abort(self):
        buy, sell = self.peer_pair("e18-nonreciprocal")
        sell = replace(sell, counterparty_agent_id="active")
        result = arbitrate("e18-nonreciprocal", self.market, (self.retail, self.quant, self.active), (buy, sell))
        self.assert_declaration_abort(result, "INVALID_PEER_TRANSFER_PAIR")

    def test_e18_nonadjacent_peer_declaration_is_verifier_valid_abort(self):
        buy, sell = self.peer_pair("e18-nonadjacent")
        sell = replace(sell, arrival_sequence=3)
        result = arbitrate("e18-nonadjacent", self.market, (self.retail, self.quant), (buy, sell))
        self.assert_declaration_abort(result, "INVALID_PEER_TRANSFER_PAIR")

    def test_e18_missing_order_peer_declaration_is_verifier_valid_abort(self):
        buy, sell = self.peer_pair("e18-missing-order")
        result = arbitrate("e18-missing-order", self.market, (self.retail, self.quant), (replace(buy, order=None), sell))
        self.assert_declaration_abort(result, "INVALID_PEER_TRANSFER_PAIR")

    def test_e18_declaration_abort_action_id_cannot_be_reused(self):
        lone = action(
            "e18-reuse-action", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-reuse-action-transfer",
        )
        first = arbitrate("e18-reuse-action", self.market, (self.retail, self.quant), (lone,))
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e18-reuse-action-next", self.market, (self.retail, self.quant), (lone,), prior_episode_state=first.episode_state)

    def test_e18_declaration_abort_invocation_and_order_cannot_be_reused(self):
        lone = action(
            "e18-reuse-identities", "retail", 1, invocation_id="e18-reused-invocation",
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-reuse-identities-transfer",
        )
        first = arbitrate("e18-reuse-identities", self.market, (self.retail, self.quant), (lone,))
        reused_invocation = replace(action("e18-new-invocation", "retail", 1), invocation_id=lone.effective_invocation_id)
        reused_order = replace(action("e18-new-order", "retail", 1), order=lone.order)
        for candidate in (reused_invocation, reused_order):
            with self.subTest(candidate=candidate.action_id):
                with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
                    arbitrate("e18-reuse-identities-next-" + candidate.action_id, self.market, (self.retail, self.quant), (candidate,), prior_episode_state=first.episode_state)

    def test_e18_declaration_abort_peer_transfer_id_cannot_be_reused(self):
        lone = action(
            "e18-reuse-transfer", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-reused-transfer-id",
        )
        first = arbitrate("e18-reuse-transfer", self.market, (self.retail, self.quant), (lone,))
        next_pair = tuple(replace(item, peer_transfer_id="e18-reused-transfer-id") for item in self.peer_pair("e18-new-transfer"))
        with self.assertRaisesRegex(ValueError, "PRIOR_ACTION_REGISTRY_COLLISION"):
            arbitrate("e18-reuse-transfer-next", self.market, (self.retail, self.quant), next_pair, prior_episode_state=first.episode_state)

    def test_e18_injected_member_and_event_into_lone_declaration_is_rejected(self):
        lone = action(
            "e18-forge-lone", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-forge-lone-transfer",
        )
        result = arbitrate("e18-forge-lone", self.market, (self.retail, self.quant), (lone,))
        injected = replace(
            self.peer_pair("e18-injected")[1], action_id="e18-injected-member",
            peer_transfer_id=lone.peer_transfer_id, scheduled_step_index=1,
        )
        injected_event = replace(
            result.episode_state.event_dag[0], event_id="e18-injected-event", ordinal=2,
            action_id=injected.action_id, agent_id=injected.agent_id,
            peer_transfer_id=injected.peer_transfer_id, counterparty_agent_id=injected.counterparty_agent_id,
        )
        forged = rehashed_episode(
            result.episode_state,
            action_registry=result.episode_state.action_registry + (injected,),
            event_dag=result.episode_state.event_dag + (injected_event,),
        )
        self.assertFalse(verify_episode_ledger(forged).valid)

    def test_e18_relabeling_declaration_abort_as_commit_is_rejected(self):
        lone = action(
            "e18-relabel", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-relabel-transfer",
        )
        result = arbitrate("e18-relabel", self.market, (self.retail, self.quant), (lone,))
        forged_event = replace(
            result.episode_state.event_dag[0], label=ActionLabel.FEASIBLE, accepted=True,
            outcome_status="FILLED", filled_quantity=1, rejected_reason_codes=(),
        )
        self.assertFalse(verify_episode_ledger(rehashed_episode(result.episode_state, event_dag=(forged_event,))).valid)

    def test_e18_public_arbitrate_peer_terminal_matrix_is_always_verifier_valid(self):
        lone = action(
            "e18-matrix-lone", "retail", 1,
            liquidity_mode=LiquidityMode.PEER_TO_PEER_TRANSFER,
            counterparty_agent_id="quant", peer_transfer_id="e18-matrix-lone-transfer",
        )
        mismatch_buy, mismatch_sell = self.peer_pair("e18-matrix-mismatch")
        mismatch_sell = replace(mismatch_sell, order=replace(mismatch_sell.order, quantity=1))
        missing_id = replace(lone, action_id="e18-matrix-missing-id", peer_transfer_id=None)
        valid_abort = self.peer_pair("e18-matrix-settlement-abort", second_options={"causal_parent_event_ids": ("missing-parent",)})
        cases = (
            ("valid-commit", self.peer_pair("e18-matrix-commit")),
            ("settlement-abort", valid_abort),
            ("lone-declaration", (lone,)),
            ("mismatch-declaration", (mismatch_buy, mismatch_sell)),
            ("missing-id-declaration", (missing_id,)),
        )
        for name, actions in cases:
            with self.subTest(name=name):
                result = arbitrate("e18-matrix-" + name, self.market, (self.retail, self.quant), actions)
                self.assertTrue(verify_episode_ledger(result.episode_state).valid)


if __name__ == "__main__":
    unittest.main(verbosity=2)
