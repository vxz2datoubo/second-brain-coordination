from __future__ import annotations

from base64 import b64encode
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from idle_signal_apply import (
    ACTIVATION_MANIFEST_SCHEMA,
    APPLY_INTENT_SCHEMA,
    APPLY_RECEIPT_SCHEMA,
    APPLIED_STATE_SCHEMA,
    AUTHORIZED_LOGICAL_PLAN,
    BOOTSTRAP_EVIDENCE_SCHEMA,
    BOOTSTRAP_MANIFEST_SCHEMA,
    CLAIMS_FILE,
    COORDINATOR_REPOSITORY,
    GPT_WORKERS_REGISTRY,
    INDEPENDENCE_ATTESTATION,
    RESOURCE_CLASS,
    REVIEWER_ROLE,
    REVIEWER_SEPARATION,
    TRUSTED_APPLIED_STATE_SCHEMA,
    TRUSTED_BOOTSTRAP_SCHEMA,
    IdleSignalApplyError,
    _authorization_identity,
    _digest,
    _next_route_epoch,
    _required_bootstrap_markers,
    _trusted_bootstrap_observation,
    _trusted_exact_head_acceptance,
    _trusted_post_apply_observation,
    prepare_apply_transaction,
    validate_bootstrap_evidence,
    verify_applied_state,
)
from idle_signal_scheduler import AUTHORIZATION_SCHEMA, OPPORTUNITY_SCHEMA
from idle_signal_scheduler import validate_opportunity


REPO_ROOT = Path(__file__).resolve().parents[3]
MAIN = "a" * 40
REVIEWED = "e" * 40
MERGE = "f" * 40
BOOTSTRAP = "d" * 40


class FakeGatewayError(Exception):
    pass


class FakeObserver:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = copy.deepcopy(responses)

    def _get_json(self, path: str):
        if path not in self.responses:
            raise AssertionError(f"unexpected GitHub read: {path}")
        return {}, copy.deepcopy(self.responses[path]), {"path": path}


def proposal(signal_ref: str = "signal:r152-fixture") -> dict:
    return {
        "schema_version": "TaskReleaseProposal/v1",
        "release_candidate_id": "R152-FIXTURE",
        "source_signal_refs": [signal_ref, "issue://463"],
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "desired_effect": "Apply one governed R151 authorization without authority expansion.",
        "proposed_target_domain": "SHARED_COGNITIVE_OS",
        "proposed_write_surface": {
            "write_paths": ["coordination/CONTROL-TOWER/example_bounded_target.py"],
            "read_paths": [
                "coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml",
                "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
            ],
            "interfaces": [
                {
                    "name": "IdleSignalAutoReleaseAuthorization",
                    "mode": "read",
                    "frozen": True,
                }
            ],
            "read_domains": ["SHARED_COGNITIVE_OS"],
            "write_domains": ["SHARED_COGNITIVE_OS"],
            "authority_claims": [],
        },
        "materiality": "MATERIAL",
        "risk": ["bounded reversible engineering"],
        "out_of_scope": ["production deployment", "secrets", "trading"],
        "capability_inventory": [
            {
                "component_id": "R151IdleSignalScheduler",
                "decision": "EXTEND",
                "satisfies_requirement": False,
                "evidence_refs": ["pr://462"],
            }
        ],
        "relations": [
            {
                "relation": "EXTENDS",
                "source": "R152ApplyTransaction",
                "target": "R151IdleSignalScheduler",
                "evidence_refs": ["issue://463"],
            }
        ],
        "reverse_consumers": [
            {
                "consumer_id": "startup_task_apply",
                "impact": "CONSUMER_REVALIDATION_ONLY",
                "evidence_refs": ["issue://463"],
            }
        ],
        "consumer_inventory_complete": True,
        "composition": {
            "optional": True,
            "can_compose": True,
            "core_invariant": False,
            "missing_capability_behavior": "ABSTAIN",
            "removal_preserves_unrelated_core": True,
            "justification": "Apply composes after retained R151/R150/R149 gates.",
        },
        "synchronized_change_set": [],
        "regression_revalidation_set": ["startup_task_apply"],
        "unaffected_set": [
            {
                "component_id": "SignalTowerDurableTruth",
                "evidence_refs": ["boundary://signal-does-not-self-authorize"],
            }
        ],
        "unresolved_unknowns": [],
    }


