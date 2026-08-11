# 第二大脑与A股交易系统企业级总工程章程 v1.5

> `agent_id: GPT`
>
> `supersedes: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.4.md`
>
> `incorporates_v1_4_by_reference: true`
>
> `new_module: CONVERSATIONAL-LONG-TERM-MEMORY-0020`
>
> `specialized_blueprint: coordination/BLUEPRINTS/CONVERSATIONAL-LONG-TERM-MEMORY-AND-MOBILE-SECOND-BRAIN-BLUEPRINT-v1.0.md`
>
> `boundary: research_only / NO_TRADE`

## 一、继承与升级

v1.5完整继承v1.4的AMED企业执行标准、W1-W13工作流、知识权威、个人认知、决策科学、A股研究、验证、资本配置、风险、影子运行和多AI协作规则。

本版本新增并提升：

`CONVERSATIONAL-LONG-TERM-MEMORY-0020`。

该模块不是新工作流，也不是独立记忆运行时，而是 **W3 Knowledge Authority and Long-Term Memory 的核心用户入口与核心长期记忆能力**。

## 二、核心架构决策

正式接受以下企业级架构决策：

> 用户与ChatGPT的长期对话不是第二大脑外围日志，而是第二大脑长期知识与个人经历的重要一等来源。ChatGPT手机/Web/Desktop的自然对话界面是用户低摩擦进入第二大脑的主要人机入口之一。

因此：

```text
ChatGPT Conversation
→ ConversationEpisode / SourceManifest
→ W3 LearningPacket / KnowledgeAtom / Relation / Conflict / UNKNOWN
→ W3 canonical memory runtime
→ MemoryRouter + Trust Gate + Hybrid Retrieval
→ MemoryContextBundle / AnswerEvidenceBundle
→ ChatGPT / W10 / AI电影 / A股 / 其他授权项目
→ 新对话、新纠错、新结果继续回灌W3
```

## 三、W3职责扩展

W3除既有知识、证据、冲突、UNKNOWN和长期记忆外，正式承担：

1. ChatGPT Conversation Source注册；
2. ConversationEpisode和Turn级provenance；
3. episodic / semantic / procedural / autobiographical / relationship / project / decision / open-loop / meta-memory视图；
4. Hot Path高价值候选记忆采集；
5. Daily / Weekly / Monthly背景巩固；
6. 双时态valid time / record time；
7. Correction / Refine / Supersede / Revoke；
8. MemoryRouter；
9. Memory Trust Gate；
10. 当前状态与历史状态查询；
11. ChatGPT原生Memory / Project / Tasks / Apps / MCP与W3的集成合同；
12. 面向长期对话的对抗评测。

## 四、与W10的边界

- W3拥有对话长期记忆、来源、版本、冲突和召回权威；
- W10消费W3提供的当前用户/历史上下文，形成Personal Epistemic Cognitive OS、TaskContext和DecisionEpisode；
- W10不得创建第二套用户长期记忆事实源；
- W10不得静默把用户偏好改写成世界概率、事实或风险限额；
- 用户纠正首先进入W3 correction/version链，再由W10消费最新有效状态。

## 五、跨项目记忆原则

用户长期记忆是跨项目资产，不属于AI电影仓、A股仓或任何单一业务项目。

AI电影、A股和未来项目通过`user_scope + project_scope + memory_type + access_policy`消费W3 ContextBundle。

一个项目可以读取与自身任务相关的用户偏好、项目决定、失败经验和工作方法，但不得默认读取与任务无关的私人关系记忆或其他项目内容。

## 六、私人数据面

现有`SECOND-BRAIN-GITHUB-SUPABASE-ENTERPRISE-BLUEPRINT-v1.0.md`建议的`second-brain-knowledge-private`继续作为推荐的 **W3 Private Durable Knowledge Data Plane**。

它不是第三套记忆系统。

公开`second-brain-coordination`只保存：

- 蓝图；
- Schema；
- 程序；
- 测试；
- public-safe receipt；
- Agent协作和治理。

私人conversation正文、episode、真实个人知识和关系记忆默认不写入公开仓。

## 七、ChatGPT原生能力定位

ChatGPT原生Memory、Reference Chat History、Project Memory、Scheduled Tasks和Apps/MCP全部视为W3的交互/采集/召回辅助能力，而不是W3 durable authority的替代物。

