# A股赌场优势启发的生存、容量与运营控制技能蓝图 v1.0

> module_id: `A-SHARE-HOUSE-EDGE-SURVIVAL-AND-OPERATING-CONTROL-0018`
>
> implementation_issue: `#71`
>
> workstreams: `W7 Validation/Risk + W9 Engineering Learning + W11 Capital Allocation`, consuming `W2/W4/W5/W13`
>
> status: `REGISTERED_CANDIDATE / NOT_IMPLEMENTED / NOT_BACKTESTED`
>
> boundary: `research_only / NO_TRADE`

## 0. 结论

赌场值得交易系统学习的，不是“下注越多越稳定”，而是把经营建立在以下组合上：

1. 规则或定价提供可计算的正优势；
2. 只经营优势、容量和可观察性满足门槛的游戏；
3. 用最大赌注、资本准备和风险破产限制保护生存；
4. 用大量有效独立试验让优势显现，而不是把相关下注重复计数；
5. 用审计、监控、对账和关停机制防止作弊、规则漂移和操作损失。

A股与赌场的关键差异是：市场优势未知且会变化，交易成本会随次数累积，收益存在相关性、厚尾、跳空、T+1和不可退出。因此本模块不是“稳定盈利生成器”，而是一个**净优势门、有效次数、风险破产、容量、关停和运营控制编译层**。

## 1. 四层知识映射

### 1.1 用户已知道且已表达

- 赌场依靠小优势和大量下注长期盈利；
- 交易系统应寻找类似的稳定经营方法；
- 需要多技能联合，而不是单指标；
- 必须跨时期回测并验证可信度。

### 1.2 用户知道但未完整表达

- 赌场不会要求每桌每天盈利，而要求总组合长期正期望；
- 高胜率不等于高期望，低胜率也可能是正期望；
- 单次大额下注会使赌场即使有优势也面临短期破产风险；
- 赌场通过游戏规则、赔率、限额、资本准备和审计共同获利；
- “下注次数”只有在近似独立、规则稳定时才会增强优势显现。

### 1.3 用户尚未知道但容易理解

- `house edge`、`hold`、`handle/turnover`和`RTP`不是同一个概念；
- 风险破产不仅取决于平均优势，还取决于赔付分布、最大赌注、相关性和资本；
- 博彩公司平衡账本可降低现金流方差，但有时会牺牲利润；
- 做市商赚取价差时仍会被逆向选择和库存风险吞噬；
- 交易系统必须把原始交易次数折算为`effective independent trials`；
- 优势衰减、拥挤和模型漂移等同于赌场规则被改变或出现优势玩家。

### 1.4 用户尚未知道且技术难度高

- 厚尾、跳空和状态相关下的风险破产模拟；
- 相关序列的有效样本量、块自助法和聚类试验；
- 参数不确定下的robust/fractional Kelly；
- 逆向选择、库存风险、容量冲击与收益分解；
- 多重检验、选择偏差和最终锁箱验证；
- 模型完整性、数据投毒、执行偏差和对账控制。

## 2. 赌场与交易的不可混淆边界

| 赌场条件 | A股现实 | 迁移结论 |
|---|---|---|
| 赌场可设定规则与赔付 | 交易者通常不能设定市场赔率 | 优势必须通过数据估计并持续折扣 |
| 游戏概率相对稳定 | 市场分布会随制度、参与者和状态变化 | 必须版本化、分状态和关停 |
| 更多投注带来更多毛利 | 更多交易增加成本、冲击和逆向选择 | 只有净优势与容量为正时才扩大次数 |
| 大量投注近似独立 | 同板块、同事件、同模型高度相关 | 必须报告有效独立次数 |
| 赌场可限制最大投注 | 交易系统可限制暴露但无法保证退出 | 限额还要叠加T+1、涨跌停和停牌 |
| 赌场拥有实时筹码和现金账 | 回测、影子和真实执行可能存在偏差 | 必须逐层对账，不得用理论收益替代实际可执行收益 |

## 3. 核心净优势合同

`HouseEdgeInspiredNetEdgeEstimate`必须拆分：

```text
net_edge_interval =
  gross_expected_edge_interval
  - explicit_cost_interval
  - slippage_and_impact_interval
  - adverse_selection_loss_interval
  - model_uncertainty_reserve
  - tail_event_reserve
  - operational_loss_reserve
```

必须保存：

- 输入概率和收益分布来源；
- 校准状态与样本外证据；
- 成本和容量假设；
- 市场状态和规则版本；
- 支持证据、反证和替代解释；
- 区间下界、上界和可信度；
- `EDGE_POSITIVE / EDGE_AMBIGUOUS / EDGE_NEGATIVE / ABSTAIN`。

`gross_edge > 0`不等于`net_edge > 0`。高胜率、Sharpe、回测收益和单次成功均不能单独替代净优势。

## 4. 十一个赌场机制映射

### 4.1 House Edge → 净优势门

只有净优势区间下界超过批准阈值，且校准、容量、规则和数据质量满足门时，才允许进入研究候选。

### 4.2 Game Selection → 策略游戏选择

`StrategyGameSelectionGate`按策略、市场状态、标的范围、持有期和数据能力决定：

- `OPEN_FOR_RESEARCH`
- `SHADOW_ONLY`
- `CAPACITY_RESTRICTED`
- `SUSPENDED`
- `CLOSED`

### 4.3 Handle/Turnover → 次数质量

交易次数只有在以下条件满足时才有价值：

- 净优势仍为正；
- 交易之间不是同一因子或事件的重复暴露；
- 成本和冲击没有侵蚀优势；
- 容量未耗尽；
- 数据和模型状态没有漂移。

