# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-17T01:30:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R139-DOMAIN-LEARNING-HANDOFF-DRY-RUN` | 139 | `RESERVED_NON_EXECUTABLE` | `false` | #375 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `READY` | `READY` | `false` | RESERVATION_MERGE_THEN_FRESH_POST_RESERVATION_RECONCILIATION_AND_SEPARATE_ACTIVATION |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | EXPLICIT_USER_START_THEN_FRESH_CONTROL_TOWER_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` | `CODEX` | `LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION` | 6 paths | epoch 139 · #375/#None |
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

- **R136 / R137 / R138 均已完成并关闭**。R138 final implementation merge `bf39a7e71860c709c85eb8ab3980d9776fe3f3bd`，post-merge closure `76c12d65d390858658b3447567ca25e6d71566b0`。
- **R139 architecture 已 canonical**。Issue #375；architecture PR #376；merge `f63582091b3bcc0ba74018e196342255957e3a51`。
- **R139 当前仅为非执行预留**。`RESERVED_NON_EXECUTABLE / execution_allowed=false / runtime_code_change_allowed=false`。Codex heartbeat 不得领取。
- **R139 目标**：把“优秀案例、好/坏反馈、真实生成证据、修订差异、纠正/反例”从 Signal Tower 以可验证 handoff 送给 domain-owned learning system；首个目标域是 AI Film。
- **Signal != Task != Learning Object**。普通导演反馈默认 `TRACE_ONLY / DOMAIN_WORKFLOW`，不会自动污染 Durable Signal backlog；只有持久系统目标/缺陷才升级 Durable Signal，正式工程任务仍需 Control Tower。
- **AI Film 继续是唯一 domain learning authority**。Second Brain 不决定 AI Film `candidate/scene_verified/project_verified/general_stable`，不复制最终 lesson body，不直接写 AI Film canonical。
- **Stage A / Stage B 分离**：R139 只做 Second Brain packet/receipt contract、router/idempotency/privacy/materiality 与 AI Film exact-head read-only dry-run。未来真正 candidate writeback 必须由 separately governed AI Film domain-owned adapter/writer 完成。
- **真实 smoke 设计**：一条用户明确“录入优秀案例”的时尚走秀案例；一条 `CD25-KAIM-WINDOW-AB-20260815` C-DANCE 2.5 真实 A/B 反馈，必须保留 confounded/inconclusive 而不能造假归因。
- **R138-F01 继续保留**，未来 production promotion 前仍需 dedicated Docker query-returncode-failure regression。
- **Lane B 继续 user-held / NO_TRADE**；Lane C closed/frozen；QCLAW/WorkBuddy 均不可执行。

## R139 reservation evidence

- Issue: `#375`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R139-DOMAIN-LEARNING-HANDOFF-DRY-RUN`
- Route epoch: `139`
- Mode: `【Codex模式：项目计划模式】`
- Architecture PR: `#376`
- Architecture merge: `f63582091b3bcc0ba74018e196342255957e3a51`
- Architecture: `DOMAIN-LEARNING-HANDOFF-ARCHITECTURE-v1.0.md`
- Contract: `DOMAIN-LEARNING-HANDOFF-CONTRACT.yaml`
- Threat model: `DOMAIN-LEARNING-HANDOFF-THREAT-MODEL-v1.0.md`
- Reservation reconciliation: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R139-RESERVATION.yaml`
- AI Film read-only ref at reservation: `44c383afd2207a97caf45b1b0da6ee1dece43a76`
- Future implementation branch: `codex/r139-domain-learning-handoff-dry-run`
- Reserved write surface: six exact Second Brain surfaces
- Current execution authority: **NONE**
- AI Film write authority: **NONE**
- Codex merge authority: **NONE**

## 下一关

1. Reservation PR exact-head Control Tower CI must pass.
2. Merge reservation only after GPT exact-head review.
3. Re-fetch post-reservation canonical main, all agent routes/claims/lanes and AI Film exact main.
4. If no drift/collision/authority expansion, create a separate activation receipt/PR to set R139 `READY` and `execution_allowed=true`.
5. After activation becomes canonical, GPT posts the structured dispatch on Issue #375; Codex 20-minute heartbeat may then claim exactly once.

No user wake-up is needed for these ordinary bounded engineering steps. Stop only if implementation would require AI Film canonical write, production/private/secret/permission expansion, major authority change, destructive history operation, expensive purchase, or trading/funds action.
