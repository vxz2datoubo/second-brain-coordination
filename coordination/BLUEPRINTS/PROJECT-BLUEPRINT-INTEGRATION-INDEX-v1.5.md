# 第二大脑与A股交易研究项目蓝图集成索引 v1.5

> `agent_id: GPT`
>
> `supersedes: PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.4.md`
>
> `new_module: CONVERSATIONAL-LONG-TERM-MEMORY-0021`
>
> `boundary: research_only / NO_TRADE`

## 一、版本目的

v1.5完整继承v1.4对W1-W13、AMED、0013/0017/0018/0019等模块的职责、权威、接口、成熟度和任务顺序，并新增：

`0021 Conversational Long-Term Memory and Mobile Second Brain`。

0021不是W14，不创建新业务工作流。它是W3长期记忆的核心能力扩展，并与W10个人认知/DecisionEpisode、W8多Agent集成、W9结果学习建立正式接口。

现有`0020 Knowledge Source Semantic Reconstruction and Graph Projection`继续承担嘈杂Source的可审计语义重建和派生图谱，0021按需复用。

专项蓝图：

`coordination/BLUEPRINTS/CONVERSATIONAL-LONG-TERM-MEMORY-AND-MOBILE-SECOND-BRAIN-BLUEPRINT-v1.0.md`

## 二、四平面总架构

| 平面 | 工作流 | 核心职责 |
|---|---|---|
| 治理与控制 | W1、W8、W9 | AMED、任务、Agent运维、影子、工程学习 |
| 事实与证据 | W2、W3、W5、W13 | 市场、规则、知识、对话经历、长期记忆、事件、参与者资金证据 |
| 研究与模型 | W4、W6、W12 | 特征、策略、实验、竞争性假设、概率与决策科学 |
| 决策与生存 | W7、W10、W11＋0017/0018 | 认知上下文、配置、风险、验证、净优势与关停 |

0021位于W3，但向W10提供个人长期上下文，并向所有授权项目提供受scope控制的MemoryContextBundle。

## 三、模块登记

| ID | 名称 | 归属 | Issue | 成熟度 |
|---|---|---|---:|---|
| 0010 | Personal Epistemic Cognitive OS | W10 | 61 | CONTRACTED_NOT_IMPLEMENTED |
| 0011 | Kelly-Thorp Expected Value and Capital Allocation | W11 | 62 | CONTRACTED_NOT_IMPLEMENTED |
| 0012 | Decision Science Skill Family | W12 | 63 / PR66 | D0_COMPLETE_PENDING_MERGE |
| 0013 | Intraday Extrema Interval and Weak-Drive State | W4＋W7＋W12 | 188 | CONTRACTED_NOT_IMPLEMENTED_DATA_PENDING |
| 0014 | Daily Participant Capital-Flow Intelligence | W13 | 67 | CONTRACTED_NOT_IMPLEMENTED |
| 0015 | Policy Macro News Cross-Asset Intelligence | W5 | 68 | CONTRACTED_NOT_IMPLEMENTED |
| 0017 | Liquidity Sweep/Reclaim Validation | W4＋W7 | 69 | CONTRACTED_NOT_IMPLEMENTED |
| 0018 | House-Edge Survival and Operating Control | W7＋W9＋W11 | 71 | CONTRACTED_NOT_IMPLEMENTED |
| 0019 | Enterprise Blueprint Convergence | W1 | 72 | ACTIVE_PROJECT_PLAN |
| 0020 | Knowledge Source Semantic Reconstruction and Graph Projection | W3 | 216 | ACTIVE_PROJECT_PLAN |
| 0021 | Conversational Long-Term Memory and Mobile Second Brain | W3＋W10 consumer interface | TBD | BLUEPRINT_COMPLETE_NOT_IMPLEMENTED |

## 四、0021核心定位

用户与ChatGPT的长期对话是第二大脑的重要一等来源，因为用户可以在手机、Web和Desktop随时把真实生活、项目、学习、判断、纠错、计划和未决问题带入系统。

因此0021正式定义：

```text
Conversation Surface
→ ConversationEpisode / SourceManifest
→ （ASR/OCR/口语噪声需要时）MODULE_0020 NormalizedSemanticView
→ W3 LearningPacket / KnowledgeAtom / Relation / Conflict / UNKNOWN
→ W3 Canonical Memory Runtime
→ MemoryRouter / Trust Gate / Hybrid Retrieval
→ MemoryContextBundle
→ ChatGPT / W10 / AI电影 / A股 / 其他授权消费者
```

