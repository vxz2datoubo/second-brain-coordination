# 决策科学技能族与蓝图缺口编译器总体蓝图 v1.0

> `module_id: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
>
> `task_id: DECISION-SCIENCE-SKILL-GAP-COMPILER-0012`
>
> `implementation_issue: #63`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `boundary: research_only / NO_TRADE`

## 一、定位

本模块不是一次性收集更多金融公式，而是补齐从“认识问题”到“事后学习”的完整决策链，并建立永久的蓝图缺口发现机制。

```text
FRAME 问题框定
→ BELIEVE 概率与信念
→ LEARN 信息价值
→ CHOOSE 效用与稳健选择
→ TIME 序贯决策和时机
→ SIZE W11资本配置
→ PORTFOLIO 多机会组合
→ SURVIVE 下行与资本生存
→ EXECUTE 成交与成本
→ VALIDATE 研究真实性
→ MONITOR 状态和衰减
→ ATTRIBUTE 结果归因
→ EVOLVE 认知、模型和规则更新
```

## 二、知识层次映射

### 2.1 用户已明确提出

- 不能只补一个凯利公式，要反思为什么系统遗漏；
- 寻找与凯利类似、重要但尚未技能化的方法；
- 把方法做成可调用、可验证、适配A股的技能；
- 不只顺着构想扩写，要核验可信度并联动现有系统。

### 2.2 用户隐含知道但尚未展开

- 好决策不只由“选什么”构成，还包括何时决定、是否继续收集信息、配置多少、如何成交和怎样复盘；
- 同一个专业词写进蓝图，不等于已经成为系统能力；
- 不同大师和模型往往解决决策链中的不同环节，不能互相替代；
- 技能越多也可能导致冲突、重复建设和伪复杂。

### 2.3 容易理解但此前未系统表达

- `Value of Information`决定是否值得继续调查；
- `Optimal Stopping / Real Options`决定等待本身是否有价值；
- `Black-Litterman`解决观点如何进入组合，不解决观点是否正确；
- `Risk Budget / CVaR`解决下行和风险分配，不产生Alpha；
- `Implementation Shortfall / TCA`衡量好想法在成交中损失了多少；
- `White Reality Check / SPA / PBO / DSR`防止从大量试验中挑出一个幸运赢家；
- `Regime Change`决定旧模型何时应降级或停用；
- `Attribution`区分赚钱来自选股、仓位、市场、执行还是运气。

### 2.4 技术上困难但系统必须处理

- 不完整和相关信息下的概率融合；
- 高维小样本的均值、协方差和尾部估计；
- 动态状态下的最优停止和路径依赖；
- 自适应实验导致的数据偏差；
- 多重检验、研究者自由度和隐藏试验总数；
- 市场冲击、部分成交、排队和反身性；
- 制度变化导致历史可比性失效；
- 多目标效用不可由单一收益指标替代。

## 三、永久元技能

### 3.1 Blueprint-to-Skill Gap Compiler

输入：

- 母蓝图和专项蓝图；
- Issue、PR、代码、测试和运行报告；
- 论文、书籍、机构方法和用户新要求；
- 当前Skill Registry与成熟度。

输出：

- 新发现术语和方法；
- 决策生命周期位置；
- 已有实现和重复能力；
- 孤儿术语与幽灵能力；
- 候选Skill ID；
- 依赖DAG；
- A股约束；
- 研究可信度；
- 优先级、Issue建议和验收门；
- `REFERENCE_ONLY / REJECTED / UNKNOWN`理由。

### 3.2 成熟度状态

```text
DISCOVERED
→ MENTIONED
→ MAPPED_TO_LIFECYCLE
→ CANDIDATE_SKILL_REGISTERED
→ RESEARCH_VALIDATED
→ CONTRACTED
→ IMPLEMENTED
→ A_SHARE_BACKTESTED
→ SHADOW_VALIDATED
→ VALIDATED_RESEARCH_CAPABILITY
```

任何状态不得跨级。

## 四、十三项技能

### DS-01 决策框定与影响图

`DECISION-FRAMING-INFLUENCE-DIAGRAM-SKILL-0012A`

职责：明确决策、可选行动、随机变量、信息可用时点、目标、约束、因果假设和决策顺序。

输出：`DecisionFrame / InfluenceDiagram / AssumptionSet / ObservabilityMap / MissingDecisionVariable`。

### DS-02 贝叶斯更新与预测融合

`BAYESIAN-BELIEF-UPDATE-FORECAST-FUSION-SKILL-0012B`

职责：把基准率、模型、市场隐含概率、专家判断和多Agent输出融合，同时处理相关来源和校准。

输出：`Prior / LikelihoodOrStructuredUpdate / Posterior / ForecastPool / CalibrationTask / UNKNOWNMass`。

### DS-03 信息价值与研究停止

`VALUE-OF-INFORMATION-RESEARCH-STOPPING-SKILL-0012C`

职责：计算完美信息、样本信息和下一项证据的价值，比较调查成本、等待成本和机会流失。

输出：`EVPI / EVSI / ExpectedNetInformationValue / NextBestEvidence / STOP_RESEARCH / CONTINUE_RESEARCH`。

### DS-04 模糊不确定性与稳健决策

`ROBUST-AMBIGUITY-MINIMAX-REGRET-SKILL-0012D`

职责：概率或分布不能可靠点估计时，使用区间、场景集合、worst-case、minimax regret和分布稳健方法。

输出：`RobustChoice / RegretTable / SensitivityRegion / FragileDecision / ABSTAIN`。

### DS-05 序贯决策、最优停止与实物期权

