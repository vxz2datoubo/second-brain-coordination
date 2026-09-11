from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import tempfile
import threading
import unittest

from tools.host_execution_broker import (
    AuthorityState,
    DecisionOutcome,
    ExecutionRequest,
    FencingError,
    HostExecutionBroker,
    ProcessOwnershipError,
    ProgressObservation,
    ProgressState,
    ResourceClaim,
    ResourceMode,
    ResourceType,
    TransportState,
    WorkerIdentity,
)

MAIN = "2b69f096f1ad4c3d2ceeb2176d8e20aea3ee6c73"
AUTH = "sha256:" + "a" * 64


def request(
    *,
    task_id: str,
    branch: str | None = None,
    worktree: str | None = None,
    collision_domain: str | None = None,
    repo_write: bool = True,
    authority_state: AuthorityState = AuthorityState.CURRENT,
    claims: tuple[ResourceClaim, ...] = (),
    write_surfaces: tuple[str, ...] = (),
    attempt: int = 1,
    episode_id: str | None = None,
) -> ExecutionRequest:
    return ExecutionRequest(
        project_id="SECOND_BRAIN",
        task_id=task_id,
        route_epoch=310,
        mission_id=f"mission-{task_id}",
        milestone_id="m1",
        episode_id=episode_id or f"episode-{task_id}",
        attempt=attempt,
        role="AUTHOR",
        branch=branch or f"gpt/{task_id}",
        worktree=worktree or f"F:/worktrees/{task_id}",
        collision_domain=collision_domain or f"cd:{task_id}",
        carrier="WORKBUDDY_CLI_HEADLESS",
        model="glm-5.3",
        canonical_main_sha=MAIN,
        authority_receipt_digest=AUTH,
        authority_state=authority_state,
        resource_claims=claims,
        write_surfaces=write_surfaces,
        repo_write=repo_write,
    )


def lease_for(decision, resource_type: ResourceType, resource_id: str):
    return next(
        item
        for item in decision.leases
        if item.resource_type == resource_type and item.resource_id == resource_id
    )


