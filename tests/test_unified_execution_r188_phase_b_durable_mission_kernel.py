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

    def test_registry_wide_r175_r184_r188_and_full_r188_chain_pass(self):
        with self._trusted_tree():
            authorities = registry.build_registered_authorities(".")
        by_task = {item.as_mapping()["task_id"]: item.as_mapping() for item in authorities}
        self.assertEqual(
            set(by_task),
            {
                "WORKBUDDY-R175-ORDERED-BATCH",
                "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
                "WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL",
            },
        )
        r188 = by_task["WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL"]
        self.assertEqual(list(r188["authorized_paths"]), R188_PATHS)
        self.assertEqual(r188["collision_domain"], R188_COLLISION)
        self.assertIn("WRITE_AUTHORIZED_PATHS", r188["authority_grants"])

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

    def test_r188_registry_membership_replaces_terminal_r186_r187_without_replay(self):
        text = self._read(registry.REGISTRY_REF).decode("utf-8")
        self.assertIn(R175_INDEX, text)
        self.assertIn(R184_INDEX, text)
        self.assertIn(R188_INDEX, text)
        self.assertNotIn(R186_INDEX, text)
        self.assertNotIn(R187_INDEX, text)

    def test_r188_active_index_blocks_until_independent_review_and_canonicalization(self):
        text = self._read(R188_INDEX).decode("utf-8")
        self.assertIn(
            'blocked_by: "INDEPENDENT_REVIEW_AND_CANONICAL_PUBLICATION_BEFORE_PROCESS_START"',
            text,
        )
        self.assertIn("execution_allowed: true", text)
        self.assertIn("second_user_start_command_required: true", text)
        self.assertIn("automatic_resume: false", text)

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


if __name__ == "__main__":
    unittest.main()
