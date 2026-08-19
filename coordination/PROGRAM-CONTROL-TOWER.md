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
| `GPT-WORKER-R143-PROGRAMMING-1` | `GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143` | 143 | `RESERVED_NON_EXECUTABLE` | `false` | `GPT-5.6 Sol` | #404 / #410 |

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
| `LANE-B-A-SHARE-REMEDIATION` | `RESERVED_IMPLEMENTATION_NON_EXECUTABLE` | `GPT_ENGINEERING_WORKER` | `LIGHT_TO_MEDIUM_IMPLEMENTATION_RESERVATION` | 5 paths | epoch 143 · #404/#410 · slot `GPT-WORKER-R143-PROGRAMMING-1` |
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
> **执行真源不是本页**。Agent 当前能否执行，以 canonical `ACTIVE-*` route、GPT worker slot、Work Claim、Release Gate 和 fresh authorization witness 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R144 已完整收口**：implementation PR #408 与 post-merge closeout PR #409 均已独立审核并合并；R144 Codex lease 为历史非执行态。
- **Signal Tower 已完成 fresh post-R144 preflight**：`GLOBAL_SHALLOW → DELTA → TARGETED_DEEP → CONDITIONAL_RESEARCH(not required for activation) → RELEASE_DECISION`，结果仅允许创建 R143 非执行 reservation candidate。
- **PR #410 只做 reservation，不是 runtime activation**：`GPT-WORKER-R143-PROGRAMMING-1` 当前 `activation_state=RESERVED`、`execution_allowed=false`，Lane-B Work Claim 为 `RESERVED_IMPLEMENTATION_NON_EXECUTABLE`。
- **编程1现在仍不能写 W2 runtime**：PR #410 即使 CI 绿，也必须先独立审核并由用户决定是否 merge。merge 后还要从 then-current main 创建真实 runtime Draft PR，再通过单独的 final ACTIVE gate 把 slot/claim exact-bind 到那个 runtime PR。
- **旧 PR #405 永久不能作为当前激活入口原样继续**：它是 pre-R144 stale candidate，当前 activation 必须基于 post-R144 canonical main。
- **GPT Engineering Worker first-class registry 保持 canonical**：编程1/编程2只是 slot/provenance，编程2不得与编程1共享 mutable W2 writer surface。
- **Signal Tower 正常 on-demand 能力继续可用**：Signal != Task，normal mode 不要求 daemon/scheduler。
- **NO_TRADE / NO_ACCOUNT_ORDER_FUND / NO_PRODUCTION_PRIVATE / NO_W3_WRITE / NO_SIGNAL_TOWER_RUNTIME_WRITE / NO_SECOND_A_SHARE_RULE_AUTHORITY** 继续锁定。

## R143 reservation binding

- Issue: `#404`
- Task: `GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143`
- Route epoch: `143`
- Intended executor: `GPT_ENGINEERING_WORKER` / 编程1
- Worker slot: `GPT-WORKER-R143-PROGRAMMING-1`
- Reservation PR: `#410`
- Reservation branch: `gpt/r143-post-r144-fresh-activation`
- Base main: `12aab49dbffcd06214d6c5dae5917dff9b548595`
- Preflight receipt: `coordination/CONTROL-TOWER/GLOBAL-RECONCILIATION-RECEIPT-R143-POST-R144-ACTIVATION.yaml`
- Old PR #405: `STALE_PRE_R144 / DO_NOT_MERGE_AS_IS`

## 下一关

先让 PR #410 在 exact head 上通过 Program Control Tower Python 3.11/3.13、worker registry、Work Claim、projection 与 authorization-witness 验证，再交给独立 GPT exact-head Review。若且仅若用户随后授权并合并 reservation，才创建真实 runtime Draft PR。最终 runtime 执行权必须由另一个基于 then-current main 的 ACTIVE gate 将同一 worker slot、Work Claim、Issue/task/epoch、runtime PR/branch 和 fresh authorization witness 原子绑定；在那之前编程1不得修改 W2 runtime。
