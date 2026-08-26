# 认识状态与知识前沿映射研究验证矩阵 v1.0

> `module_id: EPISTEMIC-KNOWLEDGE-STATE-FRONTIER-MAPPING-0013`
>
> `implementation_issue: #457`
>
> `boundary: research_only / architecture_contract_eval / NO_TRADE`

## 1. 用途

本矩阵把官方标准、真实工程项目、教育/认知建模研究、知识图谱实践、学术检索基础设施和金融机构级语义/验证方法映射到 `EPISTEMIC-KNOWLEDGE-STATE-AND-FRONTIER-MAPPING-SKILL-0013`。

目标不是堆论文名词，而是回答：

- 哪些设计已有强支持；
- 哪些只能作为可迁移工程方法；
- 哪些仍是本项目假设；
- 哪些必须保留 UNKNOWN；
- 每个外部来源能支持什么、不能证明什么；
- 与现有第二大脑技能应该怎么联动而不创建第二 authority。

## 2. 证据等级

- `A_STRONG`: 正式标准、经典/多项高质量研究或成熟基础设施直接支持设计原则；
- `B_TRANSFER_REQUIRED`: 原领域证据较强，但迁移到个人第二大脑需要本项目验证；
- `C_ENGINEERING_HYPOTHESIS`: 有合理研究/真实项目支持，具体算法/阈值尚未证明；
- `D_LONG_TERM_RESEARCH`: 仅登记研究方向、接口、停止条件，不承诺效果。

## 3. Knowledge organization / ontology / provenance

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| 区分 broader/narrower/related 与跨词表 mapping | W3C SKOS Primer/Reference | A | 可用标准关系组织概念与跨框架映射 | 两个相似标签必然同义 | 建 `EXACT_MATCH/CLOSE_MATCH/BROADER/NARROWER/RELATED`; close mapping 不做传递闭包 |
| provenance 是一等对象 | W3C PROV-O | A | 异构系统可共享 Entity/Activity/Agent 派生关系 | provenance 本身证明来源可信或结论正确 | 只做 SourceEpisode/KnowledgeAtom provenance crosswalk |
| 图约束应有独立 shapes/validation report | W3C SHACL | A/B | RDF 图可被形式化约束和验证；validation input 应保持不变 | 本项目必须使用 RDF/SHACL runtime | 借鉴 immutable validation、constraint report、fail-closed；首阶段不强制 RDF migration |
| 缺失事实不是自动为假 | W3C OWL 2 open-world assumption | A | knowledge representation 可明确区分 missing vs false | 用户一定知道所有未观察概念 | 固化 `UNOBSERVED != UNKNOWN_TO_USER`; 缺证据时允许 ABSTAIN |

### 3.1 一手来源

- W3C SKOS Primer: https://www.w3.org/TR/skos-primer/
- W3C PROV-O: https://www.w3.org/TR/prov-o/
- W3C SHACL Recommendation: https://www.w3.org/TR/shacl/
- W3C SHACL 1.2 Core Working Draft: https://www.w3.org/TR/shacl12-core/
- W3C OWL 2 Primer: https://www.w3.org/TR/owl-primer/

### 3.2 关键结论

1. 本系统最危险的错误之一是 `not observed -> user does not know`。Open-world 设计直接要求保留未观测状态。
2. Crosswalk 不能只靠 embedding。SKOS 的 exact/close 区分非常适合限制外部 taxonomy 的错误合并。
3. 图投影必须能被独立 validator 检查，且 validation 不应修改输入 evidence graph。
4. Provenance 不等于 truth，但没有 provenance 的认识状态不应升为高置信。

## 4. Competency / skill framework

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| Knowledge/Skill/Ability/Task/Activity 分型 | O*NET Content Model | A/B | 成熟职业信息系统长期以多层 taxonomy 分离 worker/job constructs | O*NET 分类适合所有个人知识与中国场景 | 用作 external adapter，禁止把所有能力压成单一 Skill 节点 |
| machine-readable competency hierarchy | O*NET competency frameworks / CTDL ASN | B | 层级 competency 可机器交换 | O*NET hierarchy 就是本系统 prerequisite graph | 只作为候选 taxonomy/crosswalk |
| 多语言 skills/knowledge/occupation graph | ESCO v1.2.1 | A/B | 大规模技能与知识概念可有 hierarchy、别名和 occupation relations | ESCO relevance 等于用户掌握或A股有效性 | 用于 multilingual alias、skill/knowledge typing、external relationships |
| GUID、parent-child、cross-framework association、rubric | 1EdTech CASE 1.1 | A/B | 教育 competency framework 可跨平台稳定引用和对齐 | CASE 可直接替代 PEOS mastery/skill authority | 借鉴 framework identity、association、rubric，保留本地 authority |

