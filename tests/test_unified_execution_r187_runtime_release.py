from contextlib import ExitStack
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from coordination.EXECUTION import unified_active_task_registry as registry
from coordination.GOVERNANCE import unified_execution_validation_base as base


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_MAIN = "5fea61a6eb98d3c9599daee93e20f161064a292b"
R187_RELEASE_HEAD = "61ff56f1f1ad9c84e40bb68b3860a10bd1d6befb"
MOCK_MAIN = "f" * 40
R187_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE.yaml"
R187_ROUTE = "coordination/ROUTES/WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE.yaml"
REGISTRY = "coordination/EXECUTION/ACTIVE-TASK-INDEX-REGISTRY.json"
RELEASE = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/EXECUTION-CARRIER-RELEASE.yaml"
LEASE = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/TASK-LEASE.yaml"
R175_INDEX = "coordination/ACTIVE-WORKBUDDY-TASK.yaml"
R184_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R184-LOCAL-BRIDGE.yaml"
COMPLETION_SIGNAL = "WORKBUDDY_R187_S1_SELECTED_WEB_SOURCE_CUTOFF_FRONTIER_PROBE_COMPLETE_RETURN_TO_GPT"


class R187RuntimeCompletionReleaseTests(unittest.TestCase):
    def _read(self, path):
        return (ROOT / path).read_bytes()

    def _registry_tree(self):
        stack = ExitStack()
        stack.enter_context(
            patch.object(registry.gate, "_protected_open", return_value=(MOCK_MAIN, self._read))
        )
        stack.enter_context(patch.object(registry.gate, "_revalidate_project_adapter_at_sha"))
        stack.enter_context(patch.object(registry.gate, "_terminal_remote_main_recheck"))
        return stack

    def _git_show_runtime_main(self, path):
        proc = subprocess.run(
            ["git", "show", f"{RUNTIME_MAIN}:{path}"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode("utf-8", errors="replace"))
        return proc.stdout

    def test_release_witness_binds_exact_original_writer_lease(self):
        release_text = self._read(RELEASE).decode("utf-8")
        self.assertEqual(base._scalar(release_text, "schema"), "EXECUTION_CARRIER_RELEASE_v1")
        with patch.object(base, "_open_trusted_main", return_value=(MOCK_MAIN, self._read)):
            witness = base.build_verified_release_witness(".", RELEASE)
        mapping = witness.as_mapping()
        original_lease = self._git_show_runtime_main(LEASE)
        expected_digest = base._sha(original_lease)
        self.assertEqual(
            expected_digest,
            "sha256:ace09e862b5863818d731e7f255cf44839bd20fc093e39e20a109f18fc54db3a",
        )
        self.assertEqual(mapping["released_lease_digest"], expected_digest)
        self.assertEqual(
            mapping["writer_lease_identity"],
            base._writer_lease_identity(mapping, mapping["writer_lease_ref"], expected_digest),
        )
        self.assertEqual(mapping["release_status"], "RELEASED")

    def test_r187_is_removed_from_active_registry_and_cannot_replay_process_start(self):
        registry_text = self._read(REGISTRY).decode("utf-8")
        self.assertNotIn(R187_INDEX, registry_text)
        with self._registry_tree():
            with self.assertRaises(registry.ExecutionContractError) as ctx:
                registry.build_verified_canonical_authority_for_task_index(".", R187_INDEX)
        self.assertIn("not registered", str(ctx.exception))

    def test_r187_index_and_route_are_nonexecuting_after_release_candidate(self):
        active = self._read(R187_INDEX).decode("utf-8")
        route = self._read(R187_ROUTE).decode("utf-8")
        self.assertEqual(base._scalar(active, "status"), "READY")
        self.assertIs(base._scalar(active, "execution_allowed"), False)
        self.assertIs(base._scalar(active, "active"), False)
        self.assertIs(base._scalar(active, "automatic_resume_within_batch"), False)
        self.assertIs(base._scalar(route, "execution_allowed"), False)
        self.assertIs(base._scalar(route, "automatic_resume_within_batch"), False)

    def test_registry_preserves_only_r175_and_r184_after_r188_terminalization(self):
        with self._registry_tree():
            authorities = registry.build_registered_authorities(".")
        tasks = {item.as_mapping()["task_id"] for item in authorities}
        self.assertEqual(
            tasks,
            {
                "WORKBUDDY-R175-ORDERED-BATCH",
                "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
            },
        )

    def test_r175_and_r184_active_indexes_are_byte_exact_unchanged_from_runtime_main(self):
        self.assertEqual(self._read(R175_INDEX), self._git_show_runtime_main(R175_INDEX))
        self.assertEqual(self._read(R184_INDEX), self._git_show_runtime_main(R184_INDEX))

    def test_runtime_review_findings_and_unknowns_are_carried_forward(self):
        text = self._read(RELEASE).decode("utf-8")
        required_literals = (
            COMPLETION_SIGNAL,
            "ACCEPT_WITH_BOUNDED_NONBLOCKING_FINDINGS",
            "NBF-REV-1",
            "PRE_ACTIVATION_REVIEW_RECORD_STATE_COMMENTED_VS_APPROVED_WORDING_NUANCE",
            "NBF-REV-2",
            "R186_INDEX_FILE_EXISTS_BUT_ACTIVE_FALSE_AND_NON_REPLAYABLE",
            "NBF-REV-3",
            "S4_POST_CUTOFF_EXCLUSION_PROOF_LOGICALLY_SOUND_BUT_MINIMALLY_DEMONSTRATED",
            'conversation_binding_digest: "de35c5fb49d0d70dbe524f809f5928f0aaabe98ed63850a36d9f319776e6de11"',
            'LIVE_OWNER_TRIGGER: "UNKNOWN"',
            'CURRENT_CONVERSATION_BINDING: "MACHINE_IDENTITY_BOUND_VIA_OWNER_PROVIDED_URL"',
            'EXACT_SOURCE_SCOPE: "PARTIAL"',
            'EXACT_CUTOFF_FRONTIER: "SYNTHETIC_MACHINERY_PROVEN / REAL_FRONTIER_UNKNOWN"',
            'AUTHENTICATED_INCREMENTAL_CAPTURE_TRANSPORT: "UNKNOWN"',
            'MOBILE_OFFLINE_DURABLE_INTAKE: "UNKNOWN"',
            'HARD_CAPTURE_CHECKPOINT_COMPLETE: "BLOCKED"',
        )
        for literal in required_literals:
            self.assertIn(literal, text)

    def test_completion_signal_is_consumed_without_starting_program_s2_or_next_s1_authority(self):
        text = self._read(RELEASE).decode("utf-8")
        self.assertIn('completion_signal_consumed: true', text)
        self.assertIn('workbuddy_executing_r187: false', text)
        self.assertIn('program_s2_may_start: false', text)
        self.assertIn('program_s2_started: false', text)
        self.assertIn('local_bridge_started: false', text)
        self.assertIn('r184_started_by_r187: false', text)
        self.assertIn('next_s1_execution_authority_created_by_this_release: false', text)

    def test_r187_historical_release_diff_is_governance_only_and_does_not_touch_r175_or_r184(self):
        proc = subprocess.run(
            ["git", "diff", "--name-only", RUNTIME_MAIN, R187_RELEASE_HEAD],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        changed = {line for line in proc.stdout.splitlines() if line}
        self.assertEqual(
            changed,
            {
                REGISTRY,
                R187_INDEX,
                R187_ROUTE,
                RELEASE,
                "tests/test_unified_execution_r187_runtime_release.py",
                "tests/test_unified_execution_s1_r187_selected_web_source_cutoff.py",
            },
        )
        self.assertNotIn(R175_INDEX, changed)
        self.assertNotIn(R184_INDEX, changed)


if __name__ == "__main__":
    unittest.main()
