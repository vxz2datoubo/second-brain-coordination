# 认识状态与知识前沿映射总体蓝图 v1.0

> `module_id: EPISTEMIC-KNOWLEDGE-STATE-FRONTIER-MAPPING-0013`
>
> `candidate_skill: EPISTEMIC-KNOWLEDGE-STATE-AND-FRONTIER-MAPPING-SKILL-0013`
>
> `implementation_issue: #457`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `boundary: ARCHITECTURE_CONTRACT_EVAL_ONLY / NO_SECOND_KNOWLEDGE_AUTHORITY / NO_TRADE`

## 1. 定位

本模块把用户在某个主题上的认识状态、外部知识结构、技能依赖、证据、未知、学习桥梁、研究前沿和时效性连接为一张可追溯、可校准、可纠正的派生图。

核心目标不是给用户贴“懂/不懂”的标签，而是让第二大脑在回答、研究、教学、方法选择和系统设计时知道：

1. 哪些内容用户明确表达过；
2. 哪些内容用户没有直接表达，但有证据支持其可能已经掌握；
3. 哪些新内容尚无掌握证据，但从当前知识结构出发可以直接接住；
4. 哪些内容当前需要前置概念、术语桥、例子、工具或结构化脚手架；
5. 当前结论来自什么证据，在哪个领域、时间和情境成立；
6. 下一步最值得补哪一个概念、证据或方法；
7. 哪些未知必须保留，而不是被相似度、模型自信或用户画像强行填满。

这是一层 **derived epistemic projection**，不是第二个 canonical memory、第二个 knowledge graph、第二个 user profile 或第二个 skill authority。

## 2. 现有 authority 复用

### 2.1 单一事实源

继续由以下现有系统拥有 truth：

- W3 / Integrated Offline Memory：长期候选知识与记忆的 canonical runtime；
- SourceEpisode / KnowledgeAtom / MemoryAtom / Event / Plan / Stance / Unknown：证据与知识对象；
- PEOS / PersonalCognitiveModel：用户认知模型与 mastery 体系；
- Skill Registry / Formal Skill Governance：技能权威；
- MethodMemory：可迁移方法记忆；
- DecisionEpisode：重要决策的事前/事后证据；
- Issue #312 Method Discovery Router：方法选择与 Effective Challenge；
- Issue #63 Blueprint-to-Skill Gap Compiler：方法发现到技能工程化的治理链。

本模块只产生可重建 projection 和 candidate mapping。

### 2.2 必须继承的四层 cognitive map

仓库已存在以下四层，因此本任务不是发明第二套分类，而是把它们编译成可执行、可校准、可验证的映射合同：

- `KNOWN_SAID`
- `KNOWN_UNSAID_INFERRED`
- `UNKNOWN_BUT_ACCESSIBLE`
- `UNKNOWN_REQUIRES_SCAFFOLDING`

### 2.3 必须复用的 mastery ladder

来自 PEOS：

```text
UNKNOWN
→ HEARD_OF
→ RECOGNIZES
→ CAN_EXPLAIN
→ CAN_APPLY_WITH_SUPPORT
→ CAN_APPLY_INDEPENDENTLY
→ CAN_TRANSFER
→ CAN_CRITIQUE
→ CAN_TEACH
→ CALIBRATED_MASTERY
```

`cognitive_band` 与 `mastery_level` 是两个不同轴。比如：

- 用户明确说“听过贝叶斯”，可为 `KNOWN_SAID + HEARD_OF`；
- 用户从未说“negative control”，但能稳定正确使用对照和反事实，可为 `UNKNOWN_BUT_ACCESSIBLE` 或经进一步 probe 后转为 `KNOWN_UNSAID_INFERRED`；
- 用户自称“会某概念”也不自动等于 `CALIBRATED_MASTERY`。

## 3. 第一性原理模型

认识状态的主键是：

