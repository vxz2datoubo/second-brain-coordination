# 第二大脑通用方法论企业级集成蓝图 v1.1

> `blueprint_id: SECOND-BRAIN-GENERIC-METHODOLOGY-ENTERPRISE-INTEGRATION-0001`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `parent_blueprint: SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP-INTEGRATION-BLUEPRINT.md`
>
> `owner: USER`
>
> `architecture_owner: GPT`
>
> `implementation_owner: CODEX`
>
> `qclaw_role: OPTIONAL_BACKFILL_AND_HUMAN_TEMPLATE_CURATION`
>
> `workbuddy_role: LOCAL_VERIFICATION_ONLY`
>
> `boundary: CANDIDATE_BLUEPRINT / PUBLIC_SAFE / NO_TRADE / NO_NEW_CANONICAL_AUTHORITY`
>
> `status: REVISED_AFTER_INDEPENDENT_REVIEW`
>
> `amed_level: C_PROPOSAL_ONLY`
>
> `review_history: v1.0 proposed 2026-08-24; v1.1 revised after independent review (17 findings, 12 fixed)`

## 一、定位与存在理由

### 1.1 问题

企业级第二大脑（W3 / CLTM-0021 / Memory Palace / KnowledgeAtom）已经在技术实现层覆盖了：原子化知识、双向链接、知识图谱、13步写入管道、retrieval-before-write、retrieval-before-answer、双时间治理、四层认知映射、15+篇AI/记忆学术论文。

但在**通用方法论层**和**人类可读操作层**存在9个已验证缺口：

| # | 缺口 | 通用方法论来源 | 企业级现状 |
|---|------|---------------|-----------|
| G1 | PARA按可操作性分类 | Tiago Forte BASB | 无用户-facing组织层，只有系统层级L0-L7和atom类型 |
| G2 | Zettelkasten人类实践法 | Luhmann / Ahrens | 有KnowledgeAtom技术实现，但无闪念/文献/永久三笔记操作指南、无Luhmann编号、无链接发现法 |
| G3 | 渐进式总结（面向阅读） | Tiago Forte | 有知识蒸馏管道，但无面向人类阅读的五层蒸馏输出（加粗/高亮/摘要/Remix） |
| G4 | MOC人工策展 | Nick Milo LYT | 有自动知识图谱，但无人工策展的CuratedGraphView概念 |
| G5 | GTD个人任务整合 | David Allen | 有AMED/Issue/Control Tower，但无个人五步工作流（Capture/Clarify/Organize/Reflect/Engage）与知识的整合 |
| G6 | 行为级失败模式 | 社区实践+PKM研究 | 有技术级risk_register，但无用户行为失败模式（收藏家/完美主义者/管理员等） |
| G7 | 人类可读笔记模板 | 通用PKM实践 | 有机器YAML/JSON模板，但无人类Markdown模板（项目笔记/文献笔记/日记/周回顾） |
| G8 | PKM经典学术文献 | Drucker/Bush/Davies/PKM4E | 有AI/记忆方向15+论文，但无PKM经典方向（知识工作者、Memex、个人知识库PKB） |
| G9 | 方法论选择决策树 | 综合对比 | 无Agent/用户选择合适方法论的决策框架 |

### 1.2 本蓝图的边界

**做什么**：把上述9个通用方法论概念映射为企业级W3系统的**上层接口字段、派生视图、人类操作指南和补充模板**。

**不做什么**：
- 不创建第二套知识权威或平行数据库；
- 不修改W3 canonical原子结构；
- 不替代现有的13步写入管道或retrieval架构；
- 不引入真实私有数据或生产桥接；
- 不解锁formal skill promotion。

### 1.3 核心设计原则