产品能力可能变化，因此所有实现必须在执行时重新核验OpenAI官方文档。

当前统一定位：

- Saved/Native Memory：高价值热缓存与原生个性化；
- Chat History：辅助召回；
- Project：项目交互驾驶舱；
- Scheduled Tasks：后台巩固触发器；
- Apps/MCP：W3记忆网关集成面；
- Hard Guarantee Gateway：未来需要“每次回答前必经Recall”时的代码级强制路径。

## 八、实施优先级

### CLTM-P0 Canonical Audit

核验PR #57、Issue #38/#59/#60、E61和最新main，冻结唯一W3 runtime和读写边界。

### CLTM-P1 First Conversational Vertical Slice

Session A写入长期信息 → Session B跨会话召回 → Session C纠正 → Session D读取current → Session E读取historical。

### CLTM-P2 Memory Router and Trust Gate

先完成实体、关键词、时间、项目、状态和版本召回，再逐步融合向量/图谱。

### CLTM-P3 Consolidation

Hot Path + Daily / Weekly / Monthly。

### CLTM-P4 Adversarial Long-Memory Evaluation

覆盖时间、更新、隐含约束、冲突、UNKNOWN、过期、跨项目、拒答和prompt injection。

### CLTM-P5 ChatGPT Integration Upgrade

按官方产品能力从Native/Apps升级到MCP或Hard Gateway。

## 九、硬规则

1. 不新建第二套canonical memory runtime；
2. Conversation是W3一等Source，不是独立数据库；
3. 原始Episode与派生摘要分离；
4. 摘要不能替代source/provenance；
5. current与historical查询分开；
6. 用户纠正不静默改写历史；
7. valid time与record time分离；
8. candidate first，E61未放行前不得绕过正式durable authority gate；
9. ChatGPT Task不能被假定覆盖账号全部聊天，coverage必须诚实；
10. 私人长期记忆默认private；
11. 凭证值零存储、零嵌入、零日志、零提交；
12. 项目scope隔离，防止跨项目记忆污染；
13. 不以向量相似度作为唯一召回/信任依据；
14. 不以“记得更多”作为成功，优先“记得正确、能更新、会拒答、不串库”；
15. 全程research_only / NO_TRADE。

## 十、专业研究和验证标准

CLTM实施属于STRATEGIC任务，必须使用AMED并执行L2专业研究。

至少核验：

- OpenAI Memory、Projects、Tasks、Apps、MCP官方文档；
- Generative Agents；
- MemGPT；
- LongMemEval；
- LoCoMo；
- LoCoMo-Plus；
- A-MEM；
- HippoRAG；
- W3C PROV；
- Event Sourcing / Bitemporal History；
- 可复现的真实开源长期记忆项目。

必须标记：官方文档、同行评审论文、预印本、工程案例、设计推断，不得将研究结果直接包装为本系统生产保证。

## 十一、企业级成功标准

除v1.4所有标准外，新增：

1. ChatGPT Conversation成为W3正式Source；
2. 用户在手机自然聊天即可进入第二大脑记忆链；
3. 对话经历能跨session被正确召回；
4. 用户纠正能更新current理解且历史仍可追溯；
5. W3能为ChatGPT和业务项目生成scope受控的ContextBundle；
6. 长期记忆具备时间、版本、冲突、UNKNOWN、provenance和撤销；
7. 长期评测覆盖显式事实与隐含用户约束；
8. 不发生公开仓私人conversation正文泄漏；
9. 不发生第二套记忆权威；
10. 不发生stale/superseded记忆无提示压过当前状态。

## 十二、当前成熟度

```yaml
enterprise_charter: ACTIVE_V1_5_CANDIDATE_ON_GPT_BRANCH
cltm_module: BLUEPRINT_COMPLETE
w3_position: CORE_CAPABILITY_ACCEPTED
conversation_source: NOT_IMPLEMENTED
conversation_vertical_slice: NOT_IMPLEMENTED
memory_router: NOT_IMPLEMENTED
trust_gate: NOT_IMPLEMENTED
background_daily_task: EXISTS_CANDIDATE_MODE
private_durable_store: BLUEPRINT_DEFINED_NOT_VERIFIED_CREATED
formal_persistence_gate: E61_DEPENDENT
chatgpt_native_integration: PARTIAL_PRODUCT_CAPABILITY
live_trade: PROHIBITED
```
