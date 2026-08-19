# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-19T17:11:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **LANE_B_W2_S1_USER_RELEASED**
- User-held lanes: NONE

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GLOBAL-SIGNAL-TOWER-R142-RETROSPECTIVE-SIGNAL-INTAKE-BRIDGE` | 142 | `DONE_HISTORICAL` | `false` | #393 / #400 |
| GPT_ENGINEERING_WORKER | `GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143` | 143 | `READY_AFTER_ACTIVATION_MERGE` | `true` | #404 / implementation PR pending |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `DONE_HISTORICAL` | `false` | #296 / NONE |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `SIGNAL_TOWER_ON_DEMAND_OPERATIONAL / NO_ACTIVE_IMPLEMENTATION` | `false` | ON_DEMAND_SIGNAL_TOWER_OPERATION / FUTURE_IMPLEMENTATION_REQUIRES_NEW_GOVERNED_DECISION |
| `LANE-B-A-SHARE-REMEDIATION` | `ACTIVE` | `W2_S1_R143_ACTIVE_BOUNDED_IMPLEMENTATION` | `false` | G0_CONCRETE_W2_C2_AUTHORITY_INVENTORY / SCHEMA_MATERIALIZATION_GATE_IF_REQUIRED |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `DONE` | `DONE` | `false` | REOPEN_ONLY_FOR_BUG_SECURITY_CONTRACT_DEFECT_PROVEN_REGRESSION |

<!-- CONTROL_TOWER_AUTOGEN:END -->

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:START -->
## 自动同步作业领空（机器生成区）

- Work claims: `PROGRAM-CONTROL-TOWER-LANE-WORK-CLAIMS-0001`
- Claim structural check: **PASS**
- Active A-share vertical slices: **1 / 1**
- Same W2/C2 canonical writers: **1 / 1**

| Lane | claim state | agent | resource | write surface | route binding |
|---|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |
| `LANE-B-A-SHARE-REMEDIATION` | `ACTIVE_BOUNDED_IMPLEMENTATION` | `GPT_ENGINEERING_WORKER` | `BOUNDED_W2_RESEARCH_RUNTIME` | Phase-2 offline research W2 slice only | `GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143` |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `CLOSED_NO_ACTIVE_IMPLEMENTATION` | `NONE` | `NO_ACTIVE_IMPLEMENTATION` | NONE | NONE |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O0** | `LANE_A_NO_IMPLEMENTATION_WRITE_SURFACE` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `NO_MATERIAL_OVERLAP` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O0** | `LANE_B_W2_ONLY / W3_W10_READ_ONLY` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各 Agent 看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Agent 当前能否执行，以 canonical route、Work Claim 和更高优先级用户指令为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

- **R60 已是历史完成态**：implementation 与 control-plane closeout 已完成，没有 active QCLAW R60 executor 或 Work Claim。
- **R142 已全生命周期关闭**：implementation PR #400 与 closeout PR #403 均已合并；Issue #393 已 completed；Lane-A implementation lease/claim 已释放。
- **Signal Tower 正常运行**：`ON_DEMAND_PREFLIGHT_AVAILABLE`，Signal != Task；正常模式不要求 daemon。
- **Lane-B Master Audit 已合并**：PR #402 accepted/merged，正式缺陷主档已进入 canonical main；合并审计本身没有自动授权 implementation。
- **用户随后明确授权 W2 第一切片**：`开始编程1 W2 第一切片。`
- **R143 是当前唯一 A股 implementation slice**：Issue #404，执行者 `GPT_ENGINEERING_WORKER`，只写 W2 Phase-2 offline-research 受限表面。
- **W2/C2 单一权威保持不变**：`AShareRuleSnapshot` owner=W2，`C2_A_SHARE_RULE_SNAPSHOT` write policy=`SINGLE_WRITER_READ_ONLY_CONSUMERS`；禁止第二规则真源。
- **第一关不是直接重写规则**：编程1先执行 G0 concrete authority inventory。若需要新 canonical schema/object identity，必须停在 `SCHEMA_MATERIALIZATION_GATE` 等 GPT 独立审查。
- **硬边界继续有效**：NO_TRADE、无账户/订单/资金、无生产/私有数据、无 W3/Signal Tower 写、无 W5/W7/W13 implementation、无 L2/tick/order/queue ingestion、无 successor 自动释放。

## R143 current binding

- Issue: `#404`
- Task: `GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143`
- Route epoch: `143`
- Slice: `LB-S1-W2-PIT-RULE-INVENTORY-REPLAY-GATE`
- Executor role: `GPT_ENGINEERING_WORKER`
- Model: `GPT-5.6 Sol`
- Reviewer: `GPT_INDEPENDENT_REVIEWER`
- Route: `coordination/ROUTES/GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143.yaml`
- Task brief: `coordination/TASK-BRIEFS/GPT-LANE-B-W2-S1-PIT-RULE-INVENTORY-REPLAY-GATE-R143.yaml`
- Planned implementation branch: `gpt/lane-b-w2-s1-pit-rule-inventory-replay-gate`
- Completion signal: `LANE_B_W2_S1_PIT_RULE_INVENTORY_REPLAY_GATE_READY_FOR_GPT_REVIEW`

## R143 first-slice invariants

1. Effective point-in-time A-share rule snapshot, not static ST/non-ST constants.
2. `PRICE_VALIDITY != ORDER_FILLABILITY`.
3. `limit_reference_price` requires governed provenance/effective-rule binding.
4. Old settled inventory remains sellable after same-day top-up; same-day lot remains locked.
5. Settlement advances by next **TRADING DAY**, not naive calendar day.
6. Unsupported market/session/rule state fails closed; BSE is never silently defaulted to SSE/SZSE parameters.
7. Existing costs/deterministic replay stay green; zero impact remains an explicit baseline assumption, not economic validation.

## 下一关

编程1读取 canonical Issue #404 + R143 Task Brief + R143 route + Lane-B Work Claim，fresh reconcile `main`，从 canonical main 创建新 implementation branch/Draft PR，然后先执行 **G0 concrete W2/C2 authority inventory**。如果需要创建新的 canonical `AShareRuleSnapshot` schema/object identity，立即 STOP 并回传 `SCHEMA_MATERIALIZATION_GATE`; 否则按 G1-G5 完成 bounded implementation、exact-head CI、资源回收和 handoff，等待独立 GPT Review。不得 self-review 或 merge。
