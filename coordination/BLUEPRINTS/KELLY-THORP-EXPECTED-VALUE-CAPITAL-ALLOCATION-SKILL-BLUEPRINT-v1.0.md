# 凯利－索普概率优势、期望值决策与资本配置技能蓝图 v1.0

> `module_id: KELLY-THORP-PROBABILISTIC-CAPITAL-ALLOCATION-0011`
>
> `skill_id: KELLY-THORP-EXPECTED-VALUE-SIZING-SKILL-0011`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `implementation_issue: #62`
>
> `related_issues: #23 / #38 / #59 / #60 / #61`
>
> `boundary: research_only / NO_TRADE`

## 一、定位

本模块不是一个“凯利公式计算器”，而是一套从概率判断到资本配置的完整决策技能。

它必须依次回答：

1. 事件和收益情景是否定义正确；
2. 概率是否有证据、基准率和校准记录；
3. 扣除所有成本后是否仍有正期望；
4. 正期望来自真实优势，还是过拟合、信息重复或偶然样本；
5. 在资本、回撤、流动性、相关性和A股制度约束下应配置多少；
6. 应使用Full Kelly、Fractional Kelly、Risk-Constrained Kelly，还是直接不做；
7. 事后如何区分判断、仓位、执行和随机性的贡献。

核心链路：

```text
机会、事件或策略信号
→ 情景定义与概率估计
→ 基准率、证据、反证与校准
→ 收益/损失分布与全部成本
→ Gross EV / Net EV / Expected Utility
→ Raw Kelly / General Log-Optimal Allocation
→ 参数不确定性、相关性、尾部和回撤约束
→ A股制度、流动性、整手和账户能力映射
→ 可执行研究仓位区间、现金储备或ABSTAIN
→ DecisionEpisode事前冻结
→ 结果、归因、概率校准和技能更新
```

## 二、知识映射

### 2.1 用户已经明确知道并提出的部分

- 凯利公式；
- Edward O. Thorp及《Beat the Dealer》《Beat the Market》；
- 期望值决策；
- 分析概率事件；
- 根据概率和赔率调整押注；
- 以长期收益最大化为目标；
- 要适配A股并成为可调用技能。

### 2.2 用户已经隐含理解但尚未完整表达的部分

- “是否值得做”和“应该做多大”是两个问题；
- 胜率高不等于期望值高；
- 同一个正期望机会，仓位过大也可能导致长期失败；
- 押注比例必须随概率、收益比和资本变化而调整；
- 多个机会不能孤立计算，需要考虑资金占用和相关性；
- 单次盈亏不能证明概率或仓位模型正确。

### 2.3 容易理解但此前未明确提出的部分

- Full Kelly最大化的是长期期望对数财富，不是单期平均利润；
- 期望值、期望效用和几何增长是不同目标；
- Fractional Kelly用部分增长换取更低波动和回撤；
- 概率估计误差会系统性导致过度下注；
- 多资产Kelly需要联合收益分布，不是把每个股票的凯利比例相加；
- 相关信号可能只是同一信息被重复计票；
- proper scoring rules可用于长期校准概率；
- 价值信息Value of Information决定是否值得继续研究或等待新证据；
- 真实资金之外还存在流动性资本、心理资本和任务生存资本。

### 2.4 技术上较难但系统必须处理的部分

- 连续收益分布下的期望对数优化；
- 多资产联合情景和协方差/尾部依赖；
- 参数后验不确定性与Bayesian Kelly；
- 分布漂移、模型风险和稳健优化；
- 回撤概率约束和风险约束Kelly；
- 非独立、非平稳和路径依赖机会；
- A股T+1、涨跌停和不可成交造成的控制失效；
- 有限期限、提款需求和效用函数差异；
- 组合容量、冲击和成交概率；
- 规则变化后的重新计算和历史结果可比性。

## 三、理论骨架

### 3.1 期望值

对于互斥情景：

```text
EV = Σ p_i × payoff_i
NetEV = Σ p_i × net_payoff_i
```

其中`net_payoff_i`必须已经包含：

- 佣金、税费和过户费用；
- 买卖价差；
- 滑点和冲击；
- 未成交、部分成交和排队成本；
- 资金占用和机会成本；
- 融资成本或借券成本；
- 退出困难和隔夜跳空的尾部情景。

`EV > 0`只是必要条件，不代表任何仓位都合理。

### 3.2 二元凯利

若每投入1单位，成功获得净利润`b`，失败损失1单位，成功概率为`p`，失败概率`q=1-p`：

```text
f* = (b p - q) / b
```

解释：

- `f* <= 0`：理论上不下注；
- `f* > 0`：存在正期望时的理论对数增长最优比例；
- 公式假设赔率、概率、损失边界和重复结构已正确描述；
- 股票收益通常不是简单二元结果，因此不能直接机械套用。

