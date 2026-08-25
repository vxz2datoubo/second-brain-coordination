"""Mechanism regressions for R137's bounded live-observation provider.

All fixtures are synthetic public GitHub API responses.  They exercise the
same request/path/object/proof mechanism without reading a private source or
making a network call.
"""
from __future__ import annotations

from base64 import b64encode
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT.parent / "S0-SYNTHETIC" / "src")]

from global_signal_gateway.gateway import SignalIntakeGateway, SystemAwarenessProjection, AuthorityBoundLiveObservationProof, validate_live_observation_proof  # noqa: E402
from global_signal_gateway.live_observation_provider import (  # noqa: E402
    API_HOST,
    API_VERSION,
    CONTROL_PATHS,
    CONTRACT_REVISION,
    DOMAIN_REPOSITORY,
    MAX_AGE_SECONDS,
    TARGET_REPOSITORY,
    DomainFreshnessTarget,
    LiveObservationProvider,
    LiveObservationRequest,
    _BUNDLES,
    _CANONICAL_MERGE_ANCHORS,
    _git_blob_sha,
)
from global_signal_gateway import live_observation_provider as provider_module  # noqa: E402
from global_signal_gateway.gateway import GatewayError  # noqa: E402
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402


TASK = "CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER"
ANCHOR_REPOSITORY, ANCHOR_PR, ANCHOR_MERGE, ANCHOR_BASE, ANCHOR_HEAD = _CANONICAL_MERGE_ANCHORS[0]


