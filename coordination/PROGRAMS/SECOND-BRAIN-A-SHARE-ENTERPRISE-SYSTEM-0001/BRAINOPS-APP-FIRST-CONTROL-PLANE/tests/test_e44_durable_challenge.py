"""E44 synthetic durable-challenge tests.  No request leaves this process."""

from __future__ import annotations

import base64
from dataclasses import replace
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
    _governed_recovery_authorization,
    _governed_recovery_principal,
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
from brainops_control_plane.terminal_attestation import (  # noqa: E402
    AttestationCode,
    AttestationError,
    BoundedTransportEnvelope,
    InvocationLifecycleState,
    RawCapabilityTransportObservation,
    RawInvocationTransportObservation,
    TerminalExecutionReconciler,
    _bounded_transport_attestor,
    _one_shot_challenge,
)
from brainops_control_plane.durable_challenge import (  # noqa: E402
    AutomationTerminalEvidence,
    CapabilityWitness,
    CliTerminalEvidence,
    CapabilityDecisionUseLedger,
    DurableChallengeLedger,
    LedgerCode,
    ManualAppTerminalEvidence,
    RecoveryAuthorizationLedger,
    _mint_challenge,
    _synthetic_transport_witness_verifier,
    bind_challenge_decision,
    evaluate_challenge_capability,
    recovery_grant_from_claim,
    validate_owner_terminal_evidence,
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


def _seed_claim_record(authority: DurableClaimAuthority, record):
    """Test-only fixture writer; never used by production authority paths."""

    object_id = authority._object_id(record.key)
    snapshot = authority._gateway.read(object_id)
    write = authority._gateway.compare_and_set(object_id, snapshot.revision, record.document_bytes)
    if not write.applied:
        raise AssertionError("test fixture CAS failed")
    return record


def _seed_invocation_record(authority: DurableClaimAuthority, record, invocation_id: str):
    return _seed_claim_record(authority, replace(record, invocation_id=invocation_id))


def _seed_terminal_record(
    authority: DurableClaimAuthority,
    record,
    state: DurableClaimState,
    reason: str,
    terminal_at: str,
    *,
    invocation_id: str | None = None,
):
    if invocation_id is not None and record.invocation_id is None:
        record = _seed_invocation_record(authority, record, invocation_id)
    return _seed_claim_record(authority, replace(record, state=state, terminal_reason=reason, terminal_at=terminal_at))


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

    def test_legacy_claim_winner_does_not_receive_effect_permit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            permit = authority.acquire_effect_permit(provenance, result.record.claim_id, holder, "2026-08-02T12:03:01Z")
        self.assertIsNone(permit)

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
        self.assertEqual(final.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_different_correlation_cannot_attach(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            wrong = ClaimHolder(holder.owner_type, holder.owner_instance_id, "corr.e42.other")
            attached = authority.attach_invocation(provenance, result.record.claim_id, wrong, "invoke.e42.one")
        self.assertEqual(attached.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_recovery_requires_same_holder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            wrong = ClaimHolder(holder.owner_type, "owner.e42.other", holder.claimant_correlation_id)
            recovered = authority.recover_expired_claim(provenance, result.record.claim_id, wrong, "2026-08-02T12:10:00Z", 30)
        self.assertEqual(recovered.code, DurableClaimResultCode.RECOVERY_UNAUTHORIZED)

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
        attached = _seed_invocation_record(authority, result.record, "invoke.e42.one")
        return authority, provenance, attached

    def test_raw_capability_is_not_accepted(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e42", "transport.e42")
        self.assertEqual(evaluate_capability(CapabilityTarget.CODEX_APP, raw).status, CapabilityStatus.BLOCKED)

    def test_verified_capability_is_accepted(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e42", "transport.e42")
        verified = _trusted_evidence_verifier("transport.e42").verify_capability(raw, NOW)
        decision = evaluate_capability(CapabilityTarget.CODEX_APP, verified)
        self.assertEqual(decision.status, CapabilityStatus.BLOCKED)
        self.assertEqual(decision.reason_code, "legacy_capability_observational_only")

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

    def test_verified_manual_receipt_is_observational_until_e43_reconciles(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _authority_one, _provenance_one, claim = self._claim_with_invocation(Path(directory), _holder())
            verifier = _trusted_evidence_verifier("transport.e42")
            verified = verifier.verify_invocation(claim, self._manual_raw(claim), "2026-08-02T12:03:30Z")
            assessment = classify_execution(claim, verified)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY)
        self.assertEqual(assessment.reason_code, "execution_in_progress_or_unreconciled")

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

    def test_verified_app_automation_is_observational_until_e43_reconciles(self) -> None:
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
        assessment = classify_execution(claim, verified)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY)
        self.assertEqual(assessment.reason_code, "execution_in_progress_or_unreconciled")

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

    def test_verified_cli_is_observational_until_e43_reconciles(self) -> None:
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
        assessment = classify_execution(claim, verified)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY)
        self.assertEqual(assessment.reason_code, "execution_in_progress_or_unreconciled")

    def test_legacy_duplicate_callback_path_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, result = _claimed(Path(directory))
            authority.attach_invocation(provenance, result.record.claim_id, holder, "invoke.e42.one")
            duplicate = authority.attach_invocation(provenance, result.record.claim_id, holder, "invoke.e42.one")
        self.assertEqual(duplicate.code, DurableClaimResultCode.EFFECT_BLOCKED)

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
        return _seed_terminal_record(authority, result.record, DurableClaimState.SUCCEEDED, "completed", "2026-08-02T12:04:00Z")

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


class E43TerminalAttestationTests(unittest.TestCase):
    """Adversarial E43 checks that exercise state and evidence, not labels."""

    def _attached_claim(self, root: Path):
        authority, provenance, holder, claimed = _claimed(root)
        self.assertEqual(claimed.code, DurableClaimResultCode.CLAIMED)
        attached = _seed_invocation_record(authority, claimed.record, "invocation.e43.one")
        return authority, provenance, holder, attached

    @staticmethod
    def _challenge(holder: ClaimHolder, *, challenge_id: str = "challenge.e43.one", nonce: str = NONCE, issued: str = "2026-08-02T12:03:00Z", expires: str = "2026-08-02T12:10:00Z", max_age: int = 60):
        return _one_shot_challenge(
            challenge_id,
            CapabilityTarget.CODEX_APP,
            holder,
            TASK,
            44,
            CANARY,
            nonce,
            issued,
            expires,
            max_age,
        )

    @staticmethod
    def _raw_terminal(holder: ClaimHolder, *, challenge_id: str = "challenge.e43.one", nonce: str = NONCE, terminal_at: str = "2026-08-02T12:05:00Z", status: str = "completed", started_at: str = "2026-08-02T12:04:00Z", exit_code: int | None = None):
        return RawInvocationTransportObservation(
            challenge_id=challenge_id,
            target=CapabilityTarget.CODEX_APP,
            claim_id="claim.e42.one",
            invocation_id="invocation.e43.one",
            owner=holder,
            evidence_type=ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION,
            task_id=TASK,
            route_epoch=44,
            canary_id=CANARY,
            nonce=nonce,
            started_at=started_at,
            terminal_at=terminal_at,
            terminal_status=status,
            exit_code=exit_code,
            log_hash=HASH,
            transport_identity="transport.e43",
        )

    def _started_and_observed(self, root: Path, *, exit_code: int | None = None):
        authority, provenance, holder, record = self._attached_claim(root)
        challenge = self._challenge(holder)
        started = TerminalExecutionReconciler.begin(record, challenge, "invocation.e43.one", "2026-08-02T12:04:00Z")
        envelope = _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder, exit_code=exit_code), "2026-08-02T12:05:01Z")
        return authority, provenance, holder, record, TerminalExecutionReconciler.observe_terminal(started, envelope)

    def test_claimed_receipt_is_only_in_progress_until_durable_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, record, observed = self._started_and_observed(Path(directory))
            result = TerminalExecutionReconciler.classify(record, observed)
        self.assertEqual(result.code, AttestationCode.EXECUTION_IN_PROGRESS_OR_UNRECONCILED)
        self.assertEqual(result.lifecycle_state, InvocationLifecycleState.INVOCATION_STARTED)

    def test_terminal_receipt_cannot_reconcile_claimed_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, _, _, record, observed = self._started_and_observed(Path(directory))
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.reconcile(observed, record, "2026-08-02T12:05:02Z")
        self.assertEqual(raised.exception.code, AttestationCode.DURABLE_STATE_INVALID)

    def test_matching_legacy_terminal_decision_cannot_classify_positive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, _provenance_one, holder, attached, observed = self._started_and_observed(Path(directory))
            finalized = _seed_terminal_record(authority, attached, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:00Z")
            challenge = _mint_challenge("challenge.e44.positive", CapabilityTarget.CODEX_APP, holder, TASK, 44, CANARY, NONCE, "2026-08-02T12:03:00Z", "2026-08-02T12:10:00Z", 60)
            ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "challenge"))
            self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
            capability = _claim_bound_capability(ledger, challenge, finalized)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(finalized, capability, _manual_terminal_evidence(finalized))
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.reconcile(observed, finalized, "2026-08-02T12:05:02Z")
        self.assertEqual(raised.exception.code, AttestationCode.TERMINAL_MISMATCH)

    def test_manual_terminal_with_process_exit_code_fails_before_positive_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, _provenance_one, holder, attached, observed = self._started_and_observed(Path(directory), exit_code=0)
            finalized = _seed_terminal_record(authority, attached, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:00Z")
            challenge = _mint_challenge("challenge.e44.exit", CapabilityTarget.CODEX_APP, holder, TASK, 44, CANARY, NONCE, "2026-08-02T12:03:00Z", "2026-08-02T12:10:00Z", 60)
            ledger = DurableChallengeLedger("ledger.e44.exit", SyntheticFileCasGateway(Path(directory) / "challenge"))
            self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
            capability = _claim_bound_capability(ledger, challenge, finalized)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(finalized, capability, _manual_terminal_evidence(finalized))

    def test_terminal_status_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, record = self._attached_claim(Path(directory))
            challenge = self._challenge(holder)
            started = TerminalExecutionReconciler.begin(record, challenge, "invocation.e43.one", "2026-08-02T12:04:00Z")
            envelope = _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder, status="failed"), "2026-08-02T12:05:01Z")
            observed = TerminalExecutionReconciler.observe_terminal(started, envelope)
            finalized = _seed_terminal_record(authority, record, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:00Z")
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.reconcile(observed, finalized, "2026-08-02T12:05:02Z")
        self.assertEqual(raised.exception.code, AttestationCode.TERMINAL_MISMATCH)

    def test_terminal_time_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, _provenance_one, holder, attached, observed = self._started_and_observed(Path(directory))
            finalized = _seed_terminal_record(authority, attached, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:03Z")
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.reconcile(observed, finalized, "2026-08-02T12:05:04Z")
        self.assertEqual(raised.exception.code, AttestationCode.TERMINAL_MISMATCH)

    def test_raw_transport_string_cannot_substitute_for_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            _, _, holder, record = self._attached_claim(Path(directory))
            challenge = self._challenge(holder)
            started = TerminalExecutionReconciler.begin(record, challenge, "invocation.e43.one", "2026-08-02T12:04:00Z")
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.observe_terminal(started, self._raw_terminal(holder))
        self.assertEqual(raised.exception.code, AttestationCode.TRANSPORT_UNATTESTED)

    def test_challenge_replay_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder)
        attestor = _bounded_transport_attestor("transport.e43")
        first = self._raw_terminal(holder)
        attestor.attest(challenge, first, "2026-08-02T12:05:01Z")
        with self.assertRaises(AttestationError) as raised:
            attestor.attest(challenge, first, "2026-08-02T12:05:02Z")
        self.assertEqual(raised.exception.code, AttestationCode.CHALLENGE_REPLAYED)

    def test_expired_challenge_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder, expires="2026-08-02T12:05:00Z")
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder), "2026-08-02T12:05:00Z")
        self.assertEqual(raised.exception.code, AttestationCode.CHALLENGE_EXPIRED)

    def test_stale_capability_observation_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder, challenge_id="challenge.capability", issued="2026-08-02T12:00:00Z", expires="2026-08-02T12:10:00Z", max_age=15)
        raw = RawCapabilityTransportObservation(
            challenge_id="challenge.capability",
            target=CapabilityTarget.CODEX_APP,
            owner=holder,
            task_id=TASK,
            route_epoch=44,
            canary_id=CANARY,
            nonce=NONCE,
            observed_at="2026-08-02T12:00:00Z",
            status=CapabilityStatus.SUPPORTED,
            evidence_hash=HASH,
            transport_identity="transport.e43",
        )
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, raw, "2026-08-02T12:01:00Z")
        self.assertEqual(raised.exception.code, AttestationCode.OBSERVATION_STALE)

    def test_future_observation_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder)
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder, terminal_at="2026-08-02T12:05:05Z"), "2026-08-02T12:05:01Z")
        self.assertEqual(raised.exception.code, AttestationCode.OBSERVATION_IN_FUTURE)

    def test_cross_owner_challenge_substitution_is_rejected(self) -> None:
        challenge = self._challenge(_holder())
        other = _holder(instance="owner.e43.other", correlation="corr.e43.other")
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(other), "2026-08-02T12:05:01Z")
        self.assertEqual(raised.exception.code, AttestationCode.CHALLENGE_BINDING_MISMATCH)

    def test_cross_nonce_challenge_substitution_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder)
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder, nonce="nonce.e43.other"), "2026-08-02T12:05:01Z")
        self.assertEqual(raised.exception.code, AttestationCode.CHALLENGE_BINDING_MISMATCH)

    def test_cross_target_challenge_substitution_is_rejected(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder)
        raw = self._raw_terminal(holder)
        raw = RawInvocationTransportObservation(**{**raw.__dict__, "target": CapabilityTarget.CODEX_CLI})
        with self.assertRaises(AttestationError) as raised:
            _bounded_transport_attestor("transport.e43").attest(challenge, raw, "2026-08-02T12:05:01Z")
        self.assertEqual(raised.exception.code, AttestationCode.CHALLENGE_BINDING_MISMATCH)

    def test_caller_cannot_construct_transport_envelope(self) -> None:
        holder = _holder()
        challenge = self._challenge(holder)
        with self.assertRaises(ValidationError):
            BoundedTransportEnvelope(challenge, self._raw_terminal(holder), "2026-08-02T12:05:01Z", "transport.e43")

    def test_terminal_before_start_is_rejected_by_raw_contract(self) -> None:
        with self.assertRaises(ValidationError):
            self._raw_terminal(_holder(), started_at="2026-08-02T12:05:00Z", terminal_at="2026-08-02T12:04:00Z")

    def test_late_callback_cannot_match_durable_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, record = self._attached_claim(Path(directory))
            challenge = self._challenge(holder)
            started = TerminalExecutionReconciler.begin(record, challenge, "invocation.e43.one", "2026-08-02T12:04:00Z")
            envelope = _bounded_transport_attestor("transport.e43").attest(challenge, self._raw_terminal(holder, terminal_at="2026-08-02T12:05:05Z"), "2026-08-02T12:05:06Z")
            observed = TerminalExecutionReconciler.observe_terminal(started, envelope)
            finalized = _seed_terminal_record(authority, record, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:00Z")
            with self.assertRaises(AttestationError) as raised:
                TerminalExecutionReconciler.reconcile(observed, finalized, "2026-08-02T12:05:07Z")
        self.assertEqual(raised.exception.code, AttestationCode.TERMINAL_MISMATCH)

    def test_governed_recovery_can_mark_expired_claim_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, claimed = _claimed(Path(directory))
            principal = _governed_recovery_principal("recovery.e43.one")
            grant = recovery_grant_from_claim("recovery.e43.one", claimed.record, "2026-08-02T12:05:00Z", "2026-08-02T12:10:00Z", "holder_timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e43", SyntheticFileCasGateway(Path(directory) / "recovery"))
            self.assertEqual(ledger.issue(grant).code, LedgerCode.ISSUED)
            early = authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:04:00Z")
            recovered = authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:06:00Z")
        self.assertEqual(early.code, DurableClaimResultCode.RECOVERY_TIMEOUT_NOT_REACHED)
        self.assertEqual(recovered.code, DurableClaimResultCode.RECOVERY_RECONCILED)
        self.assertEqual(recovered.record.state, DurableClaimState.RECOVERY_REQUIRED)
        self.assertIsNone(authority.acquire_effect_permit(provenance, "claim.e42.one", principal, "2026-08-02T12:06:01Z"))

    def test_recovery_cannot_impersonate_holder_or_attach_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, claimed = _claimed(Path(directory))
            principal = _governed_recovery_principal("recovery.e43.one")
            grant = recovery_grant_from_claim("recovery.e43.two", claimed.record, "2026-08-02T12:05:00Z", "2026-08-02T12:10:00Z", "holder_timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e43", SyntheticFileCasGateway(Path(directory) / "recovery"))
            self.assertEqual(ledger.issue(grant).code, LedgerCode.ISSUED)
            authority.governed_recover_expired_claim(provenance, grant, ledger, "2026-08-02T12:06:00Z")
            result = authority.attach_invocation(provenance, "claim.e42.one", principal, "invocation.e43.recovery")
        self.assertEqual(result.code, DurableClaimResultCode.EFFECT_BLOCKED)

    def test_legacy_terminal_mutation_is_blocked_before_provenance_reporting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, _ = self._attached_claim(Path(directory))
            result = authority.finalize(provenance, "claim.e42.one", holder, DurableClaimState.SUCCEEDED, "observed_completed", "2026-08-02T12:05:00Z", invocation_id="invocation.e43.other")
        self.assertEqual(result.code, DurableClaimResultCode.EFFECT_BLOCKED)


def _e44_witness(challenge, *, status: CapabilityStatus = CapabilityStatus.SUPPORTED):
    raw = CapabilityWitness(
        challenge.challenge_id,
        challenge.target,
        challenge.holder,
        challenge.task_id,
        challenge.route_epoch,
        challenge.canary_id,
        challenge.nonce,
        "2026-08-02T12:05:00Z",
        status,
        HASH,
        "transport.e44",
    )
    return _synthetic_transport_witness_verifier("transport.e44", "attestor.e44").attest(raw, "2026-08-02T12:05:00Z")


def _manual_terminal_evidence(claim) -> ManualAppTerminalEvidence:
    return ManualAppTerminalEvidence(
        claim.claim_id,
        claim.invocation_id,
        claim.holder,
        CapabilityTarget.CODEX_APP,
        "completed",
        claim.terminal_at,
        "session.e44",
        HASH,
        HASH,
        HASH,
        claim.holder.owner_instance_id,
        claim.holder.claimant_correlation_id,
        "transport.e44",
    )


def _claim_bound_capability(ledger, challenge, claim):
    consumed = ledger.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:01Z")
    if consumed.code is not LedgerCode.CONSUMED or consumed.decision is None:
        raise AssertionError(f"test capability mint failed: {consumed.code}")
    return bind_challenge_decision(consumed.decision, claim, "2026-08-02T12:05:02Z")


def _consume_challenge_in_child(root: str, challenge, queue) -> None:
    ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(root)))
    queue.put(ledger.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:01Z").code.value)


def _consume_recovery_in_child(root: str, grant, claim, queue) -> None:
    ledger = RecoveryAuthorizationLedger("ledger.e44", SyntheticFileCasGateway(Path(root)))
    queue.put(ledger.consume(grant, claim, "2026-08-02T12:07:00Z").code.value)


class E44DurableChallengeTests(unittest.TestCase):
    def _challenge(self, holder: ClaimHolder, *, target: CapabilityTarget = CapabilityTarget.CODEX_APP):
        return _mint_challenge("challenge.e44.one", target, holder, TASK, 44, CANARY, NONCE, "2026-08-02T12:03:00Z", "2026-08-02T12:10:00Z", 60)

    def _finalized_claim(self, root: Path, holder: ClaimHolder | None = None, state: DurableClaimState = DurableClaimState.SUCCEEDED):
        holder = holder or _holder()
        authority, provenance, _, claimed = _claimed(root, holder=holder)
        terminal_at = "2026-08-02T12:05:00Z"
        return _seed_terminal_record(authority, claimed.record, state, "e44_terminal", terminal_at, invocation_id="invoke.e44.one")

    def test_durable_challenge_grants_only_fresh_supported_witness(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            challenge = self._challenge(_holder())
            ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory)))
            self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
            consumed = ledger.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:01Z")
        self.assertEqual(consumed.code, LedgerCode.CONSUMED)
        self.assertEqual(evaluate_challenge_capability(CapabilityTarget.CODEX_APP, consumed.decision).status, CapabilityStatus.BLOCKED)

    def test_legacy_capability_cannot_bypass_durable_gate(self) -> None:
        raw = RawCapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, OBSERVED, HASH, "probe.e44", "transport.e44")
        verified = _trusted_evidence_verifier("transport.e44").verify_capability(raw, NOW)
        self.assertEqual(evaluate_capability(CapabilityTarget.CODEX_APP, verified).status, CapabilityStatus.BLOCKED)
        self.assertEqual(evaluate_challenge_capability(CapabilityTarget.CODEX_APP, verified).status, CapabilityStatus.BLOCKED)

    def test_challenge_consumption_survives_new_ledger_instance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            challenge = self._challenge(_holder())
            first = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory)))
            self.assertEqual(first.issue(challenge).code, LedgerCode.ISSUED)
            self.assertEqual(first.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:01Z").code, LedgerCode.CONSUMED)
            restarted = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory)))
            replay = restarted.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:02Z")
        self.assertEqual(replay.code, LedgerCode.ALREADY_CONSUMED)

    def test_challenge_consumption_survives_process_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            challenge = self._challenge(_holder())
            ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory)))
            self.assertEqual(ledger.issue(challenge).code, LedgerCode.ISSUED)
            context = multiprocessing.get_context("spawn")
            queue = context.Queue()
            child = context.Process(target=_consume_challenge_in_child, args=(directory, challenge, queue))
            child.start()
            child.join(20)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(queue.get(timeout=2), LedgerCode.CONSUMED.value)
            replay = ledger.consume(challenge, _e44_witness(challenge), "2026-08-02T12:05:02Z")
        self.assertEqual(replay.code, LedgerCode.ALREADY_CONSUMED)

    def test_challenge_binding_and_freshness_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            challenge = self._challenge(_holder())
            ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory)))
            ledger.issue(challenge)
            wrong_raw = CapabilityWitness(challenge.challenge_id, challenge.target, challenge.holder, challenge.task_id, challenge.route_epoch, challenge.canary_id, "nonce.e44.other", "2026-08-02T12:05:00Z", CapabilityStatus.SUPPORTED, HASH, "transport.e44")
            wrong = _synthetic_transport_witness_verifier("transport.e44", "attestor.e44").attest(wrong_raw, "2026-08-02T12:05:00Z")
            stale_raw = CapabilityWitness(challenge.challenge_id, challenge.target, challenge.holder, challenge.task_id, challenge.route_epoch, challenge.canary_id, challenge.nonce, "2026-08-02T12:03:00Z", CapabilityStatus.SUPPORTED, HASH, "transport.e44")
            stale = _synthetic_transport_witness_verifier("transport.e44", "attestor.e44").attest(stale_raw, "2026-08-02T12:03:00Z")
            mismatch = ledger.consume(challenge, wrong, "2026-08-02T12:05:01Z")
            expired = ledger.consume(challenge, stale, "2026-08-02T12:05:01Z")
        self.assertEqual(mismatch.code, LedgerCode.BINDING_MISMATCH)
        self.assertEqual(expired.code, LedgerCode.STALE)

    def test_recovery_authorization_is_bound_and_globally_one_shot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = self._finalized_claim(Path(directory) / "claim")
            grant = recovery_grant_from_claim("recovery.e44.one", claim, "2026-08-02T12:06:00Z", "2026-08-02T12:10:00Z", "timeout")
            first = RecoveryAuthorizationLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "recovery"))
            self.assertEqual(first.issue(grant).code, LedgerCode.ISSUED)
            self.assertEqual(first.consume(grant, claim, "2026-08-02T12:07:00Z").code, LedgerCode.CONSUMED)
            restarted = RecoveryAuthorizationLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "recovery"))
            replay = restarted.consume(grant, claim, "2026-08-02T12:07:01Z")
        self.assertEqual(replay.code, LedgerCode.ALREADY_CONSUMED)

    def test_recovery_authorization_rejects_other_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first_claim = self._finalized_claim(Path(directory) / "one")
            second_claim = self._finalized_claim(Path(directory) / "two", holder=_holder(instance="owner.e44.other", correlation="corr.e44.other"))
            grant = recovery_grant_from_claim("recovery.e44.one", first_claim, "2026-08-02T12:06:00Z", "2026-08-02T12:10:00Z", "timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "recovery"))
            ledger.issue(grant)
            result = ledger.consume(grant, second_claim, "2026-08-02T12:07:00Z")
        self.assertEqual(result.code, LedgerCode.BINDING_MISMATCH)

    def test_recovery_authorization_consumption_survives_process_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = self._finalized_claim(Path(directory) / "claim")
            grant = recovery_grant_from_claim("recovery.e44.process", claim, "2026-08-02T12:06:00Z", "2026-08-02T12:10:00Z", "timeout")
            ledger = RecoveryAuthorizationLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "recovery"))
            self.assertEqual(ledger.issue(grant).code, LedgerCode.ISSUED)
            context = multiprocessing.get_context("spawn")
            queue = context.Queue()
            child = context.Process(target=_consume_recovery_in_child, args=(str(Path(directory) / "recovery"), grant, claim, queue))
            child.start()
            child.join(20)
            self.assertEqual(child.exitcode, 0)
            self.assertEqual(queue.get(timeout=2), LedgerCode.CONSUMED.value)
            replay = ledger.consume(grant, claim, "2026-08-02T12:07:01Z")
        self.assertEqual(replay.code, LedgerCode.ALREADY_CONSUMED)

    def test_legacy_manual_owner_terminal_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            claim = self._finalized_claim(Path(directory))
            challenge = self._challenge(claim.holder)
            ledger = DurableChallengeLedger("ledger.e44", SyntheticFileCasGateway(Path(directory) / "challenge"))
            ledger.issue(challenge)
            capability = _claim_bound_capability(ledger, challenge, claim)
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, capability, _manual_terminal_evidence(claim))
            wrong = ManualAppTerminalEvidence(**{**_manual_terminal_evidence(claim).__dict__, "target": CapabilityTarget.CODEX_CLI})
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(claim, capability, wrong)

    def test_automation_and_cli_schemas_are_owner_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            automation_holder = _holder(owner_type=OwnerType.APP_AUTOMATION_NEW_RUN, instance="owner.e44.automation", correlation="corr.e44.automation")
            auto_claim = self._finalized_claim(Path(directory) / "auto", automation_holder)
            auto_challenge = self._challenge(automation_holder)
            auto_ledger = DurableChallengeLedger("ledger.e44.auto", SyntheticFileCasGateway(Path(directory) / "auto.challenge"))
            auto_ledger.issue(auto_challenge)
            auto_capability = _claim_bound_capability(auto_ledger, auto_challenge, auto_claim)
            auto = AutomationTerminalEvidence(auto_claim.claim_id, auto_claim.invocation_id, automation_holder, CapabilityTarget.CODEX_APP, "completed", auto_claim.terminal_at, "dispatch.e44", "run.e44", "callback.e44", "callback.identity.e44", HASH, HASH, HASH, automation_holder.owner_instance_id, automation_holder.claimant_correlation_id, "transport.e44")
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(auto_claim, auto_capability, auto)
            cli_holder = _holder(owner_type=OwnerType.CODEX_CLI_PROCESS, instance="owner.e44.cli", correlation="corr.e44.cli")
            cli_claim = self._finalized_claim(Path(directory) / "cli", cli_holder)
            cli_challenge = self._challenge(cli_holder, target=CapabilityTarget.CODEX_CLI)
            cli_ledger = DurableChallengeLedger("ledger.e44.cli", SyntheticFileCasGateway(Path(directory) / "cli.challenge"))
            cli_ledger.issue(cli_challenge)
            cli_capability = _claim_bound_capability(cli_ledger, cli_challenge, cli_claim)
            bad_cli = CliTerminalEvidence(cli_claim.claim_id, cli_claim.invocation_id, cli_holder, CapabilityTarget.CODEX_CLI, "completed", cli_claim.terminal_at, "launcher.e44", 42, HASH, 1, "CLEAN", HASH, HASH, cli_holder.owner_instance_id, cli_holder.claimant_correlation_id, "transport.e44")
            with self.assertRaises(ValidationError):
                validate_owner_terminal_evidence(cli_claim, cli_capability, bad_cli)

    def test_e44_terminal_decision_is_required_for_reconciliation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority, provenance, holder, claimed = _claimed(Path(directory))
            attached = _seed_invocation_record(authority, claimed.record, "invocation.e44.one")
            challenge = _one_shot_challenge("challenge.e44.raw", CapabilityTarget.CODEX_APP, holder, TASK, 44, CANARY, NONCE, "2026-08-02T12:03:00Z", "2026-08-02T12:10:00Z", 60)
            started = TerminalExecutionReconciler.begin(attached, challenge, "invocation.e44.one", "2026-08-02T12:04:00Z")
            raw = RawInvocationTransportObservation("challenge.e44.raw", CapabilityTarget.CODEX_APP, claimed.record.claim_id, "invocation.e44.one", holder, ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION, TASK, 44, CANARY, NONCE, "2026-08-02T12:04:00Z", "2026-08-02T12:05:00Z", "completed", 0, HASH, "transport.e44")
            observed = TerminalExecutionReconciler.observe_terminal(started, _bounded_transport_attestor("transport.e44").attest(challenge, raw, "2026-08-02T12:05:01Z"))
            final = _seed_terminal_record(authority, attached, DurableClaimState.SUCCEEDED, "done", "2026-08-02T12:05:00Z")
            with self.assertRaises(AttestationError):
                TerminalExecutionReconciler.reconcile(observed, final, "2026-08-02T12:05:02Z")


if __name__ == "__main__":
    unittest.main()