1. **叠加而非替代**：所有通用方法论概念作为W3之上的派生层或标注层存在；
2. **机器可读优先，人类可读可选**：每个概念必须有对应的机器字段，人类模板是渲染层；
3. **可重建投影**：所有自动派生的视图（PARA分类查询、渐进式总结的自动层）可从canonical原子重建；**人工策展意图（MOC叙述、人工标注、人类编辑）是独立的人工数据，不声称可自动重建**；
4. **证据绑定**：人类操作产生的任何标注必须回溯到SourceEpisode和KnowledgeAtom；
5. **范围隔离**：通用方法论层不影响交易系统、风控门或现有治理协议；
6. **优先级分层**：字段结构/基础设施可先实现（P0），内容生成/高级功能后实现（P1+）。

---

## 二、9个缺口的企业级映射

### G1: PARA分类法 → `organizational_layer` 标注字段

#### 通用概念
PARA = Projects（有截止日的活跃工作）/ Areas（持续责任）/ Resources（主题兴趣）/ Archives（已完成）。按可操作性而非主题分类。

#### 企业级映射

在KnowledgeAtom和EpisodicObject上增加可选标注字段（不改变canonical identity）：

```yaml
organizational_layer:
  para_category: PROJECT | AREA | RESOURCE | ARCHIVE
  para_project_id: <optional, links to Project object>
  para_area_id: <optional>
  para_moved_at: <timestamp>
  para_moved_by: USER | GPT | CODEX | QCLAW
  para_archive_reason: COMPLETED | SUPERSEDED | ABANDONED | ON_HOLD
```

#### 集成点
- PARA分类是**用户-facing视图**，不影响atom的canonical存储位置；
- Project对象复用现有Plan/Constraint/Outcome模型，增加`para_type: PROJECT`标注；
- Archives通过`valid_to`和`supersedes`关系实现，不物理删除；
- Dataview式查询可按`para_category`过滤，生成PARA四象限视图。

#### 与现有系统的关系
- 现有L0-L7层级不变；
- PARA是跨层级的用户组织视图，一个L2 Semantic atom可以同时属于某个Project；
- 与AMED的任务系统通过Project对象关联。

---

### G2: Zettelkasten人类实践法 → 三种笔记类型 + 链接发现协议

#### 通用概念
- Fleeting Notes（闪念）：临时捕获，1-2天内处理；
- Literature Notes（文献）：阅读时的理解，关联来源；
- Permanent Notes（永久）：原子化独立想法，用自己的话，双向链接。

#### 企业级映射

在SourceEpisode和KnowledgeAtom上增加`zettelkasten_role`标注：

```yaml
zettelkasten_role:
  note_type: FLEETING | LITERATURE | PERMANENT
  fleeting_expires_at: <timestamp, only for FLEETING>
  literature_source_ref: <SourceEpisode id, only for LITERATURE>
  permanent_atomicity_check: PASS | FAIL | NOT_CHECKED
  permanent_self_contained: true | false
  luhmann_branch_id: <optional, e.g. "12a3">
  link_discovery_status: PENDING | DISCOVERED | EXHAUSTED
```

#### 链接发现协议（补充现有retrieval-before-write）

在写入新Permanent atom时，在13步管道的**step 7 RETRIEVAL_BEFORE_WRITE之后、step 9 RELATION_EXTRACTION之前**，增加人类辅助的链接发现步骤：

1. **词汇触发**：搜索atom中的关键术语，匹配已有atom标题；
2. **实体图遍历**：通过共享实体发现2-hop关联；
3. **结构类比**：通过mechanism/constraint相似度发现低词汇重叠的关联；
4. **人工确认**：AI建议链接，用户确认或拒绝，拒绝记录为`NEGATIVE_LINK_EVIDENCE`；
5. **链接质量标注**：每个链接增加`link_rationale`（因果/对比/补充/例证）和`link_confidence`。

#### 与现有系统的关系
- 复用现有KnowledgeAtom和relation_vocabulary；
- `zettelkasten_role`是标注层，不改变atom identity；
- 链接发现协议是retrieval-before-write的人类增强步骤，不替代自动调和（step 8 RECONCILIATION）；
- Luhmann编号是可选的人类可读标识，canonical ID仍是系统生成的atom_id。

