# PHASE_C: 知识对象与调和层实现蓝图 v1.0

> `blueprint_id: SECOND-BRAIN-PHASE-C-KNOWLEDGE-OBJECT-AND-RECONCILIATION-0001`
>
> `parent_program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001`
>
> `parent_skill: GPT-SECOND-BRAIN-KNOWLEDGE-DIGESTION-ASSOCIATIVE-RECALL-SKILL-v1.0.yaml (v1.1)`
>
> `dependency: PHASE_B COMPLETED (R109 accepted, PR #280 merged 2026-08-14)`
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
> `boundary: CANDIDATE_BLUEPRINT / PUBLIC_SAFE / NO_TRADE / NO_LIVE_BRIDGE`
>
> `status: PROPOSED_AWAITING_GOVERNED_TASK_RELEASE`
>
> `amed_level: C_PROPOSAL_ONLY`

## 一、PHASE_C 目标

在已验收的R109 Memory Palace地基之上，实现**知识对象层**和**调和层**，使GPT能够：

1. 将任意输入（文章、段落、研究发现、案例、规则、经验、对话洞察、修正）消化为**源锚定的原子化知识对象**；
2. 在写入前执行**检索-比对-调和**，选择正确的演化动作（新建/重复/合并/精炼/支持/削弱/矛盾/取代/撤销/重验证），而非盲目追加；
3. 维护**知识图谱演化**，包括高置信边、显式UNKNOWN边、冲突集和取代链；
4. 通过**合成测试套件**验证调和正确性、原子化质量、图谱一致性和范围隔离；
5. 集成P0通用方法论标注字段（PARA分类、渐进式总结层）和人类可读Markdown渲染模板。

## 二、范围与边界

### 2.1 包含

- KnowledgeEpisode（不可变源事件）schema，兼容W3
- KnowledgeAtom（原子化知识）schema，兼容W3 + P0标注字段
- ReconciliationEngine（调和引擎）：12种演化动作的判定与执行
- GraphEvolutionManager（图演化管理器）：边创建、冲突集、取代链、UNKNOWN边
- 合成测试套件：调和正确性、原子化质量、图谱一致性、范围隔离、时间推理
- 人类可读Markdown渲染模板（6种）
- 写入后验证：精确召回 + 释义召回 + 图谱召回

### 2.2 不包含

- GPT实时桥接（PHASE_D）
- 主动召回路由器（PHASE_E）
- 真实影子使用评估（PHASE_F）
- 正式技能晋升（PHASE_G）
- 任何生产环境部署或真实私有数据写入
- 交易系统集成或风控门修改

## 三、知识对象Schema

### 3.1 KnowledgeEpisode（不可变源事件）

```python
@dataclass
class KnowledgeEpisode:
    """不可变源事件。一次消化输入对应一个Episode。"""
    episode_id: str                    # UUID v7
    source_type: str                   # ARTICLE | PARAGRAPH | CONVERSATION | RESEARCH | CASE | RULE | EXPERIENCE | CORRECTION | WEB_PAGE | BOOK | PAPER
    source_pointer: str                # URL | file path | conversation ref | "inline"
    source_content_hash: str           # SHA-256 of raw content
    source_span_or_locator: str        # page/paragraph/section range or "full"
    captured_at: datetime              # ISO 8601 UTC
    published_at_if_known: Optional[datetime]
    available_at_if_decision_relevant: Optional[datetime]
    user_scope: str                    # user_id or "global"
    project_scope: Optional[str]       # project_id or None
    privacy_class: str                 # PUBLIC | INTERNAL | CONFIDENTIAL | PRIVATE
    license_or_publication_basis: Optional[str]
    source_agent_or_author: Optional[str]
    raw_content: str                   # immutable original text
    derived_atom_ids: List[str]        # atoms produced from this episode
    ingestion_status: str              # CAPTURED | EXTRACTED | ATOMIZED | CLASSIFIED | RECONCILED | WRITTEN | VERIFIED | FAILED
    ingestion_errors: List[str]        # empty if successful
```

### 3.2 KnowledgeAtom（原子化知识）

