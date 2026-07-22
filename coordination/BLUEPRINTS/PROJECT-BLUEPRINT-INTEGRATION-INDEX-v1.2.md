# 第二大脑与A股交易系统项目蓝图集成索引 v1.2

> `agent_id: GPT`
>
> `supersedes: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.1.md`
>
> `boundary: research_only / NO_TRADE`

## 一、用途

本索引继承v1.1的PEOS与四群体多智能体模块登记，并新增凯利－索普概率优势、期望值和资本配置模块，确保它进入企业工作流而非成为孤立公式文档。

## 二、权威层级

- `L0`：用户批准的本地权威总蓝图；
- `L1`：企业章程、认识论、证据、权限和协作治理；
- `L2`：交易研究、世界模型、长期记忆、决策校准、风险和资本配置；
- `L3`：领域策略、事件、数据适配器、实验和数字分身影子模拟。

## 三、新登记模块

### 3.1 模块信息

- module_id: `KELLY-THORP-PROBABILISTIC-CAPITAL-ALLOCATION-0011`
- skill_id: `KELLY-THORP-EXPECTED-VALUE-SIZING-SKILL-0011`
- specialized_blueprint: `coordination/BLUEPRINTS/KELLY-THORP-EXPECTED-VALUE-CAPITAL-ALLOCATION-SKILL-BLUEPRINT-v1.0.md`
- research_validation: `coordination/BLUEPRINTS/KELLY-THORP-EXPECTED-VALUE-CAPITAL-ALLOCATION-RESEARCH-VALIDATION-v1.0.md`
- machine_readable_skill: `coordination/SKILLS/KELLY-THORP-EXPECTED-VALUE-CAPITAL-ALLOCATION-SKILL-v1.0.yaml`
- program_charter: `coordination/BLUEPRINTS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.2.md`
- implementation_issue: `#62`
- parent_program: `#31`
- dependencies: `#23 / #38 / #59 / #60 / #61`
- status: `SPECIALIZED_BLUEPRINT_REGISTERED / PROJECT_PLAN_PENDING / RUNTIME_NOT_IMPLEMENTED`

### 3.2 进入整体系统的位置

```text
市场数据、事件、策略实验、多智能体情景和用户判断
→ WorldModel与ProbabilityAndOutcomeModel
→ 概率来源、基准率、证据、反证和UNKNOWN
→ ExpectedValueAndUtilityDecision
→ Raw Kelly / General Log-Optimal Allocation
→ Fractional / Bayesian / Robust / Risk-Constrained Kelly
→ 组合相关性、共同因子、容量、现金和尾部约束
→ AShareExecutionConstraintMapping
→ 研究仓位区间、现金储备、ABSTAIN或NO_EXECUTABLE_POSITION
→ Issue #61 DecisionEpisode事前冻结
→ W9影子结果、归因、校准和信念修订
```

## 四、不重复建设边界

| 已有系统 | 继续负责 | W11新增职责 | 禁止重叠 |
|---|---|---|---|
| W2 MarketData | 原始行情、成交、质量和时间 | 使用可用时点和执行分布 | 重建行情权威源 |
| W4 StrategyResearch | 信号、策略、实验和收益样本 | 把分布转成边际资本配置 | 用Kelly重新生成信号 |
| W5 EventIntelligence | 事件、来源、日历和注意力 | 构造条件情景和信息价值 | 把事件故事直接当概率 |
| W6 AgentGame | 参与者策略和反事实 | 接收条件概率候选 | LLM故事直接驱动仓位 |
| W7 ValidationAndRisk | 样本外、成本、容量、风险门 | 增长目标与风险约束配置 | 建第二套风险权威引擎 |
| W9 ShadowMode | 冻结预测和事后结果 | 冻结仓位反事实和校准 | 影子输出变订单 |
| W10 PEOS | 世界/个人/任务模型和DecisionEpisode | 提供EV与资本配置视图 | Personal模型篡改市场概率 |
| Issue #59/#60/#38 | 知识原子、长期记忆和网关 | 保存Kelly知识与校准经验 | 建第二套canonical知识库 |

## 五、强制接口

