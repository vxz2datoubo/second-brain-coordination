"""R145 F01/F02 adversarial controls for owner-domain routing isolation."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import global_signal_gateway.domain_authority as domain_authority_module
import global_signal_gateway.gateway as gateway_module
from global_signal_gateway.domain_authority import (
    DomainAuthorityDescriptor,
    DomainAuthorityError,
    DomainAuthorityObservation,
    DomainAuthorityResolver,
    canonical_domain_freshness_ref,
    deterministic_domain_evidence_receipt,
    evaluate_signal_task_route_domain_guard,
    project_cross_domain_relation,
    trusted_exact_read_ref,
)
from global_signal_gateway.gateway import AuthorityBoundLiveObservationProof, GatewayError, exact_git_read_proofs
from global_signal_gateway.semantic_authority import (
    exact_semantic_authority_proof,
    governed_authority_source_ref,
    semantic_authority_ref,
)
from global_signal_gateway.retrospective_intake import reconcile_package
from global_signal_plane.ledger import DurableSignalLedger
import test_r142_retrospective_intake as legacy


SECOND_REPO = "vxz2datoubo/second-brain-coordination"
FILM_REPO = "vxz2datoubo/eustia-ai-film"
WORLD_REPO = "vxz2datoubo/ai-world-simulation-engine"
OBSERVED_AT = "2026-08-23T02:00:00+08:00"


def descriptor(
    domain_id: str,
    project_id: str,
    repository: str,
    commit: str,
    authority_path: str,
    *,
    owner: str | None = None,
    visibility: str = "PUBLIC_OR_METADATA_ONLY",
) -> dict[str, str]:
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


def observation(
    desc: dict[str, str],
    *,
    source_kind: str = "CANONICAL_MAIN",
    commit: str | None = None,
    repository: str | None = None,
    project_id: str | None = None,
    blob: str = "a" * 40,
    content_sha: str = "b" * 64,
    evidence_ref: str = "caller://untrusted/domain-observation",
) -> dict[str, object]:
    return {
        "domain_id": desc["domain_id"],
        "project_id": project_id or desc["project_id"],
        "repository": repository or desc["repository"],
        "canonical_ref_kind": desc["canonical_ref_kind"],
        "canonical_commit": commit or desc["canonical_commit"],
        "authority_path_or_contract_ref": desc["authority_path_or_contract_ref"],
        "authority_blob_sha": blob,
        "authority_content_sha256": content_sha,
        "authority_schema_version": desc["authority_schema_version"],
        "observation_mode": desc["observation_mode"],
        "source_kind": source_kind,
        "observed_at": OBSERVED_AT,
        "evidence_refs": [evidence_ref],
        "repository_visibility": desc.get("repository_visibility", "PUBLIC_OR_METADATA_ONLY"),
    }


def observation_from_proof(desc: dict[str, str], proof, *, evidence_ref: str = "caller://declared") -> dict[str, object]:
    return observation(
        desc,
        blob=proof.blob_sha,
        content_sha=proof.content_sha256,
        evidence_ref=evidence_ref,
    )


def explicit_snapshot(cand, descs, observations, ev):
    snap = legacy.caller_snapshot({cand["candidate_id"]: ev})
    snap["domain_authority_descriptors"] = descs
    snap["domain_authority_observations"] = observations
    return snap


def candidate_for(domain_id: str, candidate_id: str = "R145-X", **overrides):
    return legacy.candidate(candidate_id, proposed_primary_domain=domain_id, **overrides)


def git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


@contextmanager
def exact_authority(
    *,
    domain_id: str = "AI_FILM_SYSTEM",
    project_id: str = "EUSTIA_AI_FILM",
    repository: str = FILM_REPO,
    authority_path: str = "PROJECT_INDEX.yaml",
    visibility: str = "PUBLIC_OR_METADATA_ONLY",
):
    """Create a real Git object and seal semantics only after governed source attestation."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.check_call(["git", "init", "-q", str(root)])
        git("config", "user.email", "r145-tests@example.invalid", cwd=root)
        git("config", "user.name", "R145 Tests", cwd=root)
        target = root / authority_path
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "READ_ONLY_METADATA_ONLY" if repository != SECOND_REPO else "READ_ONLY"
        target.write_text(
            f"domain_id: {domain_id}\n"
            f"project_id: {project_id}\n"
            f"authority_schema_version: {project_id}/v1\n"
            f"writeback_owner: {domain_id}\n"
            f"observation_mode: {mode}\n"
            "source_authority: this_file\n",
            encoding="utf-8",
        )
        git("add", authority_path, cwd=root)
        subprocess.check_call(
            ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "authority fixture"]
        )
        commit = git("rev-parse", "HEAD", cwd=root)
        desc = descriptor(domain_id, project_id, repository, commit, authority_path, visibility=visibility)
        exact_source = exact_git_read_proofs(
            root,
            repository=repository,
            commit=commit,
            paths=(authority_path,),
            execution_id=f"r145-source-{domain_id.casefold()}",
        )[0]
        with governed_domain_provider(
            repository,
            commit,
            authority_proofs=(exact_source,),
        ) as governed_source:
            proof = exact_semantic_authority_proof(
                root,
                repository=repository,
                commit=commit,
                path=authority_path,
                execution_id=f"r145-domain-{domain_id.casefold()}",
                governed_source_proof=governed_source,
            )
        obs = observation_from_proof(desc, proof)
        yield root, desc, obs, proof


