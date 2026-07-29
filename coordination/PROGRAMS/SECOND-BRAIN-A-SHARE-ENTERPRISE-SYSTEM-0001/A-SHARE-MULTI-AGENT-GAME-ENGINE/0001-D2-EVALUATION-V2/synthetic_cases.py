"""Deterministic, synthetic-only E22 cases that exercise the public D2 SUT."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from d2_game_core import (
    ActionLabel,
    AgentInformationSet,
    AgentState,
    CandidateAction,
    ConflictTransition,
    HiddenTypePosterior,
    LiquidityMode,
    ParticipantArchetypeHypothesis,
    ParticipantSubtype,
    SYNTHETIC_CAPABILITY,
    arbitrate,
    run_one_step_counterfactual,
)
from synthetic_engine.fixtures import INVENTORY, market, order
from synthetic_engine.types import InventoryState, OrderSide, SyntheticLot

from evaluation_v2_contract import (
    CounterfactualSpec,
    CrossFamilySpec,
    EpisodeSpec,
    InvariantSpec,
    NegativeCaseSpec,
    ScenarioSpec,
)


SCENARIO_FAMILIES = (
    "external_buy", "external_sell", "conflict", "peer", "incomplete",
    "claim_release", "causal", "blocked",
)
PREDICATES = (
    "HAS_EPISODE", "NONEMPTY_EVENTS", "UNIQUE_EVENT_IDS", "ACTION_EVENT_BINDING",
    "INDEPENDENT_ACCOUNTING",
)


def posterior(subtype: ParticipantSubtype = ParticipantSubtype.RETAIL_LIQUIDITY_TAKER) -> HiddenTypePosterior:
    return HiddenTypePosterior((ParticipantArchetypeHypothesis(
        subtype, 1.0, ("synthetic:evidence",), ("synthetic:counter",), "synthetic alternative",
    ),))


def make_agent(name: str, *, subtype: ParticipantSubtype = ParticipantSubtype.RETAIL_LIQUIDITY_TAKER,
               inventory: InventoryState = INVENTORY, unknowns: tuple[str, ...] = ()) -> AgentState:
    return AgentState(
        name, posterior(subtype),
        AgentInformationSet(100, ("synthetic:observable",), unknowns, (), SYNTHETIC_CAPABILITY), inventory,
    )


def seasoned_inventory(name: str, quantity: int = 9) -> InventoryState:
    return InventoryState((SyntheticLot(name + "-seasoned", "2026-07-25", quantity),), settled_trade_date="2026-07-26")


def make_action(name: str, agent_id: str, sequence: int, *, side: OrderSide = OrderSide.BUY,
                quantity: int = 1, label: ActionLabel = ActionLabel.FEASIBLE,
                conflict_key: str | None = None, transition: ConflictTransition = ConflictTransition.CLAIM,
                liquidity: LiquidityMode = LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY,
                counterparty: str | None = None, transfer_id: str | None = None,
                requires_complete_information: bool = False, parents: tuple[str, ...] = (),
                invocation_id: str | None = None, order_id: str | None = None) -> CandidateAction:
    return CandidateAction(
        name, agent_id, label, order(order_id or name, side=side, qty=quantity),
        ("assumption:" + name,), ("synthetic:evidence",), conflict_key,
        requires_complete_information=requires_complete_information,
        causal_parent_event_ids=parents, arrival_sequence=sequence,
        invocation_id=invocation_id, conflict_transition=transition,
        liquidity_mode=liquidity, counterparty_agent_id=counterparty,
        peer_transfer_id=transfer_id,
    )


def _base_agents(prefix: str) -> tuple[AgentState, AgentState]:
    return (
        make_agent(prefix + "-retail"),
        make_agent(prefix + "-quant", subtype=ParticipantSubtype.SYSTEMATIC_REBALANCER,
                   inventory=seasoned_inventory(prefix + "-quant")),
    )


def peer_pair(prefix: str, quantity: int = 2) -> tuple[AgentState, AgentState, CandidateAction, CandidateAction]:
    retail, quant = _base_agents(prefix)
    buy = make_action(prefix + "-buy", retail.agent_id, 1, quantity=quantity,
                      liquidity=LiquidityMode.PEER_TO_PEER_TRANSFER, counterparty=quant.agent_id,
                      transfer_id=prefix + "-transfer")
    sell = make_action(prefix + "-sell", quant.agent_id, 2, side=OrderSide.SELL, quantity=quantity,
                       liquidity=LiquidityMode.PEER_TO_PEER_TRANSFER, counterparty=retail.agent_id,
                       transfer_id=prefix + "-transfer")
    return retail, quant, buy, sell


def execute_scenario(spec: ScenarioSpec):
    prefix = spec.scenario_id.lower()
    retail, quant = _base_agents(prefix)
    if spec.family == "external_buy":
        return arbitrate(prefix, market(), (retail, quant), (make_action(prefix + "-buy", retail.agent_id, 1),))
    if spec.family == "external_sell":
        return arbitrate(prefix, market(), (retail, quant), (
            make_action(prefix + "-sell", quant.agent_id, 1, side=OrderSide.SELL),
        ))
    if spec.family == "conflict":
        return arbitrate(prefix, market(), (retail, quant), (
            make_action(prefix + "-first", retail.agent_id, 1, conflict_key=prefix + "-resource"),
            make_action(prefix + "-second", quant.agent_id, 2, conflict_key=prefix + "-resource"),
        ))
    if spec.family == "peer":
        retail, quant, buy, sell = peer_pair(prefix)
        return arbitrate(prefix, market(), (retail, quant), (buy, sell))
    if spec.family == "incomplete":
        unknown = make_agent(retail.agent_id, unknowns=("synthetic:unknown",))
        return arbitrate(prefix, market(), (unknown, quant), (
            make_action(prefix + "-wait", unknown.agent_id, 1, requires_complete_information=True),
        ))
    if spec.family == "claim_release":
        first = arbitrate(prefix + ":one", market(), (retail, quant), (
            make_action(prefix + "-claim", retail.agent_id, 1, conflict_key=prefix + "-resource"),
        ))
        release = make_action(prefix + "-release", retail.agent_id, 1, conflict_key=prefix + "-resource",
                              transition=ConflictTransition.RELEASE)
        return arbitrate(prefix + ":two", market(), first.episode_state.current_agents, (release,),
                         prior_episode_state=first.episode_state)
    if spec.family == "causal":
        first = arbitrate(prefix + ":one", market(), (retail, quant), (
            make_action(prefix + "-first", retail.agent_id, 1),
        ))
        parent = first.events[-1].event_id
        second = make_action(prefix + "-second", quant.agent_id, 1, parents=(parent,))
        return arbitrate(prefix + ":two", market(), first.episode_state.current_agents, (second,),
                         prior_episode_state=first.episode_state)
    if spec.family == "blocked":
        return arbitrate(prefix, market(), (retail, quant), (
            make_action(prefix + "-blocked", retail.agent_id, 1, label=ActionLabel.BLOCKED),
        ))
    raise ValueError("UNKNOWN_SCENARIO_FAMILY:" + spec.family)


def scenario_catalog() -> tuple[ScenarioSpec, ...]:
    return tuple(
        ScenarioSpec(f"SCN-{index:03d}", SCENARIO_FAMILIES[(index - 1) % len(SCENARIO_FAMILIES)],
                     (index - 1) // len(SCENARIO_FAMILIES) + 1, "REQ-E22-SCN", "TEST-CATALOG-SCENARIOS")
        for index in range(1, 73)
    )


def invariant_catalog() -> tuple[InvariantSpec, ...]:
    scenarios = scenario_catalog()
    return tuple(
        InvariantSpec(f"INV-{index:03d}", "REQ-E22-INV", scenarios[(index - 1) % len(scenarios)].scenario_id,
                      PREDICATES[(index - 1) % len(PREDICATES)], "ORACLE-" + PREDICATES[(index - 1) % len(PREDICATES)],
                      "TEST-CATALOG-INVARIANTS")
        for index in range(1, 81)
    )


def negative_catalog() -> tuple[NegativeCaseSpec, ...]:
    families = (
        "duplicate_arrival", "duplicate_action", "duplicate_invocation", "duplicate_order",
        "prior_replay", "invalid_label", "agent_subclass", "action_subclass",
    )
    return tuple(
        NegativeCaseSpec(f"NEG-{index:03d}", families[(index - 1) % len(families)], index,
                         "ValueError", "TEST-CATALOG-NEGATIVES")
        for index in range(1, 38)
    )


def execute_negative(spec: NegativeCaseSpec) -> None:
    prefix = spec.negative_id.lower()
    retail, quant = _base_agents(prefix)
    if spec.family == "duplicate_arrival":
        actions = (make_action(prefix + "-a", retail.agent_id, 1), make_action(prefix + "-b", quant.agent_id, 1))
        arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "duplicate_action":
        action = make_action(prefix + "-same", retail.agent_id, 1)
        arbitrate(prefix, market(), (retail, quant), (action, action))
        return
    if spec.family == "duplicate_invocation":
        actions = (
            make_action(prefix + "-a", retail.agent_id, 1, invocation_id=prefix + "-invoke"),
            make_action(prefix + "-b", quant.agent_id, 2, invocation_id=prefix + "-invoke"),
        )
        arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "duplicate_order":
        actions = (
            make_action(prefix + "-a", retail.agent_id, 1, order_id=prefix + "-order"),
            make_action(prefix + "-b", quant.agent_id, 2, order_id=prefix + "-order"),
        )
        arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "prior_replay":
        first = arbitrate(prefix + ":one", market(), (retail, quant), (make_action(prefix + "-replay", retail.agent_id, 1),))
        arbitrate(prefix + ":two", market(), first.episode_state.current_agents,
                  (make_action(prefix + "-replay", retail.agent_id, 1),), prior_episode_state=first.episode_state)
        return
    if spec.family == "invalid_label":
        invalid = replace(make_action(prefix + "-bad", retail.agent_id, 1), label="feasible")
        arbitrate(prefix, market(), (retail, quant), (invalid,))
        return
    if spec.family == "agent_subclass":
        class AgentAlias(AgentState):
            pass
        alias = AgentAlias(retail.agent_id, retail.posterior, retail.information, retail.inventory)
        arbitrate(prefix, market(), (alias, quant), (make_action(prefix + "-bad", retail.agent_id, 1),))
        return
    if spec.family == "action_subclass":
        class ActionAlias(CandidateAction):
            pass
        source = make_action(prefix + "-bad", retail.agent_id, 1)
        alias = ActionAlias(**source.__dict__)
        arbitrate(prefix, market(), (retail, quant), (alias,))
        return
    raise ValueError("UNKNOWN_NEGATIVE_FAMILY:" + spec.family)


def episode_catalog() -> tuple[EpisodeSpec, ...]:
    return tuple(EpisodeSpec(f"EP-{index:03d}", index, "REQ-E22-EPISODE", "TEST-CATALOG-EPISODES") for index in range(1, 25))


def execute_episode(spec: EpisodeSpec):
    prefix = spec.episode_id.lower()
    retail, quant = _base_agents(prefix)
    one = arbitrate(prefix + ":one", market(), (retail, quant), (make_action(prefix + "-one", retail.agent_id, 1),))
    two = arbitrate(prefix + ":two", market(), one.episode_state.current_agents,
                    (make_action(prefix + "-two", quant.agent_id, 1, parents=(one.events[-1].event_id,)),),
                    prior_episode_state=one.episode_state)
    return one, two


def counterfactual_catalog() -> tuple[CounterfactualSpec, ...]:
    return tuple(CounterfactualSpec(f"CF-{index:03d}", index, "assumption:cf-%03d" % index, "TEST-CATALOG-COUNTERFACTUALS") for index in range(1, 37))


def execute_counterfactual(spec: CounterfactualSpec):
    retail, quant = _base_agents(spec.pair_id.lower())
    action = replace(make_action(spec.pair_id.lower() + "-action", retail.agent_id, 1), assumption_ids=(spec.changed_assumption_id,))
    return run_one_step_counterfactual(spec.pair_id, market(), (retail, quant), (action,), spec.changed_assumption_id)


def cross_family_catalog(mutant_ids: tuple[str, ...], property_ids: tuple[str, ...]) -> tuple[CrossFamilySpec, ...]:
    return tuple(
        CrossFamilySpec(f"XFM-{index:03d}", mutant_ids[(index - 1) % len(mutant_ids)],
                        property_ids[(index - 1) % len(property_ids)], "TEST-CATALOG-CROSS-FAMILY")
        for index in range(1, 25)
    )
