from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cognitive_os_h1.contracts import (  # noqa: E402
    SEMANTIC_INVARIANT_IDS, cognitive_fingerprint, explore_critical_states, validate_bundle, validate_mission_graph,
    validate_organization, validate_semantics, validate_trace_handoff, validate_transition,
)

NOW = "2026-08-15T00:00:00Z"

def episode(**extra):
    value = {"schema_version":"DecisionEpisode/v1","decision_episode_id":"de-1","mission_id":"m-1","problem_signature_id":"ps-1","task_class":"ENGINEERING","materiality":"LOW","risk_class":"R1","state":"INTAKE","created_at":NOW,"authority_snapshot_ref":"auth-1","trace_root_id":"trace-1","reproducibility_fingerprint":"fp-1","w7_veto_status":"PASS","decision_status":"OPEN"}
    value.update(extra); return value

def graph(nodes, edges):
    return {"schema_version":"MissionGraph/v1","mission_graph_id":"mg-1","mission_id":"m-1","nodes":nodes,"edges":edges,"generated_at":NOW}

def node(name, **extra):
    value = {"work_item_id":name,"work_type":"TEST","owner_candidate":"synthetic","resource_class":"LIGHT","status":"PLANNED","retry_budget":1,"required_authority_refs":[]}
    value.update(extra); return value

