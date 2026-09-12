"""R184 adversarial tests for the local WorkBuddy/CodeBuddy bridge (Phase 2B).

These tests exist to PROVE the bridge fails closed. Each test corresponds to one
line in the TASK-BRIEF adversarial matrix:

  1.  stale canonical main                      -> REFUSED_STALE_MAIN
  2.  task not in registered index              -> REFUSED_UNREGISTERED_TASK
  3.  wrong/expired lease or reservation        -> REFUSED_AUTHORITY_MISMATCH
  4.  duplicate launch, same immutable identity -> REFUSED_DUPLICATE
  5.  branch mismatch                           -> REFUSED_BASE_MISMATCH
  6.  collision conflict                        -> REFUSED_COLLISION_CONFLICT
  7.  candidate-only task                       -> REFUSED_CANDIDATE_ONLY
  8.  required model mismatch/unavailable       -> REFUSED_MODEL_UNAVAILABLE
  9.  hidden shell cannot execute               -> no argv execution path
  10. credentials are redacted                  -> redaction boundary
  11. model mismatch rejects                    -> (see 8, explicit)
  12. no real child process in CI/tests         -> adapter must be fake
  13. Windows case/Unicode path equivalence     -> collision identity is normalized
  +   fencing-token falsification               -> stale fencing token rejected

Hard boundary: NO test in this file may spawn a real process. The only adapter
used is FakeProcessAdapter.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from tools.local_workbuddy_bridge import (
    BridgeBoundaryError,
    BridgeDecision,
    FakeProcessAdapter,
    LaunchPlan,
    LaunchReceiptStore,
    LocalWorkBuddyBridge,
    build_return_package,
    plan_launch,
    preflight_model,
    redact,
)
from tools.local_workbuddy_bridge.launch_plan import AuthorityView
from tools.local_workbuddy_bridge.redaction import contains_secret


def _valid_view(**overrides) -> AuthorityView:
    """A fully-authorized snapshot. Tests remove exactly one thing at a time."""
    base = dict(
        task_id="R184-LOCAL-BRIDGE",
        route_epoch=41,
        is_registered=True,
        is_canonical=True,
        canonical_authority_valid=True,
        authority_state="VERIFIED_CANONICAL",
        lease_id="HL-" + "a"*24,
        fencing_token="F-" + "b"*24,
        reservation_id="RS-xyz",
        lease_valid=True,
        broker_admission="ADMIT",
        active_writer_present=False,
        canonical_main_sha="e7d903c1" + "0" * 32,
        expected_main_sha="e7d903c1" + "0" * 32,
        branch="r184/local-workbuddy-bridge",
        expected_branch="r184/local-workbuddy-bridge",
        route_epoch_valid=True,
        isolation_required=True,
        isolated_worktree="F:/worktrees/second-brain-coordination/R184-LOCAL-BRIDGE",
        carrier="LOCAL_WORKBUDDY_BRIDGE",
        execution_identity="HX" + "a" * 30,
        model="deepseek-v4-pro",
        required_model="deepseek-v4-pro",
        collision_domain="apps/second-brain-command-center",
        declared_collision_domain="apps/second-brain-command-center",
        cli_path="codebuddy",
        adapter="FAKE_PROCESS_ADAPTER",
        duplicate_receipt_present=False,
    )
    base.update(overrides)
    return AuthorityView(**base)


class TestAdversarialRefusals(unittest.TestCase):
    def test_00_happy_path_plans_and_never_launches(self):
        plan = plan_launch(_valid_view())
        self.assertIs(plan.decision, BridgeDecision.PLANNED)
        self.assertTrue(plan.dry_run)
        self.assertFalse(plan.launches_real_process)

    def test_01_stale_canonical_main_rejected(self):
        view = _valid_view(canonical_main_sha="f" * 40, expected_main_sha="e" * 40)
        plan = plan_launch(view)
        self.assertIs(plan.decision, BridgeDecision.REFUSED_STALE_MAIN)

    def test_01b_stale_route_epoch_rejected(self):
        plan = plan_launch(_valid_view(route_epoch_valid=False))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_STALE_MAIN)

    def test_02_unregistered_task_rejected(self):
        plan = plan_launch(_valid_view(is_registered=False))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_UNREGISTERED_TASK)

    def test_03_wrong_lease_rejected(self):
        plan = plan_launch(_valid_view(lease_valid=False))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_AUTHORITY_MISMATCH)

    def test_03b_missing_fencing_token_rejected(self):
        plan = plan_launch(_valid_view(fencing_token=""))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_AUTHORITY_MISMATCH)

    def test_03c_missing_reservation_rejected(self):
        plan = plan_launch(_valid_view(reservation_id=""))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_AUTHORITY_MISMATCH)

    def test_03d_trust_gate_refusal_rejected(self):
        plan = plan_launch(_valid_view(canonical_authority_valid=False))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_AUTHORITY_MISMATCH)

    def test_04_duplicate_identity_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            bridge = LocalWorkBuddyBridge(receipt_root=tmp)
            inputs = _inputs()
            first = bridge.evaluate(inputs)
            self.assertIs(first.plan.decision, BridgeDecision.PLANNED)
            self.assertIsNotNone(first.receipt_id)

            second = bridge.evaluate(inputs)
            self.assertIs(second.plan.decision, BridgeDecision.REFUSED_DUPLICATE)
            self.assertIsNone(second.receipt_id)
            # No second writer: exactly one receipt on disk.
            self.assertEqual(bridge.receipts.count(), 1)

    def test_05_branch_mismatch_rejected(self):
        plan = plan_launch(
            _valid_view(branch="feature/other", expected_branch="r184/main")
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_BASE_MISMATCH)

    def test_06_collision_conflict_rejected(self):
        plan = plan_launch(
            _valid_view(broker_admission="BLOCK_CONFLICT"),
            active_collision_domains={"apps/x": "HXother"},
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)

    def test_06a_live_writer_holding_domain_rejected(self):
        plan = plan_launch(
            _valid_view(active_writer_present=True, collision_domain="apps/x"),
            active_collision_domains={"apps/x": "HXother"},
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)

    def test_06b_unauthorized_collision_domain_rejected(self):
        plan = plan_launch(
            _valid_view(collision_domain="apps/unlisted"),
            allowed_collision_domains=["apps/listed"],
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)

    def test_07_candidate_only_rejected(self):
        plan = plan_launch(_valid_view(is_canonical=False))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_CANDIDATE_ONLY)

    def test_08_model_mismatch_rejected(self):
        plan = plan_launch(_valid_view(model="glm-5", required_model="deepseek-v4-pro"))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_MODEL_UNAVAILABLE)

    def test_08b_model_unavailable_rejected(self):
        plan = plan_launch(_valid_view(model="unknown-model-9", required_model=""))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_MODEL_UNAVAILABLE)

    def test_08c_no_silent_tier_upgrade(self):
        plan = plan_launch(_valid_view(model="gpt-6", required_model=""))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_MODEL_UNAVAILABLE)
        result = preflight_model("gpt-6")
        self.assertFalse(result.ok)
        self.assertIn("tier", result.reason)

    def test_09_hidden_shell_never_executes(self):
        """argv is metadata only. No code path runs it in 2B."""
        plan = plan_launch(_valid_view())
        self.assertIs(plan.decision, BridgeDecision.PLANNED)
        # argv must be derived from validated fields, no shell metacharacters,
        # and the plan must never claim a real launch.
        for token in plan.argv:
            for meta in (";", "|", "&&", "$(", "`", ">"):
                self.assertNotIn(meta, token)
        self.assertFalse(plan.launches_real_process)

        adapter = FakeProcessAdapter()
        note = adapter.launch(plan)
        self.assertFalse(note["launched"])
        self.assertIsNone(note["pid"])
        self.assertEqual(adapter.launch_calls, 1)

    def test_09b_plan_cannot_claim_real_launch(self):
        with self.assertRaises(BridgeBoundaryError):
            LaunchPlan(
                decision=BridgeDecision.PLANNED,
                reason="x",
                launches_real_process=True,
            )

    def test_10_credentials_redacted(self):
        # Assemble a synthetic, non-functional token at runtime so that no
        # real credential shape is ever persisted in this repository.
        secret = "ghp_" + "SYNTHETICNOTAREALTOKEN" * 2
        self.assertTrue(contains_secret(secret))
        self.assertNotIn("ghp_", redact(f"token is {secret}"))
        self.assertIn("[REDACTED]", redact(f"token is {secret}"))

        with self.assertRaises(BridgeBoundaryError):
            build_return_package(
                task_id="T",
                route_epoch=1,
                branch="b",
                tests=[f"leaked {secret}"],
            )

    def test_10b_receipt_store_rejects_secret_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LaunchReceiptStore(tmp)
            synthetic = "ghp_" + "SYNTHETICNOTAREALTOKEN" * 2
            # Directly poison the store file; the next save must fail closed.
            store._path.write_text(
                json.dumps({"x": synthetic}), encoding="utf-8"
            )
            with self.assertRaises(BridgeBoundaryError):
                store.record(
                    task_id="T", route_epoch=1,
                    execution_identity="HX", decision=BridgeDecision.PLANNED,
                )

    def test_11_fencing_token_falsification_rejected(self):
        """A forged/stale fencing token must not admit a writer."""
        for forged in ("", "F-", "F-forged"):
            plan = plan_launch(_valid_view(fencing_token=forged))
            self.assertIs(
                plan.decision,
                BridgeDecision.REFUSED_AUTHORITY_MISMATCH,
                msg=f"fencing token {forged!r} was not rejected",
            )

    def test_12_no_real_child_process_in_tests(self):
        """The bridge must refuse to hand a plan to a non-fake adapter."""
        class RealishAdapter:
            adapter_id = "CODEBUDDY_CLI_SUBPROCESS"

            def identity(self):
                return self.adapter_id

            def plan(self, plan):
                return plan

            def launch(self, plan):  # pragma: no cover - must never run
                raise AssertionError("real adapter was invoked during tests")

        with tempfile.TemporaryDirectory() as tmp:
            bridge = LocalWorkBuddyBridge(
                receipt_root=tmp, adapter=RealishAdapter()
            )
            # A fully-valid input would otherwise be PLANNED and handed off.
            with self.assertRaises(BridgeBoundaryError):
                bridge.evaluate(_inputs())

    def test_12b_unknown_adapter_rejected(self):
        plan = plan_launch(_valid_view(adapter="EVIL_ADAPTER"))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_UNKNOWN_ADAPTER)

    def test_13_windows_case_insensitive_collision_identity(self):
        """`Apps\\X` and `apps/x` must be the SAME collision domain on Windows."""
        from tools.local_workbuddy_bridge.launch_plan import normalize_domain

        self.assertEqual(normalize_domain("Apps\\X"), normalize_domain("apps/x"))

        # The gate itself must treat a case/separator variant as a conflict.
        plan = plan_launch(
            _valid_view(
                active_writer_present=True,
                collision_domain="apps/x",
            ),
            active_collision_domains={"Apps\\X": "HXother"},
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)

    def test_13b_unicode_normalization_stable(self):
        from tools.local_workbuddy_bridge.launch_plan import normalize_domain

        # NFC vs NFD for the same visual string must collapse to one identity.
        composed = "\u00e9"          # é
        decomposed = "e\u0301"       # e + combining acute
        self.assertEqual(normalize_domain(composed), normalize_domain(decomposed))

        # And a decomposed form must still collide with a live writer holding
        # the composed form.
        plan = plan_launch(
            _valid_view(active_writer_present=True, collision_domain=f"apps/{composed}"),
            active_collision_domains={f"apps/{decomposed}": "HXother"},
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)


class TestReceiptStoreDurability(unittest.TestCase):
    def test_receipt_survives_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            store_a = LaunchReceiptStore(tmp)
            receipt = store_a.record(
                task_id="T", route_epoch=7,
                execution_identity="HX", decision=BridgeDecision.PLANNED,
            )
            store_b = LaunchReceiptStore(tmp)
            found = store_b.find(receipt.idempotency_key)
            self.assertIsNotNone(found)
            self.assertEqual(found.receipt_id, receipt.receipt_id)
            self.assertEqual(store_b.count(), 1)

    def test_record_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LaunchReceiptStore(tmp)
            first = store.record(
                task_id="T", route_epoch=7, execution_identity="HX",
                decision=BridgeDecision.PLANNED,
            )
            second = store.record(
                task_id="T", route_epoch=7, execution_identity="HX",
                decision=BridgeDecision.PLANNED,
            )
            self.assertEqual(first.receipt_id, second.receipt_id)
            self.assertEqual(store.count(), 1)


class TestModelPreflight(unittest.TestCase):
    def test_free_text_rejected(self):
        result = preflight_model("please use the best model!")
        self.assertFalse(result.ok)

    def test_empty_rejected(self):
        self.assertFalse(preflight_model("").ok)
        self.assertFalse(preflight_model(None).ok)

    def test_structured_token_accepted(self):
        self.assertTrue(preflight_model("deepseek-v4-pro").ok)


def _inputs(**overrides) -> dict:
    base = dict(
        task_id="R184-LOCAL-BRIDGE",
        route_epoch=41,
        is_registered=True,
        is_canonical=True,
        canonical_authority_valid=True,
        lease_id="HL-" + "a"*24,
        fencing_token="F-" + "b"*24,
        reservation_id="RS-xyz",
        lease_valid=True,
        broker_admission="ADMIT",
        canonical_main_sha="e" * 40,
        expected_main_sha="e" * 40,
        branch="r184/main",
        expected_branch="r184/main",
        isolated_worktree="F:/worktrees/second-brain-coordination/R184-LOCAL-BRIDGE",
        carrier="LOCAL_WORKBUDDY_BRIDGE",
        execution_identity="HX" + "a" * 30,
        model="deepseek-v4-pro",
        required_model="deepseek-v4-pro",
        collision_domain="apps/x",
        cli_path="codebuddy",
        adapter="FAKE_PROCESS_ADAPTER",
    )
    base.update(overrides)
    return base


class TestWorktreeIsolation(unittest.TestCase):
    """TASK-BRIEF: 'Create one isolated worktree or clone per write task'."""

    def test_write_task_without_isolated_worktree_rejected(self):
        plan = plan_launch(_valid_view(isolated_worktree=""))
        self.assertIs(plan.decision, BridgeDecision.REFUSED_BASE_MISMATCH)

    def test_shared_worktree_is_a_collision(self):
        plan = plan_launch(
            _valid_view(
                isolated_worktree="F:/worktrees/R184",
                active_worktree_holders={"f:/worktrees/r184/": "HXother"},
                active_writer_present=False,
            )
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_COLLISION_CONFLICT)

    def test_plan_isolated_worktree_stays_inside_root(self):
        from tools.local_workbuddy_bridge import plan_isolated_worktree

        plan = plan_isolated_worktree(
            task_id="R184-LOCAL-BRIDGE",
            branch="workbuddy/r184-local-workbuddy-bridge",
            base_sha="b" * 40,
            execution_repository="F:/SecondBrainWorkspace/repos/second-brain-coordination",
            worktree_root="F:/worktrees",
        )
        self.assertFalse(plan.creates_real_worktree)
        self.assertIn("R184-LOCAL-BRIDGE", plan.worktree_path)

    def test_path_traversal_rejected(self):
        from tools.local_workbuddy_bridge import plan_isolated_worktree

        for evil in ("../escape", "..\\escape", "C:/abs", "a/b", ".."):
            with self.assertRaises(BridgeBoundaryError, msg=f"allowed {evil!r}"):
                plan_isolated_worktree(
                    task_id=evil,
                    branch="b",
                    base_sha="b" * 40,
                    execution_repository="R",
                    worktree_root="F:/worktrees",
                )

    def test_unsafe_branch_rejected(self):
        from tools.local_workbuddy_bridge import plan_isolated_worktree

        for evil in ("-flag", "a..b", "a b", "a~b", "a^b", "a:b", "a?b", "a*b"):
            with self.assertRaises(BridgeBoundaryError, msg=f"allowed {evil!r}"):
                plan_isolated_worktree(
                    task_id="T",
                    branch=evil,
                    base_sha="b" * 40,
                    execution_repository="R",
                    worktree_root="F:/worktrees",
                )


class TestRegistryAdapter(unittest.TestCase):
    """TASK-BRIEF: 'Discover executable work only from registered task indexes'."""

    def _write_index(self, tmp: str, payload: str) -> str:
        path = Path(tmp) / "ACTIVE-TASK-INDEX-REGISTRY.json"
        path.write_text(payload, encoding="utf-8")
        return str(path)

    def test_unregistered_task_reports_not_registered(self):
        from tools.local_workbuddy_bridge import RegistryAdapter

        with tempfile.TemporaryDirectory() as tmp:
            adapter = RegistryAdapter(
                index_paths=(Path(self._write_index(tmp, '{"active": []}')),)
            ).load()
            self.assertFalse(adapter.is_registered("NOPE"))
            self.assertIsNone(adapter.get("NOPE"))

    def test_registered_ready_task_is_executable(self):
        from tools.local_workbuddy_bridge import RegistryAdapter

        payload = (
            '{"active": [{"task_id": "R184-LOCAL-BRIDGE", "route_epoch": 184,'
            ' "status": "READY", "execution_allowed": true,'
            ' "branch": "workbuddy/r184", "base_sha": "b'
            + "0" * 39
            + '"}]}'
        )
        with tempfile.TemporaryDirectory() as tmp:
            adapter = RegistryAdapter(
                index_paths=(Path(self._write_index(tmp, payload)),)
            ).load()
            self.assertTrue(adapter.is_registered("R184-LOCAL-BRIDGE"))
            task = adapter.get("R184-LOCAL-BRIDGE")
            self.assertEqual(task.route_epoch, 184)
            self.assertTrue(task.execution_allowed)

    def test_r175_frozen_task_discoverable_but_not_executable(self):
        """R175 must stay discoverable yet never become executable again."""
        from tools.local_workbuddy_bridge import RegistryAdapter

        payload = (
            '{"active": [{"task_id": "R175-LEGACY", "route_epoch": 175,'
            ' "status": "SUSPENDED", "execution_allowed": false}]}'
        )
        with tempfile.TemporaryDirectory() as tmp:
            adapter = RegistryAdapter(
                index_paths=(Path(self._write_index(tmp, payload)),)
            ).load()
            # Discoverable: still in the registry, unchanged.
            self.assertTrue(adapter.is_discoverable("R175-LEGACY"))
            # Not executable: cannot be routed to again.
            self.assertFalse(adapter.is_registered("R175-LEGACY"))

    def test_r175_route_ends_to_frozen_state_fails_closed(self):
        """A frozen ancestor must fail the bridge closed if ever dispatched."""
        plan = plan_launch(
            _valid_view(task_id="R175-LEGACY", is_registered=False)
        )
        self.assertIs(plan.decision, BridgeDecision.REFUSED_UNREGISTERED_TASK)

    def test_missing_index_file_is_tolerated(self):
        from tools.local_workbuddy_bridge import RegistryAdapter

        adapter = RegistryAdapter(
            index_paths=(Path("does/not/exist.json"),)
        ).load()
        self.assertEqual(adapter.count(), 0)


if __name__ == "__main__":
    unittest.main()
