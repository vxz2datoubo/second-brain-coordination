# 个人认识论与认知操作系统蓝图 v1.0

> `module_id: PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `implementation_issue: #61`
>
> `related_issues: #38 / #59 / #60`
>
> `boundary: research_only / NO_TRADE`

## 一、定位

本模块将第二大脑从知识库、笔记系统、个人档案或数字分身，升级为一个能同时理解外部世界、理解用户、审计推理过程并推动认知成长的个人认知操作系统。

核心不是“更像用户”，而是：

1. 知道世界证据支持什么；
2. 知道用户为什么会形成当前判断；
3. 知道系统自己有哪些未知和不确定；
4. 区分结论、推理、证据、概率、行动与结果；
5. 在不迎合也不机械反对的前提下，帮助用户改善可复用的判断流程。

## 二、总体架构

```text
授权原始数据与世界数据
→ 来源、时间、参与者、情境、权限、许可、秘密扫描
→ QCLAW知识原子化、证据绑定、冲突与UNKNOWN
→ canonical知识与长期混合记忆
       │
       ├─ WorldModel
       ├─ PersonalCognitiveModel
       └─ TaskContextModel
                │
                ▼
 DecisionAndCognitiveCalibrationEngine
                │
                ▼
 MetacognitiveAuditAndGovernance
                │
                ▼
 回答 / 学习建议 / 决策支持 / 对抗复核 / 系统调用
                │
                ▼
 结果、用户纠错、反证、新证据与长期演化
```

## 三、五个同等级核心模型

### 3.1 WorldModel

不是单一万能模型，而是联邦式领域模型：

- 实体与机构模型；
- 事件和时间模型；
- 领域知识模型；
- 机制与基准概率库；
- 因果假设图；
- 情景与反事实模拟；
- 预测与概率校准；
- 来源可靠性；
- UNKNOWN与验证路径。

认识论状态至少包括：

`OBSERVED / CORROBORATED / INFERRED / CAUSAL_HYPOTHESIS / FORECAST / COUNTERFACTUAL / DISPUTED / UNKNOWN / STALE / RETRACTED`。

### 3.2 PersonalCognitiveModel

必须是动态、概率化、情境化、证据化和可协商的开放用户模型，不是隐藏的人格判决书。

包含：

- 基础经历、目标、角色、关系和项目；
- 表达习惯、解释偏好和误解风险；
- 知识掌握、能力边界和迁移能力；
- 提问、证据选择、因果建立和隐含假设；
- 风险偏好、决策速度、计划坚持和结果依赖；
- 价值观、成本容忍和目标冲突；
- 情绪、疲劳、兴奋、压力和盈亏状态；
- 认知偏差、触发情境、反证和变化趋势；
- 系统对用户模型本身的置信度与UNKNOWN。

### 3.3 TaskContextModel

同一用户在不同任务中需要不同辅助。任务情境至少记录：

- 表面问题和真实目标；
- 时间跨度；
- 风险和代价；
- 可逆性；
- 决策窗口；
- 资源和约束；
- 需要调用的领域模型；
- 用户当前状态；
- 需要的证据强度；
- 允许的行动范围。

### 3.4 DecisionAndCognitiveCalibrationEngine

分别评价：

1. 结论质量；
2. 推理过程质量；
3. 证据质量；
4. 概率与置信度校准；
5. 行动与目标的一致性；
6. 判断的可复制和可迁移程度。

必须实现过程与结果四象限：

- `GOOD_PROCESS_GOOD_OUTCOME`
- `GOOD_PROCESS_BAD_OUTCOME`
- `BAD_PROCESS_GOOD_OUTCOME`
- `BAD_PROCESS_BAD_OUTCOME`

### 3.5 MetacognitiveAuditAndGovernance

分为：

- `Monitoring`：监测证据充分度、未知、置信度、冲突、画像风险和推理错误；
- `Control`：决定继续检索、降低置信度、启动反方、请求信息、延迟判断或拒答。

允许输出：

`ANSWER / ANSWER_WITH_CAVEATS / NEEDS_MORE_EVIDENCE / NEEDS_USER_CLARIFICATION / NEEDS_DOMAIN_VALIDATION / RUN_ADVERSARIAL_REVIEW / ABSTAIN`。

