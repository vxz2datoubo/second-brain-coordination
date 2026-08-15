# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-15T18:39:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-COGNITIVE-OS-H1-CONTRACT-SYNTHETIC-SKELETON` | 133 | `READY` | `true` | #338 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `false` | H1_EXACT_HEAD_GPT_REVIEW_NO_AUTO_H2 |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `LIGHT_TO_MEDIUM_IMPLEMENTATION` | 2 paths | epoch 133 · #338/#None |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
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
- **Lane A：H1 contract-only synthetic implementation release**。Issue #338，R133，Codex 单一执行租约；仅允许合同/schema/state-machine/graph/trace/fingerprint synthetic skeleton。
- **Harness Runtime / H2：未授权**。H1 的 READY、CI、完成或 merge 都不能自动释放 H2。
- **Lane B：继续 user-held / NO_TRADE**。
- **Lane C：Foundation DONE / CLOSED_WITH_BOUNDED_GAPS**，无执行租约。

## H1 精确边界

允许写入：

- `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/HARNESS-COGNITIVE-OS-ADAPTER/H1-CONTRACT-SKELETON`
- `.github/workflows/cognitive-os-h1-contracts.yml`

禁止：Harness runtime install/binding、真实 Agent runtime、private W3、W3/#312/#308 runtime mutation、生产 gateway/scheduler、权限/密钥、Formal Skill promotion、交易、H2 route、Codex 自行 merge。

## 资源边界

- Codex active execution route max = 1；
- local heavy stage max = 1；
- H1 是 light/medium，不得膨胀为 heavy multi-agent；
- nested process pools 禁止；
- bounded workers + task-owned child cleanup；
- 禁止全局 kill Python；
- 大测试矩阵优先 remote CI。

## 下一门

R133 控制面发布必须先通过 Python 3.11/3.13 exact-head Control Tower CI：reconciliation、Work Claim、projection、durable witness、Codex route witness 全部 PASS。通过并由 GPT exact-head 审计后，用户才可向 Codex 发送 `读取任务`。

H1 完成后只进入 GPT exact-head review；**不自动 merge、不自动 H2**。
