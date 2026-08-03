"""E42 synthetic trust-boundary tests.  No request leaves this process."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.parse import parse_qs, unquote, urlparse


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.durable_authority import (  # noqa: E402
    AuthorityProvenanceBinding,
    AuthorityProvenanceVerifier,
    ClaimHolder,
    DurableClaimAuthority,
    DurableClaimResultCode,
    DurableClaimState,
    FixedRepositoryGitHubCasGateway,
    OwnerType,
    RevisionedObject,
    SyntheticFileCasGateway,
    VerifiedAuthorityProvenance,
)
from brainops_control_plane.execution_evidence import (  # noqa: E402
    CapabilityTarget,
    ExecutionEvidenceType,
    RawCapabilityObservation,
    RawInvocationReceipt,
    VerifiedCapabilityObservation,
    VerifiedInvocationReceipt,
    _trusted_evidence_verifier,
    classify_execution,
    evaluate_capability,
)
from brainops_control_plane.github_contents_cas import (  # noqa: E402
    API_ROOT,
    CasTransportStatus,
    FixedGitHubContentsCasClient,
    HttpRequest,
    HttpResponse,
)
from brainops_control_plane.models import BoundCanaryApproval, CapabilityStatus, RouteRef, RouteState, ValidationError  # noqa: E402
from brainops_control_plane.proofs import (  # noqa: E402
    CANONICAL_ACTIVE_TASK_PATH,
    CANONICAL_COORDINATION_PATH,
    CANONICAL_MAIN_REF,
    CANONICAL_REPOSITORY,
    CanonicalApprovalBinding,
    ReadOnlyApprovalVerifier,
    ReadOnlyRouteProofVerifier,
    RouteFileIdentity,
    _fetched_approval_document,
    _fetched_route_snapshot,
    _git_blob_sha1,
    canonical_approval_ref,
)
from brainops_control_plane.route_terminalization import (  # noqa: E402
    CanonicalTerminalState,
    RawCanonicalRouteTerminalization,
    RouteExecutionDisposition,
    TerminalizationVerificationStatus,
    VerifiedCanonicalRouteTerminalization,
    _canonical_terminalization_verifier,
    evaluate_route_terminalization,
)


NOW = "2026-08-02T12:02:00Z"
OBSERVED = "2026-08-02T12:00:00Z"
ISSUED = "2026-08-02T12:01:00Z"
EXPIRES = "2026-08-02T13:00:00Z"
HASH = "a" * 64
TASK = "task.e42"
ROUTE_ID = "route.e42"
CANARY = "canary.e42"
NONCE = "nonce.e42"
SCOPE = "synthetic.effect"
ACTOR = "gpt-reviewer"


def _identity(path: str, content: bytes) -> RouteFileIdentity:
    return RouteFileIdentity(path, _git_blob_sha1(content), hashlib.sha256(content).hexdigest())


def _route_snapshot(
    *,
    observed_at: str = OBSERVED,
    task: str = TASK,
    epoch: int = 44,
    actor: str = ACTOR,
    commit_sha1: str = "1" * 40,
    tree_sha1: str = "2" * 40,
):
    active = (
        f"task_id: {task}\n"
        f"route_epoch: {epoch}\n"
        "status: READY\n"
        "execution_allowed: true\n"
        "automatic_dispatch_allowed: false\n"
        "canary_execution_allowed: false\n"
        f"authorized_approval_actors: [{actor}]\n"
    ).encode()
    coordination = (
        "agents:\n"
        "  CODEX:\n"
        f"    task_id: {task}\n"
        f"    route_epoch: {epoch}\n"
        "    status: READY\n"
        "    execution_allowed: true\n"
        "    automatic_dispatch_allowed: false\n"
        "    canary_execution_allowed: false\n"
        f"    authorized_approval_actors: [{actor}]\n"
    ).encode()
    return _fetched_route_snapshot(
        CANONICAL_REPOSITORY,
        CANONICAL_MAIN_REF,
        commit_sha1,
        tree_sha1,
        _identity(CANONICAL_ACTIVE_TASK_PATH, active),
        _identity(CANONICAL_COORDINATION_PATH, coordination),
        active,
        coordination,
        observed_at,
    )


def _approval(
    *,
    actor: str = ACTOR,
    body_task: str = TASK,
    nonce: str = NONCE,
    issue_number: int = 132,
    comment_id: int = 7001,
) -> tuple[BoundCanaryApproval, object]:
    binding = CanonicalApprovalBinding(body_task, 44, CANARY, SCOPE, EXPIRES, nonce)
    body = f"approval\n```brainops-approval-v1\n{binding.canonical_json()}\n```\n"
    approval_ref = canonical_approval_ref(CANONICAL_REPOSITORY, issue_number, comment_id)
    approval = BoundCanaryApproval(
        CANARY,
        TASK,
        44,
        SCOPE,
        EXPIRES,
        NONCE,
        approval_ref,
        repository=CANONICAL_REPOSITORY,
        issue_number=issue_number,
        comment_id=comment_id,
        actor=actor,
        issued_at=ISSUED,
        body_sha256=hashlib.sha256(body.encode()).hexdigest(),
    )
    document = _fetched_approval_document(CANONICAL_REPOSITORY, issue_number, comment_id, actor, ISSUED, body)
    return approval, document


def _provenance(*, snapshot=None, approval_pair=None, checked_at: str = NOW):
    snapshot = snapshot or _route_snapshot()
    approval, document = approval_pair or _approval()
    route_ref = RouteRef(ROUTE_ID, "CODEX", 44)
    route_proof = ReadOnlyRouteProofVerifier().verify(route_ref, TASK, snapshot, checked_at)
    approval_result = ReadOnlyApprovalVerifier().verify(approval, document, route_proof, checked_at)
    return AuthorityProvenanceVerifier().verify(route_proof, approval_result, approval, checked_at)


def _holder(owner_type: OwnerType = OwnerType.CURRENT_CODEX_APP_SESSION, instance: str = "owner.e42.one", correlation: str = "corr.e42.one") -> ClaimHolder:
    return ClaimHolder(owner_type, instance, correlation)


def _authority(root: Path) -> DurableClaimAuthority:
    return DurableClaimAuthority(CANONICAL_REPOSITORY, "e42.claim", SyntheticFileCasGateway(root))


def _claimed(root: Path, *, holder: ClaimHolder | None = None):
    authority = _authority(root)
    provenance = _provenance()
    holder = holder or _holder()
    result = authority.claim(provenance, "claim.e42.one", holder, "2026-08-02T12:03:00Z")
    return authority, provenance, holder, result


def _race_worker(root: str, provenance, start, queue, index: int) -> None:
    start.wait(10)
    authority = _authority(Path(root))
    holder = _holder(instance=f"owner.e42.race.{index}", correlation=f"corr.e42.race.{index}")
    result = authority.claim(provenance, f"claim.e42.race.{index}", holder, "2026-08-02T12:03:00Z")
    queue.put(result.code.value)


class InMemoryGitHubTransport:
    """Small GitHub API model used to execute the real adapter code."""

    def __init__(self) -> None:
        self.repository = CANONICAL_REPOSITORY
        self.branch = "brainops-authority"
        self.head = "1" * 40
        self.trees = {self.head: "2" * 40}
        self.files: dict[str, dict[str, bytes]] = {self.head: {}}
        self.requests: list[HttpRequest] = []
        self.put_status: int | None = None
        self.redirect = False
        self.bad_response_path = False
        self.timeout = False
        self.fail_after_put_read = False
        self.drop_put_response_after_apply = False
        self._next_commit = 3

    @staticmethod
    def _json(status: int, url: str, value: object) -> HttpResponse:
        return HttpResponse(status, url, {"Content-Type": "application/json"}, json.dumps(value).encode())

    def request(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        if self.timeout:
            raise TimeoutError("synthetic timeout")
        if request.follow_redirects:
            raise AssertionError("adapter enabled redirects")
        if self.redirect:
            return HttpResponse(302, request.url + "/redirect", {}, b"")
        parsed = urlparse(request.url)
        prefix = f"/repos/{self.repository}"
        if not parsed.path.startswith(prefix):
            return self._json(404, request.url, {})
        suffix = parsed.path[len(prefix):]
        if request.method == "GET" and suffix == f"/git/ref/heads/{self.branch}":
            return self._json(200, request.url, {"object": {"type": "commit", "sha": self.head}})
        if request.method == "GET" and suffix.startswith("/git/commits/"):
            sha = suffix.rsplit("/", 1)[-1]
            if sha not in self.trees:
                return self._json(404, request.url, {})
            return self._json(200, request.url, {"sha": sha, "tree": {"sha": self.trees[sha]}})
        if request.method == "GET" and suffix.startswith("/contents/"):
            if self.fail_after_put_read and self._next_commit > 3:
                raise OSError("post-write read unavailable")
            path = unquote(suffix.removeprefix("/contents/"))
            commit = parse_qs(parsed.query).get("ref", [self.head])[0]
            content = self.files.get(commit, {}).get(path)
            if content is None:
                return self._json(404, request.url, {"message": "Not Found"})
            response_path = path + ".drift" if self.bad_response_path else path
            return self._json(
                200,
                request.url,
                {
                    "type": "file",
                    "path": response_path,
                    "sha": _git_blob_sha1(content),
                    "encoding": "base64",
                    "content": base64.b64encode(content).decode(),
                },
            )
        if request.method == "PUT" and suffix.startswith("/contents/"):
            if self.put_status is not None:
                return self._json(self.put_status, request.url, {"message": "synthetic rejection"})
            path = unquote(suffix.removeprefix("/contents/"))
            body = json.loads((request.body or b"").decode())
            current = self.files[self.head].get(path)
            expected = body.get("sha")
            if (current is None and expected is not None) or (current is not None and expected != _git_blob_sha1(current)):
                return self._json(409, request.url, {"message": "sha mismatch"})
            content = base64.b64decode(body["content"])
            commit = f"{self._next_commit:040x}"
            tree = f"{self._next_commit + 100:040x}"
            self._next_commit += 1
            self.files[commit] = dict(self.files[self.head])
            self.files[commit][path] = content
            self.trees[commit] = tree
            self.head = commit
            if self.drop_put_response_after_apply:
                raise OSError("synthetic response loss after write")
            response_path = path + ".drift" if self.bad_response_path else path
            return self._json(201 if current is None else 200, request.url, {"content": {"path": response_path, "sha": _git_blob_sha1(content)}, "commit": {"sha": commit}})
        return self._json(405, request.url, {})


def _cas_client(transport: InMemoryGitHubTransport) -> FixedGitHubContentsCasClient:
    return FixedGitHubContentsCasClient(
        CANONICAL_REPOSITORY,
        "refs/heads/brainops-authority",
        "coordination/authority",
        transport,
    )


class ProductionCasAdapterTests(unittest.TestCase):
    def test_create_and_exact_read(self) -> None:
        transport = InMemoryGitHubTransport()
        client = _cas_client(transport)
        created = client.compare_and_set_verified("claim.one", None, b"payload")
        self.assertEqual(created.status, CasTransportStatus.APPLIED)
        self.assertEqual(client.read_verified("claim.one").content.content, b"payload")
        self.assertTrue(all(not request.follow_redirects for request in transport.requests))

    def test_update_requires_expected_blob(self) -> None:
        client = _cas_client(InMemoryGitHubTransport())
        first = client.compare_and_set_verified("claim.one", None, b"one")
        conflict = client.compare_and_set_verified("claim.one", "f" * 40, b"two")
        updated = client.compare_and_set_verified("claim.one", first.content.blob_sha1, b"two")
        self.assertEqual(conflict.status, CasTransportStatus.CONFLICT)
        self.assertEqual(updated.status, CasTransportStatus.APPLIED)

    def test_create_conflicts_when_object_exists(self) -> None:
        client = _cas_client(InMemoryGitHubTransport())
        client.compare_and_set_verified("claim.one", None, b"one")
        self.assertEqual(client.compare_and_set_verified("claim.one", None, b"two").status, CasTransportStatus.CONFLICT)

    def test_http_conflict_codes_are_distinct(self) -> None:
        for status, expected in ((409, CasTransportStatus.CONFLICT), (412, CasTransportStatus.PRECONDITION_FAILED), (422, CasTransportStatus.UNPROCESSABLE)):
            with self.subTest(status=status):
                transport = InMemoryGitHubTransport()
                transport.put_status = status
                self.assertEqual(_cas_client(transport).compare_and_set_verified("claim.one", None, b"one").status, expected)

    def test_redirect_is_rejected(self) -> None:
        transport = InMemoryGitHubTransport()
        transport.redirect = True
        self.assertEqual(_cas_client(transport).read_verified("claim.one").status, CasTransportStatus.REDIRECT_REJECTED)

    def test_response_path_drift_is_rejected(self) -> None:
        transport = InMemoryGitHubTransport()
        transport.bad_response_path = True
        self.assertEqual(_cas_client(transport).compare_and_set_verified("claim.one", None, b"one").status, CasTransportStatus.RESPONSE_IDENTITY_MISMATCH)

    def test_timeout_is_bounded_and_fail_closed(self) -> None:
        transport = InMemoryGitHubTransport()
        transport.timeout = True
        result = _cas_client(transport).read_verified("claim.one")
        self.assertEqual(result.status, CasTransportStatus.TIMEOUT)
        self.assertEqual(len(transport.requests), 2)

    def test_post_write_recovery_failure_is_fail_closed(self) -> None:
        transport = InMemoryGitHubTransport()
        transport.fail_after_put_read = True
        result = _cas_client(transport).compare_and_set_verified("claim.one", None, b"one")
        self.assertEqual(result.status, CasTransportStatus.TRANSPORT_ERROR)

    def test_lost_write_response_never_grants_applied(self) -> None:
        transport = InMemoryGitHubTransport()
        transport.drop_put_response_after_apply = True
        result = _cas_client(transport).compare_and_set_verified("claim.one", None, b"one")
        self.assertEqual(result.status, CasTransportStatus.WRITE_OUTCOME_UNKNOWN)
        self.assertEqual(result.content.content, b"one")
        puts = [request for request in transport.requests if request.method == "PUT"]
        self.assertEqual(len(puts), 1)

    def test_gateway_cannot_be_retargeted(self) -> None:
        client = _cas_client(InMemoryGitHubTransport())
        with self.assertRaises(OSError):
            client.read_content("example/other", "refs/heads/brainops-authority", "coordination/authority/claim.one.json")

    def test_gateway_executes_adapter_contract(self) -> None:
        transport = InMemoryGitHubTransport()
        client = _cas_client(transport)
        gateway = FixedRepositoryGitHubCasGateway(CANONICAL_REPOSITORY, "refs/heads/brainops-authority", "coordination/authority", client)
        result = gateway.compare_and_set("claim.one", None, b"payload")
        self.assertTrue(result.applied)
        self.assertEqual(gateway.read("claim.one").payload, b"payload")


class ProvenanceAndOwnerTests(unittest.TestCase):
    def test_verified_provenance_binds_exact_route_and_approval(self) -> None:
        binding = _provenance().binding
        self.assertEqual(binding.route_commit_sha1, "1" * 40)
        self.assertEqual(binding.route_tree_sha1, "2" * 40)
        self.assertEqual(binding.route_path, CANONICAL_ACTIVE_TASK_PATH)
        self.assertEqual(binding.approval_comment_id, 7001)
        self.assertEqual(binding.approval_actor, ACTOR)
        self.assertEqual(binding.scope, SCOPE)

    def test_provenance_cannot_be_constructed_by_caller(self) -> None:
        with self.assertRaises(ValidationError):
            VerifiedAuthorityProvenance(_provenance().binding)

    def test_route_task_substitution_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            _provenance(snapshot=_route_snapshot(task="task.other"))

    def test_approval_body_substitution_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            _provenance(approval_pair=_approval(body_task="task.other"))

    def test_approval_actor_substitution_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            _provenance(approval_pair=_approval(actor="other-actor"))

    def test_approval_nonce_substitution_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            _provenance(approval_pair=_approval(nonce="nonce.other"))

    def test_claim_winner_receives_sealed_effect_permit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            permit = authority.acquire_effect_permit(provenance, result.record.claim_id, holder, "2026-08-02T12:03:01Z")
        self.assertEqual(permit.permit_type, "DURABLE_CLAIM_ACQUIRED_EFFECT_MAY_PROCEED")
        self.assertEqual(permit.holder, holder)

    def test_nonwinner_cannot_receive_effect_permit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, _holder_one, _ = _claimed(Path(directory))
            permit = authority.acquire_effect_permit(provenance, "claim.e42.other", _holder(instance="owner.e42.other"), "2026-08-02T12:03:01Z")
        self.assertIsNone(permit)

    def test_expired_approval_cannot_create_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValidationError):
                _authority(Path(directory)).claim(
                    _provenance(),
                    "claim.e42.late",
                    _holder(),
                    "2026-08-02T13:00:00Z",
                )

    def test_expired_approval_cannot_mint_effect_permit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            permit = authority.acquire_effect_permit(provenance, result.record.claim_id, holder, "2026-08-02T13:00:00Z")
        self.assertIsNone(permit)

    def test_different_owner_instance_cannot_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            wrong = ClaimHolder(holder.owner_type, "owner.e42.other", holder.claimant_correlation_id)
            final = authority.finalize(provenance, result.record.claim_id, wrong, DurableClaimState.FAILED, "failed", "2026-08-02T12:04:00Z")
        self.assertEqual(final.code, DurableClaimResultCode.CLAIM_OWNER_MISMATCH)

    def test_different_correlation_cannot_attach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            wrong = ClaimHolder(holder.owner_type, holder.owner_instance_id, "corr.e42.other")
            attached = authority.attach_invocation(provenance, result.record.claim_id, wrong, "invoke.e42.one")
        self.assertEqual(attached.code, DurableClaimResultCode.CLAIM_OWNER_MISMATCH)

    def test_recovery_requires_same_holder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            wrong = ClaimHolder(holder.owner_type, "owner.e42.other", holder.claimant_correlation_id)
            recovered = authority.recover_expired_claim(provenance, result.record.claim_id, wrong, "2026-08-02T12:10:00Z", 30)
        self.assertEqual(recovered.code, DurableClaimResultCode.CLAIM_OWNER_MISMATCH)

    def test_four_process_race_has_one_cas_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            queue = context.Queue()
            provenance = _provenance()
            processes = [context.Process(target=_race_worker, args=(directory, provenance, start, queue, index)) for index in range(4)]
            for process in processes:
                process.start()
            start.set()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            values = [queue.get(timeout=3) for _ in processes]
        self.assertEqual(values.count(DurableClaimResultCode.CLAIMED.value), 1)
        self.assertEqual(values.count(DurableClaimResultCode.ALREADY_CLAIMED.value), 3)

    def test_restart_reads_same_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, provenance, _holder_one, _ = _claimed(root)
            restarted = _authority(root).claim(provenance, "claim.e42.two", _holder(instance="owner.e42.two"), "2026-08-02T12:03:30Z")
        self.assertEqual(restarted.code, DurableClaimResultCode.ALREADY_CLAIMED)

    def test_tampered_persisted_provenance_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, provenance, _holder_one, result = _claimed(root)
            path = next(root.glob("*.json"))
            document = json.loads(path.read_text())
            document["provenance"]["route_commit_sha1"] = "f" * 40
            path.write_text(json.dumps(document))
            observed = authority.read(provenance)
        self.assertEqual(observed.code, DurableClaimResultCode.PROVENANCE_MISMATCH)

    def test_route_commit_substitution_cannot_create_second_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _original, _holder_one, _ = _claimed(root)
            substituted = _provenance(snapshot=_route_snapshot(commit_sha1="9" * 40, tree_sha1="8" * 40))
            result = authority.claim(substituted, "claim.e42.substitute", _holder(instance="owner.e42.substitute"), "2026-08-02T12:03:30Z")
        self.assertEqual(result.code, DurableClaimResultCode.PROVENANCE_MISMATCH)

    def test_approval_comment_substitution_cannot_create_second_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority, _original, _holder_one, _ = _claimed(root)
            substituted = _provenance(approval_pair=_approval(comment_id=7002))
            result = authority.claim(substituted, "claim.e42.substitute", _holder(instance="owner.e42.substitute"), "2026-08-02T12:03:30Z")
        self.assertEqual(result.code, DurableClaimResultCode.PROVENANCE_MISMATCH)


class TrustedExecutionEvidenceTests(unittest.TestCase):
    def _claim_with_invocation(self, root: Path, holder: ClaimHolder):
        authority, provenance, _, result = _claimed(root, holder=holder)
        attached = authority.attach_invocation(provenance, result.record.claim_id, holder, "invoke.e42.one")
        return authority, provenance, attached.record

    def test_raw_capability_is_not_accepted(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e42", "transport.e42")
        self.assertEqual(evaluate_capability(CapabilityTarget.CODEX_APP, raw).status, CapabilityStatus.BLOCKED)

    def test_verified_capability_is_accepted(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e42", "transport.e42")
        verified = _trusted_evidence_verifier("transport.e42").verify_capability(raw, NOW)
        self.assertEqual(evaluate_capability(CapabilityTarget.CODEX_APP, verified).status, CapabilityStatus.SUPPORTED)

    def test_verified_capability_constructor_is_sealed(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e42", "transport.e42")
        with self.assertRaises(ValidationError):
            VerifiedCapabilityObservation(raw, NOW)

    def _manual_raw(self, claim, **changes) -> RawInvocationReceipt:
        values = dict(
            claim_id=claim.claim_id,
            invocation_id="invoke.e42.one",
            holder=claim.holder,
            evidence_type=ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION,
            started_at="2026-08-02T12:03:10Z",
            ended_at="2026-08-02T12:03:20Z",
            terminal_status="completed",
            log_hash=HASH,
            cleanup_proof_hash=HASH,
            transport_identity="transport.e42",
            non_attempted_owners=(OwnerType.APP_AUTOMATION_NEW_RUN, OwnerType.CODEX_CLI_PROCESS),
            session_id="session.e42",
        )
        values.update(changes)
        return RawInvocationReceipt(**values)

    def test_raw_invocation_cannot_classify_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            with self.assertRaises(ValidationError):
                classify_execution(claim, self._manual_raw(claim))

    def test_verified_manual_receipt_stays_manual(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            verifier = _trusted_evidence_verifier("transport.e42")
            verified = verifier.verify_invocation(claim, self._manual_raw(claim), "2026-08-02T12:03:30Z")
            assessment = classify_execution(claim, verified)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION)

    def test_manual_cannot_promote_to_app_automation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            raw = self._manual_raw(
                claim,
                evidence_type=ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN,
                session_id=None,
                dispatch_receipt_hash=HASH,
                callback_transport_identity="transport.e42",
                callback_proof_hash=HASH,
            )
            with self.assertRaises(ValidationError):
                _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")

    def test_owner_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            raw = self._manual_raw(claim, holder=_holder(instance="owner.e42.other"))
            with self.assertRaises(ValidationError):
                _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")

    def test_non_attempted_owner_set_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            raw = self._manual_raw(claim, non_attempted_owners=(OwnerType.CODEX_CLI_PROCESS,))
            with self.assertRaises(ValidationError):
                _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")

    def test_app_automation_requires_callback_identity(self) -> None:
        holder = _holder(OwnerType.APP_AUTOMATION_NEW_RUN)
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), holder)
            raw = RawInvocationReceipt(
                claim.claim_id, "invoke.e42.one", holder, ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN,
                "2026-08-02T12:03:10Z", "2026-08-02T12:03:20Z", "completed", HASH, HASH,
                "transport.e42", (OwnerType.CURRENT_CODEX_APP_SESSION, OwnerType.CODEX_CLI_PROCESS),
                dispatch_receipt_hash=HASH, callback_transport_identity="other.transport", callback_proof_hash=HASH,
            )
            with self.assertRaises(ValidationError):
                _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")

    def test_verified_app_automation_stays_automation(self) -> None:
        holder = _holder(OwnerType.APP_AUTOMATION_NEW_RUN)
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), holder)
            raw = RawInvocationReceipt(
                claim.claim_id, "invoke.e42.one", holder, ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN,
                "2026-08-02T12:03:10Z", "2026-08-02T12:03:20Z", "completed", HASH, HASH,
                "transport.e42", (OwnerType.CURRENT_CODEX_APP_SESSION, OwnerType.CODEX_CLI_PROCESS),
                dispatch_receipt_hash=HASH, callback_transport_identity="transport.e42", callback_proof_hash=HASH,
            )
            verified = _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")
        self.assertEqual(classify_execution(claim, verified).evidence_type, ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN)

    def test_cli_requires_process_identity(self) -> None:
        holder = _holder(OwnerType.CODEX_CLI_PROCESS)
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), holder)
            raw = RawInvocationReceipt(
                claim.claim_id, "invoke.e42.one", holder, ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED,
                "2026-08-02T12:03:10Z", "2026-08-02T12:03:20Z", "completed", HASH, HASH,
                "transport.e42", (OwnerType.CURRENT_CODEX_APP_SESSION, OwnerType.APP_AUTOMATION_NEW_RUN),
                process_launcher_identity="transport.e42", process_id=None, process_token="process.e42", exit_code=0,
            )
            with self.assertRaises(ValidationError):
                _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")

    def test_verified_cli_stays_cli(self) -> None:
        holder = _holder(OwnerType.CODEX_CLI_PROCESS)
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), holder)
            raw = RawInvocationReceipt(
                claim.claim_id, "invoke.e42.one", holder, ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED,
                "2026-08-02T12:03:10Z", "2026-08-02T12:03:20Z", "completed", HASH, HASH,
                "transport.e42", (OwnerType.CURRENT_CODEX_APP_SESSION, OwnerType.APP_AUTOMATION_NEW_RUN),
                process_launcher_identity="transport.e42", process_id=42, process_token="process.e42", exit_code=0,
            )
            verified = _trusted_evidence_verifier("transport.e42").verify_invocation(claim, raw, "2026-08-02T12:03:30Z")
        self.assertEqual(classify_execution(claim, verified).evidence_type, ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED)

    def test_duplicate_callback_is_durably_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            authority.attach_invocation(provenance, result.record.claim_id, holder, "invoke.e42.one")
            duplicate = authority.attach_invocation(provenance, result.record.claim_id, holder, "invoke.e42.one")
        self.assertEqual(duplicate.code, DurableClaimResultCode.DUPLICATE_INVOCATION)

    def test_verified_receipt_constructor_is_sealed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            with self.assertRaises(ValidationError):
                VerifiedInvocationReceipt(self._manual_raw(claim), NOW)


def _terminal_snapshot(record, *, published_at: str = "2026-08-02T12:05:00Z", complete: bool = True, task: str = TASK):
    if complete:
        active = (
            f"route_id: {ROUTE_ID}\nroute_epoch: 44\ntask_id: {task}\ncanary_id: {CANARY}\nnonce: {NONCE}\n"
            f"status: BLOCKED\ndurable_claim_id: {record.claim_id}\ndurable_terminal_state: CONSUMED\n"
            f"durable_terminal_at: {record.terminal_at}\npublished_at: {published_at}\n"
        ).encode()
    else:
        active = b"status: BLOCKED\n"
    coordination = b"status: BLOCKED\n"
    return _fetched_route_snapshot(
        CANONICAL_REPOSITORY,
        CANONICAL_MAIN_REF,
        "3" * 40,
        "4" * 40,
        _identity(CANONICAL_ACTIVE_TASK_PATH, active),
        _identity(CANONICAL_COORDINATION_PATH, coordination),
        active,
        coordination,
        "2026-08-02T12:05:00Z",
    )


class CanonicalTerminalizationTests(unittest.TestCase):
    def _terminal_record(self, root: Path):
        authority, provenance, holder, result = _claimed(root)
        return authority.finalize(provenance, result.record.claim_id, holder, DurableClaimState.SUCCEEDED, "completed", "2026-08-02T12:04:00Z").record

    def test_raw_terminalization_cannot_be_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            raw = RawCanonicalRouteTerminalization(RouteState.BLOCKED, record.claim_id, CanonicalTerminalState.CONSUMED, record.terminal_at)
            decision = evaluate_route_terminalization(RouteState.BLOCKED, record, raw)
        self.assertFalse(decision.canonical_terminalization_verified)

    def test_verified_terminalization_binds_remote_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            verifier = _canonical_terminalization_verifier(CANONICAL_REPOSITORY, CANONICAL_MAIN_REF, CANONICAL_ACTIVE_TASK_PATH)
            result = verifier.verify(_terminal_snapshot(record), record, "2026-08-02T12:06:00Z")
        self.assertEqual(result.status, TerminalizationVerificationStatus.VERIFIED)
        self.assertEqual(result.terminalization.commit_sha1, "3" * 40)
        self.assertTrue(evaluate_route_terminalization(RouteState.BLOCKED, record, result).canonical_terminalization_verified)

    def test_generic_blocked_route_is_publication_pending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            verifier = _canonical_terminalization_verifier(CANONICAL_REPOSITORY, CANONICAL_MAIN_REF, CANONICAL_ACTIVE_TASK_PATH)
            result = verifier.verify(_terminal_snapshot(record, complete=False), record, "2026-08-02T12:06:00Z")
            decision = evaluate_route_terminalization(RouteState.BLOCKED, record, result)
        self.assertEqual(result.status, TerminalizationVerificationStatus.PENDING)
        self.assertEqual(decision.disposition, RouteExecutionDisposition.DURABLE_TERMINAL_ROUTE_PUBLICATION_PENDING)

    def test_publication_before_terminal_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            verifier = _canonical_terminalization_verifier(CANONICAL_REPOSITORY, CANONICAL_MAIN_REF, CANONICAL_ACTIVE_TASK_PATH)
            result = verifier.verify(_terminal_snapshot(record, published_at="2026-08-02T12:03:00Z"), record, "2026-08-02T12:06:00Z")
        self.assertEqual(result.status, TerminalizationVerificationStatus.REJECTED)

    def test_route_task_substitution_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            verifier = _canonical_terminalization_verifier(CANONICAL_REPOSITORY, CANONICAL_MAIN_REF, CANONICAL_ACTIVE_TASK_PATH)
            result = verifier.verify(_terminal_snapshot(record, task="task.other"), record, "2026-08-02T12:06:00Z")
        self.assertEqual(result.status, TerminalizationVerificationStatus.REJECTED)

    def test_terminal_constructor_is_sealed(self) -> None:
        with self.assertRaises(ValidationError):
            VerifiedCanonicalRouteTerminalization({})

    def test_stale_ready_route_is_blocked_by_durable_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            record = self._terminal_record(Path(directory))
            decision = evaluate_route_terminalization(RouteState.READY, record)
        self.assertEqual(decision.disposition, RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL)


class ImportedPrimitiveRegressionTests(unittest.TestCase):
    def test_revisioned_object_accepts_git_blob_sha(self) -> None:
        value = RevisionedObject("a" * 40, b"payload")
        self.assertEqual(value.payload_sha256, hashlib.sha256(b"payload").hexdigest())

    def test_revisioned_object_rejects_digest_substitution(self) -> None:
        with self.assertRaises(ValidationError):
            RevisionedObject("a" * 40, b"payload", "b" * 64)


if __name__ == "__main__":
    unittest.main()
