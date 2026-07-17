# 元方法论·目标模式自治系统 — 系统蓝图（v0.1 最小闭环种子）

> 本文是 `meta-method-goal-mode` 技能的系统蓝图。
> 状态：最小可运行闭环种子已落地（见 ROADMAP.md 第 1 轮）。
> 未做完的能力一律标 `Interface` / `Mock` / `TODO` / `Future Roadmap`，绝不停留在"计划"。

---

## 0. 问题陈述（用户原话提炼）

> 想做一个像 Codex 那样：我提一个想法，你用**元方法论**把它映射一遍——
> 我知道我说了的 + 我知道但我没说的 + 我不知道但我看得懂的 + 我不知道且我看不懂的，
> 全部整合成一套映射关系的技能。然后出系统蓝图，上网找改进/联动/学术论文/机构量化等
> 高质量文章深度学习，定制方案，按清单一步步完成。每步可运行/可测试/可复盘/可扩展，
> 没做完标清楚，**不许假装完成**。**最重要：无需人工干预，能持续不断自己跑**（类 Codex /goal）。

本质 = 一个**元层调度器**：把"想法"编译成"知识地图 + 自治执行循环"。

---

## 1. 研究综述（真实联网，2026-07-11）

### 1.1 Codex `/goal` 长时域模式（核心对标）
来源：OpenAI 官方介绍、Tencent Cloud 开发者文章、CSDN 多篇社区逆向。
四层实现（直接可借鉴）：
1. **持久化**：目标作为独立状态存（Rust 模型 + DB 表），与对话历史分离；`/compact` 压缩不破坏目标，`resume` 续跑。
2. **运行时延续**：每轮空闲后自动注入 `continuation.md`，模型自决下一步，无需人工催。
3. **完成审计**：想标"完成"前，必须把目标映射成清单逐条核对证据，不确定=未完成。
4. **Token 预算**：烧到上限不裸停，软停止并输出进度报告。
> 本系统用「第二大脑 `/api/goal` 状态机 + WorkBuddy 自动化」复刻这四点。

### 1.2 Ralph Loop / Loop Engineering
来源：CSDN《Ralph Loop 与前沿研究综述》。
核心：bash 循环 + 外部状态持久化 + **可验证停止条件**（把"完成判定"从模型主观转移到外部）。
报告称约 $297 成本完成 $5万 开发任务，通宵无人值守。
> 本系统的 `ROADMAP.md` + 自动化 rrule = Ralph Loop 的 WorkBuddy 版。

### 1.3 Reflexion / Voyager / Self-Refine（经验沉淀）
来源：juejin《Loop Engineering》、diors.tech、yudesk.dev。
- Reflexion：失败→自然语言反思→写入记忆→重试（跨轮保存经验）。
- Voyager：成功行为沉淀为**可执行技能库**，未来复用组合（关键中间层）。
- 启示：自改进 agent 先要"会写工作日志的工程师"，而非"每晚偷偷训练模型"。
> 本系统的「9 点迭代报告 + `/api/evolve` MAPE-K」即此闭环；`/api/knowledge-graph` 即技能库。

### 1.4 Agentic Harness 五层（生产级自改进架构）
来源：subagentic.ai / Adaline Labs（2025-10 Airbnb Data Flywheel 同思路）。
五层：Instructions / Tools / Retrieval / Orchestration / **Evaluators**。
> Evaluators 是多数团队跳过、却把静态 agent 变自改进的关键层。本系统的「validator 脚本 + 9 点报告」即轻量 Evaluator。

### 1.5 Cynefin 决策框架（映射的方法论底座）
来源：Snowden（IBM, 1999）。五域：Clear/Complicated/Complex/Chaotic/Confused。
- 有序域（Clear/Complicated）：`sense–categorize / analyze–respond`。
- 复杂域（Complex）：`probe–sense–respond`。
- 混沌域（Chaotic）：`act–sense–respond`。
> 直接用于决定四象限各格的处理动作（见 SKILL.md 第一节）。

### 1.6 动态任务分解（TDAG / 综述）
来源：ScienceDirect TDAG(2025)、CSDN《Agent 任务拆解与反思机制综述》。
- 子任务数 **3–10** 最优（兼顾可执行性与协调开销）。
- 静态分解易 error propagation；动态分解 + 实时生成子 Agent 更鲁棒。
> 本系统每轮只做 1 件事 = 最极端的"动态单步"，规避 error propagation。

### 1.7 自进化评测基准（Frontier-Eng 等）
来源：机器之心 / arXiv 2604.12290。
把 Agent 扔进真实工程问题，测其**持续优化**能力（非单次做题）。
> 本系统的「每轮 9 点报告 + validator」是单 agent 版的轻量持续评测。

---

## 2. 四象限知识映射（用户定义的方法论 — 本系统唯一新内核）

