# 第二大脑与A股交易系统企业级总工程章程 v1.2

> `agent_id: GPT`
>
> `supersedes: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.1.md`
>
> `incorporates_v1_1_by_reference: true`
>
> `new_module: KELLY-THORP-PROBABILISTIC-CAPITAL-ALLOCATION-0011`
>
> `implementation_issue: #62`
>
> `boundary: research_only / NO_TRADE`

## 一、继承与升级

v1.2完整继承v1.1关于PEOS、世界模型、个人认知模型、任务情境模型、DecisionEpisode、元认知治理、长期记忆、知识权威、A股交易研究和多AI协作的全部有效规则。

本版本新增一个独立但受约束的一级工作流：

`W11 Probabilistic Edge, Expected Value and Robust Capital Allocation`。

它把“预测概率”和“承担多少资本风险”正式分开，补上此前系统只有概率校准、风险、仓位和验证零件，却没有统一资本配置决策合同的缺口。

## 二、W11系统定位

```text
WorldModel / EventIntelligence / StrategyResearch / AgentGame
→ 情景、概率、收益分布、反证和UNKNOWN
→ ExpectedValueAndUtilityDecision
→ GrowthOptimalCapitalAllocation
→ RobustAndRiskConstrainedSizing
→ AShareExecutionConstraintMapping
→ 研究仓位区间、现金储备、ABSTAIN和后续证据任务
→ Issue #61 DecisionEpisode事前冻结
→ W9影子结果、归因、概率校准和信念修订
```

W11不生成市场信号，不修改市场事实，不替代W7风险引擎，也不直接生成真实订单。它只在已经定义机会和概率分布后，计算是否存在净优势以及资本配置范围。

## 三、新增有界上下文

在v1.1的22个有界上下文之后新增：

23. `ProbabilityAndOutcomeModel`：互斥情景、概率来源、区间、校准、基准率和UNKNOWN；
24. `ExpectedValueAndUtilityDecision`：GrossEV、NetEV、替代机会、期望效用和信息价值；
25. `GrowthOptimalCapitalAllocation`：二元、离散、连续和组合Kelly；
26. `RobustAndRiskConstrainedSizing`：fractional、Bayesian、稳健、回撤和尾部约束；
27. `AShareExecutionConstraintMapping`：T+1、涨跌幅、申报单位、成本、流动性、停牌和账户能力；
28. `CapitalAllocationCalibration`：事前仓位、事后结果、归因、概率和配置误差校准。

每个上下文必须拥有独立系统记录源、输入输出合同、版本、证据、测试、降级和停止条件。

## 四、一级工作流W11

### W11 凯利－索普概率优势、期望值与稳健资本配置

负责：

- 分析互斥概率事件和收益分布；
- 检查概率来源、基准率、证据、反证和校准；
- 计算扣除全部成本后的期望值；
- 区分货币期望值、期望效用和长期期望对数增长；
- 计算Raw Kelly、Fractional Kelly和风险约束配置；
- 处理多机会相关性、共同因子、容量和现金；
- 映射A股T+1、涨跌停、申报、税费、滑点和不可成交；
- 输出仓位区间、现金储备、敏感性、尾部场景和ABSTAIN；
- 进入DecisionEpisode和影子模式完成长期校准。

依赖：

- W2市场数据与回放；
- W4指标、理论、策略与实验；
- W5事件情报；
- W6多智能体博弈；
- W7验证与风险；
- W9影子模式与工程学习；
- W10 PEOS认知与决策校准；
- Issue #38/#59/#60/#61及PR #57 canonical知识运行时。

## 五、W11架构硬规则

1. `NetEV <= 0`时不得输出正仓位；
2. 期望值为正不等于任何仓位均合理；
3. 凯利只在指定概率、收益分布、重复结构和效用目标下成立；
4. Full Kelly不得作为默认研究建议；
5. Fractional Kelly不得被描述为自动安全；
6. 概率点估计不足以支持高影响仓位，必须保留区间、后验或敏感性；
7. 未校准LLM置信度、故事一致性或用户强烈确信不得直接转成概率；
8. 多模型同源数据、相同提示或共同假设不得冒充独立证据；
9. 多标的必须处理行业、主题、风格、事件和尾部相关性；
10. 计划止损不得被当作保证成交的最大损失；
11. A股T+1、涨跌停、停牌、整手、费用和流动性必须进入收益分布；
12. A股交易规则必须按交易所、板块、证券类型和生效日期版本化；
13. 理论比例必须经过整数股、现金、成本和可执行性映射；
14. 参数、规则或市场阶段漂移时必须重新计算；
15. 输出优先采用范围和敏感性，不制造虚假精确；
16. 资本生存、回撤和流动性约束可以否决Raw Kelly；
17. 事前概率、证据、收益分布和仓位在结果揭晓前冻结；
18. 事后分别评价预测误差、收益分布误差、仓位误差、执行误差和随机性；
19. W11始终`research_only / NO_TRADE`，LLM不进入真实订单关键路径；
20. 任何重大失败案例保持可见并阻断成熟度升级。

