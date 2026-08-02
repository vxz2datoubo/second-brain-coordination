"""E41 synthetic, fail-closed tests.  They never invoke an App, CLI, or API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import multiprocessing
from pathlib import Path
import sys
import tempfile
import unittest


PROGRAM_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROGRAM_ROOT / "src"))

from brainops_control_plane.durable_authority import (  # noqa: E402
    CasWriteResult,
    DurableClaimAuthority,
    DurableClaimKey,
    DurableClaimResultCode,
    DurableClaimState,
    FixedRepositoryGitHubCasGateway,
    RevisionedObject,
    SyntheticFileCasGateway,
)
from brainops_control_plane.execution_evidence import (  # noqa: E402
    CapabilityObservation,
    CapabilityTarget,
    ExecutionEvidenceType,
    InvocationReceipt,
    classify_execution,
    evaluate_capability,
)
from brainops_control_plane.models import CapabilityStatus, RouteState, ValidationError  # noqa: E402
from brainops_control_plane.route_terminalization import (  # noqa: E402
    CanonicalRouteTerminalization,
    CanonicalTerminalState,
    RouteExecutionDisposition,
    evaluate_route_terminalization,
)


_REPOSITORY = "vxz2datoubo/second-brain-coordination"
_NOW = "2026-08-02T12:00:00Z"
_HASH = "a" * 64


def _key(nonce: str = "nonce.e41.test") -> DurableClaimKey:
    return DurableClaimKey(
        repository=_REPOSITORY,
        route_id="route.e41",
        route_epoch=43,
        task_id="task.e41",
        canary_id="canary.e41",
        nonce=nonce,
    )


def _authority(root: Path) -> DurableClaimAuthority:
    return DurableClaimAuthority(_REPOSITORY, "e41.claim", SyntheticFileCasGateway(root))


def _claim(authority: DurableClaimAuthority, key: DurableClaimKey, claim_id: str = "claim.e41.one"):
    return authority.claim(key, claim_id, "CODEX_APP", "corr.e41.one", _NOW)


def _race_worker(root: str, start, result_queue, sequence: int) -> None:
    """Spawn-safe worker used for the cross-process claim race."""

    start.wait(10)
    authority = _authority(Path(root))
    outcome = authority.claim(
        _key("nonce.e41.race"),
        f"claim.e41.race.{sequence}",
        "CODEX_APP",
        "corr.e41.race",
        _NOW,
    )
    result_queue.put(outcome.code.value)


class _UnavailableGateway:
    def read(self, object_id: str) -> RevisionedObject:
        raise OSError("offline")

    def compare_and_set(self, object_id: str, expected_revision: str | None, payload: bytes) -> CasWriteResult:
        raise OSError("offline")


class _RecordingGitHubClient:
    def __init__(self) -> None:
        self.read_calls: list[tuple[str, str, str]] = []
        self.cas_calls: list[tuple[str, str, str, str | None, bytes]] = []
        self.object = RevisionedObject(None, None)

    def read_content(self, repository: str, ref: str, path: str) -> RevisionedObject:
        self.read_calls.append((repository, ref, path))
        return self.object

    def compare_and_set_content(
        self,
        repository: str,
        ref: str,
        path: str,
        expected_revision: str | None,
        payload: bytes,
    ) -> CasWriteResult:
        self.cas_calls.append((repository, ref, path, expected_revision, payload))
        if self.object.revision != expected_revision:
            return CasWriteResult(False, self.object.revision)
        self.object = RevisionedObject("b" * 40, payload)
        return CasWriteResult(True, self.object.revision)


class DurableAuthorityTests(unittest.TestCase):
    def test_claim_creates_durable_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _claim(_authority(Path(directory)), _key())
        self.assertEqual(result.code, DurableClaimResultCode.CLAIMED)
        self.assertEqual(result.record.state, DurableClaimState.CLAIMED)

    def test_same_key_is_claimed_once(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            duplicate = _claim(authority, _key(), "claim.e41.two")
        self.assertEqual(duplicate.code, DurableClaimResultCode.ALREADY_CLAIMED)

    def test_restart_reads_existing_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _claim(_authority(root), _key())
            restarted = _claim(_authority(root), _key(), "claim.e41.restart")
        self.assertEqual(restarted.code, DurableClaimResultCode.ALREADY_CLAIMED)

    def test_fresh_authority_has_no_local_state_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _claim(_authority(root), _key())
            observed = _authority(root).read(_key())
        self.assertIsNotNone(observed)
        self.assertEqual(observed.claim_id, "claim.e41.one")

    def test_four_process_race_has_one_winner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = multiprocessing.get_context("spawn")
            start = context.Event()
            queue = context.Queue()
            processes = [
                context.Process(target=_race_worker, args=(directory, start, queue, index))
                for index in range(4)
            ]
            for process in processes:
                process.start()
            start.set()
            for process in processes:
                process.join(15)
                self.assertEqual(process.exitcode, 0)
            results = [queue.get(timeout=3) for _ in processes]
        self.assertEqual(results.count(DurableClaimResultCode.CLAIMED.value), 1)
        self.assertEqual(results.count(DurableClaimResultCode.ALREADY_CLAIMED.value), 3)

    def test_finalize_persists_terminal_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            final = authority.finalize(
                _key(), "claim.e41.one", DurableClaimState.SUCCEEDED, "completed", "2026-08-02T12:01:00Z"
            )
        self.assertEqual(final.code, DurableClaimResultCode.FINALIZED)
        self.assertEqual(final.record.state, DurableClaimState.SUCCEEDED)

    def test_terminal_claim_cannot_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            authority.finalize(_key(), "claim.e41.one", DurableClaimState.FAILED, "failed", "2026-08-02T12:01:00Z")
            replay = _claim(authority, _key(), "claim.e41.replay")
        self.assertEqual(replay.code, DurableClaimResultCode.TERMINAL_EXISTS)

    def test_old_nonce_replay_is_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key("nonce.e41.old"))
            replay = _claim(authority, _key("nonce.e41.old"), "claim.e41.replay")
        self.assertEqual(replay.code, DurableClaimResultCode.ALREADY_CLAIMED)

    def test_different_nonce_is_a_distinct_future_authority(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key("nonce.e41.old"))
            fresh = _claim(authority, _key("nonce.e41.new"), "claim.e41.new")
        self.assertEqual(fresh.code, DurableClaimResultCode.CLAIMED)

    def test_wrong_owner_cannot_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            result = authority.finalize(
                _key(), "claim.e41.other", DurableClaimState.FAILED, "failed", "2026-08-02T12:01:00Z"
            )
        self.assertEqual(result.code, DurableClaimResultCode.CLAIM_OWNER_MISMATCH)

    def test_crash_after_claim_enters_recovery_required(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            recovered = authority.recover_expired_claim(_key(), "2026-08-02T12:02:00Z", 30)
        self.assertEqual(recovered.code, DurableClaimResultCode.FINALIZED)
        self.assertEqual(recovered.record.state, DurableClaimState.RECOVERY_REQUIRED)

    def test_nonexpired_claim_is_not_recovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            result = authority.recover_expired_claim(_key(), "2026-08-02T12:00:10Z", 30)
        self.assertEqual(result.code, DurableClaimResultCode.ALREADY_CLAIMED)

    def test_missing_claim_cannot_finalize(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = _authority(Path(directory)).finalize(
                _key(), "claim.e41.one", DurableClaimState.FAILED, "failed", "2026-08-02T12:01:00Z"
            )
        self.assertEqual(result.code, DurableClaimResultCode.CLAIM_NOT_FOUND)

    def test_authority_outage_fails_closed(self) -> None:
        authority = DurableClaimAuthority(_REPOSITORY, "e41.claim", _UnavailableGateway())
        result = _claim(authority, _key())
        self.assertEqual(result.code, DurableClaimResultCode.AUTHORITY_UNAVAILABLE)

    def test_repository_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            other = DurableClaimKey("example/other", "route.e41", 43, "task.e41", "canary.e41", "nonce.e41.test")
            with self.assertRaises(ValidationError):
                _claim(_authority(Path(directory)), other)

    def test_fixed_github_gateway_binds_repository_ref_and_prefix(self) -> None:
        client = _RecordingGitHubClient()
        gateway = FixedRepositoryGitHubCasGateway(_REPOSITORY, "refs/heads/main", "coordination/e41/claims", client)
        result = _claim(DurableClaimAuthority(_REPOSITORY, "e41.claim", gateway), _key())
        self.assertEqual(result.code, DurableClaimResultCode.CLAIMED)
        self.assertEqual(client.cas_calls[0][0:2], (_REPOSITORY, "refs/heads/main"))
        self.assertTrue(client.cas_calls[0][2].startswith("coordination/e41/claims/e41.claim."))

    def test_github_revision_can_be_a_git_blob_sha(self) -> None:
        object_with_sha1 = RevisionedObject("c" * 40, b"payload")
        self.assertEqual(object_with_sha1.payload_sha256, __import__("hashlib").sha256(b"payload").hexdigest())

    def test_revision_payload_digest_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RevisionedObject("d" * 40, b"payload", "e" * 64)


class RouteTerminalizationTests(unittest.TestCase):
    def _terminal(self, state: DurableClaimState):
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            return authority.finalize(_key(), "claim.e41.one", state, "finished", "2026-08-02T12:01:00Z").record

    def test_claimed_authority_blocks_ready_route(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            decision = evaluate_route_terminalization(RouteState.READY, authority.read(_key()))
        self.assertEqual(decision.disposition, RouteExecutionDisposition.BLOCKED_BY_DURABLE_CLAIM)
        self.assertFalse(decision.execution_permitted)

    def test_terminal_authority_blocks_stale_ready_route(self) -> None:
        decision = evaluate_route_terminalization(RouteState.READY, self._terminal(DurableClaimState.SUCCEEDED))
        self.assertEqual(decision.disposition, RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL)
        self.assertFalse(decision.execution_permitted)

    def test_terminal_authority_with_blocked_route_is_verified_terminal(self) -> None:
        record = self._terminal(DurableClaimState.FAILED)
        canonical = CanonicalRouteTerminalization(
            RouteState.BLOCKED, record.claim_id, CanonicalTerminalState.FAILED, "2026-08-02T12:01:00Z"
        )
        decision = evaluate_route_terminalization(RouteState.BLOCKED, record, canonical)
        self.assertEqual(decision.disposition, RouteExecutionDisposition.ROUTE_TERMINALIZED)
        self.assertTrue(decision.canonical_terminalization_verified)

    def test_blocked_route_without_exact_terminal_binding_is_not_verified(self) -> None:
        decision = evaluate_route_terminalization(RouteState.BLOCKED, self._terminal(DurableClaimState.SUCCEEDED))
        self.assertEqual(decision.disposition, RouteExecutionDisposition.BLOCKED_BY_DURABLE_TERMINAL)
        self.assertFalse(decision.canonical_terminalization_verified)

    def test_wrong_terminal_state_is_not_verified(self) -> None:
        record = self._terminal(DurableClaimState.SUCCEEDED)
        canonical = CanonicalRouteTerminalization(
            RouteState.BLOCKED, record.claim_id, CanonicalTerminalState.FAILED, "2026-08-02T12:01:00Z"
        )
        decision = evaluate_route_terminalization(RouteState.BLOCKED, record, canonical)
        self.assertFalse(decision.canonical_terminalization_verified)

    def test_paused_route_without_authority_is_blocked(self) -> None:
        decision = evaluate_route_terminalization(RouteState.PAUSED, None)
        self.assertEqual(decision.disposition, RouteExecutionDisposition.ROUTE_STATE_BLOCKED)
        self.assertFalse(decision.execution_permitted)

    def test_ready_route_without_authority_is_not_terminalized(self) -> None:
        decision = evaluate_route_terminalization(RouteState.READY, None)
        self.assertEqual(decision.disposition, RouteExecutionDisposition.READY_REQUIRES_DURABLE_CLAIM)
        self.assertFalse(decision.execution_permitted)
        self.assertFalse(decision.canonical_terminalization_verified)


class ExecutionEvidenceTests(unittest.TestCase):
    def _claim_record(self):
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            return authority.attach_invocation(_key(), "claim.e41.one", "invoke.e41.one").record

    def _receipt(self, evidence_type: ExecutionEvidenceType, **overrides) -> InvocationReceipt:
        values = {
            "invocation_id": "invoke.e41.one",
            "parent_correlation_id": "corr.e41.one",
            "evidence_type": evidence_type,
            "owner_type": "CODEX_APP",
            "started_at": _NOW,
            "ended_at": "2026-08-02T12:01:00Z",
            "terminal_status": "completed",
            "log_hash": _HASH,
            "non_attempted_owner": "CODEX_CLI",
            "cleanup_proof_hash": _HASH,
        }
        values.update(overrides)
        return InvocationReceipt(**values)

    def test_missing_capability_observation_is_unknown(self) -> None:
        decision = evaluate_capability(CapabilityTarget.CODEX_APP, None)
        self.assertEqual(decision.status, CapabilityStatus.UNKNOWN)

    def test_capability_target_mismatch_is_blocked(self) -> None:
        observation = CapabilityObservation(CapabilityTarget.CODEX_CLI, CapabilityStatus.SUPPORTED, _NOW, _HASH, "probe.e41")
        decision = evaluate_capability(CapabilityTarget.CODEX_APP, observation)
        self.assertEqual(decision.status, CapabilityStatus.BLOCKED)

    def test_observed_capability_is_preserved(self) -> None:
        observation = CapabilityObservation(CapabilityTarget.CODEX_APP, CapabilityStatus.SUPPORTED, _NOW, _HASH, "probe.e41")
        decision = evaluate_capability(CapabilityTarget.CODEX_APP, observation)
        self.assertEqual(decision.status, CapabilityStatus.SUPPORTED)

    def test_claim_only_cannot_be_called_execution(self) -> None:
        assessment = classify_execution(self._claim_record(), None)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CONTROL_PLANE_CLAIM_ONLY)

    def test_manual_session_receipt_stays_manual(self) -> None:
        assessment = classify_execution(
            self._claim_record(), self._receipt(ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION)
        )
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION)

    def test_app_automation_requires_callback_proof(self) -> None:
        with self.assertRaises(ValidationError):
            self._receipt(ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN)

    def test_app_automation_receipt_is_distinct(self) -> None:
        receipt = self._receipt(ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN, callback_proof_hash="b" * 64)
        assessment = classify_execution(self._claim_record(), receipt)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.APP_AUTOMATION_DISPATCHED_NEW_RUN)

    def test_cli_receipt_requires_exit_code(self) -> None:
        with self.assertRaises(ValidationError):
            self._receipt(ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED)

    def test_cli_receipt_is_distinct(self) -> None:
        receipt = self._receipt(ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED, exit_code=0)
        assessment = classify_execution(self._claim_record(), receipt)
        self.assertEqual(assessment.evidence_type, ExecutionEvidenceType.CODEX_CLI_PROCESS_INVOKED)

    def test_receipt_parent_mismatch_is_rejected(self) -> None:
        receipt = self._receipt(ExecutionEvidenceType.CURRENT_CODEX_APP_SESSION_MANUAL_EXECUTION, parent_correlation_id="corr.e41.other")
        with self.assertRaises(ValidationError):
            classify_execution(self._claim_record(), receipt)

    def test_duplicate_callback_is_durably_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            authority.attach_invocation(_key(), "claim.e41.one", "invoke.e41.one")
            duplicate = authority.attach_invocation(_key(), "claim.e41.one", "invoke.e41.one")
        self.assertEqual(duplicate.code, DurableClaimResultCode.DUPLICATE_INVOCATION)

    def test_second_owner_callback_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            authority = _authority(Path(directory))
            _claim(authority, _key())
            authority.attach_invocation(_key(), "claim.e41.one", "invoke.e41.one")
            competing = authority.attach_invocation(_key(), "claim.e41.one", "invoke.e41.two")
        self.assertEqual(competing.code, DurableClaimResultCode.INVOCATION_MISMATCH)


if __name__ == "__main__":
    unittest.main()
