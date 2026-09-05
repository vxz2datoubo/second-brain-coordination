from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def test_unified_fabric_has_exactly_four_declared_projects():
    registry = load("coordination/EXECUTION/PROJECT-REGISTRY.yaml")
    ids = {item["project_id"] for item in registry["projects"]}
    assert ids == {
        "SECOND_BRAIN",
        "TRADING_SYSTEM",
        "REALTIME_INTERACTIVE_FILM_GAME",
        "AI_DIRECTOR",
    }
    assert registry["scheduler"]["simultaneous_projects_allowed"] is True
    assert registry["scheduler"]["global_single_writer_by_collision_domain"] is True
    assert registry["scheduler"]["no_project_may_define_second_global_router"] is True


def test_project_adapters_are_global_protocol_overlays_not_replacements():
    schema = load("coordination/GOVERNANCE/PROJECT-EXECUTION-ADAPTER-SCHEMA-v1.0.yaml")
    forbidden = set(schema["weakening_forbidden"])
    assert {
        "single_writer_per_collision_domain",
        "exact_head_review_identity",
        "no_self_review",
        "no_self_merge",
        "credential_secret_exclusion",
        "active_task_authority_required",
    } <= forbidden

    for path in [
        "coordination/EXECUTION/PROJECT-ADAPTERS/SECOND-BRAIN.yaml",
        "coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml",
        "coordination/EXECUTION/PROJECT-ADAPTERS/REALTIME-INTERACTIVE-FILM.yaml",
        "coordination/EXECUTION/PROJECT-ADAPTERS/AI-DIRECTOR.yaml",
    ]:
        adapter = load(path)
        assert adapter["adapter_schema"] == "PROJECT-EXECUTION-ADAPTER-v1"
        assert "hard_boundaries" in adapter
        assert "acceptance" in adapter


def test_trading_market_read_does_not_mint_order_authority():
    trading = load("coordination/EXECUTION/PROJECT-ADAPTERS/TRADING-SYSTEM.yaml")
    tdx = next(item for item in trading["tool_interfaces"] if item["id"] == "TDX_TQ_LOCAL_MARKET_DATA")
    assert tdx["default_authority"] == "READ_MARKET_DATA"
    assert tdx["place_order_allowed"] is False
    assert trading["authority"]["engineering_execution_does_not_imply_order_authority"] is True
    assert trading["authority"]["order_authority"] == "SEPARATE_EXPLICIT_OWNER_GATE"
    assert "NO_LOOKAHEAD" in trading["numeric_and_research_invariants"]
    assert "POINT_IN_TIME_ONLY" in trading["numeric_and_research_invariants"]


def test_cli_desktop_and_parallel_projects_remain_single_writer_safe():
    carrier = load("coordination/GOVERNANCE/EXECUTION-CARRIER-AND-CONCURRENCY-CONTRACT-v1.0.yaml")
    assert carrier["carrier_switch"]["same_task_simultaneous_writers"] == "FORBIDDEN"
    assert carrier["concurrency"]["multi_project_parallelism"] == "ALLOWED_WITH_GATES"
    assert carrier["concurrency"]["write_parallelism"] == "ONLY_NON_OVERLAPPING_COLLISION_DOMAINS"
    assert carrier["git_worktrees"]["recommended"] is True


def test_local_bridge_is_pull_based_and_public_runner_is_not_default():
    bridge = load("coordination/GOVERNANCE/LOCAL-WORKBUDDY-BRIDGE-CONTRACT-v1.0.yaml")
    assert bridge["preferred_implementation"]["primary"] == "OFFICIAL_CODEBUDDY_PYTHON_SDK"
    assert bridge["preferred_implementation"]["forbidden_default"] == "UNRESTRICTED_PUBLIC_REPO_SELF_HOSTED_GITHUB_RUNNER"
    assert bridge["launch_modes"]["CLI_SERVE"]["bind_default"] == "127.0.0.1"
    assert bridge["launch_modes"]["CLI_SERVE"]["auth_none_on_normal_host"] == "FORBIDDEN"
    assert bridge["admission_gate"]["on_any_ambiguity"] == "FAIL_CLOSED_NO_PROCESS_START"


def test_model_prices_are_observations_and_router_requires_runtime_refresh():
    catalog = load("coordination/EXECUTION/MODEL-CATALOG-SNAPSHOT-2026-09-04.yaml")
    router = load("coordination/GOVERNANCE/MODEL-CAPABILITY-COST-ROUTER-v1.0.yaml")
    values = {m["display_name"]: m["observed_credit_multiplier"] for m in catalog["models"]}
    assert values["GLM-5.3-Flash"] == 0.06
    assert values["Deepseek-V4-Pro"] == 0.51
    assert values["Hy4 preview"] == 0.0
    assert catalog["freshness"]["free_promotion_must_not_be_assumed_after_observation"] is True
    assert router["catalog"]["refresh_rule"] == "RECHECK_AT_DISPATCH_WHEN_LOCALLY_OBSERVABLE"
    assert router["selection_constraints"]["never_use_credit_multiplier_alone"] is True
    assert router["initial_policy"]["fast_default"] == "GLM-5.3-Flash"
    assert router["initial_policy"]["deep_default"] == "Deepseek-V4-Pro"


def test_private_memory_policy_only_globally_excludes_authentication_secrets():
    fabric = load("coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
    assert fabric["security"]["ordinary_owner_authorized_private_memory_publication"] == "ALLOWED"
    secret_categories = set(fabric["security"]["secret_values_forbidden_in_github"])
    assert "api/client secrets" in secret_categories
    assert "auth/session/access/refresh tokens" in secret_categories


def test_old_factories_are_migration_inputs_not_parallel_global_authorities():
    migration = load("coordination/EXECUTION/MIGRATION-591-592-TO-596.yaml")
    assert {(x["issue"], x["pr"]) for x in migration["inputs"]} == {(591, 593), (592, 594)}
    assert migration["target"]["global_protocol"].endswith("UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
