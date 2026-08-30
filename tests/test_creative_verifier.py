from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creative_runtime_verifier", ROOT / "tools" / "verify_creative_runtime.py")
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class CreativeVerifierTests(unittest.TestCase):
    def test_verifier_produces_a_reproducible_offline_receipt(self) -> None:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, text=True, capture_output=True).stdout.strip()
        # The verifier's normal suite includes this test module, so this unit
        # test checks its deterministic demo path without recursively starting
        # another copy of the whole suite. The command-line verifier itself is
        # run with its default full-suite setting at clean milestones.
        receipt = verifier.verify(head, run_test_suite=False, require_clean_worktree=False)
        self.assertEqual(receipt["head_sha"], head)
        self.assertEqual(receipt["unit_test_status"], "skipped_for_verifier_self_test")
        self.assertEqual(receipt["worktree_status"], "not_checked_for_verifier_self_test")
        self.assertEqual(receipt["demonstration"]["final_state"]["scene_id"], "interior_archive")
        self.assertEqual(receipt["demonstration"]["knowledge_candidate_status"], "pending_human_review")
        self.assertEqual(receipt["demonstration"]["v2_source_binding_status"], "v2_source_verified")
        self.assertEqual(receipt["demonstration"]["session_receipt_status"], "session_source_verified")
        self.assertFalse(receipt["demonstration"]["session_receipt_contains_events"])
        self.assertFalse(receipt["demonstration"]["session_receipt_contains_customer_material"])
        self.assertEqual(receipt["demonstration"]["generation_status"], "offline_generation_recorded")
        self.assertEqual(receipt["demonstration"]["generation_verification_status"], "offline_generation_verified")
        self.assertEqual(receipt["demonstration"]["frame_status"], "interactive_frame_verified")
        self.assertEqual(receipt["demonstration"]["frame_choice_count"], 1)
        self.assertEqual(receipt["demonstration"]["frame_slot"], "default")
        self.assertEqual(receipt["demonstration"]["experience_status"], "experience_manifest_verified")
        self.assertEqual(receipt["demonstration"]["experience_frame_count"], 4)
        self.assertEqual(receipt["demonstration"]["sequence_status"], "sequence_plan_verified")
        self.assertEqual(receipt["demonstration"]["sequence_step_count"], 4)
        self.assertEqual(receipt["demonstration"]["sequence_total_duration_seconds"], 52)
        self.assertEqual(receipt["demonstration"]["catalog_status"], "scenario_catalog_verified")
        self.assertEqual(receipt["demonstration"]["catalog_transition_count"], 14)
        self.assertEqual(receipt["demonstration"]["feedback_status"], "feedback_recorded")
        self.assertFalse(receipt["demonstration"]["feedback_canonical_write"])
        self.assertEqual(receipt["demonstration"]["audit_status"], "workspace_audit_verified")
        self.assertEqual(receipt["demonstration"]["route_coverage_status"], "route_coverage_verified")
        self.assertEqual(receipt["demonstration"]["night_signal_coverage_status"], "route_coverage_verified")
        self.assertEqual(receipt["demonstration"]["night_signal_route_count"], 12)
        self.assertEqual(receipt["demonstration"]["director_coverage_status"], "director_coverage_verified")
        self.assertEqual(receipt["demonstration"]["director_coverage_state_count"], 12)
        self.assertEqual(receipt["demonstration"]["night_signal_director_coverage_status"], "director_coverage_verified")
        self.assertEqual(receipt["demonstration"]["night_signal_director_coverage_state_count"], 24)
        self.assertEqual(receipt["demonstration"]["harbor_protocol_director_coverage_status"], "director_coverage_verified")
        self.assertEqual(receipt["demonstration"]["harbor_protocol_director_coverage_state_count"], 24)
        self.assertEqual(receipt["demonstration"]["director_review_status"], "director_review_board_verified")
        self.assertEqual(receipt["demonstration"]["director_review_card_count"], 12)
        self.assertEqual(receipt["demonstration"]["night_signal_director_review_status"], "director_review_board_verified")
        self.assertEqual(receipt["demonstration"]["night_signal_director_review_card_count"], 24)
        self.assertEqual(receipt["demonstration"]["named_slot_id"], "route_b")
        self.assertEqual(receipt["demonstration"]["named_slot_generation_slot"], "route_b")
        self.assertEqual(receipt["demonstration"]["named_slot_audit_feedback_count"], 1)
        self.assertEqual(receipt["demonstration"]["realtime_first_command_status"], "chosen")
        self.assertEqual(receipt["demonstration"]["realtime_retry_status"], "command_already_applied")
        self.assertTrue(receipt["demonstration"]["realtime_retry_frame_matches"])
        self.assertTrue(receipt["demonstration"]["realtime_stale_frame_rejected"])
        self.assertEqual(receipt["demonstration"]["realtime_event_count"], 2)
        self.assertEqual(receipt["demonstration"]["local_intake_projection_status"], "local_intake_projection_valid")
        self.assertFalse(receipt["demonstration"]["local_intake_external_authorized"])
        self.assertEqual(
            receipt["demonstration"]["v2_source_binding_timeline_hash"],
            receipt["demonstration"]["timeline_hash"],
        )
        self.assertEqual(
            receipt["demonstration"]["frame_director_timeline_hash"],
            receipt["demonstration"]["timeline_hash"],
        )
        self.assertEqual(
            receipt["demonstration"]["experience_timeline_hash"],
            receipt["demonstration"]["timeline_hash"],
        )
        self.assertEqual(
            receipt["demonstration"]["sequence_timeline_hash"],
            receipt["demonstration"]["timeline_hash"],
        )

    def test_verifier_rejects_a_nonmatching_exact_head(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "Exact-head mismatch"):
            verifier.verify("0" * 40)


if __name__ == "__main__":
    unittest.main()
