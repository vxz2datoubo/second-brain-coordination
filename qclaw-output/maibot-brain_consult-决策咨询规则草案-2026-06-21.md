# brain_consult 决策咨询规则草案

日期：2026-06-21
来源任务：QC-02
适用对象：WorkBuddy (WB-01) / Codex (CX-01 / CX-02)
依赖：InnerBrainStore 数据模型（QC-01 产出）
状态：草案，待落地

## 设计决策

选定方案：**纯关键词 + 风险分层上限**（方案 C）

理由：
1. 不依赖 embedding 模型——MaiBot 刚修完 embedding 配置错误，一期不应再绑死模型可用性
2. 红线/规则用 trigger_keywords 匹配，命中率可控、可调试
3. 后续平滑升级到 embedding：只需替换"知识/教训"召回阶段的文本匹配为语义搜索
4. 一期实现量最小，Decision Brain 接入成本最低

---

## 一、brain_consult 调用契约

```
brain_consult(topic: str, risk_level: str) → ConsultResult

risk_level 取值:
  "high"   → 涉及资金/安全/不可逆操作
  "medium" → 涉及方法选择/工具使用/有一定后果
  "low"    → 信息查询/学习/讨论/闲聊中的知识调用

ConsultResult 结构:
{
  "topic":          "原始输入",
  "risk_level":     "输入的风险等级",
  "redlines":       [RedlineItem, ...],    ← 命中的红线（全部返回）
  "rules":          [RuleItem, ...],       ← 命中的规则（按优先级）
  "lessons":        [LessonItem, ...],     ← 命中的教训（按 severity × recency）
  "knowledge":      [KnowledgeItem, ...],  ← 命中的知识（按相关度）
  "postmortems":    [PostmortemItem, ...], ← 命中的复盘（按时间）
  "has_conflicts":  bool,                  ← 是否存在矛盾规则/教训
  "confidence":     "high | medium | low", ← 整体检索信心
}
```

---

## 二、检索执行流程

### 步骤 1：解析 topic → 提取关键词

```
输入: "我想满仓买入昆仑万维300418"
分词: [满仓, 买入, 昆仑万维, 300418]
提取: stock_code = "300418", stock_name = "昆仑万维"
      action_keywords = ["满仓", "买入"]
```

关键词提取策略（一期用简单规则）：

```python
# 伪代码，非实现
def extract_keywords(topic: str) -> Keywords:
    # 1. 用 jieba/内置分词器 分词
    tokens = tokenize(topic)
    
    # 2. 识别特殊实体
    stock_codes = [t for t in tokens if re.match(r'^00\d{4}$|^30\d{4}$|^60\d{4}$', t)]
    stock_names = []  # 维护一个已知股票名列表做匹配
    
    # 3. 去停用词（的、了、是、我、想、要、一个...）
    content_words = [t for t in tokens if t not in STOP_WORDS]
    
    return Keywords(
        raw=topic,
        tokens=content_words,
        stock_codes=stock_codes,
        stock_names=stock_names
    )
```

> WorkBuddy 落地提示：MaiBot 已集成 jieba（用于中文分词），直接复用。如果没有，用 `re.findall(r'[\u4e00-\u9fff]+', topic)` 做最简中文分词也勉强可用。

### 步骤 2：红线检查（最高优先级，必须最先执行）

```
FOR EACH redline IN redline_index (常驻内存):
    FOR EACH keyword IN keywords.tokens:
        IF keyword IN redline.trigger_keywords:
            ADD redline TO result.redlines (去重)

redlines 永远全部返回，不截断
```

复杂度：redline_index ≤ 30 条 × keyword ≤ 20 个 → 最多 600 次字符串匹配 → <1ms

**特殊情况**：如果 topic 中包含股票代码（如 300418），且红线有条件含 `stock:300418` 或 `stock:*`，则即使触发词不直接匹配，也追加该红线到结果中（因为讨论持仓股票本身就是高风险场景）。

### 步骤 3：规则检索

