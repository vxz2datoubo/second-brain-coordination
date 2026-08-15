from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive_os_h1.contracts import (  # noqa: E402
    SEMANTIC_INVARIANT_IDS, validate_mission_graph, validate_semantics,
    validate_structure, validate_transition,
)
from cognitive_os_h1.fixtures import episode, handoff  # noqa: E402

NOW = "2026-08-15T00:00:00Z"


def ps(**extra):
    value = {"schema_version":"ProblemSignature/v1","problem_signature_id":"p","task_class":"ENGINEERING","objective":"x","materiality":"LOW","reversibility":"REVERSIBLE","causal_requirement":"DESCRIPTIVE","evidence_mode":"INTERNAL_ONLY","point_in_time_required":False,"competing_hypotheses_required":False}
    value.update(extra); return value


def mission(**extra):
    value = {"schema_version":"Mission/v1","mission_id":"m","intake_source":"USER","objective":"x","status":"RECEIVED","created_at":NOW}
    value.update(extra); return value


def graph(nodes, edges):
    return {"schema_version":"MissionGraph/v1","mission_graph_id":"g","mission_id":"m","nodes":nodes,"edges":edges,"generated_at":NOW}


def node(identifier, **extra):
    value = {"work_item_id":identifier,"work_type":"TEST","owner_candidate":"synthetic","resource_class":"LIGHT","status":"PLANNED","retry_budget":1,"required_authority_refs":[]}
    value.update(extra); return value


def claim(**extra):
    value = {"schema_version":"Claim/v1","claim_id":"c","claim_type":"OBSERVED_FACT","statement_ref":"s","status":"OPEN"}
    value.update(extra); return value


def challenge(**extra):
    value = {"schema_version":"ChallengeCase/v1","challenge_id":"c","target_claim_id":"x","challenge_type":"OTHER","challenge_level":"C1","severity":"LOW","status":"OPEN"}
    value.update(extra); return value


def adjudication(**extra):
    value = {"schema_version":"Adjudication/v1","adjudication_id":"a","claim_results":["c"],"disposition":"UNRESOLVED"}
    value.update(extra); return value


def learning(**extra):
    value = {"schema_version":"OutcomeLearning/v1","learning_event_id":"l","decision_episode_id":"d","created_at":NOW,"correction_event_ref":"correction"}
    value.update(extra); return value


def rework(**extra):
    value = {"schema_version":"ReworkRequest/v1","rework_request_id":"r","decision_episode_id":"d","return_from_state":"ADJUDICATED","return_to_state":"EVIDENCE_PLAN_READY","reason_code":"TEST","retry_budget_remaining":1,"input_fingerprint_before":"a","input_fingerprint_after":"b"}
    value.update(extra); return value


