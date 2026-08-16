# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T12:25:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY` | 136 | `PREPARED_NON_EXECUTABLE` | `false` | #353 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `READY` | `READY` | `false` | PHASE_A_MERGE_THEN_FRESH_R136_PHASE_B_RECONCILIATION_FOR_ACTIVATION |
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
| `LANE-A-HARNESS-INTEGRATION` | `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` | `CODEX` | `MEDIUM_IMPLEMENTATION_RESERVATION` | 2 paths | epoch 136 · #353/#None |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O2** | `FROZEN_INTERFACE_CONSUMPTION` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O2** | `SHARED_KNOWLEDGE_DECISION_CONTEXT` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **S0C 已完成并关闭**。PR #346 merge `336430024faf7ed8ba93b0a102e5e245d08df2f4`；closure PR #347 merge `4aaff242f3fcd67fe68c9c711bcaec5de4947630`。
- **R135 S0D 已完成并关闭**。GPT 接受 exact head `d0249d8b16217f723d6130adbe952d3860fa08ff`，PR #351 merge `918c0bb958626c00b65ed6340b90cd69f7f9f7f7`；post-merge closure main `d83d5a3f8de82b991c1120ea46c818538e893265`。
- **R136 S0E0 已进入 Phase A 非执行预留**。Issue #353，epoch 136。当前冻结 explicit Signal intake、SystemAwarenessProjection、Adaptive Gateway、GlobalSignalPreflight、TaskReleasePacket、RuntimeInvocationReceipt 与 SignalClosureAssessment 契约；`execution_allowed=false`。
- **R136 future implementation surface**：仅 `GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY` + `.github/workflows/global-signal-plane-s0e.yml`。Phase A 不允许 Codex 写入这些路径。
- **AI Film 是第一 read-only runtime-proof consumer**：准备时 source commit `44c383afd2207a97caf45b1b0da6ee1dece43a76`，`PROJECT_INDEX.yaml` authority blob `a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19`，远端 open PR 观察为 0。R136 禁止 AI Film mutation。
- **任务分流原则已冻结候选契约**：普通一次性工作可 `EPHEMERAL/DIRECT`；普通 AI Film 导演默认 `TRACE_ONLY/DOMAIN_WORKFLOW` 并需运行回执；系统/蓝图/模块/技能/正式 Agent 任务默认走 `DURABLE_SIGNAL/GOVERNED_MISSION`。
- **形式任务发布硬门**：无 fresh valid GlobalReconciliationReceipt，不得发布新的 formal task；Signal Tower 仍不能自行授权执行，Control Tower 保持后置执行授权。
- **Harness Runtime / H2 / H7 / private-chat bridge / W3 write / domain write / daemon/live/production / trading：全部未授权**。
- **Lane B：继续 user-held / NO_TRADE**。Lane C Foundation 继续 closed/frozen。

## R136 Phase A evidence

- Issue: `#353`
- Bootstrap receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R136.yaml`
- Intake/Gateway contract: `coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/GLOBAL-SIGNAL-INTAKE-ADAPTIVE-GATEWAY-CONTRACT.yaml`
- Runtime proof contract: `coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION/RUNTIME-INVOCATION-RECEIPT-CONTRACT.yaml`
- R136 Task Brief: `coordination/TASK-BRIEFS/CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY.yaml`
- R136 Route: `coordination/ROUTES/CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY-R136.yaml`
- Dependency DAG reconciled: S0C=`COMPLETED_CLOSED_R134`, S0D=`COMPLETED_CLOSED_R135`, S0E0=`PHASE_A_RESERVED_NON_EXECUTABLE`.

## 下一门：R136 Phase B activation

1. Phase A PR 通过 exact-head Control Tower Python 3.11/3.13 并由 GPT merge；
2. 重新读取 Second Brain canonical main；
3. 重新读取 AI Film main/open PR/`PROJECT_INDEX.yaml` authority；
4. 重新核验 Codex/QCLAW/WorkBuddy routes、Work Claims、Program Lanes 和资源状态；
5. 生成 successor `GLOBAL-RECONCILIATION-RECEIPT-R136-ACTIVATION.yaml`；
6. 把 epoch 136 route 从 `PREPARED_NON_EXECUTABLE` 升为 `READY / execution_allowed=true`；
7. Phase B activation PR exact-head Control Tower 双版本全绿后由 GPT expected-head merge；
8. 用户向 **second-brain-coordination** Codex 窗口发送完整 R136 Launch Envelope；
9. Codex 首先核验 repo/task/epoch/issue/source identity 与资源/跨项目冲突；任一不符则 fail closed；
10. Codex 完成后只进入 GPT exact-head review，不自行 merge，不自动进入 AI Film domain-write successor、Harness/H2/H7/private/production。
