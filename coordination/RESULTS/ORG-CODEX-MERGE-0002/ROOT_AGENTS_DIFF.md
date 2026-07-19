# ROOT_AGENTS_DIFF — 根 AGENTS.md 旧版 vs 合并候选版

> Task: ORG-CODEX-MERGE-0002 | Date: 2026-07-16 03:44 UTC+8

## Quantitative comparison

| Metric | OLD (AGENTS.pre-coordination.md) | NEW (AGENTS.merged-candidate.md) |
|--------|------|------|
| Lines | 481 | ~180 |
| Sections | 14 | 9 |
| Role model | 1 AI (WorkBuddy centered) | 4 roles (User / ChatGPT / Codex / WorkBuddy) |
| Content type | Trading manual + API reference + evolution rules | Coordination protocol + research invariants + safety rules |

## What was REMOVED (and where it went)

| Content | Old section | New location |
|---------|-------------|--------------|
| Trading parameters (position, stop-loss, etc.) | 核心参数 | `config/trading/risk_limits.candidate.yaml` |
| Buy/sell red lines | 买入红线 / 卖出红线 | `docs/trading/STRATEGY-HYPOTHESES.md` (as hypotheses) |
| Time windows T1-T8 | 时间窗口 | `config/trading/session_windows.candidate.yaml` |
| Confidence levels A++ to D | 置信度等级 | `config/trading/strategy_parameters.candidate.yaml` |
| API endpoints & cognitive engine | 认知决策系统 | Deprecated (not deployed) |
| Codex auto-call guide | 超级博弈大脑 | Deprecated (new role model) |
| Self-evolution mechanism | 自进化机制 | `docs/trading/TRADING-GOVERNANCE.md` (design reference) |
| Stock pool & market states | 快速参考 | `docs/trading/TRADING-GOVERNANCE.md` |
| Trading operation procedures | 交易规则摘要 | `docs/trading/TRADING-GOVERNANCE.md` |
| Workflow presets (15-skill analysis, monitoring rules) | Multiple | `docs/trading/TRADING-GOVERNANCE.md` |

## What was ADDED

| Content | Reason |
|---------|--------|
| 4-role authority & boundaries | New coordination model |
| Instruction precedence (6 levels) | Disambiguation protocol |
| Single-writer rule | Prevent concurrent editing conflicts |
| Task packet protocol (mandatory fields) | Standardize task delegation |
| Quant research global invariants (10 standards) | Enforce research quality |
| Evidence & terminology standards | Separate fact from inference |
| Subsystem AGENTS.md references | Point to domain-specific rules |
| Config hierarchy | Separate config from governance |

## Key structural changes

| Aspect | Old | New |
|--------|-----|-----|
| "不可违反" classification | Mixed (trading rules + research hypotheses both called "红线") | Clear separation: global_invariant vs research_hypothesis |
| Parameter mutation | Hardcoded in AGENTS.md | Moved to versioned .yaml configs with audit trail |
| Wyckoff Phase status | "强制前置" (mandatory prerequisite) | "Model feature or hypothesis, not infallible prerequisite" |
| Signal format | "+1/0/-1 required" | "Preserve raw values, +1/0/-1 is display convenience" |