Issue #62项目计划必须冻结：

1. `OutcomeScenario`和残余UNKNOWN概率质量；
2. `ProbabilityEstimate`来源、区间、校准和版本；
3. `PayoffDistribution`与成本、流动性和未成交；
4. `ExpectedValueDecision`的GrossEV、NetEV、替代机会和信息价值；
5. `KellyAllocationRequest/Result`的理论、稳健和可执行三层；
6. 多资产相关性、共同因子和已有仓位；
7. `A_SHARE_EXECUTION_RULE_REGISTRY`按生效日版本化；
8. Issue #61 DecisionEpisode事前冻结与事后结果解锁；
9. W7风险门和W9影子模式接口；
10. QCLAW知识原子、反例和对抗夹具；
11. NO_TRADE、用户审批和权限边界。

## 六、系统记录源矩阵

| 对象 | 权威源 | 派生/索引 | 禁止 |
|---|---|---|---|
| 市场事实与成交 | W2原始追加式数据 | 特征、情景 | LLM覆盖事实 |
| 事件和信息到达 | W5事件权威 | 条件情景 | 忽略可用时点 |
| 策略结果 | W4/W7实验登记 | 未来分布候选 | 样本内均值冒充未来 |
| 概率估计 | ProbabilityEstimate registry | 融合后验 | 无来源点概率 |
| 期望值 | ExpectedValueDecision | 排序、信息价值 | GrossEV冒充NetEV |
| 资本配置 | KellyAllocationResult | A股可执行仓位 | Raw Kelly变订单 |
| 风险约束 | W7及批准的W11合同 | 压力报告 | 第二套隐藏风险规则 |
| A股制度 | 版本化官方规则登记 | 回放投影 | 永久硬编码 |
| 事前判断 | Issue #61 DecisionEpisode | 事后评分 | 结果倒改事前记录 |
| 长期经验 | PR #57 canonical知识与Issue #60索引 | 检索和宫殿入口 | 重复事实源 |

## 七、集成验收门

1. 蓝图、研究矩阵、技能合同和Issue已登记；
2. 母章程v1.2和PROGRAM-INDEX v1.2引用本模块；
3. K0完成非重复建设审计；
4. 正EV、负EV和UNKNOWN均有测试；
5. 二元和一般收益Kelly结果可手算/数值复现；
6. Full/Fractional/Risk-Constrained与固定仓位、零仓位有基线比较；
7. 相关性、共同因子和已有仓位进入组合计算；
8. T+1、涨跌停、停牌、整手、费用和未成交进入A股映射；
9. 有概率区间、参数敏感度和模型漂移；
10. 有连续亏损、跳空、流动性消失和尾部压力测试；
11. 有样本外、walk-forward和规则版本回放；
12. 有DecisionEpisode事前冻结和事后归因；
13. 有ABSTAIN、NO_EXECUTABLE_POSITION和降级路径；
14. 通过秘密、权限和NO_TRADE测试；
15. GPT验收、用户批准L0权威蓝图回写；
16. 不以公式、文档、回测单次高收益或模型自报作为完成证据。

## 八、Agent执行边界

- GPT：研究、总设计、反向审视、任务编排和验收；
- Codex：Issue #62项目计划、合同、优化器和canonical集成；
- QCLAW：研究消化、概率事件知识、公式条件、反例和对抗夹具；
- WorkBuddy：本地数据、官方规则、费用、成交和影子证据；
- 用户：目标函数、资本边界、不可承受损失、模型纠正和高风险审批。

Issue #62项目计划冻结文件归属前，各Agent不得同时修改同一canonical优化器或风险文件。

## 九、当前状态

```yaml
module_id: KELLY-THORP-PROBABILISTIC-CAPITAL-ALLOCATION-0011
specialized_blueprint: COMPLETE
research_validation_matrix: COMPLETE
machine_readable_skill_contract: COMPLETE
program_charter_v1_2: COMPLETE
integration_index_registration: COMPLETE
implementation_issue: 62
codex_project_plan: NOT_STARTED
runtime: NOT_IMPLEMENTED
a_share_historical_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
protected_master_blueprint_backwrite: PENDING
```
