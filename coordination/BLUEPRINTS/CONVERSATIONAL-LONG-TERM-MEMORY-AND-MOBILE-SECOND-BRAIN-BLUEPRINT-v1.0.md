# 对话式长期记忆与移动第二大脑蓝图 v1.0

> `agent_id: GPT`
>
> `module_id: CONVERSATIONAL-LONG-TERM-MEMORY-0021`
>
> `short_name: CLTM`
>
> `primary_workstream: W3 Knowledge Authority and Long-Term Memory`
>
> `cross_workstreams: [W10 Personal Epistemic Cognitive OS, W8 Multi-Agent Operations, W9 Outcome Learning]`
>
> `canonical_runtime: EXTEND_EXISTING_W3_ONLY`
>
> `boundary: PRIVATE_BY_DEFAULT / CANDIDATE_FIRST / research_only / NO_TRADE`

## 一、根本定义

本模块不是第二大脑的外挂、聊天备忘录或独立记忆库。

**用户与ChatGPT的长期对话记忆是第二大脑本体的核心能力之一。**

原因不是“聊天很重要”这么简单，而是对该用户而言，ChatGPT是长期、低摩擦、跨设备、尤其是手机端可以随时进入的认知入口。用户会把生活事件、项目进度、观察、疑问、选择、纠错、学习、关系、计划、失败和新认识持续带入对话。若这些经历不能被可靠地保存、消化、纠错、检索和重新用于未来回答，第二大脑就缺少最重要的一条真实人机输入通道。

因此系统目标从“保存聊天”升级为：

```text
用户在手机 / Web / Desktop 与 ChatGPT 自然交流
→ 对话成为正式 Knowledge Source / Experience Source
→ W3 摄入原始 Episode 与派生 Candidate Memory
→ 现有 LearningPacket / KnowledgeAtom / Relation / Conflict / UNKNOWN 链
→ W3 canonical memory runtime
→ 混合检索 + 时间/版本 + 证据/冲突门
→ MemoryContextBundle / AnswerEvidenceBundle
→ ChatGPT 在下一次对话中正确想起、理解并使用过去
→ 新对话、新纠错和新结果继续回灌 W3
```

这条循环是第二大脑的持续生长回路，不是单独项目。

## 二、系统定位与唯一权威

### 2.1 W3 是唯一长期记忆权威

本模块归属 W3。

W3 继续拥有：

- Source / Evidence；
- KnowledgeAtom；
- Relation；
- Conflict；
- UNKNOWN；
- LearningPacket；
- 长期记忆状态、版本和撤销；
- 混合检索；
- MemoryContextBundle / AnswerEvidenceBundle；
- 长期记忆索引与可重建投影。

CLTM 不创建：

- 第二套 SQLite memory store；
- 第二套 QueryPlan；
- 第二套 ContextBundle；
- 第二套 fusion engine；
- 第二套 vector authority；
- 第二套 graph authority；
- 独立于 W3 的“洛雪记忆数据库”。

### 2.2 与 W10 的关系

W10 负责个人认知、任务情境、DecisionEpisode、个人偏好如何进入决策上下文。

W3 保存和提供可追溯的长期记忆；W10 消费相关 MemoryContextBundle，形成当前任务中的用户模型、目标、效用、约束和 DecisionEpisode。

W10 不得静默改写 W3 历史，也不得把个人偏好自动升级为外部事实。

### 2.3 与 AI 电影、A股及未来项目的关系

AI 电影仓、A股研究、未来健康/公司/生活项目都是 W3 的消费者与候选知识生产者。

同一条用户长期记忆可以通过 scope / relation 与多个项目关联，但 canonical identity 只有一个。

项目只能读取与自身任务相关且权限允许的 ContextBundle，不默认读取全部私人关系或生活记忆。

## 三、移动端优先原则

### 3.1 ChatGPT 是第一人机入口

