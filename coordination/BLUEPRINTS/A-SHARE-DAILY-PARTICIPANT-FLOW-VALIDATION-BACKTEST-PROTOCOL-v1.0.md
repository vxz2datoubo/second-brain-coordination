# A股每日参与者资金情报验证与回测协议 v1.0

> protocol_id: `A-SHARE-DAILY-PARTICIPANT-FLOW-VALIDATION-BACKTEST-0014V`
>
> parent_skill: `A-SHARE-DAILY-PARTICIPANT-CAPITAL-FLOW-INTELLIGENCE-SKILL-0014`
>
> status: `REGISTERED / NOT_RUN`
>
> boundary: `research_only / NO_TRADE`

## 0. 为什么必须做双重验证

参与者资金研究存在两个容易混为一谈的问题：

1. **识别问题**：系统说“更像机构、北向、活跃席位、被动量化或稳定市场资金”，到底识别得准不准？
2. **经济问题**：即使识别大致正确，这些信息是否在已知价格、行业、风格、事件和注意力因子之外产生稳定的预测或风险管理增量？

因此，所有W13候选必须同时完成：

- `IDENTIFICATION_AND_DIRECTION_VALIDATION`
- `ECONOMIC_INCREMENT_VALIDATION`

不得用漂亮收益曲线代替身份校准，也不得用一次持仓披露吻合宣称可盈利。

## 1. 验证对象

### 1.1 单一证据

例如：

- 龙虎榜机构专用席位净买卖；
- 某营业部席位簇；
- 北向十大活跃证券；
- 北向季度持仓变化；
- ETF份额变化；
- 大宗交易；
- 融资余额变化；
- 官方国家队相关公告；
- 收盘竞价集中度；
- 跨标的同步成交冲击。

### 1.2 单一参与者后验

- `NorthboundActivityPosterior`
- `DomesticInstitutionPosterior`
- `ActiveSeatPosterior`
- `ProgramQuantPosterior`
- `StateLinkedStabilizationPosterior`

### 1.3 多技能组合

组合不是简单投票，必须定义角色：

```text
Context
+ Actor Evidence
+ Market Structure
+ Trigger
+ Confirmation
+ Counterevidence
+ Risk Veto
+ Execution Feasibility
```

示例：

```text
市场压力状态
+ 宽基ETF份额异常
+ 大盘蓝筹同步需求冲击
+ 官方政策/稳定市场事件
+ 收盘竞价确认
- 普通指数调整/ETF套利替代解释
- 流动性恶化否决
→ StateLinkedStabilizationHypothesis
```

### 1.4 交互项

至少验证：

- 机构资金 × 散户注意力；
- 北向活动 × 公司信息复杂度/质量；
- 短线活跃席位 × 情绪周期/涨停生态；
- 稳定市场资金 × 市场压力/大盘权重；
- 程序化/被动流 × 拥挤度/流动性/收盘竞价；
- 多主体同向 × 证据独立性；
- 多主体反向 × 后续波动、反转和流动性风险。

## 2. 点时数据要求

每条数据必须有：

- `event_time`
- `source_time`
- `published_at`
- `available_at`
- `as_of`
- `ingested_at`
- `source_version`
- `field_semantics_version`
- `rule_snapshot_id`
- `disclosure_regime_id`

### 2.1 严格规则

- 日报只能使用当时已经公开或合法可用的数据；
- 季度持仓不能回填成日度已知事实；
- 龙虎榜必须使用交易所实际披露时间；
- 指数调整必须区分公告日、生效日和实际再平衡时点；
- ETF份额和PCF必须使用其真实可用时点；
- 北向新旧披露制度必须在历史日期处切换；
- 供应商后续修订不得覆盖原始版本；
- 缺失、零值、未披露和接口错误必须分离。

任何未来泄漏直接使整个实验族无效。

## 3. 监管与数据制度分段

必须至少按以下时期分别报告，不得把全历史混为一段：

1. `PRE_STOCK_CONNECT`：2014-11-17之前；
2. `SHANGHAI_CONNECT_ONLY`：沪港通开通后、深港通前；
3. `SHANGHAI_SHENZHEN_CONNECT_PRE_NB_ID`；
4. `POST_NORTHBOUND_INVESTOR_ID_PRE_DISCLOSURE_CHANGE`；
5. `POST_2024_08_19_DISCLOSURE_CHANGE`；
6. `POST_2025_07_07_SSE_PROGRAM_RULE`；
7. `POST_2026_01_12_NORTHBOUND_PROGRAM_REPORTING`；
8. `POST_2026_07_06_CURRENT_EXCHANGE_RULES`。

每个断点必须绑定官方来源、实际生效日期和规则快照。若深交所或其他市场具体实施日期不同，使用对应市场规则，不得以单一日期覆盖全部市场。

## 4. 市场状态分层

必须在下列状态中分别检验：

- 牛市、熊市、震荡；
- 高波动、低波动；
- 高流动性、低流动性；
- 大盘、中盘、小盘；
- 高情绪、低情绪；
- 政策干预/市场压力、正常状态；
- 涨停生态强、弱；
- 行业集中、分散；
- 高拥挤、低拥挤；
- 财报季、指数调整期、重大政策窗口、普通交易日。

