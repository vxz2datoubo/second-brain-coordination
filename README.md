# second-brain-coordination

第二大脑、WorkBuddy、Codex、GPT 协作中枢。

## 项目集基础能力层

### 时序证据智能基础层（TEIF）

为交易研究、第二大脑和未来业务模块提供统一的时间、证据、来源追溯、数据谱系、可信度、版本、时序知识图谱和因果假设能力。

- [时序证据智能基础层蓝图](docs/architecture/TEMPORAL-EVIDENCE-INTELLIGENCE-FOUNDATION.md)
- [与现有项目和蓝图的集成映射](docs/architecture/TEMPORAL-EVIDENCE-INTEGRATION-MAP.md)
- [实施任务清单](docs/architecture/TEMPORAL-EVIDENCE-IMPLEMENTATION-BACKLOG.md)
- [统一事件契约](contracts/foundation/event-envelope.schema.json)
- [统一判断契约](contracts/foundation/assessment-envelope.schema.json)
- [概率与可信度策略](configs/foundation/confidence-policy.yaml)

核心方法：任何重大事实或判断都应回答“什么时候发生、系统什么时候知道、证据是什么、可信程度如何、有哪些反证和替代解释”。

## 交易研究模块

### 注意力信号引擎

用于研究“主动搜索 → 内容供给 → 大众扩散 → 机构确认 → 资本市场反应”的传播路径，并检验不同平台之间的领先与滞后关系。

- [注意力信号引擎设计蓝图](docs/trading/ATTENTION-SIGNAL-ENGINE.md)
- [注意力信号引擎实施任务清单](docs/trading/ATTENTION-SIGNAL-ENGINE-BACKLOG.md)

### 注意力异常归因与歧义消解

用于回答“热度为什么突然升高”，区分目标主题与同名词污染，并为候选事件提供证据、反证和置信度。首个案例为微信指数中的 `Matrix` 与 `Matrix 3.5`。

- [注意力异常归因与歧义消解蓝图](docs/trading/ATTENTION-SIGNAL-ATTRIBUTION.md)
- [注意力异常归因实施任务清单](docs/trading/ATTENTION-SIGNAL-ATTRIBUTION-BACKLOG.md)
- [Matrix 关键词歧义配置](configs/attention/keywords/tech.world_model.matrix.yaml)

## 当前状态

- 架构与契约处于 Proposed / Draft 阶段。
- 当前分支不包含真实平台数据、自动采集器或真实交易代码。
- 全部研究输出默认 `NO_TRADE`，不进入真实订单关键路径。
- 当前可访问仓库中尚未发现独立完整的项目集总蓝图；待其进入同一仓库后，将按集成映射执行差异审查和 ADR 对齐。