```text
user_scope
× concept_ref
× domain_scope
× context_scope
× valid_time
× model_version
```

因此禁止以下压缩：

- 把一个领域的掌握迁移成全局人格/能力结论；
- 把一次成功变成永久 mastery；
- 把未观察到当成“不知道”；
- 把用户直接陈述和模型推断混成同一种证据；
- 把“可以理解”误写成“已经知道”；
- 把外部 ontology 的分类当成本项目 canonical identity；
- 把论文引用数当成技能有效性；
- 把过去市场经验当成当前 regime 下仍有效。

## 4. 多轴状态模型

每个 EpistemicStateProjection 至少保留以下独立轴。

### 4.1 cognitive_band

#### KNOWN_SAID

直接 evidence 至少来自：

- user explicit assertion / correction / confirmation；
- user authored artifact；
- 明确地向系统展示或解释该概念；
- 明确完成针对该概念的验证任务。

`KNOWN_SAID` 只证明“用户显式表达过”，不单独证明 mastery。

#### KNOWN_UNSAID_INFERRED

必须同时满足：

1. 没有相反 explicit evidence；
2. 有可追溯的 repeated performance、行为结构或强 prerequisite evidence；
3. domain/context 范围明确；
4. inference confidence 达到当前 policy 阈值；
5. 不能仅由 embedding/topic similarity 产生；
6. 能被用户纠正、撤销或降级。

输出仍必须标 `INFERRED`，绝不伪装成用户说过。

#### UNKNOWN_BUT_ACCESSIBLE

含义不是“用户不知道”，而是：

> 当前没有足够证据确认已掌握，但 prerequisites、transfer evidence、terminology distance 与 explanation bridge 显示，该概念可在低脚手架成本下被理解或验证。

必须允许 `UNOBSERVED` 子状态，以表达“未讨论过所以不知道其真实 mastery”。

#### UNKNOWN_REQUIRES_SCAFFOLDING

至少一种原因：

- `MISSING_PREREQUISITE_CHAIN`
- `MISSING_TERMINOLOGY_BRIDGE`
- `OUT_OF_DOMAIN_OR_OOD`
- `INSUFFICIENT_EVIDENCE`
- `COMPLEXITY_ABOVE_VALIDATED_SUPPORT`
- `DOMAIN_SHIFT`
- `STALE_MASTERY_EVIDENCE`
- `UNMAPPED_CONCEPT_IDENTITY`
- `TOOL_OR_DATA_PREREQUISITE_MISSING`

系统必须输出所缺脚手架，不能只输出一个负面标签。

### 4.2 evidence_mode

建议枚举：

- `USER_EXPLICIT`
- `USER_CORRECTION`
- `USER_AUTHORED_ARTIFACT`
- `DIRECT_TASK_DEMONSTRATION`
- `REPEATED_BEHAVIORAL_EVIDENCE`
- `PREREQUISITE_INFERENCE`
- `CROSS_CONTEXT_TRANSFER_EVIDENCE`
- `MODEL_INFERENCE`
- `UNOBSERVED`
- `UNKNOWN`

证据优先级：

```text
USER_CORRECTION / USER_EXPLICIT
> DIRECT_TASK_DEMONSTRATION
> REPEATED_BEHAVIORAL_EVIDENCE
> CROSS_CONTEXT_TRANSFER_EVIDENCE
> PREREQUISITE_INFERENCE
> MODEL_INFERENCE
> PURE_SIMILARITY
```

纯相似度只能触发检索/候选，不得直接晋升认识状态。

### 4.3 calibration / confidence

置信度必须能够被历史 user correction 和验证任务回测。

至少保留：

- `confidence`
- `confidence_basis`
- `calibration_status`
- `false_known_risk`
- `false_unknown_risk`
- `abstention_reason`

高风险或低证据时允许 `ABSTAIN`。

### 4.4 prerequisite coverage

不能只看语义相似。需要显式回答：

