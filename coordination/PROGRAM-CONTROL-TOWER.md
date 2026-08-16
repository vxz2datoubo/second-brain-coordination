# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T12:47:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R136-ADAPTIVE-INTAKE-EXECUTION-GATEWAY` | 136 | `READY` | `true` | #353 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `false` | USER_R136_LAUNCH_THEN_IMPLEMENTATION_EXACT_HEAD_GPT_REVIEW |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 2 paths | epoch 136 · #353/#None |
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

- **S0C 已完成并关闭**。PR #346 merge `336430024faf7ed8ba93b0a102e5e245d08df2f4`；closure PR #347 merge `4aaff242f3fcd67fe68c9c711bcaec5de4947630`。
- **R135 S0D 已完成并关闭**。GPT 接受 exact head `d0249d8b16217f723d6130adbe952d3860fa08ff`，PR #351 merge `918c0bb958626c00b65ed6340b90cd69f7f9f7f7`；post-merge closure main `d83d5a3f8de82b991c1120ea46c818538e893265`。
- **R136 Phase A 已 canonical**。PR #354 exact head `facb1e02469218cbac3c8ecab35a48ee623bae00`，GPT review `4945417110`，Control Tower `31927346440` 与 Signal Plane architecture `31927346447` 双版本 PASS，merge `5f14455babdb46dbb5ffabd644a006c24554c5f2`。
- **R136 Phase B fresh reconciliation：PASS**。AI Film main 仍为 `44c383afd2207a97caf45b1b0da6ee1dece43a76`，远端 open PR 观察为 0，`PROJECT_INDEX.yaml` source authority blob 仍为 `a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19`。QCLAW/WorkBuddy 仍不可执行，无 GitHub 可见 same-agent lease collision。
- **R136 S0E0 激活边界**：public-safe、显式 Signal intake、derived System Awareness、Adaptive Gateway、GlobalSignalPreflight、TaskReleasePacket、RuntimeInvocationReceipt、SignalClosureAssessment；不宣称自动读取所有 ChatGPT 私有窗口。
- **R136 唯一写入面**：Second Brain `GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY` + `.github/workflows/global-signal-plane-s0e.yml`。
- **AI Film 是第一 runtime-proof consumer，但严格只读**。普通 directing 应证明 `TRACE_ONLY + DOMAIN_WORKFLOW`，并用机制证据证明 PROJECT_INDEX/read_sets/route/scans 实际执行；R136 不允许修改 AI Film。
- **Codex active lease**：epoch 136 / Issue #353 / `READY / execution_allowed=true`，但真正开工仍需要用户把完整 R136 Launch Envelope 发到 **second-brain-coordination** Codex 窗口。
- **正式任务发布硬门**：`NO_FRESH_VALID_GLOBAL_RECONCILIATION_RECEIPT -> NO_NEW_FORMAL_TASK_RELEASE`；Signal Tower 不自行授权，Control Tower 保持执行授权。
- **Task DONE ≠ Signal SATISFIED**。只有 original desired effect / success condition / outcome evidence 满足后才从 active projection 移出，append-only history 保留。
- **Harness Runtime / H2 / H7 / private-chat ingestion / W3 write / AI Film/domain write / daemon/live/production / permissions/secrets / trading：均未授权**。
- **Lane B：继续 user-held / NO_TRADE**。Lane C Foundation 继续 closed/frozen。

## R136 Phase B evidence

- Issue: `#353`
- Bootstrap receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R136.yaml`
- Activation receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R136-ACTIVATION.yaml`
- Phase A PR / accepted head / merge: `#354` / `facb1e02469218cbac3c8ecab35a48ee623bae00` / `5f14455babdb46dbb5ffabd644a006c24554c5f2`
- Second Brain post-Phase-A main rechecked: `5f14455babdb46dbb5ffabd644a006c24554c5f2`
- AI Film activation source SHA: `44c383afd2207a97caf45b1b0da6ee1dece43a76`
- AI Film source authority blob: `a9d6fd69b861c50aeef7d4f72c89fc7988e6ae19`
- QCLAW execution: false
- WorkBuddy execution: false
- unknown local/unpushed AI Film Codex activity: launch-time fail-closed requirement

## 启动前最后一关

Phase B activation PR 必须：
1. exact-head Control Tower Python 3.11/3.13 全绿；
2. exact-head Signal Plane architecture Python 3.11/3.13 全绿（本 PR 触发时）；
3. GPT compare main/head and expected-head merge；
4. merge 后重新确认 canonical `ACTIVE-CODEX-TASK` 为 epoch 136 / READY / execution_allowed=true；
5. 用户发送完整 R136 Launch Envelope；
6. Codex 首先重新检查 repo/task/epoch/issue/source commit/PROJECT_INDEX blob 与本地 AI Film Codex collision，任一不符就返回 `WRONG_REPOSITORY_OR_ROUTE_OR_LEASE_CONFLICT`；
7. Codex 创建并持续维护 `EXECUTION-PLAN.yaml`，随后才进行 material runtime edits；
8. 完成后只进入 GPT exact-head review，不自行 merge，不自动进入 AI Film domain-write successor、Harness/H2/H7/private/production。
