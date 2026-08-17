# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-18T00:49:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE` | 142 | `READY_AFTER_ACTIVATION_MERGE` | `true` | #393 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `R142_RESERVED_AFTER_ACTIVATION_MERGE / DIRECT_USER_START_REQUIRED` | `true` | MERGE_ACTIVATION_PR -> USER_DIRECT_START -> CODEX_PROJECT_PLAN_M0 |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | EXPLICIT_USER_START_THEN_SIGNAL_TOWER_PREFLIGHT_AND_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 4 paths | epoch 142 · #393/#None |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各 Agent 看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R141 已完成并 closure canonical**：当前基线 main `408e283697290c03d9b4121543934337d938c99a`；R141 实现租约已释放，Stage-B 仍未授权。
- **R142 Retrospective Signal Intake Bridge 正在走激活门**：Issue `#393`，activation PR `#394`。本 PR 只建立任务 brief、route、claim、ACTIVE 状态和 activation reconciliation，不实现 R142。
- **R142 采用【Codex模式：项目计划模式】**：任务一次连续覆盖 M0 fresh reconcile / plan → M1 `SignalImportPackage/v1` → M2 current-canonical reconciler → M3 one-shot durable bridge → M4 真实历史回溯 E2E 与对抗集 → M5 exact-head CI → M6 evidence/handoff。
- **旧窗口只是 miner，不是 current authority**：old-window `NEW` 只能作为候选；真正 admission 前必须用当前 canonical 判定 `ALREADY_CANONICAL / ALREADY_SATISFIED / DUPLICATE / SUPERSEDED / NEW_DURABLE_SIGNAL / NEEDS_REVALIDATION ...`。
- **唯一 Signal truth 不变**：优先复用 R136 `SignalIntakeGateway` 与 R134 S0C `DurableSignalLedger`；如需 Git-backed transport，它只能是 append-only transport/replay source，不能成为第二 effective ledger。
- **隐私边界**：public coordination repo 不得接收 raw/private conversation body；只允许 public-safe summary、opaque ref 和必要 provenance。
- **Signal ≠ Task**：Signal admission 不得自动创建 Codex/QClaw/WorkBuddy Task 或 Work Claim。
- **QCLAW 仍暂停**：PR #304 保持 Draft/unmerged；R142 不授权 QCLAW 执行。
- **资源**：one Codex route、one local heavy stage、single-worker default、remote CI preferred；no nested pools / daemon / global kill。
- **保留 finding/gate**：`R138-F01`、`R139-STAGE-B`、`R140-MODEL-VERSION-AUTHORITY`、`IAGL-R141-UNKNOWN-007`、`IAGL-STAGE-B` 继续有效，没有被 R142 覆盖。

## R142 activation evidence

- Issue: `#393`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE`
- Route epoch: `142`
- Activation PR: `#394`
- Activation base main: `408e283697290c03d9b4121543934337d938c99a`
- Activation reconciliation: `coordination/CONTROL-TOWER/R142-RETROSPECTIVE-SIGNAL-INTAKE-ACTIVATION-RECONCILIATION.yaml`
- Implementation branch after canonical activation: `codex/r142-retrospective-signal-intake-bridge`
- Initial write scope: existing R136 S0E extension + R142 evidence/tests/workflow only
- S0C source write authority: **NONE unless later GPT scope expansion**
- W3/domain write authority: **NONE**
- Private bridge / daemon / production / trading authority: **NONE**
- Codex merge authority: **NONE**
- Direct user start after activation merge: **REQUIRED**

## 下一关

PR #394 exact-head Program Control Tower CI → GPT 独立复核 main drift / diff / claim / route → 用户明确授权 merge → merge 后用户发送 R142 direct start instruction → Codex 从 M0 fresh reconcile + project plan 开始。未经这条链，不得开工。
