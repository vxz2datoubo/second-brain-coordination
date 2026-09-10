from contextlib import ExitStack
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordination.EXECUTION import unified_active_task_registry as registry


ROOT = Path(__file__).resolve().parents[1]
MOCK_MAIN = "f" * 40
R175_INDEX = registry.LEGACY_DEFAULT_REF
R184_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R184-LOCAL-BRIDGE.yaml"
R186_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE.yaml"
R187_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE.yaml"
R188_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL.yaml"
R188_COLLISION = "WRITESET_SHA256:9c0a00896e480f96bc8d1e5ad3b451b05a997fdffca8e0e78ca29a0c9406d53d"
R188_PATHS = [
    "tools/durable_mission_kernel/**",
    "tests/durable_mission_kernel/**",
    "tests/test_unified_execution_durable_mission_kernel.py",
    "coordination/EXECUTION/PHASE-B-DURABLE-MISSION-KERNEL/**",
    "coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/**",
]
EVIDENCE_CONTRACT = "coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/EVIDENCE-CONTRACT.yaml"
BATCH = "coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/EXECUTABLE-BATCH.json"
ROUTE = "coordination/ROUTES/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL.yaml"
PREWRITE = "coordination/EXECUTION/WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL/PREWRITE-RECONCILIATION-SNAPSHOT.yaml"
EXECUTOR_POOL_ARCHITECTURE = "coordination/GOVERNANCE/MULTI-GPT-N-WORKBUDDY-EXECUTOR-POOL-ARCHITECTURE-v1.0.yaml"
TYPED_NUMERIC_LEDGER = "coordination/GOVERNANCE/TYPED-NUMERIC-PARAMETER-AND-EXPERIMENT-LEDGER-v1.0.yaml"
base = registry.base


