# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-15T22:43:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-PLANE-S0C-ENTERPRISE-SYNTHETIC` | 134 | `PREPARED_AWAITING_POST_MERGE_RECONCILIATION` | `false` | #343 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `READY` | `READY` | `false` | POST_MERGE_GLOBAL_RECONCILIATION_THEN_R134_EXECUTION_ACTIVATION |
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

- **Unified Signal Tower 企业级架构：已合并并 canonical**。PR #342，merge `e3c2465832006a1eb4d97c83bb8bfa8d25a749b1`。
- **Lane A：R134 S0C 处于 Phase A“已准备/已预留、不可执行”**。Issue #343，Work Claim 已预留 exact S0C write surface，但 `execution_allowed=false`。
- **原因**：bootstrap GlobalReconciliationReceipt 绑定 pre-release main；Phase A governance merge 会改变 main，因此必须 merge 后重新生成 postflight receipt，再由第二个 exact-head Control Tower PR 激活 R134。
- **S0D / Harness Runtime / H2 / H7：均未授权**。Phase A/Phase B 都不能自动释放这些阶段。
- **Lane B：继续 user-held / NO_TRADE**。
- **Lane C：Foundation DONE / CLOSED_WITH_BOUNDED_GAPS**。

## Phase A 精确边界

- 预留写入面：
  - `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/GLOBAL-SIGNAL-PLANE/S0-SYNTHETIC`
  - `.github/workflows/global-signal-plane-s0.yml`
- 当前 Codex 写权限：**NONE / execution disabled**。
- 禁止：Harness/H2/H7、S0D、private cross-window bridge、live connector/webhook/daemon、W3/#312/#308 runtime mutation、AI Film/A股 canonical write、生产/权限/密钥、Formal Skill promotion、交易、自行 merge。

## 资源边界

- Work Claim reservation 已占用 R134 S0C surface，防止相邻任务抢写；
- Codex executable route 当前为 0；
- local heavy stage max = 1；
- nested process pools 禁止；
- 禁止全局 kill Python。

## 下一门

1. Phase A governance PR exact-head Control Tower CI 必须全绿；
2. 合并 Phase A；
3. 对新 canonical main + AI Film remote state 做 postflight Global Reconciliation；
4. 生成新 Receipt；
5. Phase B activation PR 将 R134 改成 `READY / execution_allowed=true`；
6. Phase B 再过 Python 3.11/3.13 Control Tower CI 后，用户才可发送完整 R134 启动提示词。

在 Phase B 完成前：**不要启动 Codex。**