---

### G3: 渐进式总结（面向阅读）→ `distillation_layers` 派生视图

#### 通用概念
五层蒸馏：Layer 0原文 → Layer 1笔记 → Layer 2加粗 → Layer 3高亮 → Layer 4执行摘要 → Layer 5 Remix。

#### 企业级映射

在KnowledgeAtom上增加`distillation_layers`结构化字段：

```yaml
distillation_layers:
  layer0_source_span_ref: <SourceEpisode span id>
  layer1_full_note: <text, initial extraction>
  layer2_bold_spans:
    - span_id: <id>
      text: <bolded passage>
      rationale: <why this is key>
  layer3_highlight_spans:
    - span_id: <id>
      text: <highlighted phrase>
      parent_bold_span: <span_id>
  layer4_executive_summary: <2-5 sentences, own words>
  layer5_remix_refs:
    - output_type: ARTICLE | DECISION | CODE | SPEECH | PROJECT
      output_ref: <id or link>
  distillation_progress: 0 | 1 | 2 | 3 | 4 | 5
  last_distilled_at: <timestamp>
  distilled_by: USER | GPT | QCLAW
```

#### 实现分层（重要）
- **P0（PHASE_C）**: 实现`distillation_layers`字段结构、存储、序列化、查询。Layer 0-1由现有FAITHFUL_EXTRACTION步骤自动填充。
- **P1（PHASE_D+）**: 实现AI辅助的Layer 2-4自动生成、人类审核工作流、Layer 5 Remix追踪。
- 字段结构先到位，内容生成后到位，避免阻塞PHASE_C。

#### 渲染规则
- 人类视图默认显示Layer 4摘要（如果存在），否则显示Layer 1，可展开下层；
- "飞机与降落伞"导航：摘要=山峰，点击深入各层；
- AI在retrieval时优先返回最高可用层的摘要，需要时展开下层；
- 蒸馏是机会主义的，不要求所有atom到达Layer 4+。

#### 与现有系统的关系
- 复用现有SourceEpisode和KnowledgeAtom；
- `distillation_layers`是派生内容，canonical仍是layer0的source span；
- 与现有的13步写入管道中的FAITHFUL_EXTRACTION（step 2）和EPISTEMIC_CLASSIFICATION（step 4）步骤对齐；
- AI辅助蒸馏时必须标注`distilled_by: GPT`并保留人类审核状态。

---

### G4: MOC人工策展 → `CuratedGraphView` 派生对象

#### 通用概念
MOC（Map of Content）= 人工策展的链接索引，带叙述和上下文，不是自动图谱也不是文件夹。

#### 企业级映射

新增派生对象类型`CuratedGraphView`：

```yaml
CuratedGraphView:
  view_id: <id>
  moc_type: THEMATIC | PROJECT | PERSON | TIMELINE | OUTPUT | OVERVIEW
  title: <human title>
  narrative_intro: <2-3 sentences, personal understanding>  # 人工策展意图，不可自动重建
  curated_links:
    - atom_ref: <KnowledgeAtom id>
      section: <section heading>
      annotation: <why this link, context>  # 人工标注，不可自动重建
      relation_to_theme: CORE | SUPPORTING | CONTRARIAN | EXAMPLE | OPEN_QUESTION
  sections:
    - heading: <section title>
      description: <optional narrative>  # 人工叙述
      link_refs: [<curated_link ids>]
  related_mocs: [<CuratedGraphView ids>]
  source_atom_refs: [<KnowledgeAtom ids that inspired this MOC>]
  created_at: <timestamp>
  last_curated_at: <timestamp>
  curated_by: USER | GPT
  auto_generated_draft: true | false
  human_reviewed: true | false
  rebuildable_components: [curated_links_atom_refs]  # 链接引用可从atoms重建；叙述/标注/章节结构不可
```