class R188PhaseBDurableMissionKernelGovernanceTests(unittest.TestCase):
    def _read(self, path):
        return (ROOT / path).read_bytes()

    def _trusted_tree(self):
        stack = ExitStack()
        stack.enter_context(
            patch.object(
                registry.gate, "_protected_open", return_value=(MOCK_MAIN, self._read)
            )
        )
        stack.enter_context(patch.object(registry.gate, "_revalidate_project_adapter_at_sha"))
        stack.enter_context(patch.object(registry.gate, "_terminal_remote_main_recheck"))
        return stack

    def _authority(self):
        return registry.build_verified_canonical_authority_for_task_index(".", R188_INDEX)

    def test_registry_preserves_r175_r184_and_allows_later_registered_successors(self):
        with self._trusted_tree():
            authorities = registry.build_registered_authorities(".")
        by_task = {item.as_mapping()["task_id"]: item.as_mapping() for item in authorities}
        self.assertTrue(
            {
                "WORKBUDDY-R175-ORDERED-BATCH",
                "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
            }.issubset(by_task)
        )
        for terminal_task in (
            "WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE",
            "WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE",
            "WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL",
        ):
            self.assertNotIn(terminal_task, by_task)

    def test_r188_collision_domain_matches_canonical_reservation_surface(self):
        digest = sha256(
            json.dumps(sorted(R188_PATHS), separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual("WRITESET_SHA256:" + digest, R188_COLLISION)

    def test_r188_reservation_surface_is_disjoint_from_r175_and_r184(self):
        r175 = ["tests/workbuddy/**", "tools/workbuddy/**"]
        r184 = [
            "tools/local_workbuddy_bridge/**",
            "tests/test_unified_execution_local_bridge.py",
            "tests/fixtures/local_workbuddy_bridge/**",
        ]
        for r188_path in R188_PATHS:
            for peer_path in r175 + r184:
                self.assertNotEqual(r188_path, peer_path)
                self.assertFalse(
                    r188_path.startswith(peer_path.replace("/**", "/")),
                    f"{r188_path} overlaps {peer_path}",
                )
                self.assertFalse(
                    peer_path.startswith(r188_path.replace("/**", "/")),
                    f"{r188_path} overlaps {peer_path}",
                )

    def test_r188_removed_from_active_registry_and_cannot_replay(self):
        text = self._read(registry.REGISTRY_REF).decode("utf-8")
        self.assertIn(R175_INDEX, text)
        self.assertIn(R184_INDEX, text)
        self.assertNotIn(R188_INDEX, text)
        self.assertNotIn(R186_INDEX, text)
        self.assertNotIn(R187_INDEX, text)
        with self._trusted_tree():
            with self.assertRaises(registry.ExecutionContractError) as ctx:
                registry.build_verified_canonical_authority_for_task_index(".", R188_INDEX)
        self.assertIn("not registered", str(ctx.exception))

    def test_r188_active_index_is_terminal_non_executable(self):
        text = self._read(R188_INDEX).decode("utf-8")
        self.assertIn('status: "CLOSED_HISTORY_ONLY_CANONICALIZED"', text)
        self.assertIn("execution_allowed: false", text)
        self.assertIn("active: false", text)
        self.assertIn("blocked_by: null", text)
        self.assertIn("second_user_start_command_required: false", text)
        self.assertIn("automatic_resume: false", text)
        self.assertIn("completion_evidence:", text)
        self.assertIn(
            'canonical_merge: "d062dee5a8690cc0564b22b7ba8486a46226e854"', text
        )

    def test_r188_evidence_contract_freezes_hard_invariants_and_result_classes(self):
        text = self._read(EVIDENCE_CONTRACT).decode("utf-8")
        required = (
            '- "no self-review"',
            '- "no self-merge"',
            'SYNTHETIC_KERNEL_RESULT',
            'WINDOWS_CONTAINMENT_RESULT',
            'HEADLESS_ADAPTER_RESULT',
            'SDK_ADAPTER_RESULT',
            'REAL_CANONICALIZER_CAPABILITY_RESULT',
            'EXACT_HEAD_CI_RESULT',
            'INDEPENDENT_REVIEW_RESULT',
            'CANONICALIZATION_RESULT',
            "self_merge_permanently_forbidden: true",
            "canonicalizer_ready_requires:",
        )
        for literal in required:
            self.assertIn(literal, text)

    def test_r188_batch_is_b0_to_b8_with_planned_status(self):
        batch = json.loads(self._read(BATCH).decode("utf-8"))
        self.assertEqual(
            [item["item_id"] for item in batch["items"]],
            ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8"],
        )
        self.assertTrue(all(item["status"] == "PLANNED" for item in batch["items"]))
        self.assertEqual(
            batch["route_authority"]["task_id"],
            "WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL",
        )
        self.assertEqual(
            batch["route_authority"]["route_epoch"], 188
        )
        self.assertEqual(
            batch["canonical_collision_reservation"]["expected_collision_domain"],
            R188_COLLISION,
        )
        self.assertIn("WRITE_AUTHORIZED_PATHS", batch["runtime_dispatch"]["authority_grants"])
        self.assertFalse(batch["runtime_dispatch"]["direct_main_write_allowed"])
        self.assertFalse(batch["runtime_dispatch"]["production_deployment_allowed"])

    def test_r188_batch_write_paths_are_within_reservation(self):
        batch = json.loads(self._read(BATCH).decode("utf-8"))
        for item in batch["items"]:
            for write_path in item["write_paths"]:
                self.assertIn(
                    write_path,
                    R188_PATHS,
                    f"batch item {item['item_id']} write_path outside reservation: {write_path}",
                )

    def test_r188_route_declares_governed_branch_write_not_identity_only(self):
        text = self._read(ROUTE).decode("utf-8")
        self.assertNotIn("branch_identity_only_no_branch_write: true", text)
        self.assertIn(
            'branch_write_semantics: "GOVERNED_IMPLEMENTATION_BRANCH_WRITE_AUTHORIZED"',
            text,
        )
        self.assertIn("candidate_branch_write_allowed: true", text)
        self.assertIn("direct_main_write_allowed: false", text)
        self.assertIn("history_rewrite_allowed: false", text)

    def test_r188_batch_allows_candidate_branch_write_but_denies_main_and_rewrite(self):
        batch = json.loads(self._read(BATCH).decode("utf-8"))
        dispatch = batch["runtime_dispatch"]
        self.assertTrue(dispatch["github_write_allowed"])
        self.assertTrue(dispatch["branch_write_allowed"])
        self.assertFalse(dispatch["direct_main_write_allowed"])
        self.assertFalse(dispatch["history_rewrite_allowed"])
        self.assertFalse(dispatch["production_deployment_allowed"])

    def test_r188_active_index_retains_main_and_history_rewrite_denials(self):
        text = self._read(R188_INDEX).decode("utf-8")
        self.assertIn('- "NO_DIRECT_MAIN_WRITE"', text)
        self.assertIn('- "NO_FORCE_PUSH_REBASE_RESET_AMEND_HISTORY_REWRITE"', text)
        self.assertIn('- "NO_SELF_REVIEW"', text)
        self.assertIn('- "NO_SELF_MERGE"', text)

    def test_r188_route_reuses_executor_pool_and_typed_numeric_ledger(self):
        text = self._read(ROUTE).decode("utf-8")
        self.assertIn(EXECUTOR_POOL_ARCHITECTURE, text)
        self.assertIn(TYPED_NUMERIC_LEDGER, text)
        self.assertIn("reuse_not_replace: true", text)
        self.assertIn("duplicate_control_plane_forbidden: true", text)
        self.assertIn("duplicate_numeric_ledger_forbidden: true", text)
        self.assertIn("second_control_tower_forbidden: true", text)

    def test_r188_route_hard_stops_ban_duplicate_control_plane_and_numeric_ledger(self):
        text = self._read(ROUTE).decode("utf-8")
        self.assertIn(
            "a second control plane, second control tower, or duplicate numeric/experiment ledger would need to be created instead of reusing the canonical executor-pool architecture and typed numeric ledger",
            text,
        )

    def test_r188_prewrite_records_fresh_main_and_reused_contracts(self):
        text = self._read(PREWRITE).decode("utf-8")
        self.assertIn("fresh_main_at_remediation", text)
        self.assertIn("d3e83dde61ec8d942db45cd8aba70ee484013024", text)
        self.assertIn(EXECUTOR_POOL_ARCHITECTURE, text)
        self.assertIn(TYPED_NUMERIC_LEDGER, text)
        self.assertIn("duplicate_control_plane_forbidden: true", text)
        self.assertIn("duplicate_numeric_ledger_forbidden: true", text)


if __name__ == "__main__":
    unittest.main()