## 四、数据与记忆分层

### L0 原始证据层

原始聊天、文件、语音、图片、视频文本、交易记录、决策日志和系统事件保持不可变或追加式保存。

### L1 情境与事件层

识别参与者、严肃讨论、假设、玩笑、角色扮演、情绪表达、用户纠错和决策场景。

### L2 知识原子与证据图层

由Issue #59负责：

- KnowledgeAtom；
- EvidenceItem；
- EvidenceChain；
- Claim / Counterclaim；
- Assumption；
- Unknown；
- Decision；
- Outcome；
- CognitiveObservation；
- UserCorrection。

### L3 长期记忆和检索层

由Issue #60负责：

- 向量语义检索；
- BM25和全文检索；
- 精确实体和ID；
- 知识图谱；
- 时间与版本；
- 来源与证据；
- 冲突与UNKNOWN；
- 记忆宫殿。

向量、图谱、宫殿和摘要都是可重建索引，canonical原子和原始证据才是事实源。

### L4 模型层

WorldModel、PersonalCognitiveModel和TaskContextModel只能读取经证据标注的内容，不得把模型推断回写成独立原始证据。

### L5 决策与应用层

输出回答、决策支持、学习计划、训练任务、认知复盘、数字分身模拟和领域系统调用。

## 五、个人认知特征合同

每项特征至少包含：

```yaml
feature_id: CF-...
feature_type: ...
canonical_statement: ...
epistemic_status: OBSERVATION | HYPOTHESIS | USER_CONFIRMED | DISPUTED | RETRACTED
state_trait_context:
  classification: STATE | CONTEXT_DEPENDENT_TENDENCY | TRAIT_CANDIDATE
  domain_scope: []
  situation_scope: []
  excluded_contexts: []
evidence:
  supporting: []
  opposing: []
temporal:
  first_seen: ...
  last_seen: ...
  frequency: ...
  review_after: ...
confidence:
  value: ...
  basis: ...
user_review:
  status: NOT_REVIEWED | ACCEPTED | DISPUTED | CORRECTED | REVOKED
  correction_ref: ...
version:
  model_version: ...
  effective_from: ...
  effective_to: ...
  supersedes: ...
invalidation_conditions: []
```

硬规则：

- 单次对话最多形成Observation或FeatureCandidate；
- 不允许无领域范围的绝对人格结论；
- 状态、特质、情境和领域必须分离；
- 反向证据必须与支持证据同级保存；
- 特征需定期复审和自动过期；
- 用户可以查看、挑战、修正、冻结和撤销。

## 六、知识与能力阶梯

使用多阶段掌握度而不是“会/不会”：

`UNKNOWN → HEARD_OF → RECOGNIZES → CAN_EXPLAIN → CAN_APPLY_WITH_SUPPORT → CAN_APPLY_INDEPENDENTLY → CAN_TRANSFER → CAN_CRITIQUE → CAN_TEACH → CALIBRATED_MASTERY`

`CALIBRATED_MASTERY`要求同时满足：

- 能正确应用；
- 知道适用条件；
- 知道失效条件；
- 能在新情境迁移；
- 能识别反例；
- 自信程度与真实表现匹配。

## 七、决策事件账本

每次重要判断建立`DecisionEpisode`：

```text
问题与目标
→ 决策时可用信息快照
→ 选项与约束
→ 前提、证据、反证、基准概率
→ 隐含假设和因果链
→ 概率预测与行动阈值
→ 失效条件
→ 冻结事前记录
→ 结果揭晓
→ 过程、结果、随机性和外部突变分开复盘
→ 可迁移经验和流程修正
```

事前过程评分必须在结果揭晓前冻结，避免outcome bias和hindsight bias。

## 八、推理审计

至少检查：

- 前提真实性；
- 推理是否跳步；
- 相关性是否误写成因果；
- 是否忽略基准概率；
- 时间尺度是否匹配；
- 是否存在反身性和反馈回路；
- 样本是否有代表性；
- 来源是否独立；
- 是否存在选择偏差、幸存者偏差或测量误差；
- 最强反方和替代解释；
- 判断在哪些条件下失效；
- 结论是否可重复。