ChatGPT 手机端、Web、Desktop 统一视为 `CONVERSATION_SURFACE`。

目标不是要求用户为了“记忆”额外打开笔记软件、GitHub 或数据库，而是：

**用户照常聊天，第二大脑在后台把可访问的重要对话转化为可追溯长期记忆。**

### 3.2 低摩擦优先

默认交互应做到：

- 不要求用户给每条消息打标签；
- 不要求用户手动选择“存入第二大脑”；
- 用户明确说“记住”“以后都这样”“这个很重要”“之前说错了”等时提高优先级；
- 自动摄入只产生 candidate，不因为自动化而自动获得事实权威。

### 3.3 覆盖边界必须诚实

标准 ChatGPT 当前不能被假定为能让后台任务逐字读取账号内所有聊天窗口。

任何自动归档必须记录：

- `source_scope`；
- `coverage: complete | partial | unknown`；
- 可访问的 conversation/session 范围；
- 缺失边界。

禁止把“系统没读到”写成“当天没发生”。

## 四、记忆分层

W3 在现有 taxonomy 上正式支持以下长期视图：

1. `WORKING_MEMORY`：当前任务临时上下文，不作为长期事实源；
2. `EPISODIC_MEMORY`：发生过的对话、事件、时间顺序和共同经历；
3. `SEMANTIC_MEMORY`：从经历与来源中形成的事实、概念、规则和解释；
4. `PROCEDURAL_MEMORY`：方法、流程、检查表、技能和稳定工作习惯；
5. `AUTOBIOGRAPHICAL_USER_MEMORY`：用户经历、长期偏好、长期目标和个人状态；
6. `RELATIONSHIP_CONTEXT_MEMORY`：用户与ChatGPT长期互动中形成的称呼、互动规则、共同历史和关系上下文；
7. `PROJECT_MEMORY`：AI电影、A股、第二大脑等项目状态、决定、失败和知识；
8. `DECISION_MEMORY`：重大选择、理由、备选、当时信息和结果；
9. `OPEN_LOOP_MEMORY`：未完成、等待、暂停、已解决事项；
10. `CONFLICT_AND_UNKNOWN_MEMORY`：冲突、反证、不确定和验证路径；
11. `META_MEMORY`：系统知道什么、不知道什么、哪些记忆可能过时、冲突或低置信。

同一内容可以被多个视图引用，但不得复制出多个彼此竞争的 canonical facts。

## 五、原始 Episode 优先，摘要不得替代历史

### 5.1 ConversationEpisode 是一等 Source

建立/复用：

- `ConversationSourceManifest`；
- `ConversationEpisode`；
- `ConversationTurnReference`；
- `ConversationMemoryCandidate`。

Episode 至少包含：

```yaml
episode_id:
conversation_id:
session_id:
user_scope:
project_scope:
participants:
started_at:
ended_at:
timezone:
source_scope:
coverage:
raw_source_pointer:
raw_content_hash:
privacy_class:
ingestion_status:
schema_version:
```

### 5.2 不可用摘要冒充原始经历

Daily / Weekly / Monthly / Reflection 都是派生层。

派生摘要必须能回到 Episode / source spans。

原始 Episode 和当时已确认事实不能因后续观点变化被静默改写。

### 5.3 内容最小化与隐私

对高度敏感内容可保留：

- 完整 source pointer / hash；
- 最小必要语义；
- 必要关系和状态；

而不是无必要复制大量逐字原文。

凭证类秘密值永久禁止进入任何长期记忆、Embedding、日志、测试、Git历史或 ContextBundle。

## 六、双时态长期记忆

所有可长期影响未来判断的记忆至少区分：

- `valid_from / valid_to`：信息在现实或用户状态中何时成立；
- `recorded_at / updated_at`：系统何时获知、记录或修正。

这解决以下典型问题：

- 临时心情被误判为长期偏好；
- 用户后来说明过去一句话只在某段时期有效；
- 项目状态已经改变，但旧判断仍有历史研究价值；
- 用户后来纠正旧事实，需要保留“当时怎么想”和“现在怎么理解”。

