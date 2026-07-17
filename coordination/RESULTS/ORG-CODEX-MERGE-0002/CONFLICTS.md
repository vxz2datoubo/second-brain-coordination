# CONFLICTS — 合并过程中发现的冲突

> Task: ORG-CODEX-MERGE-0002 | Date: 2026-07-16 03:44 UTC+8

## Conflict type: CRITICAL

### C1: Wyckoff Phase 定位冲突
- **旧版**: "所有判断/检测/回测必须按Phase分层处理" (强制前提)
- **新版**: "Treat Wyckoff Phase as a model feature or hypothesis, not an infallible prerequisite"
- **影响**: 旧版所有工作流都以此为前提 → 新版允许 Phase 作为参考但非强制
- **处理**: 旧版语句已从 AGENTS.merged-candidate.md 中移除；Phase 分析能力保留在 WorkBuddy 技能中（69项A股技能含Phase分析），由任务上下文决定是否调用

### C2: Codex 角色冲突
- **旧版**: Codex 在 WorkBuddy 管理框架下工作；超级博弈大脑指南要求 Codex 调用本地 API
- **新版**: Codex 是独立对等的首席工程师；不调用 WorkBuddy 的本地 API
- **处理**: 旧版 Codex 自动调用指南（R32-R34）已从候选 AGENTS.md 中完全移除；新 TASK-PACKET 协议取代旧版自动调用流程

### C3: QClaw 角色移除
- **旧版**: QClaw 被列为算力引擎并有多处引用
- **新版**: "QClaw does not have a role in this project"
- **影响**: CHATGPT-BRAIN-PROTOCOL 中 QClaw 相关内容已移除
- **处理**: QClaw 物理服务器和进程不改变（它们独立运行），仅从文档引用中移除

## Conflict type: HIGH

### C4: 信号格式冲突
- **旧版**: "所有技能输出 +1/0/-1" (强制)
- **新版**: "Preserve raw numerical values. +1/0/-1 is display-only convenience"
- **处理**: 旧版强制要求降级为报告格式约定（STRATEGY-HYPOTHESES.md H15）

### C5: 全面分析协议冲突
- **旧版**: "不得遗漏任何已有技能" (15项全部强制调用)
- **新版**: 15项列表不包含在 AGENTS.merged-candidate.md 中
- **处理**: 降级为工作流预设（TRADING-GOVERNANCE.md），由任务上下文动态决定调用范围

### C6: 买入/卖出"红线" 重新分类
- **旧版**: 所有买入/卖出规则以"违反必亏" / "禁止" 语言列为强制规则
- **新版**: 其中 7/10 条缺乏回测支撑，重新分类为 research_hypothesis
- **处理**: 未见化验证的规则移入 STRATEGY-HYPOTHESES.md 待验证；已验证的参数移入 YAML 配置

## Conflict type: MEDIUM

### C7: "铁律" vs "经验参考" 语言冲突
- **旧版**: 多处使用"铁律""强制规则"语言
- **新版**: 区分 global_invariant (真正不可违反) vs workflow_preset (有用但不强制) vs research_hypothesis (需验证)
- **处理**: 47 条规则按 LEGACY-RULES-AUDIT.md 分类后重新分配

### C8: 数据源优先级中的 TDX"四渠道资金"声明
- **旧版**: 说 TDX "独有四渠道资金"
- **实际**: TDX MCP 不直接提供四渠道分类字段；四渠道资金实际来自 WeStock data_fund_flow
- **处理**: 已修正

## Resolved conflicts

| # | Description | Resolution |
|---|-------------|------------|
| R1 | CHATGPT-BRAIN-PROTOCOL 声称有"集合竞价分析"能力但实际数据源不支持竞价流 | 标记为 L2 缺口（见 11_KNOWN_CONFLICTS），不删除能力声明 |
| R2 | "DDX方向"作为铁律但 TDX MCP 无直接字段 | 保留为工作流预设，WeStock data_technical 可作为替代源 |