```python
@dataclass
class KnowledgeAtom:
    """源锚定的原子化知识对象。canonical权威存储在W3。"""
    atom_id: str                       # UUID v7
    canonical_statement: str           # one atomic claim/concept/mechanism in own words
    atom_type: str                     # from primary_types enum (40+ types)
    entities: List[str]                # normalized entity IDs
    topic_tags: List[str]
    epistemic_role: str                # from epistemic_roles enum
    source_refs: List[SourceRef]       # [(episode_id, span_locator, confidence)]
    evidence_quality: str              # DIRECT | INFERRED | ANECDOTAL | UNVERIFIED
    confidence: float                  # 0.0-1.0
    scope: Scope                       # user_scope + project_scope + privacy_class
    valid_from: Optional[datetime]
    valid_to: Optional[datetime]       # None = open-ended
    recorded_at: datetime
    freshness_class: str               # TRANSIENT | SHORT_CYCLE | MEDIUM_CYCLE | STRUCTURAL | UNKNOWN
    current_status: str                # CANDIDATE | ACTIVE | SUPERSEDED | REVOKED | CONFLICTED | UNKNOWN
    assumptions: List[str]
    conditions: List[str]
    exceptions: List[str]
    counterevidence: List[str]         # atom_ids of counterevidence
    invalidation_conditions: List[str]
    validation_method: Optional[str]
    cognitive_mapping_relevance: Optional[CognitiveMapping]
    
    # --- P0 Generic Methodology Annotation Fields (from integration blueprint) ---
    organizational_layer: Optional[OrganizationalLayer]  # G1 PARA
    distillation_layers: Optional[DistillationLayers]    # G3 Progressive Summarization
    zettelkasten_role: Optional[ZettelkastenRole]        # G2 (P2, optional in PHASE_C)
    
    # --- Graph & Lineage ---
    lineage_head: bool                  # is this the current head of its lineage?
    predecessor_atom_ids: List[str]     # atoms this refines/supersedes
    successor_atom_ids: List[str]       # atoms that refine/supersede this
    conflict_set_id: Optional[str]      # if in a conflict set
    relation_ids: List[str]             # graph edges involving this atom
    
    # --- Reconciliation Audit ---
    last_reconciled_at: datetime
    last_reconciliation_action: str     # NEW | DUPLICATE | MERGE | REFINE | ...
    reconciliation_evidence: str        # what retrieval results led to this decision
```

### 3.3 P0标注字段子结构

```python
@dataclass
class OrganizationalLayer:
    """G1: PARA分类标注。用户-facing组织视图，不影响canonical存储。"""
    para_category: str                 # PROJECT | AREA | RESOURCE | ARCHIVE
    para_project_id: Optional[str]
    para_area_id: Optional[str]
    para_moved_at: Optional[datetime]
    para_moved_by: Optional[str]       # USER | GPT | CODEX | QCLAW
    para_archive_reason: Optional[str]  # COMPLETED | SUPERSEDED | ABANDONED | ON_HOLD

@dataclass
class DistillationLayers:
    """G3: 渐进式总结层。派生内容，canonical仍是source span。"""
    layer0_source_span_ref: str        # SourceEpisode span id
    layer1_full_note: Optional[str]
    layer2_bold_spans: List[BoldSpan]
    layer3_highlight_spans: List[HighlightSpan]
    layer4_executive_summary: Optional[str]  # 2-5 sentences, own words
    layer5_remix_refs: List[RemixRef]
    distillation_progress: int         # 0-5
    last_distilled_at: Optional[datetime]
    distilled_by: Optional[str]        # USER | GPT | QCLAW
```

## 四、调和引擎（ReconciliationEngine）

### 4.1 12种演化动作