def opportunity(
    opportunity_id: str = "R152-OPP-001",
    signal_ref: str = "signal:r152-fixture",
    *,
    release_proposal: dict | None = None,
) -> dict:
    p = copy.deepcopy(release_proposal or proposal(signal_ref))
    return {
        "schema_version": OPPORTUNITY_SCHEMA,
        "opportunity_id": opportunity_id,
        "signal_ref": signal_ref,
        "signal_primary_domain": "SHARED_COGNITIVE_OS",
        "source_evidence_refs": [signal_ref, "issue://463"],
        "desired_effect": p["desired_effect"],
        "problem_to_solve": "R151 authorization must not become a caller-controlled mutation primitive.",
        "success_condition": "Apply is fresh, exact-bound, staged, and independently reviewable.",
        "current_disposition": "NEW_DURABLE_SIGNAL",
        "epistemic_state": "USER_EXPLICIT",
        "desired_effect_gap_proven": True,
        "dependency_ready": True,
        "priority_class": "P3_BOUNDED_IMPROVEMENT",
        "user_value_score": 90,
        "materiality_score": 85,
        "dependency_readiness_score": 90,
        "age_cycles": 1,
        "estimated_cost_score": 25,
        "task_release_proposal": p,
    }


def hints() -> dict:
    return {
        "schema_version": "StartupPriorityHints/v1",
        "observation_id": "r152-fixture-hints",
        "evidence_refs": ["fixture://current-user-context"],
        "items": [],
    }


def authorization(raw_opportunity: dict, main: str = MAIN) -> dict:
    normalized = validate_opportunity(raw_opportunity)
    value = {
        "schema_version": AUTHORIZATION_SCHEMA,
        "signal_ref": normalized["signal_ref"],
        "opportunity_id": normalized["opportunity_id"],
        "opportunity_digest": normalized["opportunity_digest"],
        "canonical_main": main,
        "priority_observation_digest": "b" * 64,
        "r150_receipt_digest": "c" * 64,
        "r150_final_disposition": "RELEASE_AS_EXTENSION",
        "standing_user_policy_ref": "issue://461#user-direction-2026-08-26",
        "priority_semantics_ref": "fixture://priority",
        "priority_provider_ref": "fixture://provider",
        "release_gate_refs": [
            "coordination/CONTROL-TOWER/task_release_impact.py",
            "coordination/CONTROL-TOWER/trusted_task_release.py",
        ],
        "side_effect_plan": list(AUTHORIZED_LOGICAL_PLAN),
        "authority": {
            "creates_signal_truth": False,
            "signal_self_authorizes": False,
            "caller_can_attest_priority_completeness": False,
            "can_create_issue": True,
            "can_create_route": True,
            "can_create_work_claim": True,
            "can_allocate_worker_slot": True,
            "can_begin_bounded_engineering": True,
            "can_merge_without_independent_accept": False,
            "can_deploy_production": False,
            "can_expand_permissions_or_secrets": False,
            "can_touch_trading_orders_or_funds": False,
            "can_perform_destructive_history_rewrite": False,
        },
        "independent_exact_head_review_required": True,
        "apply_requires_fresh_recheck": True,
    }
    value["authorization_id"] = f"r151-auto-release:{_digest(value)[:24]}"
    value["authorization_digest"] = _digest(value)
    return value


def intent(raw_opportunity: dict, lane_id: str = "LANE-A-HARNESS-INTEGRATION") -> dict:
    return {
        "schema_version": APPLY_INTENT_SCHEMA,
        "lane_id": lane_id,
        "route_epoch": 152,
        "release_reason_class": "NEW_GOVERNED_TASK",
        "requested_surface": copy.deepcopy(
            raw_opportunity["task_release_proposal"]["proposed_write_surface"]
        ),
        "resource_class": RESOURCE_CLASS,
        "reviewer_role": REVIEWER_ROLE,
        "reviewer_separation": REVIEWER_SEPARATION,
        "operation_plan": list(AUTHORIZED_LOGICAL_PLAN),
    }


def trusted_bootstrap(manifest: dict) -> dict:
    value = {
        "schema_version": TRUSTED_BOOTSTRAP_SCHEMA,
        "repository": COORDINATOR_REPOSITORY,
        "issue": 500,
        "implementation_pr": 501,
        "branch": manifest["identity"]["branch"],
        "bootstrap_head": BOOTSTRAP,
        "bootstrap_parent_main": MAIN,
        "empty_commit_verified": True,
        "draft_pr_verified": True,
        "issue_markers_verified": True,
        "pr_markers_verified": True,
        "provider_metadata": [],
    }
    value["observation_digest"] = _digest(value)
    return value


