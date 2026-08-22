"""R145 G1-G4 adversarial controls for owner-domain routing isolation."""
from __future__ import annotations

import inspect
from pathlib import Path
import tempfile
import unittest

import global_signal_gateway.domain_authority as domain_authority_module
from global_signal_gateway.domain_authority import (
    DomainAuthorityDescriptor,
    DomainAuthorityError,
    DomainAuthorityObservation,
    DomainAuthorityResolver,
    deterministic_domain_evidence_receipt,
    evaluate_signal_task_route_domain_guard,
    project_cross_domain_relation,
)
from global_signal_gateway.retrospective_intake import reconcile_package
from global_signal_plane.ledger import DurableSignalLedger
import test_r142_retrospective_intake as legacy


SECOND_REPO = "vxz2datoubo/second-brain-coordination"
FILM_REPO = "vxz2datoubo/eustia-ai-film"
WORLD_REPO = "vxz2datoubo/ai-world-simulation-engine"
FILM_COMMIT = "1" * 40
WORLD_COMMIT = "2" * 40
A_SHARE_COMMIT = "3" * 40
FIFTH_COMMIT = "4" * 40
OBSERVED_AT = "2026-08-23T02:00:00+08:00"


def descriptor(domain_id, project_id, repository, commit, authority_path, *, owner=None, visibility="PUBLIC_OR_METADATA_ONLY"):
    return {
        "domain_id": domain_id,
        "project_id": project_id,
        "repository": repository,
        "canonical_ref_kind": "CANONICAL_MAIN",
        "canonical_commit": commit,
        "authority_path_or_contract_ref": authority_path,
        "authority_schema_version": f"{project_id}/v1",
        "writeback_owner": owner or domain_id,
        "observation_mode": "READ_ONLY_METADATA_ONLY" if repository != SECOND_REPO else "READ_ONLY",
        "repository_visibility": visibility,
    }


def observation(desc, *, source_kind="CANONICAL_MAIN", commit=None, repository=None, project_id=None, suffix="a"):
    return {
        "domain_id": desc["domain_id"],
        "project_id": project_id or desc["project_id"],
        "repository": repository or desc["repository"],
        "canonical_ref_kind": desc["canonical_ref_kind"],
        "canonical_commit": commit or desc["canonical_commit"],
        "authority_path_or_contract_ref": desc["authority_path_or_contract_ref"],
        "authority_blob_sha": suffix * 40,
        "authority_content_sha256": suffix * 64,
        "authority_schema_version": desc["authority_schema_version"],
        "observation_mode": desc["observation_mode"],
        "source_kind": source_kind,
        "observed_at": OBSERVED_AT,
        "evidence_refs": [f"opaque://domain-evidence/{desc['domain_id']}/{suffix}"],
        "repository_visibility": desc.get("repository_visibility", "PUBLIC_OR_METADATA_ONLY"),
    }


def opaque_ref(obs):
    return DomainAuthorityObservation.from_mapping(obs).opaque_ref()


def explicit_snapshot(cand, descs, observations, ev):
    snap = legacy.caller_snapshot({cand["candidate_id"]: ev})
    snap["domain_authority_descriptors"] = descs
    snap["domain_authority_observations"] = observations
    return snap


def candidate_for(domain_id, candidate_id="R145-X", **overrides):
    return legacy.candidate(candidate_id, proposed_primary_domain=domain_id, **overrides)


def decision(cand, descs, observations, ev):
    snap = explicit_snapshot(cand, descs, observations, ev)
    return reconcile_package(
        legacy.package(cand, batch_id=f"BATCH-{cand['candidate_id']}"),
        snap,
        expected_canonical_main=legacy.MAIN,
    )["results"][0]


