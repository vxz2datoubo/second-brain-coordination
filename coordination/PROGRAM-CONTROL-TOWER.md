# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-15T21:37:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-A-HARNESS-INTEGRATION, LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-COGNITIVE-OS-H1-CONTRACT-SYNTHETIC-SKELETON` | 133 | `DONE` | `false` | #338 / #340 |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `PAUSED` | `PAUSED` | `false` | EXPLICIT_USER_H2_START_THEN_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | EXPLICIT_USER_START_THEN_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | CONSUME_FROZEN_BOUNDARIES; REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **H0 Cognitive OS × Harness 架构：已合并并 canonical**，PR #336，merge `eb622264929564d70aa11c646b93fe38c0c40a8d`，verdict `ACCEPT_WITH_BOUNDED_DEBT`。
- **Lane A：H1 已完成并关闭执行租约**。PR #340，reviewed head `0b90373d8920caacb7b8847fc0af23e666cdf8a0`，merge `c17df847bee689f23363b0ddbba417c6c37c79ab`；R133 仅作为历史证据保留。
- **Harness Runtime / H2：未授权**。H1 的完成、CI、审核或 merge 都不能自动释放 H2。
- **Lane B：继续 user-held / NO_TRADE**。
- **Lane C：Foundation DONE / CLOSED_WITH_BOUNDED_GAPS**，无执行租约。
- **跨窗口状态漂移：必须在新任务发布前重新核对**。发现 route / Work Claim / Program Lane / PR 状态不一致时，标记 `CROSS_WINDOW_STATE_DRIFT` 并先 reconciliation，再发新任务。

## H1 关闭边界

R133 已关闭，不再有当前写入面。未来任何 H2 或 Lane A 新实施都必须重新建立：

- 新 route epoch / task_id；
- 新 Work Claim；
- fresh O0-O4 / WIP / resource scan；
- fresh durable authorization witness；
- GPT release；
- 需要时的用户高风险审批。

禁止从 H1 closure 推导：Harness runtime install/binding、真实 Agent runtime、private W3、W3/#312/#308 runtime mutation、生产 gateway/scheduler、权限/密钥、Formal Skill promotion、交易或 H2 授权。

## 资源边界

- Codex active execution route max = 1；当前第二大脑侧 R133 已释放该租约；
- local heavy stage max = 1；
- nested process pools 禁止；
- bounded workers + task-owned child cleanup；
- 禁止全局 kill Python；
- 大测试矩阵优先 remote CI。

## 下一门

当前先保持 Lane A/H2 与 Lane B implementation 均未授权。任何下一条跨项目 implementation 任务发布前，必须先读取最新 per-agent route、Work Claim、Program Lane、相关 PR/merge/closure状态，并处理 `CROSS_WINDOW_STATE_DRIFT`。