class SyntheticPublicGitHub(LiveObservationProvider):
    """A test subclass: production has no injectable transport constructor."""

    def __init__(self, fault: str | None = None) -> None:
        self.fault, self.calls, self.main_reads, self.pr_reads = fault, [], 0, 0
        task, epoch = TASK, 137
        route_path = "coordination/ROUTES/CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER-R137.yaml"
        if fault == "successor-route":
            task, epoch = "CODEX-NEXT-TASK", 138
            route_path = "coordination/ROUTES/CODEX-NEXT-TASK-R138.yaml"
        pointer = route_path
        if fault == "route-malformed": pointer = "coordination/ROUTES/not-yaml.txt"
        if fault == "route-traversal": pointer = "coordination/ROUTES/../escape.yaml"
        if fault == "route-missing": pointer = "coordination/ROUTES/missing.yaml"
        if fault == "route-wrong-prefix": pointer = "coordination/NOT-ROUTES/route.yaml"
        controls = {
            CONTROL_PATHS[0]: f"task_id: {task}\nroute_epoch: {epoch}\ncanonical_route: {pointer}\nstatus: READY\n",
            CONTROL_PATHS[1]: "claims:\n  - claim_id: R137\n",
            CONTROL_PATHS[2]: "lanes:\n  - lane_id: A\n",
            CONTROL_PATHS[3]: "# public control tower\n",
        }
        if fault != "route-missing":
            route_task = "CODEX-WRONG-TASK" if fault == "route-wrong-task" else task
            controls[route_path] = f"task_id: {route_task}\nroute_epoch: {epoch}\nexecution_allowed: true\n"
        self.blobs = { _git_blob_sha(text.encode()): text.encode() for text in controls.values() }
        self.paths = {path: _git_blob_sha(text.encode()) for path, text in controls.items()}
        self.main, self.tree, self.domain = "a" * 40, "b" * 40, "d" * 40

    def _get_json(self, path: str):  # type: ignore[override]
        self.calls.append(path)
        metadata = {"path": path, "status": 200, "content_sha256": hashlib.sha256(path.encode()).hexdigest(), "bytes": len(path)}
        if path == f"/repos/{TARGET_REPOSITORY}/git/ref/heads/main":
            self.main_reads += 1
            sha = "e" * 40 if self.fault == "main-drift" and self.main_reads > 1 else self.main
            return {}, {"object": {"sha": sha}}, metadata
        if path == f"/repos/{DOMAIN_REPOSITORY}/git/ref/heads/main":
            return {}, {"object": {"sha": self.domain}}, metadata
        if path == f"/repos/{TARGET_REPOSITORY}/git/commits/{ANCHOR_MERGE}":
            parents = [{"sha": ANCHOR_BASE}, {"sha": ANCHOR_HEAD}]
            if self.fault == "merged-null-head-first":
                parents = [{"sha": ANCHOR_HEAD}, {"sha": ANCHOR_BASE}]
            elif self.fault == "merged-null-head-sole":
                parents = [{"sha": ANCHOR_HEAD}]
            elif self.fault == "merged-null-unrelated-descendant":
                parents = [{"sha": ANCHOR_BASE}, {"sha": "f" * 40}]
            elif self.fault == "merged-null-malformed-parents":
                parents = [{"sha": ANCHOR_BASE}, {"not_sha": ANCHOR_HEAD}]
            return {}, {"tree": {"sha": self.tree}, "parents": parents}, metadata
        if path == f"/repos/{TARGET_REPOSITORY}/git/commits/{self.main}":
            return {}, {"tree": {"sha": self.tree}}, metadata
        compare_path = f"/repos/{TARGET_REPOSITORY}/compare/{ANCHOR_MERGE}...{self.main}"
        if path == compare_path:
            if self.fault == "merged-null-no-ancestry":
                return {}, {"status": "diverged", "ahead_by": 1, "behind_by": 1, "base_commit": {"sha": ANCHOR_MERGE}, "merge_base_commit": {"sha": "f" * 40}}, metadata
            ahead_by = 100 if self.fault == "merged-null-more-than-64-later" else 1
            return {}, {"status": "ahead", "ahead_by": ahead_by, "behind_by": 0, "base_commit": {"sha": ANCHOR_MERGE}, "merge_base_commit": {"sha": ANCHOR_MERGE}}, metadata
        if path == f"/repos/{TARGET_REPOSITORY}/git/trees/{self.tree}?recursive=1":
            entries = [{"path": item, "type": "blob", "sha": sha} for item, sha in self.paths.items()]
            if self.fault == "missing-path": entries.pop()
            if self.fault == "tree-mismatch": entries[0]["sha"] = "f" * 40
            tree_response = {"tree": entries, "truncated": False}
            if self.fault == "tree-truncated": tree_response["truncated"] = True
            if self.fault == "tree-truncated-malformed": tree_response["truncated"] = "false"
            if self.fault == "tree-truncated-missing": tree_response.pop("truncated")
            return {}, tree_response, metadata
        prefix = f"/repos/{TARGET_REPOSITORY}/git/blobs/"
        if path.startswith(prefix):
            sha = path[len(prefix):]
            payload = self.blobs.get(sha, b"not-the-claimed-blob")
            if self.fault == "blob-mismatch": payload += b"!"
            return {}, {"encoding": "base64", "content": b64encode(payload).decode()}, metadata
        pr_number = next((number for number in (360, ANCHOR_PR) if path == f"/repos/{TARGET_REPOSITORY}/pulls/{number}"), None)
        if pr_number is not None:
            self.pr_reads += 1
            if pr_number == ANCHOR_PR:
                head, base = ANCHOR_HEAD, ANCHOR_BASE
            else:
                head, base = "c" * 40, "b" * 40
            if self.fault == "pr-drift" and self.pr_reads > 1: head = "9" * 40
            if self.fault == "pr-base-drift" and self.pr_reads > 1: base = "8" * 40
            state, merged, merge = "open", False, None
            if self.fault in {"open-merge-sha", "merge-sha-drift"}: merge = "6" * 40
            if self.fault == "pr-state-drift" and self.pr_reads > 1: state = "closed"
            if self.fault == "merge-drift" and self.pr_reads > 1: state, merged, merge = "closed", True, "7" * 40
            if self.fault == "merge-sha-drift" and self.pr_reads > 1: merge = "7" * 40
            if self.fault in {
                "merged-null-then-valid",
                "merged-null-always",
                "merged-null-no-ancestry",
                "merged-null-head-first",
                "merged-null-head-sole",
                "merged-null-unrelated-descendant",
                "merged-null-malformed-parents",
                "merged-null-more-than-64-later",
                "merged-null-unanchored",
            }:
                state, merged, merge = "closed", True, None
            return {}, {"state": state, "head": {"sha": head}, "base": {"sha": base}, "merged": merged, "merge_commit_sha": merge}, metadata
        review_number = next((number for number in (360, ANCHOR_PR) if path.startswith(f"/repos/{TARGET_REPOSITORY}/pulls/{number}/reviews?per_page=100&page=")), None)
        if review_number is not None:
            page = int(path.rsplit("=", 1)[1])
            headers = {"link": f'<https://api.github.com/next?page={page + 1}>; rel="next"'} if self.fault == "pagination" else {}
            if self.fault == "review-invalid": return headers, [{"id": 1}], metadata
            commit = ANCHOR_HEAD if review_number == ANCHOR_PR else "c" * 40
            if self.fault == "review-drift": commit = "0" * 40
            return headers, [{"id": page, "state": "APPROVED", "commit_id": commit, "submitted_at": "2026-08-16T00:00:00+00:00", "user": {"id": 1}}], metadata
        raise AssertionError(f"unexpected synthetic API path: {path}")