class DomainOwnershipIsolationTests(unittest.TestCase):
    def setUp(self):
        self.film = descriptor("AI_FILM_SYSTEM", "EUSTIA_AI_FILM", FILM_REPO, FILM_COMMIT, "PROJECT_INDEX.yaml")
        self.film_obs = observation(self.film, suffix="a")
        self.world = descriptor(
            "WORLD_MODEL_SYSTEM", "AWRSE", WORLD_REPO, WORLD_COMMIT, "ARCHITECTURE.md",
            visibility="PRIVATE",
        )
        self.world_obs = observation(self.world, suffix="b")

    def test_01_ai_film_absent_from_second_brain_is_not_second_brain_gap(self):
        cand = candidate_for("AI_FILM_SYSTEM", "R145-01")
        result = decision(cand, [self.film], [], legacy.evidence())
        self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
        self.assertEqual("DOMAIN_AUTHORITY_UNAVAILABLE", result["reason"])
        self.assertNotEqual("NEW_DURABLE_SIGNAL", result["disposition"])

    def test_02_ai_film_canonical_satisfaction_wins_without_second_brain_feature(self):
        cand = candidate_for("AI_FILM_SYSTEM", "R145-02")
        ref = opaque_ref(self.film_obs)
        ev = legacy.evidence(
            satisfied_refs=[ref], desired_effect_unmet=False,
            authority_domain_id="AI_FILM_SYSTEM", authority_evidence_refs=[ref],
        )
        result = decision(cand, [self.film], [self.film_obs], ev)
        self.assertEqual("ALREADY_SATISFIED", result["disposition"])
        self.assertIn(ref, result["authority_evidence_refs"])

    def test_03_ai_film_authority_unavailable_never_falls_back(self):
        cand = candidate_for("AI_FILM_SYSTEM", "R145-03")
        result = decision(cand, [self.film], [], legacy.evidence())
        self.assertEqual(("NEEDS_REVALIDATION", "DOMAIN_AUTHORITY_UNAVAILABLE"), (result["disposition"], result["reason"]))

    def test_04_same_repository_a_share_and_second_brain_remain_distinct(self):
        brain = descriptor("SECOND_BRAIN_SYSTEM", "SECOND_BRAIN", SECOND_REPO, A_SHARE_COMMIT, "coordination/PROGRAM-CONTROL-TOWER.md")
        share = descriptor("A_SHARE_SYSTEM", "A_SHARE", SECOND_REPO, A_SHARE_COMMIT, "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE.md")
        brain_obs = observation(brain, suffix="c")
        share_obs = observation(share, suffix="d")
        resolver = DomainAuthorityResolver([brain, share])
        brain_result = resolver.resolve("SECOND_BRAIN_SYSTEM", [brain_obs, share_obs])
        share_result = resolver.resolve("A_SHARE_SYSTEM", [brain_obs, share_obs])
        self.assertTrue(brain_result["valid"] and share_result["valid"])
        self.assertNotEqual(brain_result["project_id"], share_result["project_id"])
        self.assertNotEqual(brain_result["authority_refs"], share_result["authority_refs"])

    def test_05_world_model_absent_from_second_brain_is_not_second_brain_gap(self):
        cand = candidate_for("WORLD_MODEL_SYSTEM", "R145-05")
        result = decision(cand, [self.world], [], legacy.evidence())
        self.assertEqual("DOMAIN_AUTHORITY_UNAVAILABLE", result["reason"])

    def test_06_world_model_canonical_wins_over_draft_candidate_evidence(self):
        draft = observation(self.world, source_kind="DRAFT_PR", commit="9" * 40, suffix="c")
        ref = opaque_ref(self.world_obs)
        ev = legacy.evidence(
            satisfied_refs=[ref], desired_effect_unmet=False,
            authority_domain_id="WORLD_MODEL_SYSTEM", authority_evidence_refs=[ref],
        )
        result = decision(candidate_for("WORLD_MODEL_SYSTEM", "R145-06"), [self.world], [draft, self.world_obs], ev)
        self.assertEqual("ALREADY_SATISFIED", result["disposition"])

    def test_07_world_model_canonical_drift_fails_closed(self):
        drifted = observation(self.world, commit="8" * 40, suffix="d")
        ev = legacy.evidence(
            authority_domain_id="WORLD_MODEL_SYSTEM",
            authority_evidence_refs=[opaque_ref(drifted)],
        )
        result = decision(candidate_for("WORLD_MODEL_SYSTEM", "R145-07"), [self.world], [drifted], ev)
        self.assertEqual(("NEEDS_REVALIDATION", "DOMAIN_CANONICAL_DRIFT"), (result["disposition"], result["reason"]))

    def test_08_unknown_future_domain_has_no_second_brain_default(self):
        cand = candidate_for("FUTURE_DOMAIN_X", "R145-08")
        result = decision(cand, [], [], legacy.evidence())
        self.assertEqual("DOMAIN_ROUTE_UNRESOLVED", result["reason"])

    def test_external_domain_true_new_requires_owner_and_local_admission_proofs(self):
        cand = candidate_for("AI_FILM_SYSTEM", "R145-NEW")
        ref = opaque_ref(self.film_obs)
        ev = legacy.evidence(
            authority_domain_id="AI_FILM_SYSTEM", authority_evidence_refs=[ref],
        )
        with tempfile.TemporaryDirectory() as directory, legacy.synthetic_governed_provider() as proof:
            ledger = DurableSignalLedger(Path(directory) / "ledger.sqlite")
            try:
                exacts = legacy.exact_current_reads("r145-external-new")
                snap = legacy.bound_snapshot(ledger, proof, exacts, {cand["candidate_id"]: ev})
                snap["domain_authority_descriptors"] = [self.film]
                snap["domain_authority_observations"] = [self.film_obs]
                result = reconcile_package(
                    legacy.package(cand, batch_id="R145-EXTERNAL-NEW"), snap,
                    expected_canonical_main=legacy.MAIN,
                    live_observation_proof=proof, exact_read_proofs=exacts, ledger=ledger,
                )["results"][0]
                self.assertEqual("NEW_DURABLE_SIGNAL", result["disposition"])
                self.assertIn(ref, result["authority_evidence_refs"])
            finally:
                ledger.close()