### 4.1 当前官方事实

- O*NET 31.0 Content Model Reference 当前包含 3,006 rows，Element ID 编码 parent-child hierarchy。
- O*NET 明确分 Abilities、Skills、Knowledge、Education、Tasks、Work Activities、Work Context 等结构。
- ESCO v1.2.1 当前 skills pillar 有 13,939 concepts，分 Knowledge、Language skills and knowledge、Skills、Transversal skills，并维护多语言术语与 occupation relationships。
- CASE 1.1 是 Final 标准，定义 competency frameworks、items、associations、rubrics 与 REST/JSON exchange。

### 4.2 一手来源

- O*NET Content Model: https://www.onetcenter.org/content.html
- O*NET 31.0 Content Model Reference: https://www.onetcenter.org/dictionary/31.0/csv/content_model_reference.html
- O*NET Competency Frameworks: https://www.onetcenter.org/competencyFrameworks.html
- ESCO: https://esco.ec.europa.eu/
- CASE 1.1: https://standards.1edtech.org/case/

### 4.3 工程结论

“用户会什么”不能只有一张 Skill 表。至少应区分：

```text
concept knowledge
skill/procedure
ability/capacity evidence
task/application
method
professional terminology
tool/data prerequisite
```

但这些 external taxonomies 只负责帮助对齐概念，不拥有用户 mastery truth。

## 5. Knowledge tracing / learner modeling

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| mastery 是动态 latent state | Corbett & Anderson 1995 BKT | A/B | 可从连续练习表现更新技能掌握概率 | BKT 参数适合开放领域聊天 | 认识状态必须时序化、概率化、可纠正；不照搬固定参数 |
| sequence interaction 能学习更复杂 knowledge state | Piech et al. Deep Knowledge Tracing, NeurIPS 2015 | B | 序列模型可预测未来表现并发现课程结构 | 黑盒 hidden state 等于真实用户知识 | learned estimator 未来只能是 candidate projection，证据链仍必需 |
| attention + psychometric inductive bias | Ghosh et al. AKT, KDD 2020 | B | 更复杂时序模型可兼顾性能与部分解释性 | AKT 可直接用于跨主题个人第二大脑 | future estimator research，首阶段只冻结接口 |
| concept prerequisite 可由 heterogeneous evidence 学习 | NAACL 2021 prerequisite relation learning | B/C | 多源 features + weak supervision 可发现 prerequisite candidate | 自动学到的 edge 就是 canonical prerequisite | 输出必须为 `CANDIDATE_PREREQUISITE`，独立验证后才提升 |

### 5.1 来源

- Corbett & Anderson, *Knowledge tracing: Modeling the acquisition of procedural knowledge*, User Modeling and User-Adapted Interaction, 1995, DOI 10.1007/BF01099821.
- Piech et al., *Deep Knowledge Tracing*, NeurIPS 2015: https://proceedings.neurips.cc/paper/2015/hash/bac9162b47c56fc8a4d2a519803d51b3-Abstract.html
- Ghosh, Heffernan, Lan, *Context-Aware Attentive Knowledge Tracing*, KDD 2020: https://kdd.org/kdd2020/accepted-papers/view/context-aware-attentive-knowledge-tracing.html
- Liu et al., *Heterogeneous Graph Neural Networks for Concept Prerequisite Relation Learning in Educational Data*, NAACL 2021: https://aclanthology.org/2021.naacl-main.164/

### 5.2 迁移风险

教育 KT 通常有：

- 明确题目；
- 明确技能标签；
- 高频反馈；
- 相对封闭 curriculum；
- 可观察的对错。

第二大脑面对：

- 开放域；
- 用户表达不一定是测试；
- 概念标签会漂移；
- 任务成功可能依赖工具/外部资料；
- 用户可能故意简化、玩笑、角色扮演；
- 大量知识没有可观测练习。

因此 KT 只提供“状态应动态更新”的结构启示，不能直接拿教育预测 AUC 证明本系统 user model 有效。

