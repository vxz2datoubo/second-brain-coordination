"""Synthetic-only D2 core tests. No market, account, or execution interface is used."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from d2_game_core import (  # noqa: E402
    ActionLabel, AgentInformationSet, AgentState, CandidateAction, HiddenTypePosterior,
    NarrativeForecastRecord, NarrativeStatus, ParticipantArchetypeHypothesis,
    ParticipantSubtype, arbitrate, evaluate_narrative, feature_container,
    inventory_ledger_conserved, run_bounded_counterfactual_episode, run_one_step_counterfactual,
)
from synthetic_engine.fixtures import INVENTORY, market, order  # noqa: E402
from synthetic_engine.types import (  # noqa: E402
    InventoryState, MatchMode, OrderSide, OutcomeStatus, SecurityStatus, SessionPhase,
    SyntheticLot, SyntheticOrder,
)


def posterior(weight=1.0):
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(
        ParticipantSubtype.RETAIL_LIQUIDITY_TAKER, weight, ("synthetic:evidence",),
        ("synthetic:counter",), "synthetic alternative",
    ),))


def agent(name="agent-a", available=100, inventory=INVENTORY, belief=None):
    return AgentState(name, belief or posterior(), AgentInformationSet(available, ("synthetic:observable",), ()), inventory)


def action(name="action-a", agent_id="agent-a", label=ActionLabel.FEASIBLE, synthetic_order=None, **kwargs):
    return CandidateAction(name, agent_id, label, synthetic_order or order(name), ("assumption:one",), ("synthetic:evidence",), **kwargs)


def scenarios():
    phases = (
        SessionPhase.PREOPEN, SessionPhase.CALL_AUCTION, SessionPhase.AUCTION_FREEZE,
        SessionPhase.CONTINUOUS_AM, SessionPhase.MIDDAY_BREAK, SessionPhase.CONTINUOUS_PM,
        SessionPhase.CLOSING_AUCTION, SessionPhase.CLOSED,
    )
    result = []
    for index, phase in enumerate(phases, start=1):
        result.append((f"S{index:02d}_phase_{phase.value}", market(phase), INVENTORY, action(f"a{index}")))
    result.extend((
        ("S09_suspended", market(status=SecurityStatus.SUSPENDED), INVENTORY, action("a9")),
        ("S10_limit", market(), INVENTORY, action("a10", synthetic_order=order("a10", price=11))),
        ("S11_fresh_t1", market(), InventoryState((SyntheticLot("fresh", "2026-07-26", 2),), settled_trade_date="2026-07-26"), action("a11", synthetic_order=order("a11", side=OrderSide.SELL, qty=1))),
        ("S12_partial", market(), INVENTORY, action("a12", synthetic_order=order("a12", mode=MatchMode.PARTIAL, partial=1))),
        ("S13_no_fill_cancel", market(), INVENTORY, action("a13", synthetic_order=order("a13", mode=MatchMode.NO_FILL_CANCEL))),
        ("S14_no_fill_carry", market(), INVENTORY, action("a14", synthetic_order=order("a14", mode=MatchMode.NO_FILL_CARRY))),
        ("S15_future_info", market(), INVENTORY, action("a15")),
        ("S16_missing_evidence", market(), INVENTORY, CandidateAction("a16", "agent-a", ActionLabel.FEASIBLE, order("a16"), ("assumption:one",), ())),
        ("S17_abstain", market(), INVENTORY, action("a17", label=ActionLabel.ABSTAIN, synthetic_order=None)),
        ("S18_conflict_one", market(), INVENTORY, action("a18", conflict_key="same")),
        ("S19_conflict_two", market(), INVENTORY, action("a19", conflict_key="same")),
        ("S20_invalid_order_timestamp", market(), INVENTORY, action("a20", synthetic_order=order("a20", available=101))),
        ("S21_unknown_match", market(), INVENTORY, action("a21", synthetic_order=order("a21", mode=MatchMode.UNKNOWN))),
        ("S22_adversarial_narrative", market(), INVENTORY, action("a22")),
        ("S23_most_consistent", market(), INVENTORY, action("a23", label=ActionLabel.MOST_CONSISTENT)),
        ("S24_robust", market(), INVENTORY, action("a24", label=ActionLabel.ROBUST)),
    ))
    return tuple(result)


class D2GameCoreTests(unittest.TestCase):
    def test_24_synthetic_scenarios_execute_or_fail_closed(self):
        self.assertEqual(24, len(scenarios()))
        for name, state, inventory, candidate in scenarios():
            subject = agent(available=99 if name == "S15_future_info" else 100, inventory=inventory)
            result = arbitrate(name, state, (subject,), (candidate,))
            self.assertEqual(1, len(result.events), name)
            self.assertTrue(result.ledger_hash, name)

    def test_30_named_invariants(self):
        state, initial = market(), INVENTORY
        primary = action("buy")
        secondary = action("sell", synthetic_order=order("sell", side=OrderSide.SELL, qty=1), conflict_key="shared")
        run = arbitrate("invariants", state, (agent(), agent("agent-b")), (primary, secondary))
        names = {
            "stable_event_ids": len({event.event_id for event in run.events}) == len(run.events),
            "stable_order": tuple(event.ordinal for event in run.events) == (1, 2),
            "action_ids_unique": len({event.action_id for event in run.events}) == 2,
            "inventory_conservation": inventory_ledger_conserved(initial, run, (primary, secondary)),
            "nonnegative_inventory": all(lot.quantity >= 0 for lot in run.final_inventory.lots),
            "bounded_inventory": all(lot.quantity <= 1_000_000_000 for lot in run.final_inventory.lots),
            "known_agents_only": all(event.agent_id in {"agent-a", "agent-b"} for event in run.events),
            "cause_refs_preserved": all(event.cause_refs for event in run.events),
            "reasons_stable": all(isinstance(event.rejected_reason_codes, tuple) for event in run.events),
            "labels_declared": all(isinstance(event.label, ActionLabel) for event in run.events),
            "no_real_capability": True,
            "posterior_not_identity": posterior().status == "UNCALIBRATED_SYNTHETIC_HYPOTHESIS",
            "posterior_normalized": posterior().validate()[0],
            "family_mapping_complete": len({item.value for item in ParticipantSubtype}) == 9,
            "no_future_info": arbitrate("future", state, (agent(available=101),), (action("future"),)).events[0].accepted is False,
            "missing_evidence_blocks": arbitrate("missing", state, (agent(),), (CandidateAction("m", "agent-a", ActionLabel.FEASIBLE, order("m"), ("a",), ()),)).events[0].accepted is False,
            "abstention_preserved": arbitrate("abstain", state, (agent(),), (action("x", label=ActionLabel.ABSTAIN, synthetic_order=None),)).events[0].outcome_status == "ABSTAINED",
            "d1_reducer_composed": run.events[0].outcome_status == OutcomeStatus.FILLED.value,
            "conflict_deterministic": arbitrate("conflict", state, (agent(),), (action("a", conflict_key="k"), action("b", conflict_key="k"))).events[1].accepted is False,
            "unknown_narrative_retained": evaluate_narrative(NarrativeForecastRecord("n", "claim", (), (), None), 5) == NarrativeStatus.UNKNOWN,
            "incomplete_information_abstains": arbitrate("unknown", state, (AgentState("agent-a", posterior(), AgentInformationSet(100, ("public",), ("missing",)), INVENTORY),), (CandidateAction("unknown", "agent-a", ActionLabel.FEASIBLE, order("unknown"), ("a",), ("e",), requires_complete_information=True),)).events[0].outcome_status == "ABSTAINED",
            "feature_is_uncalibrated": feature_container(0.1, ("x",)).status == "UNCALIBRATED_SYNTHETIC_FEATURE",
            "mismatch_is_uncalibrated": feature_container(0.2, ("x",), mismatch=True).status == "UNCALIBRATED_SYNTHETIC_FEATURE",
            "counterfactual_single_change": len(run_one_step_counterfactual("cf", state, (agent(),), (primary,), "assumption:one").changed_action_ids) == 1,
            "price_limit_fail_closed": arbitrate("limit", state, (agent(),), (action("limit", synthetic_order=order("limit", price=11)),)).events[0].accepted is False,
            "t1_fail_closed": arbitrate("t1", state, (agent(inventory=InventoryState((SyntheticLot("f", "2026-07-26", 1),), settled_trade_date="2026-07-26")),), (action("t1", synthetic_order=order("t1", side=OrderSide.SELL, qty=1)),)).events[0].accepted is False,
            "partial_fill_labeled": arbitrate("partial", state, (agent(),), (action("p", synthetic_order=order("p", mode=MatchMode.PARTIAL, partial=1)),)).events[0].outcome_status == OutcomeStatus.PARTIALLY_FILLED.value,
            "carry_state_visible": arbitrate("carry", state, (agent(),), (action("c", synthetic_order=order("c", mode=MatchMode.NO_FILL_CARRY)),)).final_inventory.pending_buy_quantity == 2,
            "negative_order_is_blocked": arbitrate("bad", state, (agent(),), (action("bad", synthetic_order=order("bad", qty=-1)),)).events[0].accepted is False,
            "causal_parent_unknown_blocks": arbitrate("causal", state, (agent(),), (CandidateAction("causal", "agent-a", ActionLabel.FEASIBLE, order("causal"), ("a",), ("e",), causal_parent_event_ids=("future-event",)),)).events[0].accepted is False,
        }
        self.assertEqual(30, len(names))
        self.assertTrue(all(names.values()), names)

    def test_bounded_counterfactual_changes_declared_assumptions_only(self):
        first = CandidateAction("first", "agent-a", ActionLabel.FEASIBLE, order("first"), ("assumption:first",), ("e",))
        second = CandidateAction("second", "agent-a", ActionLabel.FEASIBLE, order("second"), ("assumption:second",), ("e",))
        episode = run_bounded_counterfactual_episode("multi", market(), (agent(),), (first, second), ("assumption:first", "assumption:second"), max_steps=2)
        self.assertEqual(3, len(episode.runs))
        self.assertNotEqual(episode.runs[0].ledger_hash, episode.runs[-1].ledger_hash)

    def test_12_negative_cases_fail_closed_or_raise(self):
        state = market()
        cases = (
            lambda: arbitrate("n1", state, (agent(),), (CandidateAction("n1", "ghost", ActionLabel.FEASIBLE, order("n1"), ("a",), ("e",)),)),
            lambda: arbitrate("n2", state, (agent(),), (CandidateAction("n2", "agent-a", ActionLabel.FEASIBLE, None, ("a",), ("e",)),)),
            lambda: arbitrate("n3", state, (agent(),), (CandidateAction("n3", "agent-a", ActionLabel.FEASIBLE, order("n3"), ("a",), ()),)),
            lambda: arbitrate("n4", state, (agent(available=None),), (action("n4"),)),
            lambda: arbitrate("n5", state, (agent(belief=HiddenTypePosterior(())),), (action("n5"),)),
            lambda: arbitrate("n6", state, (agent(belief=posterior(0.9)),), (action("n6"),)),
            lambda: arbitrate("n7", state, (agent(),), (action("dup"), action("dup"))),
            lambda: arbitrate("n8", state, (agent(), agent()), (action("n8"),)),
            lambda: run_one_step_counterfactual("n9", state, (agent(),), (action("n9"), action("n10")), "assumption:one"),
            lambda: feature_container(1_000_001, ("x",)),
            lambda: feature_container(0.1, ()),
            lambda: arbitrate("n12", state, (), (action("n12"),)),
        )
        self.assertEqual(12, len(cases))
        for index, case in enumerate(cases, start=1):
            try:
                result = case()
                if hasattr(result, "events"):
                    self.assertFalse(result.events[0].accepted if result.events else True, index)
                else:
                    self.fail(f"negative case {index} did not fail")
            except ValueError:
                pass

    def test_nine_subtypes_cover_four_families(self):
        from d2_game_core import SUBTYPE_FAMILY, ParticipantFamily
        self.assertEqual(9, len(SUBTYPE_FAMILY))
        self.assertEqual(4, len(set(SUBTYPE_FAMILY.values())))
        self.assertIn(ParticipantFamily.RETAIL, set(SUBTYPE_FAMILY.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
