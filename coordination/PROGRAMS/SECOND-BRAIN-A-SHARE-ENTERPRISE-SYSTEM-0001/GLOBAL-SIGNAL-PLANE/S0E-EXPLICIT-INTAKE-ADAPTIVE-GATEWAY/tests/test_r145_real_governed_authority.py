"""R145 production-seam regressions for native owner-domain authority binding."""
from __future__ import annotations

from base64 import b64encode
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

import yaml

from global_signal_gateway.gateway import GatewayError, validate_live_observation_proof
from global_signal_gateway.live_observation_provider import (
    CONTRACT_REVISION,
    CONTROL_PATHS,
    DOMAIN_REPOSITORY,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationRequest,
    _git_blob_sha,
)
from global_signal_gateway.semantic_authority import (
    exact_semantic_authority_proof,
    governed_semantic_authority_ref,
    native_semantic_authority_identity,
    semantic_authority_ref,
)
import test_r137_live_observation_provider as r137


R145_CONTRACT = (
    "coordination/TASK-BRIEFS/"
    "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145.yaml"
)
WORLD_REPOSITORY = "vxz2datoubo/ai-world-simulation-engine"
AI_FILM_IDENTITY = {
    "domain_id": "AI_FILM_SYSTEM",
    "project_id": "EUSTIA_AI_FILM",
    "authority_schema_version": "AI_FILM_PROJECT_INDEX/v1",
    "writeback_owner": "AI_FILM_SYSTEM",
    "observation_mode": "READ_ONLY",
}


def git(*args: str, cwd: Path) -> str:
    return subprocess.check_output(["git", "-C", str(cwd), *args], text=True).strip()


def project_index_payload() -> bytes:
    # Native AI Film shape: project identity + self authority, not an R145
    # five-field synthetic domain object.
    return (
        "project_id: EUSTIA_AI_FILM\n"
        "title: native owner project\n"
        "status: active\n"
        "source_authority: this_file\n"
        "policy:\n"
        "  memory_is_canonical: false\n"
        "canonical:\n"
        "  project_entry: project.md\n"
    ).encode("utf-8")


def governed_contract_payload() -> bytes:
    value = {
        "release_preflight": {
            "strategy": "ADAPT_EXISTING / NO_NEW_PARALLEL_DOMAIN_AUTHORITY"
        },
        "required_domain_authority_binding": [
            "domain_id",
            "project_id",
            "repository",
            "canonical_commit",
            "authority_path_or_contract_ref",
            "provenance_or_exact_read_proof",
        ],
        "mandatory_domain_regressions": {
            "AI_FILM_SYSTEM": {
                "repository": DOMAIN_REPOSITORY,
                "authority_hint": "PROJECT_INDEX.yaml",
                "write_policy": "READ_ONLY_FROM_SIGNAL_TOWER",
            },
            "WORLD_MODEL_SYSTEM": {
                "repository": WORLD_REPOSITORY,
                "architecture_hint": "ARCHITECTURE.md",
                "repository_visibility": "PRIVATE",
                "write_policy": "READ_ONLY_FROM_SIGNAL_TOWER",
            },
        },
    }
    return yaml.safe_dump(value, sort_keys=False).encode("utf-8")


class SyntheticGovernedAuthorityGitHub(r137.SyntheticPublicGitHub):
    """Same production provider with a synthetic transport and native source body."""

    def __init__(
        self,
        *,
        domain_commit: str,
        domain_tree: str,
        domain_blob: str,
        domain_payload: bytes,
    ) -> None:
        super().__init__()
        self._governed_domain_repositories = set()
        self.domain = domain_commit
        self.domain_tree = domain_tree
        self.domain_blob = domain_blob
        self.domain_payload = domain_payload
        contract = governed_contract_payload()
        contract_blob = _git_blob_sha(contract)
        self.blobs[contract_blob] = contract
        self.paths[R145_CONTRACT] = contract_blob

    def _get_json(self, path: str):  # type: ignore[override]
        metadata = {
            "path": path,
            "status": 200,
            "content_sha256": hashlib.sha256(path.encode()).hexdigest(),
            "bytes": len(path),
        }
        if path == f"/repos/{DOMAIN_REPOSITORY}/git/commits/{self.domain}":
            self.calls.append(path)
            return {}, {"tree": {"sha": self.domain_tree}}, metadata
        if path == f"/repos/{DOMAIN_REPOSITORY}/git/trees/{self.domain_tree}?recursive=1":
            self.calls.append(path)
            return {}, {
                "tree": [
                    {"path": "PROJECT_INDEX.yaml", "type": "blob", "sha": self.domain_blob}
                ],
                "truncated": False,
            }, metadata
        if path == f"/repos/{DOMAIN_REPOSITORY}/git/blobs/{self.domain_blob}":
            self.calls.append(path)
            return {}, {
                "encoding": "base64",
                "content": b64encode(self.domain_payload).decode("ascii"),
            }, metadata
        return super()._get_json(path)


def request_for(target: DomainFreshnessTarget) -> LiveObservationRequest:
    return LiveObservationRequest(
        request_id="r145-real-governed-authority-test",
        provider_contract_revision=CONTRACT_REVISION,
        target_repository=TARGET_REPOSITORY,
        target_branch="main",
        pull_request_number=360,
        expected_task_id=r137.TASK,
        expected_route_epoch=137,
        required_control_plane_paths=CONTROL_PATHS,
        required_domain_freshness_targets=(target,),
        required_review_scope="ALL_RAW_REVIEWS",
        requested_max_age_seconds=60,
        requested_at=datetime.now(timezone.utc).isoformat(),
    )


