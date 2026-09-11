"""Autopilot 配置加载与校验。

配置以 YAML 表达，全部字段有安全默认值。校验在启动时 fail-fast，
避免在无人值守（睡觉）模式下带着坏配置跑一整夜。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


# 模式语义来自 OWNER-AGENT-BEHAVIOR-AND-INTERRUPTION-PROTOCOL-v1.0.yaml
MODE_SLEEP_AUTONOMY = "SLEEP_AUTONOMY"
MODE_NORMAL_AUTONOMY = "NORMAL_AUTONOMY"
MODE_WRAP_UP = "WRAP_UP"
VALID_MODES = {MODE_SLEEP_AUTONOMY, MODE_NORMAL_AUTONOMY, MODE_WRAP_UP}

# 合法宿主：WorkBuddy（codebuddy CLI，日常主力）与 Codex（codex CLI，高价值专用）
VALID_HOSTS = {"codebuddy", "codex"}

DEFAULT_CONFIG = {
    "repo": "vxz2datoubo/second-brain-coordination",
    "default_branch": "main",
    "mode": MODE_SLEEP_AUTONOMY,
    "max_duration_hours": 8,
    "poll_interval_seconds": 120,
    "worktree_dir": ".autopilot-worktrees",
    "state_dir": ".autopilot-state",
    "executors": {
        "mechanical": True,
        # headless 主执行：用 model_routing.default_tier 指定的宿主+模型做真实工程实现。
        "headless": False,
    },
    # 模型分档路由：按任务价值/复杂度路由到不同宿主 + 模型。
    # 这是 CLI 无人值守的核心价值——App 里手动切模型无法脚本化自动化，CLI 可编程切换。
    #   routine    简单任务 + 验算（快模型，第二双眼睛）
    #   standard   日常搭建（默认，强模型）
    #   high_value 高价值框架 / 反复解不开的问题（Codex GPT-6，算力贵）
    "model_routing": {
        "default_tier": "standard",
        "verify_tier": "routine",
        "tiers": {
            "routine": {"host": "codebuddy", "model": "deepseek-v4.1-flash"},
            "standard": {"host": "codebuddy", "model": "deepseek-v4-pro"},
            "high_value": {"host": "codex", "model": "gpt-6"},
        },
    },
    # 双模型交叉验证：主执行用 default_tier（强模型），验算用 verify_tier（快模型）独立跑。
    # enabled=False 时由 OWNER 睡醒后手动用 CLI 验算；设为 True 则引擎在每轮 verify 后
    # 追加一次独立 review。落地依赖本机 codebuddy CLI。
    "verification": {
        "enabled": False,
    },
    "auto_merge": {
        "tier1_enabled": True,
        "tier2_enabled": False,
        "tier1_path_globs": [
            "coordination/CONTROL-TOWER/**",
            "coordination/ROUTES/**",
            "coordination/RESULTS/**",
            "coordination/PROGRAMS/**/*CLOSEOUT*",
            "coordination/PROGRAMS/**/*RECEIPT*",
            "coordination/PROGRAMS/**/POST-MERGE-*/**",
            ".autopilot-state/**",
        ],
        "tier1_forbidden_terms": [
            "trade", "order", "fund", "secret", "production",
            "credential", "password", "token", "private",
        ],
    },
    "collision_domains": [],
}


@dataclass
class ModelTier:
    host: str
    model: str


@dataclass
class AutopilotConfig:
    repo: str
    default_branch: str
    mode: str
    max_duration_hours: float
    poll_interval_seconds: int
    local_root: Path
    worktree_dir: Path
    state_dir: Path
    executors_mechanical: bool
    executors_headless: bool
    model_routing_tiers: dict[str, ModelTier]
    model_routing_default_tier: str
    model_routing_verify_tier: str
    verification_enabled: bool
    tier1_enabled: bool
    tier2_enabled: bool
    tier1_path_globs: list[str]
    tier1_forbidden_terms: list[str]
    collision_domains: list[str]

    @property
    def is_sleep_autonomy(self) -> bool:
        return self.mode == MODE_SLEEP_AUTONOMY

    @property
    def is_wrap_up(self) -> bool:
        return self.mode == MODE_WRAP_UP

    @property
    def default_tier(self) -> ModelTier:
        return self.model_routing_tiers[self.model_routing_default_tier]

    @property
    def verify_tier(self) -> ModelTier:
        return self.model_routing_tiers[self.model_routing_verify_tier]


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | str | None, local_root: Path | str) -> AutopilotConfig:
    """Load config from a YAML file, falling back to safe defaults."""
    raw: dict[str, Any] = dict(DEFAULT_CONFIG)
    if path is not None:
        p = Path(path)
        if p.is_file():
            with p.open("r", encoding="utf-8") as fh:
                user_cfg = yaml.safe_load(fh) or {}
            if not isinstance(user_cfg, dict):
                raise ValueError("autopilot config must be a YAML mapping")
            raw = _deep_merge(raw, user_cfg)

    root = Path(local_root).resolve()
    tiers_raw = raw["model_routing"]["tiers"]
    if not isinstance(tiers_raw, dict) or not tiers_raw:
        raise ValueError("model_routing.tiers must be a non-empty mapping")
    tiers: dict[str, ModelTier] = {
        str(name): ModelTier(host=str(t["host"]), model=str(t["model"]))
        for name, t in tiers_raw.items()
    }

    cfg = AutopilotConfig(
        repo=str(raw["repo"]),
        default_branch=str(raw.get("default_branch", "main")),
        mode=str(raw["mode"]),
        max_duration_hours=float(raw["max_duration_hours"]),
        poll_interval_seconds=int(raw["poll_interval_seconds"]),
        local_root=root,
        worktree_dir=root / str(raw["worktree_dir"]),
        state_dir=root / str(raw["state_dir"]),
        executors_mechanical=bool(raw["executors"]["mechanical"]),
        executors_headless=bool(raw["executors"]["headless"]),
        model_routing_tiers=tiers,
        model_routing_default_tier=str(raw["model_routing"]["default_tier"]),
        model_routing_verify_tier=str(raw["model_routing"]["verify_tier"]),
        verification_enabled=bool(raw["verification"]["enabled"]),
        tier1_enabled=bool(raw["auto_merge"]["tier1_enabled"]),
        tier2_enabled=bool(raw["auto_merge"]["tier2_enabled"]),
        tier1_path_globs=[str(g) for g in raw["auto_merge"]["tier1_path_globs"]],
        tier1_forbidden_terms=[str(t) for t in raw["auto_merge"]["tier1_forbidden_terms"]],
        collision_domains=[str(c) for c in raw["collision_domains"]],
    )
    validate(cfg)
    return cfg


def validate(cfg: AutopilotConfig) -> None:
    if cfg.mode not in VALID_MODES:
        raise ValueError(f"invalid mode {cfg.mode!r}; expected one of {sorted(VALID_MODES)}")
    if cfg.max_duration_hours <= 0:
        raise ValueError("max_duration_hours must be > 0")
    if cfg.poll_interval_seconds <= 0:
        raise ValueError("poll_interval_seconds must be > 0")
    if not cfg.repo or "/" not in cfg.repo:
        raise ValueError(f"repo must be owner/name, got {cfg.repo!r}")
    if not cfg.executors_mechanical and not cfg.executors_headless:
        raise ValueError("at least one executor (mechanical/headless) must be enabled")
    if cfg.model_routing_default_tier not in cfg.model_routing_tiers:
        raise ValueError(
            f"model_routing.default_tier {cfg.model_routing_default_tier!r} "
            f"not in tiers {sorted(cfg.model_routing_tiers)}"
        )
    if cfg.model_routing_verify_tier not in cfg.model_routing_tiers:
        raise ValueError(
            f"model_routing.verify_tier {cfg.model_routing_verify_tier!r} "
            f"not in tiers {sorted(cfg.model_routing_tiers)}"
        )
    for name, tier in cfg.model_routing_tiers.items():
        if tier.host not in VALID_HOSTS:
            raise ValueError(
                f"model_routing.tiers.{name}.host {tier.host!r} "
                f"not in {sorted(VALID_HOSTS)}"
            )
        if not tier.model:
            raise ValueError(f"model_routing.tiers.{name}.model must be non-empty")
    if not cfg.local_root.is_dir():
        raise ValueError(f"local_root does not exist: {cfg.local_root}")