#### 可重建性澄清（修正v1.0矛盾）
- **可自动重建的部分**：`curated_links`中的`atom_ref`引用（如果atom被删除，链接可标记为broken）；`source_atom_refs`。
- **不可自动重建的部分**：`narrative_intro`、`annotation`、`sections`结构和描述、`relation_to_theme`分类。这些是人工策展意图，必须独立持久化和版本化。
- **重建策略**：从atoms可重建"哪些atom被引用"，但不能重建"为什么被引用"和"如何组织叙述"。MOC的价值在于后者。

#### MOC与自动图谱的区别
| 维度 | 自动知识图谱 | MOC (CuratedGraphView) |
|------|------------|----------------------|
| 生成方式 | 自动从relation提取 | 人工策展，AI可起草 |
| 叙述层 | 无 | 有（narrative_intro + section descriptions） |
| 链接质量 | 所有relation | 人工筛选+标注rationale |
| 更新频率 | 实时 | 机会主义，随理解演进 |
| 可重建性 | 完全可从atoms重建 | 链接引用可重建，策展意图不可 |
| 用途 | 全局发现、多跳推理 | 主题导航、深度理解、输出准备 |

#### 与现有系统的关系
- `CuratedGraphView`存储在W3但标注为`projection_type: CURATED_MOC`，`is_rebuildable: PARTIAL`；
- 不创建新的canonical知识原子；
- MOC中的链接复用现有relation_vocabulary，增加`curated_annotation`；
- 与GraphRAG式community summary的区别：community summary是自动聚类，MOC是人工策展。

---

### G5: GTD个人任务整合 → 个人任务层与知识的双向链接

#### 通用概念
GTD五步：Capture → Clarify → Organize → Reflect → Engage。与PARA的Projects联动。

#### 企业级映射

在现有Plan/Constraint/Outcome模型基础上，增加`gtd_state`标注和个人工作流视图：

```yaml
gtd_personal_task:
  task_id: <id>
  gtd_state: INBOX | CLARIFIED | NEXT_ACTION | WAITING | SCHEDULED | SOMEDAY | DONE | ARCHIVED
  clarify_result:
    is_actionable: true | false
    outcome_type: SINGLE_ACTION | PROJECT | REFERENCE | TRASH | SOMEDAY
    next_physical_action: <text>
    context: @COMPUTER | @PHONE | @ERRANDS | @HOME | @OFFICE | @ANYWHERE
    energy_required: LOW | MEDIUM | HIGH
    time_estimate_minutes: <int>
  project_ref: <optional, Project/Plan id>
  linked_knowledge_atoms: [<KnowledgeAtom ids>]
  weekly_review_touched_at: <timestamp>
```

#### GTD与AMED优先级规则（新增）
当同一个任务同时有GTD个人状态和AMED企业级状态时：
1. **交易相关任务**：AMED状态和A股风控门**绝对优先**，GTD标注仅作个人视图补充，不改变任何权限或执行逻辑。
2. **非交易的企业任务**（如AMED治理任务、代码实现任务）：AMED状态为权威，GTD状态为个人辅助视图。
3. **纯个人任务**（无AMED对应）：GTD状态为权威。
4. **冲突解决**：如果GTD状态标记为DONE但AMED状态不是DONE，以AMED为准，并生成`GTD_AMED_MISMATCH_OBSERVATION`供用户确认。

#### 周回顾整合（与现有AMED回顾互补）

个人周回顾清单（区别于AMED的任务级回顾）：

```
□ 清空所有Inbox（个人捕获）
□ 澄清新捕获项（GTD Clarify）
□ 更新项目状态（PARA Projects → ARCHIVE完成项）
□ 检查Waiting For
□ 查看下周日历
□ 提炼高价值笔记（渐进式总结Layer 2/3）
□ 更新相关MOC
□ 选择下周1-3个重点
```

#### 与现有系统的关系
- 复用现有Plan/Constraint/Outcome和Issue系统；
- `gtd_state`是个人任务标注，不替代AMED的企业级任务合同；
- 个人任务与KnowledgeAtom双向链接：任务引用相关知识，知识引用产生它的任务；
- 周回顾是个人层操作，与AMED的标准/战略任务回顾并行但不冲突；
- 交易相关任务继续受A股风控门约束，GTD标注不改变权限。

