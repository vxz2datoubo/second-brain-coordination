# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-16T18:57:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER` | 137 | `READY` | `true` | #360 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `true` | CODEX_IMPLEMENTATION_COMPLETION_SIGNAL_THEN_GPT_EXACT_HEAD_REVIEW_NO_MERGE |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `MEDIUM_IMPLEMENTATION` | 6 paths | epoch 137 · #360/#None |
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

- **R136 已完整完成并关闭**。Implementation PR #356 merge `54c99780ad6d1a1cc8a035a18130f26b2f91eb62`；post-merge closure PR #357 merge `16f158e1123fa6b52c1a489ddd53093a91270624`。
- **R137 Phase A 架构已完成**。Issue #358；PR #359 merge `a065cc8eb4d978bef78543f2536d12d659067829`。
- **R137 A1 非执行预留已完成**。PR #361 merge `7b0996a98fc908b2afad6be7775eafc74381e648`。
- **R137 A2 Root Provider Bootstrap 已完成**。PR #362 merge `af786f5851d459c8a580cc6e3de2e2ebed69f5b0`；bootstrap `ROOT-PROVIDER-BOOTSTRAP-R137-0001` 已在本次 activation 中一次性消费，不可重放、不可用于 R138。
- **用户已明确启动 R137**：`启动 R137`。GPT 已 fresh re-observe current main、bootstrap、route/task/claim/lane、其他 Agent、资源与跨项目状态，并生成 `R137-ACTIVATION-RECONCILIATION-0001`。
- **R137 当前状态**：`READY / execution_allowed=true / runtime_code_change_allowed=true`，但只允许 exact R137 allowlist。Codex 仍无 merge 权限。
- **V1 trust class**：`PUBLIC_GITHUB_ON_DEMAND_TRUSTED_PROCESS_V1`。固定 `api.github.com`、public read-only、on-demand、serial；不支持 private repo/token、generic URL、write API、daemon/webhook/polling/scheduler。
- **R137 第一动作必须是项目计划**：在 `R137/EXECUTION-PLAN.yaml` 写明 repository facts、source import map、trust boundary、provider components、observation sequence、evidence bundle、gateway integration、bootstrap consumption、adversarial matrix、resource/rollback/unresolved questions，再开始 material runtime edits。
- **E38/E39 历史能力只做 exact source reuse**：E38 transport = ADAPT_AND_RETEST；E39 selective reference only，旧 non-None approval 语义禁止；whole-branch merge/cherry-pick 禁止。
- **AI Film 继续独立 authority**，activation fresh check main 仍为 `44c383afd2207a97caf45b1b0da6ee1dece43a76`，open PR = 0，只读 freshness reference，不写域仓库。
- **Domain Capability Execution Provider 继续 NOT_AUTHORIZED**，必须等 R137 独立验收/merge/closure 后单独开门。
- **Harness/H2/H7/private W3/domain write/daemon-webhook-polling/production/permissions-secrets/Formal Skill/trading 均未授权**。
- **Lane B 继续 user-held / NO_TRADE**；Lane C closed/frozen。

## R137 activation evidence

- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R137-AUTHORITY-BOUND-LIVE-OBSERVATION-PROVIDER`
- Issue: `#360`
- Route epoch: `137`
- Mode: `【Codex模式：项目计划模式】`
- Activation base main: `af786f5851d459c8a580cc6e3de2e2ebed69f5b0`
- Activation receipt: `coordination/CONTROL-TOWER/R137-ACTIVATION-RECONCILIATION.yaml`
- Activation receipt ID: `R137-ACTIVATION-RECONCILIATION-0001`
- Bootstrap ID: `ROOT-PROVIDER-BOOTSTRAP-R137-0001`
- Bootstrap consumed: **true**
- User launch received: **true**
- Execution authority: **R137_BOUNDED_IMPLEMENTATION_ONLY**
- Implementation branch: `codex/r137-authority-live-observation-provider`
- Merge authority: **NONE_TO_CODEX**

## 下一关：Codex 实现 R137

Codex 必须：
1. 核对 repo/task/epoch/issue/branch/activation receipt；不匹配立即 STOP；
2. 先创建/更新 `R137/EXECUTION-PLAN.yaml`，再做 material runtime edits；
3. 只写 6 个已授权 surface；
4. 实现 public GitHub on-demand read-only provider、LiveObservationEvidenceBundle 与 R136 proof integration；
5. 完整覆盖 caller forgery、host/redirect/media/size/json、pagination、main/PR/review/route/claim/lane/lease/domain/approval drift、expiry/replay/provider-code drift 等对抗测试；
6. 保持 network concurrency=1、single local heavy stage、no nested pools、no global kill Python；
7. exact-head Python 3.11/3.13 CI 后回传，不得 merge；
8. GPT 对 exact head 独立复审后才决定是否进入 merge gate。