- 已掌握前置概念有哪些；
- 哪些前置节点只是 inferred；
- 哪些节点缺失；
- 是否存在循环 prerequisite；
- 当前领域下前置关系是否有效；
- 是否存在更短 explanation bridge。

### 4.5 temporal / freshness

至少支持：

- `CURRENT`
- `HISTORICAL`
- `STALE`
- `REVALIDATION_REQUIRED`
- `SUPERSEDED`
- `RETRACTED`
- `DRIFT_DETECTED`

工程 API、金融规则、政策、模型版本、市场机制等快速变化知识不得永久保持 CURRENT。

## 5. 图结构

### 5.1 ConceptGraph

节点可引用：

- Concept
- Definition
- Theory
- Mechanism
- ProfessionalTerm
- Method
- Skill
- FailureMode
- Case
- Tool
- Dataset
- Standard
- Paper
- InstitutionFramework
- DomainObject

语义边至少包括：

- `BROADER_THAN`
- `NARROWER_THAN`
- `RELATED_TO`
- `EXACT_MATCH`
- `CLOSE_MATCH`
- `PART_OF`
- `IS_A`

### 5.2 SkillCapabilityGraph

复用 Skill Registry / MethodMemory，不创建第二技能系统。

边：

- `PREREQUISITE_OF`
- `ENABLES`
- `APPLIES_TO`
- `ASSESSED_BY`
- `PRACTICED_BY`
- `FAILS_UNDER`
- `REQUIRES_TOOL`
- `REQUIRES_DATA`
- `CONFLICTS_WITH`
- `ALTERNATIVE_TO`

### 5.3 EvidenceGraph

边：

- `EXPLICITLY_STATED_BY`
- `DEMONSTRATED_BY`
- `INFERRED_FROM`
- `SUPPORTED_BY`
- `WEAKENED_BY`
- `CONTRADICTED_BY`
- `CORRECTED_BY`
- `SUPERSEDED_BY`
- `REVALIDATED_BY`
- `DERIVED_FROM`

### 5.4 FrontierGraph

输出两个关键 frontier：

#### NEXT_ACCESSIBLE_FRONTIER

尚未确认 mastery，但：

- prerequisites 充分；
- terminology distance 较低；
- 有 explanation bridge；
- 学习/研究价值高；
- 证据成本与认知成本在 budget 内。

#### SCAFFOLDING_FRONTIER

尚不可直接解释，需要先补：

- prerequisite concept；
- bridge concept；
- concrete example；
- visual/analogy bridge；
- data/tool literacy；
- domain terminology；
- evidence/revalidation。

## 6. External Crosswalk Registry

外部框架永远是 adapter / candidate mapping，不是本地 truth owner。

### 6.1 W3C SKOS

吸收：

- broader/narrower/related；
- exactMatch / closeMatch / broadMatch / narrowMatch / relatedMatch；
- `closeMatch` 非传递，防止多个词表跨接时 compound mapping error；
- `exactMatch` 只在高置信等价时使用。

因此本系统禁止：

```text
A closeMatch B
B closeMatch C
=> 自动推出 A closeMatch C
```

来源：
- https://www.w3.org/TR/skos-primer/

### 6.2 W3C PROV-O

吸收 Entity / Activity / Agent 与 derived/provenance semantics，作为 SourceEpisode / KnowledgeAtom provenance 的 crosswalk 参考。

来源：
- https://www.w3.org/TR/prov-o/

### 6.3 SHACL

吸收“data graph + shapes graph + validation report”思路，用于未来图约束和 fail-closed validation。

重点：SHACL validation 过程中 data graph 与 shapes graph 不应被修改，可借鉴为 projection validator 的 mutation isolation 原则。

来源：
- https://www.w3.org/TR/shacl/
- https://www.w3.org/TR/shacl12-core/

### 6.4 OWL 2 Open World

关键工程映射：