def bootstrap_selectors(manifest: dict) -> dict:
    proof = trusted_bootstrap(manifest)
    return {
        "schema_version": BOOTSTRAP_EVIDENCE_SCHEMA,
        "issue": proof["issue"],
        "implementation_pr": proof["implementation_pr"],
        "branch": proof["branch"],
        "bootstrap_head": proof["bootstrap_head"],
    }


def applied_selectors(manifest: dict) -> dict:
    bootstrap = manifest["trusted_bootstrap_observation"]
    return {
        "schema_version": APPLIED_STATE_SCHEMA,
        "activation_gate_pr": 502,
        "activation_gate_reviewed_head": REVIEWED,
        "activation_gate_merge_commit": MERGE,
        "issue": bootstrap["issue"],
        "implementation_pr": bootstrap["implementation_pr"],
        "branch": bootstrap["branch"],
    }


def acceptance() -> dict:
    value = {
        "queue_issue": 453,
        "pr": 502,
        "reviewed_head": REVIEWED,
        "verdict": "ACCEPT",
        "review_channel": "EXACT_HEAD_COMMENT_ATTESTATION",
        "reviewer_agent_id": REVIEWER_ROLE,
        "independence_attestation": INDEPENDENCE_ATTESTATION,
        "queue_result_comment_id": 7002,
        "queue_result_ref": "https://github.com/example/issues/453#issuecomment-7002",
        "review_evidence_ref": "pullrequestreview-9001",
        "review_submission_id": 9001,
        "review_submission_state": "COMMENTED",
        "queue_refs": ["fixture://request", "fixture://result"],
    }
    value["acceptance_digest"] = _digest(value)
    return value


def trusted_post_apply(manifest: dict) -> dict:
    selectors = applied_selectors(manifest)
    value = {
        "schema_version": TRUSTED_APPLIED_STATE_SCHEMA,
        "base_main_before_activation": MAIN,
        "activation_gate_pr": selectors["activation_gate_pr"],
        "activation_gate_reviewed_head": REVIEWED,
        "activation_gate_merge_commit": MERGE,
        "current_main_after_activation": MERGE,
        "merge_parents": [MAIN, REVIEWED],
        "independent_review_acceptance": acceptance(),
        "activation_changed_paths": sorted(manifest["activation_gate"]["exact_changed_paths"]),
        "implementation_issue": selectors["issue"],
        "implementation_pr": selectors["implementation_pr"],
        "branch": selectors["branch"],
        "implementation_head_still_bootstrap": True,
        "route_readback_verified": True,
        "full_claims_document_readback_verified": True,
        "full_worker_registry_readback_verified": True,
        "provider_metadata": [],
    }
    value["observation_digest"] = _digest(value)
    return value


def yaml_blob(value: dict) -> dict:
    raw = yaml.safe_dump(value, sort_keys=False, allow_unicode=True).encode("utf-8")
    return {"encoding": "base64", "content": b64encode(raw).decode("ascii")}


