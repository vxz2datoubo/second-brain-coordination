# MEMORY PATCH — PATCH-0001

patch_id: PATCH-0001
date: 2026-07-16
reason: user_correction — ST最新规则按上下10%处理；删除旧ST=5%和"ST仅收盘清算"表述
approved_by: user
related_task_id: QUANT-MEMORY-SETUP-0001

## add

- ST最新规则基线：上下10%。
- 运行时优先读取正规行情源当日 `upper_limit_price` / `lower_limit_price`。
- 规则引擎使用：exchange + board + security_type + risk_warning_type + listing_stage + special_status + effective_date。
- 行情源与规则引擎不一致时，阻断交易并报警。
- 回测使用历史交易日当时有效的涨跌停规则。
- 保存规则版本、生效日期和来源。

## modify

| 文件 | 原文 | 改后 |
|------|------|------|
| `daytrade_system/AGENTS.candidate.md` | ST stocks (±5%) | ST stocks: latest rules — ±10% baseline; runtime uses `upper_limit_price` / `lower_limit_price`; versioned rule engine with historical effective dates |
| `handoff/ORG-CODEX-REVIEW-PACK-0003/daytrade_system/AGENTS.candidate.md` | ST stocks (±5%) | (同上) |

## deprecate

- 旧"ST=5%"所有有效表述 — 已废弃。
- "ST仅收盘清算" / "ST settlement only" — 已废弃。
- 运行时代码中硬编码的固定涨跌幅常量 — 日活跃状态标记，待Codex重建规则引擎时替换。

## evidence

- user_correction: ST最新规则按上下10%处理
- ORG-CODEX-REVIEW-DECISION-0004_v3 §B03: 确认规则并补充运行时优先级和回测要求

## affected_modules

- `daytrade_system/AGENTS.candidate.md` — 交易子系统作用域文档
- `daytrade_system/` — 运行时涨跌停检查代码（待后续Codex重建）
- `memory/QUANT-SYSTEM-MASTER-MEMORY.md` — §0.5 A股关键约束 + §6.4 交易规则
