from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import reversible_change as rc


def base_intent(**overrides):
    value = {
        "change_id": "R159-CASE",
        "surface_kind": "CODE_CONFIG_ONLY",
        "blast_radius": "SMALL",
        "explicit_rollback_marker_requested": False,
        "gpt_judged_large_change": False,
        "persistent_state_mutation": False,
        "external_irreversible_side_effect": False,
        "rollback_mechanism": "GIT_REVERT",
        "rollback_checkpoint_ref": None,
    }
    value.update(overrides)
    return value


class TempGitRepo:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.check_call(["git", "init", "-b", "main"], cwd=self.root, stdout=subprocess.DEVNULL)
        subprocess.check_call(["git", "config", "user.name", "R159 Test"], cwd=self.root)
        subprocess.check_call(["git", "config", "user.email", "r159@example.invalid"], cwd=self.root)
        (self.root / "tracked.txt").write_text("known-good\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "tracked.txt"], cwd=self.root)
        subprocess.check_call(["git", "commit", "-m", "known good"], cwd=self.root, stdout=subprocess.DEVNULL)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root, text=True).strip()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.tmp.cleanup()


def make_checkpoint(trigger="MANUAL_OPERATION", reason="anchor"):
    with TempGitRepo() as repo:
        return rc.capture_known_good_checkpoint(
            repo.root,
            repository="repo",
            expected_head=repo.head,
            trigger_source=trigger,
            reason=reason,
        )