def request(**changes: object) -> LiveObservationRequest:
    values: dict[str, object] = {
        "request_id": "r137-test-request", "provider_contract_revision": CONTRACT_REVISION,
        "target_repository": TARGET_REPOSITORY, "target_branch": "main", "pull_request_number": 360,
        "expected_task_id": TASK, "expected_route_epoch": 137, "required_control_plane_paths": CONTROL_PATHS,
        "required_domain_freshness_targets": (DomainFreshnessTarget(DOMAIN_REPOSITORY),),
        "required_review_scope": "ALL_RAW_REVIEWS", "requested_max_age_seconds": 60,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    values.update(changes)
    return LiveObservationRequest(**values)  # type: ignore[arg-type]


class R137LiveObservationTests(unittest.TestCase):
    def observe(self, fault: str | None = None, **request_changes: object):
        return SyntheticPublicGitHub(fault).observe(request(**request_changes))

    def assert_rejected(self, fault: str) -> None:
        with self.assertRaises(GatewayError):
            self.observe(fault)

    def assert_merge_proof_rejected(self, fault: str, *, pull_request_number: int = ANCHOR_PR) -> None:
        with self.assertRaises(GatewayError) as caught:
            self.observe(fault, pull_request_number=pull_request_number)
        self.assertEqual(caught.exception.code, "GITHUB_PR_MERGE_ANCESTRY_UNVERIFIED")

    def test_r137_r001_valid_public_observation_has_complete_evidence_and_proof(self) -> None:
        bundle, proof = self.observe()
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertEqual((bundle.initial_main_sha, bundle.final_main_sha, bundle.github_api_version), ("a" * 40, "a" * 40, API_VERSION))
        self.assertTrue(bundle.pagination_complete)
        self.assertIn(bundle.identity_ref(), proof.exact_refs)

    def test_r137_r002_caller_filled_proof_is_not_provider_evidence(self) -> None:
        _, proof = self.observe()
        self.assertFalse(validate_live_observation_proof(replace(proof, _issuer_seal=object())))

    def test_r137_r003_no_caller_registration_api_exists(self) -> None:
        self.assertFalse(hasattr(provider_module, "register_provider"))
        self.assertFalse(hasattr(LiveObservationProvider, "register_verifier"))

    def test_r137_r004_unknown_repository_is_rejected_before_network(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(target_repository="private/repository"))

    def test_r137_r005_fixed_host_redirect_media_size_and_json_transport_guards(self) -> None:
        class Response:
            def __init__(self, status=200, headers=(), payload=b'{"object":{"sha":"a"}}'):
                self.status, self._headers, self._payload = status, list(headers), payload
            def getheaders(self): return self._headers
            def read(self, _limit): return self._payload
        class Connection:
            instances = []
            response = Response(headers=(("Content-Type", "application/json"),))
            def __init__(self, host, timeout): self.host, self.timeout, self.request_args = host, timeout, None; self.__class__.instances.append(self)
            def request(self, *args, **kwargs): self.request_args = (args, kwargs)
            def getresponse(self): return self.__class__.response
            def close(self): pass
        with patch("global_signal_gateway.live_observation_provider.http.client.HTTPSConnection", Connection):
            headers, _, _ = LiveObservationProvider()._get_json(f"/repos/{TARGET_REPOSITORY}/git/ref/heads/main")
            self.assertEqual(headers["content-type"], "application/json")
            connection = Connection.instances[-1]
            self.assertEqual((connection.host, connection.request_args[0][0]), (API_HOST, "GET"))
            sent = connection.request_args[1]["headers"]
            self.assertNotIn("Authorization", sent)
            self.assertEqual(sent["X-GitHub-Api-Version"], API_VERSION)
            for response in (
                Response(status=302, headers=(("Content-Type", "application/json"), ("Location", "https://elsewhere"))),
                Response(headers=(("Content-Type", "text/plain"),)),
                Response(headers=(("Content-Type", "application/json"), ("Content-Length", "1000001"))),
                Response(headers=(("Content-Type", "application/json"),), payload=b"not-json"),
            ):
                Connection.response = response
                with self.subTest(response=response.status, headers=response.getheaders()):
                    with self.assertRaises(GatewayError): LiveObservationProvider()._get_json(f"/repos/{TARGET_REPOSITORY}/git/ref/heads/main")
        self.assertFalse(any(name in provider_module.__dict__ for name in ("requests", "urllib", "POST", "PUT", "PATCH", "DELETE")))

    def test_r137_r006_missing_required_path_fails(self) -> None: self.assert_rejected("missing-path")
    def test_r137_r007_tree_blob_substitution_fails(self) -> None: self.assert_rejected("tree-mismatch")
    def test_r137_r008_blob_payload_identity_mismatch_fails(self) -> None: self.assert_rejected("blob-mismatch")
    def test_r137_r008b_truncated_or_malformed_tree_fails(self) -> None:
        self.assert_rejected("tree-truncated")
        self.assert_rejected("tree-truncated-malformed")
        self.assert_rejected("tree-truncated-missing")
    def test_r137_r009_main_drift_fails(self) -> None: self.assert_rejected("main-drift")
    def test_r137_r010_pr_head_drift_fails(self) -> None: self.assert_rejected("pr-drift")
    def test_r137_r011_pr_base_drift_fails(self) -> None: self.assert_rejected("pr-base-drift")
    def test_r137_r012_merge_state_drift_fails(self) -> None: self.assert_rejected("merge-drift")
    def test_r137_r012b_pr_state_only_drift_fails(self) -> None: self.assert_rejected("pr-state-drift")
    def test_r137_r012c_null_merged_pr_field_uses_exact_main_ancestry_or_fails_closed(self) -> None:
        bundle, proof = self.observe("merged-null-then-valid", pull_request_number=ANCHOR_PR)
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertEqual(ANCHOR_MERGE, bundle.pr["merge_commit_sha"])
        self.assert_merge_proof_rejected("merged-null-no-ancestry")

    def test_r137_r012d_valid_two_parent_anchor_requires_main_first_parent_and_reviewed_head_second(self) -> None:
        bundle, proof = self.observe("merged-null-always", pull_request_number=ANCHOR_PR)
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertEqual((ANCHOR_PR, ANCHOR_MERGE, ANCHOR_HEAD, ANCHOR_BASE), (bundle.pr["number"], bundle.pr["merge_commit_sha"], bundle.pr["head_sha"], bundle.pr["base_sha"]))

    def test_r137_r012e_reviewed_head_as_first_or_sole_parent_fails_closed(self) -> None:
        self.assert_merge_proof_rejected("merged-null-head-first")
        self.assert_merge_proof_rejected("merged-null-head-sole")

    def test_r137_r012f_unrelated_descendant_and_malformed_parent_data_fail_closed(self) -> None:
        self.assert_merge_proof_rejected("merged-null-unrelated-descendant")
        self.assert_merge_proof_rejected("merged-null-malformed-parents")

    def test_r137_r012g_fixed_historical_merge_survives_more_than_64_later_main_commits(self) -> None:
        provider = SyntheticPublicGitHub("merged-null-more-than-64-later")
        bundle, proof = provider.observe(request(pull_request_number=ANCHOR_PR))
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertEqual(ANCHOR_MERGE, bundle.pr["merge_commit_sha"])
        anchor_reads = [call for call in provider.calls if call == f"/repos/{TARGET_REPOSITORY}/git/commits/{ANCHOR_MERGE}"]
        compare_reads = [call for call in provider.calls if call == f"/repos/{TARGET_REPOSITORY}/compare/{ANCHOR_MERGE}...{provider.main}"]
        self.assertEqual((len(anchor_reads), len(compare_reads)), (2, 2))
        commit_reads = [call for call in provider.calls if f"/repos/{TARGET_REPOSITORY}/git/commits/" in call]
        self.assertEqual(len(commit_reads), 3)

    def test_r137_r012h_nullable_merge_without_immutable_anchor_fails_closed(self) -> None:
        self.assert_merge_proof_rejected("merged-null-unanchored", pull_request_number=360)

    def test_r137_r013_malformed_review_fails(self) -> None: self.assert_rejected("review-invalid")
    def test_r137_r014_incomplete_pagination_fails(self) -> None: self.assert_rejected("pagination")

    def test_r137_r015_replay_after_expiry_fails(self) -> None:
        _, proof = self.observe()
        after = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
        self.assertFalse(validate_live_observation_proof(proof, at=after))

    def test_r137_r016_unknown_provider_fails_closed(self) -> None:
        _, proof = self.observe()
        self.assertFalse(validate_live_observation_proof(replace(proof, provider_id="unknown-provider")))

    def test_r137_r017_code_digest_drift_fails(self) -> None:
        bundle, proof = self.observe()
        _BUNDLES[bundle.identity_ref()] = replace(bundle, provider_code_digest="0" * 64)
        self.assertFalse(validate_live_observation_proof(proof))

    def test_r137_r018_route_claim_lane_lease_drift_invalidates(self) -> None:
        _, proof = self.observe()
        for field in ("route_fingerprint", "claim_fingerprint", "lane_fingerprint", "lease_fingerprint"):
            with self.subTest(field=field): self.assertFalse(validate_live_observation_proof(replace(proof, **{field: "drift"})))

    def test_r137_r019_head_base_review_main_drift_invalidates(self) -> None:
        _, proof = self.observe()
        for field in ("head_sha", "base_sha", "review_state_ref", "current_main_sha"):
            with self.subTest(field=field): self.assertFalse(validate_live_observation_proof(replace(proof, **{field: "drift"})))

    def test_r137_r020_merge_domain_approval_drift_invalidates(self) -> None:
        _, proof = self.observe()
        for changes in ({"merged": True, "merge_commit_sha": "1" * 40}, {"domain_freshness_ref": "drift"}, {"pending_approval_ref": "drift"}):
            with self.subTest(changes=changes): self.assertFalse(validate_live_observation_proof(replace(proof, **changes)))

    def test_b01_genuine_proof_pr_identity_and_state_mutations_fail(self) -> None:
        _, proof = self.observe()
        self.assertFalse(validate_live_observation_proof(replace(proof, pr_state="closed")))
        self.assertFalse(validate_live_observation_proof(replace(proof, pr_number=proof.pr_number + 1)))

    def test_b05_successor_route_is_read_from_active_exact_main(self) -> None:
        next_task, next_epoch = "CODEX-NEXT-TASK", 138
        bundle, proof = self.observe("successor-route", expected_task_id=next_task, expected_route_epoch=next_epoch)
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertIn("coordination/ROUTES/CODEX-NEXT-TASK-R138.yaml", [record.path for record in bundle.exact_objects])
        for fault in ("route-malformed", "route-traversal", "route-missing", "route-wrong-prefix", "route-wrong-task"):
            with self.subTest(fault=fault): self.assert_rejected(fault)

    def test_b06_open_pr_non_null_merge_sha_is_bound_and_rechecked(self) -> None:
        _, proof = self.observe("open-merge-sha")
        self.assertFalse(proof.merged)
        self.assertEqual(proof.merge_commit_sha, "6" * 40)
        self.assertTrue(validate_live_observation_proof(proof))
        self.assertFalse(validate_live_observation_proof(replace(proof, merge_commit_sha="7" * 40)))
        self.assert_rejected("merge-sha-drift")

    def test_r137_r021_request_contract_revision_is_fixed(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(provider_contract_revision="v2"))

    def test_r137_r022_age_policy_is_bounded(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(requested_max_age_seconds=MAX_AGE_SECONDS + 1))

    def test_r137_r023_domain_target_is_allowlisted(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(required_domain_freshness_targets=(DomainFreshnessTarget("other/repo"),)))

    def test_r137_r024_control_plane_set_is_exact(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(required_control_plane_paths=CONTROL_PATHS[:-1]))

    def test_r137_r025_review_scope_is_raw_not_policy(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(required_review_scope="APPROVED_ONLY"))

    def test_r137_r026_pr_is_required_for_formal_observation(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(pull_request_number=None))

    def test_r137_r027_expected_task_binding_is_observed_not_supplied(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(expected_task_id="other-task"))

    def test_r137_r028_expected_epoch_binding_is_observed_not_supplied(self) -> None:
        with self.assertRaises(GatewayError): SyntheticPublicGitHub().observe(request(expected_route_epoch=999))

    def test_r137_r029_proof_references_registered_bundle_identity(self) -> None:
        bundle, proof = self.observe()
        self.assertIs(_BUNDLES[bundle.identity_ref()], bundle)
        self.assertFalse(validate_live_observation_proof(replace(proof, provider_attribution_ref="provider://r137/evidence/forged#sha256=" + proof.evidence_digest)))

    def test_r137_r030_provider_cannot_authorize_execution_or_merge(self) -> None:
        bundle, proof = self.observe()
        text = repr(bundle)
        self.assertNotIn("execution_authorized", text)
        self.assertNotIn("merge_authorized", text)
        with tempfile.TemporaryDirectory() as directory:
            ledger = DurableSignalLedger(Path(directory) / "synthetic.sqlite")
            try:
                projection = ledger.rebuild_projection(expected_version=ledger.current_projection_version())
                awareness = SystemAwarenessProjection.build({"synthetic": {"revision": "one"}}, projection)
                preflight = SignalIntakeGateway(ledger).preflight(awareness=awareness, canonical_root=None, reconciliation_proof=proof)
                self.assertEqual((preflight["status"], preflight["can_release"], preflight["authority_granted"]), ("PASS", True, False))
                packet = SignalIntakeGateway(ledger).release(preflight=preflight, included_signal_refs=(), awareness=awareness)
                self.assertFalse(packet["execution_authorized"])
            finally:
                ledger.close()

    def test_r137_r031_evidence_contains_raw_review_facts_not_adjudication(self) -> None:
        bundle, _ = self.observe()
        self.assertEqual(bundle.reviews[0].state, "APPROVED")
        self.assertFalse(hasattr(bundle, "review_accepted"))

    def test_r137_r032_evidence_is_public_safe_metadata(self) -> None:
        bundle, _ = self.observe()
        self.assertTrue(all("content" not in item for item in bundle.request_response_metadata))
        self.assertTrue(all(record.content_sha256 for record in bundle.exact_objects))

    def test_r137_r033_serial_transport_has_no_executor_or_scheduler(self) -> None:
        source = Path(provider_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("ThreadPoolExecutor", source)
        self.assertNotIn("schedule", source.casefold())

    def test_r137_r034_only_get_endpoint_shapes_are_generated(self) -> None:
        _, _ = self.observe()
        source = Path(provider_module.__file__).read_text(encoding="utf-8")
        self.assertIn('connection.request("GET", path', source)
        self.assertNotIn('connection.request("POST"', source)

    def test_r137_r035_pr_review_commit_is_recorded_not_approved(self) -> None:
        bundle, _ = self.observe()
        self.assertEqual(bundle.reviews[0].commit_id, "c" * 40)

    def test_r137_r036_bootstrap_cannot_validate_as_observation(self) -> None:
        _, proof = self.observe()
        self.assertFalse(validate_live_observation_proof(replace(proof, provider_id="ROOT-PROVIDER-BOOTSTRAP-R137-0001")))

    def test_r137_r037_bundle_has_initial_final_and_exact_object_binding(self) -> None:
        bundle, _ = self.observe()
        self.assertEqual(len(bundle.exact_objects), len(CONTROL_PATHS) + 1)
        self.assertTrue(all(record.commit_sha == bundle.initial_main_sha for record in bundle.exact_objects))

    def test_r137_r038_bundle_invalidation_is_complete(self) -> None:
        bundle, _ = self.observe()
        self.assertEqual(set(bundle.invalidation_fingerprints), {"pr_number", "pr_state", "head_sha", "base_sha", "current_main_sha", "review_state_ref", "merged", "merge_commit_sha", "route_fingerprint", "claim_fingerprint", "lane_fingerprint", "lease_fingerprint", "domain_freshness_ref", "pending_approval_ref"})

    def test_r137_r039_no_private_or_credential_request_surface(self) -> None:
        fields = set(LiveObservationRequest.__dataclass_fields__)
        self.assertFalse(fields & {"token", "credential", "private_repository", "url"})

    def test_r137_r040_no_generic_host_surface(self) -> None:
        self.assertFalse(hasattr(LiveObservationProvider, "request_url"))
        self.assertEqual(API_HOST, "api.github.com")
        with self.assertRaises(GatewayError):
            LiveObservationProvider()._get_json(f"/repos/{TARGET_REPOSITORY}/issues")

    def test_r137_r041_proof_has_bounded_freshness(self) -> None:
        bundle, proof = self.observe()
        self.assertLessEqual((datetime.fromisoformat(bundle.fresh_until) - datetime.fromisoformat(bundle.completed_at)).total_seconds(), MAX_AGE_SECONDS)
        self.assertEqual(proof.fresh_until, bundle.fresh_until)

    def test_r137_r042_provider_code_identity_is_bound(self) -> None:
        bundle, _ = self.observe()
        self.assertEqual(bundle.provider_code_ref, "global_signal_gateway/live_observation_provider.py")
        self.assertEqual(len(bundle.provider_code_digest), 64)

    def test_r137_r043_observation_request_is_not_a_live_proof(self) -> None:
        self.assertFalse(validate_live_observation_proof(request()))

    def test_r137_r044_rollback_is_additive_and_r136_unknown_stays_closed(self) -> None:
        self.assertFalse(validate_live_observation_proof(object()))


if __name__ == "__main__":
    unittest.main()
