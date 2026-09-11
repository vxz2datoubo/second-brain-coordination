"""Autopilot 配置加载与校验。

配置以 YAML 表达，全部字段有安全默认值。校验在启动时 fail-fast，
避免在无人值守（睡觉）模式下带着坏配置跑一整夜。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# 模式语义来自 OWNER-AGENT-BEHAVIOR-AND-INTERRUPTION-PROTOCOL-v1.0.yaml
MODE_SLEEP_AUTONOMY = "SLEEP_AUTONOMY"
MODE_NORMAL_AUTONOMY = "NORMAL_AUTONOMY"
MODE_WRAP_UP = "WRAP_UP"
VALID_MODES = {MODE_SLEEP_AUTONOMY, MODE_NORMAL_AUTONOMY, MODE_WRAP_UP}

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
        # headless 主执行：WorkBuddy CLI（codebuddy -p --model），用强模型做真实工程实现。
        # Codex 只在交易系统等高价值任务用（GPT-6），不参与日常 headless 执行。
        "headless": False,
        "headless_model_profile": "deepseek-v4-pro",
    },
    # 双模型交叉验证：主执行用 WorkBuddy 强模型（deepseek-v4-pro），验算用 WorkBuddy 快模型
    # （deepseek-v4.1-flash）独立跑（codebuddy -p --model <model>）。Codex 只在交易系统等
    # 高价值任务使用（GPT-6），不参与日常搭建/验算。
    # enabled=False 时由 OWNER 睡醒后手动用 CLI 验算；设为 True 则引擎在每轮 verify 后
    # 追加一次独立 review。落地依赖本机 codebuddy CLI。
    "verification": {
        "enabled": False,
        "model": "deepseek-v4.1-flash",
        "mode": "codebuddy_headless",
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
    headless_model_profile: str
    verification_enabled: bool
    verification_model: str
    verification_mode: str
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
        headless_model_profile=str(raw["executors"]["headless_model_profile"]),
        verification_enabled=bool(raw["verification"]["enabled"]),
        verification_model=str(raw["verification"]["model"]),
        verification_mode=str(raw["verification"]["mode"]),
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
    if not cfg.local_root.is_dir():
        raise ValueError(f"local_root does not exist: {cfg.local_root}")
