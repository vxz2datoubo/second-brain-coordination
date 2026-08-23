"""R145 mandatory regressions for semantic owner identity and retained matrix cases."""
from __future__ import annotations

import unittest

from global_signal_gateway.domain_authority import DomainAuthorityResolver
from global_signal_gateway.retrospective_intake import reconcile_package
from global_signal_gateway.semantic_authority import semantic_authority_ref
import test_r142_r145_cross_domain as base
import test_r142_retrospective_intake as legacy


class SemanticAuthorityIdentityRegressions(unittest.TestCase):
    def test_semantic_git_object_from_domain_a_cannot_be_relabelled_as_domain_b(self):
        with base.exact_authority(
            domain_id="DOMAIN_A",
            project_id="PROJECT_A",
            repository="vxz2datoubo/domain-a",
            authority_path="AUTHORITY.yaml",
        ) as (_, source_desc, _, source_proof), base.governed_domain_provider(
            source_desc["repository"], source_desc["canonical_commit"]
        ) as live:
            relabelled = base.descriptor(
                "DOMAIN_B",
                "PROJECT_B",
                source_desc["repository"],
                source_desc["canonical_commit"],
                source_desc["authority_path_or_contract_ref"],
                owner="DOMAIN_B",
            )
            relabelled_observation = base.observation_from_proof(relabelled, source_proof)
            result = DomainAuthorityResolver([relabelled]).resolve(
                "DOMAIN_B",
                [relabelled_observation],
                exact_read_proofs=(source_proof,),
                live_observation_proof=live,
                expected_canonical_main=legacy.MAIN,
                coordinator_repository=base.SECOND_REPO,
            )
        self.assertFalse(result["valid"])
        self.assertEqual("DOMAIN_AUTHORITY_SEMANTIC_IDENTITY_UNVERIFIED", result["reason"])

    def test_world_model_canonical_main_beats_draft_pr_for_completion_truth(self):
        with base.exact_authority(
            domain_id="WORLD_MODEL_SYSTEM",
            project_id="AWRSE",
            repository=base.WORLD_REPO,
            authority_path="ARCHITECTURE.md",
            visibility="PRIVATE",
        ) as (_, desc, canonical_observation, semantic_proof), base.governed_domain_provider(
            base.WORLD_REPO, desc["canonical_commit"]
        ) as live:
            canonical_ref = semantic_authority_ref(semantic_proof)
            draft = dict(canonical_observation)
            draft["source_kind"] = "DRAFT_PR"
            draft["canonical_commit"] = "9" * 40
            cand = base.candidate_for("WORLD_MODEL_SYSTEM", "R145-WORLD-CANONICAL-WINS")
            evidence = legacy.evidence(
                satisfied_refs=[canonical_ref],
                desired_effect_unmet=False,
                authority_domain_id="WORLD_MODEL_SYSTEM",
                authority_evidence_refs=[canonical_ref],
            )
            snapshot = base.explicit_snapshot(cand, [desc], [draft, canonical_observation], evidence)
            snapshot["source_provenance_refs"].extend([live.provider_attribution_ref, canonical_ref])
            snapshot["scan_coverage"]["domain_canonical"]["evidence_refs"].append(canonical_ref)
            result = reconcile_package(
                legacy.package(cand, batch_id="R145-WORLD-CANONICAL-WINS"),
                snapshot,
                expected_canonical_main=legacy.MAIN,
                live_observation_proof=live,
                exact_read_proofs=(semantic_proof,),
            )["results"][0]
        self.assertEqual("ALREADY_SATISFIED", result["disposition"])
        self.assertIn(canonical_ref, result["authority_evidence_refs"])

    def test_domain_repository_move_preserves_historical_exact_binding(self):
        with base.exact_authority(
            domain_id="MOVING_DOMAIN",
            project_id="MOVING_PROJECT",
            repository="vxz2datoubo/old-home",
            authority_path="AUTHORITY.yaml",
        ) as (_, old_desc, old_observation, old_proof):
            old_ref = semantic_authority_ref(old_proof)
            old_commit = old_desc["canonical_commit"]
            with base.exact_authority(
                domain_id="MOVING_DOMAIN",
                project_id="MOVING_PROJECT",
                repository="vxz2datoubo/new-home",
                authority_path="AUTHORITY.yaml",
            ) as (_, new_desc, new_observation, new_proof), base.governed_domain_provider(
                new_desc["repository"], new_desc["canonical_commit"]
            ) as live:
                old_only = DomainAuthorityResolver([new_desc]).resolve(
                    "MOVING_DOMAIN",
                    [new_observation],
                    exact_read_proofs=(old_proof,),
                    live_observation_proof=live,
                    expected_canonical_main=legacy.MAIN,
                    coordinator_repository=base.SECOND_REPO,
                )
                current = DomainAuthorityResolver([new_desc]).resolve(
                    "MOVING_DOMAIN",
                    [new_observation],
                    exact_read_proofs=(old_proof, new_proof),
                    live_observation_proof=live,
                    expected_canonical_main=legacy.MAIN,
                    coordinator_repository=base.SECOND_REPO,
                )
                new_ref = semantic_authority_ref(new_proof)
        self.assertFalse(old_only["valid"])
        self.assertEqual("DOMAIN_AUTHORITY_EXACT_READ_PROOF_REQUIRED", old_only["reason"])
        self.assertTrue(current["valid"])
        self.assertIn(new_ref, current["trusted_authority_refs"])
        self.assertNotIn(old_ref, current["trusted_authority_refs"])
        self.assertIn("vxz2datoubo/old-home", old_ref)
        self.assertIn(old_commit, old_ref)
        self.assertNotEqual(old_ref, new_ref)
        self.assertEqual("vxz2datoubo/old-home", old_observation["repository"])


if __name__ == "__main__":
    unittest.main()