| 动作 | 触发条件 | 执行结果 |
|------|---------|---------|
| NEW | 无语义等价的现有atom | 创建新lineage，lineage_head=True |
| DUPLICATE | 相同语义声明+相同范围+来源等价 | 保留来源，不重复投票，标记duplicate_of |
| MERGE | 互补表示，无矛盾 | 合并为新atom，predecessors指向两者 |
| REFINE | 新证据缩小/条件化/改进现有声明 | 新atom取代旧atom为lineage_head，旧atom status=SUPERSEDED |
| SUPPORT | 独立支持，不改变命题 | 添加counterevidence的反向（support_for边），confidence可提升 |
| WEAKEN | 反证降低置信度或缩小适用范围 | 添加counterevidence，confidence降低，可能添加conditions |
| CONTRADICT | 实质不兼容声明共存 | 创建conflict_set，两个atom status=CONFLICTED |
| SUPERSEDE | 更新的/当前的声明取代旧声明用于CURRENT | 新atom lineage_head=True，旧atom status=SUPERSEDED，保留历史 |
| REVOKE | 显式失效当前使用 | atom status=REVOKED，historical evidence保留 |
| REVALIDATE | 新证据更新当前适用性 | atom status=ACTIVE，valid_from更新，confidence调整 |
| RESOLVE_UNKNOWN | 证据关闭先前跟踪的知识缺口 | 对应UNKNOWN atom status更新，添加resolution边 |
| UNKNOWN | 关系或状态无法确定 | 不强制合并，创建UNKNOWN边，记录待决 |

### 4.2 调和判定流程

```
输入: candidate_atom + retrieval_results
输出: reconciliation_decision (action + target_atom_ids + rationale)

步骤:
1. 词汇匹配: 对candidate的entities + topic_tags做精确/模糊匹配
2. 语义匹配: embedding相似度 > threshold (0.85) 的候选
3. 图谱遍历: 通过共享实体发现2-hop关联
4. 结构类比: mechanism/constraint相似度匹配
5. 范围过滤: 排除不同user_scope/project_scope/privacy_class的候选
6. 时间过滤: 排除已revoked/superseded的候选（除非任务是历史查询）
7. 逐候选比对:
   a. 语义等价性判定 (same proposition?)
   b. 范围等价性判定 (same scope?)
   c. 证据关系判定 (support/weaken/contradict/refine?)
   d. 时间关系判定 (before/after/overlap?)
8. 选择最高置信动作
9. 如果置信度 < 0.6 → UNKNOWN
10. 生成rationale，记录检索证据
```

### 4.3 调和置信度门

- `confidence >= 0.85`: 自动执行
- `0.6 <= confidence < 0.85`: 标记为`REQUIRES_HUMAN_REVIEW`，不自动执行
- `confidence < 0.6`: UNKNOWN，不执行，记录待决

## 五、图演化管理器（GraphEvolutionManager）

### 5.1 边类型

复用技能规范中的`relation_vocabulary`（6大类，40+边类型）。

### 5.2 边创建规则

```python
@dataclass
class KnowledgeRelation:
    relation_id: str
    source_atom_id: str
    target_atom_id: str
    relation_type: str                # from relation_vocabulary
    confidence: float                 # 0.0-1.0
    rationale: str                    # why this edge exists
    evidence_refs: List[str]          # source spans supporting this edge
    created_at: datetime
    created_by: str                   # GPT | CODEX | QCLAW | USER
    status: str                       # ACTIVE | REVOKED | SUPERSEDED
    is_unknown: bool                  # explicit UNKNOWN edge
    human_confirmed: Optional[bool]   # None = not reviewed
```

### 5.3 冲突集

```python
@dataclass
class ConflictSet:
    conflict_set_id: str
    member_atom_ids: List[str]
    conflict_type: str                # FACTUAL | VALUE | SCOPE | TEMPORAL | DEFINITIONAL
    description: str
    discovered_at: datetime
    discovered_by: str
    resolution_status: str            # OPEN | PARTIALLY_RESOLVED | RESOLVED | ESCALATED
    resolution_at: Optional[datetime]
    resolution_notes: Optional[str]
```

### 5.4 取代链

每个atom的`predecessor_atom_ids`和`successor_atom_ids`形成有向无环图。
- 查询CURRENT状态时，只返回lineage_head=True的atom
- 查询HISTORICAL状态时，可遍历predecessors
- 取代链必须是单向的（A supersedes B，B不能supersedes A）