@contextmanager
def governed_domain_provider(repository: str, commit: str, *, authority_proofs=()):
    """Test-only sealed provider; optional exact refs attest governed authority sources."""
    provider_id = "test-only-r145-domain-provider"
    now = datetime.now(timezone.utc)
    bindings = {
        "head_sha": legacy.MAIN,
        "base_sha": legacy.MAIN,
        "current_main_sha": legacy.MAIN,
        "review_state_ref": "review-r145",
        "merged": False,
        "merge_commit_sha": None,
        "route_fingerprint": "route-r145",
        "claim_fingerprint": "claim-r145",
        "lane_fingerprint": "lane-r145",
        "lease_fingerprint": "lease-r145",
        "domain_freshness_ref": canonical_domain_freshness_ref(repository, commit),
        "pending_approval_ref": "approval-r145",
    }
    exact_refs = (
        "provider://synthetic/r145/pr",
        "provider://synthetic/r145/control-plane",
        *(governed_authority_source_ref(proof) for proof in authority_proofs),
    )
    observed_at = (now - timedelta(seconds=2)).isoformat()
    fresh_until = (now + timedelta(minutes=5)).isoformat()
    evidence_digest = gateway_module.digest({
        "provider": provider_id,
        "bindings": bindings,
        "exact_refs": exact_refs,
        "observed_at": observed_at,
        "fresh_until": fresh_until,
    })

    def verifier(proof, checked_at):
        del checked_at
        return (
            proof.evidence_digest == evidence_digest
            and proof.exact_refs == exact_refs
            and all(getattr(proof, field) == value for field, value in bindings.items())
        )

    prior = gateway_module._LIVE_OBSERVATION_VERIFIERS.get(provider_id)
    gateway_module._LIVE_OBSERVATION_VERIFIERS[provider_id] = verifier
    try:
        yield AuthorityBoundLiveObservationProof(
            SECOND_REPO,
            418,
            "open",
            bindings["head_sha"],
            bindings["base_sha"],
            bindings["current_main_sha"],
            bindings["merged"],
            bindings["merge_commit_sha"],
            bindings["review_state_ref"],
            observed_at,
            bindings["route_fingerprint"],
            bindings["claim_fingerprint"],
            bindings["lane_fingerprint"],
            bindings["lease_fingerprint"],
            bindings["domain_freshness_ref"],
            bindings["pending_approval_ref"],
            exact_refs,
            provider_id,
            "provider://synthetic/r145/attestation",
            evidence_digest,
            fresh_until,
            dict(bindings),
            gateway_module._LIVE_OBSERVATION_ISSUER_SEAL,
        )
    finally:
        if prior is None:
            gateway_module._LIVE_OBSERVATION_VERIFIERS.pop(provider_id, None)
        else:
            gateway_module._LIVE_OBSERVATION_VERIFIERS[provider_id] = prior


