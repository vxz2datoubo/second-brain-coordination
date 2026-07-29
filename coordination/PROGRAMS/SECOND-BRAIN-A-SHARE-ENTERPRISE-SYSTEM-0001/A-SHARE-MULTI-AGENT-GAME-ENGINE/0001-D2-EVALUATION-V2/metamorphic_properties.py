"""Black-box metamorphic properties for synthetic D2 Evaluation V2."""
from __future__ import annotations

from dataclasses import replace

from d2_game_core import CandidateAction, arbitrate
from synthetic_engine.fixtures import market
from synthetic_engine.types import SyntheticOrder

from evaluation_v2_contract import PropertyReport, canonical_sha256
from independent_oracle import evaluate_episode, independent_digest, independent_projection
from synthetic_cases import (
    EpisodeSpec, NegativeCaseSpec,
    ScenarioSpec,
    _base_agents,
    execute_episode,
    execute_negative,
    execute_scenario,
    make_action,
)


PROPERTY_IDS = (
    "MP-001-FIXED-ARRIVAL-PERMUTATION",
    "MP-002-IDENTIFIER-ALPHA-RENAMING",
    "MP-003-EPISODE-CONTINUATION",
    "MP-004-DUPLICATE-REPLAY-REJECTION",
    "MP-005-PEER-CLOSED-SYSTEM-CONSERVATION",
    "MP-006-EXTERNAL-FLOW-ACCOUNTING",
    "MP-007-TAMPER-DETECTION",
    "MP-008-EXACT-BOUNDARY-REJECTION",
)


def _semantic_events(run, reverse_ids: dict[str, str] | None = None):
    reverse_ids = reverse_ids or {}
    return tuple(
        (
            reverse_ids.get(event.agent_id, event.agent_id), reverse_ids.get(event.action_id, event.action_id),
            event.accepted, event.label.value, event.outcome_status, event.filled_quantity,
            event.rejected_reason_codes, event.liquidity_mode.value, event.conflict_transition.value,
        )
        for event in run.events
    )


def fixed_arrival_permutation() -> PropertyReport:
    retail, quant = _base_agents("mp-arrival")
    actions = (
        make_action("mp-arrival-zeta", retail.agent_id, 1, conflict_key="mp-arrival-resource"),
        make_action("mp-arrival-alpha", quant.agent_id, 2, conflict_key="mp-arrival-resource"),
    )
    baseline = arbitrate("mp-arrival", market(), (retail, quant), actions)
    transformed = arbitrate("mp-arrival", market(), (retail, quant), tuple(reversed(actions)))
    passed = _semantic_events(baseline) == _semantic_events(transformed)
    return PropertyReport(PROPERTY_IDS[0], passed, "arrival_sequence remains the sole priority", independent_digest(baseline.episode_state), independent_digest(transformed.episode_state))


def identifier_alpha_renaming() -> PropertyReport:
    retail, quant = _base_agents("mp-alpha")
    original = (
        make_action("mp-alpha-retail", retail.agent_id, 1, conflict_key="mp-alpha-resource"),
        make_action("mp-alpha-quant", quant.agent_id, 2, conflict_key="mp-alpha-resource"),
    )
    baseline = arbitrate("mp-alpha", market(), (retail, quant), original)
    renamed_retail, renamed_quant = _base_agents("mp-alpha-renamed")
    renamed = (
        make_action("mp-alpha-renamed-retail", renamed_retail.agent_id, 1, conflict_key="mp-alpha-renamed-resource"),
        make_action("mp-alpha-renamed-quant", renamed_quant.agent_id, 2, conflict_key="mp-alpha-renamed-resource"),
    )
    transformed = arbitrate("mp-alpha-renamed", market(), (renamed_retail, renamed_quant), renamed)
    reverse = {
        renamed_retail.agent_id: retail.agent_id, renamed_quant.agent_id: quant.agent_id,
        renamed[0].action_id: original[0].action_id, renamed[1].action_id: original[1].action_id,
    }
    passed = _semantic_events(baseline) == _semantic_events(transformed, reverse)
    return PropertyReport(PROPERTY_IDS[1], passed, "consistent identifier renaming preserves normalized event semantics", independent_digest(baseline.episode_state), independent_digest(transformed.episode_state))


