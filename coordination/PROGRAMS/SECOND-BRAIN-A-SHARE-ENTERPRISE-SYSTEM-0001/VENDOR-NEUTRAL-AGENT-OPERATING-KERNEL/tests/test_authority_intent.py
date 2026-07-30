from __future__ import annotations

from dataclasses import replace
import unittest

from _support import meta
from vendor_neutral_agent_kernel.authority import (
    AuthorityDirective,
    AuthorityKind,
    resolve_authority,
)
from vendor_neutral_agent_kernel.contracts import SideEffectClass
from vendor_neutral_agent_kernel.intent import compile_intent


class AuthorityIntentTests(unittest.TestCase):
    def test_user_explicit_decision_overrides_lower_route_action(self):
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
        self.assertIn("create_candidate_branch", result.allowed_actions)
        self.assertNotIn("create_candidate_branch", result.forbidden_actions)
        self.assertEqual(result.effective_task_id, "task-kernel")
        self.assertTrue(any(item.startswith("OVERRIDDEN_ACTION") for item in result.conflicts))

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
        self.assertIn("SAME_RANK_ACTION_CONFLICT:publish", result.conflicts)

    def test_highest_nonempty_path_scope_wins(self):
        directives = (
            AuthorityDirective(
                AuthorityKind.USER_EXPLICIT_DECISION,
                "user:scope",
                task_id="task",
                allowed_paths=("coordination/BLUEPRINTS/",),
            ),
            AuthorityDirective(
                AuthorityKind.ACTIVE_ROUTE,
                "route:scope",
                task_id="old-task",
                allowed_paths=("other/",),
            ),
        )
        result = resolve_authority(meta("authority"), directives, agent_id="CODEX")
        self.assertEqual(result.allowed_paths, ("coordination/BLUEPRINTS/",))
        self.assertTrue(any(item.startswith("OVERRIDDEN_PATH_SCOPE") for item in result.conflicts))

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

    def test_authority_requires_task_identity(self):
        with self.assertRaisesRegex(ValueError, "EFFECTIVE_TASK_ID_UNRESOLVED"):
            resolve_authority(
                meta("authority"),
                (AuthorityDirective(AuthorityKind.SKILL_CONTRACT, "skill"),),
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
