# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-17T01:38:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R139-DOMAIN-LEARNING-HANDOFF-DRY-RUN` | 139 | `READY` | `true` | #375 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `true` | CODEX_COMPLETION_SIGNAL_THEN_INDEPENDENT_GPT_EXACT_HEAD_REVIEW_NO_CODEX_MERGE |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 6 paths | epoch 139 · #375/#None |
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

- **R136 / R137 / R138 均已完成并关闭**。R138 post-merge closure main `76c12d65d390858658b3447567ca25e6d71566b0`。
- **R139 architecture 已 canonical**：Issue #375，PR #376，merge `f63582091b3bcc0ba74018e196342255957e3a51`。
- **R139 non-executable reservation 已 canonical**：PR #377，accepted head `fa8f4bd529e7d5b0c3723d90ee5b9449f62c7fbf`，review `4946814715`，Control Tower run `31962098485`，merge `54546699c5684a559137c8efe911629ea47dea0a`。
- **R139 activation 当前候选将释放唯一一个 bounded Codex implementation lease**。目标仅是 Second Brain 侧 Domain Learning Handoff dry-run，不是 AI Film writer。
- **用户工作流目标**：优秀案例、好/坏反馈、真实生成证据、修订差异、纠正/反例通过 Signal Tower 路由给 domain-owned learning system；未来相似导演任务能按适用范围、成熟度、模型版本与失效条件召回。
- **Signal != Task != Learning Object**。日常反馈默认 `TRACE_ONLY / DOMAIN_WORKFLOW`；只有持久系统目标/缺陷才升级 Durable Signal；formal task 仍需 Control Tower。
- **AI Film 是唯一 domain learning authority**。R139 不决定其 maturity、不复制最终 lesson body、不写 AI Film canonical。
- **Stage A / Stage B 分离**：R139 只实现 packet/receipt schema、router/materiality/privacy/idempotency/correction 与 AI Film exact-head read-only smoke。未来 Stage B writer 必须是 separately governed AI Film domain-owned adapter。
- **真实 smoke**：`AI_FILM_EXCELLENT_CASE_FASHION_RUNWAY` 与 `CD25-KAIM-WINDOW-AB-20260815`；后者必须保留 confounded/inconclusive。
- **Codex heartbeat 只有在 activation merge 后才可领取**，并须先通过本地原子 claim/de-dupe；GitHub 记录可审计领取回执。
- **R138-F01 保留**；production/private/secret/permission/Harness/H2/H7/trading/history rewrite 均未授权。
- **Lane B 继续 user-held / NO_TRADE**；Lane C closed/frozen；QCLAW/WorkBuddy 不可执行。

## R139 activation evidence

- Issue: `#375`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R139-DOMAIN-LEARNING-HANDOFF-DRY-RUN`
- Route epoch: `139`
- Mode: `【Codex模式：项目计划模式】`
- Architecture merge: `f63582091b3bcc0ba74018e196342255957e3a51`
- Reservation PR: `#377`
- Reservation merge: `54546699c5684a559137c8efe911629ea47dea0a`
- Activation reconciliation: `coordination/CONTROL-TOWER/R139-ACTIVATION-RECONCILIATION.yaml`
- AI Film exact read-only ref: `44c383afd2207a97caf45b1b0da6ee1dece43a76`
- Implementation branch: `codex/r139-domain-learning-handoff-dry-run`
- Write allowlist: six exact Second Brain surfaces
- AI Film write authority: **NONE**
- Codex merge authority: **NONE**

## 下一关

1. Activation PR exact-head Program Control Tower CI must pass.
2. GPT independently reviews and merges activation with expected-head protection.
3. GPT posts a structured `AUTOMATIC_DISPATCH` on Issue #375 binding exact canonical activation main, task/epoch/branch/allowlist/resource/hard locks/completion signal.
4. Codex heartbeat claims it exactly once and executes in isolated worktree.
5. Codex returns Draft PR + exact-head CI/artifacts/completion signal; GPT independently reviews, fixes or merges under the user's routine engineering authorization.

High-risk gates remain manual, but safe adjacent work should continue without waking the user.
