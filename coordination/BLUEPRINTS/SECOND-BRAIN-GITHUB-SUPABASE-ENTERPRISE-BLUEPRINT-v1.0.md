# 第二大脑 GitHub + Supabase 企业级知识云蓝图 v1.0

> 状态：架构蓝图，research_only / NO_TRADE
>
> 关联：Issue #20 QCLAW知识消化引擎
>
> 原则：当前公开协调仓库只保存架构、Schema和程序，不保存私人知识、原始私密资料或任何凭证。

## 一、目标

建立一套本地与云端结构一致、可审计、可回滚、可被多个AI调用的第二大脑知识平台：

- QCLAW按需离线消化知识；
- 本地私有Git知识仓库存放权威知识包及原始证据；
- GitHub私有仓库作为云端权威版本库；
- Supabase作为结构化查询、关系扩展、全文检索与向量检索的云端Serving Layer；
- GPT、Codex、WorkBuddy、交易系统及其他AI通过统一只读接口调用；
- QCLAW下线后，第二大脑仍可独立检索和使用全部已导入知识。

## 二、难度判断

### MVP

中等难度。Supabase项目、Postgres表、pgvector、迁移和REST接口本身成熟；主要工作是把QCLAW知识包稳定映射为数据库对象，并建立可重复导入与检索测试。

### 企业级版本

中高难度。困难不在“把文档上传”，而在：

1. GitHub与Supabase谁是权威；
2. 新旧知识冲突如何并存与升级；
3. 原子、关系、证据、技能如何保持可追溯；
4. 如何避免重复导入和版本漂移；
5. 如何让表面不相关但有价值的知识被召回；
6. 如何在QCLAW离线时继续被多个AI调用；
7. 免费层暂停、无自动备份和容量限制下如何可恢复。

## 三、总架构

```text
用户提供知识
      ↓
QCLAW离线消化器
      ↓
本地私有知识仓库 working tree
      ↓  Schema校验 / 质量门禁 / Git commit
GitHub私有知识仓库（权威事实源）
      ↓  projector / idempotent sync
Supabase云端Serving Layer
      ├─ Postgres结构化知识
      ├─ pgvector语义检索
      ├─ 全文与关键词检索
      ├─ 关系扩展与冲突检索
      └─ 只读API / 第二大脑MCP
             ↓
GPT / Codex / WorkBuddy / 交易系统 / 其他AI
```

## 四、权威边界

### 1. GitHub私有知识仓库是Canonical Source of Truth

保存：

- 原始材料不可变副本及SHA-256；
- QCLAW完整KnowledgePacket；
- 原子、关系、模型、技能的规范化导出；
- JSON Schema；
- 协议版本；
- 变更历史、审核记录和回滚点。

### 2. Supabase是Materialized Serving Projection

保存用于高效调用的规范化表、全文索引、向量、关系边、调用反馈和运行日志。Supabase中的权威知识可从GitHub完整重建，因此云端数据库损坏、暂停或迁移时不会丢失知识资产。

### 3. 本地目录是GitHub仓库的离线工作镜像

离线期间QCLAW写入本地分支与sync_queue；联网后提交并推送。禁止本地文件与Supabase互相自由覆盖。

### 4. 反馈采用反向事件流

AI调用次数、成功/误导反馈等可先写Supabase，再周期性导出为不可变usage snapshot提交GitHub；反馈不能直接修改知识原文，只能产生新的知识版本或复核任务。

## 五、推荐仓库分离

### 公开协调仓库

`vxz2datoubo/second-brain-coordination`

仅保存：蓝图、Schema、迁移、同步器、MCP/API代码、测试和Agent协作记录。

### 私有知识仓库

建议新建：`second-brain-knowledge-private`

仅保存真实知识资产。ChatGPT GitHub连接、Codex、WB和QCLAW按最小权限访问。

## 六、私有知识仓库目录

```text
second-brain-knowledge-private/
├─ README.md
├─ KNOWLEDGE-MANIFEST.yaml
├─ schemas/
│  ├─ knowledge-packet.schema.json
│  ├─ knowledge-atom.schema.json
│  ├─ relation-edge.schema.json
│  ├─ reusable-skill.schema.json
│  └─ import-report.schema.json
├─ protocols/
│  └─ QCLAW-KNOWLEDGE-DIGESTER-PROTOCOL.md
├─ sources/YYYY/MM/<source_id>/
│  ├─ original.*
│  └─ source-meta.yaml
├─ packets/YYYY/MM/<packet_id>/
│  ├─ packet.yaml
│  ├─ atoms.jsonl
│  ├─ relations.jsonl
│  ├─ structures.jsonl
│  ├─ skills.jsonl
│  ├─ retrieval-index.jsonl
│  ├─ unknowns.jsonl
│  └─ import-report.yaml
├─ indexes/
│  ├─ direct-index.jsonl
│  ├─ aliases.jsonl
│  ├─ contradiction-index.jsonl
│  ├─ surprise-links.jsonl
│  └─ project-index.jsonl
├─ exports/
│  ├─ supabase/
│  └─ usage-snapshots/
├─ quarantine/
├─ archive/
└─ sync_queue/
```