def episode_continuation_equivalence() -> PropertyReport:
    baseline_one, baseline_two = execute_episode(EpisodeSpec("EP-MP", 1, "REQ", "TEST"))
    transformed_one, transformed_two = execute_episode(EpisodeSpec("EP-MP", 1, "REQ", "TEST"))
    passed = (
        baseline_two.episode_state.step_index == 2
        and _semantic_events(baseline_two) == _semantic_events(transformed_two)
        and independent_projection(baseline_two.episode_state) == independent_projection(transformed_two.episode_state)
    )
    return PropertyReport(PROPERTY_IDS[2], passed, "same immutable continuation schedule reconstructs the same public episode", independent_digest(baseline_two.episode_state), independent_digest(transformed_two.episode_state))


def duplicate_replay_rejection() -> PropertyReport:
    try:
        execute_negative(NegativeCaseSpec("NEG-MP-REPLAY", "prior_replay", 1, "ValueError", "TEST"))
    except ValueError as error:
        passed, observation = True, str(error)
    else:
        passed, observation = False, "replay accepted"
    digest = canonical_sha256({"property": PROPERTY_IDS[3], "observation": observation})
    return PropertyReport(PROPERTY_IDS[3], passed, observation, digest, digest)


def peer_closed_system_conservation() -> PropertyReport:
    run = execute_scenario(ScenarioSpec("MP-PEER", "peer", 1, "REQ", "TEST"))
    report = evaluate_episode(run.episode_state)
    has_no_flow = not run.episode_state.external_liquidity_flows
    passed = report.valid and has_no_flow
    return PropertyReport(PROPERTY_IDS[4], passed, ",".join(report.reason_codes) or "peer delta conserved", independent_digest(run.episode_state), independent_digest(run.episode_state))


def external_flow_accounting() -> PropertyReport:
    run = execute_scenario(ScenarioSpec("MP-EXTERNAL", "external_buy", 1, "REQ", "TEST"))
    report = evaluate_episode(run.episode_state)
    passed = report.valid and bool(run.episode_state.external_liquidity_flows)
    return PropertyReport(PROPERTY_IDS[5], passed, ",".join(report.reason_codes) or "external offset accounted", independent_digest(run.episode_state), independent_digest(run.episode_state))


def tamper_detection() -> PropertyReport:
    run = execute_scenario(ScenarioSpec("MP-TAMPER", "external_buy", 1, "REQ", "TEST"))
    baseline = independent_digest(run.episode_state)
    event = run.episode_state.event_dag[0]
    tampered = replace(run.episode_state, event_dag=(replace(event, filled_quantity=0, accepted=False),))
    report = evaluate_episode(tampered, expected_digest=baseline)
    passed = not report.valid and "ORACLE_INDEPENDENT_DIGEST_MISMATCH" in report.reason_codes
    return PropertyReport(PROPERTY_IDS[6], passed, ",".join(report.reason_codes), baseline, independent_digest(tampered))


def exact_boundary_rejection() -> PropertyReport:
    retail, quant = _base_agents("mp-exact")
    source = make_action("mp-exact-action", retail.agent_id, 1)
    class NominalAction(CandidateAction):
        pass
    variants = {
        "nominal_carrier": NominalAction(**source.__dict__),
        "string_enum": replace(source, label="feasible"),
        "bool_primitive": replace(source, arrival_sequence=True),
        "multi_fault": replace(source, label="feasible", arrival_sequence=True),
    }
    observed = {}
    for name, action in variants.items():
        try:
            arbitrate("mp-exact-" + name, market(), (retail, quant), (action,))
        except ValueError as error:
            observed[name] = str(error)
        else:
            observed[name] = "boundary accepted"
    passed = all(value != "boundary accepted" for value in observed.values())
    observation = ";".join(name + "=" + observed[name] for name in sorted(observed))
    digest = canonical_sha256({"property": PROPERTY_IDS[7], "observation": observation})
    return PropertyReport(PROPERTY_IDS[7], passed, observation, digest, digest)


def property_function_map():
    return {
        PROPERTY_IDS[0]: fixed_arrival_permutation,
        PROPERTY_IDS[1]: identifier_alpha_renaming,
        PROPERTY_IDS[2]: episode_continuation_equivalence,
        PROPERTY_IDS[3]: duplicate_replay_rejection,
        PROPERTY_IDS[4]: peer_closed_system_conservation,
        PROPERTY_IDS[5]: external_flow_accounting,
        PROPERTY_IDS[6]: tamper_detection,
        PROPERTY_IDS[7]: exact_boundary_rejection,
    }


def run_metamorphic_properties() -> tuple[PropertyReport, ...]:
    return tuple(function() for _property_id, function in property_function_map().items())