---

### G6: 行为级失败模式 → `user_behavior_failure_mode` 补充风险登记

#### 通用概念
6种行为失败模式。

#### 企业级映射

在risk_register中增加用户行为维度。所有6种模式的完整结构如下：

```yaml
user_behavior_failure_modes:
  - mode: COLLECTOR
    description: "只收集不使用，捕获率远高于蒸馏率和产出率"
    indicators:
      - capture_rate >> distillation_rate
      - inbox_size > threshold for > N days
      - zero output_products in 30 days
    detection_metrics:
      - capture_to_distill_ratio
      - inbox_age_distribution
      - output_frequency
    mitigation:
      - raise capture bar (only "resonates" not "might be useful")
      - inbox hard limit with forced processing
      - monthly output requirement
  - mode: PERFECTIONIST
    description: "系统优化时间超过实际使用时间，笔记永远不够好"
    indicators:
      - tool_change_frequency > threshold
      - system_config_time >> usage_time
      - notes never "good enough" to save
    mitigation:
      - tool freeze period (90 days)
      - "good enough" note standard
      - timebox system maintenance to 30 min/week
  - mode: JANITOR
    description: "整理和维护系统成为主要活动，实际知识产出被挤出"
    indicators:
      - reorganization_frequency > threshold
      - tag/category maintenance time >> content creation time
      - high atom edit rate but low new atom rate
    mitigation:
      - monthly reorganization freeze
      - "just-in-time" organization (only organize when needed)
      - timebox maintenance
  - mode: TOPIC_FILER
    description: "按主题而非可操作性分类，导致知道存哪但不知道该做什么"
    indicators:
      - high topic_tag count but low para_category usage
      - atoms with no project/action linkage
      - user reports "I know I saved it but can't find when I need it"
    mitigation:
      - PARA分类默认提示
      - "what will I do with this?" capture question
      - periodic action-link audit
  - mode: NON_DISTILLER
    description: "全文剪藏不提炼，知识库变成全文搜索引擎而非思考工具"
    indicators:
      - distillation_progress distribution skewed to 0-1
      - high raw_content storage but low layer4 summary count
      - retrieval returns full text not summaries
    mitigation:
      - layer1 extraction mandatory at capture
      - AI-assisted layer4 draft suggestion
      - "one sentence summary" capture requirement
  - mode: TOOL_FRAGMENTER
    description: "多工具并行使用无集成，知识分散在多个系统中无法关联"
    indicators:
      - multiple active storage locations detected
      - cross-tool link count = 0
      - user mentions different tools for different tasks
    mitigation:
      - canonical store enforcement (W3 as system of record)
      - import/export bridges for auxiliary tools
      - "one canonical copy" principle
```

#### 检测机制与隐私保护
- 从W3使用日志中**被动计算聚合指标**（不增加用户负担），不记录具体内容，只记录行为模式统计；
- 超过阈值时生成`BEHAVIORAL_RISK_OBSERVATION`，不自动干预；
- 用户可查看、确认或驳回观察；
- 确认的观察进入PersonalCognitiveModel的`cognitive_pattern`字段；
- **隐私保护**：行为指标存储为聚合统计，不关联具体atom内容；用户可随时清除行为历史；行为观察不影响任何权限或风控决策。

#### 与现有系统的关系
- 补充现有技术级risk_register，不替代；
- 与PersonalCognitiveModel（PEOS蓝图）的认知偏差检测联动；
- 所有观察都是`OBSERVATION`级别，不形成`trait`判断；
- 用户可冻结、修正或撤销任何行为观察。

---

### G7: 人类可读笔记模板 → Markdown渲染层

#### 通用概念
6种人类模板：项目笔记、文献笔记、永久笔记、MOC、日记、周回顾。

#### 企业级映射

