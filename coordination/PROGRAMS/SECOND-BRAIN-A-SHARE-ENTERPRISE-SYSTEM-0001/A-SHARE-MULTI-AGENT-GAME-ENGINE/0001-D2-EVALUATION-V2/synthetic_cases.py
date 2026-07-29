"""Distinct, synthetic-only fixtures shared by baseline and shadow D2 SUTs."""
from __future__ import annotations

from dataclasses import replace
from types import ModuleType

import d2_game_core as BASE_SUT
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
    "INDEPENDENT_ACCOUNTING", "BOUNDARY_ORDER", "NO_UNEXPLAINED_FLOW",
    "TERMINAL_ACTION_COVERAGE", "STEP_MONOTONIC", "PORTFOLIO_DELTA_EXPLAINED",
)


def _pairs(values: dict[str, object]) -> tuple[tuple[str, object], ...]:
    return tuple((key, values[key]) for key in sorted(values))


def posterior(sut: ModuleType, subtype=None):
    subtype = subtype or sut.ParticipantSubtype.RETAIL_LIQUIDITY_TAKER
    return sut.HiddenTypePosterior((sut.ParticipantArchetypeHypothesis(
        subtype, 1.0, ("synthetic:evidence",), ("synthetic:counter",), "synthetic alternative",
    ),))


def make_agent(
    name: str,
    *,
    sut: ModuleType = BASE_SUT,
    subtype=None,
    inventory: InventoryState = INVENTORY,
    unknowns: tuple[str, ...] = (),
):
    return sut.AgentState(
        name,
        posterior(sut, subtype),
        sut.AgentInformationSet(100, ("synthetic:observable",), unknowns, (), sut.SYNTHETIC_CAPABILITY),
        inventory,
    )


def seasoned_inventory(name: str, quantity: int = 9) -> InventoryState:
    return InventoryState((SyntheticLot(name + "-seasoned", "2026-07-25", quantity),), settled_trade_date="2026-07-26")


def make_action(
    name: str,
    agent_id: str,
    sequence: int,
    *,
    sut: ModuleType = BASE_SUT,
    side: OrderSide = OrderSide.BUY,
    quantity: int = 1,
    label=None,
    conflict_key: str | None = None,
    transition=None,
    liquidity=None,
    counterparty: str | None = None,
    transfer_id: str | None = None,
    requires_complete_information: bool = False,
    parents: tuple[str, ...] = (),
    invocation_id: str | None = None,
    order_id: str | None = None,
):
    label = label or sut.ActionLabel.FEASIBLE
    transition = transition or sut.ConflictTransition.CLAIM
    liquidity = liquidity or sut.LiquidityMode.EXTERNAL_SYNTHETIC_LIQUIDITY
    return sut.CandidateAction(
        name, agent_id, label, order(order_id or name, side=side, qty=quantity),
        ("assumption:" + name,), ("synthetic:evidence",), conflict_key,
        requires_complete_information=requires_complete_information,
        causal_parent_event_ids=parents, arrival_sequence=sequence,
        invocation_id=invocation_id, conflict_transition=transition,
        liquidity_mode=liquidity, counterparty_agent_id=counterparty,
        peer_transfer_id=transfer_id,
    )


def _base_agents(prefix: str, *, sut: ModuleType = BASE_SUT):
    return (
        make_agent(prefix + "-retail", sut=sut),
        make_agent(
            prefix + "-quant", sut=sut,
            subtype=sut.ParticipantSubtype.SYSTEMATIC_REBALANCER,
            inventory=seasoned_inventory(prefix + "-quant"),
        ),
    )


def peer_pair(prefix: str, quantity: int = 2, *, sut: ModuleType = BASE_SUT):
    retail, quant = _base_agents(prefix, sut=sut)
    buy = make_action(
        prefix + "-buy", retail.agent_id, 1, sut=sut, quantity=quantity,
        liquidity=sut.LiquidityMode.PEER_TO_PEER_TRANSFER, counterparty=quant.agent_id,
        transfer_id=prefix + "-transfer",
    )
    sell = make_action(
        prefix + "-sell", quant.agent_id, 2, sut=sut, side=OrderSide.SELL, quantity=quantity,
        liquidity=sut.LiquidityMode.PEER_TO_PEER_TRANSFER, counterparty=retail.agent_id,
        transfer_id=prefix + "-transfer",
    )
    return retail, quant, buy, sell