> missing fact may simply be missing, not false.

因此：

`NO_EVIDENCE_OF_KNOWLEDGE != EVIDENCE_OF_USER_NOT_KNOWING`

来源：
- https://www.w3.org/TR/owl-primer/

### 6.5 O*NET

O*NET Content Model把 worker/job 信息拆成 abilities、skills、knowledge、education、work activities、work context、tasks 等层级。

工程吸收：

- 不把 Skill / Knowledge / Ability / Task / Activity 混成一种 node；
- parent-child hierarchy 可作为 domain adapter；
- occupation relationship 只提供外部先验，不代表用户能力。

来源：
- https://www.onetcenter.org/content.html
- https://www.onetcenter.org/competencyFrameworks.html

### 6.6 ESCO

ESCO v1.2.1 有 skills/knowledge/occupations、多语言 preferred/non-preferred terms、skill hierarchy 与 occupation relationship。

工程吸收：

- multilingual alias；
- knowledge 与 skill/competence 分型；
- occupation-to-skill relationship；
- external mapping 保留版本。

来源：
- https://esco.ec.europa.eu/

### 6.7 1EdTech CASE 1.1

吸收：

- competency framework GUID；
- parent-child hierarchy；
- cross-framework association；
- rubric / performance criterion；
- REST/JSON exchange model。

来源：
- https://standards.1edtech.org/case/

### 6.8 FIBO

金融领域优先 crosswalk 到 FIBO，而不是让 LLM临时发明金融概念 identity。

FIBO 是行业协作治理的 OWL ontology，提供 machine-readable 概念和关系，并有 Production / Development release 机制。

工程吸收：

- domain modularization；
- quarterly release / drift tracking；
- formal relation semantics；
- finance ontology adapter。

来源：
- https://edmcouncil.org/financial-industry-business-ontology/
- https://spec.edmcouncil.org/fibo/

### 6.9 OpenAlex

用于 Research Frontier Scanner。

当前 OpenAlex aboutness 层级：

```text
4 domains
→ 26 fields
→ 252 subfields
→ 4,516 topics
```

每个 work 可有 topics、references、incoming citations、related works。

工程吸收：

- topic neighborhood；
- citation neighborhood；
- classic vs recent frontier；
- related work discovery；
- topic assignment是 inferred，不能作为 truth。

来源：
- https://help.openalex.org/data/topics/
- https://help.openalex.org/data/works/citations/

### 6.10 Microsoft GraphRAG

可借鉴：

- entities / relationships / claims extraction；
- hierarchical communities；
- community summaries；
- local/global retrieval。

但其 graph extraction 本身是 LLM/NLP derived projection，不是事实 authority；Standard 方法成本较高，FastGraphRAG 更便宜但更噪。

因此默认策略：

- 不全量复制 GraphRAG 成第二知识库；
- 只在大语料 global sensemaking 或 frontier mapping 有明确 VOI 时建立可重建投影；
- raw W3 evidence 保持 canonical。

来源：
- https://microsoft.github.io/graphrag/

## 7. 学习状态与知识追踪研究吸收

### 7.1 Bayesian Knowledge Tracing

Corbett & Anderson (1995) 的核心价值不是让我们照搬四参数模型，而是：

- mastery 是 latent state；
- 需要从连续表现估计；
- 个体练习路径可由 mastery estimate 调整。

映射：认识状态应是时序、概率、可更新，而非永久标签。

### 7.2 Deep Knowledge Tracing

Piech et al. (NeurIPS 2015) 说明序列模型可从学生交互学习更复杂的知识状态结构。

映射：未来可研究更复杂 state estimator，但首阶段不能让黑盒模型成为 user knowledge authority。

### 7.3 AKT

Ghosh et al. (KDD 2020) 将 attention 与 Rasch/psychometric components 结合，并强调 interpretability 对 personalized learning 的价值。

