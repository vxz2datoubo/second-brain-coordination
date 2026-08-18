"""Executable, synthetic-only S1-S10 regression scenarios."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .contracts import ValidationError, validate_organization, validate_semantics, validate_trace_handoff, validate_transition
from .fixtures import canonical_organization, episode, handoff


@dataclass(frozen=True)
class ScenarioReceipt:
    scenario_id: str
    transitions_checked: int
    errors: tuple[ValidationError, ...]
    final_disposition: str


def _rework(*, changed: bool) -> dict[str, Any]:
    return {"schema_version":"ReworkRequest/v1","rework_request_id":"r","decision_episode_id":"d","return_from_state":"ADJUDICATED","return_to_state":"EVIDENCE_PLAN_READY","reason_code":"SYNTHETIC","retry_budget_remaining":1,"input_fingerprint_before":"a","input_fingerprint_after":"b" if changed else "a"}


def execute_scenario(spec: dict[str, Any]) -> ScenarioReceipt:
    scenario_id = spec["id"]
    errors: list[ValidationError] = []
    transitions = 0
    for current, target in spec["expected_transitions"]:
        request = _rework(changed=scenario_id == "S5") if (current, target) == ("ADJUDICATED", "EVIDENCE_PLAN_READY") else None
        errors.extend(validate_transition(current, target, request)); transitions += 1
    if scenario_id == "S2":
        errors.extend(validate_semantics({"schema_version":"ProblemSignature/v1","problem_signature_id":"p","task_class":"RESEARCH","objective":"synthetic","materiality":"HIGH","reversibility":"REVERSIBLE","causal_requirement":"CAUSAL","evidence_mode":"EXTERNAL_REQUIRED","point_in_time_required":False,"competing_hypotheses_required":True}))
        errors.extend(validate_semantics({"schema_version":"ChallengeCase/v1","challenge_id":"c","target_claim_id":"claim","challenge_type":"ALTERNATIVE_EXPLANATION","challenge_level":"C3","severity":"HIGH","independent_pass_ref":"synthetic-independent","status":"VERIFIED"}))
    elif scenario_id == "S3":
        errors.extend(validate_semantics(episode(state="ABSTAINED", decision_status="ABSTAINED")))
    elif scenario_id == "S4":
        errors.extend(validate_semantics(episode(w7_veto_status="VETO", decision_status="ACCEPTED")))
    elif scenario_id == "S6":
        errors.extend(validate_transition("ADJUDICATED", "EVIDENCE_PLAN_READY", _rework(changed=False)))
    elif scenario_id == "S7":
        errors.extend(validate_semantics({"schema_version":"OutcomeLearning/v1","learning_event_id":"l","decision_episode_id":"d","created_at":"2026-08-15T00:00:00Z","correction_event_ref":"synthetic-correction"}))
    elif scenario_id == "S8":
        errors.extend(validate_trace_handoff(handoff(), trace_ids=set(), trace_level="T1"))
    elif scenario_id == "S9":
        errors.extend(validate_organization(canonical_organization(), alias_resolution={"RESPONSIBLE_UPSTREAM":["W3_SECOND_BRAIN", "SIGNAL_TOWER"]}))
    elif scenario_id == "S10":
        errors.extend(validate_organization(canonical_organization(), alias_resolution={"RESPONSIBLE_UPSTREAM":["W3_SECOND_BRAIN"]}, h2_authorized=True))
    return ScenarioReceipt(scenario_id, transitions, tuple(errors), spec["final_disposition"])