### 3.3 一般收益分布

对单一机会收益率随机变量`R`：

```text
f* = argmax_f E[log(1 + fR)]
subject to 1 + fR > 0 for all admissible scenarios
```

对多资产或多策略：

```text
w* = argmax_w E[log(1 + wᵀR)]
```

并加入：

- `w >= 0`或允许融资融券时的授权边界；
- `Σw <= capital_budget`；
- 单标的、行业、主题和因子上限；
- 流动性、容量和成交约束；
- 回撤、尾部和现金储备约束。

### 3.4 Fractional Kelly

```text
f_used = λ × f_raw, 0 <= λ <= 1
```

`λ`不得只是用户随意选择的“胆量旋钮”。它应由以下因素共同决定：

- 概率估计的样本量和校准；
- 收益分布的不确定性；
- 模型漂移；
- 机会相关性；
- 尾部风险；
- 用户不可承受损失；
- 资金期限和提款需求；
- 交易成本与流动性；
- 当前组合回撤状态。

默认输出应同时展示`1/4 Kelly、1/2 Kelly、3/4 Kelly、Full Kelly`的增长与风险差异，但Full Kelly不得成为默认研究建议。

### 3.5 Risk-Constrained Kelly

当用户或系统有明确回撤约束时，目标不再只是最大化期望对数增长，而是：

```text
maximize expected log growth
subject to drawdown probability / tail loss / liquidity / concentration constraints
```

必须优先输出满足生存和任务持续性的解，而不是数学上增长最快但现实中可能被迫退出的解。

### 3.6 期望效用与目标冲突

凯利对应对数效用和长期增长目标，不是所有人的唯一效用函数。

系统必须区分：

- 长期资本增长；
- 单期预期利润；
- 最大回撤控制；
- 达到目标财富的概率；
- 在固定期限内避免资金不足；
- 保留流动性；
- 用户心理和业务生存约束。

如果目标不是长期对数增长，系统必须显示凯利结果和目标特定结果的差异，不得把凯利包装成普遍唯一最优。

## 四、概率建模系统

### 4.1 概率来源等级

每个概率必须标记：

- `MARKET_IMPLIED`：市场价格或赔率隐含；
- `FREQUENCY_ESTIMATE`：历史频率；
- `MODEL_PREDICTION`：统计/机器学习模型；
- `EXPERT_JUDGMENT`：人工判断；
- `MULTI_AGENT_INFERENCE`：多智能体博弈；
- `BASE_RATE`：基准率；
- `POSTERIOR_BLEND`：多来源后验融合；
- `UNKNOWN`。

### 4.2 概率质量字段

至少保存：

- point_estimate；
- interval_or_distribution；
- sample_size；
- effective_sample_size；
- source_lineage；
- independence_assumption；
- calibration_history；
- Brier/log score；
- base_rate；
- model_version；
- regime_scope；
- effective_from / review_after；
- supporting_evidence / counterevidence；
- confidence_basis；
- drift_status；
- disconfirmation_conditions。

### 4.3 贝叶斯更新

新证据进入后，不应只把概率从60%随手改为70%。系统必须保存：

```text
Prior
→ Evidence likelihood or structured weight
→ Posterior distribution
→ Sensitivity to alternative priors
→ Position-size change
```

当无法可靠定义似然时，必须标记为结构化专家更新，而不是伪装成严格贝叶斯推导。

### 4.4 概率校准

长期记录：

- calibration curve；
- Brier score；
- logarithmic score；
- resolution/discrimination；
- coverage；
- 不同市场阶段和事件类型的分组表现；
- 概率区间覆盖率；
- 对仓位和实际效用的影响。

校准指标用于改进概率，不得单独证明策略能赚钱。

## 五、A股约束映射

### 5.1 制度版本化

建立`A_SHARE_EXECUTION_RULE_REGISTRY`，至少按以下维度区分：

- 交易所和板块；
- 证券类型；
- 生效日期；
- 涨跌幅限制；
- 无涨跌幅阶段；
- 最小申报数量和递增单位；
- 最小价格变动；
- T+1/T+0属性；
- 盘后交易；
- 风险警示和退市整理；
- 融资融券和可卖空能力；
- 税费和收费版本。

规则必须来自上交所、深交所、北交所、证监会、财政部或税务机关等权威来源，并带生效日期，禁止永久硬编码。

### 5.2 T+1风险

现金股票买入当日不能卖出，因此：

- 计划止损不等于可执行止损；
- 当日突发事件必须进入尾部情景；
- 凯利损失端不能只使用止损比例；
- 新开仓、已有底仓和可卖T仓必须分开建模；
- 隔夜风险和次日开盘流动性必须单独估计。