映射：如果未来用 learned estimator，必须同时保存可解释 prerequisite/evidence path，不能只输出 latent embedding。

### 7.4 prerequisite relation learning

NAACL 2021 的 heterogeneous graph prerequisite work表明，前置关系可以从多种 features/weak supervision 学习。

映射：机器发现的 prerequisite edge 只能为 `CANDIDATE_PREREQUISITE`，必须经过 source/validation 或用户/任务证据提升，不能一开始就是 canonical relation。

### 7.5 calibration / selective prediction / open world

- Guo et al. (ICML 2017): model confidence 可明显失准；
- Geifman & El-Yaniv (NeurIPS 2017): selective classification 用 coverage 换 risk；
- Bendale & Boult (CVPR 2015): unknown 应是有效输出，系统需处理 novel categories；
- conformal prediction 文献：可提供 distribution-free uncertainty set 思路，但在非 exchangeable / drift 环境仍需保守解释。

映射：

- `ABSTAIN` 是合法输出；
- 不强制每个 concept 进入四层之一；
- inference confidence 必须校准；
- OOD/unmapped 概念先进入 unknown registry。

### 7.6 Active Learning

Settles survey 的核心启示：不是平均询问，而是选择最有信息增益的样本/问题。

映射到 Active Discovery Planner：当状态不确定时，以最低认知成本选择一个 probe。

## 8. Active Discovery Planner

候选 probe：

- `CLARIFY`: 直接问用户是否熟悉；
- `RECOGNITION`: 给概念名/定义做识别；
- `EXPLAIN_BACK`: 让用户简述机制；
- `MICRO_APPLY`: 小题应用；
- `TRANSFER`: 新情境迁移；
- `COUNTEREXAMPLE`: 找失效条件；
- `SOURCE_CHECK`: 查外部证据；
- `PREREQUISITE_CHECK`: 验证缺口节点。

选择函数至少考虑：

```text
Expected Information Gain
× Materiality
× Future Reuse
÷ User Cost
÷ Tool/Latency Cost
```

但首阶段只冻结接口，不固化任意未经验证的数值公式。

与 DS-03 Value of Information 连接，允许 `STOP_PROBING`。

## 9. Research Frontier Scanner

目标不是“论文越新越好”，而是建立 evidence-bounded research neighborhood。

### 9.1 输入

- current concept / method / skill；
- OpenAlex topic/subfield/field/domain；
- seminal source refs；
- publication time window；
- venue/source class；
- current unanswered questions；
- negative evidence需求。

### 9.2 输出

- `FOUNDATIONAL_WORK`
- `HIGH_QUALITY_REVIEW`
- `RECENT_FRONTIER_WORK`
- `ADJACENT_TOPIC`
- `COUNTEREVIDENCE_OR_FAILURE`
- `NEW_TERM`
- `ORPHAN_TERM`
- `POTENTIAL_METHOD`
- `REVALIDATION_TRIGGER`

### 9.3 防止文献动物园

任何新术语进入 Gap Compiler，必须归类为：

- `EXISTING_SKILL_SUBCAPABILITY`
- `CANDIDATE_INDEPENDENT_SKILL`
- `REFERENCE_ONLY`
- `REJECTED`
- `UNKNOWN_NEEDS_RESEARCH`

不允许“论文里出现过”直接变成 Skill。

## 10. 金融与周期问题

### 10.1 FIBO 负责概念对齐，不负责 alpha

FIBO 可帮助定义证券、实体、关系、市场概念，但不证明策略有效。

### 10.2 Regime 是 validity 维度

Ang & Timmermann关于金融 regime change 的研究支持将市场关系视为可能出现 abrupt and persistent change。

因此市场方法的认识图必须区分：

- `HISTORICALLY_KNOWN`
- `CURRENTLY_VALIDATED`
- `REVALIDATION_REQUIRED`

### 10.3 研究过拟合门