class Clock:
    def __init__(self, value: float = 1000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def advance_ms(self, value: int) -> None:
        self.value += value / 1000.0


class HostExecutionBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def db(self, name: str = "broker.db") -> Path:
        return self.tmp / name

    def test_same_worktree_concurrent_writers_exactly_one_admit(self):
        left = HostExecutionBroker(self.db())
        right = HostExecutionBroker(self.db())
        barrier = threading.Barrier(2)
        r1 = request(task_id="wt-a", worktree="F:/shared/wt")
        r2 = request(task_id="wt-b", worktree="F:/shared/wt")

        def run(broker, req):
            barrier.wait()
            return broker.admit(req).outcome

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda pair: run(*pair), ((left, r1), (right, r2))))
        self.assertEqual(outcomes.count(DecisionOutcome.ADMIT), 1)
        self.assertEqual(outcomes.count(DecisionOutcome.BLOCK_CONFLICT), 1)

    def test_same_branch_writers_conflict(self):
        broker = HostExecutionBroker(self.db())
        self.assertEqual(broker.admit(request(task_id="b1", branch="gpt/shared")).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(request(task_id="b2", branch="gpt/shared")).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_disjoint_worktrees_and_collision_domains_parallelize(self):
        broker = HostExecutionBroker(self.db())
        self.assertEqual(broker.admit(request(task_id="a")).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(request(task_id="b")).outcome, DecisionOutcome.ADMIT)

    def test_read_read_same_branch_worktree_collision_domain_parallelizes(self):
        broker = HostExecutionBroker(self.db())
        common = dict(branch="gpt/shared", worktree="F:/shared", collision_domain="cd:shared", repo_write=False)
        self.assertEqual(broker.admit(request(task_id="r1", **common)).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(request(task_id="r2", **common)).outcome, DecisionOutcome.ADMIT)

    def test_read_vs_destructive_service_restart_conflicts(self):
        broker = HostExecutionBroker(self.db())
        reader = request(task_id="svc-read", repo_write=False, claims=(ResourceClaim(ResourceType.WORKBUDDY_DAEMON, "daemon", ResourceMode.READ),))
        restart = request(task_id="svc-restart", repo_write=False, claims=(ResourceClaim(ResourceType.WORKBUDDY_DAEMON, "daemon", ResourceMode.WRITE),))
        self.assertEqual(broker.admit(reader).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(restart).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_idempotent_duplicate_dispatch_never_creates_second_writer(self):
        broker = HostExecutionBroker(self.db())
        req = request(task_id="idem")
        first = broker.admit(req)
        second = broker.admit(req)
        self.assertEqual(first.outcome, DecisionOutcome.ADMIT)
        self.assertEqual(second.outcome, DecisionOutcome.JOIN_EXISTING)
        self.assertEqual(second.execution_id, first.execution_id)

    def test_broker_short_identity_uses_hashed_execution_material(self):
        left = request(task_id="hs-canary-a")
        right = request(task_id="hs-canary-b")
        self.assertTrue(left.broker_key.startswith("HX"))
        self.assertTrue(right.broker_key.startswith("HX"))
        self.assertNotEqual(left.broker_key, right.broker_key)
        self.assertEqual(len(left.broker_key), 18)

    def test_stale_lease_generation_is_fenced_and_successor_can_admit(self):
        clock = Clock()
        broker = HostExecutionBroker(self.db(), lease_ttl_ms=1000, clock=clock)
        first = broker.admit(request(task_id="old", worktree="F:/shared/wt"))
        old = lease_for(first, ResourceType.WORKTREE, "F:/shared/wt")
        clock.advance_ms(1100)
        second = broker.admit(request(task_id="new", worktree="F:/shared/wt"))
        new = lease_for(second, ResourceType.WORKTREE, "F:/shared/wt")
        self.assertEqual(second.outcome, DecisionOutcome.ADMIT)
        self.assertEqual(new.generation, old.generation + 1)
        with self.assertRaises(FencingError):
            broker.assert_effect_authorized(old)

    def test_fencing_token_mismatch_denies_effect(self):
        broker = HostExecutionBroker(self.db())
        decision = broker.admit(request(task_id="fence"))
        with self.assertRaises(FencingError):
            broker.assert_effect_authorized(replace(decision.leases[0], fencing_token="F-invalid"))

    def test_rdc_timeout_is_outcome_unknown_and_does_not_duplicate_writer(self):
        broker = HostExecutionBroker(self.db())
        req = request(task_id="timeout")
        first = broker.admit(req)
        self.assertEqual(broker.transport_state(transport_timed_out=True, worker_alive=None), TransportState.OUTCOME_UNKNOWN)
        second = broker.admit(req)
        self.assertEqual(second.outcome, DecisionOutcome.JOIN_EXISTING)
        self.assertEqual(first.execution_id, second.execution_id)

    def test_authorized_not_started_and_starting_are_distinct(self):
        not_started = ProgressObservation(now_ms=1000, process_alive=False, process_started=False)
        starting = ProgressObservation(now_ms=1500, process_alive=True, process_started=True, process_started_at_ms=1000, heartbeat_at_ms=1499)
        self.assertEqual(not_started.classify(stall_after_ms=1000), ProgressState.AUTHORIZED_NOT_STARTED)
        self.assertEqual(starting.classify(stall_after_ms=1000), ProgressState.STARTING)

    def test_process_start_receipt_binds_exact_identity_and_rejects_pid_reuse(self):
        broker = HostExecutionBroker(self.db())
        decision = broker.admit(request(task_id="process"))
        binding = decision.leases[0]
        worker = WorkerIdentity(
            pid=1234,
            process_creation_identity="2026-09-11T04:00:00Z#1234",
            session_id="h310-proc-1",
            executor_id="wb-executor-1",
            task_id="process",
            route_epoch=310,
            execution_lease_id=binding.lease_id,
            generation=binding.generation,
            fencing_token=binding.fencing_token,
            cli_path=r"C:\tools\codebuddy.exe",
            cli_version="2.148.0",
            endpoint="http://127.0.0.1:12001",
        )
        receipt = broker.bind_process_start(decision.execution_id, worker)
        self.assertEqual(receipt.worker, worker)
        self.assertEqual(receipt.branch, "gpt/process")
        self.assertEqual(receipt.canonical_main_sha, MAIN)
        reused_pid = replace(worker, process_creation_identity="later-process#1234")
        self.assertFalse(broker.process_identity_matches(reused_pid, worker))
        with self.assertRaises(ProcessOwnershipError):
            broker.bind_process_start(decision.execution_id, reused_pid)

    def test_heartbeat_without_meaningful_progress_eventually_stalls(self):
        obs = ProgressObservation(now_ms=10_000, process_alive=True, process_started_at_ms=1000, heartbeat_at_ms=9_999, model_response_at_ms=9_998, meaningful_progress_at_ms=None)
        self.assertEqual(obs.classify(stall_after_ms=2000), ProgressState.STALLED)

    def test_meaningful_progress_keeps_worker_running(self):
        obs = ProgressObservation(now_ms=10_000, process_alive=True, process_started_at_ms=1000, heartbeat_at_ms=9_999, meaningful_progress_at_ms=9_500)
        self.assertEqual(obs.classify(stall_after_ms=2000), ProgressState.RUNNING)

    def test_max_turn_episode_rolls_to_checkpoint_not_mission_failure(self):
        broker = HostExecutionBroker(self.db())
        result = broker.episode_budget(turns_used=20, max_turns=20, mission_complete=False, checkpoint_ref="checkpoint://episode-1")
        self.assertEqual(result.outcome.value, "CHECKPOINT_AND_SUCCESSOR")
        self.assertTrue(result.checkpoint_required)
        self.assertTrue(result.successor_episode_required)

    def test_terminal_release_frees_resources_but_retains_receipts(self):
        broker = HostExecutionBroker(self.db())
        first = broker.admit(request(task_id="release", worktree="F:/shared/wt"))
        broker.release(first.execution_id)
        history = broker.history(first.execution_id)
        self.assertEqual(history["execution"]["status"], "TERMINAL")
        self.assertEqual(history["execution"]["terminal_state"], "COMPLETE")
        self.assertTrue(all(item["status"] == "RELEASED" for item in history["leases"]))
        second = broker.admit(request(task_id="successor", worktree="F:/shared/wt"))
        self.assertEqual(second.outcome, DecisionOutcome.ADMIT)

    def test_same_one_time_runner_is_exclusive_and_reroutes(self):
        broker = HostExecutionBroker(self.db())
        claim = (ResourceClaim(ResourceType.WORKBUDDY_ONE_TIME_RUNNER, "runner-1"),)
        self.assertEqual(broker.admit(request(task_id="one-a", repo_write=False, claims=claim)).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(request(task_id="one-b", repo_write=False, claims=claim)).outcome, DecisionOutcome.REROUTE)

    def test_multiple_independent_cli_sessions_are_legal_when_disjoint(self):
        broker = HostExecutionBroker(self.db())
        a = request(task_id="cli-a", claims=(ResourceClaim(ResourceType.WORKBUDDY_AGENT_SESSION, "session-a"),))
        b = request(task_id="cli-b", claims=(ResourceClaim(ResourceType.WORKBUDDY_AGENT_SESSION, "session-b"),))
        self.assertEqual(broker.admit(a).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(b).outcome, DecisionOutcome.ADMIT)

    def test_unknown_or_stale_authority_fails_closed(self):
        broker = HostExecutionBroker(self.db())
        self.assertEqual(broker.admit(request(task_id="unknown", authority_state=AuthorityState.UNKNOWN)).outcome, DecisionOutcome.BLOCK_CONFLICT)
        self.assertEqual(broker.admit(request(task_id="stale", authority_state=AuthorityState.STALE)).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_overlapping_write_surface_blocks_even_with_disjoint_git_resources(self):
        broker = HostExecutionBroker(self.db())
        self.assertEqual(broker.admit(request(task_id="surface-a", write_surfaces=("tools/x/**",))).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(request(task_id="surface-b", write_surfaces=("tools/x/**",))).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_explicit_read_claim_cannot_downgrade_implicit_branch_write(self):
        req = request(task_id="strongest", branch="gpt/shared", claims=(ResourceClaim(ResourceType.BRANCH, "gpt/shared", ResourceMode.READ),))
        branch = next(item for item in req.all_claims() if item.resource_type == ResourceType.BRANCH)
        self.assertEqual(branch.mode, ResourceMode.WRITE)

    def test_lease_binding_contains_durable_expiry_and_holder(self):
        broker = HostExecutionBroker(self.db(), lease_ttl_ms=5000)
        decision = broker.admit(request(task_id="lease-fields"))
        binding = decision.leases[0]
        self.assertEqual(binding.execution_id, decision.execution_id)
        self.assertEqual(binding.holder, decision.execution_id)
        self.assertGreater(binding.expires_at_ms, binding.issued_at_ms)
        self.assertEqual(binding.state, "ACTIVE")


    def test_recursive_write_surface_conflicts_with_child_path(self):
        broker = HostExecutionBroker(self.db())
        first = request(task_id="tree", write_surfaces=("tools/x/**",))
        second = request(task_id="child", write_surfaces=("tools/x/a.py",))
        self.assertEqual(broker.admit(first).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(second).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_windows_case_equivalent_write_surfaces_conflict(self):
        broker = HostExecutionBroker(self.db())
        first = request(task_id="case-a", write_surfaces=("Tools/X.py",))
        second = request(task_id="case-b", write_surfaces=("tools/x.py",))
        self.assertEqual(broker.admit(first).outcome, DecisionOutcome.ADMIT)
        self.assertEqual(broker.admit(second).outcome, DecisionOutcome.BLOCK_CONFLICT)

    def test_noncanonical_write_surface_fails_before_admission(self):
        with self.assertRaises(ValueError):
            request(task_id="bad-surface", write_surfaces=("tools/../secret.py",))

    def test_durable_broker_rejects_process_local_memory_database(self):
        with self.assertRaises(ValueError):
            HostExecutionBroker(":memory:")


if __name__ == "__main__":
    unittest.main()