为每种机器对象定义Markdown渲染模板（渲染层，不改变canonical数据）：

| 人类模板 | 对应机器对象 | 渲染要点 | 实现阶段 |
|---------|------------|---------|---------|
| 项目笔记 | Project + linked atoms | 目标/下一步/等待中/决策日志/相关资料/复盘 | PHASE_C |
| 文献笔记 | SourceEpisode + Literature atoms | 元数据/核心论点/关键摘录/个人理解/引发问题/关联 | PHASE_C |
| 永久笔记 | Permanent KnowledgeAtom | 一句话表述/详细阐述/为什么重要/关联/来源 | PHASE_C |
| MOC | CuratedGraphView | 概述/核心概念/方法论/实践案例/待探索/相关MOC | P1（PHASE_D+） |
| 日记 | Daily Episode + fleeting atoms | 今日重点/捕获/会议/反思/明日计划/关联 | PHASE_C |
| 周回顾 | Weekly Review Episode | 清空Inbox/项目更新/任务清理/知识维护/亮点/下周重点/数据 | PHASE_C |

#### 模板实现
- 模板存储为可渲染的Markdown skeleton，带变量占位符；
- 渲染时从W3 canonical对象填充数据；
- 人类编辑Markdown后，变更通过`human_annotation`字段回写（结构见下方），不直接修改canonical atom；
- AI可生成模板草稿，人类审核确认。

#### HumanAnnotation结构（新增定义）
```yaml
human_annotation:
  annotation_id: <id>
  target_atom_id: <id>
  target_field: <canonical_statement | conditions | assumptions | custom>
  annotation_type: CORRECTION | ADDITION | CLARIFICATION | TAG | CUSTOM
  content: <text>
  created_at: <timestamp>
  created_by: USER
  applied_to_canonical: true | false  # 是否已合并到canonical（需审核）
  merge_requested_at: <optional timestamp>
```

#### 与现有系统的关系
- 复用现有TEMPLATES目录的机器模板格式；
- 人类模板是`rendering_layer`，标注为`template_type: HUMAN_MARKDOWN`；
- 与QCLAW的知识消化联动：QCLAW生成atom，人类模板渲染供阅读和编辑。

---

### G8: PKM经典学术文献 → 研究基础补充

#### 通用概念
PKM领域经典文献：Drucker知识工作者、Bush Memex、Davies个人知识库(PKB)、PKM4E赋能框架、个人知识基础设施与影子IT。

#### 企业级映射

在现有`research_design_basis`中补充PKM经典方向：

```yaml
research_design_basis_pkm_classics:
  - id: DRUCKER-1968
    contribution: "知识工作者概念，知识作为关键资源，个人知识管理是组织知识管理基础"
    integration_point: "justifies PersonalCognitiveModel and owner stance tracking"
  - id: BUSH-1945-MEMEX
    contribution: "associative indexing, 个人信息存储设备构想，超文本和PKB思想源头"
    integration_point: "justifies entity_graph and associative retrieval architecture"
  - id: DAVIES-PKB-2005
    contribution: "个人知识库(PKB)定义、分类法、设计选择分析，60年Memex未实现"
    integration_point: "validates W3 as PKB implementation, informs design tradeoffs"
  - id: PKM4E-2015
    contribution: "个人知识管理赋能框架，无知矩阵扩展，大数据与外部智能"
    integration_point: "informs cognitive mapping and UNKNOWN tracking"
  - id: JARRAHI-PKI-SHADOW-IT-2020
    contribution: "个人知识基础设施作为影子IT，非正式社交网络支持PKM"
    integration_point: "justifies multi-agent coordination and informal knowledge flows"
  - id: SHUJAHAT-PKM-JOB-DESIGN-2021
    contribution: "工作定义、创新要求、终身学习对PKM的正向影响；过度自主性的负向影响"
    integration_point: "informs AMED task design and bounded autonomy principles"
```

