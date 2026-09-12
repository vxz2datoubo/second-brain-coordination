# 项目插件契约 · Project Plugin Contract

> 目标：**NEW PROJECT SHOULD BE PLUGGABLE.**
> 不应出现 `if (project === trading)` 这样写死整个系统的代码。

## 现状（Phase 1）

前端 Shell **不知道**任何项目的内部细节。项目列表完全来自：

```
coordination/EXECUTION/PROJECT-REGISTRY.yaml  → projects[]  （真源，动态发现）
coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml → 每个项目的适配器
```

新增项目 = 在 registry 加一条 + 提供 adapter，**前端无需改动**。

## 已消费的适配器字段

| 字段 | 用途 |
|---|---|
| `project_id` / `display_name` | 项目标识与显示名 |
| `authority.owns` | mission 兜底（权威域描述） |
| `canonical_entrypoints` | mission 兜底 + 入口展示 |
| `collision_domains` | 项目页碰撞域标签 |
| `hard_boundaries` | 项目页硬边界列表 |
| `tool_interfaces` / `handoff` | 项目页关系图 |
| `allowed_execution_carriers` | （未来）派发校验 |
| `default_model_profiles` | （未来）路由展示 |

## ProjectFrontendManifest（Phase 2+ 设计）

未来每个项目可声明一个可选的前端清单，Shell 按此渲染扩展面板：

```yaml
# coordination/EXECUTION/PROJECT-ADAPTERS/<PROJECT>.frontend.yaml (proposed)
project_id: TRADING_SYSTEM
icon: chart
authority_sources:
  - github: vxz2datoubo/second-brain-coordination
  - local_provider: TDX_TQ
default_panels: [overview, tasks, artifacts, activity, governance]
custom_panels:
  - id: market
    label: 行情
    component: TradingCharts
  - id: hypotheses
    label: 假设板
    component: HypothesisBoard
capabilities:
  read_only: true
  dispatch: false
commands: []
```

## Shell 与扩展的边界

| 层 | 职责 |
|---|---|
| Global Core Panels | Overview / Tasks / Artifacts / Activity / Governance（所有项目共有） |
| Project Custom Panels | 交易图表 / 知识图谱 / 导演场景 / 互动叙事（按项目声明） |
| Adapter | 只读数据获取 + 归一化 |
| Manifest | 声明式路由与能力（不含逻辑） |

**Shell 只做路由与布局，不认识项目内部 schema。**

## 硬约束

- 项目适配器**不得**定义第二个全局 router
- 每个 canonical 对象仍只有一个 writer
- 前端 manifest 不构成 authority，只是展示声明
- 新增项目不得要求重写 Shell