`SEQUENTIAL-DECISION-OPTIMAL-STOPPING-REAL-OPTIONS-SKILL-0012E`

职责：处理等待、分批进入、继续持有、加仓、减仓、退出和未来信息到达。

A股必须建模T+1库存、涨跌停、不可成交和隔夜状态。

### DS-06 探索利用与自适应实验

`EXPLORATION-EXPLOITATION-ADAPTIVE-EXPERIMENT-SKILL-0012F`

职责：为影子策略、研究资源和模型试验分配探索预算，记录regret和停止规则。

非目标：用固定平稳bandit假设直接控制A股实盘。

### DS-07 从观点到组合权重

`PORTFOLIO-BELIEF-TO-WEIGHTS-SKILL-0012G`

职责：连接收益观点、置信度、市场均衡先验、风险模型和组合约束。

参考：Markowitz、Black-Litterman、收缩估计、稳健组合。

输出：`ExpectedReturnView / Confidence / PriorPortfolio / PosteriorReturn / TargetWeightRange / BindingConstraints`。

### DS-08 风险预算、波动和下行生存

`RISK-BUDGET-DOWNSIDE-SURVIVAL-SKILL-0012H`

职责：风险贡献、风险平价、波动目标、Expected Shortfall/CVaR、drawdown、risk of ruin、流动性储备。

非目标：用低波动替代收益优势。

### DS-09 最优执行与Implementation Shortfall

`OPTIMAL-EXECUTION-IMPLEMENTATION-SHORTFALL-SKILL-0012I`

职责：将目标仓位转换为成交计划，平衡冲击、价格风险、成交概率和机会成本。

覆盖：TWAP、VWAP、POV、竞价、盘后固定价格、TCA、部分成交和排队。

### DS-10 多重检验与回测过拟合审计

`RESEARCH-MULTIPLE-TESTING-OVERFITTING-AUDIT-SKILL-0012J`

职责：试验族登记、锁箱、White Reality Check、Hansen SPA、PBO/CSCV、Deflated Sharpe、purge/embargo、失败保留。

输出：`ExperimentFamily / TrialCount / SelectionBiasRisk / AdjustedEvidence / RejectOrRetest`。

### DS-11 状态变化与模型衰减

`REGIME-CHANGE-MODEL-DECAY-SKILL-0012K`

职责：检测市场、制度、数据和模型关系的变化，决定继续、降权、重新训练、冻结或停用。

输出：`RegimePosterior / ChangePoint / DriftEvidence / ValidityWindow / DegradeAction`。

### DS-12 绩效、决策和执行归因

`PERFORMANCE-DECISION-EXECUTION-ATTRIBUTION-SKILL-0012L`

职责：分离市场Beta、行业、因子、选股、事件、时机、仓位、执行、成本和随机性。

输出必须进入Issue #61 DecisionEpisode和W9工程学习。

### DS-13 多目标效用、机会成本与资本配给

`MULTI-OBJECTIVE-UTILITY-CAPITAL-RATIONING-SKILL-0012M`

职责：在长期增长、回撤、流动性、目标达成、心理承受、项目资源和机会成本之间形成显式选择。

非目标：由个人画像暗中替用户决定效用函数。

## 五、与W11凯利系统的关系

W11主要解决：

- 是否有扣费后正优势；
- 正优势下配置多少；
- 如何做fractional和risk-constrained sizing。

W12技能族补齐其上下游：

```text
DS-01框定
→ DS-02概率
→ DS-03信息价值
→ DS-04稳健选择
→ DS-05时机
→ W11仓位
→ DS-07组合
→ DS-08生存
→ DS-09执行
→ DS-10验证
→ DS-11监控
→ DS-12归因
→ DS-13多目标演化
```

## 六、A股统一合同

所有交易相关技能必须读取版本化规则，至少包含：

- 交易所、板块、证券类型和生效日期；
- T+1可卖库存；
- 涨跌幅、无涨跌幅阶段、停牌和复牌；
- 申报数量、价格步长和整数股；
- 竞价、连续、收盘和盘后交易；
- 成交概率、排队、部分成交、滑点、冲击和容量；
- 税费、融资和借券条件；
- ST、退市、新股及规则变化；
- `research_only / NO_TRADE`。

## 七、优先级和实施节奏

### P0 基础认识论和研究真实性

- Gap Compiler；
- DS-01；
- DS-02；
- DS-03；
- DS-04；
- DS-10。

### P1 组合、风险、执行和学习

- DS-07；
- DS-08；
- DS-09；
- DS-11；
- DS-12。

### P2 动态和高级资源决策

- DS-05；
- DS-06；
- DS-13。

第一轮只允许选择不超过三个P0纵向切片，避免同时制造十三个空壳运行时。

## 八、验收门

1. 每个技能有明确决策问题，不按大师名字机械拆分；
2. 有输入、输出、非目标、假设和停止条件；
3. 与现有W2-W11无权威重叠；
4. 有正向、反向、边界和对抗测试；
5. 有简单基线和至少一个替代方法；
6. 交易技能有A股规则版本和真实成本；
7. 有样本外、walk-forward或适当的时序验证；
8. 有失败和UNKNOWN；
9. 运行结果可进入DecisionEpisode和长期记忆；
10. 不以论文、公式、文档或单次回测声明已验证。

## 九、当前成熟度

```yaml
blueprint: COMPLETE
root_cause_audit: COMPLETE
research_validation_matrix: REQUIRED
machine_registry: REQUIRED
implementation_issue: 63
codex_project_plan: NOT_STARTED
gap_compiler_runtime: NOT_IMPLEMENTED
child_skill_runtimes: NOT_IMPLEMENTED
a_share_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
```
