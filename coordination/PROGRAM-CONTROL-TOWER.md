# AI系统 Program Control Tower

<!-- CONTROL_TOWER_AUTOGEN:START -->
## 自动同步快照（机器生成区）

- Registry: `AI-SYSTEM-PARALLEL-PROGRAM-LANES-0001`
- as_of: `2026-08-14T20:49:00+08:00`
- Foundation structural check: **PASS**
- Lane release decision: **HOLD_BY_USER**
- User-held lanes: `LANE-A-HARNESS-INTEGRATION, LANE-B-A-SHARE-REMEDIATION`

### Agent routes

| Agent | task_id | epoch | status | execution_allowed | Issue / PR |
|---|---|---:|---|---|---|
| CODEX | `CODEX-GPT-SECOND-BRAIN-COGNITIVE-CLOSED-LOOP-FUSION-P2-2-EPISTEMIC-MATERIALITY-HARDENING` | 120 | `READY_REMEDIATION` | `true` | #305 / #307 |
| QCLAW | `QCLAW-P2-RETRIEVAL-ADVERSARIAL-BENCHMARK-R60` | 60 | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | `false` | #296 / #304 |
| WORKBUDDY | `WORKBUDDY-PAUSED-COMPUTE-UNAVAILABLE-UNTIL-AFTER-2026-07-28` | 15 | `PAUSED_COMPUTE_UNAVAILABLE` | `false` | #89 / #97 |

### Program lanes

| Lane | desired | observed | heavy | next gate |
|---|---|---|---|---|
| `LANE-A-HARNESS-INTEGRATION` | `PAUSED` | `RESEARCHED_NOT_IMPLEMENTED` | `false` | CONTROL_TOWER_FOUNDATION_SAFE_TO_RELEASE |
| `LANE-B-A-SHARE-REMEDIATION` | `PAUSED` | `PREPARING_NOT_STARTED` | `false` | CONTROL_TOWER_FOUNDATION_SAFE_TO_RELEASE |
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `ACTIVE` | `ACTIVE` | `true` | Complete exact P2.2 remediation and GPT review before later P2.3/P2.4 or production bridge work. |

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
| `LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | `ACTIVE_IMPLEMENTATION` | `CODEX` | `HEAVY_IMPLEMENTATION` | 3 paths | epoch 120 · #305/#307 |

### Pairwise current-claim collision scan

| Pair | level | reason |
|---|---|---|
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-B-A-SHARE-REMEDIATION` | **O1** | `READ_READ` |
| `LANE-A-HARNESS-INTEGRATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O1** | `READ_READ` |
| `LANE-B-A-SHARE-REMEDIATION ↔ LANE-C-SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP` | **O1** | `READ_READ` |

<!-- CONTROL_TOWER_CLAIMS_AUTOGEN:END -->

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `boundary: NO_TRADE`

## 当前正式节奏

用户已明确决定：**先把Control Tower框架做到可安全放行，再启动另外两条线。**

因此在最终Foundation dry-run之前，不需要给Harness窗口或A股窗口发送启动提示词，也不允许它们进入正式执行。

Control Tower现在把“窗口开始工作”和“进入运行时代码实施”拆成两道权限：

- **PROPOSAL_ONLY**：只允许研究、设计、缺陷账本、PoC合同和任务包，并且只能写各自隔离的proposal root；
- **ACTIVE_IMPLEMENTATION**：必须另有正式Agent route、exact write paths/interfaces/authority claims、O0-O4复扫和commit-time authorization witness。

## 为什么先暂停A/B

如果多个窗口只靠自然语言自行理解规则，仍可能出现旧状态、共享mutable interface、同一Agent重复分配、commit前route变化、公告板与ACTIVE route漂移等问题。

因此采用“先塔台、后放行”，并新增机器可读 `LANE-WORK-CLAIMS.yaml`，做到**没有Work Claim就没有durable runtime write权限**。

## 放行门

Lane A和Lane B只有在以下条件满足后才能从PAUSED进入安全启动：

1. Program Lane与per-agent ACTIVE route reconciliation机械化并有测试；
2. `STALE_VIEW`检测可靠执行；
3. O0-O4 path/interface/authority冲突检测有targeted regression；
4. per-agent WIP与本机heavy-resource限制有可执行检查；
5. Work Claim明确实际读/写面、接口、权威和资源；
6. durable write前重新验证route + claim + hold/WIP/overlap policy authorization witness；
7. Markdown公告区由canonical自动推导并由CI检查，不成为第二份真相；
8. GPT完成三线dry-run并明确给出放行等级。

放行等级分开：

- `SAFE_TO_RELEASE_PROPOSAL_ONLY`：A/B可以开始研究设计，但不能改共享runtime；
- `SAFE_TO_RELEASE_IMPLEMENTATION`：某一条线获得正式实施route后，才允许按其Work Claim修改代码；
- `NOT_READY`：继续hold。

## 已发现的历史状态漂移

| 旧聚合视图 | 问题 | 当前处理 |
|---|---|---|
| `ACTIVE-THREE-AGENT-COORDINATION.yaml` | 仍显示旧Codex/QCLAW状态 | `STALE_VIEW`，不得覆盖最新per-agent route |
| `PROGRAM-INDEX.yaml` | current control仍停留旧基线 | 历史程序基线，其current-status字段不作为今日路由真源 |
| `ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml` | 旧执行序列 | 历史记录，不作为当前调度 |

## WIP硬边界

- Program战略Lane最多3条登记；
- Codex最多1条active execution route；
- QCLAW最多1条active execution route；
- WorkBuddy最多1条active execution route；
- 本机重计算阶段最多1个；
- A股业务纵向切片最多1个；
- 同一个canonical对象最多1个writer；
- nested parallelism禁止；
- proposal-only不能借研究名义写runtime。

## Control Tower不是谁

它不是新的第二大脑、任务路由器、W14、交易引擎、风险/概率权威或DeepSeek Harness本身。

它是整个系统的交通塔台：先确认跑道、航线、作业领空、优先级和冲突，再放行其他飞机。✈️

## 当前下一步

1. **Lane C**：继续当前Codex P2.2，不被#310抢占。
2. **Control Tower Foundation**：完成exact-head CI、authorization witness、双自动投影和三线dry-run。
3. **Lane A / Lane B**：仍保持用户hold，不自动启动。
4. Foundation通过后，GPT只先判定是否允许A/B进入`PROPOSAL_ONLY`；任何runtime实施仍需独立新route和新的Work Claim复扫。

## 相关canonical

- `coordination/ACTIVE-PROGRAM-LANES.yaml`
- `coordination/GOVERNANCE/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-PROTOCOL-v1.0.yaml`
- `coordination/BLUEPRINTS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-BLUEPRINT-v1.0.md`
- `coordination/SKILLS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-SKILL-v1.0.yaml`
- `coordination/CONTROL-TOWER/LANE-WORK-CLAIMS.yaml`
- `coordination/CONTROL-TOWER/RELEASE-GATE.yaml`
- Issue #310
