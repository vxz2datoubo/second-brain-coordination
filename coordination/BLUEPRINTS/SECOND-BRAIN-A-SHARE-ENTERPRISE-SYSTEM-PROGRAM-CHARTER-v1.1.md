# 第二大脑与A股交易系统企业级总工程章程 v1.1

> `agent_id: GPT`
>
> `supersedes: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.0.md`
>
> `new_module: PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`
>
> `implementation_issue: #61`
>
> `boundary: research_only / NO_TRADE`

## 一、第一性原理目标

本工程不是堆积AI、知识、指标和文档，而是建设一个可持续感知、记忆、解释、推演、验证、校准、学习和回溯的企业级决策研究系统。

v1.1将第二大脑正式定义为：

`Personal Epistemic and Cognitive Operating System，PEOS，个人认识论与认知操作系统`。

它必须同时理解：

1. 外部世界发生了什么以及证据支持什么；
2. 用户为什么会提出当前问题和形成当前判断；
3. 当前任务真正要解决什么、风险和约束是什么；
4. 结论、推理、证据、概率、行动和结果各自质量如何；
5. 系统自己有哪些未知、冲突和可能错误；
6. 下一次如何改进可复用的判断流程。

总体闭环：

```text
真实数据、事件、个人资料与项目知识
→ 时间、来源、参与者、质量、许可和证据
→ 原子化、冲突、UNKNOWN和长期记忆
→ WorldModel + PersonalCognitiveModel + TaskContextModel
→ DecisionAndCognitiveCalibrationEngine
→ MetacognitiveAuditAndGovernance
→ 研究回答、概率情景、学习与决策支持
→ 事前冻结、事后结果、过程/结果分离复盘
→ 信念修订、能力更新、失败经验和持续演化
```

## 二、企业平台边界

### A. PEOS第二大脑平台

负责：

- 原始资料、知识、证据、版本、冲突和UNKNOWN；
- 知识原子化、持续消化和抗谄媚校验；
- 长期语义、情景、程序、项目、用户和元记忆；
- 向量、BM25、精确实体、图谱、时间、来源和记忆宫殿混合检索；
- 世界模型、个人认知模型和任务情境模型；
- 决策事件账本、推理过程审计、概率校准和能力迁移；
- 开放、可协商、可修正和可撤销的用户模型；
- 元认知monitoring/control、独立反方和ABSTAIN门；
- 数字分身的受控影子模拟。

### B. A股交易研究平台

继续负责：

- 实时和历史市场数据、Level-2聚合、公告、新闻、事件和注意力；
- A股制度、时间语义、回放、指标、策略、实验和验证；
- 成本、滑点、容量、风险和样本外评估；
- 四群体多智能体博弈、对手建模和反事实；
- 概率情景、影子模式和研究决策支持。

市场事实和实验结果是WorldModel输入；PersonalCognitiveModel只能分析用户如何使用这些信息，不得修改市场事实。

### C. 协作控制面

负责GPT、Codex、QCLAW、WorkBuddy和用户之间的任务、权限、分支、合同、测试、验收、回滚和工程学习。

## 三、能力域与有界上下文

保留v1.0能力域，并新增：

12. `WorldKnowledgeAndMechanism`：外部事实、机制、基准率、因果假设和情景；
13. `PersonalCognitiveModel`：用户知识、能力、思维、价值、状态、偏差和边界；
14. `TaskSituationModel`：单次任务目标、时间、风险、资源和约束；
15. `EvidenceAndBeliefMaintenance`：理由、依赖、冲突、修订、撤销和真值维护；
16. `DecisionEpisodeLedger`：事前判断、概率、行动、结果和复盘；
17. `ReasoningProcessAudit`：前提、推理步骤、因果、基准率、反证和失效条件；
18. `MetacognitiveMonitoringAndControl`：系统自知、不确定性和控制动作；
19. `OpenNegotiatedUserModel`：用户查看、争议、纠正、冻结和撤销认知模型；
20. `ForecastAndCalibration`：概率、Brier/log score、校准、分辨率和经济效用；
21. `LearningAndTransfer`：能力缺口、训练、跨情境迁移和长期效果；
22. `DigitalTwinSimulation`：过去模式、当前可能与客观更优方案的受控比较。

## 四、系统记录源

- 原始事实和原始个人资料：不可变或追加式来源存储；
- canonical知识原子、证据、冲突和UNKNOWN：Phase 3唯一候选记忆运行时；
- 向量、图谱、时间、宫殿和摘要：可重建索引，不是事实源；
- WorldModel结论：带来源、状态、版本和失效条件的领域推断；
- PersonalCognitiveModel：带正反证、情境、时间、置信度和用户审查的版本化模型；
- DecisionEpisode：事前冻结的决策记录和事后独立结果；
- 工程学习登记：任务预期、实际效果、正负影响和规则演化。

LLM摘要、模型推断和数字分身输出不得冒充独立原始证据。

## 五、一级工作流

保留W1至W9，新增：

### W10 PEOS世界模型、个人认知模型与决策校准

```text
证据和长期记忆
→ 世界/个人/任务三模型
→ 推理审计和决策校准
→ 元认知与对抗门
→ 回答、学习和研究决策支持
→ 事后结果和信念修订
```

