# 状态语义 · Status Semantics

> 最重要的原则：**禁止折叠以下状态**
> `candidate` / `CI passed` / `independent review` / `ACCEPT` / `canonical` / `deployed` / `active`

## 项目状态 (ProjectStateKind)

| 值 | 中文 | 含义 |
|---|---|---|
| `ACTIVE` | 正在推进 | 有活跃泳道且在执行 |
| `PAUSED` | 已暂停 | 优先级停放 / 可恢复检查点 |
| `CLOSED` | 已关闭 | 无当前实现 |
| `BLOCKED` | 受阻 | 需要 Owner 或依赖解锁 |
| `CANONICAL_HISTORY` | 已进正史 | 历史里程碑 |
| `UNKNOWN` | 状态未知 | **无活跃泳道，不编造状态** |

## 任务状态 (TaskState)

覆盖完整生命周期：
`IDEA → PLANNED → READY → DISPATCHED → RUNNING → REVIEW → CANONICALIZATION → DONE`
以及旁路：`BLOCKED / STALLED / OUTCOME_UNKNOWN / OWNER_GATE / PAUSED`

**IDEA / MISSION / AUTHORIZED TASK 是三个不同阶段**（Signal ≠ Task）。

## 施工者活跃度 (AgentLiveness)

**绝不从 PID 或 heartbeat 判定"正在施工"。**

| 值 | 判定依据 |
|---|---|
| `INFRA_LIVE` | 仅基础设施在线 |
| `SESSION_LIVE` | 会话在线但无任务证据 |
| `AGENT_ACTIVE` | 有活跃 route 且 execution_allowed |
| `MEANINGFUL_PROGRESS` | 有 model turn / tool call / file diff / test delta / checkpoint |
| `STALLED` | 曾活跃但已无进展 |
| `BLOCKED` | route blocked |
| `TERMINATED` | 终态 |
| `OUTCOME_UNKNOWN` | 证据不足，**默认不乐观** |
| `IDLE` | route READY 但未开始（无 session 证据） |

> 当前实现：WORKBUDDY route 为 READY → 显示 `IDLE`，提示"route READY, not yet
> executing (no session evidence)"，**而非**显示为"正在施工"。

## 仓库同步 (RepoSyncState)

`SYNCED / REMOTE_AHEAD / LOCAL_AHEAD / DIVERGED / DIRTY / NO_REMOTE / UNKNOWN`

> **0 ahead / 0 behind ≠ 整个系统已同步。** dirty worktree 单独标注。

## 新鲜度 (Freshness)

`FRESH / AGING / STALE / UNKNOWN` — 每个重要数据都带 `observed_at` + `source`。
**不能只显示"最新"。**

## 动作分离（防止"同步=晋升"）

必须在 UX 上区分：
`FETCH` / `PULL` / `PUSH CANDIDATE` / `CREATE PR` / `REVIEW` / `CANONICALIZE` / `MERGE`

> **SYNC ≠ PROMOTION** — 最近真实发生过"同步 GitHub"被误当成"直接 merge main"的问题。

## 数据信任徽章 (TrustBadge)

| 值 | 含义 |
|---|---|
| `CANONICAL` | 已入正史 |
| `CANDIDATE` | 候选，未经独立验收 |
| `RUNTIME_OBSERVED` | 运行时观测 |
| `DERIVED` | 推导（如泳道→项目归属） |
| `HISTORICAL` | 历史 |
| `UNKNOWN` | 未知 |

## 演示数据政策

`MOCK` / `SYNTHETIC` / `REAL_LOCAL` / `REAL_GITHUB` / `LIVE_RUNTIME` 必须可区分。
**Phase 1 MVP 全部使用 REAL_LOCAL + REAL_GITHUB，无 mock。**