White Reality Check 与 Probability of Backtest Overfitting 的核心作用是提醒：大量试验后出现的赢家可能只是 selection artifact。

因此：

- `我知道一个方法` 不等于 `该方法在A股当前周期有效`；
- `用户理解该方法` 与 `策略有效性` 完全分离；
- 新研究进入技能系统前经过 DS-10 多重检验与过拟合审计。

## 11. Explanation Bridge

同一 concept truth 不变，但 explanation depth 可根据 projection 调整。

### KNOWN_SAID

- 少解释定义；
- 更快进入边界、反例、组合和新信息。

### KNOWN_UNSAID_INFERRED

- 用一句 bridge 先校验；
- 不重复基础课；
- 若用户纠正，立即重估。

### UNKNOWN_BUT_ACCESSIBLE

- 用已知概念作桥；
- 先给直观机制，再给专业术语；
- 允许一个快速 probe。

### UNKNOWN_REQUIRES_SCAFFOLDING

- 先展示 prerequisite path；
- 一次只跨一个或少量结构节点；
- 可用案例、图、类比，但 analogy 标记 non-evidentiary；
- 不因用户暂时不懂而永久降低 mastery。

## 12. 与现有技能联动

### PEOS #61

复用：

- PersonalCognitiveModel；
- state/trait/context/domain 分离；
- user correction；
- mastery ladder；
- calibration；
- metacognitive monitoring/control。

### Cognitive Closed Loop #282

复用：

- retrieval-before-write；
- retrieval-before-answer；
- KnowledgeAtom / Unknown / Conflict；
- CURRENT/HISTORICAL；
- ContextBundle；
- W3 canonical truth。

### Method Discovery #312

复用：

- ProblemSignature；
- MethodMemory；
- SkillManifest；
- USER_COGNITIVE_BRIDGE；
- Active Evidence Retrieval；
- Effective Challenge；
- ABSTAIN。

### Gap Compiler #63

复用：

- ORPHAN_TERM；
- GHOST_CAPABILITY；
- maturity states；
- candidate skill generation；
- source validation；
- A股制度映射。

### Decision Science

- DS-01：frame 当前要理解/解决的问题；
- DS-02：belief / confidence / calibration；
- DS-03：Value of Information；
- DS-10：研究过拟合；
- DS-11：regime / drift；
- DS-12：结果归因与 feedback。

## 13. 关键验收故事

### A. Explicit ≠ mastery

用户说“我知道贝叶斯公式”。

系统：
- `KNOWN_SAID`；
- mastery 不能自动高于证据支持；
- 后续应用失败时更新 mastery，不删除 explicit historical evidence。

### B. Inferred but correctable

用户从未说“我懂控制变量”，但多次在独立任务中正确要求控制变量、基准率、最强反方和时间尺度。

系统可以产生：
- domain-scoped `KNOWN_UNSAID_INFERRED` candidate；
- evidence refs；
- confidence；
- invalidate conditions。

用户说“其实控制变量我不会”，user correction 优先，状态立即修正。

### C. Accessible frontier

用户已能应用控制变量和反事实，但没听过 `negative control`。

系统：
- 不写“已知”；
- 进入 `UNKNOWN_BUT_ACCESSIBLE`；
- explanation bridge = `控制变量 → 负对照用于检测伪关联/系统性偏差`；
- 可用一个 micro-apply probe 验证。

### D. Scaffolded frontier

新概念依赖用户从未接触的多个数学前置。

系统：
- `UNKNOWN_REQUIRES_SCAFFOLDING`；
- 输出最短 prerequisite path；
- 不对用户做固定能力评价。

### E. Unobserved ≠ unknown

完全没有相关对话证据。

系统：
- `UNOBSERVED / ABSTAIN`；
- 不强行写 `UNKNOWN_TO_USER`。

### F. Cross-domain negative transfer

金融中会贝叶斯更新，不自动推断医学诊断 mastery。