class IdleSignalApplyTests(unittest.TestCase):
    def prepare(
        self,
        raw_opportunity: dict | None = None,
        *,
        auth: dict | None = None,
        apply_intent: dict | None = None,
        bootstrap: dict | None = None,
        fresh_error: IdleSignalApplyError | None = None,
        next_epoch: int = 152,
    ) -> dict:
        raw_opportunity = copy.deepcopy(raw_opportunity or opportunity())
        auth = copy.deepcopy(auth or authorization(raw_opportunity))
        apply_intent = copy.deepcopy(apply_intent or intent(raw_opportunity))
        fresh_patch = (
            patch("idle_signal_apply._fresh_authorization", side_effect=fresh_error)
            if fresh_error
            else patch("idle_signal_apply._fresh_authorization", return_value=auth)
        )
        bootstrap_manifest = None
        if bootstrap is not None:
            bootstrap_manifest = {
                "identity": _authorization_identity(auth, next_epoch)
            }
        trusted_bootstrap_value = (
            trusted_bootstrap(bootstrap_manifest) if bootstrap_manifest else None
        )
        with (
            patch("idle_signal_apply._git_head", return_value=MAIN),
            patch("idle_signal_apply._next_route_epoch", return_value=next_epoch),
            fresh_patch,
            patch(
                "idle_signal_apply._trusted_bootstrap_observation",
                return_value=trusted_bootstrap_value,
            ),
        ):
            return prepare_apply_transaction(
                REPO_ROOT,
                raw_opportunity,
                hints(),
                auth,
                apply_intent,
                expected_current_main=MAIN,
                bootstrap_evidence=bootstrap,
            )

    def activation(self) -> dict:
        raw = opportunity()
        auth = authorization(raw)
        first = self.prepare(raw, auth=auth)
        return self.prepare(raw, auth=auth, bootstrap=bootstrap_selectors(first))

    def test_01_main_drift_invalidates_authorization(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        with patch("idle_signal_apply._git_head", return_value="9" * 40):
            with self.assertRaisesRegex(IdleSignalApplyError, "CURRENT_MAIN_DRIFT"):
                prepare_apply_transaction(
                    REPO_ROOT,
                    raw,
                    hints(),
                    auth,
                    intent(raw),
                    expected_current_main=MAIN,
                )

    def test_02_new_p1_or_p2_after_scheduling_blocks_fresh_apply(self) -> None:
        with self.assertRaisesRegex(IdleSignalApplyError, "R151_FRESH_REPLAY_NOT_AUTHORIZED"):
            self.prepare(
                fresh_error=IdleSignalApplyError(
                    "R151_FRESH_REPLAY_NOT_AUTHORIZED:HIGHER_PRIORITY_OR_ACTIVE_WORK_PRESENT"
                )
            )

    def test_03_forged_authorization_digest_fails(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        auth["authorization_digest"] = "0" * 64
        with self.assertRaisesRegex(IdleSignalApplyError, "DIGEST_FORGED"):
            self.prepare(raw, auth=auth)

    def test_04_authorization_from_other_opportunity_fails(self) -> None:
        raw = opportunity()
        other = opportunity("OTHER-OPP")
        with self.assertRaisesRegex(IdleSignalApplyError, "OPPORTUNITY_ID_MISMATCH"):
            self.prepare(raw, auth=authorization(other))

    def test_05_write_path_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["write_paths"].append(
            "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        )
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_06_write_domain_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["write_domains"].append("W3_MEMORY")
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_07_authority_claim_expansion_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["authority_claims"].append(
            "SECOND_TASK_AUTHORITY"
        )
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_08_interface_mutation_fails(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["requested_surface"]["interfaces"][0]["mode"] = "write"
        with self.assertRaisesRegex(IdleSignalApplyError, "SURFACE_EXPANSION_OR_DRIFT"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_09_route_epoch_is_not_caller_reusable(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw)
        apply_intent["route_epoch"] = 151
        with self.assertRaisesRegex(IdleSignalApplyError, "ROUTE_EPOCH_NOT_NEXT_CANONICAL"):
            self.prepare(raw, apply_intent=apply_intent, next_epoch=152)

    def test_10_next_route_epoch_is_derived_from_canonical_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routes = root / "coordination/ROUTES"
            routes.mkdir(parents=True)
            (routes / "a.yaml").write_text("route_epoch: 145\n", encoding="utf-8")
            (routes / "b.yaml").write_text(
                "binding:\n  route_epoch: 147\n", encoding="utf-8"
            )
            self.assertEqual(_next_route_epoch(root), 148)

    def test_11_ambiguous_route_epoch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            routes = root / "coordination/ROUTES"
            routes.mkdir(parents=True)
            (routes / "bad.yaml").write_text(
                "route_epoch: 145\nbinding:\n  route_epoch: 146\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(IdleSignalApplyError, "ROUTE_EPOCH_AMBIGUOUS"):
                _next_route_epoch(root)

    def test_12_old_self_attested_bootstrap_truth_fields_are_rejected(self) -> None:
        value = {
            "schema_version": BOOTSTRAP_EVIDENCE_SCHEMA,
            "issue": 500,
            "implementation_pr": 501,
            "branch": "gpt/x",
            "bootstrap_head": BOOTSTRAP,
            "draft": True,
            "empty_bootstrap_commit": True,
            "file_mutations": [],
        }
        with self.assertRaisesRegex(IdleSignalApplyError, "BOOTSTRAP_EVIDENCE_FIELDS_INVALID"):
            validate_bootstrap_evidence(value)

    def test_13_valid_bootstrap_manifest_is_deterministic_and_non_executable(self) -> None:
        first = self.prepare()
        second = self.prepare()
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], BOOTSTRAP_MANIFEST_SCHEMA)
        self.assertEqual(first["runtime_pr_bootstrap"]["file_mutations"], [])
        self.assertTrue(first["trusted_bootstrap_readback_required"])
        self.assertFalse(first["authority_boundary"]["execution_authority_granted"])

    def test_14_lane_c_ordinary_improvement_cannot_bypass_reopen_rule(self) -> None:
        raw = opportunity()
        apply_intent = intent(raw, "LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP")
        with self.assertRaisesRegex(IdleSignalApplyError, "LANE_REOPEN_REASON_NOT_AUTHORIZED"):
            self.prepare(raw, apply_intent=apply_intent)

    def test_15_existing_active_claim_or_slot_blocks_duplicate_apply(self) -> None:
        raw = opportunity()
        auth = authorization(raw)
        with (
            patch("idle_signal_apply._git_head", return_value=MAIN),
            patch("idle_signal_apply._next_route_epoch", return_value=152),
            patch("idle_signal_apply._fresh_authorization", return_value=auth),
            patch(
                "idle_signal_apply._assert_no_existing_live_control_state",
                side_effect=IdleSignalApplyError("EXISTING_ACTIVE_OR_RESERVED_CLAIM"),
            ),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "EXISTING_ACTIVE"):
                prepare_apply_transaction(
                    REPO_ROOT,
                    raw,
                    hints(),
                    auth,
                    intent(raw),
                    expected_current_main=MAIN,
                )

    def test_16_partial_or_reordered_operation_plan_fails(self) -> None:
        raw = opportunity()
        partial = intent(raw)
        partial["operation_plan"] = partial["operation_plan"][:-1]
        with self.assertRaisesRegex(IdleSignalApplyError, "OPERATION_PLAN_INVALID"):
            self.prepare(raw, apply_intent=partial)
        reordered = intent(raw)
        reordered["operation_plan"][1:3] = reversed(reordered["operation_plan"][1:3])
        with self.assertRaisesRegex(IdleSignalApplyError, "OPERATION_PLAN_INVALID"):
            self.prepare(raw, apply_intent=reordered)

    def test_17_excluded_high_risk_side_effect_fails(self) -> None:
        p = proposal()
        p["risk"] = ["production deploy"]
        raw = opportunity(release_proposal=p)
        with self.assertRaisesRegex(IdleSignalApplyError, "EXCLUDED_SIDE_EFFECT_REQUESTED"):
            self.prepare(raw)

    def test_18_valid_activation_manifest_binds_full_control_documents(self) -> None:
        manifest = self.activation()
        self.assertEqual(manifest["schema_version"], ACTIVATION_MANIFEST_SCHEMA)
        self.assertEqual(len(manifest["activation_gate"]["exact_changed_paths"]), 3)
        self.assertTrue(manifest["atomic_control_plane_commit_required"])
        self.assertTrue(manifest["partial_apply_forbidden"])
        self.assertIn("expected_document", manifest["control_plane_documents"]["claims"])
        self.assertIn("expected_document", manifest["control_plane_documents"]["workers"])
        self.assertFalse(manifest["authority_boundary"]["execution_authority_granted_by_manifest"])

    def test_19_bootstrap_branch_is_not_caller_replaceable(self) -> None:
        first = self.prepare()
        selectors = bootstrap_selectors(first)
        selectors["branch"] = "gpt/attacker"
        with self.assertRaisesRegex(IdleSignalApplyError, "BOOTSTRAP_BRANCH_MISMATCH"):
            self.prepare(bootstrap=selectors)

    def _bootstrap_fake(self, *, mutate: callable | None = None):
        raw = opportunity()
        auth = authorization(raw)
        identity = _authorization_identity(auth, 152)
        markers = _required_bootstrap_markers(auth, validate_opportunity(raw), identity)
        marker_text = "\n".join(f"{k}: {v}" for k, v in markers.items())
        branch = identity["branch"]
        tree_sha = "1" * 40
        responses = {
            f"/repos/{COORDINATOR_REPOSITORY}/issues/500": {
                "number": 500,
                "state": "open",
                "body": marker_text,
            },
            f"/repos/{COORDINATOR_REPOSITORY}/pulls/501": {
                "number": 501,
                "state": "open",
                "draft": True,
                "merged": False,
                "body": f"{marker_text}\nCloses #500",
                "base": {"ref": "main", "repo": {"full_name": COORDINATOR_REPOSITORY}},
                "head": {
                    "ref": branch,
                    "sha": BOOTSTRAP,
                    "repo": {"full_name": COORDINATOR_REPOSITORY},
                },
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{BOOTSTRAP}": {
                "tree": {"sha": tree_sha},
                "parents": [{"sha": MAIN}],
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{MAIN}": {
                "tree": {"sha": tree_sha},
                "parents": [],
            },
        }
        if mutate:
            mutate(responses)
        selectors = {
            "schema_version": BOOTSTRAP_EVIDENCE_SCHEMA,
            "issue": 500,
            "implementation_pr": 501,
            "branch": branch,
            "bootstrap_head": BOOTSTRAP,
        }
        return raw, auth, identity, selectors, responses

    def test_20_trusted_bootstrap_readback_proves_draft_empty_commit(self) -> None:
        raw, auth, identity, selectors, responses = self._bootstrap_fake()
        fake = FakeObserver(responses)
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            result = _trusted_bootstrap_observation(
                REPO_ROOT, selectors, auth, validate_opportunity(raw), identity
            )
        self.assertTrue(result["empty_commit_verified"])
        self.assertTrue(result["draft_pr_verified"])

    def test_21_nonempty_bootstrap_commit_fails_trusted_readback(self) -> None:
        def mutate(responses):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{BOOTSTRAP}"]["tree"]["sha"] = "2" * 40

        raw, auth, identity, selectors, responses = self._bootstrap_fake(mutate=mutate)
        fake = FakeObserver(responses)
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            with self.assertRaisesRegex(IdleSignalApplyError, "COMMIT_NOT_EMPTY"):
                _trusted_bootstrap_observation(
                    REPO_ROOT, selectors, auth, validate_opportunity(raw), identity
                )

    def test_22_bootstrap_wrong_parent_main_fails(self) -> None:
        def mutate(responses):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{BOOTSTRAP}"]["parents"] = [{"sha": "9" * 40}]

        raw, auth, identity, selectors, responses = self._bootstrap_fake(mutate=mutate)
        fake = FakeObserver(responses)
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            with self.assertRaisesRegex(IdleSignalApplyError, "PARENT_MAIN_MISMATCH"):
                _trusted_bootstrap_observation(
                    REPO_ROOT, selectors, auth, validate_opportunity(raw), identity
                )

    def test_23_bootstrap_not_draft_or_marker_mismatch_fails(self) -> None:
        def mutate(responses):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/pulls/501"]["draft"] = False

        raw, auth, identity, selectors, responses = self._bootstrap_fake(mutate=mutate)
        fake = FakeObserver(responses)
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            with self.assertRaisesRegex(IdleSignalApplyError, "PR_IDENTITY_INVALID"):
                _trusted_bootstrap_observation(
                    REPO_ROOT, selectors, auth, validate_opportunity(raw), identity
                )

    def _review_fake(self, *, mutate: callable | None = None):
        request = {
            "id": 7001,
            "html_url": "fixture://request",
            "body": (
                "schema: REVIEW_REQUEST/v1\nproject: SECOND_BRAIN\npr: 502\n"
                f"exact_head: {REVIEWED}\nstatus: WAITING_REVIEW\n"
            ),
        }
        result = {
            "id": 7002,
            "html_url": "fixture://result",
            "body": (
                "schema: REVIEW_RESULT/v1\nproject: SECOND_BRAIN\npr: 502\n"
                f"reviewed_head: {REVIEWED}\nverdict: ACCEPT\n"
                "review_evidence_ref: pullrequestreview-9001\n"
                "review_channel: EXACT_HEAD_COMMENT_ATTESTATION\n"
                f"reviewer_agent_id: {REVIEWER_ROLE}\n"
                f"independence_attestation: {INDEPENDENCE_ATTESTATION}\n"
            ),
        }
        reviews = [{"id": 9001, "commit_id": REVIEWED, "state": "COMMENTED"}]
        responses = {
            f"/repos/{COORDINATOR_REPOSITORY}/issues/453/comments?per_page=100&page=1": [request, result],
            f"/repos/{COORDINATOR_REPOSITORY}/pulls/502/reviews?per_page=100&page=1": reviews,
        }
        if mutate:
            mutate(responses)
        return responses

    def test_24_queue_accept_requires_matching_exact_head_pr_review(self) -> None:
        fake = FakeObserver(self._review_fake())
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            result = _trusted_exact_head_acceptance(REPO_ROOT, 502, REVIEWED)
        self.assertEqual(result["verdict"], "ACCEPT")
        self.assertEqual(result["review_submission_state"], "COMMENTED")

    def test_25_queue_accept_without_independence_attestation_fails(self) -> None:
        def mutate(responses):
            result = responses[f"/repos/{COORDINATOR_REPOSITORY}/issues/453/comments?per_page=100&page=1"][1]
            result["body"] = result["body"].replace(
                f"independence_attestation: {INDEPENDENCE_ATTESTATION}\n", ""
            )

        fake = FakeObserver(self._review_fake(mutate=mutate))
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            with self.assertRaisesRegex(IdleSignalApplyError, "INDEPENDENCE_ATTESTATION_INVALID"):
                _trusted_exact_head_acceptance(REPO_ROOT, 502, REVIEWED)

    def test_26_queue_accept_with_no_matching_pr_review_fails(self) -> None:
        def mutate(responses):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/pulls/502/reviews?per_page=100&page=1"][0]["commit_id"] = "9" * 40

        fake = FakeObserver(self._review_fake(mutate=mutate))
        with patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)):
            with self.assertRaisesRegex(IdleSignalApplyError, "REVIEW_EVIDENCE_MISMATCH"):
                _trusted_exact_head_acceptance(REPO_ROOT, 502, REVIEWED)

    def _post_apply_fake(self, manifest: dict, *, mutate: callable | None = None):
        route_path = manifest["route_artifact"]["path"]
        base_tree_sha = "2" * 40
        reviewed_tree_sha = "3" * 40
        route_blob = "7" * 40
        claims_blob = "8" * 40
        workers_blob = "9" * 40
        base_entries = [
            {"path": CLAIMS_FILE, "sha": "4" * 40, "type": "blob", "mode": "100644"},
            {"path": GPT_WORKERS_REGISTRY, "sha": "5" * 40, "type": "blob", "mode": "100644"},
        ]
        reviewed_entries = [
            {"path": route_path, "sha": route_blob, "type": "blob", "mode": "100644"},
            {"path": CLAIMS_FILE, "sha": claims_blob, "type": "blob", "mode": "100644"},
            {"path": GPT_WORKERS_REGISTRY, "sha": workers_blob, "type": "blob", "mode": "100644"},
        ]
        branch = manifest["trusted_bootstrap_observation"]["branch"]
        responses = {
            f"/repos/{COORDINATOR_REPOSITORY}/git/ref/heads/main": {"object": {"sha": MERGE}},
            f"/repos/{COORDINATOR_REPOSITORY}/pulls/502": {
                "number": 502,
                "state": "closed",
                "merged": True,
                "draft": False,
                "merge_commit_sha": MERGE,
                "base": {"ref": "main"},
                "head": {"sha": REVIEWED, "repo": {"full_name": COORDINATOR_REPOSITORY}},
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{MERGE}": {
                "tree": {"sha": reviewed_tree_sha},
                "parents": [{"sha": MAIN}, {"sha": REVIEWED}],
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{MAIN}": {
                "tree": {"sha": base_tree_sha},
                "parents": [],
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{REVIEWED}": {
                "tree": {"sha": reviewed_tree_sha},
                "parents": [{"sha": MAIN}],
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/trees/{base_tree_sha}?recursive=1": {
                "truncated": False,
                "tree": base_entries,
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/trees/{reviewed_tree_sha}?recursive=1": {
                "truncated": False,
                "tree": reviewed_entries,
            },
            f"/repos/{COORDINATOR_REPOSITORY}/pulls/501": {
                "number": 501,
                "state": "open",
                "draft": True,
                "merged": False,
                "head": {"ref": branch, "sha": BOOTSTRAP},
            },
            f"/repos/{COORDINATOR_REPOSITORY}/git/blobs/{route_blob}": yaml_blob(
                manifest["route_artifact"]["payload"]
            ),
            f"/repos/{COORDINATOR_REPOSITORY}/git/blobs/{claims_blob}": yaml_blob(
                manifest["control_plane_documents"]["claims"]["expected_document"]
            ),
            f"/repos/{COORDINATOR_REPOSITORY}/git/blobs/{workers_blob}": yaml_blob(
                manifest["control_plane_documents"]["workers"]["expected_document"]
            ),
        }
        if mutate:
            mutate(responses, reviewed_entries, route_blob, claims_blob, workers_blob)
        return responses

    def test_27_valid_post_apply_trusted_readback_verifies_atomic_state(self) -> None:
        manifest = self.activation()
        fake = FakeObserver(self._post_apply_fake(manifest))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            trusted = _trusted_post_apply_observation(
                REPO_ROOT, manifest, applied_selectors(manifest)
            )
        self.assertEqual(trusted["current_main_after_activation"], MERGE)
        self.assertTrue(trusted["full_claims_document_readback_verified"])

    def test_28_current_main_must_equal_activation_merge_commit(self) -> None:
        manifest = self.activation()
        def mutate(responses, *_):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/ref/heads/main"]["object"]["sha"] = "6" * 40
        fake = FakeObserver(self._post_apply_fake(manifest, mutate=mutate))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "CURRENT_MAIN_MISMATCH"):
                _trusted_post_apply_observation(REPO_ROOT, manifest, applied_selectors(manifest))

    def test_29_merge_parent_2_must_be_reviewed_head(self) -> None:
        manifest = self.activation()
        def mutate(responses, *_):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/commits/{MERGE}"]["parents"][1]["sha"] = "6" * 40
        fake = FakeObserver(self._post_apply_fake(manifest, mutate=mutate))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "MERGE_PARENT_BINDING_INVALID"):
                _trusted_post_apply_observation(REPO_ROOT, manifest, applied_selectors(manifest))

    def test_30_activation_gate_extra_fourth_path_fails(self) -> None:
        manifest = self.activation()
        def mutate(responses, reviewed_entries, *_):
            reviewed_entries.append(
                {"path": "coordination/ATTACK.yaml", "sha": "6" * 40, "type": "blob", "mode": "100644"}
            )
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/trees/{'3' * 40}?recursive=1"]["tree"] = reviewed_entries
        fake = FakeObserver(self._post_apply_fake(manifest, mutate=mutate))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "CHANGED_PATH_SET_MISMATCH"):
                _trusted_post_apply_observation(REPO_ROOT, manifest, applied_selectors(manifest))

    def test_31_same_claims_file_collateral_mutation_fails_full_document_readback(self) -> None:
        manifest = self.activation()
        def mutate(responses, _entries, _route_blob, claims_blob, _workers_blob):
            attacked = copy.deepcopy(
                manifest["control_plane_documents"]["claims"]["expected_document"]
            )
            attacked["owner"] = "ATTACKER"
            responses[f"/repos/{COORDINATOR_REPOSITORY}/git/blobs/{claims_blob}"] = yaml_blob(attacked)
        fake = FakeObserver(self._post_apply_fake(manifest, mutate=mutate))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "CLAIMS_FULL_DOCUMENT_MISMATCH"):
                _trusted_post_apply_observation(REPO_ROOT, manifest, applied_selectors(manifest))

    def test_32_implementation_pr_must_still_be_at_empty_bootstrap_head(self) -> None:
        manifest = self.activation()
        def mutate(responses, *_):
            responses[f"/repos/{COORDINATOR_REPOSITORY}/pulls/501"]["head"]["sha"] = "6" * 40
        fake = FakeObserver(self._post_apply_fake(manifest, mutate=mutate))
        with (
            patch("idle_signal_apply._make_apply_observer", return_value=(fake, FakeGatewayError)),
            patch("idle_signal_apply._trusted_exact_head_acceptance", return_value=acceptance()),
        ):
            with self.assertRaisesRegex(IdleSignalApplyError, "IMPLEMENTATION_PR_DRIFT"):
                _trusted_post_apply_observation(REPO_ROOT, manifest, applied_selectors(manifest))

    def test_33_applied_selector_issue_or_branch_drift_fails_before_readback(self) -> None:
        manifest = self.activation()
        selectors = applied_selectors(manifest)
        selectors["issue"] += 1
        with self.assertRaisesRegex(IdleSignalApplyError, "APPLIED_IDENTITY_MISMATCH"):
            verify_applied_state(REPO_ROOT, manifest, selectors)

    def test_34_valid_receipt_is_trusted_and_evidence_only(self) -> None:
        manifest = self.activation()
        trusted = trusted_post_apply(manifest)
        with patch("idle_signal_apply._trusted_post_apply_observation", return_value=trusted):
            receipt = verify_applied_state(
                REPO_ROOT, manifest, applied_selectors(manifest)
            )
        self.assertEqual(receipt["schema_version"], APPLY_RECEIPT_SCHEMA)
        self.assertEqual(receipt["current_main_after_activation"], MERGE)
        self.assertTrue(receipt["verification"]["exact_head_independent_accept_verified"])
        self.assertTrue(receipt["authority_boundary"]["evidence_only"])
        self.assertFalse(receipt["authority_boundary"]["grants_execution_authority"])
        self.assertFalse(receipt["authority_boundary"]["grants_merge_authority"])
        self.assertFalse(receipt["authority_boundary"]["grants_production_deploy"])
        self.assertFalse(receipt["authority_boundary"]["grants_secrets_or_permission_expansion"])
        self.assertFalse(receipt["authority_boundary"]["grants_trading_order_or_fund_access"])
        self.assertFalse(receipt["authority_boundary"]["grants_destructive_history_rewrite"])


if __name__ == "__main__":
    unittest.main()
