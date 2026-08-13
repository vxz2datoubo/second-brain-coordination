# 第二大脑 × GPT 认知闭环融合蓝图

- parent_program: `SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
- integration_issue: `#282`
- owner: `USER`
- architecture_owner: `GPT`
- implementation_owner: `CODEX`
- mode: `【Codex模式：项目计划模式】`
- status: `WAITING_PREDECESSOR_R108`
- canonical_runtime: `W3 / PHASE-3-INTEGRATED-OFFLINE-MEMORY`
- memory_program: `CLTM-0021 / Memory Palace`
- knowledge_skill: `GPT-SECOND-BRAIN-KNOWLEDGE-DIGESTION-ASSOCIATIVE-RECALL-SKILL-0001`
- upper_cognitive_model: `PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`

## 1. 定位

本蓝图把“长期记忆”“知识消化”“知识图谱”“计划/约束”“用户认知模型”“主动召回”“实际反馈”收敛到同一认知闭环中。

目标不是多建一套数据库，而是让 GPT 在工程意义上拥有一个可追溯的外部认知层：

`世界资料 / 文件 / 网页 / 聊天 / 真实经历 / 系统结果`
→ `GPT理解与忠实提取`
→ `知识/记忆/事件/计划/stance 多原子化`
→ `Retrieval-before-write：检索旧W3并对账`
→ `去重 / 关联 / 冲突 / 版本 / 时间 / 来源治理`
→ `W3 candidate canonical structure`
→ `Retrieval-before-answer：按需召回`
→ `GPT结合当前事实重新推理`
→ `行动/回答/研究/决策支持`
→ `现实结果与用户纠错`
→ `反馈写回与知识生命周期更新`
→ `下一轮`

“第二大脑成为GPT的大脑”仅指持久外部记忆、按需召回、上下文组装、推理利用和反馈更新，不表示修改基础模型参数或训练权重。

## 2. 唯一系统记录源原则

### 2.1 不得创建平行大脑

- W3 / Integrated Offline Memory 继续作为长期候选记忆与知识运行时基础。
- ConversationEpisode、KnowledgeEpisode、原始证据均追加保存。
- KnowledgeAtom、MemoryAtom、Event、Plan、Stance、Conflict、Unknown、SkillCandidate 是派生结构。
- Embedding、BM25、FTS、向量索引、知识图谱投影、community summary、Memory Palace placement 均是可重建投影，不得成为第二份canonical truth。
- QQ/QCLAW只允许作为可选批量消化、backfill、索引维护、历史队列和质量任务执行器；GPT日常摄入和召回不得依赖QQ在线。

### 2.2 现有系统职责融合

| 层 | 现有能力 | 融合后职责 |
|---|---|---|
| L0 Source | ConversationEpisode / source manifest | 原始证据、内容hash、时间、来源、scope、privacy |
| L1 Episodic | CLTM / Memory Palace | 经历、聊天、计划、事件、目标、commitment、owner stance |
| L2 Semantic | Knowledge digestion skill | 概念、事实主张、机制、条件、反例、方法、案例、UNKNOWN |
| L3 Graph & Lifecycle | W3 relation/conflict/version/time | 关系、更新、冲突、CURRENT/HISTORICAL、freshness |
| L4 Cognitive Models | Personal Cognitive OS | WorldModel、PersonalCognitiveModel、TaskContextModel |
| L5 Retrieval | lexical/semantic/time/graph | retrieval-before-write 与 retrieval-before-answer |
| L6 Reasoning | GPT | 重新推理、反证、失效条件、解释、决策支持 |
| L7 Feedback | correction/outcome/learning | SUPPORT/WEAKEN/REVALIDATE/SUPERSEDE/REVOKE/Skill promotion |

## 3. 统一对象模型

### 3.1 SourceEpisode

必须保留：
- source_episode_id
- source_type
- source_pointer
- source_content_hash
- source_span_or_locator
- recorded_at
- published_at / available_at（若决策相关）
- user_scope
- project_scope
- privacy_class
- author/source agent

### 3.2 Episodic objects

- USER_ASSERTION
- USER_PREFERENCE
- USER_DECISION
- USER_CORRECTION
- USER_PLAN
- USER_GOAL
- USER_COMMITMENT
- USER_EVENT_REPORT
- OWNER_STANCE
- Event
- Plan
- Constraint
- Outcome