## 6. Calibration / abstention / open-world unknown

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| model confidence 需要校准 | Guo et al. ICML 2017 | A/B | 现代神经网络可明显 miscalibrated，temperature scaling 可改善很多 benchmark | 一个 calibration method 对本系统长期有效 | 对 cognitive inference 做 empirical calibration；不信任模型自报 confidence |
| 允许拒判可降低高风险错误 | Geifman & El-Yaniv, NeurIPS 2017 | A/B | selective classification 通过 coverage-risk tradeoff 控制风险 | 论文的 risk guarantee 自动迁移到开放聊天 | `ABSTAIN` / `UNOBSERVED` 作为一等结果 |
| unknown class 必须合法 | Bendale & Boult, CVPR 2015 Open World Recognition | A/B | operational systems应检测 novel/unknown 而非硬塞入 closed set | CV classifier方法可直接分类概念未知 | unmapped/OOD concept 先入 Unknown Registry |
| distribution-free uncertainty set 思路 | conformal prediction literature | B/C | 在满足假设时可提供明确 coverage 的 uncertainty set | 非平稳个人知识/金融环境无条件满足 exchangeability | future confidence-set research；drift/regime 时必须降级 |

### 6.1 来源

- Guo et al., *On Calibration of Modern Neural Networks*, ICML 2017.
- Geifman & El-Yaniv, *Selective Classification for Deep Neural Networks*, NeurIPS 2017.
- Bendale & Boult, *Towards Open World Recognition*, CVPR 2015.
- Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, 2021.

### 6.2 系统要求

至少分别测：

- False Known Rate；
- False Unknown Rate；
- coverage；
- confidence calibration；
- user correction latency；
- useful abstention；
- cross-domain negative transfer。

不能用一个“准确率”吞掉这些风险。

## 7. Active Learning / Value of Information

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| 主动选择最有信息的 probe | Settles Active Learning Survey | A/B | 在标注成本存在时，主动选样可比平均采样高效 | 任意聊天中主动提问都值得 | 与 DS-03 VOI 联动，只有 expected value > user interruption cost 才 probe |
| probe 不是考试，而是证据获取 | active learning + metacognitive control | B | 可通过最小任务减少状态不确定性 | probe结果是永久 mastery | probe evidence 仍 domain/context/time scoped |

Probe优先级不是固定公式，v1只冻结维度：

```text
information gain
materiality
future reuse
user burden
tool/latency cost
privacy/permission
```

## 8. Research frontier / scholarly graph

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| topic hierarchy + citation graph 做研究导航 | OpenAlex | A/B | 可用 topic / references / citations / related works构建研究邻域 | topic自动推断绝对正确；引用高=结论正确 | Research Frontier Scanner，所有结果都是 evidence candidates |
| graph extraction + community summaries 做大语料 sensemaking | Microsoft GraphRAG | B/C | 实际项目支持实体/关系/claim抽取、Leiden communities、local/global query | LLM抽取图是事实源；适合所有私有语料 | 可重建 projection；W3 source truth不变；高成本任务才启用 |

### 8.1 OpenAlex 当前结构

OpenAlex 当前 aboutness hierarchy：

```text
4 domains
26 fields
252 subfields
4,516 topics
```

Works 同时保存：

- `referenced_works`；
- incoming citations / `cited_by_count`；
- `related_works`；
- topics / primary_topic；
- publication metadata。

这非常适合作为“基础论文 → 当前前沿 → 相邻领域 → 反向引用”发现入口。

来源：
- https://help.openalex.org/data/topics/
- https://help.openalex.org/data/works/citations/

### 8.2 GraphRAG 成本/权威边界

Microsoft 当前 GraphRAG docs：

- Standard pipeline 用 LLM抽取 entity/relationship，并可选 claim extraction，再做 community summary；
- FastGraphRAG 用 NLP/co-occurrence 降成本，但图更噪；
- 官方说明 graph extraction 约占 standard indexing cost 的 75%。

因此本项目不应“为了知识图谱”全量重做 W3。只有需要 global corpus sensemaking、结构发现或复杂 research frontier 时才有 VOI。

来源：
- https://microsoft.github.io/graphrag/index/overview/
- https://microsoft.github.io/graphrag/index/methods/

## 9. Finance ontology / institutional practice / regime