## 六、合成测试套件

### 6.1 调和正确性测试（20+用例）

| 测试ID | 场景 | 期望动作 |
|--------|------|---------|
| REC-001 | 全新概念，无匹配 | NEW |
| REC-002 | 完全相同的声明，不同来源 | DUPLICATE |
| REC-003 | 同一概念的互补描述 | MERGE |
| REC-004 | 新证据缩小适用范围 | REFINE |
| REC-005 | 独立来源支持同一声明 | SUPPORT |
| REC-006 | 反证削弱声明 | WEAKEN |
| REC-007 | 实质矛盾的声明 | CONTRADICT |
| REC-008 | 更新版本取代旧版本 | SUPERSEDE |
| REC-009 | 显式撤销 | REVOKE |
| REC-010 | 新证据重验证过期声明 | REVALIDATE |
| REC-011 | 关闭先前的UNKNOWN | RESOLVE_UNKNOWN |
| REC-012 | 无法确定关系 | UNKNOWN |
| REC-013 | 跨范围匹配（应忽略） | NEW（范围隔离） |
| REC-014 | 低置信语义匹配 | UNKNOWN |
| REC-015 | 多候选冲突 | CONTRADICT + conflict_set |

### 6.2 原子化质量测试

- `over_fragmentation_rate`: 一个完整机制被拆成过多碎片 → FAIL
- `under_fragmentation_rate`: 多个不兼容声明在一个atom中 → FAIL
- `source_span_fidelity`: atom内容可回溯到source span → PASS
- `epistemic_role_accuracy`: 事实/主张/推断/价值判断正确分离 → PASS
- `condition_negation_exception_preservation`: 条件、否定、例外被保留 → PASS

### 6.3 图谱一致性测试

- 取代链无环
- 冲突集成员都标记CONFLICTED
- 边的source/target都存在
- UNKNOWN边不参与自动推理
- 跨范围边不存在（除非显式标注）

### 6.4 范围隔离测试（零容忍）

- user_scope A的atom不出现在user_scope B的查询结果中
- project_scope A的atom不出现在project_scope B的查询结果中
- PRIVATE隐私类的atom不出现在PUBLIC查询中
- 已revoked的atom不出现在CURRENT查询中

### 6.5 时间推理测试

- valid_to已过的atom标记为EXPIRED
- SUPERSEDE链的CURRENT查询只返回最新head
- HISTORICAL查询可返回旧版本
- TRANSIENT类的atom在过期后不影响当前决策

## 七、人类可读Markdown渲染模板

### 7.1 模板清单

| 模板 | 对应对象 | 用途 |
|------|---------|------|
| project_note.md | Project + linked atoms | 项目笔记 |
| literature_note.md | SourceEpisode + Literature atoms | 文献笔记 |
| permanent_note.md | Permanent KnowledgeAtom | 永久笔记 |
| moc.md | CuratedGraphView | MOC（P1，PHASE_C可选） |
| daily_note.md | Daily Episode + fleeting atoms | 日记 |
| weekly_review.md | Weekly Review Episode | 周回顾 |

### 7.2 渲染规则

- 模板是渲染层，不改变canonical数据
- 人类编辑Markdown后，变更通过`human_annotation`字段回写
- AI可生成模板草稿，人类审核确认
- 每个模板包含`metadata`块（YAML frontmatter）+ `content`块

### 7.3 永久笔记模板示例

```markdown
---
atom_id: <id>
atom_type: <type>
epistemic_role: <role>
confidence: <float>
source_refs: [<episode_id:span>]
para_category: <PROJECT|AREA|RESOURCE|ARCHIVE>
distillation_progress: <0-5>
created_at: <datetime>
last_reconciled: <datetime>
status: <CANDIDATE|ACTIVE|SUPERSEDED|REVOKED>
---

# <一句话表述>

## 详细阐述
<canonical_statement的展开>

## 为什么重要
<这个知识为什么有价值>

## 条件与例外
- 条件: <conditions>
- 例外: <exceptions>
- 失效条件: <invalidation_conditions>

## 关联
- 支持: <supporting atom links>
- 反证: <counterevidence links>
- 相关: <related atom links>
- 前身: <predecessor links>

## 来源
<source refs with spans>
```