这不是“聊天备份”，而是第二大脑持续成长的主输入回路之一。

## 五、唯一权威表

v1.4所有权威继续有效，并补充：

| 权威 | 所有者 |
|---|---|
| Conversation Source / Episode / conversational provenance | W3 |
| 用户长期记忆current/historical version | W3 |
| Correction / Supersession / Revocation | W3 |
| MemoryRouter / MemoryContextBundle | W3 |
| 嘈杂Source的NormalizedSemanticView和派生Graph Projection | W3 / MODULE_0020 projection only |
| 当前任务中的个人认知模型与DecisionEpisode | W10 |
| ChatGPT/Agent调用编排 | W8 |
| 记忆使用结果与质量校准 | W9 |

W10、AI电影、A股和其他项目不得创建平行用户长期记忆事实源。

## 六、共享合同新增

在v1.4共享合同基础上新增或扩展：

12. `ConversationSourceManifest`，W3写；
13. `ConversationEpisode`，W3写；
14. `ConversationTurnReference`，W3写；
15. `ConversationMemoryCandidate`，W3写；
16. `TemporalMemoryValidity`，W3写；
17. `MemoryCorrection / Supersession`，W3写；
18. `RecallDecision`，W3 MemoryRouter写；
19. `MemoryTrustDecision`，W3写；
20. `MemoryContextBundle`，W3写，ChatGPT/W10/其他授权消费者读。

若现有Phase 3 / Issue #38已有等价对象，必须REUSE/EXTEND，不得因命名差异重复建Schema。

若Conversation来自语音/ASR/OCR且需要语义修复，复用MODULE_0020的NormalizedSemanticView / NormalizationEdit / provenance映射，不创建第二套Normalization对象。

## 七、跨项目消费规则

### 7.1 用户长期记忆是跨项目资产

它不归AI电影、A股或任何单一项目仓。

### 7.2 最小必要上下文

项目读取长期记忆时至少按：

- user_scope；
- project_scope；
- memory_type；
- time_scope；
- access_policy；
- task relevance；

过滤。

AI电影可以读与创作偏好、既有决定、项目经历和工作方法相关的记忆；默认不需要读取与任务无关的私人关系记录。

A股同理。

### 7.3 一个事实一个canonical identity

同一用户偏好或经历可关联多个项目，但不能复制出彼此独立的“AI电影版记忆”“A股版记忆”和“聊天版记忆”。

## 八、存储边界

### 公开协调仓

`vxz2datoubo/second-brain-coordination`

只保存public-safe：

- 蓝图；
- Schema；
- 程序；
- 测试；
- 治理；
- Agent协作；
- 脱敏receipt。

### 私人W3数据面

现有蓝图建议的：

`second-brain-knowledge-private`

作为W3 private durable knowledge data plane，而不是新运行时。

用于保存真实私人Source/Episode/LearningPacket/Atom export/snapshot/audit/rollback等。

### 业务项目仓

AI电影等项目仓保存项目代码、资产、制作资料和该项目自身交付，通过W3接口引用跨项目用户长期记忆。

## 九、记忆数据模型关键规则

1. Episode与Derived Memory分离；
2. Daily/Weekly/Monthly是派生摘要；
3. 任何长期记忆保留provenance；
4. `valid time`与`record time`分离；
5. current和historical查询分离；
6. correction是一等事件，不静默覆盖历史；
7. candidate-first；
8. conflict/UNKNOWN不得被摘要吞掉；
9. 关系记忆、用户偏好、项目事实、外部事实不得混为同一authority type；
10. Prompt injection不得晋升长期系统规则。

## 十、ChatGPT产品集成分级

### L-A Native / Soft Guarantee

ChatGPT Memory + Reference Chat History + Project Instructions + Apps/GitHub + W3 Recall协议。

适合当前手机优先MVP。

### L-B Custom Memory App / MCP

W3暴露recall/search/fetch/current-profile/open-loops及受控candidate/correction写接口。

### L-C Hard-Guarantee Gateway

所有模型请求必须先通过W3 MemoryRouter和ContextBundle，才允许生成回答。