## 六、系统记录源

| 对象 | 权威源 | 派生对象 | 禁止 |
|---|---|---|---|
| 原始市场、事件与成交数据 | W2/W5追加式来源 | 情景与特征 | LLM摘要覆盖原始事实 |
| 策略收益分布与实验结果 | W4/W7实验登记 | 概率和收益候选 | 样本内结果冒充未来分布 |
| 概率估计 | ProbabilityEstimate版本记录 | 融合后验、校准报告 | 无来源点概率 |
| 期望值决策 | ExpectedValueDecision | 排序和信息价值 | 忽略成本的GrossEV冒充NetEV |
| Kelly配置 | KellyAllocationResult | 可执行研究仓位 | Raw Kelly直接变订单 |
| A股制度 | AShareExecutionRuleRegistry | 回放规则投影 | 无生效日期硬编码 |
| 事前决策 | Issue #61 DecisionEpisode | 事后评分 | 根据结果修改事前记录 |
| 长期校准 | W9/CapitalAllocationCalibration | 技能更新 | 只保留成功案例 |

## 七、阶段路线

### K0 审计和非重复建设

确认W7/W9/W10与现有仓位能力，冻结W11边界。

### K1 概率事件和期望值合同

建立情景、概率、收益、成本和证据合同。

### K2 单机会稳健Kelly

实现二元、离散和连续分布的原始与fractional配置。

### K3 组合、相关性和共同因子

加入已有仓位、行业、主题、容量和现金。

### K4 A股可执行映射

加入按日期版本化的制度、整手、费用、流动性和成交状态。

### K5 回撤、尾部和模型风险

加入risk-constrained、Bayesian/robust方法和压力测试。

### K6 DecisionEpisode和概率校准

建立事前冻结、事后归因和长期Brier/log/calibration记录。

### K7 A股历史与影子验证

在无未来函数、真实成本和真实制度下比较多个仓位基线，不进入真实交易。

## 八、成功标准新增

1. 有一个可手算验证的二元Kelly闭环；
2. 有一个多情景股票收益分布闭环；
3. 有一个处理相关性和已有仓位的组合闭环；
4. 有一个应用A股T+1、涨跌停、整手和成本的可执行映射；
5. 有Full、1/2、1/4、固定仓位、零仓位和risk-constrained基线；
6. 有概率区间和参数敏感性，不只给点估计；
7. 有真实失败案例、连续亏损和不可成交压力测试；
8. 有样本外、walk-forward、成本、容量和规则版本回放；
9. 有DecisionEpisode事前/事后校准；
10. 有ABSTAIN和NO_EXECUTABLE_POSITION；
11. GPT验收且用户批准本地权威蓝图回写；
12. 不以公式正确、回测高收益或文档完成冒充系统已验证。

## 九、Agent职责

- GPT：研究、架构、反向审视、编排和验收；
- Codex：Issue #62项目计划、合同、优化器、测试和集成；
- QCLAW：Kelly/Thorp/EV研究消化、概率知识原子和对抗夹具；
- WorkBuddy：本地历史数据、规则、费用、成交与影子证据；
- 用户：目标、资本边界、不可承受损失、模型修正和高风险审批。

## 十、当前成熟度

```yaml
module_id: KELLY-THORP-PROBABILISTIC-CAPITAL-ALLOCATION-0011
specialized_blueprint: COMPLETE
research_validation_matrix: COMPLETE
machine_readable_skill_contract: COMPLETE
implementation_issue: 62
codex_project_plan: NOT_STARTED
runtime: NOT_IMPLEMENTED
a_share_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
protected_master_blueprint_backwrite: PENDING
```