## 八、写入后验证

每个atom写入后必须通过：

1. **精确召回测试**: 用atom的canonical_statement查询，返回该atom在top-1
2. **释义召回测试**: 用canonical_statement的释义查询，返回该atom在top-3
3. **图谱召回测试**: 通过关联实体/边遍历可到达该atom
4. **范围隔离测试**: 该atom不出现在错误范围的查询中
5. **时间状态测试**: CURRENT/HISTORICAL查询返回正确状态

全部通过 → `ingestion_status=VERIFIED`
任一失败 → `ingestion_status=FAILED`，记录错误，不报告成功

## 九、实现依赖与前置条件

### 9.1 已满足

- R109 Memory Palace地基验收（PR #280 merged，27/27 + 246/246 PASS）
- 认知闭环激活（PR #286 merged）
- 技能规范v1.1更新（本分支）
- 通用方法论集成蓝图（PR #448 draft）

### 9.2 需新建

- KnowledgeEpisode/KnowledgeAtom Python dataclass或Pydantic model
- ReconciliationEngine实现
- GraphEvolutionManager实现
- 合成测试套件（pytest）
- Markdown模板文件
- 写入后验证器

### 9.3 复用现有

- W3 MemoryStore（canonical存储）
- CLTM-0021检索管道
- 现有relation_vocabulary
- 现有epistemic_roles
- 现有freshness_classes
- 现有AMED治理协议

## 十、验收标准

PHASE_C被接受为完成的标准：

1. **Schema兼容**: KnowledgeEpisode/KnowledgeAtom可序列化为W3兼容格式，无损往返
2. **调和正确性**: 20+合成测试用例全部通过，调和动作准确率>=95%
3. **原子化质量**: over/under fragmentation率<5%，source span保真度100%
4. **图谱一致性**: 无环取代链，冲突集正确标记，边完整性100%
5. **范围隔离**: 零跨范围泄漏（零容忍）
6. **时间推理**: CURRENT/HISTORICAL查询状态正确
7. **写入后验证**: 每个测试atom通过5项验证
8. **P0标注字段**: organizational_layer和distillation_layers可正确存储和查询
9. **人类模板**: 6种Markdown模板可从canonical对象渲染，人类编辑可回写
10. **不破坏现有**: 全量Phase 3 regression（246测试）仍通过
11. **公开安全**: 无私有数据，无凭证，无交易逻辑

## 十一、与后续PHASE的接口

### PHASE_D（GPT实时桥接）
- PHASE_C提供的KnowledgeAtom/ReconciliationEngine是PHASE_D桥接工具的后端
- PHASE_D暴露: memory_capture, knowledge_reconcile, memory_search, memory_recall_context, memory_conflicts, memory_feedback

### PHASE_E（主动召回路由器）
- PHASE_C的retrieval_architecture是PHASE_E路由器的基础
- PHASE_E增加: intent分类、效用预估、正负触发器判定

### PHASE_F（评估与影子使用）
- PHASE_C的合成测试是PHASE_F真实评估的基线
- PHASE_F增加: LongMemEval-style套件、真实影子对话、owner反馈循环

## 十二、UNKNOWN与待决问题

1. KnowledgeAtom的Python实现应放在哪个目录？需与现有W3代码结构对齐
2. 调和引擎的语义匹配threshold（0.85）是否需要按atom_type调整？
3. 人类Markdown编辑的回写机制是diff级还是全量覆盖？需实现时决定
4. PARA分类的初始值是AI自动建议还是必须用户指定？
5. 渐进式总结的Layer 2/3是否在PHASE_C实现，还是推迟到PHASE_D+？
6. 合成测试的fixture数据量（多少个预置atom）需要多少才能充分测试调和？

---

*本蓝图为C级PROPOSAL_ONLY，需GPT独立审核后作为新governed task释放给CODEX实现。不直接写入main，不解锁任何执行权限。*
