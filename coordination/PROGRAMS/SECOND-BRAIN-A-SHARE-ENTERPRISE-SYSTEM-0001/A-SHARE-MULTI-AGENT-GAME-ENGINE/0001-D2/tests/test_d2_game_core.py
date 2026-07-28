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
    SharedMarketState, _sha, _system_hash,
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