def _scenario_dimensions(family: str, variant: int) -> dict[str, object]:
    return {
        "family": family,
        "quantity": variant,
        "requires_complete_information": family == "incomplete",
        "conflict_transition": "release" if family == "claim_release" else "claim",
        "peer_transfer": family == "peer",
        "causal_continuation": family == "causal",
        "blocked_context": (variant % 3) if family == "blocked" else 0,
    }


def execute_scenario(spec: ScenarioSpec, *, sut: ModuleType = BASE_SUT):
    """Run the same declared fixture against baseline or a source-derived SUT."""
    prefix = spec.scenario_id.lower()
    quantity = spec.variant
    retail, quant = _base_agents(prefix, sut=sut)
    if spec.family == "external_buy":
        return sut.arbitrate(prefix, market(), (retail, quant), (make_action(prefix + "-buy", retail.agent_id, 1, sut=sut, quantity=quantity),))
    if spec.family == "external_sell":
        return sut.arbitrate(prefix, market(), (retail, quant), (
            make_action(prefix + "-sell", quant.agent_id, 1, sut=sut, side=OrderSide.SELL, quantity=quantity),
        ))
    if spec.family == "conflict":
        return sut.arbitrate(prefix, market(), (retail, quant), (
            make_action(prefix + "-first", retail.agent_id, 1, sut=sut, quantity=quantity, conflict_key=prefix + "-resource"),
            make_action(prefix + "-second", quant.agent_id, 2, sut=sut, quantity=quantity, conflict_key=prefix + "-resource"),
        ))
    if spec.family == "peer":
        retail, quant, buy, sell = peer_pair(prefix, quantity, sut=sut)
        return sut.arbitrate(prefix, market(), (retail, quant), (buy, sell))
    if spec.family == "incomplete":
        unknown = make_agent(retail.agent_id, sut=sut, unknowns=("synthetic:unknown:" + str(quantity),))
        return sut.arbitrate(prefix, market(), (unknown, quant), (
            make_action(prefix + "-wait", unknown.agent_id, 1, sut=sut, quantity=quantity, requires_complete_information=True),
        ))
    if spec.family == "claim_release":
        first = sut.arbitrate(prefix + ":one", market(), (retail, quant), (
            make_action(prefix + "-claim", retail.agent_id, 1, sut=sut, quantity=quantity, conflict_key=prefix + "-resource"),
        ))
        release = make_action(
            prefix + "-release", retail.agent_id, 1, sut=sut, quantity=quantity, conflict_key=prefix + "-resource",
            transition=sut.ConflictTransition.RELEASE,
        )
        return sut.arbitrate(prefix + ":two", market(), first.episode_state.current_agents, (release,), prior_episode_state=first.episode_state)
    if spec.family == "causal":
        first = sut.arbitrate(prefix + ":one", market(), (retail, quant), (
            make_action(prefix + "-first", retail.agent_id, 1, sut=sut, quantity=quantity),
        ))
        parent = first.events[-1].event_id
        second = make_action(prefix + "-second", quant.agent_id, 1, sut=sut, quantity=quantity, parents=(parent,))
        return sut.arbitrate(prefix + ":two", market(), first.episode_state.current_agents, (second,), prior_episode_state=first.episode_state)
    if spec.family == "blocked":
        return sut.arbitrate(prefix, market(), (retail, quant), (
            make_action(
                prefix + "-blocked", retail.agent_id, 1, sut=sut, quantity=quantity,
                label=sut.ActionLabel.BLOCKED, conflict_key=(prefix + "-context" if quantity % 2 else None),
                requires_complete_information=bool(quantity % 3),
            ),
        ))
    raise ValueError("UNKNOWN_SCENARIO_FAMILY:" + spec.family)


def scenario_catalog() -> tuple[ScenarioSpec, ...]:
    specs: list[ScenarioSpec] = []
    index = 1
    for family in SCENARIO_FAMILIES:
        for variant in range(1, 10):
            dimensions = _scenario_dimensions(family, variant)
            specs.append(ScenarioSpec(
                f"SCN-{index:03d}", family, variant, _pairs(dimensions),
                _pairs({"independent_oracle": "valid", "family": family, "quantity": variant}),
                "REQ-E23-SCENARIO", "TEST-E23-SCENARIOS",
            ))
            index += 1
    return tuple(specs)