状态定义必须事前冻结，禁止看到结果后重新划分。

## 5. 横截面与时间序列样本

### 5.1 横截面

在每个交易日比较：

- 被某类资金高后验覆盖的股票；
- 同行业、同市值、同流动性、同动量和同事件暴露的匹配控制组；
- 参与者后验的分位数组合；
- 高置信、低置信和弃权样本。

### 5.2 时间序列

研究：

- 市场层参与者活动；
- 行业层流入/流出；
- ETF和指数需求冲击；
- 席位簇活跃与市场情绪；
- 国家队背景稳定市场假设与市场压力；
- 程序化/被动拥挤和尾盘冲击。

### 5.3 持有期

统一报告：

- 1日；
- 3日；
- 5日；
- 10日；
- 20日；
- 60日。

短期延续和中期反转可以同时存在，禁止只选择表现最好的期限。

## 6. 基准和中性化

每个参与者技能都必须与以下基准比较：

### B0 无信息基准

- 历史基准率；
- 横截面等权；
- 市场或行业平均。

### B1 市场与传统因子基准

至少包括：

- 市场beta；
- 行业；
- 市值；
- 流动性；
- 波动率；
- 动量与短期反转；
- 估值；
- 质量/盈利；
- 换手和成交异常。

### B2 事件与注意力基准

- 公告和新闻事件；
- 情绪与注意力；
- 涨停/跌停和龙虎榜触发状态；
- 指数调整；
- 是否为沪深股通标的；
- 国企/央企或政策暴露；
- 财报与解禁窗口。

### B3 完整母系统基准

已有市场、指标、事件、博弈和风险模型。

W13只有在`B3 + W13`稳定优于`B3`时，才算具有经济增量。

## 7. 身份、方向和金额验证

### 7.1 标签来源

优先标签：

- 后续官方持仓披露；
- 龙虎榜机构专用和席位复现；
- ETF份额与PCF变化；
- 已知指数调整与复制需求；
- 官方国家队公告和定期持仓锚点；
- 合法授权的账户类别标签；
- 大宗交易和公司增减持公告；
- 程序化标签仅在监管或许可数据明确提供时使用。

### 7.2 指标

- Brier score；
- log loss；
- calibration slope/intercept；
- ECE；
- precision / recall / F1；
- actor confusion matrix；
- direction accuracy；
- amount error interval coverage；
- abstention coverage；
- selective risk；
- high-confidence error rate。

### 7.3 三重校准

分别校准：

- 身份；
- 方向；
- 金额区间。

不得用一个“综合置信度”遮盖三者差异。

## 8. 经济增量验证

### 8.1 预测与排序

- Pearson IC；
- rank IC；
- IC稳定性；
- 分位数组合收益；
- 多空研究差；
- 命中率和赔率；
- 条件收益分布；
- 短期延续与中期反转。

### 8.2 风险和市场质量

- 波动率；
- 最大回撤；
- Expected Shortfall；
- 跳空风险；
- 涨跌停无法退出；
- 交易量和市场深度；
- 价格冲击；
- 流动性恢复；
- 信息效率和价格延迟。

### 8.3 可执行性

- T+1可卖库存；
- 涨跌停和停牌；
- 手数与价格步长；
- 佣金、印花税和过户费；
- 滑点和冲击；
- 部分成交和排队；
- 容量；
- 组合换手；
- 目标权重上限；
- 公告/披露延迟后的可交易窗口。

所有结果同时报告毛收益和成本后收益。

## 9. 模型验证框架

### 9.1 时间切分

- expanding walk-forward；
- rolling walk-forward；
- purged cross-validation；
- embargo；
- final lockbox；
- 完全未使用的后验影子期。

### 9.2 嵌套选择

外层评估，内层选择：

- 参数；
- 特征；
- 参与者组合；
- 市场状态；
- 概率融合方法；
- 阈值与弃权门。

测试集不能参与任何调参或状态定义。

### 9.3 滚动重估

只能使用当时已有历史数据。每个重估点冻结：

- 训练窗口；
- 参数；
- 特征版本；
- 证据权重；
- 规则版本；
- 模型版本；
- 下一次允许重估时间。

## 10. 组合、依赖和消融

### 10.1 证据簇

同源或高相关信号必须聚成`EvidenceCluster`：

- 多个动量指标；
- 多个成交量代理；
- 同一供应商不同“主力”字段；
- ETF成交、ETF份额和指数成分成交；
- 同一龙虎榜事件派生的多个席位指标。

系统按证据簇而不是指标数量投票。

### 10.2 必做消融

- 移除每个参与者家族；
- 移除每类来源；
- 移除市场状态；
- 移除注意力和事件；
- 移除执行/流动性层；
- 仅官方证据；
- 官方证据加代理；
- 完整组合。

### 10.3 增量归因

可使用：

- 条件回归；
- 逐层模型比较；
- partial R²；
- permutation importance；
- Shapley/SHAP作为解释辅助；
- 交互项和非线性响应。