```
FOR EACH rule IN type_index["rule"]:
    score = 0
    
    # 关键词命中加分
    FOR EACH keyword IN keywords.tokens:
        IF keyword IN rule.trigger_keywords:
            score += 2     ← trigger_keywords 精确匹配权重最高
        ELIF keyword IN rule.title:
            score += 1
    
    # topic 标签与 rule.scope 匹配加分（如 scope="stock:300418"）
    IF keywords.stock_codes CONTAINS scope_stock_code:
        score += 3
    
    # 按 priority 调整
    score *= (4 - rule.priority)  # priority=1 → ×3, priority=2 → ×2, priority=3 → ×1
    
    IF score > 0:
        ADD (rule, score) TO candidates

SORT candidates BY score DESC
TRUNCATE to rules_limit (见下方风险分级表)
```

### 步骤 4：教训检索

```
FOR EACH lesson IN type_index["lesson"]:
    score = 0
    
    FOR EACH keyword IN keywords.tokens:
        IF keyword IN lesson.topic_tags:
            score += 2
        IF keyword IN lesson.title:
            score += 2
        IF keyword IN lesson.lesson_text:
            score += 1
        IF keyword IN lesson.context:
            score += 1
    
    # 股票代码精确匹配（如果 topic 提到具体股票）
    IF keywords.stock_codes OVERLAP lesson.topic_tags:
        score += 3
    
    # 陈旧度衰减
    days_since = (now - lesson.last_reviewed).days IF lesson.last_reviewed ELSE (now - lesson.created_at).days
    decay = 1 / (1 + math.log(max(days_since, 1) + 1))
    score *= decay
    
    # severity 加权
    score *= lesson.severity
    
    IF score > 0:
        ADD (lesson, score) TO candidates

SORT BY score DESC
TRUNCATE to lessons_limit
```

### 步骤 5：知识检索

```
关键词匹配模式（无 embedding 的情况下）：
- title 包含 → 权重 3
- tags 包含 → 权重 2
- content 包含 → 权重 1
- 多个关键词都命中 → 乘法加成（不是加法）

SORT BY weighted_score DESC
TRUNCATE to knowledge_limit
```

### 步骤 6：复盘检索

```
关键词匹配 + topic_tags 模糊匹配
SORT BY created_at DESC（最新的复盘最有用）
TRUNCATE to postmortem_limit
```

---

## 三、风险分级返回上限

这是控制噪声的核心机制。不是固定 `top_k`，而是根据风险等级差异化每种类型的返回数量。

```
┌────────────────┬─────────┬─────────┬─────────┐
│ 类型           │ HIGH    │ MEDIUM  │ LOW     │
├────────────────┼─────────┼─────────┼─────────┤
│ redlines       │ ALL     │ ALL     │ top-3   │
│ rules          │ top-8   │ top-5   │ top-3   │
│ lessons        │ top-5   │ top-3   │ top-2   │
│                │(sev≥3)  │(sev≥2)  │(不限)   │
│ knowledge      │ top-3   │ top-5   │ top-8   │
│ postmortems    │ top-2   │ top-1   │ top-1   │
├────────────────┼─────────┼─────────┼─────────┤
│ 总上限(不含红线)│ 18      │ 14      │ 14      │
└────────────────┴─────────┴─────────┴─────────┘
```

注意：总上限是软上限——如果 redlines 超过 3 条（在 LOW 模式），仍然全部返回，不会截断。

---

## 四、噪声控制策略

### 4.1 规则覆盖去重

```
对于每条候选 lesson：
  IF 存在 rule.derived_from CONTAINS lesson.id:
      保留 rule，lesson 降为附注（只返回 lesson.lesson_text，不返回完整字段）
      lesson.score *= 0.3
```

语义：如果一条教训已经蒸馏成了规则，那教训本身变成补充信息而非主要依据。

### 4.2 陈旧度衰减（仅适用于教训和知识）

```
lesson: score *= 1 / (1 + ln(days_since_last_review + 1))
knowledge: score *= 1 / (1 + ln(days_since_last_access + 1))
```