### 3.3 Semantic knowledge objects

- CONCEPT
- DEFINITION
- FACT_CLAIM
- SOURCE_CLAIM
- SOURCE_INTERPRETATION
- EVIDENCE
- MECHANISM
- CAUSAL_CHAIN
- CONDITION
- EXCEPTION
- NEGATION
- COUNTEREXAMPLE
- ALTERNATIVE_EXPLANATION
- INDICATOR
- METHOD
- FAILURE_MODE
- INVALIDATION_CONDITION
- CASE
- OPEN_QUESTION
- UNKNOWN
- SKILL_CANDIDATE

### 3.4 Epistemic separation

必须区分：
- source fact / claim / interpretation / value judgment
- user assertion / preference / decision / correction / stance
- assistant analysis / hypothesis
- model inference
- unknown

用户认为某事为假，不等于该事实客观为假；作者观点不等于系统事实；模型推断不等于用户原话。

## 4. 时间、计划与矛盾理解

时间至少分三类：
1. evidence time：何时说/记录；
2. valid/event time：内容何时成立或事件何时发生；
3. freshness/revalidation time：当前是否仍可用于判断。

### 4.1 计划冲突示例

历史：`2026-08-16 要去旅游`。
新消息发生于 `2026-08-15`：`明天准备直接睡大觉睡一天`。

要求：
- 保留两个source episode；
- 将`明天`解析为`2026-08-16`；
- 生成两个plan/event/constraint对象；
- 自动检索同日计划；
- 若旅游时间/是否取消/灵活性未知，产生`SCHEDULE_POTENTIAL_CONFLICT`；
- 若固定时间/资源/互斥约束证明无法共存，升级为`SCHEDULE_HARD_CONFLICT`；
- 用户后续取消旅游则形成 correction + supersession/revocation 关系，不删除历史；
- CURRENT 只使用当前有效计划，HISTORICAL 可重建过去计划状态。

AI表现应自然：提醒“这可能和你之前8月16日旅游的安排冲突”，并指出缺失信息，而不是打印数据库字段。

## 5. Retrieval-before-write

用户说`消化这个/录入知识/采集记忆`时，不允许盲写。

流程：
1. faithful extraction；
2. multi-atom decomposition；
3. epistemic classification；
4. entity/term resolution；
5. bounded retrieval of old W3；
6. reconciliation；
7. graph evolution；
8. temporal/freshness binding；
9. atomic candidate write；
10. post-write exact scoped recall + appropriate paraphrase/graph recall。

Reconciliation actions：
`NEW / DUPLICATE / MERGE / REFINE / SUPPORT / WEAKEN / CONTRADICT / SUPERSEDE / REVOKE / REVALIDATE / RESOLVE_UNKNOWN / UNKNOWN`。

## 6. Retrieval-before-answer

不是每句闲聊都查全库。GPT先运行轻量认知路由器。

### 6.1 触发条件

- 当前消息明确指向过去：之前、上次、记得、继续等；
- 当前计划可能与历史计划/约束冲突；
- 新知识可能更新、冲突或重验证旧知识；
- 当前任务是复杂研究/系统设计/市场分析，旧方法、失败案例或机制类比会显著改善答案；
- 用户稳定偏好/纠错会影响答案；
- 当前概念可通过用户认知映射改善解释层级；
- 当前问题与历史案例存在强机制/约束相似性。

### 6.2 不触发或ABSTAIN

- 普通无连续性闲聊；
- 只有低置信语义相似；
- 所有匹配内容均过时且无法重验证；
- scope/privacy不允许；
- 仅有superseded/revoked内容且当前问题不是历史查询。

## 7. 主动联想与反锚定

目标不是“最像的笔记”，而是检索证据路径：

- lexical
- semantic
- entity graph
- temporal
- provenance
- structural analogy
- hierarchical/theme abstraction

高风险任务必须执行anti-anchor：
- 取当前lineage head；
- 取关键支持证据；
- 取最强反证/替代解释；
- 检查旧案例与当前regime/约束差异；
- stale/superseded/revoked不能凭相似度恢复CURRENT权重。