W10依赖Issue #38、#59、#60和PR #57，不得另建第二套canonical事实源。

## 六、阶段路线升级

### Phase 0至Phase 2

维持企业审计、基础合同和交易数据纵向闭环。

### Phase 3A 知识原子与长期记忆

Issue #38/#59/#60完成知识原子、LearningPacket、混合检索、时间版本、冲突和UNKNOWN。

### Phase 3B PEOS认知宪法和决策日志

完成事实/观点/偏好/状态/特质/能力/偏差的认识论合同，并建立少量真实DecisionEpisode纵向切片。

### Phase 3C 开放个人认知模型

允许用户查看、争议、修正、撤销和查看历史版本；建立错误画像专项评测。

### Phase 4至Phase 7

指标、事件、多智能体和对手模型作为WorldModel的领域输入，同时把用户推理和预测进入DecisionEpisode。

### Phase 8 统一影子模式与认知校准

同时验证：

- 策略和市场预测；
- 用户推理过程；
- 世界模型情景；
- 个人认知特征；
- 系统自身置信度。

### Phase 9 受控部署与持续演化

数字分身仅在开放用户模型、对抗评测和长期校准达到门槛后进入影子运行，不替代用户重大决策。

## 七、架构硬规则

1. 世界模型、个人认知模型和任务情境模型地位独立，不得互相篡改事实；
2. 用户偏好、要求和纠错是重要用户知识，不自动成为外部已验证事实；
3. 单次对话不得直接形成永久人格或能力标签；
4. 所有个人认知特征必须区分state、trait、context和domain；
5. 每项认知特征绑定支持证据、反向证据、时间、范围、置信度和复审日期；
6. 用户拥有查看、争议、纠正、冻结、撤销和删除传播权；
7. 重要决策必须在结果揭晓前冻结事前证据、概率、推理和失效条件；
8. 过程质量、结果质量、证据质量、校准质量和行动质量分别评价；
9. 结果正确不自动证明过程正确，结果错误也不自动否定合理过程；
10. Brier Score或任何单一总分不得单独作为能力、校准或决策价值证明；
11. 反方必须有证据和重要性，不得机械反对用户；
12. 证据不足必须允许UNKNOWN、NEEDS_VERIFICATION或ABSTAIN；
13. 冲突和反证不得为了整洁、迎合或提高分数而删除；
14. 向量相似度、宫殿邻近和重复出现不得自动解释为真实性或因果；
15. 所有索引必须可从canonical知识重建；
16. 用户授权的非秘密知识可进入公开GitHub、本地架构或两者；
17. API Key、Token、密码、Cookie、私钥和银行/券商认证秘密值零存储、零向量化、零日志和零提交；
18. 第三方内容必须单独执行许可和发布治理；
19. LLM不直接控制真实订单或不可逆高风险操作；
20. 每个非简单任务进入工程学习、认知校准和结果复盘闭环。

## 八、企业级非功能要求新增

- `ProfileCorrectability`：个人模型可查看、可争议、可修正；
- `EpistemicTraceability`：事实、推断、预测和偏好的认识论状态可追溯；
- `BeliefRevisability`：新证据触发依赖重算而非静默覆盖；
- `StateTraitSafety`：临时状态不会被永久人格化；
- `MetacognitiveCalibration`：系统置信度与真实正确率长期匹配；
- `AntiSycophancy`：证据冲突时允许并要求不同意用户；
- `AutonomyPreservation`：系统提升用户判断力，而非制造依赖；
- `IndexRebuildability`：所有派生索引可重建；
- `OutcomeBiasResistance`：事前过程记录不受事后结果改写。

## 九、成功标准新增

除v1.0标准外，至少需要：

1. 一个可运行的DecisionEpisode事前/事后闭环；
2. 一个开放可纠正的PersonalCognitiveModel纵向切片；
3. 世界模型与个人模型分别提供证据，不互相污染；
4. 测试能识别角色扮演污染、状态/特质混淆和跨领域画像迁移；
5. 系统能保留最强反方、冲突和UNKNOWN；
6. 概率评估同时报告校准、分辨率、过程质量和决策效用；
7. 用户纠正能沿证据、画像、索引和上下文包传播；
8. 数字分身在未达门槛时保持NOT_IMPLEMENTED或SHADOW_ONLY；
9. QCLAW、Codex和WorkBuddy无第二套平行canonical运行时；
10. Issue #61全部重大失败案例保持可见并阻断100%完成。

## 十、Agent职责升级

- GPT：学术研究、总体架构、任务编排、反向审视和验收；
- Codex：项目计划、canonical合同、核心实现和集成；
- QCLAW：知识原子化、研究消化、个人模型候选、长期记忆和对抗评测；
- WorkBuddy：本地数据导入、真实格式、接口、运行态和本地证据；
- 用户：方向、个人模型纠正、公开授权和高风险审批。

## 十一、启动策略

Issue #61先使用项目计划模式完成C0非重复建设审计和C0至C7计划。QCLAW可以并行消化研究并准备对抗夹具，WorkBuddy只审计本地来源和格式；接口冻结前不得同时修改同一canonical文件。
