# AI系统 Program Control Tower

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `as_of: 2026-08-14 20:12 +08:00` · `boundary: NO_TRADE`

## 一眼看懂

| Program Lane | 状态 | 现在谁在工作 | 当前阶段 | 最大重叠点 | 下一Gate |
|---|---|---|---|---|---|
| **A · DeepSeek Harness Integration** | 🟡 READY / 尚未实施 | 暂无执行Agent | 研究完成，PoC前 | 与Lane C共享W3/W8/W9/W10、Context/Skill/Runtime | 先做隔离PoC合同，不抢当前Codex |
| **B · A股交易系统缺陷改进** | 🟡 PREPARING / 尚未启动 | 暂无执行Agent | 缺陷归并与首切片前 | 与A共享Guard/Observability；与C共享W3/W9/W10/W12 | 冻结缺陷总账和一个有界首修切片 |
| **C · 第二大脑×GPT多端/认知闭环** | 🟢 ACTIVE | Codex | P2.2 epistemic/materiality hardening | 正在改ContextBundle语义，A线不可直接耦合 | 完成Issue #305 / PR #307并GPT验收 |

## 当前Agent执行状态

| Agent | 当前执行真源 | 当前状态 | Issue / PR | 备注 |
|---|---|---|---|---|
| **Codex** | `ACTIVE-CODEX-TASK.yaml` | `READY_REMEDIATION` | #305 / #307 | epoch 120；当前唯一重实施主线 |
| **QCLAW** | `ACTIVE-QCLAW-TASK.yaml` | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | #296 / #304 | 2026-08-14剩余额度保护，今晚不继续 |
| **WorkBuddy** | `ACTIVE-WORKBUDDY-TASK.yaml` | `PAUSED_COMPUTE_UNAVAILABLE` | #89 / #97 | 未获GPT重新释放，不执行 |

## ⚠️ 已发现的状态漂移

| 旧聚合视图 | 问题 | 当前处理 |
|---|---|---|
| `ACTIVE-THREE-AGENT-COORDINATION.yaml` | 仍显示8月7日附近的旧Codex/QCLAW状态 | `STALE_VIEW`，不得覆盖最新per-agent route |
| `PROGRAM-INDEX.yaml` | current control仍停留Issue #72基线 | 保留历史程序基线，但其current-status字段不能作为今日执行真源 |
| `ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml` | `as_of: 2026-07-23` | 历史执行序列，不作为当前调度 |

## 三线当前重叠地图

```text
Lane A Harness
   ├── W8 Agent Runtime ─────────────┐
   ├── W9 Observability/Learning ─┐  │
   ├── W7 Guard/Risk             │  │
   └── W3/W10 Context  ──────┐   │  │
                              │   │  │
Lane B A股修复                 │   │  │
   ├── W2/W4/W5               │   │  │
   ├── W7/W9 ─────────────────┼───┘  │
   └── W12/W13 ───────────────┤      │
                              │      │
Lane C 认知闭环                │      │
   ├── W3/W10 ────────────────┘      │
   ├── W9/W12                        │
   └── W8 ───────────────────────────┘
```

### 当前并行判断

**可以三线同时“存在和推进”，但不能三线同时重实施。**

当前最安全组合：

```text
Lane C = Codex重实施
Lane A = Harness PoC合同 / 外部研究 / adapter设计
Lane B = 缺陷总账 / 数据与证据审计 / 首修切片设计
```

直到Lane C的相关共享接口稳定，再释放A或B的下一条重执行route。

## WIP硬边界

- Program战略Lane：最多3条同时open；
- Codex：最多1条active execution route；
- QCLAW：最多1条active execution route；
- WorkBuddy：最多1条active execution route；
- 本机重计算阶段：最多1个；
- A股首批业务纵向切片：最多1个；
- 同一个canonical对象：最多1个writer；
- nested parallelism：禁止。

这意味着“3条线并行”是**目标并行**，不是**资源无上限并行**。

## 状态词

`PROPOSED → READY → ACTIVE → REVIEW → BLOCKED/PAUSED → DONE`

异常不是正常状态，而是独立报警：

`STALE_VIEW / AUTHORITY_CONFLICT / PATH_OVERLAP / INTERFACE_OVERLAP / DEPENDENCY_BLOCKED / WIP_EXCEEDED / DOUBLE_BOOKED / RESOURCE_COLLISION / SEMANTIC_VERSION_SKEW / COMMIT_AUTHORITY_STALE`

## 以后GitHub Project应该怎么显示

如果后续用GitHub Project做真正的UI，建议仍只做**一个Project，多视图**：

| View | 用途 |
|---|---|
| Executive Overview | 三线状态、风险、下一Gate |
| Active Now | 真实正在执行的Issue/PR |
| By Program Lane | Harness / A股 / 认知闭环 |
| By Agent | 找double booking和容量 |
| Dependencies & Blocked | 依赖图、blocked age |
| Risk & Gates | O2/O3/O4重叠与人门 |
| Roadmap | 真实日期和阶段 |
| Recently Completed | Throughput / Cycle Time |
| Learning Queue | AMED发现、Skill候选、UNKNOWN |

Project只显示，不能反过来覆盖ACTIVE route。

## 应持续看的流指标

自动化后至少记录：

- **WIP**：开了多少还没完成；
- **Work Item Age**：一个未完成任务活了多久；
- **Blocked Age**：卡住多久；
- **Throughput**：真正完成多少；
- **Cycle Time**：从开始到完成多久。

有足够同类历史后才估算SLE，不先拍“几天必须完成”。研究、设计、实现、审计、修复必须分开统计。

## 四状态知识映射入口

以后用户让系统学习一个新框架、新治理方法、新量化机制或新工作流时，总控Skill会主动分成：

| 状态 | 含义 |
|---|---|
| `KNOWN_SAID` | 用户明确说过，直接保留来源 |
| `KNOWN_UNSAID_INFERRED` | 用户没说，但系统可高置信推断，必须标Inference |
| `UNKNOWN_BUT_ACCESSIBLE` | 用户没学过但用现有概念一解释就能懂 |
| `UNKNOWN_REQUIRES_SCAFFOLDING` | 需要先搭前置概念，不能直接扔术语 |

## Control Tower不是谁

它不是：

- 新的第二大脑；
- 新的任务路由器；
- 新的W14；
- 新的交易引擎；
- 新的风险/概率权威；
- DeepSeek Harness本身。

它是**全系统的交通塔台**：知道跑道上有谁、谁准备起飞、谁必须等、哪两架会冲突、哪份航班表已经过期。✈️

## 当前下一步队列

1. **Lane C**：继续完成当前Codex P2.2，不被#310抢占。
2. **Lane A**：形成Harness隔离PoC，优先验证W8/W9/W7运行价值和与W3/W10接口边界。
3. **Lane B**：把最近发现的“解释先于证据、主动探索不足、实时/点时数据缺口、交易因果归因”等缺陷收敛成一个Defect Ledger，再选一个首修切片。
4. **#310自动化**：未来Codex任务实现scanner/reconciler、GitHub Project同步、flow metrics和regression；只有GPT显式发布route后执行。

## 相关canonical

- `coordination/ACTIVE-PROGRAM-LANES.yaml`
- `coordination/GOVERNANCE/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-PROTOCOL-v1.0.yaml`
- `coordination/BLUEPRINTS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-BLUEPRINT-v1.0.md`
- `coordination/SKILLS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-SKILL-v1.0.yaml`
- Issue #310
