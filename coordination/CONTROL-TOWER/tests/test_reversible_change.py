from __future__ import annotations

import copy
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


def redigest_assessment(value):
    body = dict(value)
    body.pop("assessment_digest", None)
    value["assessment_digest"] = rc._digest(body)
    return value


def redigest_plan(value):
    body = dict(value)
    body.pop("plan_digest", None)
    value["plan_digest"] = rc._digest(body)
    return value


class TempGitRepo:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        subprocess.check_call(
            ["git", "init", "-b", "main"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
        )
        subprocess.check_call(
            ["git", "config", "user.name", "R159 Test"],
            cwd=self.root,
        )
        subprocess.check_call(
            ["git", "config", "user.email", "r159@example.invalid"],
            cwd=self.root,
        )
        (self.root / "tracked.txt").write_text("known-good\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.root)
        subprocess.check_call(
            ["git", "commit", "-m", "known good"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
        )
        self.head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
        ).strip()
        return self

    def commit_more(self):
        (self.root / "tracked.txt").write_text("later\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.root)
        subprocess.check_call(
            ["git", "commit", "-m", "later"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
        )
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=self.root,
            text=True,
        ).strip()

    def __exit__(self, exc_type, exc, tb):
        self.tmp.cleanup()


class ReversibleChangeTests(unittest.TestCase):
    def checkpoint(self, repo, trigger="MANUAL_OPERATION", reason="anchor"):
        return rc.capture_known_good_checkpoint(
            repo.root,
            repository="repo",
            expected_head=repo.head,
            trigger_source=trigger,
            reason=reason,
        )

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

    def test_04_large_change_requires_checkpoint(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertIn("BLAST_RADIUS_LARGE", result["rollback_marker_reasons"])

    def test_05_gpt_large_change_judgment_requires_checkpoint(self):
        result = rc.assess_change_intent(
            base_intent(gpt_judged_large_change=True)
        )
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")

    def test_06_digest_string_alone_does_not_satisfy_marker(self):
        result = rc.assess_change_intent(
            base_intent(
                blast_radius="LARGE",
                rollback_checkpoint_ref="a" * 64,
            )
        )
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertFalse(result["rollback_checkpoint_binding_verified"])

    def test_07_checkpoint_capture_creates_real_git_marker_ref(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo, "GPT_LARGE_CHANGE_JUDGMENT")
            marker_ref = rc._marker_ref(checkpoint["checkpoint_digest"])
            marker_commit = subprocess.check_output(
                ["git", "rev-parse", marker_ref],
                cwd=repo.root,
                text=True,
            ).strip()
            self.assertEqual(marker_commit, repo.head)
            rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

    def test_08_full_checkpoint_object_forgery_without_git_marker_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            subprocess.check_call(
                ["git", "update-ref", "-d", rc._marker_ref(checkpoint["checkpoint_digest"])],
                cwd=repo.root,
            )
            forged = copy.deepcopy(checkpoint)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "TRUSTED_GIT_MARKER_REQUIRED",
            ):
                rc.validate_known_good_checkpoint(forged, repo_root=repo.root)

    def test_09_full_checkpoint_object_forgery_cannot_satisfy_large_gate(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo, "GPT_LARGE_CHANGE_JUDGMENT")
            subprocess.check_call(
                ["git", "update-ref", "-d", rc._marker_ref(checkpoint["checkpoint_digest"])],
                cwd=repo.root,
            )
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "TRUSTED_GIT_MARKER_REQUIRED",
            ):
                rc.assess_change_intent(
                    base_intent(
                        blast_radius="LARGE",
                        rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                    ),
                    checkpoint,
                    repo_root=repo.root,
                )

    def test_10_real_checkpoint_satisfies_large_gate(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo, "GPT_LARGE_CHANGE_JUDGMENT")
            result = rc.assess_change_intent(
                base_intent(
                    blast_radius="LARGE",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            self.assertEqual(result["assessment_result"], "PASS")
            self.assertTrue(result["rollback_checkpoint_binding_verified"])

    def test_11_checkpoint_marker_survives_head_advance(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            repo.commit_more()
            rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

    def test_12_moved_checkpoint_marker_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            later = repo.commit_more()
            subprocess.check_call(
                [
                    "git",
                    "update-ref",
                    rc._marker_ref(checkpoint["checkpoint_digest"]),
                    later,
                ],
                cwd=repo.root,
            )
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "TRUSTED_GIT_MARKER_REQUIRED",
            ):
                rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

    def test_13_checkpoint_tree_binding_is_reverified_from_git(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            forged = copy.deepcopy(checkpoint)
            forged["tree_sha"] = "0" * 40
            body = dict(forged)
            body.pop("checkpoint_id")
            body.pop("checkpoint_digest")
            digest = rc._digest(body)
            forged["checkpoint_id"] = f"KGC-{digest[:16]}"
            forged["checkpoint_digest"] = digest
            subprocess.check_call(
                ["git", "update-ref", rc._marker_ref(digest), repo.head],
                cwd=repo.root,
            )
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "TREE_BINDING_MISMATCH",
            ):
                rc.validate_known_good_checkpoint(forged, repo_root=repo.root)

    def test_14_dirty_worktree_cannot_mint_checkpoint(self):
        with TempGitRepo() as repo:
            (repo.root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(rc.ReversibleChangeError, "WORKTREE_DIRTY"):
                self.checkpoint(repo)

    def test_15_untracked_file_counts_as_dirty(self):
        with TempGitRepo() as repo:
            (repo.root / "new.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(rc.ReversibleChangeError, "WORKTREE_DIRTY"):
                self.checkpoint(repo)

    def test_16_head_drift_cannot_mint_checkpoint(self):
        with TempGitRepo() as repo:
            with self.assertRaisesRegex(rc.ReversibleChangeError, "HEAD_DRIFT"):
                rc.capture_known_good_checkpoint(
                    repo.root,
                    repository="repo",
                    expected_head="0" * 40,
                    trigger_source="MANUAL_OPERATION",
                    reason="wrong",
                )

    def test_17_wrong_branch_cannot_mint_canonical_checkpoint(self):
        with TempGitRepo() as repo:
            subprocess.check_call(
                ["git", "checkout", "-b", "feature"],
                cwd=repo.root,
                stdout=subprocess.DEVNULL,
            )
            with self.assertRaisesRegex(rc.ReversibleChangeError, "BRANCH_MISMATCH"):
                self.checkpoint(repo)

    def test_18_checkpoint_repo_root_is_required_for_trusted_use(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "CHECKPOINT_REPO_ROOT_REQUIRED",
            ):
                rc.assess_change_intent(
                    base_intent(
                        rollback_checkpoint_ref=checkpoint["checkpoint_digest"]
                    ),
                    checkpoint,
                )

    def test_19_stateful_git_only_recovery_is_blocked(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="GIT_REVERT",
            )
        )
        self.assertEqual(
            result["reversibility_class"],
            "IRREVERSIBLE_OR_HIGH_RISK",
        )
        self.assertEqual(
            result["assessment_result"],
            "BLOCKED_ROLLBACK_PLAN_INCOMPLETE",
        )

    def test_20_stateful_snapshot_classifies_correctly(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            result = rc.assess_change_intent(
                base_intent(
                    surface_kind="STATEFUL_DATA",
                    blast_radius="LARGE",
                    persistent_state_mutation=True,
                    rollback_mechanism="SNAPSHOT",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            self.assertEqual(
                result["reversibility_class"],
                "REVERSIBLE_WITH_SNAPSHOT",
            )

    def test_21_stateful_migration_classifies_correctly(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            result = rc.assess_change_intent(
                base_intent(
                    surface_kind="STATEFUL_DATA",
                    blast_radius="MEDIUM",
                    persistent_state_mutation=True,
                    rollback_mechanism="MIGRATION",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            self.assertEqual(
                result["reversibility_class"],
                "REVERSIBLE_WITH_MIGRATION",
            )

    def test_22_external_compensation_is_not_git_only(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            result = rc.assess_change_intent(
                base_intent(
                    surface_kind="EXTERNAL_SIDE_EFFECT",
                    blast_radius="MEDIUM",
                    rollback_mechanism="COMPENSATION",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            self.assertEqual(result["reversibility_class"], "COMPENSATABLE_ONLY")

    def test_23_irreversible_external_side_effect_requires_user_approval(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="CRITICAL",
                external_irreversible_side_effect=True,
                rollback_mechanism="NONE",
            )
        )
        self.assertEqual(result["assessment_result"], "USER_APPROVAL_REQUIRED")

    def test_24_plain_assessment_digest_tamper_is_rejected(self):
        result = rc.assess_change_intent(base_intent())
        result["assessment_result"] = "USER_APPROVAL_REQUIRED"
        with self.assertRaisesRegex(rc.ReversibleChangeError, "DIGEST_MISMATCH"):
            rc.validate_assessment(result)

    def test_25_recomputed_digest_stateful_to_git_only_pass_laundering_rejected(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="GIT_REVERT",
            )
        )
        result["reversibility_class"] = "REVERSIBLE_GIT_ONLY"
        result["assessment_result"] = "PASS"
        result["rollback_marker_required"] = False
        result["rollback_marker_reasons"] = []
        result["classification_reasons"] = [
            "CODE_CONFIG_RECOVERABLE_BY_GIT_HISTORY"
        ]
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError,
            "SEMANTIC_REDERIVATION_MISMATCH",
        ):
            rc.validate_assessment(result)

    def test_26_recomputed_digest_large_marker_bypass_rejected(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        result["assessment_result"] = "PASS"
        result["rollback_marker_required"] = False
        result["rollback_marker_reasons"] = []
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError,
            "SEMANTIC_REDERIVATION_MISMATCH",
        ):
            rc.validate_assessment(result)

    def test_27_recomputed_checkpoint_verified_bit_without_checkpoint_rejected(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        result["assessment_result"] = "PASS"
        result["rollback_checkpoint_binding_verified"] = True
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError,
            "SEMANTIC_REDERIVATION_MISMATCH",
        ):
            rc.validate_assessment(result)

    def test_28_valid_assessment_rederives_with_real_checkpoint(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    blast_radius="LARGE",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            rc.validate_assessment(
                assessment,
                checkpoint_value=checkpoint,
                repo_root=repo.root,
            )

    def test_29_recomputed_assessment_authority_escalation_rejected(self):
        result = rc.assess_change_intent(base_intent())
        result["authority"]["grants_merge"] = True
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError,
            "SEMANTIC_REDERIVATION_MISMATCH",
        ):
            rc.validate_assessment(result)

    def test_30_git_only_revert_plan_is_history_preserving(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    blast_radius="LARGE",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="effect regressed",
                repo_root=repo.root,
            )
            self.assertEqual(
                plan["strategy"],
                "FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT",
            )
            self.assertTrue(plan["preserve_history"])
            self.assertFalse(plan["destructive_history_rewrite"])
            self.assertTrue(plan["exact_head_reverification_required"])
            self.assertTrue(plan["independent_review_required"])
            rc.validate_governed_revert_plan(
                plan,
                checkpoint_value=checkpoint,
                assessment_value=assessment,
                repo_root=repo.root,
            )

    def test_31_snapshot_revert_plan_requires_snapshot_restore(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    surface_kind="STATEFUL_DATA",
                    blast_radius="LARGE",
                    persistent_state_mutation=True,
                    rollback_mechanism="SNAPSHOT",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="restore state",
                repo_root=repo.root,
            )
            self.assertEqual(
                plan["strategy"],
                "FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE",
            )

    def test_32_migration_revert_plan_requires_down_migration(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    surface_kind="STATEFUL_DATA",
                    blast_radius="MEDIUM",
                    persistent_state_mutation=True,
                    rollback_mechanism="MIGRATION",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="down migrate",
                repo_root=repo.root,
            )
            self.assertEqual(
                plan["strategy"],
                "FORWARD_REVERT_PLUS_DOWN_MIGRATION",
            )

    def test_33_compensation_revert_plan_requires_user_approval(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    surface_kind="EXTERNAL_SIDE_EFFECT",
                    blast_radius="MEDIUM",
                    rollback_mechanism="COMPENSATION",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="compensate",
                repo_root=repo.root,
            )
            self.assertTrue(plan["user_approval_required"])

    def test_34_recomputed_strategy_laundering_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    blast_radius="LARGE",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="rollback",
                repo_root=repo.root,
            )
            plan["strategy"] = "VERSION_SWITCH_OR_FEATURE_FLAG"
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "SEMANTIC_REDERIVATION_MISMATCH",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_35_recomputed_independent_review_suppression_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    blast_radius="LARGE",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="rollback",
                repo_root=repo.root,
            )
            plan["independent_review_required"] = False
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "SEMANTIC_REDERIVATION_MISMATCH",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_36_recomputed_user_approval_suppression_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    surface_kind="EXTERNAL_SIDE_EFFECT",
                    blast_radius="MEDIUM",
                    rollback_mechanism="COMPENSATION",
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="compensate",
                repo_root=repo.root,
            )
            plan["user_approval_required"] = False
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "SEMANTIC_REDERIVATION_MISMATCH",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_37_recomputed_history_rewrite_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"]
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="rollback",
                repo_root=repo.root,
            )
            plan["preserve_history"] = False
            plan["destructive_history_rewrite"] = True
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "HISTORY_PRESERVATION_REQUIRED|DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_38_recomputed_plan_authority_escalation_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"]
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="rollback",
                repo_root=repo.root,
            )
            plan["authority"]["grants_merge"] = True
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "AUTHORITY_BOUNDARY_MISMATCH",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_39_plan_rejects_checkpoint_after_marker_removed(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            assessment = rc.assess_change_intent(
                base_intent(
                    rollback_checkpoint_ref=checkpoint["checkpoint_digest"]
                ),
                checkpoint,
                repo_root=repo.root,
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="rollback",
                repo_root=repo.root,
            )
            subprocess.check_call(
                ["git", "update-ref", "-d", rc._marker_ref(checkpoint["checkpoint_digest"])],
                cwd=repo.root,
            )
            with self.assertRaisesRegex(
                rc.ReversibleChangeError,
                "TRUSTED_GIT_MARKER_REQUIRED",
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_40_unknown_intent_field_fails_closed(self):
        value = base_intent()
        value["caller_truth"] = True
        with self.assertRaisesRegex(
            rc.ReversibleChangeError,
            "FIELD_UNRECOGNIZED",
        ):
            rc.assess_change_intent(value)

    def test_41_cli_assess_outputs_machine_readable_json(self):
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