class ReversibleChangeTests(unittest.TestCase):
    def test_01_small_code_only_is_git_reversible_without_marker(self):
        result = rc.assess_change_intent(base_intent())
        self.assertEqual(result["assessment_result"], "PASS")
        self.assertEqual(result["reversibility_class"], "REVERSIBLE_GIT_ONLY")
        self.assertFalse(result["rollback_marker_required"])

    def test_02_literal_trigger_phrase_is_detected(self):
        self.assertEqual(
            rc.trigger_from_user_text("先做个滚回记号，然后再改"),
            "USER_EXPLICIT_ROLLBACK_MARKER",
        )
        self.assertEqual(rc.trigger_from_user_text("直接继续"), "NONE")

    def test_03_explicit_marker_request_requires_checkpoint(self):
        result = rc.assess_change_intent(
            base_intent(explicit_rollback_marker_requested=True)
        )
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertTrue(result["rollback_marker_required"])
        self.assertIn("USER_EXPLICIT_ROLLBACK_MARKER", result["rollback_marker_reasons"])

    def test_04_large_change_requires_checkpoint(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertIn("BLAST_RADIUS_LARGE", result["rollback_marker_reasons"])

    def test_05_gpt_large_change_judgment_requires_checkpoint(self):
        result = rc.assess_change_intent(base_intent(gpt_judged_large_change=True))
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertIn("GPT_LARGE_CHANGE_JUDGMENT", result["rollback_marker_reasons"])

    def test_06_caller_minted_digest_does_not_satisfy_required_marker(self):
        result = rc.assess_change_intent(
            base_intent(blast_radius="LARGE", rollback_checkpoint_ref="a" * 64)
        )
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertFalse(result["rollback_checkpoint_binding_verified"])

    def test_06b_valid_checkpoint_object_satisfies_required_marker(self):
        checkpoint = make_checkpoint("GPT_LARGE_CHANGE_JUDGMENT")
        result = rc.assess_change_intent(
            base_intent(blast_radius="LARGE", rollback_checkpoint_ref=checkpoint["checkpoint_digest"]),
            checkpoint,
        )
        self.assertEqual(result["assessment_result"], "PASS")
        self.assertTrue(result["rollback_checkpoint_binding_verified"])

    def test_07_invalid_checkpoint_ref_fails_closed(self):
        with self.assertRaisesRegex(rc.ReversibleChangeError, "SHA256_REQUIRED"):
            rc.assess_change_intent(
                base_intent(blast_radius="LARGE", rollback_checkpoint_ref="not-a-digest")
            )

    def test_08_stateful_change_cannot_claim_git_only_recovery(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="GIT_REVERT",
                rollback_checkpoint_ref="b" * 64,
            )
        )
        self.assertEqual(result["reversibility_class"], "IRREVERSIBLE_OR_HIGH_RISK")
        self.assertEqual(result["assessment_result"], "BLOCKED_ROLLBACK_PLAN_INCOMPLETE")

    def test_09_stateful_snapshot_classifies_correctly(self):
        checkpoint = make_checkpoint("PRE_MATERIAL_CHANGE_POLICY")
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="SNAPSHOT",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        self.assertEqual(result["reversibility_class"], "REVERSIBLE_WITH_SNAPSHOT")
        self.assertEqual(result["assessment_result"], "PASS")

    def test_10_stateful_migration_classifies_correctly(self):
        checkpoint = make_checkpoint("PRE_MATERIAL_CHANGE_POLICY")
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="MEDIUM",
                persistent_state_mutation=True,
                rollback_mechanism="MIGRATION",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        self.assertEqual(result["reversibility_class"], "REVERSIBLE_WITH_MIGRATION")
        self.assertEqual(result["assessment_result"], "PASS")

    def test_11_policy_version_switch_classifies_correctly(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="POLICY_BEHAVIOR",
                blast_radius="MEDIUM",
                rollback_mechanism="FEATURE_FLAG_OR_VERSION_SWITCH",
            )
        )
        self.assertEqual(result["reversibility_class"], "REVERSIBLE_BY_VERSION_SWITCH")
        self.assertEqual(result["assessment_result"], "PASS")

    def test_12_external_compensation_is_not_called_reversible_git(self):
        checkpoint = make_checkpoint("PRE_MATERIAL_CHANGE_POLICY")
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="MEDIUM",
                rollback_mechanism="COMPENSATION",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        self.assertEqual(result["reversibility_class"], "COMPENSATABLE_ONLY")
        self.assertEqual(result["assessment_result"], "PASS")

    def test_13_external_irreversible_side_effect_requires_user_approval(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="CRITICAL",
                external_irreversible_side_effect=True,
                rollback_mechanism="NONE",
            )
        )
        self.assertEqual(result["reversibility_class"], "IRREVERSIBLE_OR_HIGH_RISK")
        self.assertEqual(result["assessment_result"], "USER_APPROVAL_REQUIRED")

    def test_14_unknown_enum_fails_closed(self):
        with self.assertRaisesRegex(rc.ReversibleChangeError, "UNSUPPORTED"):
            rc.assess_change_intent(base_intent(surface_kind="MAGIC"))

    def test_15_assessment_digest_tamper_is_rejected(self):
        result = rc.assess_change_intent(base_intent())
        result["reversibility_class"] = "REVERSIBLE_WITH_SNAPSHOT"
        with self.assertRaisesRegex(rc.ReversibleChangeError, "DIGEST_MISMATCH"):
            rc.validate_assessment(result)

    def test_16_assessment_authority_must_stay_false(self):
        result = rc.assess_change_intent(base_intent())
        self.assertTrue(all(v is False for v in result["authority"].values()))
        result["authority"]["grants_merge"] = True
        body = dict(result)
        body.pop("assessment_digest")
        result["assessment_digest"] = rc._digest(body)
        with self.assertRaisesRegex(rc.ReversibleChangeError, "AUTHORITY_BOUNDARY_MISMATCH"):
            rc.validate_assessment(result)

    def test_17_clean_exact_git_state_mints_checkpoint(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="vxz2datoubo/second-brain-coordination",
                expected_head=repo.head,
                trigger_source="GPT_LARGE_CHANGE_JUDGMENT",
                reason="before large change",
                evidence_refs=("review://accepted", "ci://green", "review://accepted"),
            )
        self.assertEqual(checkpoint["schema_version"], rc.CHECKPOINT_SCHEMA)
        self.assertEqual(checkpoint["canonical_commit"], repo.head)
        self.assertEqual(checkpoint["source_ref"], "main")
        self.assertTrue(checkpoint["git_binding_verified"])
        self.assertEqual(checkpoint["evidence_refs"], ["review://accepted", "ci://green"])
        self.assertTrue(checkpoint["checkpoint_id"].startswith("KGC-"))
        self.assertTrue(all(v is False for v in checkpoint["authority"].values()))
        rc.validate_known_good_checkpoint(checkpoint)

    def test_18_dirty_worktree_cannot_mint_checkpoint(self):
        with TempGitRepo() as repo:
            (repo.root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(rc.ReversibleChangeError, "WORKTREE_DIRTY"):
                rc.capture_known_good_checkpoint(
                    repo.root,
                    repository="repo",
                    expected_head=repo.head,
                    trigger_source="MANUAL_OPERATION",
                    reason="dirty should fail",
                )

    def test_19_untracked_file_also_counts_as_dirty(self):
        with TempGitRepo() as repo:
            (repo.root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(rc.ReversibleChangeError, "WORKTREE_DIRTY"):
                rc.capture_known_good_checkpoint(
                    repo.root,
                    repository="repo",
                    expected_head=repo.head,
                    trigger_source="MANUAL_OPERATION",
                    reason="untracked should fail",
                )

    def test_20_head_drift_cannot_mint_checkpoint(self):
        with TempGitRepo() as repo:
            with self.assertRaisesRegex(rc.ReversibleChangeError, "HEAD_DRIFT"):
                rc.capture_known_good_checkpoint(
                    repo.root,
                    repository="repo",
                    expected_head="0" * 40,
                    trigger_source="MANUAL_OPERATION",
                    reason="wrong head",
                )

    def test_21_wrong_branch_cannot_mint_canonical_checkpoint(self):
        with TempGitRepo() as repo:
            subprocess.check_call(["git", "checkout", "-b", "feature"], cwd=repo.root, stdout=subprocess.DEVNULL)
            with self.assertRaisesRegex(rc.ReversibleChangeError, "BRANCH_MISMATCH"):
                rc.capture_known_good_checkpoint(
                    repo.root,
                    repository="repo",
                    expected_head=repo.head,
                    trigger_source="MANUAL_OPERATION",
                    reason="wrong branch",
                )

    def test_22_checkpoint_digest_tamper_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="MANUAL_OPERATION",
                reason="known good",
            )
        checkpoint["reason"] = "tampered"
        with self.assertRaisesRegex(rc.ReversibleChangeError, "DIGEST_MISMATCH"):
            rc.validate_known_good_checkpoint(checkpoint)

    def test_23_git_only_revert_plan_is_history_preserving(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="GPT_LARGE_CHANGE_JUDGMENT",
                reason="anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(
                blast_radius="LARGE",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="effect regressed")
        self.assertEqual(plan["strategy"], "FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT")
        self.assertTrue(plan["preserve_history"])
        self.assertFalse(plan["destructive_history_rewrite"])
        self.assertTrue(plan["exact_head_reverification_required"])
        self.assertTrue(plan["independent_review_required"])
        rc.validate_governed_revert_plan(plan)

    def test_24_small_revert_does_not_force_independent_review(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="MANUAL_OPERATION",
                reason="anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(rollback_checkpoint_ref=checkpoint["checkpoint_digest"]),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="small correction")
        self.assertFalse(plan["independent_review_required"])

    def test_25_snapshot_revert_plan_requires_snapshot_restore(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="PRE_MATERIAL_CHANGE_POLICY",
                reason="stateful anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="SNAPSHOT",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="restore state")
        self.assertEqual(plan["strategy"], "FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE")

    def test_26_migration_revert_plan_requires_down_migration(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="PRE_MATERIAL_CHANGE_POLICY",
                reason="migration anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="MEDIUM",
                persistent_state_mutation=True,
                rollback_mechanism="MIGRATION",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="down migrate")
        self.assertEqual(plan["strategy"], "FORWARD_REVERT_PLUS_DOWN_MIGRATION")

    def test_27_compensation_revert_plan_requires_user_approval(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="PRE_MATERIAL_CHANGE_POLICY",
                reason="external anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="MEDIUM",
                rollback_mechanism="COMPENSATION",
                rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            ),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="compensate")
        self.assertEqual(plan["strategy"], "COMPENSATING_ACTION_PLUS_FORWARD_REVERT")
        self.assertTrue(plan["user_approval_required"])

    def test_28_nonpassing_assessment_cannot_mint_revert_plan(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="GPT_LARGE_CHANGE_JUDGMENT",
                reason="anchor",
            )
        assessment = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        with self.assertRaisesRegex(rc.ReversibleChangeError, "ASSESSMENT_NOT_PASS"):
            rc.build_governed_revert_plan(checkpoint, assessment, reason="should fail")

    def test_29_checkpoint_binding_mismatch_is_rejected(self):
        checkpoint = make_checkpoint("GPT_LARGE_CHANGE_JUDGMENT")
        other = dict(checkpoint)
        other["reason"] = "other"
        body = dict(other)
        body.pop("checkpoint_id")
        body.pop("checkpoint_digest")
        other_digest = rc._digest(body)
        other["checkpoint_id"] = f"KGC-{other_digest[:16]}"
        other["checkpoint_digest"] = other_digest
        assessment = rc.assess_change_intent(
            base_intent(
                blast_radius="LARGE",
                rollback_checkpoint_ref=other["checkpoint_digest"],
            ),
            other,
        )
        with self.assertRaisesRegex(rc.ReversibleChangeError, "CHECKPOINT_BINDING_MISMATCH"):
            rc.build_governed_revert_plan(checkpoint, assessment, reason="wrong anchor")

    def test_30_revert_plan_digest_tamper_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="MANUAL_OPERATION",
                reason="anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(rollback_checkpoint_ref=checkpoint["checkpoint_digest"]),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="rollback")
        plan["strategy"] = "FORCE_RESET"
        with self.assertRaisesRegex(rc.ReversibleChangeError, "DIGEST_MISMATCH"):
            rc.validate_governed_revert_plan(plan)

    def test_31_revert_plan_authority_must_stay_false(self):
        with TempGitRepo() as repo:
            checkpoint = rc.capture_known_good_checkpoint(
                repo.root,
                repository="repo",
                expected_head=repo.head,
                trigger_source="MANUAL_OPERATION",
                reason="anchor",
            )
        assessment = rc.assess_change_intent(
            base_intent(rollback_checkpoint_ref=checkpoint["checkpoint_digest"]),
            checkpoint,
        )
        plan = rc.build_governed_revert_plan(checkpoint, assessment, reason="rollback")
        self.assertTrue(all(v is False for v in plan["authority"].values()))
        plan["authority"]["grants_merge"] = True
        body = dict(plan)
        body.pop("plan_digest")
        plan["plan_digest"] = rc._digest(body)
        with self.assertRaisesRegex(rc.ReversibleChangeError, "AUTHORITY_BOUNDARY_MISMATCH"):
            rc.validate_governed_revert_plan(plan)

    def test_32_cli_assess_outputs_machine_readable_json(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "intent.json"
            path.write_text(json.dumps(base_intent()), encoding="utf-8")
            output = subprocess.check_output(
                ["python", str(Path(rc.__file__)), "assess", "--input", str(path)],
                text=True,
            )
        parsed = json.loads(output)
        self.assertEqual(parsed["schema_version"], rc.ASSESSMENT_SCHEMA)
        self.assertEqual(parsed["assessment_result"], "PASS")


if __name__ == "__main__":
    unittest.main()