def invariant_catalog() -> tuple[InvariantSpec, ...]:
    scenarios = scenario_catalog()
    specs: list[InvariantSpec] = []
    for index in range(80):
        fixture = scenarios[index % len(scenarios)]
        predicate = PREDICATES[(index * 3) % len(PREDICATES)]
        specs.append(InvariantSpec(
            f"INV-{index + 1:03d}", fixture.scenario_id, predicate,
            _pairs({"fixture_input_signature": fixture.signatures[0], "predicate": predicate, "slot": index // len(scenarios)}),
            _pairs({"predicate": predicate, "expected": True}), "REQ-E23-INVARIANT",
            "ORACLE-" + predicate, "TEST-E23-INVARIANTS",
        ))
    return tuple(specs)


_NEGATIVE_LAYOUT = (
    ("duplicate_arrival", 5), ("duplicate_action", 5), ("duplicate_invocation", 5),
    ("duplicate_order", 5), ("prior_replay", 4), ("invalid_label", 3),
    ("agent_subclass", 3), ("action_subclass", 3), ("string_enum", 2), ("bool_arrival", 2),
)


def negative_catalog() -> tuple[NegativeCaseSpec, ...]:
    specs: list[NegativeCaseSpec] = []
    index = 1
    for family, count in _NEGATIVE_LAYOUT:
        for variant in range(1, count + 1):
            specs.append(NegativeCaseSpec(
                f"NEG-{index:03d}", family, variant,
                _pairs({"fault_family": family, "variant": variant, "carrier": "public_arbitrate"}),
                _pairs({"raises": "ValueError", "fail_closed": True}), "ValueError", "TEST-E23-NEGATIVES",
            ))
            index += 1
    return tuple(specs)


def execute_negative(spec: NegativeCaseSpec, *, sut: ModuleType = BASE_SUT) -> None:
    prefix = spec.negative_id.lower()
    retail, quant = _base_agents(prefix, sut=sut)
    variant = spec.variant
    if spec.family == "duplicate_arrival":
        actions = (
            make_action(prefix + "-a", retail.agent_id, variant, sut=sut),
            make_action(prefix + "-b", quant.agent_id, variant, sut=sut),
        )
        sut.arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "duplicate_action":
        action = make_action(prefix + "-same", retail.agent_id, variant, sut=sut)
        sut.arbitrate(prefix, market(), (retail, quant), (action, action))
        return
    if spec.family == "duplicate_invocation":
        actions = (
            make_action(prefix + "-a", retail.agent_id, 1, sut=sut, invocation_id=prefix + "-invoke"),
            make_action(prefix + "-b", quant.agent_id, 2, sut=sut, invocation_id=prefix + "-invoke"),
        )
        sut.arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "duplicate_order":
        actions = (
            make_action(prefix + "-a", retail.agent_id, 1, sut=sut, order_id=prefix + "-order"),
            make_action(prefix + "-b", quant.agent_id, 2, sut=sut, order_id=prefix + "-order"),
        )
        sut.arbitrate(prefix, market(), (retail, quant), actions)
        return
    if spec.family == "prior_replay":
        first = sut.arbitrate(prefix + ":one", market(), (retail, quant), (make_action(prefix + "-replay", retail.agent_id, 1, sut=sut),))
        sut.arbitrate(prefix + ":two", market(), first.episode_state.current_agents,
                      (make_action(prefix + "-replay", retail.agent_id, 1, sut=sut),), prior_episode_state=first.episode_state)
        return
    if spec.family == "invalid_label":
        invalid = replace(make_action(prefix + "-bad", retail.agent_id, 1, sut=sut), label="feasible:" + str(variant))
        sut.arbitrate(prefix, market(), (retail, quant), (invalid,))
        return
    if spec.family == "agent_subclass":
        class AgentAlias(sut.AgentState):
            pass
        alias = AgentAlias(retail.agent_id, retail.posterior, retail.information, retail.inventory)
        sut.arbitrate(prefix, market(), (alias, quant), (make_action(prefix + "-bad", retail.agent_id, 1, sut=sut),))
        return
    if spec.family == "action_subclass":
        class ActionAlias(sut.CandidateAction):
            pass
        source = make_action(prefix + "-bad", retail.agent_id, 1, sut=sut)
        alias = ActionAlias(**source.__dict__)
        sut.arbitrate(prefix, market(), (retail, quant), (alias,))
        return
    if spec.family == "string_enum":
        invalid = replace(make_action(prefix + "-enum", retail.agent_id, 1, sut=sut), liquidity_mode="external_synthetic_liquidity")
        sut.arbitrate(prefix, market(), (retail, quant), (invalid,))
        return
    if spec.family == "bool_arrival":
        invalid = replace(make_action(prefix + "-bool", retail.agent_id, 1, sut=sut), arrival_sequence=True)
        sut.arbitrate(prefix, market(), (retail, quant), (invalid,))
        return
    raise ValueError("UNKNOWN_NEGATIVE_FAMILY:" + spec.family)


def episode_catalog() -> tuple[EpisodeSpec, ...]:
    return tuple(EpisodeSpec(
        f"EP-{index:03d}", index,
        _pairs({"first_quantity": ((index - 1) % 8) + 1, "second_quantity": ((index * 3) % 8) + 1, "first_label_mode": (index - 1) // 8, "continuation": "causal_parent"}),
        _pairs({"steps": 2, "independent_oracle": "valid", "causal_parent": "prior_event"}),
        "REQ-E23-EPISODE", "TEST-E23-EPISODES",
    ) for index in range(1, 25))


def execute_episode(spec: EpisodeSpec, *, sut: ModuleType = BASE_SUT):
    prefix = spec.episode_id.lower()
    retail, quant = _base_agents(prefix, sut=sut)
    first_quantity = ((spec.variant - 1) % 8) + 1
    second_quantity = ((spec.variant * 3) % 8) + 1
    first_label = (sut.ActionLabel.FEASIBLE, sut.ActionLabel.ABSTAIN, sut.ActionLabel.BLOCKED)[(spec.variant - 1) // 8]
    one = sut.arbitrate(prefix + ":one", market(), (retail, quant), (
        make_action(prefix + "-one", retail.agent_id, 1, sut=sut, quantity=first_quantity, label=first_label),
    ))
    two = sut.arbitrate(prefix + ":two", market(), one.episode_state.current_agents, (
        make_action(prefix + "-two", quant.agent_id, 1, sut=sut, side=OrderSide.SELL, quantity=second_quantity, parents=(one.events[-1].event_id,)),
    ), prior_episode_state=one.episode_state)
    return one, two


def counterfactual_catalog() -> tuple[CounterfactualSpec, ...]:
    return tuple(CounterfactualSpec(
        f"CF-{index:03d}", index, "assumption:cf-%03d" % index,
        _pairs({"quantity": ((index - 1) % 8) + 1, "side": "BUY" if ((index - 1) // 8) % 2 == 0 else "SELL", "requires_complete_information": bool((index - 1) // 16), "conflict_mode": (index - 1) // 8, "changed_action_count": 1}),
        _pairs({"changed_action_count": 1, "alternative_label": "abstain"}), "TEST-E23-COUNTERFACTUALS",
    ) for index in range(1, 37))


def execute_counterfactual(spec: CounterfactualSpec, *, sut: ModuleType = BASE_SUT):
    retail, quant = _base_agents(spec.pair_id.lower(), sut=sut)
    side = OrderSide.BUY if ((spec.variant - 1) // 8) % 2 == 0 else OrderSide.SELL
    owner = retail if side is OrderSide.BUY else quant
    action = replace(
        make_action(spec.pair_id.lower() + "-action", owner.agent_id, 1, sut=sut, side=side, quantity=((spec.variant - 1) % 8) + 1, requires_complete_information=bool((spec.variant - 1) // 16), conflict_key=(spec.pair_id.lower() + "-resource" if (spec.variant - 1) // 8 >= 2 else None)),
        assumption_ids=(spec.changed_assumption_id,),
    )
    return sut.run_one_step_counterfactual(spec.pair_id, market(), (retail, quant), (action,), spec.changed_assumption_id)


def cross_family_catalog(pairs: tuple[tuple[str, str], ...]) -> tuple[CrossFamilySpec, ...]:
    specs: list[CrossFamilySpec] = []
    index = 1
    for mutant_id, property_id in pairs:
        for fixture_variant in (1, 2, 3):
            specs.append(CrossFamilySpec(
                f"XFM-{index:03d}", mutant_id, property_id, fixture_variant,
                _pairs({"mutant_id": mutant_id, "property_id": property_id, "fixture_variant": fixture_variant}),
                _pairs({"baseline_relation": "holds", "mutant_relation": "detected"}), "TEST-E23-CROSS-FAMILY",
            ))
            index += 1
    return tuple(specs)
