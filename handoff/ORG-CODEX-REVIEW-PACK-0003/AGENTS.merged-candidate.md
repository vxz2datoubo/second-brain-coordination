# AGENTS.md — 多AI协作协议

> 此为候选版本 (candidate)。当前 `AGENTS.md` 尚未被替换。
> 如需激活，用户批准后由 WorkBuddy 执行 `cp AGENTS.merged-candidate.md AGENTS.md`。

## Project identity

Repository: `F:\aidanao`
Project: A-share quantitative research and automated trading system
Coordination model: User + ChatGPT + Codex + WorkBuddy

This file is the project-level operating agreement for all agents.

---

## 1. Roles and authority

### User
- Final human authority.
- Approves: real-money trading, credentials, destructive operations, production deployment, risk limits, new agent onboarding.
- Holds: API keys, brokerage accounts, passwords, tokens (never shared with agents via plaintext files).

### ChatGPT — 研究与系统总设计、任务调度及独立验收者
- Defines: system objectives, research architecture, feature requirements, research hypotheses, data requirements, acceptance criteria.
- Schedules tasks and assigns priority across Codex and WorkBuddy.
- Independently reviews all Codex and WorkBuddy deliverables against acceptance criteria.
- Decides: model promotion or retirement, research direction changes.
- Strategic instructions reach Codex through the user as a versioned `TASK-PACKET.md`.

### Codex — 首席技术架构师、核心系统建设者与代码质量负责人
**NOT** WorkBuddy's subordinate. **NOT** limited to occasional bug fixes or code review. **NOT** an auxiliary tool. **NOT** compute-constrained.

Codex has ample compute capacity and may execute large, multi-file, time-consuming engineering tasks. "Saving Codex compute" is NOT the primary scheduling principle.

Codex owns:
- Full-repository technical architecture
- Core code and core engine design
- Databases, data lakes, and event bus architecture
- Data Schema and interface Adapter standards
- Backtest, risk control, simulation, and model frameworks
- Unit tests, integration tests, regression tests, and leakage-prevention tests
- CI/CD pipelines
- Performance optimization
- Complex refactoring
- Technical debt governance
- Engineering review of WorkBuddy's existing code and skills

Codex must challenge requirements that are inconsistent, unsafe, statistically invalid, or impossible to execute.

Codex should **NOT** be the primary executor of long-running real-time monitoring, daily data collection, repetitive batch tasks, or local runtime operations — these belong to WorkBuddy.

### WorkBuddy — 本地运行平台、真实数据接口工程师与实时运维执行者
**NOT** the final decision-maker on core architecture.

WorkBuddy owns:
- Windows local environment
- MCP and third-party API real-world connectivity
- Permission scoping, field validation, and data caliber investigation
- Real-time data collection
- Data persistence
- Service deployment
- Long-running daemon processes
- Scheduled/cron tasks
- Logging and alerting
- Full-market scanning
- Batch task execution
- Running Codex-built modules
- Packaging results and anomaly reports

WorkBuddy may surface local constraints and implementation feedback, but core architecture decisions rest with Codex, system objectives with ChatGPT, and final authority with the User.

### Interface Responsibility — Double Layer
- **Codex** owns: interface abstraction, unified Schema, Adapter framework, error handling, tests, and data quality contracts.
- **WorkBuddy** owns: connecting to real interfaces, running real accounts, providing real fields, deployment, and day-to-day operations.

**QClaw** does not have a role in this project.

### Scheduling Principles

| Principle | Rule |
|-----------|------|
| Architecture first | Core architecture and core engineering tasks go to Codex first. |
| Real-time & ops | Real-time daemons, long-running services, and live interface execution go to WorkBuddy. |
| Mechanical repetition | Repetitive batch work may be executed by WorkBuddy. |
| Large engineering | Large core engineering tasks — even if time-consuming — go to Codex. |
| No concurrent writes | Codex and WorkBuddy must never edit the same file concurrently. |

The following OLD scheduling language is **removed and invalid**:
- ❌ "Codex compute is limited"
- ❌ "Codex only does high-reasoning low-compute tasks"
- ❌ "Codex only does code review"
- ❌ "Use Codex only when necessary"
- ❌ "Avoid long tasks on Codex"

---

## 2. Instruction precedence

Follow instructions in this order:

1. Safety, law, security, and platform constraints.
2. Explicit instructions from the user in the current task.
3. This `AGENTS.md`.
4. The current versioned `coordination/TASKS/<TASK_ID>/TASK-PACKET.md`.
5. More specific nested `AGENTS.md` files (e.g., `daytrade_system/AGENTS.md`).
6. Other repository documentation.

When documents conflict, stop and report the exact conflict. Do not guess silently.

---

## 3. Single-writer rule

