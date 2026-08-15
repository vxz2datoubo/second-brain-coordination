# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-15T17:29:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GPT-SECOND-BRAIN-COGNITIVE-CLOSED-LOOP-FUSION-P2-4B-STRUCTURAL-ANALOGY` | 132 | `DONE` | `false` | #332 / #334 |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `ACTIVE` | `ACTIVE` | `false` | H0_FINAL_COMPATIBILITY_VERDICT_BEFORE_H1 |
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
| `LANE-A-HARNESS-INTEGRATION` | `HELD_PROPOSAL_ONLY` | `NONE` | `LIGHT_RESEARCH_DESIGN` | `coordination/PROPOSALS/PROGRAM-LANES/LANE-A-HARNESS-INTEGRATION` | NONE |
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
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

当前状态已经从“先建塔台、三线等待”进入下一阶段：

- **Lane C 第二大脑 Foundation：DONE**。P2.4B 已合并，#335 结论为 `CLOSED_WITH_BOUNDED_GAPS`；R132只保留为历史 tombstone，不再有Codex执行租约。
- **Lane A Harness × Cognitive OS：ACTIVE，但仅 PROPOSAL_ONLY**。用户已经明确启动 H0 架构设计；Draft PR #336 正在做总架构、机器合同、有效挑战、学习闭环、Harness Adapter 与验证体系。它没有 runtime route，也不占用 heavy implementation lease。
- **Lane B A股系统缺陷修复：继续 PAUSED**。除非用户另行启动，否则保持原 hold 与 `NO_TRADE`。

Control Tower继续把“可以研究设计”和“可以改运行时代码”拆成两道完全不同的权限：

- **PROPOSAL_ONLY**：只允许研究、架构、合同、评估、PoC任务草案，并限制在隔离 proposal root；
- **ACTIVE_IMPLEMENTATION**：必须另有全新的 Agent route、exact Work Claim、O0-O4/WIP复扫和 fresh authorization witness；
- **CLOSED_NO_ACTIVE_IMPLEMENTATION**：Lane 已完成当前实现阶段，释放 Agent、route、读写、接口和 authority 工作面，只保留 closure receipt。

## 为什么新增 Closed Work Claim 状态

此前 `LANE-WORK-CLAIMS.yaml` 的验证器只有：

- `ACTIVE_IMPLEMENTATION`
- `HELD_PROPOSAL_ONLY`

这无法真实表达“Foundation已经完成，而且当前没有任何执行租约”的 Lane C。继续写 ACTIVE 会制造幽灵租约；伪装成 HELD proposal 又会篡改真实生命周期。

因此 Control Tower 增加最小第三状态：

`CLOSED_NO_ACTIVE_IMPLEMENTATION`

其硬约束是：

- `execution_agent = null`
- `route_binding = null`
- 当前 read/write/interface/domain/authority work surfaces 全部为空
- 必须保留 durable `closure_receipt`
- future implementation 必须重新创建新的 ACTIVE route + Work Claim

这不是新业务能力，只是修复 Control Tower 无法表达正常完成态的合同缺陷。

## 当前 H0 门

Lane A 现在可以继续 H0 proposal architecture，但 H1 仍不得执行。

H1 之前必须满足：

1. Control Tower 当前状态 reconciliation PASS；
2. Work Claims PASS；
3. bulletin projection PASS；
4. authorization witness round trip PASS；
5. H0 static audit无 OPEN P0；
6. GPT给出 H0 final verdict；
7. H1 获得独立新 Work Claim / Agent route；
8. 本机 single-agent / single-heavy-stage / no-nested-parallelism 约束继续成立。

H1即使通过也**不会自动放行 H2 Harness runtime**。

## WIP硬边界

- Program战略Lane最多3条登记；
- Codex最多1条active execution route；
- QCLAW最多1条active execution route；
- WorkBuddy最多1条active execution route；
- 本机重计算阶段最多1个；
- A股业务纵向切片最多1个；
- 同一个canonical对象最多1个writer；
- nested parallelism禁止；
- proposal-only不能借研究名义写runtime；
- closed claim不能保留隐形读写/Agent租约。

## Control Tower不是谁

它不是新的第二大脑、Signal Tower任务路由器、W14、交易引擎、风险/概率权威或DeepSeek Harness本身。

它是整个系统的交通塔台：确认跑道、航线、作业领空、优先级、资源和冲突，再决定某个实现任务能不能起飞。✈️

## 当前下一步

1. 验证本次 Foundation closure reconciliation 的双Python targeted tests / reconciliation / Work Claim / projection / witness 全链路。
2. 若验证通过，合并前由GPT做 exact-head治理审计；不得因为 CI 绿就自动 merge。
3. 回到 Draft PR #336，重新运行 H0 final gate。
4. 只有 H0 final accepted，才发布 H1 contract-only synthetic skeleton 的新 Codex route。
5. Lane B保持 hold，真实交易始终未授权。

## 相关canonical

- `coordination/ACTIVE-PROGRAM-LANES.yaml`
- `coordination/ACTIVE-CODEX-TASK.yaml`
- `coordination/GOVERNANCE/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-PROTOCOL-v1.0.yaml`
- `coordination/BLUEPRINTS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-BLUEPRINT-v1.0.md`
- `coordination/SKILLS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-SKILL-v1.0.yaml`
- `coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml`
- `coordination/CONTROL-TOWER/RELEASE-GATE.yaml`
- Issue #310
- Issue #335
- Draft PR #336