#### 与现有AI/记忆文献的关系
- 现有15+篇AI/记忆论文（RAG/GraphRAG/A-Mem/HaluMem等）覆盖**技术实现层**；
- PKM经典文献覆盖**理论基础和用户行为层**；
- 两者互补：AI论文回答"怎么技术实现"，PKM经典回答"为什么这样设计、用户怎么用"；
- 所有引用保持现有格式（id + contribution + integration_point）。

---

### G9: 方法论选择决策树 → Agent路由辅助

#### 通用概念
根据用户目标和场景选择合适的方法论组合：BASB vs Zettelkasten vs PARA+GTD vs AI原生。

#### 企业级映射

在GPT认知路由器中增加`methodology_selection`子路由：

```yaml
methodology_selection_decision:
  input_signals:
    - user_goal: PROJECT_OUTPUT | ACADEMIC_RESEARCH | LIFE_ORGANIZATION | AI_ASSISTANT | EXPLORATORY
    - note_volume_estimate: <int, from W3 atom count>
    - technical_comfort_inferred: LOW | MEDIUM | HIGH  # from interaction history, not explicit user profile
    - collaboration_need: NONE | TEAM | PUBLIC
  data_sources:
    note_volume_estimate: "W3 atom count by user_scope"
    technical_comfort_inferred: "from interaction complexity history (PEOS PersonalCognitiveModel)"
    user_goal: "from current request intent classification"
    collaboration_need: "from project_scope and shared atom indicators"
  recommended_composition:
    primary_methodology: BASB | ZETTELKASTEN | PARA_GTD | AI_NATIVE | HYBRID
    supporting_methodologies: [<list>]
    rationale: <explanation>
    minimum_viable_setup: [<steps>]
    expected_maintenance_cost: LOW | MEDIUM | HIGH
  methodology_gap_analysis:
    - current_methodology: <what user is using>
    - missing_capabilities: [<list>]
    - recommended_additions: [<list with priority>]
```

#### 决策逻辑
1. 项目输出为主 → BASB(CODE+PARA)，任务多则+GTD；
2. 学术/深度写作为主 → Zettelkasten，笔记>100则+MOC；
3. 生活信息管理 → PARA+GTD；
4. AI驱动知识库 → 全方法论+AI集成（现有W3架构）；
5. 技术用户 → 可叠加Johnny Decimal文件编码。

#### 与现有系统的关系
- 作为GPT认知路由器的辅助模块，不改变现有retrieval架构；
- 帮助GPT在与用户交互时推荐合适的工作方式；
- 与四层认知映射联动：根据用户的`UNKNOWN_REQUIRES_SCAFFOLDING`概念调整解释深度；
- 输入信号从W3使用数据和PEOS PersonalCognitiveModel获取，不创建新的用户画像系统。

---

## 三、实现优先级与依赖

### 3.1 优先级排序

| 优先级 | 缺口 | 理由 | 依赖 |
|--------|------|------|------|
| P0 | G7 人类模板 | 立即提升可用性，纯渲染层无风险；5种模板PHASE_C可实现 | 无 |
| P0 | G1 PARA分类 | 用户-facing组织层，价值高，实现简单；字段结构PHASE_C到位 | 无 |
| P0 | G3 字段结构 | distillation_layers字段结构+Layer 0-1自动填充，是渲染和后续蒸馏的基础 | 无 |
| P1 | G3 内容生成 | AI辅助Layer 2-4生成+人类审核工作流 | G3字段结构、G7渲染 |
| P1 | G4 MOC策展 | 知识图谱的人工增强层；CuratedGraphView对象+模板 | G1（PARA分类） |
| P2 | G2 Zettelkasten实践 | 链接发现协议较复杂；三笔记类型标注+人类辅助链接 | G3（蒸馏）、G4（MOC） |
| P2 | G5 GTD整合 | 与AMED需仔细对齐边界；优先级规则已定义 | G1（PARA） |
| P2 | G8 PKM文献 | 纯文档补充，无实现风险；排P2因为不阻塞任何功能，可随时加入 | 无 |
| P3 | G6 行为失败模式 | 需要使用日志积累；6种模式已完整定义 | 系统运行数据 |
| P3 | G9 决策树 | 路由器增强，依赖其他模块数据积累 | G1-G5 |