必须支持：

- `CORRECTION`；
- `REFINES`；
- `UPDATES`；
- `SUPERSEDES`；
- `RESOLVES_UNKNOWN`；
- `REVOKES`。

默认 current-answer query 排除已失效/被 supersede 的版本；历史问题可以显式召回历史版本。

## 七、来源与 Provenance

每一条派生长期记忆必须能追溯：

```text
MemoryAtom / MemoryObject
→ LearningPacket
→ ConversationEpisode / SourceDocument
→ exact turn(s) / source span(s)
```

至少保存：

```yaml
source_episode_id:
source_turn_ids: []
source_hash:
derived_by:
derivation_run_id:
created_at:
runtime_version:
confidence:
confidence_basis:
verification_status:
```

设计参考 W3C PROV 的 Entity / Activity / Agent 与 derivation 思想，但本项目优先复用现有 W3 provenance 合同，不为“标准化”另造 RDF 权威。

## 八、Hot Path：聊天发生时就产生候选记忆

### 8.1 为什么必须有 Hot Path

后台定时任务不能被假定能访问当天所有账号聊天，因此不能只依赖“晚上再找聊天”。

任何可控制的 ChatGPT / Memory Gateway / MCP 集成，应尽量在对话发生时捕获高价值候选。

### 8.2 Hot Path 默认提取

优先提取：

- `USER_EXPLICIT_LONG_TERM_PREFERENCE`；
- `USER_CORRECTION`；
- `IMPORTANT_EVENT`；
- `PROJECT_DECISION`；
- `OPEN_LOOP`；
- `RESOLUTION`；
- `NEW_STABLE_RULE`；
- `IMPORTANT_LEARNING`；
- `FAILURE_LESSON`；
- `RELATIONSHIP_CONTEXT_UPDATE`；
- `GOAL_OR_CONSTRAINT_CHANGE`。

默认不自动升级：

- 普通寒暄；
- 一次性情绪；
- 随机玩笑；
- 未确认猜测；
- 无复用价值的琐事。

这些仍可存在于 Episode 历史中。

### 8.3 Candidate-first

Hot Path 只能产生 candidate。

用户明确长期指令可以提高 `authority_level` / `confidence_basis`，但涉及正式 PROJECT/GLOBAL knowledge authority 时仍遵守当前 W3 / E61 durable authority gate。

## 九、Cold Path：每日、每周、每月巩固

### 9.1 Daily

对运行时可访问的 Episode：

- 去重；
- 识别事件；
- 识别用户/助手观点；
- 识别决策；
- 识别学习；
- 识别偏好候选；
- 识别纠错；
- 识别 Open Loop；
- 识别冲突和 UNKNOWN；
- 产生 candidate LearningPacket。

### 9.2 Weekly

形成跨 Episode 的 Reflection：

- 哪些观点重复稳定；
- 哪些目标正在变化；
- 哪些未决事项持续存在；
- 哪些旧记忆可能失效；
- 哪些方法从多次成功/失败中形成。

### 9.3 Monthly

执行：

- duplicate consolidation；
- stale detection；
- supersession review；
- contradiction review；
- user profile evolution；
- relationship/context evolution；
- project-state consolidation；
- open-loop review；
- memory quality drift review。

所有派生层必须保留 provenance，不能成为不可追溯的新事实源。

## 十、Memory Router：回答前先决定是否需要回忆

### 10.1 输入

```yaml
current_query:
conversation_context:
user_scope:
project_scope:
current_time:
```

### 10.2 RecallDecision

至少输出：

```yaml
recall_required:
memory_types: []
entities: []
time_scope:
project_scope:
user_scope:
historical_required:
conflict_required:
unknown_required:
retrieval_depth:
context_budget:
```

### 10.3 强制召回情形

