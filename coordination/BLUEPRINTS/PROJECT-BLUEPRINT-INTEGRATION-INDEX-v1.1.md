# 第二大脑与A股交易系统项目蓝图集成索引 v1.1

> `agent_id: GPT`
>
> `supersedes: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.0.md`
>
> `boundary: research_only / NO_TRADE`

## 一、用途

本索引登记专项蓝图如何进入企业母工程，防止形成孤立文档、重复运行时或无人验收的概念堆积。

## 二、权威层级

- `L0`：用户批准的本地权威总蓝图；
- `L1`：企业章程、认识论合同、证据、知识权威和协作治理；
- `L2`：交易研究、世界模型、个人认知模型、长期记忆和决策校准核心能力；
- `L3`：领域专项、实验、数据适配器和受控数字分身。

所有专项蓝图必须登记：模块ID、蓝图、Issue、依赖、系统记录源、接口、验证、权限、回滚、UNKNOWN和本地权威回写差异。

## 三、已登记模块

### 3.1 四群体多智能体战略博弈

沿用v1.0登记：

- module_id: `A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-0001`
- implementation_issue: `#23`
- boundary: `research_only / NO_TRADE`

### 3.2 PEOS个人认识论与认知操作系统

- module_id: `PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`
- specialized_blueprint: `coordination/BLUEPRINTS/PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-BLUEPRINT-v1.0.md`
- research_validation: `coordination/BLUEPRINTS/PERSONAL-EPISTEMIC-COGNITIVE-OS-RESEARCH-VALIDATION-v1.0.md`
- program_charter: `coordination/BLUEPRINTS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.1.md`
- implementation_issue: `#61`
- parent_program: `#31`
- dependencies: `#38 / #59 / #60 / PR #57`
- status: `SPECIALIZED_BLUEPRINT_REGISTERED / PROGRAM_CHARTER_UPDATED / PROJECT_PLAN_PENDING`

## 四、PEOS在整体系统中的位置

```text
原始世界数据、个人资料、对话、项目和交易研究
→ Issue #59 原子化、证据、冲突、UNKNOWN和对抗校验
→ PR #57 canonical知识与Issue #60长期混合记忆
→ WorldModel + PersonalCognitiveModel + TaskContextModel
→ DecisionAndCognitiveCalibrationEngine
→ MetacognitiveAuditAndGovernance
→ 回答、学习、研究决策支持和受控数字分身
→ 结果、纠错、反证、信念修订和长期演化
```

PEOS不是Issue #59、#60或#38的替代品：

- #59负责把知识和用户观察变成忠实、可追溯的原子；
- #60负责长期保存、混合检索、时间版本和记忆宫殿；
- #38负责统一知识网关和canonical上下文接口；
- #61负责世界/个人/任务三模型、推理审计、决策校准和元认知治理。

## 五、强制接口

PEOS项目计划必须冻结：

1. `KnowledgeAtom → WorldBelief / CognitiveObservation / DecisionEvidence`映射；
2. `LearningPacket → canonical memory`兼容；
3. `MemoryContextBundle`中的world、personal、task、conflict、unknown和source视图；
4. DecisionEpisode事前冻结与事后结果解锁；
5. PersonalCognitiveFeature支持证据、反证、情境、时间和用户审查；
6. BeliefRevision和source revocation依赖传播；
7. 元认知输出状态和ABSTAIN合同；
8. 概率校准、过程评分和经济效用的独立指标；
9. A股交易研究的市场事实、实验和多智能体情景输入；
10. GPT、Codex、QCLAW和WorkBuddy的文件所有权与禁止事项。

## 六、系统记录源矩阵

| 对象 | 权威源 | 派生/索引 | 禁止 |
|---|---|---|---|
| 原始对话、文件、市场事实 | 原始追加式存储 | 文本解析、摘要 | 模型推断覆盖原文 |
| 知识、证据、冲突、UNKNOWN | PR #57 canonical合同及批准演进 | 向量、图谱、宫殿、缓存 | 第二套静默canonical store |
| 世界模型结论 | 带证据和版本的领域模型记录 | 查询上下文、情景摘要 | 当成原始事实 |
| 个人认知特征 | 开放、版本化、可纠正的PersonalCognitiveModel | 个性化解释和训练建议 | 单次观察变永久人格 |
| 决策过程 | 事前冻结DecisionEpisode | 事后评分和复盘 | 根据结果改写事前推理 |
| 概率与校准 | Forecast/Calibration registry | Brier、log、曲线和报告 | 单一总分证明能力或效用 |
| 数字分身输出 | 影子模拟记录 | 比较报告 | 冒充用户意图或直接行动 |

## 七、集成验收门

模块只有同时满足以下条件才可声明进入整体蓝图：

1. 专项蓝图、研究验证矩阵和Issue已登记；
2. 母章程和PROGRAM-INDEX已引用；
3. 完成C0非重复建设审计；
4. 世界、个人和任务模型的系统记录源清楚；
5. 完成DecisionEpisode最小纵向闭环；
6. 个人模型可见、可争议、可修正和可撤销；
7. 通过状态/特质、角色扮演、跨领域迁移和抗谄媚评测；
8. 通过证据、冲突、UNKNOWN、时间和来源测试；
9. 通过秘密值、权限、许可和删除传播测试；
10. GPT验收、用户批准权威蓝图回写；
11. 数字分身在门槛前保持`NOT_IMPLEMENTED`或`SHADOW_ONLY`；
12. 不以文档数量、模型自报或测试夹具删减作为完成证据。

## 八、Agent执行边界

- GPT：研究、总体架构、编排、反向审视和验收；
- Codex：Issue #61项目计划、canonical合同、核心实现和集成；
- QCLAW：Issue #59/#60主线及#61研究消化、用户模型候选和对抗夹具；
- WorkBuddy：本地来源、格式、接口和真实运行证据；
- 用户：公开授权、模型纠正、重大方向和高风险批准。

Issue #61项目计划完成前，各Agent不得同时修改同一canonical文件。

## 九、当前状态

```yaml
module_id: PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010
specialized_blueprint: COMPLETE
research_validation_matrix: COMPLETE
program_charter_v1_1: COMPLETE
program_index_registration: COMPLETE
implementation_issue: 61
implementation_plan: NOT_STARTED
runtime: NOT_IMPLEMENTED
real_data_validation: NOT_STARTED
open_user_model: NOT_IMPLEMENTED
decision_episode_vertical_slice: NOT_IMPLEMENTED
digital_twin: DEFERRED
protected_master_blueprint_backwrite: PENDING
boundary: research_only / NO_TRADE
```