| 设计 | 来源 | 等级 | 支持 | 不支持/不能证明 | 本项目吸收 |
|---|---|---:|---|---|---|
| 金融概念用正式 ontology 对齐 | EDMC FIBO | A/B | 行业 ontology 可精确定义金融概念/关系并跨系统共享 | FIBO提供交易策略或中国A股制度真相 | finance crosswalk；A股制度继续由交易系统 point-in-time rules治理 |
| ontology 应模块化并持续版本化 | FIBO Production/Development releases | A/B | FIBO Production按季度发布并经 SME/hygiene review | 季度频率适合所有本项目 domain | external ontology drift watcher 参考 |
| 反复试验会产生 lucky winner | White Reality Check 2000 | A/B | 数据重复用于模型选择产生 data snooping risk | Reality Check 单独解决所有回测偏差 | Research Frontier/Skill promotion联动 DS-10，保存完整试验族 |
| 回测选择本身可过拟合 | Bailey et al. PBO | B | 可量化策略选择后样本外失效风险的一类方法 | PBO 一个数决定策略有效性 | 与锁箱、成本、制度回放、shadow联合 |
| 金融关系会 regime switch | Ang & Timmermann 2011 | A/B | 均值、波动、相关可在不同 regime 显著变化 | 统计 regime 一定有唯一经济解释 | `HISTORICALLY_KNOWN != CURRENTLY_VALIDATED`; stale methods进入 revalidation |

### 9.1 FIBO 一手来源

- https://edmcouncil.org/financial-industry-business-ontology/
- https://spec.edmcouncil.org/fibo/
- FIBO OWL Production / Development releases: https://spec.edmcouncil.org/fibo/page/owl

FIBO 的重要工程启发：

- 概念、关系、属性分开；
- ontology模块化；
- Production与Development分开；
- 行业 SME review；
- RDF/OWL作为 machine-readable source；
- 可以衍生 SKOS/Data Dictionary，而不是多个平行 truth。

这与我们“W3 canonical + rebuildable projection”的原则高度一致。

## 10. 与现有技能/知识库的联动矩阵

| 本技能子能力 | 复用对象 | 读 | 写/输出 | 不得做 |
|---|---|---|---|---|
| explicit evidence | #282 W3 Source/Knowledge/Memory atoms | yes | provenance refs | 复制 raw private truth 到公开库 |
| inferred cognitive state | #61 PEOS PersonalCognitiveModel | yes | derived projection candidate | 写永久人格标签 |
| mastery | PEOS mastery ladder | yes | reference + calibrated estimate | 创建第二 mastery ladder |
| method/skill prerequisite | #312 MethodMemory / SkillManifest | yes | candidate relation | 创建第二 Skill Authority |
| orphan method discovery | #63 Gap Compiler | yes | candidate finding | 自动生成 Formal Skill |
| active probe | DS-03 VOI + #312 Effective Challenge | yes | evidence request | 无限追问 |
| research frontier | OpenAlex/public web | yes | evidence candidates | 以引用数自动判真 |
| finance crosswalk | FIBO + A股 rule registry | yes | external mapping | FIBO替代A股交易规则 |
| graph sensemaking | GraphRAG-derived projection | optional | rebuildable graph | graph summary成为 canonical truth |
| feedback | #282/#30 OutcomeLearning | yes | SUPPORT/WEAKEN/REVALIDATE | 一次成功直接晋升 |

## 11. 四层状态的研究级解释

### 11.1 KNOWN_SAID

属于 **evidence classification**，不是 competency verdict。

强证据：
- explicit statement/correction；
- user-authored artifact；
- direct targeted demonstration。

风险：用户可能只“听过”、复制过、随口说过。

因此 mastery 独立建模。

### 11.2 KNOWN_UNSAID_INFERRED

属于 **bounded probabilistic inference**。

可使用：
- repeated correct applications；
- transfer across nearby contexts；
- prerequisite closure；
- ability to critique/counterexample；
- successful teach-back。

必须保留：
- evidence refs；
- confidence；
- context/domain；
- opposing evidence；
- user correction path。

### 11.3 UNKNOWN_BUT_ACCESSIBLE

属于 **learning-frontier prediction**，不是 knowledge claim。

主要依据：
- prerequisite coverage；
- semantic/terminology distance；
- nearby mastered structure；
- available explanation bridge；
- observed transfer；
- tool/data prerequisites。

验证优先用低成本 probe。

### 11.4 UNKNOWN_REQUIRES_SCAFFOLDING

属于 **instructional dependency state**。

系统必须具体指出：
- 缺哪个 prerequisite；
- 缺哪个 term bridge；
- 需不需要 example/visual/analogy；
- 需不需要 tool/data literacy；
- 是不会，还是只是没证据/已过时。

## 12. 必须诚实保留的 UNKNOWN