class ExtensibilityAndBindingTests(unittest.TestCase):
    def test_09_synthetic_fifth_domain_is_added_by_descriptor_only(self):
        fifth = descriptor("FUTURE_DOMAIN_5", "FIFTH_PROJECT", "vxz2datoubo/fifth-system", FIFTH_COMMIT, "AUTHORITY.yaml")
        fifth_obs = observation(fifth, suffix="e")
        result = DomainAuthorityResolver([fifth]).resolve("FUTURE_DOMAIN_5", [fifth_obs])
        self.assertTrue(result["valid"])
        self.assertEqual("FUTURE_DOMAIN_5", result["domain_id"])

    def test_10_two_domains_same_repo_different_authority_roots(self):
        one = descriptor("D1", "P1", SECOND_REPO, A_SHARE_COMMIT, "authority/one.yaml")
        two = descriptor("D2", "P2", SECOND_REPO, A_SHARE_COMMIT, "authority/two.yaml")
        resolver = DomainAuthorityResolver([one, two])
        first = resolver.resolve("D1", [observation(one, suffix="a")])
        second = resolver.resolve("D2", [observation(two, suffix="b")])
        self.assertTrue(first["valid"] and second["valid"])
        self.assertNotEqual(first["authority_refs"], second["authority_refs"])

    def test_11_repository_move_invalidates_old_observation_binding(self):
        moved = descriptor("D-MOVE", "P-MOVE", "vxz2datoubo/new-home", FIFTH_COMMIT, "AUTHORITY.yaml")
        old = observation(moved, repository="vxz2datoubo/old-home", suffix="c")
        result = DomainAuthorityResolver([moved]).resolve("D-MOVE", [old])
        self.assertFalse(result["valid"])
        self.assertEqual("DOMAIN_CANONICAL_DRIFT", result["reason"])
        self.assertIn("vxz2datoubo/old-home", opaque_ref(old))

    def test_project_identity_mismatch_fails_closed_even_when_repository_matches(self):
        desc = descriptor("D-PROJECT", "RIGHT", SECOND_REPO, A_SHARE_COMMIT, "AUTHORITY.yaml")
        wrong = observation(desc, project_id="WRONG", suffix="d")
        result = DomainAuthorityResolver([desc]).resolve("D-PROJECT", [wrong])
        self.assertEqual("DOMAIN_PROJECT_ID_MISMATCH", result["reason"])

    def test_noncanonical_source_only_fails_closed(self):
        desc = descriptor("D-DRAFT", "P-DRAFT", SECOND_REPO, A_SHARE_COMMIT, "AUTHORITY.yaml")
        draft = observation(desc, source_kind="DRAFT_PR", suffix="e")
        result = DomainAuthorityResolver([desc]).resolve("D-DRAFT", [draft])
        self.assertEqual("NON_CANONICAL_SOURCE_ONLY", result["reason"])


