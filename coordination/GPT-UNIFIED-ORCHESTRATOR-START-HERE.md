# GPT Unified Orchestrator — Start Here

这是未来新 GPT 窗口的稳定入口。聊天上下文可以丢，GitHub 当前 `main` 不能猜。

## 固定启动顺序

1. Fresh 读取 `vxz2datoubo/second-brain-coordination` 当前 `main`。
2. 读取：
   - `coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml`
   - `coordination/EXECUTION/PROJECT-REGISTRY.yaml`
   - 当前项目对应的 `coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml`
   - 当前 ACTIVE route / Issue / PR / exact head / CI / review。
3. 先判断用户当前是在：
   - 第二大脑
   - 交易系统
   - 实时互动电影游戏
   - AI 导演
   - 或跨项目任务。
4. 分类 S0–S5。
5. 决定执行载体：
   - GPT_DIRECT
   - WorkBuddy CLI Headless
   - WorkBuddy CLI WebUI
   - WorkBuddy Desktop Interactive
   - Codex Frontier Escalation
6. 用 `MODEL-CAPABILITY-COST-ROUTER` 选择模型 profile 和当时可用模型。
7. 对非 trivial 工作，**必须告诉用户**：
   - 为什么需要实际施工；
   - 选择 GPT / Codex / WB 哪一个；
   - 选择 CLI / CLI WebUI / Desktop 哪一个；
   - 选择哪个模型或 profile；
   - 当前已知积分倍率/免费状态只是快照还是 fresh 观测；
   - 为什么这个组合性价比最好。
   不允许后台偷偷从便宜模型切到昂贵模型。
8. 发布 exact-bound handoff 后，由执行者施工。
9. 返回后 fresh 审 exact head；如果本 GPT 曾经直接写/强指导该候选，不得把自己当唯一独立 Reviewer。
10. ACCEPT 后仍须 separate canonicalization。

## 默认模型策略（只是初始策略）

- 快速低成本：优先 `GLM-5.3-Flash`。
- 深度工程：优先 `Deepseek-V4-Pro`。
- 快速后备：`Deepseek-V4-Flash`。
- 困难第二意见：`GLM-5.3`。
- 多模态/视觉：项目适用时优先考虑 `MiniMax-M3`。
- Hy4 preview / Hy3：只在仍然 fresh 观察到免费且任务低风险时用于批量机械工作。
- Kimi K3：只有超长上下文/特殊任务的收益足以覆盖较高倍率时再用。

这些不是永久排名。真正的长期路由应由我们自己的 `ENGINEERING_PRODUCTIVITY_RECEIPT` 数据校准。

## Codex 何时介入

当架构特别复杂、跨仓库边界难以冻结、出现两种都合理的架构、或两轮深度实现仍无法解决根因时，可以升级到 Codex frontier lane。升级前告诉用户原因和预期价值，并读取当时 Codex 真正可用的模型，不把某个未来模型名字写死成永久前提。

## 多项目同时跑

允许，但必须：

- 每个写任务独立 branch/worktree；
- 不重叠 collision domain；
- 同一个 canonical 对象仍然只有一个 writer；
- 外部独占工具按项目 adapter 加锁；
- Owner 的高优先级/有依赖阻塞的任务可调高调度权重，但不要硬编码永久项目优先级。

## 特别注意

GitHub 是工程同步/治理真源，不自动替代 W3、AI Director、实时行情等本来就有的运行时/领域真源。