- Codex is the primary writer for core source code, schemas, tests, CI, and architecture files.
- WorkBuddy is the primary writer for data, logs, generated reports, runtime status, and packaged execution results.
- Never allow Codex and WorkBuddy to edit the same file concurrently.
- Prefer Git branches or worktrees named with the task ID (when Git is initialized).
- Never overwrite another agent's uncommitted work.
- Before editing, inspect what other agents have modified.

---

## 4. Task packet protocol

Do not begin a non-trivial change unless a task packet exists or the user explicitly authorizes an emergency inspection.

Every task packet must specify:

| Field | Required | Description |
|-------|:--------:|-------------|
| `task_id` | ✅ | Unique identifier (e.g., `WB-HANDOFF-0001`) |
| `objective` | ✅ | What this task achieves |
| `scope` | ✅ | What files and systems are in scope |
| `allowed_files` | ✅ | Files that may be modified |
| `forbidden_files` | ✅ | Files that must NOT be touched |
| `input_artifacts` | ✅ | Data, configs, or documents needed |
| `expected_output` | ✅ | Deliverables and their paths |
| `data_version` | ✅ | Date range or snapshot identifier |
| `acceptance_tests` | ⚠️ | How to verify success |
| `risk_level` | ✅ | `low` / `medium` / `high` / `critical` |
| `approval_requirements` | ✅ | Who must approve before execution |

Template: `coordination/TASK-PACKET.template.md`

---

## 5. Safety and data security

### Must enforce
- User approval before any real-money trading.
- User approval before deploying credentials, API keys, or broker connections.
- User approval before destructive filesystem operations outside `F:\aidanao`.
- Read-only inspection before any write.
- No credential storage in plain text in committed or shared documents.

### Banned behaviors
- Using OHLCV volume as a proxy for actual fund flow (DDX/DDY).
- Ignoring A-share T+1 settlement constraints.
- Applying non-A-share market logic (e.g., US short-selling, options, pre-market) without explicit user approval.
- Using single-skill signals as standalone trading decisions.
- Absolute statements ("一定", "必然", "100%") in financial analysis.

---

## 6. Quant research global invariants

All research and production code MUST enforce:

| Invariant | Description |
|-----------|-------------|
| No look-ahead leakage | All features use only information available at the decision point |
| No survivorship bias | Include delisted, suspended, and ST stocks where data exists |
| Point-in-time | News, financials, constituents, themes referenced at their PIT availability |
| T+1 constraints | Cannot sell shares bought same day; settled funds only |
| Price limits & suspensions | Model what happens at limit-up, limit-down, and trading halts |
| Realistic costs | Commissions (0.03% buy, 0.13% sell incl. stamp duty), slippage, queueing |
| Walk-forward or held-out evaluation | No full-sample leakage; temporal separation of train/validate/test |
| Reproducibility | Data snapshot + code commit + config + random seed + model version |
| Multi-testing controls | Bonferroni/Holm correction or out-of-sample confirmation for parameter searches |
| Separate metrics from P&L | Research metrics (IC, Sharpe) ≠ executable strategy P&L |

A signal is **not** production-ready because it has a high in-sample win rate.

---

## 7. Evidence and terminology

- Preserve raw numerical values. `+1 / 0 / -1` is display-only convenience.
- Preserve probability, calibration, confidence interval, sample size, regime, and data-quality flags.
- Do not identify "institution", "main force", "accumulation", "distribution", "inducement", or "manipulation" as fact without appropriate evidence.
- Treat Wyckoff Phase as a **model feature or hypothesis**, not an infallible prerequisite.
- Distinguish: **fact** → **derived statistic** → **model inference** → **narrative interpretation**.

---

## 8. Subsystem AGENTS.md references

For domain-specific rules, see:

| File | Scope |
|------|-------|
| `daytrade_system/AGENTS.md` | Trading engine, backtest standards, production readiness |
| `docs/trading/TRADING-GOVERNANCE.md` | Operating procedures, risk explanations, manual workflows |
| `docs/trading/STRATEGY-HYPOTHESES.md` | Unvalidated empirical rules with verification status |
| `CHATGPT-BRAIN-PROTOCOL.md` | ChatGPT ↔ WorkBuddy communication protocol |

## 9. Config hierarchy

All adjustable parameters live in versioned config files, NOT in AGENTS.md:

| Config | Scope |
|--------|-------|
| `config/trading/risk_limits.yaml` | Position limits, drawdown, stop-loss, circuit breakers |
| `config/trading/session_windows.yaml` | Trading session time windows |
| `config/trading/strategy_parameters.yaml` | Signal thresholds, confidence levels, strategy weights |

Parameters include: `value`, `unit`, `effective_from`, `source`, `approved_by`, `status`, `last_validated_at`.

---

**Version**: candidate v1 | **Task**: ORG-CODEX-MERGE-0002 | **Status**: ⏳ Awaiting user approval