class CrossDomainPromotionAndTaskGuardTests(unittest.TestCase):
    def test_12_transferable_pattern_does_not_move_film_ownership(self):
        result = project_cross_domain_relation(
            relation="TRANSFERABLE_PATTERN_CANDIDATE",
            source_domain="AI_FILM_SYSTEM", related_domain="SECOND_BRAIN_SYSTEM",
            accepted_as_shared_capability=True,
        )
        self.assertTrue(result["shared_capability_candidate"])
        self.assertFalse(result["ownership_transferred"])
        self.assertFalse(result["write_permission_created"])

    def test_13_domain_specific_mechanism_may_be_rejected_as_shared_without_w3_effect(self):
        result = project_cross_domain_relation(
            relation="RELATED_TO", source_domain="AI_FILM_SYSTEM",
            related_domain="SECOND_BRAIN_SYSTEM", accepted_as_shared_capability=False,
        )
        self.assertFalse(result["shared_capability_candidate"])
        self.assertFalse(result["ownership_transferred"])

    def test_14_cross_domain_relation_never_creates_write_permission(self):
        for relation in ("RELATED_TO", "REINFORCES", "EXTENDS", "TRANSFERABLE_PATTERN_CANDIDATE", "CROSS_PROJECT_CAPABILITY_CANDIDATE"):
            with self.subTest(relation=relation):
                self.assertFalse(project_cross_domain_relation(
                    relation=relation, source_domain="AI_FILM_SYSTEM", related_domain="SECOND_BRAIN_SYSTEM"
                )["write_permission_created"])

    def test_15_ai_film_signal_to_second_brain_task_blocks_without_separate_governance(self):
        blocked = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="AI_FILM_SYSTEM", task_target_domain="SECOND_BRAIN_SYSTEM",
            route_authority_domain="SECOND_BRAIN_SYSTEM", writeback_owner_domain="SECOND_BRAIN_SYSTEM",
        )
        self.assertFalse(blocked["eligible_for_normal_release_gates"])
        allowed = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="AI_FILM_SYSTEM", task_target_domain="SECOND_BRAIN_SYSTEM",
            route_authority_domain="SECOND_BRAIN_SYSTEM", writeback_owner_domain="SECOND_BRAIN_SYSTEM",
            governed_cross_domain_task_ref="governed://cross-domain/task-1",
        )
        self.assertTrue(allowed["eligible_for_normal_release_gates"])
        self.assertFalse(allowed["automatic_task_created"])

    def test_16_world_model_signal_with_a_share_route_blocks(self):
        result = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="WORLD_MODEL_SYSTEM", task_target_domain="WORLD_MODEL_SYSTEM",
            route_authority_domain="A_SHARE_SYSTEM", writeback_owner_domain="A_SHARE_SYSTEM",
        )
        self.assertEqual((False, "DOMAIN_IDENTITY_MISMATCH_BLOCK"), (result["eligible_for_normal_release_gates"], result["reason"]))

    def test_17_a_share_identity_match_is_only_eligible_for_normal_release_gates(self):
        result = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="A_SHARE_SYSTEM", task_target_domain="A_SHARE_SYSTEM",
            route_authority_domain="A_SHARE_SYSTEM", writeback_owner_domain="A_SHARE_SYSTEM",
        )
        self.assertTrue(result["eligible_for_normal_release_gates"])
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["write_permission_created"])


