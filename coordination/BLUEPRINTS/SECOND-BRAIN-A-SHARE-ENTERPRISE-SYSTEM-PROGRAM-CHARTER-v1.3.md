# 第二大脑与A股交易系统企业级总工程章程 v1.3

> `agent_id: GPT`
>
> `supersedes: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.2.md`
>
> `incorporates_v1_2_by_reference: true`
>
> `new_module: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012`
>
> `implementation_issue: #63`
>
> `boundary: research_only / NO_TRADE`

## 一、继承与升级

v1.3完整继承v1.2关于PEOS、世界模型、个人认知模型、任务情境、DecisionEpisode、长期记忆、知识权威、W11凯利－索普资本配置、A股研究、风险、影子模式和多AI协作的有效规则。

本版本新增：

`W12 Decision Science Skill Family and Blueprint-to-Skill Gap Compiler`。

W12解决两个结构性问题：

1. 补齐从问题框定、概率、信息价值、时机、组合、风险、执行、研究审计、状态监控到归因学习的完整决策链；
2. 防止专业术语进入蓝图后长期停留为“写过但没有系统”的幽灵能力。

## 二、决策生命周期

```text
FRAME
→ BELIEVE
→ LEARN
→ CHOOSE
→ TIME
→ SIZE（W11）
→ PORTFOLIO
→ SURVIVE
→ EXECUTE
→ VALIDATE
→ MONITOR
→ ATTRIBUTE
→ EVOLVE
```

每个重要决策必须能够定位到一个或多个阶段，并明确其输入、输出、系统记录源、依赖、风险、成熟度和停止条件。

## 三、新增有界上下文

在v1.2的28个上下文后新增：

29. `DecisionProblemFraming`：行动、随机变量、信息顺序、目标、约束和影响图；
30. `BeliefUpdateAndForecastFusion`：基准率、Bayesian/结构化更新、预测融合、依赖和校准；
31. `InformationValueAndResearchStopping`：EVPI、EVSI、调查成本、等待成本和下一项证据；
32. `RobustAmbiguityDecision`：概率区间、场景集合、稳健选择和minimax regret；
33. `SequentialDecisionAndOptimalStopping`：等待、进入、继续、调整、停止和状态策略；
34. `AdaptiveExperimentation`：探索利用、影子实验、研究预算和regret；
35. `BeliefToPortfolioWeights`：Markowitz、Black-Litterman、收缩、稳健权重和约束；
36. `RiskBudgetAndDownsideSurvival`：风险贡献、CVaR、回撤、资本生存和现金缓冲；
37. `ExecutionAndImplementationShortfall`：冲击、成交概率、执行路径和TCA；
38. `MultipleTestingAndOverfittingAudit`：试验族、White/SPA/PBO/DSR、锁箱和失败保留；
39. `RegimeChangeAndModelDecay`：状态、突变、漂移、有效期和降级；
40. `DecisionPerformanceAttribution`：市场、因子、选择、时机、仓位、执行和随机性；
41. `MultiObjectiveUtilityAndCapitalRationing`：多目标、机会成本、资源竞争和用户确认；
42. `SkillGapCompilerAndMaturityRegistry`：术语扫描、技能映射、重复检测和成熟度治理。

## 四、W12一级工作流

```text
蓝图、研究、Issue、PR和用户新要求
→ Gap Compiler扫描
→ 决策生命周期覆盖图
→ 已有碎片和非重复建设矩阵
→ 候选Skill Registry与研究可信度
→ 选择纵向切片
→ 合同、实现、A股验证和影子运行
→ DecisionEpisode与长期记忆回写
```

W12登记十三项候选技能：

1. 决策框定与影响图；
2. 贝叶斯更新与预测融合；
3. 信息价值与研究停止；
4. 模糊不确定性与稳健决策；
5. 序贯决策、最优停止与实物期权；
6. 探索利用与自适应实验；
7. 从观点到组合权重；
8. 风险预算、波动和下行生存；
9. 最优执行与Implementation Shortfall；
10. 多重检验与回测过拟合审计；
11. 市场状态、结构突变和模型衰减；
12. 绩效、决策和执行归因；
13. 多目标效用、机会成本和资本配给。

## 五、与现有工作流的边界