## 七、核心数据对象

### KnowledgePacket

一次QCLAW消化任务的完整交付单元，包含协议版本、输入来源、处理器、质量审查、原子、关系、结构、技能、未知项和写入建议。

### KnowledgeAtom

最小可独立判断、验证、引用或调用的语义命题。必须保存原文、来源、时间、类型、范围、条件、例外、置信度、验证状态和失效条件。

### RelationEdge

原子或高阶结构之间的有向关系，包括CAUSES、REQUIRES、SUPPORTS、CONTRADICTS、REFINES、UPDATES、REPLACES、ANALOGOUS_TO、EVIDENCED_BY等。

### ReusableSkill

由知识原子派生的可执行技能，包含触发、输入、步骤、输出、约束、失败模式、测试和回滚。

## 八、Supabase逻辑表

建议最少建立：

1. `source_documents`
2. `source_versions`
3. `knowledge_packets`
4. `knowledge_atoms`
5. `atom_versions`
6. `relation_edges`
7. `higher_order_structures`
8. `reusable_skills`
9. `retrieval_aliases`
10. `surprise_links`
11. `contradictions`
12. `unknown_registry`
13. `embedding_records`
14. `project_links`
15. `ingestion_runs`
16. `sync_events`
17. `usage_events`
18. `review_tasks`

所有对象必须携带：

- 稳定ID；
- schema_version；
- protocol_version；
- content_hash；
- git_repository；
- git_path；
- git_commit_sha；
- created_at / updated_at；
- status；
- provenance链。

## 九、向量与全文检索

### 初期免费策略

- PostgreSQL全文检索负责关键词、术语、别名和用户口语；
- pgvector负责语义相似度；
- Embedding优先由本地模型生成，再上传Supabase，避免持续云端Embedding费用；
- Embedding模型和维度必须记录在`embedding_records`，更换模型时并存版本，不覆盖旧向量。

### 混合检索流程

1. 直接关键词和实体检索；
2. 语义向量检索；
3. 关系图一至两跳扩展；
4. 强制检索反例、冲突和失效条件；
5. 从surprise_links召回少量跨域候选；
6. 依据相关性、证据、时间、适用范围和冲突状态重排；
7. 输出带来源的ContextBundle。

## 十、统一只读调用接口

推荐工具：

- `search_knowledge(query, project, time_scope, filters)`
- `fetch_atom(atom_id)`
- `expand_relations(node_id, relation_types, depth)`
- `find_skills(query, project)`
- `get_evidence(object_id)`
- `get_conflicts(object_id)`
- `retrieve_context_bundle(query, intent, budget)`
- `record_usage_feedback(object_ids, outcome, notes)`

知识调用默认只读。QCLAW与受信任ingestion worker拥有写入权限，普通AI不得直接改权威知识。

## 十一、GPT在线调用双通道

### 当前可立即使用

ChatGPT通过GitHub应用读取私有知识仓库中的Markdown、JSON/YAML和索引文件。需要在项目说明中固定执行四轮检索：直接、机制、反例、意外关联。

### 目标通道

建立远程只读“第二大脑MCP/API”，后端查询Supabase混合检索。由于不同ChatGPT套餐对自定义MCP能力不同，系统不能把可用性建立在单一套餐功能上；GitHub读取始终作为降级通道。

## 十二、同步流程

```text
QCLAW生成packet
→ 本地Schema校验
→ 内容哈希与幂等键
→ 建任务分支
→ 提交到私有知识仓库
→ CI再次校验
→ projector读取变更packet
→ Supabase事务性upsert
→ 建全文索引与Embedding
→ 执行检索验收集
→ 记录ingestion_run和git_commit_sha
→ 成功后发布可检索状态
```

幂等键建议：

`sha256(source_hash + protocol_version + normalizer_version + packet_payload_hash)`

同一幂等键重复执行必须返回既有导入结果，不产生重复原子。

## 十三、冲突与版本

