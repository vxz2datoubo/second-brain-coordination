"""R145 exact-head CI positive path through the production governed provider."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import unittest

import yaml

from global_signal_gateway.gateway import (
    temporary_exact_clone,
    validate_live_observation_proof,
)
from global_signal_gateway.live_observation_provider import (
    ACTIVE_TASK_PATH,
    CONTROL_PATHS,
    CONTRACT_REVISION,
    DOMAIN_REPOSITORY,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
)
from global_signal_gateway.semantic_authority import (
    exact_semantic_authority_proof,
    semantic_authority_ref,
)


R145_CONTRACT = (
    "coordination/TASK-BRIEFS/"
    "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
)
AI_FILM_AUTHORITY_PATH = "PROJECT_INDEX.yaml"
AI_FILM_IDENTITY = {
    "domain_id": "AI_FILM_SYSTEM",
    "project_id": "EUSTIA_AI_FILM",
    "authority_schema_version": "AI_FILM_PROJECT_INDEX/v1",
    "writeback_owner": "AI_FILM_SYSTEM",
    "observation_mode": "READ_ONLY",
}


@unittest.skipUnless(
    os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("GITHUB_EVENT_PATH"),
    "real production-provider proof is an exact-head GitHub Actions check",
)
class RealGitHubActionsAuthorityPositivePath(unittest.TestCase):
    def test_real_ai_film_main_mints_semantic_authority_from_production_provider(self) -> None:
        workspace = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
        event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        pull_request = event.get("pull_request")
        self.assertIsInstance(pull_request, dict)
        number = event.get("number")
        self.assertIsInstance(number, int)
        self.assertGreater(number, 0)

        active = yaml.safe_load((workspace / ACTIVE_TASK_PATH).read_text(encoding="utf-8"))
        self.assertIsInstance(active, dict)
        task_id = active.get("task_id")
        route_epoch = active.get("route_epoch")
        self.assertIsInstance(task_id, str)
        self.assertTrue(task_id)
        self.assertIsInstance(route_epoch, int)

        request = LiveObservationRequest(
            request_id=f"r145-real-ai-film-ci-{number}",
            provider_contract_revision=CONTRACT_REVISION,
            target_repository=TARGET_REPOSITORY,
            target_branch="main",
            pull_request_number=number,
            expected_task_id=task_id,
            expected_route_epoch=route_epoch,
            required_control_plane_paths=CONTROL_PATHS,
            required_domain_freshness_targets=(
                DomainFreshnessTarget(
                    DOMAIN_REPOSITORY,
                    domain_id="AI_FILM_SYSTEM",
                    authority_contract_path=R145_CONTRACT,
                ),
            ),
            required_review_scope="ALL_RAW_REVIEWS",
            requested_max_age_seconds=240,
            requested_at=datetime.now(timezone.utc).isoformat(),
        )
        bundle, live_proof = LiveObservationProvider().observe(request)
        self.assertTrue(validate_live_observation_proof(live_proof))

        source_records = [
            record
            for record in bundle.exact_objects
            if record.repository == DOMAIN_REPOSITORY
            and record.path == AI_FILM_AUTHORITY_PATH
        ]
        self.assertEqual(1, len(source_records))
        source = source_records[0]
        self.assertIn(source.ref(), live_proof.exact_refs)

        with temporary_exact_clone(
            f"https://github.com/{DOMAIN_REPOSITORY}.git", source.commit_sha
        ) as source_root:
            semantic_proof = exact_semantic_authority_proof(
                source_root,
                repository=DOMAIN_REPOSITORY,
                commit=source.commit_sha,
                path=AI_FILM_AUTHORITY_PATH,
                execution_id=f"r145-real-ai-film-ci:{source.commit_sha[:16]}",
                governed_source_proof=live_proof,
                expected_identity=AI_FILM_IDENTITY,
            )

        semantic_ref = semantic_authority_ref(semantic_proof)
        self.assertIn(DOMAIN_REPOSITORY, semantic_ref)
        self.assertIn(source.commit_sha, semantic_ref)
        self.assertEqual(AI_FILM_IDENTITY, semantic_proof.semantic_dict())
        self.assertEqual(live_proof.provider_attribution_ref, semantic_proof.governed_source_provider_ref)


if __name__ == "__main__":
    unittest.main()