```
              能表达/理解 ─────────── 不能表达/理解
            ┌─────────────────────┬─────────────────────┐
   已 知    │ Q1 已知·已说         │ Q2 已知·未说         │
            │ 用户明说的需求/约束   │ 隐含假设/环境/偏好/   │
            ├─────────────────────┼─────────────────────┤
   未 知    │ Q3 未知·可懂         │ Q4 未知·不懂         │
            │ 不知但能研究掌握     │ 看不懂的盲点 → 必标   │
            │ → 联网深度学习后纳入 │ TODO/Interface/Mock  │
            └─────────────────────┴─────────────────────┘
```
- 与 `pragmatic-blueprint` 的区别：后者是 2 格（已知/未知）；本系统是 **2x2 精确格**，多出的两轴（已说/未说、可懂/不懂）正是用户强调的"我知道但没说的"和"我不知道且看不懂的"。
- Q4 是**反假装完成**的硬锚点：任何进入 Q4 且无法验证的内容，必须显式降级为 `Interface/TODO/Mock/Future Roadmap`。

---

## 3. 系统架构（分层）

```
┌──────────────────────────────────────────────────────────┐
│ L1 Interface       用户想法入口 + 本轮指令（自动化注入）    │
├──────────────────────────────────────────────────────────┤
│ L2 Mapping Engine  四象限映射（Q1–Q4）★本技能核心          │
├──────────────────────────────────────────────────────────┤
│ L3 Research         联网深度学习（Q3，WebSearch/WebFetch） │
│ Synthesizer                                                   │
├──────────────────────────────────────────────────────────┤
│ L4 Blueprint        系统蓝图 + 数据流向图                  │
│ Generator                                                     │
├──────────────────────────────────────────────────────────┤
│ L5 Iteration Loop   每轮 9 点报告 + 最小闭环              │
├──────────────────────────────────────────────────────────┤
│ L6 Persistence      ★第二大脑 /api/goal（状态机/里程碑）   │
├──────────────────────────────────────────────────────────┤
│ L7 Self-Evolution   ★第二大脑 /api/evolve（MAPE-K/熔断）   │
├──────────────────────────────────────────────────────────┤
│ L8 Orchestration    ★第二大脑 /api/agent（决策审计）       │
├──────────────────────────────────────────────────────────┤
│ L9 Autonomy Driver  WorkBuddy 自动化（rrule 触发续跑）     │
└──────────────────────────────────────────────────────────┘
        ★ = 直接复用第二大脑已有原语，不重建
```

### 数据流向
```
用户想法 → L2 四象限映射 → L3 研究补充 Q3 → L4 蓝图
   → L5 每轮取 1 个改进 → 实现 + L5 validator 测试
   → 写 ROADMAP.md（L5 持久化副本）
   → best-effort L6 /api/goal milestone（权威持久化）
   → best-effort L7 /api/evolve/cycle（自进化）
   → L9 自动化定时触发下一轮
```

---

## 4. 最小闭环范围（v0.1 已落地）

| 模块 | 状态 | 说明 |
|---|---|---|
| 技能定义 SKILL.md | ✅ 完成 | 四象限 + 9 点协议 + 联动表 |
| 系统蓝图 BLUEPRINT.md | ✅ 完成 | 研究综述 + 架构 + 数据流向 |
| 四象限映射（bootstrap 想法） | ✅ 完成 | 见 ROADMAP.md |
| 闭环验证器 meta_goal.py | ✅ 完成 | validate/scaffold/status |
| 测试 test_meta_goal.py | ✅ 完成 | 断言通过/失败路径 |
| 第 1 轮 9 点报告 | ✅ 完成 | ROADMAP.md Round 1 |
| 自治自动化（WorkBuddy） | ✅ 创建 | rrule 定时触发续跑 |
| L6 /api/goal 真实接入 | 🔶 Interface | 端点已知，本轮回合内尝试，待确认 |
| L7 /api/evolve 每轮自动调用 | 🔶 Interface | 端点已知，未接线 |
| L8 /api/agent 决策审计 | 🔶 Interface | 端点已知，未接线 |
| 四象限节点自动入库 knowledge-graph | 🔶 TODO | 未做 |
| 无限自治 token 预算/熔断细化 | 🔶 Future Roadmap | 依赖 L6/L7 实测 |
| MCP(tdx/westock) 在自动化上下文可用性 | 🔶 Future Roadmap | 待验证 |
| Q4 递归"承认无知"协议 | 🔶 Future Roadmap | 策略层设计，未落地 |

---

## 5. 风险与对策

| 风险 | 等级 | 对策 |
|---|---|---|
| 自动化频繁跑烧 token | 中 | ROADMAP 顶部 PAUSE/COMPLETE 标志 + 轮次上限；evolve/mode 联动熔断 |
| 第二大脑未运行 → L6 接入失败 | 低 | ROADMAP.md 为权威副本；L6 best-effort 不阻塞 |
| 假装完成 | 高 | Q4/未完成强制标 TODO/Interface/Mock；validator 检查 |
| MCP 工具在自动化上下文不可用 | 中 | Future Roadmap 验证；本轮不依赖 |
| 跑飞/偏离目标 | 中 | 每轮只 1 件事 + 9 点审计 + 完成证据核对 |

---

## 6. 下一步（非本次范围，列清单）

- Round 2：把 L6 `/api/goal` 真正接上（确认 create 路由 + 每轮 milestone 自动写入）。
- Round 3：L7 `/api/evolve/cycle` 每轮后自动调用 + 模式联动。
- Round 4：L8 `/api/agent/orchestrate` 用于重大决策审计。
- Round 5：四象限节点自动写入 `/api/knowledge-graph`。
- Round N：token 预算/熔断细化、MCP 可用性验证、Q4 承认无知协议。