SHAP不能证明因果，也不能代替样本外消融。

## 11. 因果与事件研究

对于制度、国家队公告、指数调整和重大政策事件，可以使用：

- 事件研究；
- 匹配样本；
- difference-in-differences；
- synthetic control；
- placebo dates；
- placebo securities；
- negative controls；
- pre-trend检查；
- 异质性分析。

必须明确：

- 处理时点；
- 信息公开时点；
- 处理组和对照组；
- 并发事件；
- 选择机制；
- 可识别假设；
- 无法识别项。

## 12. 多重检验与研究诚信

每组相关研究登记为`ExperimentFamily`，记录：

- 原始假设；
- 全部特征和参数搜索空间；
- 已尝试次数；
- 成功和失败实验；
- 选择规则；
- 基准；
- 锁箱；
- 结果修订。

必须根据问题使用：

- White Reality Check；
- Hansen SPA；
- Probability of Backtest Overfitting；
- Deflated Sharpe Ratio；
- Romano-Wolf stepdown；
- FDR或FWER控制；
- 预注册和失败保存。

不能只汇报最优参数、最优市场状态和最优持有期。

## 13. 参与者特定测试

### 13.1 北向

必须比较：

- 旧披露制度的日度净流信号；
- 新披露制度的活动/十大活跃信号；
- 季度持仓锚点；
- 日度持仓nowcast；
- 披露制度改变前后模型衰减；
- 2018北向投资者识别制度前后；
- 质量、信息复杂度、大小盘和连接标的异质性。

若旧制度效果在新制度消失，必须退役旧模型，不得用旧回测装点新日报。

### 13.2 国内机构

- 机构专用席位短期延续与中期反转；
- 季度持仓与公告之间的时点误差；
- 主动机构与ETF/指数被动流分离；
- 大宗交易与二级市场行为分离；
- 赎回、风险预算和考核期强制交易。

### 13.3 短线活跃席位

- 龙虎榜触发选择偏差；
- 营业部别名稳定性；
- 席位簇在不同题材和情绪周期中的迁移；
- 次日溢价、3/5/10日反转；
- 机构/北向/量化相似轨迹误分类；
- 新席位和冷启动处理。

### 13.4 国家队背景稳定市场资金

- 官方公告事件窗口；
- 宽基ETF份额和成交；
- 大盘权重、金融和核心指数异质性；
- 市场压力与正常状态；
- 普通ETF套利、养老金、保险、公募申赎替代解释；
- 稳定价格、降低波动、改善流动性与提高信息效率必须分别检验。

### 13.5 程序化与量化

- 已知指数再平衡作为正标签；
- 尾盘/收盘竞价集中；
- 横截面同步性；
- 因子拥挤与去杠杆；
- 流动性和冲击状态；
- 监管规则生效前后；
- 无账户标签时只验证“量化样式活动”，不验证账户身份。

## 14. 可靠性分级

每个结论分为：

- `HIGH`: 官方语义清晰、点时正确、跨期样本外稳定、校准和增量验证通过；
- `MEDIUM`: 官方聚合或高质量代理，部分时期稳定，但存在覆盖/身份限制；
- `LOW`: 仅代理、样本小、制度变化敏感或校准不足；
- `REJECTED`: 未来泄漏、不可复现、样本外失败、成本后失效或身份越级；
- `UNKNOWN`: 数据不足或来源语义未验证。

日报必须显示可靠性分级，不得只显示方向箭头。

## 15. 晋级门

### Gate 1 Source Ready

- 来源、许可、字段语义、披露制度和可用时点完成；
- 数据缺失和错误语义可区分。

### Gate 2 Identification Validated

- 参与者身份/方向概率校准；
- 误分类矩阵可接受；
- 能在证据不足时弃权。

### Gate 3 Economic Increment Validated

- 对完整母系统基准存在样本外增量；
- 成本、容量和A股规则后仍成立；
- 不同时期和状态表现可解释。

### Gate 4 Shadow Daily Validated

- 连续影子日报；
- 无未来数据；
- 置信度、覆盖和漂移受控；
- 误报、漏报和不可用时点得到复盘。

### Gate 5 Validated Research Capability

- 通过独立复核；
- 实验族和失败完整保存；
- 明确适用范围和退役条件；
- 仍保持`NO_TRADE`，任何实盘使用需要新的用户批准与独立风险门。

## 16. 当前验证状态

```yaml
ValidationReality:
  point_in_time_participant_dataset: NOT_ASSEMBLED
  northbound_regime_split: NOT_IMPLEMENTED
  dragon_tiger_seat_graph: NOT_IMPLEMENTED
  state_linked_labels: NOT_ASSEMBLED
  program_quant_labels: PARTIAL_PUBLIC_ANCHORS_ONLY
  identification_tests: NOT_RUN
  economic_increment_tests: NOT_RUN
  multiple_testing_audit: NOT_RUN
  shadow_daily_validation: NOT_STARTED
  trust_level: ARCHITECTURE_ONLY
```
