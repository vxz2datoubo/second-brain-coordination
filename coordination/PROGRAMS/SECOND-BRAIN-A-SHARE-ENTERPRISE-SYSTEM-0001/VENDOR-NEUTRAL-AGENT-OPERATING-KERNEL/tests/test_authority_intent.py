from __future__ import annotations

from dataclasses import replace
import unittest

from _support import meta
from vendor_neutral_agent_kernel.authority import (
    AuthorityDirective,
    AuthorityKind,
    is_action_executable,
    resolve_authority,
)
from vendor_neutral_agent_kernel.contracts import SideEffectClass
from vendor_neutral_agent_kernel.intent import compile_intent


class AuthorityIntentTests(unittest.TestCase):
    def test_user_cannot_override_active_route_hard_deny(self):
        directives = (
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:1",
                task_id="task-route",
                forbidden_actions=("create_candidate_branch",),
            ),
            AuthorityDirective(
                AuthorityKind.USER_EXPLICIT_DECISION,
                "user:explicit",
                task_id="task-kernel",
                allowed_actions=("create_candidate_branch",),
            ),
        )
        result = resolve_authority(meta("authority"), directives, agent_id="CODEX")
        self.assertNotIn("create_candidate_branch", result.allowed_actions)
        self.assertIn("create_candidate_branch", result.forbidden_actions)
        self.assertEqual(result.effective_task_id, "task-route")
        self.assertFalse(is_action_executable(result, "create_candidate_branch"))

    def test_route_overrides_skill_when_user_has_no_override(self):
        directives = (
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:1",
                task_id="task-route",
                forbidden_actions=("write_main",),
            ),
            AuthorityDirective(
                AuthorityKind.SKILL_CONTRACT,
                "skill:1",
                allowed_actions=("write_main",),
            ),
        )
        result = resolve_authority(meta("authority"), directives, agent_id="CODEX")
        self.assertIn("write_main", result.forbidden_actions)

    def test_same_rank_conflict_fails_closed(self):
        directives = (
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:a",
                task_id="task",
                allowed_actions=("publish",),
            ),
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:b",
                task_id="task",
                forbidden_actions=("publish",),
            ),
        )
        result = resolve_authority(meta("authority"), directives, agent_id="CODEX")
        self.assertIn("publish", result.forbidden_actions)
        self.assertEqual(result.resolution_status, "BLOCKED_AUTHORITY_CONFLICT")
        self.assertIn(
            "BLOCKED_AUTHORITY_CONFLICT:SAME_RANK_ACTION:ACTIVE_ROUTE:publish",
            result.conflicts,
        )

    def test_path_scope_is_intersection_not_highest_nonempty_scope(self):
        directives = (
            AuthorityDirective(
                AuthorityKind.USER_EXPLICIT_DECISION,
                "user:scope",
                allowed_paths=("coordination/BLUEPRINTS/",),
            ),
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:scope",
                task_id="task",
                allowed_paths=("coordination/",),
            ),
        )
        result = resolve_authority(meta("authority"), directives, agent_id="CODEX")
        self.assertEqual(result.allowed_paths, ("coordination/BLUEPRINTS/",))

    def test_nonoverlapping_authorized_path_scopes_fail_closed(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(
                    AuthorityKind.PROJECT_CHARTER,
                    "charter:scope",
                    allowed_paths=("coordination/",),
                ),
                AuthorityDirective(
                    AuthorityKind.ACTIVE_ROUTE,
                    "route:scope",
                    task_id="task",
                    allowed_paths=("src/",),
                ),
            ),
            agent_id="CODEX",
        )
        self.assertEqual(result.resolution_status, "BLOCKED_AUTHORITY_CONFLICT")
        self.assertEqual(result.allowed_paths, ())
        self.assertIn(
            "BLOCKED_AUTHORITY_CONFLICT:PATH_SCOPE_INTERSECTION_EMPTY",
            result.conflicts,
        )

    def test_directive_input_order_does_not_change_resolution(self):
        first = AuthorityDirective(
            AuthorityKind.ACTIVE_ROUTE,
            "route:a",
            task_id="task",
            allowed_actions=("read",),
        )
        second = AuthorityDirective(
            AuthorityKind.SKILL_CONTRACT,
            "skill:b",
            allowed_actions=("inspect",),
        )
        left = resolve_authority(meta("left"), (first, second), agent_id="CODEX")
        right = resolve_authority(meta("right"), (second, first), agent_id="CODEX")
        self.assertEqual(left.authority_hash, right.authority_hash)
        self.assertEqual(left.allowed_actions, right.allowed_actions)

    def test_authority_requires_active_route_task_identity(self):
        with self.assertRaisesRegex(ValueError, "ACTIVE_ROUTE_TASK_REQUIRED"):
            resolve_authority(
                meta("authority"),
                (AuthorityDirective(AuthorityKind.USER_EXPLICIT_DECISION, "user"),),
                agent_id="CODEX",
            )

    def test_directive_rejects_internal_action_contradiction(self):
        with self.assertRaisesRegex(ValueError, "DIRECTIVE_ACTION_CONTRADICTION"):
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route",
                task_id="task",
                allowed_actions=("write",),
                forbidden_actions=("write",),
            )

    def test_tool_and_model_can_not_grant_action_authority(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(AuthorityKind.ACTIVE_ROUTE, "route", task_id="task"),
                AuthorityDirective(
                    AuthorityKind.TOOL_CAPABILITY,
                    "tool",
                    allowed_actions=("activate_runtime",),
                ),
                AuthorityDirective(
                    AuthorityKind.MODEL_PROFILE,
                    "model",
                    allowed_actions=("activate_runtime",),
                ),
            ),
            agent_id="CODEX",
        )
        self.assertNotIn("activate_runtime", result.allowed_actions)
        self.assertFalse(is_action_executable(result, "activate_runtime"))
        self.assertIn("NONAUTHORITY_ALLOW_IGNORED:activate_runtime", result.conflicts)

    def test_tool_feasibility_can_add_a_deny_without_granting_authority(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(
                    AuthorityKind.ACTIVE_ROUTE,
                    "route",
                    task_id="task",
                    allowed_actions=("read_private_artifact",),
                ),
                AuthorityDirective(
                    AuthorityKind.TOOL_CAPABILITY,
                    "tool",
                    forbidden_actions=("read_private_artifact",),
                ),
            ),
            agent_id="CODEX",
        )
        self.assertIn("read_private_artifact", result.forbidden_actions)
        self.assertFalse(is_action_executable(result, "read_private_artifact"))

    def test_approval_is_required_even_when_action_is_otherwise_allowed(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(
                    AuthorityKind.ACTIVE_ROUTE,
                    "route",
                    task_id="task",
                    allowed_actions=("publish_candidate",),
                    approval_requirements=("publish_candidate",),
                ),
            ),
            agent_id="CODEX",
        )
        self.assertIn("publish_candidate", result.allowed_actions)
        self.assertIn("publish_candidate", result.approval_requirements)
        self.assertFalse(is_action_executable(result, "publish_candidate"))

    def test_verified_route_approval_unblocks_required_action(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(
                    AuthorityKind.ACTIVE_ROUTE,
                    "route",
                    task_id="task",
                    allowed_actions=("publish_candidate",),
                    approval_requirements=("publish_candidate",),
                    verified_approval_actions=("publish_candidate",),
                ),
            ),
            agent_id="CODEX",
        )
        self.assertTrue(is_action_executable(result, "publish_candidate"))

    def test_only_active_route_may_supply_verified_approval(self):
        with self.assertRaisesRegex(ValueError, "VERIFIED_APPROVALS_REQUIRE_ACTIVE_ROUTE"):
            AuthorityDirective(
                AuthorityKind.USER_EXPLICIT_DECISION,
                "user",
                approval_requirements=("publish_candidate",),
                verified_approval_actions=("publish_candidate",),
            )

    def test_conflicting_active_route_tasks_do_not_choose_by_source_id(self):
        result = resolve_authority(
            meta("authority"),
            (
                AuthorityDirective(AuthorityKind.ACTIVE_ROUTE, "route:a", task_id="task-a"),
                AuthorityDirective(AuthorityKind.ACTIVE_ROUTE, "route:z", task_id="task-z"),
            ),
            agent_id="CODEX",
        )
        self.assertEqual(result.effective_task_id, "UNRESOLVED")
        self.assertEqual(result.resolution_status, "BLOCKED_AUTHORITY_CONFLICT")
        self.assertIn("BLOCKED_AUTHORITY_CONFLICT:ACTIVE_ROUTE_TASK", result.conflicts)

    def test_compile_intent_produces_sealed_contract(self):
        result = compile_intent(
            meta("intent"),
            objective="Build the candidate kernel.",
            explicit_requirements=("contracts", "tests"),
            success_criteria=("all tests pass",),
            non_goals=("production activation",),
            unknowns=("GPT acceptance",),
            side_effect_class=SideEffectClass.REVERSIBLE_LOCAL,
            evidence_budget=4,
            time_budget_seconds=3600,
            autonomy_boundary=("candidate branch only",),
        )
        self.assertEqual(len(result.meta.content_hash), 64)
        self.assertEqual(result.evidence_budget, 4)

    def test_intent_rejects_duplicate_requirements(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_REQUIREMENTS_DUPLICATE"):
            compile_intent(
                meta("intent"),
                objective="Test duplicate rejection.",
                explicit_requirements=("same", "same"),
                success_criteria=("reject",),
            )

    def test_intent_rejects_invalid_time_budget(self):
        with self.assertRaisesRegex(ValueError, "TIME_BUDGET_INVALID"):
            compile_intent(
                meta("intent"),
                objective="Test time.",
                explicit_requirements=("one",),
                success_criteria=("one",),
                time_budget_seconds=0,
            )


if __name__ == "__main__":
    unittest.main()