规则和红线不衰减——规范不随时间失效。

### 4.3 矛盾标记（不隐藏）

```
IF result.rules 中存在两条 scope 相同但 action 相反的规则：
    result.has_conflicts = true
    两条都保留，各附加 conflict_flag = true
```

不替 Decision Brain 做选择，但必须让它知道存在矛盾。

### 4.4 低价值过滤

在返回前统一过滤：
- `importance < 2` 且 `access_count < 3` 的知识条目 → 丢弃
- `severity < 2` 且 `reinforcement_count = 0` 且创建超过 90 天的教训 → 丢弃
- `rating < 2` 的复盘 → 丢弃

---

## 五、confidence 计算规则

```
confidence = "high"   IF: redlines 命中 > 0  OR  rules 命中 ≥ 3  OR  lessons(sev≥4) 命中 > 0
confidence = "medium" IF: (rules 命中 1-2)  OR  (knowledge 命中 ≥ 3)  OR  (lessons 命中 ≥ 2)
confidence = "low"    IF: 上述都不满足（检索结果以知识为主、没有强约束）
```

Decision Brain 可以根据 confidence 决定：
- confidence = "low" → 可以直接回复（没有强依据约束）
- confidence = "high" 且 redlines 触发 → 必须阻断或警告

---

## 六、与 Decision Brain 的配合

```
Decision Brain 收到用户请求
    │
    ├─ 判断请求类型（陪伴/知识/复杂任务）
    │
    ├─ 如果是知识/复杂任务：
    │   │
    │   ├─ 评估 risk_level（涉及钱→high，涉及代码→medium，纯聊天→low）
    │   │
    │   ├─ 调用 brain_consult(topic, risk_level)
    │   │
    │   ├─ 收到 ConsultResult：
    │   │   ├─ redlines 非空 → block_action=true 的 → 直接阻断并回复
    │   │   ├─ has_conflicts → 向用户说明当前知识体系有矛盾，给出两条路径
    │   │   ├─ confidence = low → 只参考 knowledge，不强制约束行为
    │   │   └─ confidence = high → 规则/教训作为决策依据的一部分
    │   │
    │   └─ 综合后决定：直接回复 / 调 QClaw 分析 / 调 WorkBuddy 执行
    │
    └─ 如果是陪伴对话：不调 brain_consult
```

---

## 七、降级方案（embedding 不可用时）

当前方案（纯关键词）本身就是降级方案。如果将来加了 embedding：

```
优先：embedding 语义搜索 → 召回 top-50 → 按本草案的风险上限截断
降级：纯关键词匹配 → 按本草案流程 → 直接返回

切换条件：embedding 模型连续失败 3 次 → 自动降级
恢复条件：embedding 模型连续成功 3 次 → 自动恢复
```

---

## 八、一期不做的

1. **不做向量语义搜索**——留到后续升级
2. **不做多轮追溯**（lesson → 关联 knowledge → 关联 lesson…递归展开）——只做一层关联
3. **不做自动规则发现**（从多条相似教训中自动提炼规则）——这是 InnerBrain 的 digest 能力，不是 consult 的职责
4. **不做用户偏好注入**（如"用户只想要简洁建议"）——这是 Companion Brain 在 Decision Brain 之前的职责

---

## 九、未决事项

1. 分词器选型：MaiBot 已有 jieba 就用 jieba，否则用正则 `[\u4e00-\u9fff]+` 最简方案
2. 停用词表：建议从 jieba 自带停用词 + MaiBot 场景词续补（"洛雪""蓝色光标""昆仑万维"等不应被去掉）
3. trigger_keywords 的维护责任：brain_digest 写规则/教训时是否自动提取 —— 建议手动维护（自动提取不准，反而污染索引）
4. 红线索引的触发条件是否需要支持正则 —— 一期不用，关键词匹配足够

---

*本草案由 QC-02 任务产出。WorkBuddy 落地时请对接到 InnerBrainStore 的实际存储 API。*