def outcomes() -> dict[str, tuple[list, list]]:
    return {
        "DE-W7-VETO-NO-ACCEPT": (validate_semantics(episode(w7_veto_status="PASS", decision_status="ACCEPTED")), validate_semantics(episode(w7_veto_status="VETO", decision_status="ACCEPTED"))),
        "DE-ABSTAIN-STATE-CONSISTENCY": (validate_semantics(episode(state="ABSTAINED", decision_status="ABSTAINED")), validate_semantics(episode(state="INTAKE", decision_status="ABSTAINED"))),
        "DE-EXECUTION-AUTH-REQUIRED": (validate_semantics(episode(state="EXECUTING", control_tower_authorization_ref="a")), validate_semantics(episode(state="EXECUTING"))),
        "DE-POST-PRIMARY-TRACE-RESOLVABLE": (validate_semantics(episode(state="PRIMARY_RESULT_READY", control_tower_authorization_ref="a"), trace_refs={"trace-1"}), validate_semantics(episode(state="PRIMARY_RESULT_READY", control_tower_authorization_ref="a"), trace_refs=None)),
        "DE-LEARNING-NEEDS-OUTCOME-OR-CORRECTION": (validate_semantics(episode(learning_ref="l", outcome_ref="o")), validate_semantics(episode(learning_ref="l"))),
        "DE-NO-RAW-PRIVATE-BODY": (validate_semantics(episode()), validate_semantics(episode(raw_private_source_body="synthetic-disallowed"))),
        "PS-HIGH-MATERIALITY-EVIDENCE-OR-WAIVER": (validate_semantics(ps(materiality="HIGH", evidence_mode="EXTERNAL_REQUIRED")), validate_semantics(ps(materiality="HIGH"))),
        "PS-CAUSAL-REQUIRES-COMPETING-HYPOTHESES": (validate_semantics(ps(causal_requirement="CAUSAL", competing_hypotheses_required=True)), validate_semantics(ps(causal_requirement="CAUSAL"))),
        "PS-PIT-REQUIRES-CAPABILITY": (validate_semantics(ps(point_in_time_required=True, pit_capability_ref="pit")), validate_semantics(ps(point_in_time_required=True))),
        "M-USER-INTAKE-NO-AUTH-GRANT": (validate_semantics(mission()), validate_semantics(mission(intake_authorizes_execution=True))),
        "M-COMPLETED-NEEDS-RESULT-OR-NO-WORK": (validate_semantics(mission(status="COMPLETED", final_result_ref="r")), validate_semantics(mission(status="COMPLETED"))),
        "MG-DEPENDENCY-DAG-ACYCLIC": (validate_mission_graph(graph([node("a"),node("b")],[{"from":"a","to":"b","type":"DEPENDS_ON"}]), authorization_refs=set()), validate_mission_graph(graph([node("a"),node("b")],[{"from":"a","to":"b","type":"DEPENDS_ON"},{"from":"b","to":"a","type":"BLOCKS"}]), authorization_refs=set())),
        "MG-RETURN-CYCLE-BOUNDED": (validate_mission_graph(graph([node("a"),node("b")],[{"from":"a","to":"b","type":"RETURNS_TO","rework_request":{"retry_budget_remaining":1,"termination_condition_ref":"done","escalation_ref":"user"}}]), authorization_refs=set()), validate_mission_graph(graph([node("a"),node("b")],[{"from":"a","to":"b","type":"RETURNS_TO"}]), authorization_refs=set())),
        "MG-EXECUTABLE-NODE-NEEDS-CONTROL-TOWER": (validate_mission_graph(graph([node("a",status="AUTHORIZED",required_authority_refs=["auth"],termination_condition_ref="done")],[]), authorization_refs={"auth"}), validate_mission_graph(graph([node("a",status="AUTHORIZED",termination_condition_ref="done")],[]), authorization_refs=set())),
        "MG-CAN-PARALLEL-NOT-AUTHORIZATION": (validate_mission_graph(graph([node("a"),node("b")],[{"from":"a","to":"b","type":"CAN_PARALLEL_WITH"}]), authorization_refs=set()), validate_mission_graph(graph([node("a",status="RUNNING",termination_condition_ref="done"),node("b")],[{"from":"a","to":"b","type":"CAN_PARALLEL_WITH"}]), authorization_refs=set())),
        "MG-HEAVY-LOCAL-RESOURCE-CAP": (validate_mission_graph(graph([node("a",resource_class="HEAVY_LOCAL",status="RUNNING",required_authority_refs=["auth"],termination_condition_ref="done")],[]), authorization_refs={"auth"}), validate_mission_graph(graph([node("a",resource_class="HEAVY_LOCAL",status="RUNNING",required_authority_refs=["auth"],termination_condition_ref="done"),node("b",resource_class="HEAVY_LOCAL",status="RUNNING",required_authority_refs=["auth"],termination_condition_ref="done")],[]), authorization_refs={"auth"})),
        "C-UNKNOWN-CONFIDENCE-UNKNOWN": (validate_semantics(claim(claim_type="UNKNOWN", confidence_class="UNKNOWN")), validate_semantics(claim(claim_type="UNKNOWN", confidence_class="HIGH"))),
        "C-MATERIAL-CAUSAL-NEEDS-FALSIFIER": (validate_semantics(claim(claim_type="CAUSAL_HYPOTHESIS",materiality="HIGH",falsifier_refs=["f"])), validate_semantics(claim(claim_type="CAUSAL_HYPOTHESIS",materiality="HIGH"))),
        "C-PROSE-CANNOT-PROMOTE-INFERENCE-TO-FACT": (validate_semantics(claim(claim_type="MODEL_INFERENCE")), validate_semantics(claim(claim_type="MODEL_INFERENCE",human_companion_claim_type="OBSERVED_FACT"))),
        "CH-C2-C4-INDEPENDENT-PASS-REQUIRED": (validate_semantics(challenge(challenge_level="C3",independent_pass_ref="i")), validate_semantics(challenge(challenge_level="C3"))),
        "A-NO-W7-OVERRIDE": (validate_semantics(adjudication(disposition="ACCEPT",w7_veto_status="PASS")), validate_semantics(adjudication(disposition="ACCEPT",w7_veto_status="VETO"))),
        "A-UNRESOLVED-ABSTAIN-VALID": (validate_structure(adjudication()), validate_structure(adjudication(disposition="NOT_A_DISPOSITION"))),
        "FH-RAW-TRACE-REF-REQUIRED": (validate_semantics(handoff()), validate_semantics(handoff(raw_trace_refs=[]))),
        "FH-HUMAN-COMPANION-NONAUTHORITATIVE": (validate_semantics(handoff(analysis_companion={"rationale":"safe"})), validate_semantics(handoff(analysis_companion={"epistemic_status":"OBSERVED"}))),
        "OL-NEEDS-OUTCOME-CORRECTION-OR-AUDIT": (validate_semantics(learning()), validate_semantics(learning(correction_event_ref=None))),
        "OL-NO-DIRECT-FORMAL-SKILL": (validate_semantics(learning()), validate_semantics(learning(requested_maturity="FORMAL_SKILL"))),
        "OL-GOOD-OUTCOME-NOT-PROOF-OF-GOOD-METHOD": (validate_semantics(learning(outcome_ref="o",outcome_polarity="POSITIVE")), validate_semantics(learning(outcome_ref="o",outcome_polarity="POSITIVE",method_quality_update="GOOD"))),
        "OL-BAD-OUTCOME-NOT-PROOF-OF-BAD-METHOD": (validate_semantics(learning(outcome_ref="o",outcome_polarity="NEGATIVE")), validate_semantics(learning(outcome_ref="o",outcome_polarity="NEGATIVE",method_quality_update="BAD"))),
        "RW-RETURN-TARGET-ALLOWED-BY-STATE-MACHINE": (validate_transition("ADJUDICATED","EVIDENCE_PLAN_READY",rework()), validate_transition("ADJUDICATED","EXECUTING",rework(return_to_state="EXECUTING"))),
        "RW-NO-RETRY-WHEN-BUDGET-ZERO": (validate_transition("ADJUDICATED","EVIDENCE_PLAN_READY",rework()), validate_transition("ADJUDICATED","EVIDENCE_PLAN_READY",rework(retry_budget_remaining=0))),
        "RW-RETRY-REQUIRES-MATERIAL-CHANGE-OR-EXPLICIT-ESCALATION": (validate_transition("ADJUDICATED","EVIDENCE_PLAN_READY",rework()), validate_transition("ADJUDICATED","EVIDENCE_PLAN_READY",rework(input_fingerprint_after="a"))),
    }


class InvariantCoverageTest(unittest.TestCase):
    def test_canonical_registry_is_total_and_executable(self):
        registry = json.loads((ROOT / "fixtures" / "invariant-coverage.json").read_text(encoding="utf-8"))["coverage"]
        self.assertEqual(set(registry), SEMANTIC_INVARIANT_IDS)
        cases = outcomes()
        self.assertEqual(set(cases), set(registry))
        for invariant_id, evidence in registry.items():
            with self.subTest(invariant_id=invariant_id):
                self.assertTrue(evidence["validator"] and evidence["positive"] and evidence["negative"])
                positive, negative = cases[invariant_id]
                self.assertFalse(any(error.code == evidence["error_code"] and error.path == evidence["error_path"] for error in positive))
                self.assertTrue(any(error.code == evidence["error_code"] and error.path == evidence["error_path"] for error in negative), negative)


if __name__ == "__main__": unittest.main()