### 3.2 与PHASE_C的关系

本蓝图的P0项可作为PHASE_C（知识对象与调和层实现）的**首批垂直切片**：
- **G1 PARA分类**：PHASE_C实现KnowledgeAtom schema时，同步增加`organizational_layer`字段；
- **G3 字段结构**：PHASE_C实现`distillation_layers`字段结构+Layer 0-1自动填充（由FAITHFUL_EXTRACTION步骤驱动）；Layer 2-4内容生成推迟到P1；
- **G7 人类模板**：PHASE_C实现5种模板（项目/文献/永久/日记/周回顾）的渲染逻辑；MOC模板推迟到P1（因为G4是P1）。

### 3.3 不阻塞主线

本蓝图所有内容均为C级提案，不阻塞R145/R146/R147等现有执行路线。实现时需：
1. 先通过GPT独立审核；
2. 作为新的governed task释放；
3. 不与现有active route争用worker slot。

---

## 四、验收标准

本蓝图被接受为有效提案的标准：

1. **不创建平行权威**：所有9个映射均为标注层/派生视图/渲染层，canonical仍是W3原子；
2. **可重建性诚实声明**：自动派生部分可重建，人工策展意图明确标记为不可自动重建；
3. **证据绑定**：人类操作产生的标注可回溯到SourceEpisode；
4. **范围隔离**：不影响交易系统、风控门、现有治理协议；GTD/AMED冲突时AMED优先；
5. **与现有架构对齐**：字段命名、对象模型、关系词汇与现有蓝图一致；
6. **优先级分层清晰**：字段结构/基础设施P0，内容生成/高级功能P1+，不阻塞PHASE_C；
7. **隐私保护**：行为模式检测使用聚合统计，不关联具体内容，用户可清除。

---

## 五、UNKNOWN与待决问题

1. `CuratedGraphView`的人工策展意图版本化策略：是否需要完整的version history，还是只保留last_curated_at？需实现时设计；
2. 行为失败模式的检测阈值如何校准？需真实使用数据，初始阈值为启发式；
3. GTD个人任务与AMED企业任务的边界在实际使用中是否会混淆？需影子测试，优先级规则已预定义；
4. 人类Markdown模板的编辑回写机制：HumanAnnotation结构已定义，但是否需要diff级别的审计？需实现时决定；
5. PARA分类与现有L0-L7层级在查询时的性能影响？需基准测试，预期影响很小（标注字段有索引）；
6. G9决策树的technical_comfort_inferred准确性？依赖PEOS PersonalCognitiveModel的成熟度。

---

## 六、参考与继承

- 继承：`SECOND-BRAIN-GPT-COGNITIVE-CLOSED-LOOP-INTEGRATION-BLUEPRINT.md`
- 继承：`PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-BLUEPRINT-v1.0.md`
- 继承：`KNOWLEDGE-SOURCE-SEMANTIC-RECONSTRUCTION-AND-GRAPH-PROJECTION-BLUEPRINT-v1.0.md`
- 参考：`GPT-SECOND-BRAIN-KNOWLEDGE-DIGESTION-ASSOCIATIVE-RECALL-SKILL-v1.0.yaml (v1.1)`
- 通用方法论来源：Tiago Forte BASB、Sönke Ahrens Smart Notes、Nick Milo LYT、David Allen GTD、Johnny Decimal System
- PKM经典文献：Drucker 1968、Bush 1945、Davies 2005、PKM4E 2015、Jarrahi 2020、Shujahat 2021

---

*本蓝图为C级PROPOSAL_ONLY。v1.1已通过独立审核（17项发现，12项已修正，5项轻微问题记录为UNKNOWN待决）。需GPT独立审核后作为新governed task释放。不直接写入main，不解锁任何执行权限。*
