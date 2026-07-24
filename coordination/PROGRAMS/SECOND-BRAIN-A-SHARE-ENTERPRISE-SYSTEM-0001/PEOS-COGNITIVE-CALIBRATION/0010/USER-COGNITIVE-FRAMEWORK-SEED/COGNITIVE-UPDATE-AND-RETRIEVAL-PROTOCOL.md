# 认知框架更新与检索协议 v0.1

> status: `RESEARCH_CANDIDATE`
>
> canonical_runtime: `NO`
>
> user_review_required: `YES`

## 1. 目标

建立一个能随聊天、学习、任务和结果持续演化的认知框架，同时防止：

- 一次对话被误写成永久特质；
- AI 只保存支持自己判断的证据；
- 用户观点被误写成外部世界事实；
- 角色扮演、玩笑、疲劳或情绪状态污染真实画像；
- 旧认知长期不复审；
- 公开仓库泄露私人信息。

## 2. 写入对象

每次更新只能写入以下对象之一：

1. `CognitiveObservation`：一次具体观察；
2. `KnowledgeMasteryUpdate`：某个概念掌握度变化；
3. `CognitiveGapCandidate`：新发现的缺口；
4. `UnknownRegistryEntry`：已知未知或未知未知；
5. `ReasoningPatternCandidate`：需要多次验证的推理模式；
6. `UserConfirmedPreference`：用户明确确认的学习或解释偏好；
7. `UserCorrection`：对模型判断的修正、争议或撤销；
8. `LearningTask`：补足缺口的行动；
9. `ValidationResult`：任务、预测或案例验证结果。

## 3. 对话采集流程

### 3.1 情境识别

先判断当前内容属于：

- 严肃观点；
- 探索性假设；
- 反讽或玩笑；
- 角色扮演；
- 情绪表达；
- 工作任务；
- 高风险决策；
- 用户纠错；
- 显式记忆写入请求。

无法判断时标记 `NEEDS_USER_CLARIFICATION`，不得强行画像。

### 3.2 原子化

把讨论拆为：

- 原始观点；
- 论据；
- 案例；
- 隐含假设；
- 反例；
- 相关术语；
- 尚未解决的问题；
- 用户明确同意或纠正的部分。

### 3.3 候选生成

候选记录必须回答：

- 这是知识、能力、偏好、状态还是推理模式；
- 适用于哪个领域和情境；
- 有哪些支持证据；
- 有哪些反向证据；
- 当前置信度是多少；
- 哪些条件会使它失效；
- 是否需要用户复审。

### 3.4 升级规则

```text
单次出现
→ Observation

多次独立出现
→ Candidate Feature

用户明确确认 + 证据一致
→ User-Confirmed Feature

出现反例或用户纠正
→ Disputed / Corrected / Superseded

长时间无支持或情境变化
→ Stale / Expired / Review Required
```

稳定能力或倾向至少需要三次跨时间、跨情境或跨任务观察。高风险判断需要更多证据和独立复核。

## 4. “认知点拨”协议

用户明确要求，在非简单事实问答中，AI 除了回应表面问题，还应检查以下层次：

1. **术语层**：这个直觉是否已有学科名称；
2. **前提层**：结论依赖哪些未说出的假设；
3. **反例层**：最强反方是什么；
4. **边界层**：在哪些条件下成立或失效；
5. **证据层**：哪些是事实，哪些只是合理推断；
6. **迁移层**：能否应用到其他领域；
7. **形式化层**：能否转换为变量、因果图、概率或指标；
8. **元认知层**：用户是否高估、低估或尚未意识到自己的能力与缺口；
9. **行动层**：下一步最小学习或验证任务是什么。

点拨必须自然融入讨论，不应居高临下，也不应为了显得聪明而强行塞术语。

## 5. 显式触发词处理

当用户说：

- “记忆采集”；
- “录入永久记忆”；
- “放入认知框架”；
- “以后记得提醒我”；

系统应：

1. 提炼真正需要长期保留的原则；
2. 区分公开安全内容与私人内容；
3. 创建候选记录；
4. 告知用户写入了什么，而不是只说“记住了”；
5. 仍保留用户纠正、撤销和版本更新权。

