# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-19T17:52:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144` | 144 | `READY` | `true` | #406 / #None |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `DONE_HISTORICAL` | `false` | #296 / #None |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### GPT Engineering Worker slots

| slot | task_id | epoch | status | execution_allowed | model_id | Issue / PR |
|---|---|---:|---|---|---|---|
| _NONE_ | _no active GPT Engineering Worker slot_ | | | | | |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `R144_GPT_ENGINEERING_WORKER_FIRST_CLASS_IMPLEMENTATION_ACTIVE` | `false` | R144_IMPLEMENTATION_READY_FOR_INDEPENDENT_GPT_REVIEW |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `W2_S1_R143_USER_RELEASED_BUT_EXECUTOR_IDENTITY_BLOCKED` | `false` | WAIT_R144_ACCEPTED_MERGED_THEN_FRESH_R143_ACTIVATION |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `LIGHT_TO_MEDIUM_CONTROL_TOWER_IMPLEMENTATION` | 6 paths | epoch 144 · #406/#None |
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
> **执行真源不是本页**。Agent 当前能否执行，以 canonical `ACTIVE-*` route、Work Claim 和 fresh authorization witness 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R144 是当前唯一活动 implementation**：Issue #406，Codex 作为现有受控 Agent，任务仅限把 `GPT_ENGINEERING_WORKER` 纳入 Control Tower 一等执行身份。
- **目标不是让 GPT worker 冒充 Codex**：目标模型为一个 `GPT_ENGINEERING_WORKER` agent type + 可区分的 multi-slot/lease registry；编程1/编程2是 slot/provenance，不是两个新 agent ontology。
- **Lane-B R143 暂停 runtime**：Issue #404 的用户授权保留，但 PR #405 因 executor identity gate 保持 Draft/blocked；R144 未 accepted+merged 前不得写 W2 runtime。
- **Lane-B 在 R144 期间临时撤掉 shared Control Tower read surface**：避免 proposal-only reader 与 R144 Control Tower writer 形成 O3；A/B 当前机械重叠降为 O1 READ_READ。
- **Signal Tower 正常 on-demand 能力继续可用**：R144 不关闭 Signal Tower，也不创建新的 Signal/Task 自动链。
- **R142/R60 保持历史完成态**：没有恢复旧 executor lease，也没有重开历史实现。
- **NO_TRADE / NO_W2_RUNTIME / NO_W3_WRITE / NO_PRODUCTION / NO_PRIVATE_DATA** 继续锁定。

## R144 release binding

- Issue: `#406`
- Task: `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144`
- Route epoch: `144`
- Executor: `CODEX`
- Reviewer: `GPT_INDEPENDENT_REVIEWER`
- Planned implementation branch: `codex/r144-control-tower-gpt-worker-first-class`
- Task brief: `coordination/TASK-BRIEFS/CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144.yaml`
- Route: `coordination/ROUTES/CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144.yaml`
- Architecture decision checkpoint: Issue #406 comment `5340334185`
- Source blocker: R143 activation PR #405 / Review `4970596508`

## 下一关

先让本 activation candidate 通过 exact merge-ref 的 Control Tower 3.11/3.13、Work Claim、projection 与 authorization-witness 验证。只有 activation 被独立核验并 canonicalize 后，Codex 才能按 Issue #406/Route R144 创建 implementation branch 与 Draft PR。R144 implementation 必须独立 GPT exact-head Review，不得 self-review/self-merge。R144 merge 后再 fresh preflight 恢复 R143；不得自动启动 W2。