- W2继续拥有市场原始事实、成交和时间权威；
- W4继续拥有信号、策略和实验；
- W5继续拥有事件和信息到达；
- W6继续拥有多Agent情景，不拥有真实概率权威；
- W7继续拥有独立硬风险和验证门；
- W9继续拥有影子结果和工程学习；
- W10继续拥有世界/个人/任务模型和DecisionEpisode；
- W11继续拥有正优势、期望值和资本配置；
- W12补齐其上下游决策技能与技能完整性治理；
- Issue #38/#59/#60继续拥有知识权威、原子、长期记忆和网关。

不得由W12创建第二套风险、执行、组合、市场或知识权威运行时。

## 六、蓝图到技能强制规则

任何进入正式蓝图的重要理论、模型、大师或方法必须被分类为：

- `EXISTING_SKILL_SUBCAPABILITY`；
- `CANDIDATE_INDEPENDENT_SKILL`；
- `REFERENCE_ONLY`并说明原因；
- `REJECTED`并保留依据；
- `UNKNOWN_NEEDS_RESEARCH`。

以下情况为阻断性缺陷：

- 重要术语无任何映射；
- 文档宣称能力但无合同、代码或测试；
- 公式无假设和反例；
- 交易技能没有A股规则映射；
- 有实现但无样本外或影子验证；
- 多Agent制造重复权威运行时；
- 蓝图完成被标为能力验证完成。

## 七、实施优先级

### D0 技能缺口审计

扫描公开仓、本地受保护蓝图、Issue、PR、代码、Skill和测试，建立非重复建设矩阵。

### D1 Gap Compiler与成熟度注册

先实现可重复扫描和人工审查流程，不自动创建运行时。

### D2 P0纵向切片

首轮最多选择三个：

- 决策框定；
- 贝叶斯更新与预测融合；
- 信息价值；
- 稳健决策；
- 研究过拟合审计。

### D3 P1组合、风险、执行和归因

只有在W7/W11边界冻结后，吸收现有碎片并扩展，不重建权威模块。

### D4 P2动态实验与多目标

最优停止、Bandit和多目标资本配给仅在真实反馈和状态合同成熟后进入。

### D5 A股历史和规则验证

按生效日回放T+1、价格限制、申报、费用、停牌、成交和容量。

### D6 影子运行与技能组合评估

评估单技能、组合技能、成本和负面影响，未通过者降级或停止。

## 八、W12架构硬规则

1. 不以技能数量为目标；
2. 按决策问题拆技能，不按大师姓名堆模块；
3. 每个技能有明确非目标和权威边界；
4. 任何重要输出保留来源、假设、反证、UNKNOWN和失效条件；
5. 概率、效用、权重、风险、执行和归因不得混为一个总分；
6. 方法之间必须有简单基线和替代方案；
7. 海外或其他市场研究不能自动证明A股有效；
8. Bandit、自适应实验和动态策略默认只允许shadow；
9. 个人模型不得暗中修改世界概率、效用函数或风险限额；
10. 交易技能读取版本化A股规则；
11. 测试必须包含不可成交、状态突变、相关性上升和成本反转；
12. 研究试验总数、失败和人工选择必须保留；
13. 自动Gap Compiler的误报、漏报和错误合并也必须评测；
14. 第一轮最多三个P0运行切片；
15. 所有能力保持`research_only / NO_TRADE`。

## 九、成功标准

1. 有完整的决策生命周期覆盖矩阵；
2. 旧蓝图的重要术语均有明确成熟度和归属；
3. Gap Compiler能发现孤儿术语、幽灵能力和重复运行时；
4. 十三项候选技能有机器注册和研究验证；
5. 至少一个P0技能完成真实纵向切片；
6. P0技能能与W10 DecisionEpisode和W11资本配置连接；
7. DS-10能读取真实试验总账并识别选择偏差风险；
8. 交易相关技能完成A股规则版本化验证；
9. 影子结果能进入归因、长期记忆和成熟度回写；
10. 不以文档数量、论文名气、复杂公式或自报完成作为验收。

## 十、当前成熟度

```yaml
module_id: DECISION-SCIENCE-AND-A-SHARE-SKILL-FAMILY-0012
root_cause_audit: COMPLETE
specialized_blueprint: COMPLETE
research_validation_matrix: COMPLETE
machine_skill_registry: COMPLETE
implementation_issue: 63
codex_project_plan: NOT_STARTED
gap_compiler_runtime: NOT_IMPLEMENTED
child_skill_contracts: CANDIDATE_REGISTERED
child_skill_runtimes: NOT_IMPLEMENTED
a_share_validation: NOT_STARTED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
protected_master_backwrite: USER_APPROVED_LOCAL_EXECUTION_PENDING
```