## 九、抗谄媚与系统级去偏

对抗机制不是机械反对，而是信息设计、程序门禁和独立复核的组合：

1. 先记录用户原始观点，不立即改写；
2. 独立检索支持和反对证据；
3. 构建最强反方而非稻草人；
4. 检查基准概率和替代解释；
5. 重要结论采用独立评测器；
6. 失败案例不因提高分数而删除；
7. 证据不足输出UNKNOWN或ABSTAIN；
8. 也禁止为了显得客观而无证据反对用户。

## 十、世界模型与交易系统联动

A股交易系统向WorldModel提供：

- 不可变市场数据；
- 事件、公告和注意力；
- 策略实验和验证；
- 多智能体博弈情景；
- 实际结果、成本和风险。

PersonalCognitiveModel只分析用户如何使用这些信息，不得修改市场事实。

最小闭环：

```text
用户交易判断
→ 冻结DecisionEpisode
→ 交易系统提供事实和验证
→ 世界模型生成客观情景
→ 个人模型识别推理模式和状态
→ 校准引擎输出支持、反证、概率和失效条件
→ 事后过程/结果分离复盘
→ 可迁移经验进入长期记忆
```

## 十一、数字分身边界

数字分身必须始终区分：

1. 过去的用户通常会怎么做；
2. 当前状态下用户可能怎么做；
3. 从目标和证据出发更优的做法是什么。

数字分身不得：

- 替代用户作重大决定；
- 把过去行为固化成永久身份；
- 把模拟结果冒充用户真实意图；
- 直接触发真实交易或不可逆操作。

## 十二、评测体系

### 12.1 知识和检索

Recall@K、Precision@K、MRR、nDCG、来源覆盖、时间正确率、冲突召回、UNKNOWN召回、过时泄漏、跨项目串库和撤销泄漏。

### 12.2 个人模型

- Unsupported Profile Rate；
- False Trait Fixation Rate；
- State-Trait Confusion Rate；
- Context Transfer Error；
- Counterevidence Coverage；
- User Correction Latency；
- Profile Drift Detection；
- Roleplay Contamination Rate。

### 12.3 决策和概率

- 过程评分；
- 证据评分；
- calibration curve；
- Brier/log score；
- resolution和discrimination；
- 同类情境迁移表现；
- 决策净收益和风险成本。

Brier Score不得单独作为能力或实际效用的唯一指标。

### 12.4 元认知

区分metacognitive bias、sensitivity和efficiency；评估系统能否识别自身正确与错误、是否在证据不足时降低置信度以及是否正确启动进一步检索。

## 十三、实施路线

- C0：审计现有架构和非重复建设；
- C1：认识论宪法和状态合同；
- C2：数据结构、证据图和信念修订；
- C3：决策日志最小闭环；
- C4：开放可协商个人模型；
- C5：A股领域世界模型纵向切片；
- C6：元认知和对抗评测；
- C7：数字分身受控实验。

优先顺序不是先建数字人，而是：

```text
决策日志闭环
→ 知识原子与证据闭环
→ 开放个人模型闭环
→ 世界模型纵向切片
→ 数字分身
```

## 十四、Agent职责

- GPT：研究、总体设计、编排、反向审视和验收；
- Codex：canonical合同、核心运行时和系统集成；
- QCLAW：知识消化、用户模型候选、长期记忆和对抗评测；
- WorkBuddy：本地来源、真实导入、运行态与接口验证；
- 用户：方向、模型纠正、公开范围和高风险批准。

## 十五、主要失败风险

1. 一次建万能世界模型；
2. 几次对话就形成稳定画像；
3. 模型生成内容自我循环成为证据；
4. 向量相关性冒充真实性；
5. 结果反向污染过程评价；
6. 认知标签成为自我实现预言；
7. 对抗机制变成机械抬杠；
8. 数据越多但证据质量越差；
9. 自动化削弱用户独立判断；
10. 多Agent重复建立平行运行时。

每项风险必须有检测指标、触发门、回滚和用户纠正路径。