可生成 transfer candidate，但需 domain-specific evidence。

### G. Stale technical knowledge

用户曾掌握旧版 API，但新版本 breaking change。

系统：
- historical mastery 保留；
- current 状态 `REVALIDATION_REQUIRED`；
- 优先召回官方新文档。

### H. External ontology conflict

O*NET、ESCO、CASE 对一个技能术语分类不完全一致。

系统：
- 保存各自 concept identity；
- 使用 exact/close/broad/narrow mapping；
- 不强制 merge。

### I. Research frontier

OpenAlex 找到一个近期高引用/高相关论文。

系统：
- `DISCOVERED` evidence；
- 追踪 references / citations / related works；
- Gap Compiler 判定是否已有方法；
- 不能直接晋升 Formal Skill。

### J. Market regime

一个历史上有效方法在制度/市场状态变化后失效。

系统：
- 方法知识仍可 `KNOWN_SAID`；
- method health `REVALIDATION_REQUIRED/DEGRADED`；
- 当前交易决策不得因用户熟悉而自动调用。

## 14. 评测体系

### 14.1 cognitive state

- Cognitive Band Precision / Recall
- False Known Rate
- False Unknown Rate
- Inference Overreach Rate
- User Correction Latency
- Mastery Calibration
- Useful Abstention Rate

### 14.2 prerequisite / frontier

- Prerequisite Violation Rate
- Missing Prerequisite Rate
- False Prerequisite Rate
- Next-Frontier Utility
- Scaffold Completion Rate
- Cross-domain Negative Transfer Rate

### 14.3 mapping / source

- Crosswalk False-Merge Rate
- Exact-vs-Close Mapping Confusion Rate
- Provenance Coverage
- External Ontology Drift Detection
- Stale Knowledge Reactivation Rate

### 14.4 research frontier

- Frontier Precision@K
- Frontier Novelty@K
- Foundational Source Recall
- Counterevidence Recall
- Orphan Term Recall
- Duplicate Skill Proposal Rate

### 14.5 system economics

- context/token cost
- retrieval latency
- probe burden
- user interruption cost
- GraphRAG/indexing cost when enabled

## 15. 首阶段边界

本阶段只冻结：

- architecture；
- machine-readable skill contract；
- research validation matrix；
- adversarial acceptance stories。

明确不实现：

- production private-memory bridge；
- autonomous user-profile writer；
- learned KT model runtime；
- full GraphRAG private corpus duplication；
- automatic ontology merge；
- automatic formal-skill promotion；
- live trading；
- user-sensitive trait inference。

## 16. 成熟度

```yaml
architecture_blueprint: CANDIDATE
skill_contract: CANDIDATE
research_validation: CANDIDATE
w3_runtime: REUSE_ONLY
peos_mastery_authority: REUSE_ONLY
formal_skill_authority: REUSE_ONLY
learned_state_estimator: NOT_IMPLEMENTED
external_crosswalk_runtime: NOT_IMPLEMENTED
research_frontier_runtime: NOT_IMPLEMENTED
active_probe_runtime: NOT_IMPLEMENTED
production_private_memory: NOT_AUTHORIZED
live_trading: PROHIBITED
```

## 17. 升级门

只有满足以下条件才能从候选蓝图继续进入 runtime slice：

1. 第三窗口 independent review ACCEPT；
2. 与 #61/#282/#312/#63 无 authority 重叠；
3. explicit/inferred/unknown 证据边界可机器验证；
4. `UNOBSERVED` 与 `UNKNOWN` 分离；
5. user correction 能覆盖 inference；
6. prerequisite graph 对循环、错误边、跨域 transfer 有 fail-closed 设计；
7. external crosswalk 不创建 identity merge authority；
8. research frontier 输出进入 Gap Compiler，不自动晋升；
9. sensitive profile inference 保持禁止；
10. `ABSTAIN` 与 UNKNOWN 是合法输出。
