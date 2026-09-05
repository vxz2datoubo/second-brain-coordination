from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class UnifiedExecutionFabricTests(unittest.TestCase):
    def test_exactly_four_project_ids_are_registered(self):
        registry = text("coordination/EXECUTION/PROJECT-REGISTRY.yaml")
        for project_id in (
            "SECOND_BRAIN",
            "TRADING_SYSTEM",
            "REALTIME_INTERACTIVE_FILM_GAME",
            "AI_DIRECTOR",
        ):
            self.assertEqual(registry.count(f'project_id: "{project_id}"'), 1)
        self.assertEqual(registry.count("  - project_id:"), 4)
        self.assertIn("simultaneous_projects_allowed: true", registry)
        self.assertIn("global_single_writer_by_collision_domain: true", registry)
        self.assertIn("no_project_may_define_second_global_router: true", registry)

    def test_project_adapter_schema_cannot_weaken_global_invariants(self):
        schema = text("coordination/GOVERNANCE/PROJECT-EXECUTION-ADAPTER-SCHEMA-v1.0.yaml")
        for token in (
            "single_writer_per_collision_domain",
            "exact_head_review_identity",
            "no_self_review",
            "no_self_merge",
            "credential_secret_exclusion",
            "active_task_authority_required",
        ):
            self.assertIn(token, schema)

        for path in (
            "coordination/EXECUTION/PROJECT-ADAPTERS/SECOND-BRAIN.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/REALTIME-INTERACTIVE-FILM.yaml",
            "coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml",
        ):
            adapter = text(path)
            self.assertIn('adapter_schema: "PROJECT-EXECUTION-ADAPTER-v1"', adapter)
            self.assertIn("hard_boundaries:", adapter)
            self.assertIn("acceptance:", adapter)

    def test_trading_read_market_data_never_mints_order_authority(self):
        trading = text("coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml")
        self.assertIn('default_authority: "READ_MARKET_DATA"', trading)
        self.assertIn("place_order_allowed: false", trading)
        self.assertIn("engineering_execution_does_not_imply_order_authority: true", trading)
        self.assertIn('order_authority: "SEPARATE_EXPLICIT_OWNER_GATE"', trading)
        self.assertIn('  - "NO_LOOKAHEAD"', trading)
        self.assertIn('  - "POINT_IN_TIME_ONLY"', trading)

    def test_cli_desktop_parallelism_is_single_writer_safe(self):
        carrier = text("coordination/GOVERNANCE/EXECUTION-CARRIER-AND-CONCURRENCY-CONTRACT-v1.0.yaml")
        self.assertIn('same_task_simultaneous_writers: "FORBIDDEN"', carrier)
        self.assertIn('multi_project_parallelism: "ALLOWED_WITH_GATES"', carrier)
        self.assertIn('write_parallelism: "ONLY_NON_OVERLAPPING_COLLISION_DOMAINS"', carrier)
        self.assertIn("recommended: true", carrier)

    def test_local_bridge_is_narrow_and_fail_closed(self):
        bridge = text("coordination/GOVERNANCE/LOCAL-WORKBUDDY-BRIDGE-CONTRACT-v1.0.yaml")
        self.assertIn('primary: "OFFICIAL_CODEBUDDY_PYTHON_SDK"', bridge)
        self.assertIn('forbidden_default: "UNRESTRICTED_PUBLIC_REPO_SELF_HOSTED_GITHUB_RUNNER"', bridge)
        self.assertIn('bind_default: "127.0.0.1"', bridge)
        self.assertIn('auth_none_on_normal_host: "FORBIDDEN"', bridge)
        self.assertIn('on_any_ambiguity: "FAIL_CLOSED_NO_PROCESS_START"', bridge)

    def test_model_cost_is_observation_not_permanent_truth(self):
        catalog = text("coordination/EXECUTION/MODEL-CATALOG-SNAPSHOT-2026-09-04.yaml")
        router = text("coordination/GOVERNANCE/MODEL-CAPABILITY-COST-ROUTER-v1.0.yaml")
        self.assertIn('display_name: "GLM-5.3-Flash"', catalog)
        self.assertIn("observed_credit_multiplier: 0.06", catalog)
        self.assertIn('display_name: "Deepseek-V4-Pro"', catalog)
        self.assertIn("observed_credit_multiplier: 0.51", catalog)
        self.assertIn('display_name: "GLM-5.3"', catalog)
        self.assertIn("observed_credit_multiplier: 0.79", catalog)
        self.assertIn('display_name: "Hy4 preview"', catalog)
        self.assertIn("free_promotion_must_not_be_assumed_after_observation: true", catalog)
        self.assertIn('refresh_rule: "RECHECK_AT_DISPATCH_WHEN_LOCALLY_OBSERVABLE"', router)
        self.assertIn("never_use_credit_multiplier_alone: true", router)
        self.assertIn('fast_default: "GLM-5.3-Flash"', router)
        self.assertIn('deep_peer_models: ["Deepseek-V4-Pro", "GLM-5.3"]', router)
        self.assertIn('deep_selection: "TASK_AFFINITY_PLUS_FRESH_VALUE"', router)

    def test_deep_peer_tier_and_codex_standard_are_distinct_from_frontier(self):
        router = text("coordination/GOVERNANCE/MODEL-CAPABILITY-COST-ROUTER-v1.0.yaml")
        fabric = text("coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
        gpt_start = text("coordination/GPT-UNIFIED-ORCHESTRATOR-START-HERE.md")
        wb_start = text("coordination/WORKBUDDY-UNIFIED-START-HERE.md")

        self.assertIn("fixed_primary_forbidden: true", router)
        self.assertIn('same_capability_tier_may_contain_multiple_peer_models: true', router)
        self.assertIn("Deepseek-V4-Pro / GLM-5.3 同档 peer models", wb_start)
        self.assertIn("CODEX_STANDARD_ENGINEERING:", router)
        self.assertIn('named_standard_preference_examples:', router)
        self.assertIn('      - "GPT-5.6 when actually available"', router)
        self.assertIn("codex_standard_not_equivalent_to_frontier: true", fabric)
        self.assertIn("Codex 是载体，不等于 frontier", gpt_start)
        self.assertIn("Codex Standard 可在 L1/L2", gpt_start)

    def test_frontier_compute_is_value_gated_and_workbuddy_cannot_self_escalate(self):
        router = text("coordination/GOVERNANCE/MODEL-CAPABILITY-COST-ROUTER-v1.0.yaml")
        fabric = text("coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
        gpt_start = text("coordination/GPT-UNIFIED-ORCHESTRATOR-START-HERE.md")
        wb_start = text("coordination/WORKBUDDY-UNIFIED-START-HERE.md")

        self.assertIn('principle: "ALLOCATE_SCARCE_FRONTIER_COMPUTE_BY_EXPECTED_MARGINAL_VALUE_NOT_PRESTIGE"', router)
        self.assertIn("frontier_spend_requires_explicit_value_case: true", router)
        self.assertIn('frontier_default: "DENY_UNLESS_VALUE_GATE_PASSES"', fabric)
        self.assertIn("workbuddy_cannot_self_authorize_frontier_compute: true", fabric)
        self.assertIn("Reality Map -> Architecture Gap Map -> Decision Set -> Bounded Frontier Questions", gpt_start)
        self.assertIn("自己启动 Codex frontier lane", wb_start)
        self.assertIn("named_frontier_models_are_preferences_not_dependencies: true", fabric)
        self.assertIn("named_model_is_required_dependency: false", router)

    def test_owner_private_memory_policy_and_secret_exclusion(self):
        fabric = text("coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
        self.assertIn('ordinary_owner_authorized_private_memory_publication: "ALLOWED"', fabric)
        self.assertIn('    - "api/client secrets"', fabric)
        self.assertIn('    - "auth/session/access/refresh tokens"', fabric)

    def test_old_factories_are_inputs_not_parallel_global_authorities(self):
        migration = text("coordination/EXECUTION/MIGRATION-591-592-TO-596.yaml")
        self.assertIn("  - issue: 591", migration)
        self.assertIn("    pr: 593", migration)
        self.assertIn("  - issue: 592", migration)
        self.assertIn("    pr: 594", migration)
        self.assertIn("SUPERSEDE_GLOBAL_SCOPE", migration)
        self.assertIn("UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml", migration)


if __name__ == "__main__":
    unittest.main()