## 8. GPTSecondBrainContextBundle

统一返回给GPT的紧凑上下文至少包含：
- query intent
- current relevant atoms
- historical predecessors（必要时）
- events/plans/constraints
- cases/analogies
- owner stance/preferences
- cognitive map and teaching bridges
- supporting evidence
- counterevidence
- conflicts
- unknowns
- freshness/revalidation
- provenance
- retrieval explanation
- abstention reason

## 9. 用户认知模型融合

沿用四状态：
- KNOWN_SAID
- KNOWN_UNSAID_INFERRED
- UNKNOWN_BUT_ACCESSIBLE
- UNKNOWN_REQUIRES_SCAFFOLDING

同时兼容Personal Cognitive OS的掌握度阶梯。

硬规则：
- topic-specific；
- time-versioned；
- evidence-backed；
- inferred不能覆盖explicit；
- 用户纠错优先；
- 不形成无领域范围的人格判决。

## 10. 反馈与闭环学习

每次实际使用后的反馈可形成：
- useful
- irrelevant
- stale
- wrong
- incomplete_conditions
- cross_context_success
- failed_case

对应动作：
- SUPPORT
- WEAKEN
- REVALIDATE
- REFINE
- SUPERSEDE
- REVOKE
- RESOLVE_UNKNOWN

知识不能因为一次成功直接晋升技能。

技能生命周期：
`DISCOVERED_INSIGHT → KNOWLEDGE_CANDIDATE → METHOD_CANDIDATE → SKILL_CANDIDATE → SYNTHETIC_TESTED → REAL_CASE_TESTED → CROSS_CONTEXT_VALIDATED → FORMAL_SKILL → DEGRADED/RETIRED`。

## 11. 与A股系统联动

- 旧市场案例可参与历史相似性和机制类比；
- current validity必须用当前数据/公告/规则重验证；
- 市场记忆区分historical similarity、current validity、current relevance、revalidation status；
- T+1、涨跌停、停牌、滑点、成本、流动性和风险门继续由交易系统治理；
- 第二大脑不得因旧经验直接产生真实订单。

## 12. GPT直接工具接口目标

最终目标通过窄接口让GPT不依赖QQ：
- `memory.capture`
- `knowledge.reconcile`
- `memory.search`
- `memory.recall_context`
- `memory.conflicts`
- `memory.feedback`

首个Codex阶段只允许设计/实现synthetic/private-safe contract与vertical slice，不得擅自部署production MCP/Gateway或读取真实私有库。

## 13. 分阶段实施

### Gate 0：R108地基
必须先验收PR #280的七个blocker：bitemporal、temporal confidence、multi-atom、stance targets、typed conflict、content provenance、domain freshness。

### Phase 1：统一对象与写入前对账
KnowledgeEpisode/KnowledgeAtom兼容W3；reconciliation；graph evolution；synthetic tests。

### Phase 2：统一召回与ContextBundle
bounded hybrid retrieval；structural analogy；anti-anchor；CURRENT/HISTORICAL；conflict/unknown bundle。

### Phase 3：GPT tool bridge
在Owner/GPT单独批准后，连接真实private W3；先canary，后常态化。

### Phase 4：反馈学习
memory.feedback、outcome、correction、skill promotion/degradation。

### Phase 5：shadow evaluation
长对话、中文歧义、跨项目串库、过时知识、错误经验、计划冲突、日常主动召回等真实/合成测试。

### Phase 6：formal promotion
只有端到端证据足够后，升级为FORMAL_SKILL。

## 14. 完成标准

“融合完成”必须同时证明：
1. 长文本可正确多原子化且保留同一来源episode；
2. 新知识写入前会查旧知识并执行typed reconciliation；
3. durable candidate write + restart + recall均通过；
4. relative time、CURRENT/HISTORICAL和计划冲突正确；
5. 知识、记忆、计划、stance在同一关系图中可互相检索；
6. 相关对话能主动召回，不相关对话能跳过；
7. 错误/过时/撤销记忆不会被高相似度重新放大；
8. 反馈能更新知识生命周期；
9. 第二大脑中的知识确实改善后续回答/研究质量；
10. 无跨scope泄漏、无credential持久化、无未经授权真实交易或不可逆动作。