class NativeAuthorityRepresentationTests(unittest.TestCase):
    def test_ai_film_project_index_native_shape_is_recognized_without_r145_schema(self) -> None:
        identity = native_semantic_authority_identity(
            project_index_payload(), path="PROJECT_INDEX.yaml"
        )
        self.assertEqual("EUSTIA_AI_FILM", identity["project_id"])
        self.assertEqual("AI_FILM_PROJECT_INDEX/v1", identity["authority_schema_version"])
        self.assertNotIn("domain_id", identity)
        self.assertNotIn("writeback_owner", identity)

    def test_world_model_canonical_architecture_markdown_shape_is_supported(self) -> None:
        payload = (
            "# AWRSE Canonical Architecture\n\n"
            "Status: `CANDIDATE`\n\n"
            "Authority role: `CANONICAL_ARCHITECTURE_MASTER`.\n"
        ).encode("utf-8")
        identity = native_semantic_authority_identity(payload, path="ARCHITECTURE.md")
        self.assertEqual(
            {
                "project_id": "AWRSE",
                "authority_schema_version": "CANONICAL_ARCHITECTURE_MARKDOWN/v1",
            },
            identity,
        )


class GovernedProductionSeamTests(unittest.TestCase):
    def test_existing_r137_provider_attests_native_ai_film_source_and_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.check_call(["git", "init", "-q", str(root)])
            git("config", "user.email", "r145-tests@example.invalid", cwd=root)
            git("config", "user.name", "R145 Tests", cwd=root)
            payload = project_index_payload()
            (root / "PROJECT_INDEX.yaml").write_bytes(payload)
            git("add", "PROJECT_INDEX.yaml", cwd=root)
            subprocess.check_call(
                [
                    "git",
                    "-C",
                    str(root),
                    "-c",
                    "commit.gpgsign=false",
                    "commit",
                    "-q",
                    "-m",
                    "native authority",
                ]
            )
            commit = git("rev-parse", "HEAD", cwd=root)
            tree = git("rev-parse", f"{commit}^{{tree}}", cwd=root)
            blob = git("rev-parse", f"{commit}:PROJECT_INDEX.yaml", cwd=root)

            provider = SyntheticGovernedAuthorityGitHub(
                domain_commit=commit,
                domain_tree=tree,
                domain_blob=blob,
                domain_payload=payload,
            )
            bundle, live = provider.observe(
                request_for(
                    DomainFreshnessTarget(
                        DOMAIN_REPOSITORY,
                        domain_id="AI_FILM_SYSTEM",
                        authority_contract_path=R145_CONTRACT,
                    )
                )
            )
            self.assertTrue(validate_live_observation_proof(live))
            source_refs = [
                record.ref()
                for record in bundle.exact_objects
                if record.repository == DOMAIN_REPOSITORY
                and record.path == "PROJECT_INDEX.yaml"
            ]
            self.assertEqual(1, len(source_refs))
            self.assertIn(source_refs[0], live.exact_refs)
            semantic_attestation = governed_semantic_authority_ref(
                source_refs[0], AI_FILM_IDENTITY
            )
            self.assertIn(semantic_attestation, live.exact_refs)

            proof = exact_semantic_authority_proof(
                root,
                repository=DOMAIN_REPOSITORY,
                commit=commit,
                path="PROJECT_INDEX.yaml",
                execution_id="r145-native-ai-film",
                governed_source_proof=live,
                expected_identity=AI_FILM_IDENTITY,
            )
            ref = semantic_authority_ref(proof)
            self.assertIn(DOMAIN_REPOSITORY, ref)
            self.assertIn(commit, ref)

    def test_private_world_model_contract_fails_before_private_repository_read(self) -> None:
        payload = project_index_payload()
        provider = SyntheticGovernedAuthorityGitHub(
            domain_commit="d" * 40,
            domain_tree="e" * 40,
            domain_blob=_git_blob_sha(payload),
            domain_payload=payload,
        )
        with self.assertRaises(GatewayError) as got:
            provider.observe(
                request_for(
                    DomainFreshnessTarget(
                        WORLD_REPOSITORY,
                        domain_id="WORLD_MODEL_SYSTEM",
                        authority_contract_path=R145_CONTRACT,
                    )
                )
            )
        self.assertEqual("DOMAIN_AUTHORITY_PRIVATE_SOURCE_UNAVAILABLE", got.exception.code)
        self.assertFalse(any(WORLD_REPOSITORY in call for call in provider.calls))

    def test_contract_repository_mismatch_cannot_redirect_authority_read(self) -> None:
        payload = project_index_payload()
        provider = SyntheticGovernedAuthorityGitHub(
            domain_commit="d" * 40,
            domain_tree="e" * 40,
            domain_blob=_git_blob_sha(payload),
            domain_payload=payload,
        )
        with self.assertRaises(GatewayError) as got:
            provider.observe(
                request_for(
                    DomainFreshnessTarget(
                        "vxz2datoubo/not-the-film-repo",
                        domain_id="AI_FILM_SYSTEM",
                        authority_contract_path=R145_CONTRACT,
                    )
                )
            )
        self.assertEqual("DOMAIN_AUTHORITY_REPOSITORY_MISMATCH", got.exception.code)


if __name__ == "__main__":
    unittest.main()
