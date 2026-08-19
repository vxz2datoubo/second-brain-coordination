# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-20T02:32:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144` | 144 | `DONE_HISTORICAL` | `false` | #406 / #408 |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `DONE_HISTORICAL` | `false` | #296 / #None |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### GPT Engineering Worker slots

| slot | task_id | epoch | status | execution_allowed | model_id | Issue / PR |
|---|---|---:|---|---|---|---|
| _NONE_ | _no active GPT Engineering Worker slot_ | | | | | |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `SIGNAL_TOWER_ON_DEMAND_OPERATIONAL / NO_ACTIVE_IMPLEMENTATION` | `false` | ON_DEMAND_SIGNAL_TOWER_OR_NEW_GOVERNED_TASK_RELEASE |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `W2_S1_R143_USER_RELEASE_RETAINED / AWAIT_FRESH_POST_R144_PREFLIGHT` | `false` | FRESH_SIGNAL_TOWER_CONTROL_TOWER_PREFLIGHT_THEN_NEW_R143_ACTIVATION |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Proposal-only release candidate: **ELIGIBLE_FOR_GPT_RELEASE_DECISION**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |
| `LANE-B-A-SHARE-REMEDIATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-B-A-SHARE-REMEDIATION` | NONE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各 Agent 看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Agent 当前能否执行，以 canonical `ACTIVE-*` route、GPT worker slot、Work Claim 和 fresh authorization witness 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R144 implementation 已 ACCEPTED + MERGED**：PR #408 合并 exact head `217a38e341b0c66864b67b549cdccf0be7757206`，merge commit `d9734f2db3f039167f0e3e32933392ae5571de13`。
- **本 closeout 候选只释放旧控制面租约**：R144 Codex route / Lane-A Work Claim 转为历史非执行态，不修改 R144 runtime 实现，不创建 successor execution authority。
- **GPT Engineering Worker first-class registry 已 canonical**：`coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml` 保留，当前 `worker_slots=[]`，没有任何 GPT worker 获得执行权。
- **Lane-B R143 用户授权意图保留但 runtime 继续 HOLD**：旧 PR #405 是 pre-R144 candidate，不能原样 merge；必须在 R144 closeout 后重新做 Signal Tower + Control Tower preflight，再建立 fresh slot/claim/witness。
- **Signal Tower 正常 on-demand 能力继续可用**：Signal != Task，normal mode 不要求 daemon/scheduler；正式 Task release 仍需 fresh preflight。
- **R142/R60 保持历史完成态**：不恢复旧 executor lease，不重开历史实现。
- **NO_TRADE / NO_W2_RUNTIME / NO_W3_WRITE / NO_PRODUCTION / NO_PRIVATE_DATA** 在 closeout 期间继续锁定。

## R144 closure binding

- Issue: `#406`
- Task: `CODEX-CONTROL-TOWER-GPT-ENGINEERING-WORKER-FIRST-CLASS-R144`
- Route epoch: `144`
- Implementation PR: `#408`
- Accepted exact head: `217a38e341b0c66864b67b549cdccf0be7757206`
- Independent final Review: `4975349444`
- Merge commit: `d9734f2db3f039167f0e3e32933392ae5571de13`
- Closeout branch: `gpt/r144-control-plane-closeout`
- Closure receipt: `coordination/CONTROL-TOWER/R144-GPT-WORKER-FIRST-CLASS-CLOSURE-RECONCILIATION.yaml`

## R143 下一关

R144 closeout 必须先通过 fresh exact-head Program Control Tower 3.11/3.13、Work Claim、worker registry、projection 与 authorization-witness 验证，再由独立 GPT 审核。closeout 未 merged 前不得启动 R143 runtime。closeout merged 后重新执行 `GLOBAL_SHALLOW → DELTA → TARGETED_DEEP → CONDITIONAL_RESEARCH(如需要) → RELEASE_DECISION`，随后才允许创建 fresh GPT worker slot、exact `ACTIVE_IMPLEMENTATION` Work Claim 和 authorization witness。旧 PR #405 不得未经重绑定直接 merge。