### 5.3 涨跌停和不可成交

系统必须模拟：

- 单日跌停；
- 连续跌停；
- 一字板无成交；
- 盘口容量不足；
- 停牌和复牌跳空；
- 退市和流动性接近消失；
- 理论仓位无法按目标价格退出。

这意味着A股的“最大损失”不能简单等于计划止损。

### 5.4 整手和最小资金

理论权重必须经过：

```text
理论资金
→ 价格与申报单位
→ 向下/最接近可执行数量取整
→ 成本后现金检查
→ 最低有效仓位检查
→ 组合重新归一化
```

如果取整后仓位过小、成本吞噬优势或组合约束被破坏，应输出`NO_EXECUTABLE_POSITION`。

### 5.5 成本和流动性

净期望必须使用情景化成本，而不是固定一个费率：

- 买入与卖出成本不同；
- 不同流动性和交易时段滑点不同；
- 大单冲击非线性；
- 事件日、涨停附近和竞价阶段成交概率变化；
- 持有期影响资金占用和机会成本。

### 5.6 普通账户与融资融券

默认现金账户：

- 禁止负权重；
- 禁止假设可裸卖空；
- 现金作为显式资产；
- 融资融券只有在账户资格、标的资格、可用券源和成本均验证后才能进入模型。

## 六、技能执行流程

### Step 0 任务与资金边界

确认：

- 这是学习、研究、影子模拟还是真实决策；
- 可配置资本是多少；
- 哪些资金不能承受损失；
- 时间期限和流动性要求；
- 最大允许回撤；
- NO_TRADE和审批边界。

### Step 1 情景定义

把“会涨”改写为互斥且尽可能穷尽的收益情景，包含：

- 收益区间；
- 时间窗口；
- 成交和退出状态；
- 事件路径；
- 尾部结果；
- 未覆盖残差情景。

### Step 2 概率估计

结合：

- 世界模型和基准率；
- 事件雷达；
- 量化模型；
- 多智能体博弈；
- 市场隐含信息；
- 用户判断；
- 反方模型。

用户判断进入PersonalCognitiveModel和DecisionEpisode，但不能覆盖WorldModel概率。

### Step 3 期望值与边际优势

计算：

- Gross EV；
- Net EV；
- EV相对现金或替代机会；
- 对概率和收益估计的敏感性；
- 价值信息和继续等待的价值。

### Step 4 原始凯利

根据二元、离散、连续或组合模型计算Raw Kelly，并输出数学假设。

### Step 5 不确定性折扣

使用至少一种可解释方法：

- fractional Kelly；
- posterior expected log growth；
- 概率区间最差/保守分位；
- distributionally robust optimization；
- parameter bootstrap；
- 模型集合与权重；
- risk-constrained Kelly。

不得把“置信度×Kelly”冒充唯一严格公式，除非其决策依据已说明。

### Step 6 组合与相关性

检查：

- 已有仓位；
- 行业、主题和因子暴露；
- 多信号同源；
- 事件共同风险；
- 尾部相关性；
- 资金占用重叠；
- 对手和流动性反馈。

### Step 7 A股可执行映射

应用交易规则、整手、成本、成交概率、T+1、涨跌停、停牌和账户权限。

### Step 8 风险与生存门

至少输出：

- 最大/典型回撤分布；
- 亏损一半、连续损失和尾部情景；
- 达到风险阈值概率；
- 资本恢复所需收益；
- 用户和系统是否能在该路径中继续执行。

### Step 9 输出建议区间

输出：

- 不做；
- 观察/等待信息；
- 试探仓；
- 1/4 Kelly区间；
- 1/2 Kelly区间；
- 风险约束最优区间；
- 理论Full Kelly仅作参照；
- 现金和后续加减仓规则。

### Step 10 事前冻结与事后复盘

与Issue #61的DecisionEpisode对接：

- 冻结概率、证据、收益分布、仓位和失效条件；
- 结果揭晓后不得改写事前判断；
- 分离预测误差、仓位误差、执行误差和随机性；
- 进入概率校准、知识原子和能力迁移记录。

## 七、输出合同

```yaml
skill_output:
  edge_status: POSITIVE | NEGATIVE | UNCERTAIN
  gross_ev: number
  net_ev: number
  expected_utility: number_or_unknown
  raw_kelly_fraction: number_or_unknown
  fractional_kelly_scenarios: []
  confidence_adjusted_range: [min, max]
  drawdown_constrained_fraction: number_or_unknown
  correlation_adjusted_portfolio: []
  a_share_executable_position: []
  cash_reserve: number
  expected_log_growth: number_or_unknown
  binding_constraints: []
  sensitivity_analysis: []
  tail_scenarios: []
  counterevidence: []
  unknowns: []
  abstention_reasons: []
  invalidation_conditions: []
  required_next_evidence: []
  decision_episode_ref: string
```