def resolve_verified(desc, obs, exact_proof, live_proof):
    return DomainAuthorityResolver([desc]).resolve(
        desc["domain_id"],
        [obs],
        exact_read_proofs=(exact_proof,),
        live_observation_proof=live_proof,
        expected_canonical_main=legacy.MAIN,
        coordinator_repository=SECOND_REPO,
    )


class DomainOwnershipIsolationTests(unittest.TestCase):
    def test_01_external_domain_absence_is_not_second_brain_gap(self):
        cand = candidate_for("AI_FILM_SYSTEM", "R145-01")
        desc = descriptor("AI_FILM_SYSTEM", "EUSTIA_AI_FILM", FILM_REPO, "1" * 40, "PROJECT_INDEX.yaml")
        snap = explicit_snapshot(cand, [desc], [], legacy.evidence())
        result = reconcile_package(legacy.package(cand), snap, expected_canonical_main=legacy.MAIN)["results"][0]
        self.assertEqual(("NEEDS_REVALIDATION", "DOMAIN_AUTHORITY_UNAVAILABLE"), (result["disposition"], result["reason"]))

    def test_02_fabricated_self_consistent_metadata_cannot_mint_authority(self):
        desc = descriptor("AI_FILM_SYSTEM", "EUSTIA_AI_FILM", FILM_REPO, "1" * 40, "PROJECT_INDEX.yaml")
        obs = observation(desc)
        result = DomainAuthorityResolver([desc]).resolve("AI_FILM_SYSTEM", [obs])
        self.assertFalse(result["valid"])
        self.assertEqual("DOMAIN_AUTHORITY_EXACT_READ_PROOF_REQUIRED", result["reason"])

    def test_02b_self_declared_semantics_without_governed_source_ref_cannot_mint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.check_call(["git", "init", "-q", str(root)])
            git("config", "user.email", "r145-tests@example.invalid", cwd=root)
            git("config", "user.name", "R145 Tests", cwd=root)
            path = "SELF_ASSERTED.yaml"
            (root / path).write_text(
                "domain_id: AI_FILM_SYSTEM\n"
                "project_id: EUSTIA_AI_FILM\n"
                "authority_schema_version: EUSTIA_AI_FILM/v1\n"
                "writeback_owner: AI_FILM_SYSTEM\n"
                "observation_mode: READ_ONLY_METADATA_ONLY\n"
                "source_authority: this_file\n",
                encoding="utf-8",
            )
            git("add", path, cwd=root)
            subprocess.check_call(
                ["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "self asserted"]
            )
            commit = git("rev-parse", "HEAD", cwd=root)
            with governed_domain_provider(FILM_REPO, commit) as live:
                with self.assertRaises(GatewayError) as got:
                    exact_semantic_authority_proof(
                        root,
                        repository=FILM_REPO,
                        commit=commit,
                        path=path,
                        execution_id="r145-self-asserted",
                        governed_source_proof=live,
                    )
        self.assertEqual("GOVERNED_AUTHORITY_SOURCE_UNVERIFIED", got.exception.code)

    def test_03_genuine_sealed_exact_read_plus_live_canonical_proof_binds(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            result = resolve_verified(desc, obs, exact_proof, live)
        self.assertTrue(result["valid"])
        self.assertEqual("DOMAIN_CANONICAL_AUTHORITY_BOUND", result["reason"])
        self.assertEqual([semantic_authority_ref(exact_proof)], result["trusted_authority_refs"])
        self.assertNotIn(obs["evidence_refs"][0], result["authority_refs"])

    def test_04_wrong_git_blob_fails_closed(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            wrong = dict(obs)
            wrong["authority_blob_sha"] = "f" * 40
            result = resolve_verified(desc, wrong, exact_proof, live)
        self.assertEqual("DOMAIN_AUTHORITY_EXACT_READ_PROOF_REQUIRED", result["reason"])

    def test_05_declared_commit_drift_fails_before_authority(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            drifted = dict(obs)
            drifted["canonical_commit"] = "8" * 40
            result = resolve_verified(desc, drifted, exact_proof, live)
        self.assertEqual("DOMAIN_CANONICAL_DRIFT", result["reason"])

    def test_06_current_main_source_drift_fails_closed(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, "9" * 40) as stale_live:
            result = resolve_verified(desc, obs, exact_proof, stale_live)
        self.assertEqual("DOMAIN_AUTHORITY_CANONICAL_FRESHNESS_UNVERIFIED", result["reason"])

    def test_07_project_identity_mismatch_fails_closed(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            wrong = dict(obs)
            wrong["project_id"] = "WRONG"
            result = resolve_verified(desc, wrong, exact_proof, live)
        self.assertEqual("DOMAIN_PROJECT_ID_MISMATCH", result["reason"])

    def test_08_noncanonical_source_only_fails_closed(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            draft = dict(obs)
            draft["source_kind"] = "DRAFT_PR"
            result = resolve_verified(desc, draft, exact_proof, live)
        self.assertEqual("NON_CANONICAL_SOURCE_ONLY", result["reason"])

    def test_09_descriptor_ref_or_arbitrary_ref_never_counts_as_authority_evidence(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            binding = resolve_verified(desc, obs, exact_proof, live)
            for ref in (
                DomainAuthorityDescriptor.from_mapping(desc).descriptor_ref(),
                trusted_exact_read_ref(exact_proof),
                "opaque://caller/chosen",
            ):
                ev = legacy.evidence(authority_domain_id=desc["domain_id"], authority_evidence_refs=[ref])
                self.assertFalse(domain_authority_module.authority_evidence_is_bound(ev, binding))
            trusted = legacy.evidence(
                authority_domain_id=desc["domain_id"],
                authority_evidence_refs=[semantic_authority_ref(exact_proof)],
            )
            self.assertTrue(domain_authority_module.authority_evidence_is_bound(trusted, binding))

    def test_10_reconciliation_requires_snapshot_provenance_and_domain_scan_to_reference_sealed_read(self):
        with exact_authority() as (_, desc, obs, exact_proof), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            cand = candidate_for("AI_FILM_SYSTEM", "R145-10")
            trusted_ref = semantic_authority_ref(exact_proof)
            ev = legacy.evidence(authority_domain_id="AI_FILM_SYSTEM", authority_evidence_refs=[trusted_ref])
            snap = explicit_snapshot(cand, [desc], [obs], ev)
            snap["source_provenance_refs"].append(live.provider_attribution_ref)
            result = reconcile_package(
                legacy.package(cand), snap, expected_canonical_main=legacy.MAIN,
                live_observation_proof=live, exact_read_proofs=(exact_proof,),
            )["results"][0]
            self.assertEqual("DOMAIN_AUTHORITY_PROVENANCE_NOT_BOUND", result["reason"])
            snap["source_provenance_refs"].append(trusted_ref)
            result = reconcile_package(
                legacy.package(cand), snap, expected_canonical_main=legacy.MAIN,
                live_observation_proof=live, exact_read_proofs=(exact_proof,),
            )["results"][0]
            self.assertEqual("DOMAIN_AUTHORITY_SCAN_NOT_BOUND", result["reason"])

    def test_11_external_true_new_requires_owner_exact_read_and_local_admission_proofs(self):
        with exact_authority() as (_, desc, obs, domain_exact), governed_domain_provider(FILM_REPO, desc["canonical_commit"]) as live:
            cand = candidate_for("AI_FILM_SYSTEM", "R145-NEW")
            trusted_ref = semantic_authority_ref(domain_exact)
            ev = legacy.evidence(authority_domain_id="AI_FILM_SYSTEM", authority_evidence_refs=[trusted_ref])
            with tempfile.TemporaryDirectory() as directory:
                ledger = DurableSignalLedger(Path(directory) / "ledger.sqlite")
                try:
                    coordinator_exacts = legacy.exact_current_reads("r145-external-new")
                    snap = legacy.bound_snapshot(ledger, live, coordinator_exacts, {cand["candidate_id"]: ev})
                    snap["domain_authority_descriptors"] = [desc]
                    snap["domain_authority_observations"] = [obs]
                    snap["source_provenance_refs"].append(trusted_ref)
                    snap["scan_coverage"]["domain_canonical"]["evidence_refs"].append(trusted_ref)
                    result = reconcile_package(
                        legacy.package(cand, batch_id="R145-EXTERNAL-NEW"),
                        snap,
                        expected_canonical_main=legacy.MAIN,
                        live_observation_proof=live,
                        exact_read_proofs=(*coordinator_exacts, domain_exact),
                        ledger=ledger,
                    )["results"][0]
                    self.assertEqual("NEW_DURABLE_SIGNAL", result["disposition"])
                    self.assertIn(trusted_ref, result["authority_evidence_refs"])
                finally:
                    ledger.close()

    def test_12_unknown_future_domain_has_no_second_brain_default(self):
        cand = candidate_for("FUTURE_DOMAIN_X", "R145-12")
        result = reconcile_package(
            legacy.package(cand), explicit_snapshot(cand, [], [], legacy.evidence()),
            expected_canonical_main=legacy.MAIN,
        )["results"][0]
        self.assertEqual("DOMAIN_ROUTE_UNRESOLVED", result["reason"])


class ExtensibilityAndPrivacyTests(unittest.TestCase):
    def test_13_fifth_domain_is_data_driven_but_still_requires_real_proofs(self):
        with exact_authority(
            domain_id="FUTURE_DOMAIN_5", project_id="FIFTH_PROJECT",
            repository="vxz2datoubo/fifth-system", authority_path="AUTHORITY.yaml",
        ) as (_, desc, obs, exact_proof), governed_domain_provider(desc["repository"], desc["canonical_commit"]) as live:
            result = resolve_verified(desc, obs, exact_proof, live)
        self.assertTrue(result["valid"])
        self.assertEqual("FUTURE_DOMAIN_5", result["domain_id"])

    def test_14_two_domains_same_repo_different_authority_roots_remain_distinct(self):
        with exact_authority(
            domain_id="D1", project_id="P1", repository=SECOND_REPO, authority_path="authority/one.yaml",
        ) as (_, one, one_obs, one_proof):
            root = Path(_)
            second_path = root / "authority/two.yaml"
            second_path.write_text(
                "domain_id: D2\n"
                "project_id: P2\n"
                "authority_schema_version: P2/v1\n"
                "writeback_owner: D2\n"
                "observation_mode: READ_ONLY\n"
                "source_authority: this_file\n",
                encoding="utf-8",
            )
            git("add", "authority/two.yaml", cwd=root)
            subprocess.check_call(["git", "-C", str(root), "-c", "commit.gpgsign=false", "commit", "-q", "-m", "second authority"])
            current_commit = git("rev-parse", "HEAD", cwd=root)
            two = descriptor("D2", "P2", SECOND_REPO, current_commit, "authority/two.yaml")
            two_source = exact_git_read_proofs(
                root,
                repository=SECOND_REPO,
                commit=current_commit,
                paths=("authority/two.yaml",),
                execution_id="r145-d2-source",
            )[0]
            with governed_domain_provider(
                SECOND_REPO,
                current_commit,
                authority_proofs=(two_source,),
            ) as governed_source:
                two_proof = exact_semantic_authority_proof(
                    root,
                    repository=SECOND_REPO,
                    commit=current_commit,
                    path="authority/two.yaml",
                    execution_id="r145-d2",
                    governed_source_proof=governed_source,
                )
            two_obs = observation_from_proof(two, two_proof)
            with governed_domain_provider(SECOND_REPO, legacy.MAIN) as live:
                first = DomainAuthorityResolver([one]).resolve(
                    "D1", [one_obs], exact_read_proofs=(one_proof,), live_observation_proof=live,
                    expected_canonical_main=legacy.MAIN, coordinator_repository=SECOND_REPO,
                )
                second = DomainAuthorityResolver([two]).resolve(
                    "D2", [two_obs], exact_read_proofs=(two_proof,), live_observation_proof=live,
                    expected_canonical_main=legacy.MAIN, coordinator_repository=SECOND_REPO,
                )
            self.assertFalse(first["valid"])
            self.assertFalse(second["valid"])
            self.assertEqual("DOMAIN_AUTHORITY_CANONICAL_FRESHNESS_UNVERIFIED", first["reason"])
            self.assertEqual("DOMAIN_AUTHORITY_CANONICAL_FRESHNESS_UNVERIFIED", second["reason"])

    def test_15_private_world_model_body_is_structurally_forbidden(self):
        desc = descriptor("WORLD_MODEL_SYSTEM", "AWRSE", WORLD_REPO, "2" * 40, "ARCHITECTURE.md", visibility="PRIVATE")
        raw = observation(desc)
        raw["raw_source_body"] = "private material"
        with self.assertRaises(DomainAuthorityError) as got:
            DomainAuthorityObservation.from_mapping(raw)
        self.assertEqual("DOMAIN_AUTHORITY_PRIVATE_BODY_FORBIDDEN", got.exception.code)

    def test_16_domain_resolver_has_no_network_process_or_write_surface(self):
        source = inspect.getsource(domain_authority_module)
        for forbidden in ("subprocess", "urllib", "requests.", "urlopen", "write_text(", "write_bytes("):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_17_opaque_declaration_ref_contains_identity_not_body(self):
        desc = descriptor("WORLD_MODEL_SYSTEM", "AWRSE", WORLD_REPO, "2" * 40, "ARCHITECTURE.md", visibility="PRIVATE")
        obs = observation(desc)
        ref = DomainAuthorityObservation.from_mapping(obs).opaque_ref()
        self.assertIn(WORLD_REPO, ref)
        self.assertIn("ARCHITECTURE.md", ref)
        self.assertIn("blob=", ref)
        self.assertIn("sha256=", ref)
        self.assertNotIn("private material", ref)

    def test_18_deterministic_receipt_is_explicitly_non_authoritative(self):
        desc = descriptor("D-EVIDENCE", "P-EVIDENCE", SECOND_REPO, "3" * 40, "AUTHORITY.yaml")
        obs = observation(desc)
        checks = {"G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS"}
        first = deterministic_domain_evidence_receipt(descriptors=[desc], observations=[obs], checks=checks)
        second = deterministic_domain_evidence_receipt(
            descriptors=[dict(reversed(list(desc.items())))],
            observations=[dict(reversed(list(obs.items())))],
            checks=dict(reversed(list(checks.items()))),
        )
        self.assertEqual(first, second)
        self.assertFalse(first["effective_truth_authority"])
        self.assertFalse(first["private_body_persisted"])
        self.assertEqual(64, len(first["receipt_sha256"]))


class CrossDomainPromotionAndTaskGuardTests(unittest.TestCase):
    def test_19_transferable_pattern_never_moves_ownership_or_permission(self):
        result = project_cross_domain_relation(
            relation="TRANSFERABLE_PATTERN_CANDIDATE",
            source_domain="AI_FILM_SYSTEM",
            related_domain="SECOND_BRAIN_SYSTEM",
            accepted_as_shared_capability=True,
        )
        self.assertTrue(result["shared_capability_candidate"])
        self.assertFalse(result["ownership_transferred"])
        self.assertFalse(result["write_permission_created"])
        self.assertFalse(result["automatic_task_created"])

    def test_20_arbitrary_cross_domain_task_strings_never_grant_exception(self):
        refs = (
            "governed://cross-domain/task-1",
            "https://example.invalid/tasks/real-looking",
            "NONEXISTENT-TASK",
            "stale://task/old",
            "tampered://task/proof",
        )
        for ref in refs:
            with self.subTest(ref=ref):
                result = evaluate_signal_task_route_domain_guard(
                    signal_primary_domain="AI_FILM_SYSTEM",
                    task_target_domain="SECOND_BRAIN_SYSTEM",
                    route_authority_domain="SECOND_BRAIN_SYSTEM",
                    writeback_owner_domain="SECOND_BRAIN_SYSTEM",
                    governed_cross_domain_task_ref=ref,
                )
                self.assertFalse(result["eligible_for_normal_release_gates"])
                self.assertEqual("GOVERNED_CROSS_DOMAIN_TASK_BINDING_REQUIRED", result["reason"])
                self.assertFalse(result["cross_domain_exception_verified"])

    def test_21_cross_domain_wrong_target_route_or_owner_blocks(self):
        cases = (
            ("SECOND_BRAIN_SYSTEM", "A_SHARE_SYSTEM", "SECOND_BRAIN_SYSTEM"),
            ("SECOND_BRAIN_SYSTEM", "SECOND_BRAIN_SYSTEM", "A_SHARE_SYSTEM"),
            ("WORLD_MODEL_SYSTEM", "WORLD_MODEL_SYSTEM", "A_SHARE_SYSTEM"),
        )
        for target, route, owner in cases:
            with self.subTest(target=target, route=route, owner=owner):
                result = evaluate_signal_task_route_domain_guard(
                    signal_primary_domain="AI_FILM_SYSTEM",
                    task_target_domain=target,
                    route_authority_domain=route,
                    writeback_owner_domain=owner,
                    governed_cross_domain_task_ref="governed://caller-only",
                )
                self.assertFalse(result["eligible_for_normal_release_gates"])

    def test_22_same_domain_remains_only_eligibility_not_authority_creation(self):
        result = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="A_SHARE_SYSTEM",
            task_target_domain="A_SHARE_SYSTEM",
            route_authority_domain="A_SHARE_SYSTEM",
            writeback_owner_domain="A_SHARE_SYSTEM",
        )
        self.assertTrue(result["eligible_for_normal_release_gates"])
        self.assertEqual("DOMAIN_IDENTITY_MATCH", result["reason"])
        self.assertFalse(result["automatic_task_created"])
        self.assertFalse(result["write_permission_created"])
        self.assertFalse(result["ownership_transferred"])

    def test_23_signal_remains_not_task(self):
        guard = evaluate_signal_task_route_domain_guard(
            signal_primary_domain="SECOND_BRAIN_SYSTEM",
            task_target_domain="SECOND_BRAIN_SYSTEM",
            route_authority_domain="SECOND_BRAIN_SYSTEM",
            writeback_owner_domain="SECOND_BRAIN_SYSTEM",
        )
        self.assertFalse(guard["automatic_task_created"])
        self.assertFalse(guard["write_permission_created"])


class RetainedR142CompatibilityTests(unittest.TestCase):
    def test_24_stale_second_brain_snapshot_still_fails_closed(self):
        cand = legacy.candidate("R145-24")
        snap = legacy.caller_snapshot({cand["candidate_id"]: legacy.evidence()}, main="b" * 40)
        result = reconcile_package(
            legacy.package(cand, batch_id="R145-24"), snap, expected_canonical_main=legacy.MAIN
        )["results"][0]
        self.assertEqual(("NEEDS_REVALIDATION", "STALE_CANONICAL_SNAPSHOT"), (result["disposition"], result["reason"]))

    def test_25_legacy_r142_local_domain_remains_compatible(self):
        cand = legacy.candidate("R145-25")
        result = reconcile_package(
            legacy.package(cand, batch_id="R145-25"),
            legacy.caller_snapshot({cand["candidate_id"]: legacy.evidence(desired_effect_unmet=False)}),
            expected_canonical_main=legacy.MAIN,
        )["results"][0]
        self.assertEqual("NEEDS_REVALIDATION", result["disposition"])
        self.assertEqual("NO_EVIDENCE_FOR_SAFE_ADMISSION", result["reason"])


if __name__ == "__main__":
    unittest.main()