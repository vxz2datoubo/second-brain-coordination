# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-15T22:49:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-PLANE-S0C-ENTERPRISE-SYNTHETIC` | 134 | `READY` | `true` | #343 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `false` | S0C_EXACT_HEAD_GPT_REVIEW_NO_AUTO_S0D_H2_H7 |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `LIGHT_TO_MEDIUM_IMPLEMENTATION` | 2 paths | epoch 134 · #343/#None |
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

- **Unified Signal Tower 企业级架构：已 canonical**。PR #342，merge `e3c2465832006a1eb4d97c83bb8bfa8d25a749b1`。
- **R134 两相发布 Phase A：已 canonical**。PR #344，merge `740b77ab20b24c76bd5621b08123dec657862d5a`，只预留 work surface，未授权执行。
- **Lane A：Phase B 激活候选**。successor GlobalReconciliationReceipt 重新绑定 Phase A 后的新 main 与 AI Film remote state；本 PR exact-head Control Tower 通过并 merge 后，R134 才真正成为 `READY / execution_allowed=true`。
- **S0C范围**：public-safe/offline pre-Mission Signal Plane，目标是 append-only event ingest、idempotency、projection/replay、GlobalReconciliationReceipt 与 24 条 enterprise regressions。
- **S0D / Harness Runtime / H2 / H7：均未授权**。S0C 的执行、CI、review、merge 都不能自动释放这些阶段。
- **Lane B：继续 user-held / NO_TRADE**。
- **Lane C：Foundation DONE / CLOSED_WITH_BOUNDED_GAPS**。

## S0C 精确写入面

- `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0-SYNTHETIC`
- `.github/workflows/global-signal-plane-s0.yml`

禁止：DeepSeek Harness runtime、H2/H7、S0D、private cross-window bridge、webhook/daemon/live connector、W3/#312/#308 runtime mutation、AI Film/A股 canonical write、生产/权限/密钥、Formal Skill promotion、交易、自行 merge。

## 资源边界

- Codex active execution route max = 1；R134 激活后独占该 lease；
- S0C 为 light/medium，默认 single worker；
- local heavy stage max = 1；
- nested process pools 禁止；
- bounded workers + task-owned child cleanup；
- 禁止全局 kill Python；
- 大测试矩阵优先 remote CI；
- 禁止 daemon/server。

## 下一门

1. Phase B activation PR exact-head Control Tower Python 3.11/3.13 必须全绿；
2. GPT exact-head review + merge；
3. merge 后再次确认 canonical `ACTIVE-CODEX-TASK` 是 epoch 134 / READY / execution_allowed=true；
4. 用户才可向 **second-brain-coordination** 的 Codex 窗口发送完整 R134 启动提示词；
5. S0C 完成后只进入 GPT exact-head review，**不自动 merge、不自动 S0D、不自动 H2/H7**。