任何小数点后精确仓位都必须有输入精度支撑。否则输出范围，不制造“12.37%仓位”式虚假精确。

## 八、与其他系统联动

### 8.1 与PEOS世界模型

提供：

- 基准率；
- 因果机制；
- 外部情景；
- 历史案例；
- 来源质量；
- 替代解释。

### 8.2 与PersonalCognitiveModel

记录：

- 用户是否高估概率；
- 是否忽略收益分布或成本；
- 是否因近期盈亏改变风险偏好；
- 是否存在追涨、损失厌恶、结果偏差或过度自信。

个人模型只调整解释、审批和风险约束，不得偷偷篡改外部概率。

### 8.3 与事件雷达

事件雷达输出事件时间、情景、信息到达和可用时点；本技能将其转成概率－收益－仓位问题。

### 8.4 与四群体多智能体博弈

多智能体引擎提供条件概率、对手反应和可观察验证信号；本技能不得把LLM生成的“主力故事”直接当概率。

### 8.5 与指标、策略和回测

策略系统提供样本外收益分布、交易频率、成本、容量和漂移；本技能计算边际配置，而不是重新发明信号。

### 8.6 与W7验证和风险

共同负责：

- walk-forward；
- 样本外；
- Monte Carlo和bootstrap；
- 未来函数和数据泄漏；
- 成本、容量和冲击；
- drawdown和risk of ruin；
- 稳健性和升级门。

### 8.7 与W9影子模式

实时冻结概率与仓位建议但不下单，持续记录：

- 如果执行会怎样；
- 概率是否校准；
- Kelly是否过大；
- 哪种fractional/risk-constrained方案更适合。

### 8.8 与QQ知识系统

QCLAW负责：

- Kelly、Thorp、EV和概率决策知识原子；
- 公式条件、反例和失败条件；
- 概率事件本体；
- 对抗测试和错误案例；
- 长期校准经验进入记忆宫殿。

## 九、对抗测试

必须覆盖：

1. EV为负但胜率很高；
2. EV为正但尾部存在近乎毁灭损失；
3. 成本使正EV转负；
4. 仅凭最近20次胜率计算Kelly；
5. 忽略概率区间只用点估计；
6. 两个同源模型被当作独立证据；
7. 多个股票实际属于同一主题风险；
8. 计划止损在T+1和跌停下无法执行；
9. 把平均盈利/亏损当作完整分布；
10. 低波动历史掩盖跳空；
11. 训练期概率未经校准直接进入Kelly；
12. regime shift后继续使用旧参数；
13. Full Kelly在有限期限和提款需求下被错误推荐；
14. Fractional Kelly被误当成自动安全；
15. 用户要求“收益最大化”时忽略生存和回撤；
16. 组合取整后超出现金；
17. 涨停买不到、跌停卖不出却按理论成交；
18. 用结果好坏反向修改事前概率；
19. 通过删除失败案例提高回测结果；
20. 无法估计概率时仍给出精确仓位。

## 十、成熟度与停止条件

```yaml
blueprint: COMPLETE
research_validation: REQUIRED
project_plan: PENDING_ISSUE_62
runtime: NOT_IMPLEMENTED
real_data_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
```

停止或降级条件：

- 净期望不为正；
- 概率来源不可追溯；
- 概率严重失校准；
- 分布或市场规则发生漂移；
- 流动性和退出无法建模；
- 尾部情景可能破坏资本生存；
- 组合相关性未知且影响重大；
- A股规则版本未验证；
- 用户风险边界未明确；
- 关键测试或真实案例失败。

## 十一、核心参考体系

- J. L. Kelly Jr., A New Interpretation of Information Rate, 1956；
- Edward O. Thorp, Beat the Dealer；
- Edward O. Thorp and Sheen T. Kassouf, Beat the Market；
- Edward O. Thorp, The Kelly Criterion in Blackjack, Sports Betting, and the Stock Market；
- MacLean, Thorp, Ziemba, The Kelly Capital Growth Investment Criterion: Theory and Practice；
- MacLean, Ziemba, Blazenko, Growth Versus Security in Dynamic Investment Analysis；
- Busseti, Ryu, Boyd, Risk-Constrained Kelly Gambling；
- Cover, Universal Portfolios；
- Samuelson and Merton对log-optimal普遍化限制的研究；
- proper scoring rules、概率校准和决策效用研究；
- 上交所、深交所、北交所、证监会及税务机关现行规则。

引用学术体系不等于本模块已在A股有效。A股适用性必须通过Issue #62的历史、回放和影子验证。