- 永远不直接覆盖知识原子；
- 更新产生新`atom_version`；
- `SUPERSEDES`、`CORRECTS`、`CONTRADICTS`显式建边；
- 当前有效版本由治理规则计算，而不是删除旧版本；
- 高冲突、低证据和高风险内容进入quarantine；
- 每次检索必须能返回适用条件、反例和证据。

## 十四、安全

- 私人知识只进入私有仓库与私有Supabase项目；
- 当前公开协调仓库不得保存真实知识内容；
- `.env`、Token、数据库密码、service role key禁止提交；
- GitHub Secrets或本地凭证管理器保存部署凭证；
- Supabase开启RLS；
- AI调用使用只读角色；
- service role只给ingestion worker；
- Supabase官方MCP仅用于受控开发管理，不直接作为开放的生产知识接口；
- 自建第二大脑MCP只暴露固定查询工具，不暴露任意SQL。

## 十五、免费层与成本策略

### Supabase Free适合MVP

当前免费层可用于小规模个人知识库，但有数据库、文件存储、流量和活跃项目限额，并可能在一周不活跃后暂停。免费层无自动备份，因此GitHub权威仓库必须保证可重建。

### 零新增费用路径

- GitHub私有仓库；
- 本地QCLAW；
- 本地Embedding模型；
- Supabase Free；
- 本地self-hosted同步器；
- GitHub作为永久备份与权威历史。

### 升级触发

只有出现以下情况才考虑付费：

- 数据库逼近免费限额；
- 一周暂停影响日常调用；
- 需要自动备份或更高可用；
- 多用户并发与权限复杂化；
- 远程MCP/API需要稳定生产SLA。

## 十六、实施阶段

### Phase 0 现场审计

确认本地第二大脑目录、现有知识格式、Docker/Node/Supabase CLI、GitHub私有仓库、QCLAW读写能力、当前ChatGPT GitHub访问和MCP计划能力。

### Phase 1 合同与Schema

冻结KnowledgePacket、Atom、Relation、Skill、ImportReport JSON Schema和ID规则。

### Phase 2 私有知识仓库

建立目录、协议、样例数据、校验器和本地测试。

### Phase 3 Supabase本地开发栈

建立`supabase/`、迁移、seed、RLS与重建测试。

### Phase 4 云端项目

创建免费Supabase项目，链接CLI，执行dry-run和迁移部署。

### Phase 5 Projector同步器

实现GitHub packet到Supabase的幂等导入、事务、失败回滚和运行报告。

### Phase 6 混合检索

实现全文、向量、关系、冲突与surprise-links检索及重排。

### Phase 7 调用接口

实现只读REST/RPC与第二大脑MCP工具。

### Phase 8 QCLAW接入

QCLAW只负责消化和写入候选packet，不负责日常调用。

### Phase 9 多AI接入

GPT先使用GitHub通道，支持MCP的客户端使用Supabase检索通道；Codex、WB和交易系统统一调用同一工具合同。

### Phase 10 验收与运行

使用交易、导演、项目规则、用户偏好、经验复盘各两组真实材料建立测试集。

## 十七、验收门禁

1. 本地可从零重建Supabase Schema；
2. 同一packet重复导入不产生重复记录；
3. 每个数据库对象可追溯到Git路径和commit SHA；
4. QCLAW下线后仍能检索；
5. GitHub通道和Supabase通道返回一致核心知识；
6. 直接、同义、模糊、反向、关系与意外关联测试通过；
7. 冲突、反例和失效条件不会被遗漏；
8. RLS阻止匿名读写与普通AI写入；
9. Supabase清空后可从GitHub完整重建；
10. 导入失败不会发布半成品；
11. 不含任何真实凭证；
12. 全流程输出Agent执行反馈v2。

## 十八、当前最合理的MVP

第一版不要同时建设复杂双向同步、网页UI和自动知识裁决。只做：

1. 私有GitHub知识仓库；
2. QCLAW标准packet；
3. Supabase表、RLS和pgvector；
4. 单向幂等projector；
5. 五个只读检索工具；
6. GitHub检索降级；
7. 十组真实材料验收。

## 十九、关键决策

- GitHub是权威，Supabase是服务层；
- 单向投影优先于自由双向同步；
- 本地Embedding优先以保持免费；
- 私有知识仓库与公开协调仓库分离；
- QCLAW是临时消化器，不是在线调用器；
- GPT当前先走GitHub通道，MCP作为增强而不是单点依赖；
- 所有知识、关系和技能必须保留证据与版本链。