class PrivacySafetyAndRetainedR142Tests(unittest.TestCase):
    def test_18_private_world_model_raw_body_is_structurally_forbidden(self):
        desc = descriptor("WORLD_MODEL_SYSTEM", "AWRSE", WORLD_REPO, WORLD_COMMIT, "ARCHITECTURE.md", visibility="PRIVATE")
        raw = observation(desc, suffix="f")
        raw["raw_source_body"] = "private material"
        with self.assertRaises(DomainAuthorityError) as got:
            DomainAuthorityObservation.from_mapping(raw)
        self.assertEqual("DOMAIN_AUTHORITY_PRIVATE_BODY_FORBIDDEN", got.exception.code)

    def test_19_cross_repo_mutation_apis_are_absent_from_domain_resolver(self):
        source = inspect.getsource(domain_authority_module)
        for forbidden in ("subprocess", "urllib", "requests.", "urlopen", "write_text(", "write_bytes("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_20_opaque_ref_binds_repository_commit_authority_and_hash_without_body(self):
        desc = descriptor("WORLD_MODEL_SYSTEM", "AWRSE", WORLD_REPO, WORLD_COMMIT, "ARCHITECTURE.md", visibility="PRIVATE")
        obs = observation(desc, suffix="a")
        ref = opaque_ref(obs)
        self.assertIn(WORLD_REPO, ref)
        self.assertIn(WORLD_COMMIT, ref)
        self.assertIn("ARCHITECTURE.md", ref)
        self.assertIn("blob=", ref)
        self.assertIn("sha256=", ref)
        self.assertNotIn("private material", ref)

    def test_21_r142_disposition_precedence_is_retained_inside_resolved_owner(self):
        desc = descriptor("D-R142", "P-R142", SECOND_REPO, A_SHARE_COMMIT, "AUTHORITY.yaml")
        obs = observation(desc, suffix="b")
        ref = opaque_ref(obs)
        cases = (
            ("superseded_refs", "SUPERSEDED"), ("contradicts_refs", "CONTRADICTS"),
            ("satisfied_refs", "ALREADY_SATISFIED"), ("current_signal_refs", "ALREADY_CANONICAL"),
            ("duplicate_refs", "DUPLICATE"), ("domain_canonical_refs", "DOMAIN_CANONICAL_ONLY"),
            ("needs_revalidation_refs", "NEEDS_REVALIDATION"), ("extends_refs", "EXTENDS"),
            ("reinforces_refs", "REINFORCES"),
        )
        for field, expected in cases:
            with self.subTest(field=field):
                cand = candidate_for("D-R142", f"R145-21-{field}")
                ev = legacy.evidence(
                    **{field: [ref]}, authority_domain_id="D-R142", authority_evidence_refs=[ref]
                )
                self.assertEqual(expected, decision(cand, [desc], [obs], ev)["disposition"])

    def test_22_historical_new_todo_not_implemented_never_supplies_current_authority(self):
        desc = descriptor("D-HIST", "P-HIST", SECOND_REPO, A_SHARE_COMMIT, "AUTHORITY.yaml")
        obs = observation(desc, suffix="c")
        ref = opaque_ref(obs)
        for status in ("NEW", "TODO", "NOT_IMPLEMENTED"):
            with self.subTest(status=status):
                cand = candidate_for("D-HIST", f"R145-22-{status}", historical_status=status)
                ev = legacy.evidence(
                    desired_effect_unmet=False,
                    authority_domain_id="D-HIST", authority_evidence_refs=[ref],
                )
                result = decision(cand, [desc], [obs], ev)
                self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
                self.assertEqual("NO_EVIDENCE_FOR_SAFE_ADMISSION", result["reason"])

    def test_23_stale_second_brain_snapshot_still_fails_closed(self):
        cand = legacy.candidate("R145-23")
        snap = legacy.caller_snapshot({cand["candidate_id"]: legacy.evidence()}, main="b" * 40)
        result = reconcile_package(
            legacy.package(cand, batch_id="R145-23"), snap,
            expected_canonical_main=legacy.MAIN,
        )["results"][0]
        self.assertEqual(("NEEDS_REVALIDATION", "STALE_CANONICAL_SNAPSHOT"), (result["disposition"], result["reason"]))

    def test_24_signal_remains_not_task(self):
        guard = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="SECOND_BRAIN_SYSTEM", task_target_domain="SECOND_BRAIN_SYSTEM",
            route_authority_domain="SECOND_BRAIN_SYSTEM", writeback_owner_domain="SECOND_BRAIN_SYSTEM",
        )
        self.assertFalse(guard["automatic_task_created"])
        self.assertFalse(guard["write_permission_created"])

    def test_deterministic_public_safe_evidence_receipt(self):
        desc = descriptor("D-EVIDENCE", "P-EVIDENCE", SECOND_REPO, A_SHARE_COMMIT, "AUTHORITY.yaml")
        obs = observation(desc, suffix="d")
        checks = {"G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS"}
        first = deterministic_domain_evidence_receipt(descriptors=[desc], observations=[obs], checks=checks)
        second = deterministic_domain_evidence_receipt(descriptors=[dict(reversed(list(desc.items())))], observations=[dict(reversed(list(obs.items())))], checks=dict(reversed(list(checks.items()))))
        self.assertEqual(first, second)
        self.assertFalse(first["private_body_persisted"])
        self.assertFalse(first["cross_repo_mutation_available"])
        self.assertFalse(first["automatic_task_created"])
        self.assertEqual(64, len(first["receipt_sha256"]))


if __name__ == "__main__":
    unittest.main()
