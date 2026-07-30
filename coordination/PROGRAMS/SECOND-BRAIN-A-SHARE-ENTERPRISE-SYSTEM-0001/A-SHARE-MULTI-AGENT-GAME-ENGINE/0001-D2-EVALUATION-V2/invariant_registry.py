"""E25 executable controlled-violation registry for Evaluation V2.

The registry deliberately derives a malformed *artifact* from an actual,
already-executed ``GameRun``.  A predicate is then re-run against that object
and a named oracle reads the same object.  It never accepts a caller-provided
boolean as proof that an invariant was violated.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from d2_game_core import ExternalLiquidityFlowEvent, GameRun
from evaluation_v2_contract import canonical_sha256, public_value
from independent_oracle import evaluate_episode


PREDICATE_IDS = (
    "HAS_EPISODE", "NONEMPTY_EVENTS", "UNIQUE_EVENT_IDS", "ACTION_EVENT_BINDING",
    "INDEPENDENT_ACCOUNTING", "BOUNDARY_ORDER", "NO_UNEXPLAINED_FLOW",
    "TERMINAL_ACTION_COVERAGE", "STEP_MONOTONIC", "PORTFOLIO_DELTA_EXPLAINED",
)


@dataclass(frozen=True)
class NamedOracleEvidence:
    oracle_id: str
    detected: bool
    reason_codes: tuple[str, ...]
    artifact_sha256: str


@dataclass(frozen=True)
class ControlledViolationEvidence:
    predicate_id: str
    failure_oracle_id: str
    valid_predicate_passed: bool
    violating_predicate_passed: bool
    oracle: NamedOracleEvidence
    valid_artifact_sha256: str
    violating_artifact_sha256: str


Predicate = Callable[[GameRun], bool]
ViolationConstructor = Callable[[GameRun], GameRun]
FailureOracle = Callable[[GameRun], NamedOracleEvidence]


@dataclass(frozen=True)
class InvariantRule:
    predicate_id: str
    failure_oracle_id: str
    predicate: Predicate
    controlled_violation: ViolationConstructor
    failure_oracle: FailureOracle


def _artifact_sha256(run: GameRun) -> str:
    return canonical_sha256(public_value(run))


def _episode_required(run: GameRun):
    if run.episode_state is None:
        raise ValueError("E25_CONTROLLED_VIOLATION_REQUIRES_EPISODE")
    return run.episode_state


def _replace_episode(run: GameRun, episode) -> GameRun:
    return replace(run, episode_state=episode, events=episode.event_dag)


def _first_event(run: GameRun):
    episode = _episode_required(run)
    if not episode.event_dag:
        raise ValueError("E25_CONTROLLED_VIOLATION_REQUIRES_EVENT")
    return episode, episode.event_dag[0]


def _corrupt_current_inventory(run: GameRun) -> GameRun:
    episode = _episode_required(run)
    agent = episode.current_agents[0]
    if not agent.inventory.lots:
        raise ValueError("E25_CONTROLLED_VIOLATION_REQUIRES_INVENTORY_LOT")
    first_lot = agent.inventory.lots[0]
    changed_lot = replace(first_lot, quantity=first_lot.quantity + 1)
    changed_inventory = replace(agent.inventory, lots=(changed_lot,) + agent.inventory.lots[1:])
    changed_agent = replace(agent, inventory=changed_inventory)
    changed_episode = replace(episode, current_agents=(changed_agent,) + episode.current_agents[1:])
    return _replace_episode(run, changed_episode)


def _violate_has_episode(run: GameRun) -> GameRun:
    return replace(run, episode_state=None)


def _violate_nonempty_events(run: GameRun) -> GameRun:
    return replace(run, events=())


def _violate_unique_event_ids(run: GameRun) -> GameRun:
    episode, event = _first_event(run)
    changed_episode = replace(episode, event_dag=episode.event_dag + (replace(event, ordinal=event.ordinal + 1000),))
    return _replace_episode(run, changed_episode)


def _violate_action_event_binding(run: GameRun) -> GameRun:
    episode, event = _first_event(run)
    changed_event = replace(event, agent_id=event.agent_id + "-forged")
    changed_episode = replace(episode, event_dag=(changed_event,) + episode.event_dag[1:])
    return _replace_episode(run, changed_episode)


def _violate_boundary_order(run: GameRun) -> GameRun:
    episode, event = _first_event(run)
    changed_event = replace(event, step_index=event.step_index + 1000)
    changed_episode = replace(episode, event_dag=(changed_event,) + episode.event_dag[1:])
    return _replace_episode(run, changed_episode)


def _violate_unexplained_flow(run: GameRun) -> GameRun:
    episode = _episode_required(run)
    changed_flow = ExternalLiquidityFlowEvent(
        flow_id="E25-UNEXPLAINED-FLOW",
        ledger_event_id="E25-NO-SUCH-EVENT",
        agent_id=episode.initial_agents[0].agent_id,
        agent_inventory_delta=1,
        external_inventory_delta=-1,
    )
    changed_episode = replace(
        episode,
        external_liquidity_flows=episode.external_liquidity_flows + (changed_flow,),
    )
    return _replace_episode(run, changed_episode)


def _violate_terminal_action_coverage(run: GameRun) -> GameRun:
    episode = _episode_required(run)
    changed_episode = replace(episode, event_dag=episode.event_dag[1:])
    return _replace_episode(run, changed_episode)


def _violate_step_monotonic(run: GameRun) -> GameRun:
    episode = _episode_required(run)
    return _replace_episode(run, replace(episode, step_index=0))


def _predicate_has_episode(run: GameRun) -> bool:
    episode = run.episode_state
    return episode is not None and episode.step_index >= 1


def _predicate_nonempty_events(run: GameRun) -> bool:
    return bool(run.events)


def _predicate_unique_event_ids(run: GameRun) -> bool:
    episode = _episode_required(run)
    return len({event.event_id for event in episode.event_dag}) == len(episode.event_dag)


def _predicate_action_event_binding(run: GameRun) -> bool:
    episode = _episode_required(run)
    actions = {action.action_id: action for action in episode.action_registry}
    return all(
        actions.get(event.action_id) is not None and actions[event.action_id].agent_id == event.agent_id
        for event in episode.event_dag
    )


def _predicate_report_has_no(run: GameRun, *reason_codes: str) -> bool:
    report = evaluate_episode(_episode_required(run))
    return not any(code in report.reason_codes for code in reason_codes)


def _predicate_independent_accounting(run: GameRun) -> bool:
    return evaluate_episode(_episode_required(run)).valid


def _predicate_boundary_order(run: GameRun) -> bool:
    return _predicate_report_has_no(run, "ORACLE_ARRIVAL_SEQUENCE_ORDER")


def _predicate_no_unexplained_flow(run: GameRun) -> bool:
    return _predicate_report_has_no(
        run,
        "ORACLE_EXTERNAL_FLOW_MISSING_OR_DUPLICATE",
        "ORACLE_EXTERNAL_FLOW_OFFSET_MISMATCH",
        "ORACLE_UNEXPLAINED_EXTERNAL_FLOW",
    )


def _predicate_terminal_action_coverage(run: GameRun) -> bool:
    return _predicate_report_has_no(run, "ORACLE_ACTION_EVENT_COVERAGE_MISMATCH")


def _predicate_step_monotonic(run: GameRun) -> bool:
    episode = _episode_required(run)
    return (
        episode.step_index == len(episode.step_boundaries)
        and tuple(item.step_index for item in episode.step_boundaries) == tuple(range(1, episode.step_index + 1))
    )


def _predicate_portfolio_delta_explained(run: GameRun) -> bool:
    return _predicate_report_has_no(run, "ORACLE_INVENTORY_DELTA_MISMATCH")


def _inspect_missing_episode(run: GameRun) -> NamedOracleEvidence:
    """Inspect the carrier directly; this must not reuse HAS_EPISODE."""
    detected = getattr(run, "episode_state", None) is None
    return NamedOracleEvidence(
        "ORACLE-HAS_EPISODE", detected,
        ("ORACLE_MISSING_EPISODE",) if detected else (), _artifact_sha256(run),
    )


def _inspect_empty_run_events(run: GameRun) -> NamedOracleEvidence:
    """Inspect the GameRun event carrier directly, not NONEMPTY_EVENTS."""
    events = getattr(run, "events", None)
    detected = type(events) is not tuple or not events
    return NamedOracleEvidence(
        "ORACLE-NONEMPTY_EVENTS", detected,
        ("ORACLE_EMPTY_RUN_EVENTS",) if detected else (), _artifact_sha256(run),
    )


def _inspect_nonmonotonic_step_boundary(run: GameRun) -> NamedOracleEvidence:
    """Independently derive schedule consistency from the stored episode shape."""
    episode = getattr(run, "episode_state", None)
    boundaries = getattr(episode, "step_boundaries", None)
    if type(boundaries) is not tuple:
        return NamedOracleEvidence(
            "ORACLE-STEP_MONOTONIC", True, ("ORACLE_INVALID_STEP_BOUNDARY_COLLECTION",), _artifact_sha256(run),
        )
    expected_steps = tuple(range(1, len(boundaries) + 1))
    observed_steps = tuple(getattr(boundary, "step_index", None) for boundary in boundaries)
    stored_step_index = getattr(episode, "step_index", None)
    detected = stored_step_index != len(boundaries) or observed_steps != expected_steps
    return NamedOracleEvidence(
        "ORACLE-STEP_MONOTONIC", detected,
        ("ORACLE_STEP_BOUNDARY_MONOTONICITY",) if detected else (), _artifact_sha256(run),
    )


def _independent_oracle(oracle_id: str, run: GameRun, expected_reason: str) -> NamedOracleEvidence:
    report = evaluate_episode(_episode_required(run))
    return NamedOracleEvidence(oracle_id, expected_reason in report.reason_codes, report.reason_codes, _artifact_sha256(run))


def _rule_registry() -> dict[str, InvariantRule]:
    return {
        "HAS_EPISODE": InvariantRule(
            "HAS_EPISODE", "ORACLE-HAS_EPISODE", _predicate_has_episode, _violate_has_episode,
            _inspect_missing_episode,
        ),
        "NONEMPTY_EVENTS": InvariantRule(
            "NONEMPTY_EVENTS", "ORACLE-NONEMPTY_EVENTS", _predicate_nonempty_events, _violate_nonempty_events,
            _inspect_empty_run_events,
        ),
        "UNIQUE_EVENT_IDS": InvariantRule(
            "UNIQUE_EVENT_IDS", "ORACLE-UNIQUE_EVENT_IDS", _predicate_unique_event_ids, _violate_unique_event_ids,
            lambda run: _independent_oracle("ORACLE-UNIQUE_EVENT_IDS", run, "ORACLE_DUPLICATE_OR_INVALID_EVENT_ID"),
        ),
        "ACTION_EVENT_BINDING": InvariantRule(
            "ACTION_EVENT_BINDING", "ORACLE-ACTION_EVENT_BINDING", _predicate_action_event_binding, _violate_action_event_binding,
            lambda run: _independent_oracle("ORACLE-ACTION_EVENT_BINDING", run, "ORACLE_EVENT_AGENT_BINDING_MISMATCH"),
        ),
        "INDEPENDENT_ACCOUNTING": InvariantRule(
            "INDEPENDENT_ACCOUNTING", "ORACLE-INDEPENDENT_ACCOUNTING", _predicate_independent_accounting, _corrupt_current_inventory,
            lambda run: _independent_oracle("ORACLE-INDEPENDENT_ACCOUNTING", run, "ORACLE_INVENTORY_DELTA_MISMATCH"),
        ),
        "BOUNDARY_ORDER": InvariantRule(
            "BOUNDARY_ORDER", "ORACLE-BOUNDARY_ORDER", _predicate_boundary_order, _violate_boundary_order,
            lambda run: _independent_oracle("ORACLE-BOUNDARY_ORDER", run, "ORACLE_ARRIVAL_SEQUENCE_ORDER"),
        ),
        "NO_UNEXPLAINED_FLOW": InvariantRule(
            "NO_UNEXPLAINED_FLOW", "ORACLE-NO_UNEXPLAINED_FLOW", _predicate_no_unexplained_flow, _violate_unexplained_flow,
            lambda run: _independent_oracle("ORACLE-NO_UNEXPLAINED_FLOW", run, "ORACLE_UNEXPLAINED_EXTERNAL_FLOW"),
        ),
        "TERMINAL_ACTION_COVERAGE": InvariantRule(
            "TERMINAL_ACTION_COVERAGE", "ORACLE-TERMINAL_ACTION_COVERAGE", _predicate_terminal_action_coverage, _violate_terminal_action_coverage,
            lambda run: _independent_oracle("ORACLE-TERMINAL_ACTION_COVERAGE", run, "ORACLE_ACTION_EVENT_COVERAGE_MISMATCH"),
        ),
        "STEP_MONOTONIC": InvariantRule(
            "STEP_MONOTONIC", "ORACLE-STEP_MONOTONIC", _predicate_step_monotonic, _violate_step_monotonic,
            _inspect_nonmonotonic_step_boundary,
        ),
        "PORTFOLIO_DELTA_EXPLAINED": InvariantRule(
            "PORTFOLIO_DELTA_EXPLAINED", "ORACLE-PORTFOLIO_DELTA_EXPLAINED", _predicate_portfolio_delta_explained, _corrupt_current_inventory,
            lambda run: _independent_oracle("ORACLE-PORTFOLIO_DELTA_EXPLAINED", run, "ORACLE_INVENTORY_DELTA_MISMATCH"),
        ),
    }


def invariant_registry() -> dict[str, InvariantRule]:
    return _rule_registry()


def rule_for(predicate_id: str) -> InvariantRule:
    try:
        return invariant_registry()[predicate_id]
    except KeyError as error:
        raise ValueError("UNKNOWN_INVARIANT_PREDICATE:" + predicate_id) from error


def validate_invariant_registry(
    predicate_ids: tuple[str, ...], registry: dict[str, InvariantRule] | None = None,
) -> None:
    registry = invariant_registry() if registry is None else registry
    if tuple(sorted(registry)) != tuple(sorted(PREDICATE_IDS)):
        raise AssertionError("E25_INVARIANT_REGISTRY_INCOMPLETE")
    if len(set(predicate_ids)) != len(predicate_ids):
        raise AssertionError("E25_DUPLICATE_PREDICATE_REGISTRATION")
    for predicate_id in predicate_ids:
        rule = registry.get(predicate_id)
        if rule is None:
            raise AssertionError("E25_UNMAPPED_INVARIANT_PREDICATE:" + predicate_id)
        if not rule.failure_oracle_id.startswith("ORACLE-"):
            raise AssertionError("E25_INVALID_FAILURE_ORACLE_ID:" + predicate_id)
        if not callable(rule.predicate) or not callable(rule.controlled_violation) or not callable(rule.failure_oracle):
            raise AssertionError("E25_INCOMPLETE_INVARIANT_RULE:" + predicate_id)
        _assert_oracle_independence(rule)


def _assert_oracle_independence(rule: InvariantRule) -> None:
    """Reject a failure oracle that closes over its paired predicate or rule."""
    pending = list(getattr(rule.failure_oracle, "__closure__", ()) or ())
    seen: set[int] = set()
    while pending:
        value = pending.pop().cell_contents
        marker = id(value)
        if marker in seen:
            continue
        seen.add(marker)
        if value is rule.predicate:
            raise AssertionError("E26_ORACLE_DEPENDS_ON_PAIRED_PREDICATE:" + rule.predicate_id)
        if isinstance(value, InvariantRule):
            pending.extend(getattr(value.failure_oracle, "__closure__", ()) or ())
            if value.predicate is rule.predicate:
                raise AssertionError("E26_ORACLE_DEPENDS_ON_PAIRED_PREDICATE:" + rule.predicate_id)


def execute_controlled_violation(predicate_id: str, valid_run: GameRun) -> ControlledViolationEvidence:
    rule = rule_for(predicate_id)
    return execute_invariant_rule(rule, valid_run)


def execute_invariant_rule(rule: InvariantRule, valid_run: GameRun) -> ControlledViolationEvidence:
    """Execute one registered predicate against its real controlled artifact."""
    valid_passed = rule.predicate(valid_run)
    violating_run = rule.controlled_violation(valid_run)
    violating_passed = rule.predicate(violating_run)
    oracle = rule.failure_oracle(violating_run)
    if not valid_passed:
        raise AssertionError("E25_VALID_FIXTURE_REJECTED:" + rule.predicate_id)
    if violating_passed:
        raise AssertionError("DECORATIVE_OR_NON_VIOLATING_FIXTURE:" + rule.predicate_id)
    if not oracle.detected:
        raise AssertionError("E25_NAMED_ORACLE_MISSED_CONTROLLED_VIOLATION:" + rule.predicate_id)
    return ControlledViolationEvidence(
        rule.predicate_id, rule.failure_oracle_id, valid_passed, violating_passed, oracle,
        _artifact_sha256(valid_run), _artifact_sha256(violating_run),
    )