以下情况默认强制走长期记忆检索：

- “之前 / 上次 / 以前 / 还记得 / 我说过”；
- 项目延续；
- 人物历史；
- 个人偏好；
- 长期规则；
- 重大决策；
- Open Loop；
- 已解决事项；
- 用户纠错；
- 过去观点；
- 长期健康、资金、法律或其他历史状态会改变当前判断的场景；
- 当前请求含有与长期用户目标/价值明显相关的隐含约束。

普通“你好”“老婆”等轻聊天无需为形式完整强制进行昂贵全库检索。

## 十一、混合检索

不得只依赖向量相似度。

复用 W3 / Issue #60 现有检索架构：

- Lexical / BM25；
- Exact ID / Entity；
- Vector semantic；
- Knowledge graph；
- Temporal / Version；
- Source / Evidence；
- User / Project scope；
- Conflict / UNKNOWN；
- Memory palace / navigation projection（如已实现且证明有增量）。

推荐流程：

```text
Query
→ intent/entity/time/project parsing
→ query expansion
→ multi-retriever recall
→ dedupe
→ version merge
→ relation expansion
→ conflict/UNKNOWN supplement
→ Memory Trust Gate
→ rerank
→ budget packing
→ MemoryContextBundle / AnswerEvidenceBundle
```

## 十二、Memory Trust Gate

任何记忆进入 ChatGPT 上下文前检查：

1. user scope；
2. project scope；
3. memory type；
4. valid time；
5. record time；
6. current / historical intent；
7. superseded / revoked / stale；
8. source quality；
9. confidence / verification；
10. fact vs opinion vs preference；
11. conflict / counterevidence；
12. UNKNOWN；
13. prompt injection risk；
14. privacy / access policy。

高相似但错误项目、错误人物、已过期或已撤销的记忆不得因为 cosine score 高进入 current context。

低向量相似但实体、时间、ID 或明确历史指针强匹配的记忆不能被轻易丢弃。

## 十三、Open Loop 与 Resolution

状态至少支持：

- `OPEN`；
- `WAITING`；
- `PAUSED`；
- `RESOLVED`；
- `CANCELLED`。

字段至少：

```yaml
id:
title:
opened_at:
source_episode:
importance:
status:
next_action:
review_after:
related_project:
resolved_at:
resolution:
```

`RESOLVED` 项不得继续以“当前待办”身份反复召回，但可在历史问题中出现。

## 十四、Correction 是一等对象

用户说“不对”“我以前说错了”“那个已经解决”“那只是临时想法”“以后不要这样理解”等，不允许只覆盖 profile。

必须创建 correction event：

```text
old memory
→ correction event
→ reason/evidence
→ valid-time change
→ refine / supersede / resolve / revoke
```

历史保留，当前状态更新。

## 十五、ChatGPT 原生能力在体系中的角色

截至蓝图编写时，OpenAI Memory 能从聊天、文件和连接应用中使用相关上下文，但官方明确不保证每次请求都搜索历史，也不保证保留过去聊天的每个细节。因此：

### 15.1 ChatGPT Memory

定位：`HOT_PERSONALIZATION_CACHE`

保存少量高价值、长期稳定且适合持续进入上下文的信息。

不是 durable history authority。

### 15.2 Reference Chat History

定位：`NATIVE_RECALL_AUXILIARY`

可提高原生连续性，但不能替代 W3 的可审计长期记忆。

### 15.3 Project Memory

定位：`PROJECT_INTERACTION_COCKPIT`

适合长期项目内连续工作。Project-only memory 可形成项目隔离，但需要注意它会限制跨项目个人上下文。

### 15.4 Scheduled Tasks

定位：`BACKGROUND_CONSOLIDATION_TRIGGER`

可运行 Daily/Weekly/Monthly candidate consolidation，也可使用部分已连接应用；但任务不能被假定能访问账号全部历史聊天，而且项目含文件时任务当前不能访问这些项目文件。