L-C解决“每次回答前100%必经长期记忆检索”的硬保证问题。

## 十一、首个0021纵向切片

固定验收序列：

1. Session A：用户提供长期信息；
2. 写入ConversationEpisode和candidate memory；
3. Session B：用户不重复信息，系统跨session正确召回；
4. Session C：用户纠正旧信息；
5. 写Correction/Supersession；
6. Session D：current query只返回新状态；
7. Session E：historical query可回到旧状态及其有效期；
8. 全流程有source/provenance/hash；
9. 同时测试跨项目不泄漏和无证据时ABSTAIN。

完成信号：

`CONVERSATIONAL_MEMORY_VERTICAL_SLICE_READY`

## 十二、0021评测门

至少覆盖：

- 信息提取；
- 跨session推理；
- 时间推理；
- 知识更新；
- 正确拒答；
- 隐含约束；
- 用户纠错；
- stale/superseded leakage；
- project bleed；
- conflict/UNKNOWN recall；
- provenance coverage；
- open-loop resolution；
- prompt injection memory；
- negation/exception；
- current vs historical。

核心KPI不是memory count，而是：

- 正确召回；
- 正确更新；
- 正确时间；
- 正确scope；
- 正确拒答；
- 无串库；
- 无凭证泄漏。

## 十三、非重复边界新增

- 0021不建立W3之外的长期记忆系统；
- 0021复用0020的语义重建，不重复Normalization/Graph Projection；
- ChatGPT原生Memory不是W3 durable authority；
- Project Memory不是跨项目用户事实源；
- GitHub私人仓是数据平面，不是第二运行时；
- Scheduled Task是巩固触发器，不是假定的全账号聊天抓取器；
- vector index和memory palace都是可重建投影；
- W10不拥有长期记忆source/version authority；
- AI电影和A股仓不得复制跨项目用户记忆。

## 十四、实施依赖

0021实施前必须核验：

- 最新main和当前控制面；
- PR #57 current canonical runtime；
- Issue #38 knowledge gateway；
- Issue #59 atomization；
- Issue #60 hybrid retrieval；
- Issue #216 / MODULE_0020 semantic reconstruction；
- Issue #209 / E61 durable authority及其当前活动路由；
- OpenAI最新Memory / Projects / Tasks / Apps / MCP能力。

正式写PROJECT/GLOBAL authority不得绕过E61。

## 十五、研究基础

实施任务必须将以下来源分级登记并做REUSE/ADAPT决策：

- OpenAI官方Memory、Projects、Tasks、Apps、MCP文档；
- Generative Agents；
- MemGPT；
- LongMemEval；
- LoCoMo；
- LoCoMo-Plus；
- A-MEM；
- HippoRAG；
- W3C PROV；
- Event Sourcing；
- Bitemporal History；
- 可复现长期记忆开源项目。

## 十六、WIP与执行顺序

0021属于战略级W3能力，但不得盲目覆盖当前活动Codex路由。

截至本次蓝图审计，仓库已存在`CODEX-E61-ACTIVE-ROUTE-CONTRACT.yaml`，因此实施Agent必须先同步最新main并读取实时control plane，不能依赖旧PROGRAM-INDEX中的#72描述。

当控制面允许0021实施时：

1. 建立独立Issue；
2. Codex项目计划模式；
3. 先canonical audit；
4. 只实现首个纵向切片；
5. GPT七门审核；
6. 再释放MemoryRouter/Consolidation/Hybrid Retrieval后续切片。

不允许一次性建设全部MCP、Supabase、图数据库和UI。

## 十七、当前成熟度

```yaml
module_id: CONVERSATIONAL-LONG-TERM-MEMORY-0021
registered: true
workstream: W3
w10_consumer_interface: true
specialized_blueprint: COMPLETE
implementation_issue: TBD
canonical_audit: NOT_STARTED
conversation_source_runtime: NOT_IMPLEMENTED
first_vertical_slice: NOT_IMPLEMENTED
memory_router: NOT_IMPLEMENTED
trust_gate: NOT_IMPLEMENTED
background_consolidation: PARTIAL_TASK_EXISTS
semantic_reconstruction: REUSE_MODULE_0020
private_data_plane: BLUEPRINT_DEFINED_NOT_VERIFIED
formal_authority: E61_DEPENDENT
no_trade: true
```