## 6. 检索策略

一次认知检索不应只做语义相似度。建议采用六路检索：

1. **精确实体检索**：术语、项目、案例、feature_id；
2. **全文/BM25**：用户原始措辞和关键词；
3. **语义检索**：相似观点和隐含关系；
4. **图谱检索**：观点、理论、证据、反例和任务关系；
5. **时间检索**：认知形成、变化、纠正和过期；
6. **情境检索**：当前任务、风险、用户状态和领域。

排序应综合：

- 当前任务相关性；
- 用户确认等级；
- 证据质量；
- 时间新鲜度；
- 反向证据；
- 领域匹配；
- 隐私权限。

## 7. 典型检索问题

- “我对系统论学到哪里了？”
- “我在哪些地方只是有直觉但缺术语？”
- “我最近发现了哪些未知未知？”
- “我对媒体影响的观点有哪些支持和反例？”
- “我在哪些领域能迁移局部最优与整体最优的框架？”
- “我过去在哪些决策中知道方法但执行失败？”
- “这次问题最可能触发我的哪些认知盲点？”
- “哪项能力已经过三次独立验证？”

## 8. 冲突与纠错

当新记录与旧记录冲突时，不覆盖旧内容。应保留：

```text
旧判断
新证据
冲突原因
领域或状态差异
用户解释
当前版本
仍未解决的 UNKNOWN
```

用户纠错优先级高于模型对用户的推断，但用户对外部世界的观点仍需外部证据验证。

## 9. 状态、特质和情境分离

示例：

- “今天疲劳时反应慢”是状态；
- “在高压交易任务中容易跳过检查”可能是情境倾向；
- “永远不严谨”是未经支持的绝对特质，禁止写入。

同样，角色扮演、情侣对话、网络梗测试和故意反驳不能直接用于真实认知能力评价，除非用户明确要求并有独立证据。

## 10. 公开与私有存储

### 公开 GitHub 可存

- 抽象认知框架；
- 学术术语；
- 公开安全的讨论摘要；
- 不含身份细节的学习路线；
- schema 和协议。

### 私有层才可存

- 原始聊天全文；
- 个人身份和联系方式；
- 精确财务、健康、关系和生活轨迹；
- 私人决策细节；
- 账号、凭据和密钥。

## 11. 最小数据合同候选

```yaml
entry_id: CE-...
entry_type: OBSERVATION | MASTERY | GAP | UNKNOWN | FEATURE_CANDIDATE | USER_CORRECTION
statement: ...
domain_scope: []
situation_scope: []
epistemic_status: OBSERVED | INFERRED | USER_CONFIRMED | DISPUTED | RETRACTED
mastery_stage: ...
evidence:
  supporting: []
  opposing: []
confidence:
  value: 0.0
  basis: ...
temporal:
  first_seen: ...
  last_seen: ...
  review_after: ...
user_review:
  status: NOT_REVIEWED | ACCEPTED | CORRECTED | REVOKED
invalidation_conditions: []
privacy_class: PUBLIC_SAFE | PRIVATE | SENSITIVE_RESTRICTED
```

## 12. 质量指标候选

- Unsupported Profile Rate；
- False Trait Fixation Rate；
- State-Trait Confusion Rate；
- User Correction Latency；
- Counterevidence Coverage；
- Unknown Recall Rate；
- Cross-Domain Transfer Accuracy；
- Stale Cognition Leakage；
- Private-to-Public Leakage；
- Retrieval Relevance@K；
- 用户主观“被准确理解”评分；
- 点拨后真实学习或决策改善率。

## 13. 与正式运行时的集成边界

在 Issue #61/#72 完成接口冻结前：

- 本协议只作为研究候选；
- 不创建第二套 canonical 数据库；
- 不绕过 Issue #38 知识网关；
- 不直接修改交易、概率或资本配置事实；
- 后续由 Codex 将成熟字段映射到正式 schema；
- QCLAW 可负责原子化、候选关系和检索夹具；
- WorkBuddy 只负责本地来源、格式和真实导入验证；
- GPT 负责认知点拨、反向审视和用户复审编排。