### 15.5 Apps / MCP

定位：`MEMORY_GATEWAY_INTEGRATION_SURFACE`

连接应用可用于搜索/读取外部数据。完整 MCP 写/修改能力目前属于特定套餐/工作空间的 beta 能力，必须在实施时再次查官方文档，不得把今天的产品能力写死成永久前提。

## 十六、三档 ChatGPT 集成成熟度

### LEVEL A — Native / Soft Guarantee

```text
ChatGPT Memory + Reference Chat History
+ Project Instructions
+ connected GitHub / App retrieval
+ W3 Memory Router protocol
```

优点：现在最容易落地，手机体验最好。

限制：不能证明“每条实质消息都 100% 必经 W3 recall”。

### LEVEL B — Custom Memory App / MCP

暴露统一接口：

```text
recall_memory
retrieve_episode
search_memory
expand_relations
get_current_profile
get_open_loops
stage_memory_candidate
submit_correction
resolve_open_loop
revoke_memory
```

所有写操作必须服从 W3 authority / E61 gate。

### LEVEL C — Hard-Guarantee Memory Gateway

当需要“没有执行 recall 就绝不能回答”时，在模型调用前建立薄层 Gateway：

```text
User message
→ mandatory MemoryRouter
→ W3 recall
→ MemoryContextBundle
→ LLM
→ answer
→ candidate capture
```

这时“先回忆”是代码中的必经节点，不是提示词偏好。

本阶段首先实现 LEVEL A + W3 可测试垂直切片；LEVEL B/C 以接口合同和真实产品能力门推进。

## 十七、私人 GitHub 知识仓的角色

现有蓝图建议的 `second-brain-knowledge-private` 若建立，其定位必须明确为：

`W3 PRIVATE DURABLE KNOWLEDGE DATA PLANE`

不是第三个独立记忆系统。

它可以保存：

- immutable conversation episode exports / pointers；
- 原始私人 Source 副本；
- LearningPacket；
- KnowledgeAtom / relation / correction 的规范化导出；
- snapshot；
- schema；
- audit / rollback history。

公开 `second-brain-coordination` 只保存架构、Schema、程序、测试和 public-safe receipt，不保存私人对话正文。

AI电影仓继续保存 AI电影项目自身代码/资产/交付，不承担跨项目用户记忆权威。

## 十八、Memory Palace 的地位

“记忆宫殿”如继续实现，只能是稳定可计算的导航/索引投影：

- Wing；
- Room；
- Locus；
- Placement。

不得复制 canonical 正文，不得因为空间邻近推导语义因果。

如果基准不能证明检索增量，可以保持可选而不阻塞核心长期记忆上线。

## 十九、研究依据与吸收原则

本蓝图吸收但不机械复制以下思路：

### Generative Agents

吸收：完整 experience record、动态 retrieval、reflection、planning。

不吸收：把模拟人类行为的目标直接当作个人助手目标。

### MemGPT

吸收：有限上下文与大容量外部记忆的分层管理；快/慢记忆层。

### LongMemEval

吸收：长期记忆至少要测试信息提取、跨 session 推理、时间推理、知识更新和正确拒答；系统应区分 indexing、retrieval、reading。

### LoCoMo

吸收：超长、多 session、时间/因果一致性测试，而不是只测单事实背诵。

### LoCoMo-Plus

吸收：隐含约束和 cue-trigger semantic disconnect；用户过去表达的目标、价值、状态可能在未来问题中没有被重新明说，但仍应在有充分证据时正确影响回答。

### A-MEM

吸收：动态 linking、记忆属性和上下文表示可随新证据演化；但任何更新必须保留版本和 provenance，不能静默重写历史。

### HippoRAG

吸收：图关系和多跳检索可以作为向量/关键词之外的补充，但必须通过本项目基准证明净增量。

### W3C PROV

吸收：Entity / Activity / Agent、wasDerivedFrom 等 provenance 思想。

