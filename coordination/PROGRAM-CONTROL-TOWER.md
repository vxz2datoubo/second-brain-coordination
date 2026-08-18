# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-18T12:29:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE` | 142 | `PAUSED_EXECUTOR_SUBSTITUTED` | `false` | #393 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `R142_GPT_ENGINEERING_WORKER_RELEASED / FRESH_RECONCILE_REQUIRED` | `true` | GPT_ENGINEERING_WORKER_FRESH_RECONCILE -> PROJECT_PLAN_M0 |
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
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `GPT_ENGINEERING_WORKER` | `MEDIUM_IMPLEMENTATION` | 4 paths | epoch 142 · #393/#None |
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
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy 当前能否执行，以最新 `ACTIVE-*.yaml` 为准；GPT Engineering Worker executor substitution 以 canonical handoff route + Lane Work Claim + Issue/PR handoff 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R142 保留同一 Mission/Issue/epoch，但执行器已从 Codex 切为 GPT Engineering Worker**：Codex 未曾实际启动 R142，现为 `PAUSED_EXECUTOR_SUBSTITUTED / execution_allowed=false`；replacement 使用 `GPT-5.6 Sol`，仍为【项目计划模式】，先 M0 fresh reconcile + plan commit。
- **R142 用户启动门已满足**：用户明确批准并行工程并新开 GPT 项目窗口。新窗口仍必须 fresh reconcile current main / Issue #393 / original route+task brief / Lane-A claim / substitution route，不能仅凭聊天提示词开工。
- **R60 与 R142 允许并行**：R60 只写 R60 root + `.github/workflows/r60-retrieval-adversarial-benchmark.yml`；R142 只写 S0E bounded paths + `.github/workflows/global-signal-plane-r142-retrospective-intake.yml`。同一 canonical object writer 仍最多 1；local-heavy stage 最多 1；nested parallelism 禁止。
- **QQ 继续保留态**：`ACTIVE-QCLAW-TASK.yaml` 为 `PAUSED / execution_allowed=false`。QQ 算力是可长期保留资源，GPT 能可靠完成的默认优先 GPT。
- **所有 GPT Worker 必须真实记录身份**：`executor_role=GPT_ENGINEERING_WORKER`、`model_id=GPT-5.6 Sol` 与实际 harness/tool provenance；不得冒充历史 Codex/QCLAW executor。
- **R142 目标不变**：历史聊天只形成候选包，不拥有今天的最终 `NEW` 判定权；必须 fresh reconcile 当前 canonical，只有真正仍有效的 durable Signals 才可经现有 R136 Gateway → S0C ledger 正式 admission，并拿到 durable receipt/read-back。`Signal != Task`，`prepared package != persisted signal`。
- **R142 硬锁不变**：S0C source read-only；无 private/raw public write；无 private cross-window bridge；无 daemon/webhook/server/scheduler；无 W3/domain write；无 Formal Skill promotion；无 auto Task；无 production/permission/trading；无 self-merge。
- **R60 当前仍等待独立 Reviewer 对 exact head 的最终验收**；其状态不授予 R142 任何额外权限。
- **保留 finding/gate**：`R138-F01`、`R139-STAGE-B`、`R140-MODEL-VERSION-AUTHORITY`、`IAGL-R141-UNKNOWN-007`、`IAGL-STAGE-B` 继续有效。

## R60 executor-substitution evidence

- Issue: `#296`
- Draft PR: `#304`
- Task: `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60`
- Route epoch: `60`
- Same branch: `qclaw/p2-retrieval-adversarial-benchmark-r60`
- Historical executor: `QCLAW`
- Replacement executor: `GPT_ENGINEERING_WORKER`
- Required model: `GPT-5.6 Sol`
- Canonical handoff route: `coordination/ROUTES/GPT-ENGINEERING-WORKER-R60-EXECUTOR-SUBSTITUTION.yaml`
- QCLAW current execution authority: **NONE**
- Worker merge authority: **NONE**

## R142 status

- Issue: `#393`
- Task: `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE`
- Route epoch: `142`
- Historical executor: `CODEX / ACTIVATED_BUT_NOT_STARTED`
- Replacement executor: `GPT_ENGINEERING_WORKER`
- Required model: `GPT-5.6 Sol`
- Substitution route: `coordination/ROUTES/GPT-ENGINEERING-WORKER-R142-EXECUTOR-SUBSTITUTION.yaml`
- User start for replacement: **RECEIVED**
- Implementation branch: `codex/r142-retrospective-signal-intake-bridge` (name retained for history; GPT must not claim Codex identity)
- S0C source write authority: **NONE unless later GPT scope expansion**
- W3/domain write authority: **NONE**
- Private bridge / daemon / production / trading authority: **NONE**
- Worker merge authority: **NONE**

## 下一关

新开的 GPT Engineering Worker 窗口 fresh reconcile canonical state 后，在同一 R142 / Issue #393 / route epoch 142 / branch `codex/r142-retrospective-signal-intake-bridge` 中执行 M0→M6。先提交 project plan，再实现；完成后只发 `R142_RETROSPECTIVE_SIGNAL_INTAKE_BRIDGE_READY_FOR_GPT_REVIEW` 并停止，等待独立 GPT exact-head 验收，不得自行 merge。