### 4.4 Table Limits → 最大暴露

`MaxExposureAndTableLimitPolicy`至少覆盖：

- 单笔；
- 单标的；
- 单策略；
- 单行业/主题；
- 单事件；
- 单日；
- 组合共同因子；
- 不可退出场景。

它只向W7/W11提供约束建议，不拥有最终仓位权威。

### 4.5 Bankroll Requirement → 资本缓冲

`CapitalBufferAndRuinAssessment`必须包含：

- 正常经营资本；
- 压力损失资本；
- T+1冻结与不可退出缓冲；
- 交易成本恶化缓冲；
- 数据/系统故障缓冲；
- 恢复与重新验证预算。

### 4.6 Risk of Ruin → 生存概率

不得只使用独立正态收益的简化公式。必须支持：

- 历史压力；
- 块自助法；
- 状态转换；
- 厚尾与跳空；
- 相关性突升；
- 跌停、停牌和流动性枯竭；
- 参数误差和优势衰减。

### 4.7 Game Mix → 多策略组合

不同策略只有在共同数据、共同因子、共同事件和共同持仓去重后，才形成真正的组合分散。

### 4.8 Book Balancing / Hedging → 净暴露控制

降低现金流方差不等于创造优势。对冲后必须重新计算净期望、成本、基差和容量。

### 4.9 Game Protection → 模型与数据保护

`GameProtectionAndModelIntegrityControl`监控：

- 数据污染或字段语义变化；
- 未来信息泄漏；
- 回测作弊式选择；
- 模型漂移；
- 策略拥挤；
- 异常滑点和成交失败；
- 研究结果与影子结果背离；
- 版本、配置或权限越界。

### 4.10 Internal Controls → 运营对账

`OperatingReconciliationReceipt`必须将以下链路对齐：

```text
研究假设
→ 数据版本
→ 特征与模型版本
→ 预测与净优势
→ W11候选配置
→ W7风险否决
→ 回放/影子结果
→ 成本与收益归因
→ 失效和关停记录
```

### 4.11 Close the Table → 策略关停

触发条件至少包括：

- 净优势下界不再为正；
- 校准显著恶化；
- 成本或容量超过阈值；
- 有效独立次数骤降；
- 规则或数据语义改变；
- 风险破产、回撤或不可退出门触发；
- 模型完整性或对账失败。

## 5. 核心对象

- `HouseEdgeInspiredNetEdgeEstimate`
- `EdgeUncertaintyReserve`
- `EffectiveIndependentTrialEstimate`
- `StrategyGameSelectionGate`
- `MaxExposureAndTableLimitPolicy`
- `CapitalBufferAndRuinAssessment`
- `CapacityAndTurnoverQualityAssessment`
- `AdverseSelectionAndCrowdingAssessment`
- `GameProtectionAndModelIntegrityControl`
- `OperatingReconciliationReceipt`
- `HouseEdgeSurvivalValidationReport`

所有对象必须包含：`as_of`、`available_at`、`rule_snapshot_id`、`data_lineage`、`model_version`、`supporting_evidence`、`counterevidence`、`unknowns`、`confidence`、`status`和`invalidating_conditions`。

## 6. 有效独立试验

`EffectiveIndependentTrialEstimate`不得等同于原始交易数。至少考虑：

- 同一标的连续信号；
- 同一行业和主题；
- 同一政策或公告事件；
- 同一模型与特征族；
- 同一市场状态；
- 时间序列自相关；
- 组合共同因子；
- 重叠持有期。

必须同时报告：

- `raw_trial_count`；
- `effective_trial_count_interval`；
- `dependence_clusters`；
- `independence_assumptions`；
- `overcount_risk`。

## 7. 与现有系统的权威边界

- W12/DS-02拥有`ProbabilityEstimate`计算权威；
- W11/Issue #62拥有Kelly、净期望后的资本配置权威；
- W7拥有最终硬风险门与否决权；
- W2拥有行情、规则和回放；
- W4拥有策略与实验定义；
- W5提供事件和政策上下文；
- W13提供参与者资金证据，不证明身份；
- W9拥有结果校准和工程学习；
- 0018只编译净优势质量、有效次数、生存、容量、关停和运营控制。

不得创建第二套概率、Kelly、风险、组合、市场数据、回放、事件、记忆、执行或订单运行时。

## 8. A股第一类约束

必须显式建模：

- 股票现货T+1；
- 涨跌停与一字板不可退出；
- 停牌、退市和ST风险；
- 主板、科创板、创业板、北交所和特殊证券规则；
- 隔夜跳空；
- 交易成本、滑点、冲击和容量；
- 无普通现金账户裸卖空；
- 指数、行业、政策和资金状态变化。

## 9. 第一纵向切片

`0018-VS1 NET-EDGE / EFFECTIVE-TRIAL / RUIN SHADOW REPORT`

只读取现有研究与回放结果，输出：

1. gross/net edge区间和扣减瀑布；
2. 原始次数与有效独立次数；
3. 成本、容量、拥挤和逆向选择评估；
4. 最大暴露上限提案；
5. 资本缓冲和风险破产区间；
6. 关停条件；
7. 事实优先、NO_TRADE影子报告。

不得修改W11配置、W7风险门或任何订单路径。

## 10. 成熟度

- 蓝图：`COMPLETE`
- 研究矩阵：`COMPLETE`
- Skill合同：`REGISTERED_CANDIDATE`
- D0审计：`NOT_STARTED`
- 实现：`NOT_IMPLEMENTED`
- A股回测：`NOT_RUN`
- 影子验证：`NOT_STARTED`
- 实盘：`PROHIBITED`