### 双时态历史 / Event Sourcing

吸收：事实发生时间与系统获知时间分离；历史 append/audit 优先，当前状态由事件和版本投影得到。

所有研究分为：官方产品文档、正式论文/会议、预印本、工程案例、设计推断。不得把预印本结果或外部项目性能直接包装成本系统生产保证。

## 二十、首个纵向切片

不得先建大而全基础设施。

第一纵向切片固定为：

```text
Session A
用户提供一条有长期价值的信息
↓
ConversationEpisode
↓
现有 LearningPacket / candidate memory runtime
↓
Session B
用户不重复原文，系统通过 W3 recall 正确取回
↓
Session C
用户纠正旧信息
↓
Correction / supersedes
↓
Session D
询问 current state，必须返回新信息
↓
Session E
询问 historical state，必须能返回旧信息并说明其历史有效期
```

必须同时证明：

- provenance；
- user/project scope；
- valid/record time；
- current vs historical；
- correction；
- abstention；
- 无跨项目泄漏。

完成信号：

`CONVERSATIONAL_MEMORY_VERTICAL_SLICE_READY`

## 二十一、长期评测

建立 `PERSONAL-LONG-MEMORY-EVAL`，至少覆盖：

- FACT_RECALL；
- CROSS_SESSION_REASONING；
- TEMPORAL_REASONING；
- KNOWLEDGE_UPDATE；
- ABSTENTION；
- IMPLICIT_CONSTRAINT；
- USER_CORRECTION；
- STALE_MEMORY；
- SUPERSEDED_MEMORY；
- PROJECT_BLEED；
- USER_SCOPE_LEAK；
- CONFLICT_RECALL；
- UNKNOWN_RECALL；
- OPEN_LOOP_RESOLUTION；
- PROVENANCE；
- PROMPT_INJECTION_MEMORY；
- NEGATION；
- EXCEPTION；
- HISTORICAL_QUERY；
- MEMORY_TO_ACTION_GROUNDING（当未来工具调用接入时）。

指标至少：

```text
Recall@K
Precision@K
MRR
Temporal Accuracy
Knowledge Update Accuracy
Stale Leakage
Superseded Leakage
Cross-project Bleed
Conflict Recall
UNKNOWN Recall
Provenance Coverage
Abstention Precision/Recall
Constraint Consistency
Token Cost
Latency
```

验收不以“记住多少条”作为核心 KPI，而以**记得正确、用得正确、能纠错、能拒答、不会串库**为核心。

## 二十二、生命周期与遗忘

状态至少支持：

- INGESTED；
- CANDIDATE；
- ACTIVE；
- CONSOLIDATED；
- SUPERSEDED；
- STALE；
- DISPUTED；
- REVOKED；
- ARCHIVED；
- FORGOTTEN_INDEX_ONLY。

“忘记”默认指降低索引/召回权重或归档，不无审计删除 canonical 历史。

用户明确要求删除/撤销时按正式 privacy/revocation 协议执行。

## 二十三、安全与认知完整性

永久禁止保存：

- password；
- API key / secret；
- access / refresh token；
- cookie / session credential；
- private key；
- 2FA secret / recovery code；
- bank / broker / payment credential；
- 可直接登录、签名、转账或下单的秘密值。

此外必须防止：

- prompt injection 被当成长效系统规则；
- 用户一次性猜测被自动升级为事实；
- 助手自己的错误陈述因为重复出现而“投票成真”；
- 高相似度旧记忆压过最新 correction；
- 一个项目的隐私无边界流入另一项目；
- 关系记忆被业务项目无必要读取；
- embedding / logs 泄露秘密值。

## 二十四、实施阶段

### P0 Canonical Audit

冻结 PR #57、Issue #38/#59/#60、Issue #216 / MODULE_0020、E61 与 W3 当前真实写/读路径。

### P1 Conversational Vertical Slice

跑通 Session A-E。