1. 从开放聊天推断 mastery 的最低样本量没有通用答案。
2. “用户知道但没说”的 precision/recall 需要真实用户纠错和长期任务数据校准。
3. 教育 Knowledge Tracing 的参数和结构不能无损迁移到开放式成人跨域知识。
4. prerequisite learning 对非课程型知识的 false edge rate 需本项目测量。
5. 什么 explanation bridge 对特定用户最有效需要 longitudinal evaluation。
6. OpenAlex topic/related works 是机器推断，可能漏掉重要跨领域论文。
7. GraphRAG extracted graph可能 hallucinate/merge错误，必须回到 source text/provenance。
8. ESCO/O*NET/CASE/FIBO 的 identity 与本项目 concept identity 不总是一一对应。
9. 金融 regime 检测存在事后解释、模型选择和延迟风险。
10. cognitive state model 本身可能形成自我实现偏差，必须允许用户查看、纠正、撤销。

## 13. Adversarial validation plan

### 13.1 absence-of-evidence trap

输入：从未谈过概念 X。

错误结果：`UNKNOWN_TO_USER`。

正确结果：`UNOBSERVED/ABSTAIN`，除非另有 direct evidence。

### 13.2 user-correction supremacy

模型多次推断用户会 X，用户明确纠正“我不会”。

当前 projection 必须以 correction 为准，同时历史 inference 留作 calibration failure evidence。

### 13.3 cross-domain contamination

用户能在交易中做 Bayesian update，不可自动得到医学诊断 `CAN_APPLY_INDEPENDENTLY`。

### 13.4 stale competence

曾经熟悉 Python/SDK vOld，但 API breaking change。

历史 mastery 不删除，CURRENT knowledge 标 `REVALIDATION_REQUIRED`。

### 13.5 taxonomy false merge

ESCO `skill A` 与 O*NET `skill B` 名称近似但 scope不同。

必须 `CLOSE_MATCH` 或不映射，不得自动 exact merge。

### 13.6 prerequisite cycle

A prerequisite B, B prerequisite A。

Frontier planner 必须 fail closed 到 `CYCLIC_OR_INVALID`。

### 13.7 high-citation false authority

新论文 citations 高，但结论与更强实验/标准冲突。

Research scanner只产生 candidate + conflict，不自动晋升。

### 13.8 good outcome / bad process

用户偶然答对。

一次 lucky outcome 不能等同掌握。联动 PEOS process/outcome separation。

### 13.9 market regime leak

用户熟悉某策略，历史回测好，但当前制度/流动性变化。

认知 mastery 与 method health 必须分离。

### 13.10 sensitive profile creep

从学习速度、话题或知识缺口推断敏感身份/健康/政治画像。

必须禁止。

## 14. 升级为 contracted capability 前的门

1. 所有四层定义与 #61/#282/#312/IAGL 完全兼容；
2. `UNOBSERVED` 明确存在；
3. explicit evidence 与 inference 机器可区分；
4. user correction 优先级有 adversarial fixture；
5. prerequisite candidate 与 canonical relation 分离；
6. external taxonomy crosswalk exact/close 语义有负面测试；
7. provenance coverage可测；
8. temporal/freshness/regime 能使旧 mastery 与 current validity 分离；
9. Research Frontier Scanner输出只能进入 Gap Compiler；
10. 第三窗口 independent review ACCEPT。

## 15. 当前结论

```yaml
knowledge_organization_model: A_STRONG_TO_B_TRANSFER_REQUIRED
provenance_first: A_STRONG
open_world_unobserved_rule: A_STRONG
competency_crosswalk: B_TRANSFER_REQUIRED
four_band_user_state_projection: C_ENGINEERING_HYPOTHESIS_WITH_EXISTING_PROJECT_PRIOR
knowledge_tracing_transfer: B_TRANSFER_REQUIRED
learned_prerequisite_graph: C_ENGINEERING_HYPOTHESIS
calibrated_inference_and_abstention: A_STRONG_TO_B_TRANSFER_REQUIRED
active_probe_planner: B_TRANSFER_REQUIRED
openalex_research_frontier: B_TRANSFER_REQUIRED
full_private_graphrag_index: C_ENGINEERING_HYPOTHESIS_AND_VOI_GATED
finance_fibo_crosswalk: B_TRANSFER_REQUIRED
regime_aware_current_validity: B_TRANSFER_REQUIRED
formal_skill_promotion: NOT_AUTHORIZED
production_private_runtime: NOT_AUTHORIZED
live_trading: PROHIBITED
```
