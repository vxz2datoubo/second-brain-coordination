from __future__ import annotations

import copy
import json
import subprocess
import sys
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
        subprocess.check_call(["git", "config", "user.name", "R159 Test"], cwd=self.root)
        subprocess.check_call(
            ["git", "config", "user.email", "r159@example.invalid"], cwd=self.root
        )
        (self.root / "tracked.txt").write_text("known-good\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.root)
        subprocess.check_call(
            ["git", "commit", "-m", "known good"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
        )
        self.head = self.git("rev-parse", "HEAD")
        return self

    def git(self, *args):
        return subprocess.check_output(
            ["git", *args], cwd=self.root, text=True
        ).strip()

    def refs(self):
        return self.git("for-each-ref", "--format=%(refname):%(objectname)")

    def commit_more(self):
        (self.root / "tracked.txt").write_text("later\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "."], cwd=self.root)
        subprocess.check_call(
            ["git", "commit", "-m", "later"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
        )
        return self.git("rev-parse", "HEAD")

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

    def assessment_with_checkpoint(self, repo, **overrides):
        checkpoint = self.checkpoint(repo)
        intent = base_intent(
            rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
            **overrides,
        )
        assessment = rc.assess_change_intent(
            intent,
            checkpoint,
            repo_root=repo.root,
        )
        return checkpoint, assessment

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
        result = rc.assess_change_intent(base_intent(gpt_judged_large_change=True))
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")

    def test_06_digest_string_alone_does_not_satisfy_marker(self):
        result = rc.assess_change_intent(
            base_intent(blast_radius="LARGE", rollback_checkpoint_ref="a" * 64)
        )
        self.assertEqual(result["assessment_result"], "REQUIRES_ROLLBACK_MARKER")
        self.assertFalse(result["rollback_checkpoint_binding_verified"])

    def test_07_capture_mints_sealed_checkpoint_without_ref_mutation(self):
        with TempGitRepo() as repo:
            before = repo.refs()
            checkpoint = self.checkpoint(repo, "GPT_LARGE_CHANGE_JUDGMENT")
            after = repo.refs()
            self.assertEqual(before, after)
            self.assertEqual(
                checkpoint["trust_semantics"],
                "INVOCATION_LOCAL_SEAL_REQUIRED_FOR_AUTHORITY_BEARING_USE",
            )
            rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

    def test_08_serialized_checkpoint_copy_is_evidence_only(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            serialized = json.loads(json.dumps(rc.checkpoint_evidence(checkpoint)))
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "TRUSTED_CAPTURE_REQUIRED"
            ):
                rc.validate_known_good_checkpoint(serialized, repo_root=repo.root)

    def test_09_plain_dict_full_object_forgery_cannot_satisfy_large_gate(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            forged = rc.checkpoint_evidence(checkpoint)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "TRUSTED_CAPTURE_REQUIRED"
            ):
                rc.assess_change_intent(
                    base_intent(
                        blast_radius="LARGE",
                        rollback_checkpoint_ref=forged["checkpoint_digest"],
                    ),
                    forged,
                    repo_root=repo.root,
                )

    def test_10_deepcopy_loses_trust(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            copied = copy.deepcopy(checkpoint)
            self.assertIs(type(copied), dict)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "TRUSTED_CAPTURE_REQUIRED"
            ):
                rc.validate_known_good_checkpoint(copied, repo_root=repo.root)

    def test_11_real_checkpoint_satisfies_large_gate(self):
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

    def test_12_checkpoint_survives_head_advance_via_ancestry(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            repo.commit_more()
            rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

    def test_13_checkpoint_tree_binding_is_reverified_from_git(self):
        with TempGitRepo() as repo:
            checkpoint = self.checkpoint(repo)
            subprocess.check_call(
                ["git", "replace", checkpoint["canonical_commit"], repo.commit_more()],
                cwd=repo.root,
            )
            with self.assertRaises(rc.ReversibleChangeError):
                rc.validate_known_good_checkpoint(checkpoint, repo_root=repo.root)

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
                rc.ReversibleChangeError, "CHECKPOINT_REPO_ROOT_REQUIRED"
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
        self.assertEqual(result["reversibility_class"], "IRREVERSIBLE_OR_HIGH_RISK")
        self.assertEqual(
            result["assessment_result"], "BLOCKED_ROLLBACK_PLAN_INCOMPLETE"
        )

    def test_20_stateful_snapshot_classifies_correctly(self):
        with TempGitRepo() as repo:
            _, result = self.assessment_with_checkpoint(
                repo,
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="SNAPSHOT",
            )
            self.assertEqual(result["reversibility_class"], "REVERSIBLE_WITH_SNAPSHOT")

    def test_21_stateful_migration_classifies_correctly(self):
        with TempGitRepo() as repo:
            _, result = self.assessment_with_checkpoint(
                repo,
                surface_kind="STATEFUL_DATA",
                blast_radius="MEDIUM",
                persistent_state_mutation=True,
                rollback_mechanism="MIGRATION",
            )
            self.assertEqual(result["reversibility_class"], "REVERSIBLE_WITH_MIGRATION")

    def test_22_policy_version_switch_classifies_correctly(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="POLICY_BEHAVIOR",
                rollback_mechanism="FEATURE_FLAG_OR_VERSION_SWITCH",
            )
        )
        self.assertEqual(
            result["reversibility_class"], "REVERSIBLE_BY_VERSION_SWITCH"
        )

    def test_23_external_compensation_is_not_git_only(self):
        with TempGitRepo() as repo:
            _, result = self.assessment_with_checkpoint(
                repo,
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="MEDIUM",
                rollback_mechanism="COMPENSATION",
            )
            self.assertEqual(result["reversibility_class"], "COMPENSATABLE_ONLY")

    def test_24_irreversible_external_side_effect_requires_user_approval(self):
        result = rc.assess_change_intent(
            base_intent(
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="CRITICAL",
                external_irreversible_side_effect=True,
                rollback_mechanism="NONE",
            )
        )
        self.assertEqual(result["assessment_result"], "USER_APPROVAL_REQUIRED")

    def test_25_plain_assessment_digest_tamper_is_rejected(self):
        result = rc.assess_change_intent(base_intent())
        result["assessment_result"] = "USER_APPROVAL_REQUIRED"
        with self.assertRaisesRegex(rc.ReversibleChangeError, "DIGEST_MISMATCH"):
            rc.validate_assessment(result)

    def test_26_recomputed_digest_stateful_to_git_only_pass_laundering_rejected(self):
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
        result["classification_reasons"] = ["CODE_CONFIG_RECOVERABLE_BY_GIT_HISTORY"]
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
        ):
            rc.validate_assessment(result)

    def test_27_recomputed_digest_large_marker_bypass_rejected(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        result["assessment_result"] = "PASS"
        result["rollback_marker_required"] = False
        result["rollback_marker_reasons"] = []
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
        ):
            rc.validate_assessment(result)

    def test_28_recomputed_checkpoint_verified_bit_without_checkpoint_rejected(self):
        result = rc.assess_change_intent(base_intent(blast_radius="LARGE"))
        result["assessment_result"] = "PASS"
        result["rollback_checkpoint_binding_verified"] = True
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
        ):
            rc.validate_assessment(result)

    def test_29_valid_assessment_rederives_with_real_checkpoint(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            rc.validate_assessment(
                assessment,
                checkpoint_value=checkpoint,
                repo_root=repo.root,
            )

    def test_30_recomputed_assessment_authority_escalation_rejected(self):
        result = rc.assess_change_intent(base_intent())
        result["authority"]["grants_merge"] = True
        redigest_assessment(result)
        with self.assertRaisesRegex(
            rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
        ):
            rc.validate_assessment(result)

    def test_31_git_only_revert_plan_is_history_preserving(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            plan = rc.build_governed_revert_plan(
                checkpoint,
                assessment,
                reason="effect regressed",
                repo_root=repo.root,
            )
            self.assertEqual(
                plan["strategy"], "FORWARD_REVERT_PR_OR_CORRECTIVE_COMMIT"
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

    def test_32_snapshot_revert_plan_requires_snapshot_restore(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo,
                surface_kind="STATEFUL_DATA",
                blast_radius="LARGE",
                persistent_state_mutation=True,
                rollback_mechanism="SNAPSHOT",
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="restore state", repo_root=repo.root
            )
            self.assertEqual(
                plan["strategy"], "FORWARD_REVERT_PLUS_SNAPSHOT_RESTORE"
            )

    def test_33_migration_revert_plan_requires_down_migration(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo,
                surface_kind="STATEFUL_DATA",
                blast_radius="MEDIUM",
                persistent_state_mutation=True,
                rollback_mechanism="MIGRATION",
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="down migrate", repo_root=repo.root
            )
            self.assertEqual(
                plan["strategy"], "FORWARD_REVERT_PLUS_DOWN_MIGRATION"
            )

    def test_34_compensation_revert_plan_requires_user_approval(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo,
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="MEDIUM",
                rollback_mechanism="COMPENSATION",
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="compensate", repo_root=repo.root
            )
            self.assertTrue(plan["user_approval_required"])

    def test_35_recomputed_strategy_laundering_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="r", repo_root=repo.root
            )
            plan["strategy"] = "VERSION_SWITCH_OR_FEATURE_FLAG"
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_36_recomputed_independent_review_suppression_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="r", repo_root=repo.root
            )
            plan["independent_review_required"] = False
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_37_recomputed_user_approval_suppression_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo,
                surface_kind="EXTERNAL_SIDE_EFFECT",
                blast_radius="MEDIUM",
                rollback_mechanism="COMPENSATION",
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="r", repo_root=repo.root
            )
            plan["user_approval_required"] = False
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "SEMANTIC_REDERIVATION_MISMATCH"
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_38_recomputed_history_rewrite_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="r", repo_root=repo.root
            )
            plan["destructive_history_rewrite"] = True
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "DESTRUCTIVE_HISTORY_REWRITE_FORBIDDEN"
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_39_recomputed_plan_authority_escalation_is_rejected(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            plan = rc.build_governed_revert_plan(
                checkpoint, assessment, reason="r", repo_root=repo.root
            )
            plan["authority"]["grants_merge"] = True
            redigest_plan(plan)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "AUTHORITY_BOUNDARY_MISMATCH"
            ):
                rc.validate_governed_revert_plan(
                    plan,
                    checkpoint_value=checkpoint,
                    assessment_value=assessment,
                    repo_root=repo.root,
                )

    def test_40_plain_checkpoint_cannot_build_revert_plan(self):
        with TempGitRepo() as repo:
            checkpoint, assessment = self.assessment_with_checkpoint(
                repo, blast_radius="LARGE"
            )
            evidence = rc.checkpoint_evidence(checkpoint)
            with self.assertRaisesRegex(
                rc.ReversibleChangeError, "TRUSTED_CAPTURE_REQUIRED"
            ):
                rc.build_governed_revert_plan(
                    evidence, assessment, reason="r", repo_root=repo.root
                )

    def test_41_unknown_intent_field_fails_closed(self):
        intent = base_intent()
        intent["unexpected"] = True
        with self.assertRaisesRegex(rc.ReversibleChangeError, "FIELD_UNRECOGNIZED"):
            rc.assess_change_intent(intent)

    def test_42_cli_assess_outputs_machine_readable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "intent.json"
            path.write_text(json.dumps(base_intent()), encoding="utf-8")
            output = subprocess.check_output(
                [sys.executable, str(Path(rc.__file__)), "assess", "--input", str(path)],
                text=True,
            )
            result = json.loads(output)
            self.assertEqual(result["assessment_result"], "PASS")

    def test_43_cli_checkpoint_outputs_evidence_without_ref_mutation(self):
        with TempGitRepo() as repo:
            before = repo.refs()
            output = subprocess.check_output(
                [
                    sys.executable,
                    str(Path(rc.__file__)),
                    "checkpoint",
                    "--repo-root",
                    str(repo.root),
                    "--repository",
                    "repo",
                    "--expected-head",
                    repo.head,
                    "--trigger-source",
                    "MANUAL_OPERATION",
                    "--reason",
                    "anchor",
                ],
                text=True,
            )
            after = repo.refs()
            result = json.loads(output)
            self.assertEqual(before, after)
            self.assertEqual(result["canonical_commit"], repo.head)

    def test_44_cli_serialized_checkpoint_cannot_be_used_as_trust(self):
        with TempGitRepo() as repo, tempfile.TemporaryDirectory() as tmp:
            checkpoint = self.checkpoint(repo)
            cpath = Path(tmp) / "checkpoint.json"
            ipath = Path(tmp) / "intent.json"
            cpath.write_text(
                json.dumps(rc.checkpoint_evidence(checkpoint)), encoding="utf-8"
            )
            ipath.write_text(
                json.dumps(
                    base_intent(
                        blast_radius="LARGE",
                        rollback_checkpoint_ref=checkpoint["checkpoint_digest"],
                    )
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(Path(rc.__file__)),
                    "assess",
                    "--input",
                    str(ipath),
                    "--checkpoint",
                    str(cpath),
                    "--repo-root",
                    str(repo.root),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("SERIALIZED_CHECKPOINT_EVIDENCE_ONLY", proc.stderr)

    def test_45_no_tag_or_ref_mutation_api_exists_in_module_source(self):
        source = Path(rc.__file__).read_text(encoding="utf-8")
        self.assertNotIn("update-ref", source)
        self.assertNotIn("refs/tags/", source)
        self.assertNotIn("git tag", source)

    def test_46_no_public_or_private_seal_function_can_self_mint_checkpoint(self):
        self.assertFalse(hasattr(rc, "_SEAL_CAPTURED_CHECKPOINT"))
        self.assertFalse(hasattr(rc, "seal_checkpoint"))
        self.assertFalse(hasattr(rc, "mint_trusted_checkpoint"))

    def test_47_all_authority_booleans_remain_false(self):
        self.assertTrue(rc.AUTHORITY)
        self.assertFalse(any(rc.AUTHORITY.values()))


if __name__ == "__main__":
    unittest.main()