### P2 Memory Router + Trust Gate

先使用 BM25 / entity / time / project / status；复杂检索后加。

### P3 Hybrid Retrieval

按基准逐步加入 vector / graph / temporal / evidence / conflict / UNKNOWN。

### P4 Consolidation

Daily / Weekly / Monthly + stale / correction / profile evolution。

### P5 Adversarial Evaluation

使用个人化 LongMemEval / LoCoMo / LoCoMo-Plus 思路测试。

### P6 ChatGPT Integration Upgrade

从 LEVEL A 到 MCP / Hard Gateway，按当时产品能力与权限推进。

### P7 Cloud Serving

只有出现真实规模/延迟/多设备/多Agent并发需求时才评估 Supabase / pgvector / graph serving。

## 二十五、与MODULE_0020语义重建的关系

现有 `KNOWLEDGE-SOURCE-SEMANTIC-RECONSTRUCTION-AND-GRAPH-PROJECTION-0020` 负责把嘈杂ASR/OCR/口述等Source生成可审计的 `NormalizedSemanticView`，并输出候选知识图谱投影。

CLTM 0021不得重复这套能力。

当Conversation Source来自语音转写、ASR或存在明显口语噪声时：

```text
Conversation Raw Episode
→ MODULE_0020 NormalizedSemanticView（derived, auditable）
→ CLTM/W3 conversation atomization and memory candidate
```

原始Conversation Episode仍是证据源；NormalizedSemanticView只是派生理解层。

## 二十六、成功标准

1. ChatGPT Conversation 成为 W3 一等 Source；
2. 手机端自然聊天无需额外记笔记动作即可产生高价值 candidate memory；
3. 原始 Episode、派生 Memory、当前状态和历史版本分离；
4. user correction 能可靠覆盖当前理解而不删除历史；
5. 每次重要回答前可以通过 MemoryRouter 获取相关长期上下文；
6. W3 ContextBundle 可以被 ChatGPT、Codex、AI电影项目、A股项目按 scope 消费；
7. 项目之间无无授权串库；
8. ChatGPT 原生 Memory 只作为辅助热缓存，不冒充 W3 durable authority；
9. 后台任务覆盖不完整时如实标记 partial；
10. 第一垂直切片 Session A-E 全部通过；
11. 长期基准显示 stale/superseded/cross-project leakage 在门槛内；
12. 无凭证值泄漏；
13. 不创建第二套 canonical runtime；
14. E61 未放行前不绕过正式 durable authority gate；
15. 与现有MODULE_0020语义重建复用而非重复；
16. 整体仍保持 research_only / NO_TRADE。

## 二十七、当前成熟度

```yaml
module_id: CONVERSATIONAL-LONG-TERM-MEMORY-0021
architecture_position: W3_CORE_CAPABILITY
mobile_chat_as_primary_capture_surface: ACCEPTED_BLUEPRINT_DECISION
conversation_source_contract: TO_IMPLEMENT
hot_path_candidate_capture: TO_IMPLEMENT
background_consolidation: TASK_EXISTS_BUT_CANONICAL_INGESTION_PENDING
memory_router: CONTRACT_TO_IMPLEMENT
trust_gate: CONTRACT_TO_IMPLEMENT
hybrid_retrieval: PARTIAL_EXISTING_W3_FOUNDATION
semantic_reconstruction_dependency: REUSE_MODULE_0020_WHEN_NEEDED
conversation_vertical_slice: NOT_IMPLEMENTED
chatgpt_level_a_integration: PARTIAL_PRODUCT_CAPABILITY_EXISTS
chatgpt_level_b_mcp: PRODUCT_PLAN_DEPENDENT
chatgpt_level_c_hard_gateway: FUTURE_OPTION
private_durable_store: BLUEPRINT_DEFINED_NOT_VERIFIED_CREATED
formal_persistence_gate: E61_DEPENDENT
live_trade: PROHIBITED
```
