# AI系统 Program Control Tower

> **用途**：给用户、GPT和各Agent看的跨线路公告板 / 总控台。
>
> **执行真源不是本页**。Codex/QCLAW/WorkBuddy当前能否执行、执行什么，以远端最新 `ACTIVE-*.yaml` 为准。
>
> `control_tower_issue: #310` · `as_of: 2026-08-14 20:49 +08:00` · `boundary: NO_TRADE`

## 当前正式节奏

用户已明确决定：**先把Control Tower框架做到可安全放行，再启动另外两条线。**

因此现在不需要给Harness窗口或A股窗口发送启动提示词，也不允许它们进入正式执行。

| Program Lane | 状态 | 现在谁在工作 | 当前阶段 | 下一Gate |
|---|---|---|---|---|
| **A · DeepSeek Harness Integration** | ⏸️ PAUSED | 无执行Agent | 研究完成，PoC前 | `CONTROL_TOWER_FOUNDATION_SAFE_TO_RELEASE` |
| **B · A股交易系统缺陷改进** | ⏸️ PAUSED | 无执行Agent | 缺陷归并与首切片前 | `CONTROL_TOWER_FOUNDATION_SAFE_TO_RELEASE` |
| **C · 第二大脑×GPT多端/认知闭环** | 🟢 ACTIVE | Codex | P2.2 epistemic/materiality hardening | 完成当前Issue #305 / PR #307并GPT验收 |

## 为什么先暂停A/B

当前Control Tower已经有Program Lane、O0-O4重叠规则、WIP、Source precedence与Commit-time freshness设计，但自动scanner/reconciler、硬WIP validator和三线dry-run尚未完成。

如果此时让多个对话框自行理解规则并开始修改，仍可能出现：

- 一个窗口按旧状态工作；
- 两条线同时碰同一mutable interface；
- 同一Agent被重复分配；
- task开始时安全，但commit前route/authority已经变化；
- 人类公告板与真正ACTIVE route再次漂移。

因此当前采用“先塔台、后放行”。

## 放行门

Lane A和Lane B只有在以下条件满足后才能从PAUSED切回READY/ACTIVE：

1. Program Lane与per-agent ACTIVE route的reconciliation已经机械化定义并有测试；
2. `STALE_VIEW`检测可可靠执行；
3. O0-O4 path/interface/authority冲突检测有targeted regression；
4. per-agent WIP与本机heavy-resource限制有可执行检查；
5. durable write前会重新验证route epoch / authority / dependency；
6. Markdown/未来GitHub Project只作为投影，不再产生第二份手工真相；
7. GPT完成一次三线dry-run并明确给出：`SAFE_TO_RELEASE` 或 `NOT_READY`。

## 当前Agent执行状态

| Agent | 当前执行真源 | 当前状态 | Issue / PR | 备注 |
|---|---|---|---|---|
| **Codex** | `ACTIVE-CODEX-TASK.yaml` | `READY_REMEDIATION` | #305 / #307 | epoch 120；当前唯一重实施主线 |
| **QCLAW** | `ACTIVE-QCLAW-TASK.yaml` | `GPT_REVIEW_CHANGES_REQUIRED_PAUSED` | #296 / #304 | 当前不执行 |
| **WorkBuddy** | `ACTIVE-WORKBUDDY-TASK.yaml` | `PAUSED_COMPUTE_UNAVAILABLE` | #89 / #97 | 未获GPT重新释放，不执行 |

## 已发现的状态漂移

| 旧聚合视图 | 问题 | 当前处理 |
|---|---|---|
| `ACTIVE-THREE-AGENT-COORDINATION.yaml` | 仍显示旧Codex/QCLAW状态 | `STALE_VIEW`，不得覆盖最新per-agent route |
| `PROGRAM-INDEX.yaml` | current control仍停留Issue #72基线 | 只作为历史程序基线 |
| `ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml` | `as_of: 2026-07-23` | 历史执行序列，不作为当前调度 |

## 三线重叠地图

```text
Lane A Harness      ⏸ PAUSED
   ├── W8 Agent Runtime ─────────────┐
   ├── W9 Observability/Learning ─┐  │
   ├── W7 Guard/Risk             │  │
   └── W3/W10 Context  ──────┐   │  │
                              │   │  │
Lane B A股修复       ⏸ PAUSED │   │  │
   ├── W2/W4/W5               │   │  │
   ├── W7/W9 ─────────────────┼───┘  │
   └── W12/W13 ───────────────┤      │
                              │      │
Lane C 认知闭环      🟢 ACTIVE│      │
   ├── W3/W10 ────────────────┘      │
   ├── W9/W12                        │
   └── W8 ───────────────────────────┘
```

## WIP硬边界

- Program战略Lane可登记3条，但当前A/B被用户显式hold；
- Codex最多1条active execution route；
- QCLAW最多1条active execution route；
- WorkBuddy最多1条active execution route；
- 本机重计算阶段最多1个；
- A股业务纵向切片最多1个；
- 同一个canonical对象最多1个writer；
- nested parallelism禁止。

## Control Tower不是谁

它不是新的第二大脑、任务路由器、W14、交易引擎、风险/概率权威或DeepSeek Harness本身。

它是整个系统的交通塔台：先确认跑道、航线、优先级和冲突，再放行其他飞机。✈️

## 当前下一步

1. **Lane C**：继续当前Codex P2.2，不被#310抢占。
2. **Control Tower Foundation**：完成scanner/reconciler设计与可执行实现、targeted regression、WIP/资源门、commit freshness、projection同步和三线dry-run。
3. **Lane A / Lane B**：保持PAUSED，不发启动提示词，不正式执行。
4. Control Tower通过放行门后，由GPT重新判断A/B谁先获得下一条执行route，并给用户一份非常简单的启动指令。

## 相关canonical

- `coordination/ACTIVE-PROGRAM-LANES.yaml`
- `coordination/GOVERNANCE/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-PROTOCOL-v1.0.yaml`
- `coordination/BLUEPRINTS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-BLUEPRINT-v1.0.md`
- `coordination/SKILLS/AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-SKILL-v1.0.yaml`
- Issue #310