class H1ContractTest(unittest.TestCase):
    def test_formal_schema_bundle_and_structure_positive_negative(self):
        schema = json.loads((ROOT / "schemas" / "contract-schemas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(schema["definitions"]), 11)
        self.assertEqual(validate_bundle([episode()]), [])
        errors = validate_bundle([{"schema_version":"DecisionEpisode/v1"}])
        self.assertTrue(any(e.code == "REQUIRED_FIELD_MISSING" for e in errors))

    def test_semantic_invariants_positive_and_negative(self):
        self.assertEqual(validate_semantics(episode()), [])
        cases = [
            (episode(w7_veto_status="VETO", decision_status="ACCEPTED"), "DE-W7-VETO-NO-ACCEPT"),
            (episode(state="EXECUTING", control_tower_authorization_ref=None), "DE-EXECUTION-AUTH-REQUIRED"),
            ({"schema_version":"ProblemSignature/v1","problem_signature_id":"p","task_class":"OTHER","objective":"x","materiality":"HIGH","reversibility":"REVERSIBLE","causal_requirement":"CAUSAL","evidence_mode":"INTERNAL_ONLY","point_in_time_required":True,"competing_hypotheses_required":False}, "PS-HIGH-MATERIALITY-EVIDENCE-OR-WAIVER"),
            ({"schema_version":"ChallengeCase/v1","challenge_id":"c","target_claim_id":"x","challenge_type":"OTHER","challenge_level":"C3","severity":"HIGH","status":"OPEN"}, "CH-C2-C4-INDEPENDENT-PASS-REQUIRED"),
            ({"schema_version":"OutcomeLearning/v1","learning_event_id":"l","decision_episode_id":"d","created_at":NOW,"requested_maturity":"FORMAL_SKILL"}, "OL-NO-DIRECT-FORMAL-SKILL"),
        ]
        for record, validator in cases:
            with self.subTest(validator=validator): self.assertIn(validator, {e.validator_id for e in validate_semantics(record)})

    def test_decision_state_machine_rework_and_identical_retry_attack(self):
        self.assertEqual(validate_transition("INTAKE", "PROBLEM_SIGNATURED"), [])
        self.assertTrue(validate_transition("INTAKE", "EXECUTING"))
        rework = {"schema_version":"ReworkRequest/v1","rework_request_id":"rw","decision_episode_id":"de","return_from_state":"ADJUDICATED","return_to_state":"EVIDENCE_PLAN_READY","reason_code":"EVIDENCE","retry_budget_remaining":1,"input_fingerprint_before":"a","input_fingerprint_after":"b"}
        self.assertEqual(validate_transition("ADJUDICATED", "EVIDENCE_PLAN_READY", rework), [])
        rework["input_fingerprint_after"] = "a"
        self.assertIn("IDENTICAL_RETRY_FORBIDDEN", {e.code for e in validate_transition("ADJUDICATED", "EVIDENCE_PLAN_READY", rework)})

    def test_mission_graph_dag_authorization_resource_and_cycle(self):
        good = graph([node("a", status="AUTHORIZED", required_authority_refs=["auth"], termination_condition_ref="done"), node("b")], [{"from":"a","to":"b","type":"DEPENDS_ON"}])
        self.assertEqual(validate_mission_graph(good, authorization_refs={"auth"}), [])
        bad = graph([node("a", resource_class="HEAVY_LOCAL", status="RUNNING", required_authority_refs=[]), node("b", resource_class="HEAVY_LOCAL", status="RUNNING", required_authority_refs=[])], [{"from":"a","to":"b","type":"DEPENDS_ON"},{"from":"b","to":"a","type":"BLOCKS"}])
        codes = {e.code for e in validate_mission_graph(bad, authorization_refs=set())}
        self.assertTrue({"DEPENDENCY_CYCLE", "HEAVY_LOCAL_CAP_EXCEEDED", "AUTHORIZATION_MISSING"}.issubset(codes))

    def test_organization_alias_authority_and_h1_h2_boundary(self):
        org = {"departments":[{"id":"USER","authority_domain":"USER_APPROVAL","node_kind":"DEPARTMENT"},{"id":"W3_SECOND_BRAIN","authority_domain":"KNOWLEDGE","node_kind":"DEPARTMENT"},{"id":"PRIMARY_PRODUCER","authority_domain":"NONE","node_kind":"ROLE_TEMPLATE"}],"edges":[{"from":"USER","to":"W3_SECOND_BRAIN"},{"from":"W3_SECOND_BRAIN","to":"PRIMARY_PRODUCER"},{"from":"PRIMARY_PRODUCER","to":"RESPONSIBLE_UPSTREAM"}]}
        self.assertEqual(validate_organization(org, alias_resolution={"RESPONSIBLE_UPSTREAM":["W3_SECOND_BRAIN"]}), [])
        bad = validate_organization(org, alias_resolution={"RESPONSIBLE_UPSTREAM":["USER", "W3_SECOND_BRAIN"]}, h2_authorized=True)
        self.assertTrue({"RETURN_ALIAS_NOT_UNIQUE", "H2_AUTHORIZATION_FORBIDDEN_IN_H1"}.issubset({e.code for e in bad}))

    def test_trace_handoff_and_fingerprint(self):
        handoff = {"schema_version":"FormalHandoff/v1","handoff_id":"h","decision_episode_id":"d","producer":"p","consumer":"c","stage":"TEST","epistemic_status":"SUPPORTED","input_fingerprint":"f","raw_trace_refs":["trace-1"],"created_at":NOW,"claim_ids":["claim"]}
        self.assertEqual(validate_trace_handoff(handoff, trace_ids={"trace-1"}, trace_level="T2"), [])
        self.assertIn("TRACE_INCOMPLETE", {e.code for e in validate_trace_handoff(handoff, trace_ids=set())})
        payload = {"SourceSnapshotHash":"a","ContextBundleHash":"b","UpstreamHandoffHashes":["c"],"PromptTemplateHash":"d","MethodSkillVersions":["e"],"ModelProvider":"synthetic","ModelID":"none","ToolSchemaHash":"f","CodeCommit":"g","DomainRuleSnapshot":"h","SchemaVersion":"v1","ui_color":"blue"}
        first = cognitive_fingerprint(payload); payload["ui_color"] = "red"; self.assertEqual(first, cognitive_fingerprint(payload))
        payload["CodeCommit"] = "changed"; self.assertNotEqual(first, cognitive_fingerprint(payload))
        payload["api_key"] = "forbidden"; self.assertRaises(ValueError, cognitive_fingerprint, payload)

    def test_synthetic_scenarios_and_bounded_model_exploration(self):
        scenarios = {"S1","S2","S3","S4","S5","S6","S7","S8","S9","S10"}
        fixture = json.loads((ROOT / "fixtures" / "scenarios.json").read_text(encoding="utf-8"))
        self.assertEqual({item["id"] for item in fixture["scenarios"]}, scenarios)
        report = explore_critical_states()
        self.assertGreater(report.states_checked, 40)
        self.assertEqual(report.violations, ())
        self.assertEqual(validate_organization({"departments":[],"edges":[]}, alias_resolution={}, h2_authorized=False), [])

    def test_repeated_run_is_deterministic(self):
        payload = {"SourceSnapshotHash":"a","ContextBundleHash":"b","UpstreamHandoffHashes":["c"],"PromptTemplateHash":"d","MethodSkillVersions":["e"],"ModelProvider":"synthetic","ModelID":"none","ToolSchemaHash":"f","CodeCommit":"g","DomainRuleSnapshot":"h","SchemaVersion":"v1"}
        first = (validate_bundle([episode()]), explore_critical_states(), cognitive_fingerprint(payload))
        second = (validate_bundle([episode()]), explore_critical_states(), cognitive_fingerprint(payload))
        self.assertEqual(first, second)

    def test_resource_policy_and_no_harness_shadow_implementation(self):
        audit = (ROOT / "public_safety_scan.py").read_text(encoding="utf-8")
        self.assertIn("NO_CHILD_PROCESS_CREATED", audit)
        self.assertNotIn("import deepseek", audit.casefold())
        self.assertNotIn("import subprocess", audit)

    def test_h0_semantic_registry_and_parallel_authorization_attack(self):
        self.assertEqual(len(SEMANTIC_INVARIANT_IDS), 31)
        self.assertIn("A-UNRESOLVED-ABSTAIN-VALID", SEMANTIC_INVARIANT_IDS)
        admissible = {"schema_version":"Adjudication/v1","adjudication_id":"a","claim_results":["c"],"disposition":"UNRESOLVED"}
        self.assertEqual(validate_semantics(admissible), [])
        parallel = graph([node("a", status="RUNNING", required_authority_refs=[], termination_condition_ref="done"), node("b")], [{"from":"a","to":"b","type":"CAN_PARALLEL_WITH"}])
        ids = {error.validator_id for error in validate_mission_graph(parallel, authorization_refs=set())}
        self.assertTrue({"MG-CAN-PARALLEL-NOT-AUTHORIZATION", "MG-EXECUTABLE-NODE-NEEDS-CONTROL-TOWER"}.issubset(ids))

    def test_remaining_named_semantic_invariants_have_fail_closed_attacks(self):
        cases = [
            ({"schema_version":"Mission/v1","mission_id":"m","intake_source":"USER","objective":"x","status":"RECEIVED","created_at":NOW,"intake_authorizes_execution":True}, "M-USER-INTAKE-NO-AUTH-GRANT"),
            ({"schema_version":"Claim/v1","claim_id":"c","claim_type":"MODEL_INFERENCE","statement_ref":"s","status":"OPEN","human_companion_claim_type":"OBSERVED_FACT"}, "C-PROSE-CANNOT-PROMOTE-INFERENCE-TO-FACT"),
            ({"schema_version":"Adjudication/v1","adjudication_id":"a","claim_results":["c"],"disposition":"ACCEPT","w7_veto_status":"VETO"}, "A-NO-W7-OVERRIDE"),
            ({"schema_version":"FormalHandoff/v1","handoff_id":"h","decision_episode_id":"d","producer":"p","consumer":"c","stage":"x","epistemic_status":"SUPPORTED","input_fingerprint":"f","raw_trace_refs":["t"],"created_at":NOW,"analysis_companion":{"epistemic_status":"OBSERVED"}}, "FH-HUMAN-COMPANION-NONAUTHORITATIVE"),
            ({"schema_version":"OutcomeLearning/v1","learning_event_id":"l","decision_episode_id":"d","created_at":NOW,"outcome_ref":"o","outcome_polarity":"POSITIVE","method_quality_update":"GOOD"}, "OL-GOOD-OUTCOME-NOT-PROOF-OF-GOOD-METHOD"),
            ({"schema_version":"OutcomeLearning/v1","learning_event_id":"l","decision_episode_id":"d","created_at":NOW,"outcome_ref":"o","outcome_polarity":"NEGATIVE","method_quality_update":"BAD"}, "OL-BAD-OUTCOME-NOT-PROOF-OF-BAD-METHOD"),
        ]
        for record, validator in cases:
            with self.subTest(validator=validator): self.assertIn(validator, {error.validator_id for error in validate_semantics(record)})

    def test_structural_timestamp_rework_graph_and_trace_attacks(self):
        bad_time = episode(created_at="2026-08-15T00:00:00")
        self.assertIn("RFC3339_OFFSET_AWARE_REQUIRED", {error.code for error in validate_bundle([bad_time])})
        wrong_target = {"schema_version":"ReworkRequest/v1","rework_request_id":"rw","decision_episode_id":"de","return_from_state":"ADJUDICATED","return_to_state":"EXECUTING","reason_code":"x","retry_budget_remaining":1,"input_fingerprint_before":"a","input_fingerprint_after":"b"}
        self.assertIn("REWORK_TARGET_FORBIDDEN", {error.code for error in validate_transition("ADJUDICATED", "EXECUTING", wrong_target)})
        unbounded = graph([node("a"), node("b")], [{"from":"a","to":"b","type":"RETURNS_TO"}])
        self.assertIn("REWORK_LOOP_UNBOUNDED", {error.code for error in validate_mission_graph(unbounded, authorization_refs=set())})
        handoff = {"schema_version":"FormalHandoff/v1","handoff_id":"h","decision_episode_id":"d","producer":"p","consumer":"c","stage":"TEST","epistemic_status":"SUPPORTED","input_fingerprint":"f","raw_trace_refs":["trace-1"],"created_at":NOW,"claim_ids":["claim"]}
        self.assertIn("TRACE_LEVEL_FIELD_MISSING", {error.code for error in validate_trace_handoff(handoff, trace_ids={"trace-1"}, trace_level="T3", trace_material={})})

    def test_organization_orphan_dead_end_trading_w3_attacks(self):
        org = {"departments":[{"id":"A","authority_domain":"KNOWLEDGE_MEMORY_LIFECYCLE","node_kind":"DEPARTMENT","produces":["x"]},{"id":"B","authority_domain":"KNOWLEDGE_MEMORY_LIFECYCLE","node_kind":"DEPARTMENT"}],"edges":[{"from":"A","to":"B","type":"LIVE_TRADE"}]}
        ids = {error.validator_id for error in validate_organization(org, alias_resolution={})}
        self.assertTrue({"OGV-W3-SINGLE-AUTHORITY", "OGV-022-A-SHARE-NO-TRADE"}.issubset(ids))
        orphan = validate_organization({"departments":[{"id":"A","authority_domain":"NONE","node_kind":"DEPARTMENT","produces":["x"]}],"edges":[]}, alias_resolution={})
        self.assertTrue({"OGV-002-ORPHAN-DEPARTMENT", "OGV-003-DEAD-END"}.issubset({error.validator_id for error in orphan}))

if __name__ == "__main__": unittest.main()
