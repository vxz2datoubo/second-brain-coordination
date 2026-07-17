# InnerBrainStore 最小数据模型设计草案

日期：2026-06-21
来源任务：QC-01
适用对象：WorkBuddy (WB-01) / Codex (CX-02)
状态：设计草案，待 WorkBuddy 落地

## 设计决策

选定方案：**主表 + 类型特化扩展索引**（方案 C）

理由：
1. 一期只有一张主表，实现量可控
2. 规则/红线/教训/知识/复盘五种类型共享核心字段，但扩展索引支持差异化检索
3. brain_search 查主表，brain_consult 走内存类型索引快速命中红线/高优规则
4. 未来迁移时，一张主表导出比多表 JOIN 简单

---

## 一、存储结构

### 1.1 物理存储

```
MaiBot 内部文件路径（由 WorkBuddy 确定）：
  {maibot_data_root}/inner_brain/items.jsonl    ← 主存储（一行一个 JSON 对象）
  {maibot_data_root}/inner_brain/type_index.json ← 类型索引（随写更新）
  {maibot_data_root}/inner_brain/redline_index.json ← 红线专用索引（常驻，极少变化）
```

为什么选 JSONL（而不是 SQLite）：
- 与 A_Memorix 的存储风格一致
- 一条一条追加，不会锁表
- 迁移时直接复制文件
- 红线数量极少（≤30 条），完全可以一次性加载到内存

> 注：WorkBuddy 可根据 MaiBot 现有存储规范调整格式。

### 1.2 核心条目（core item）

所有五种类型的共有字段：

```yaml
id:             "字符串，唯一ID，建议格式 {type_prefix}_{uuid8}"   # 如 kn_X7k2p1m3 / ru_L9a4b5c6
item_type:      "枚举: knowledge | rule | lesson | redline | postmortem"
title:          "简洁标题，≤80字符，检索和列表展示用"
content:        "正文，可多段落，utf-8"
tags:           "字符串数组，如 ['股票','t+0','VWAP']"
source:         "来源标注: manual | digest | lesson_extract | rule_extract | import"
importance:     "整数 1-5，1=补充参考，5=核心知识"
created_at:     "ISO 时间戳"
updated_at:     "ISO 时间戳"
last_accessed:  "ISO 时间戳（brain_search/brain_consult 命中时更新）"
access_count:   "整数，累计检索命中次数"
```

### 1.3 类型特化扩展字段

每种类型在上述共有字段基础上追加：

**knowledge（专题知识）**

```yaml
category:       "分类: finance_trade | tech_knowledge | life_decision | project_meta | general"
confidence:     "浮点数 0.0-1.0，0.5=不确定，0.9=高度可信"
related_ids:    "字符串数组，引用其他条目的 id（跨类型也可引用）"
digest_source:  "字符串，如 '用户对话 #2026-06-21_14:32'（仅 source=digest 时填写）"
```

**rule（规则）**

```yaml
scope:          "适用范围: global | topic:{name} | stock:{code} | task_type:{type}"
priority:       "整数 1-3，1=必须遵守，2=强烈建议，3=参考建议"
trigger_keywords: "字符串数组，如 ['追高','打板','满仓']——无 embedding 时的主要命中手段"
positive_example: "遵守规则的正面案例（简短文本）"
negative_example: "违反规则的后果案例（简短文本）"
derived_from:   "字符串数组，引用的教训 ID 列表（此规则是从哪些教训蒸馏出来的）"
```

**lesson（教训）**

```yaml
context:        "发生情境（简短描述什么情况下发生的）"
decision:       "当时做的决定"
outcome:        "结果"
lesson_text:    "提炼的一句话教训"
severity:       "整数 1-5，1=小失误/微调，5=重大亏损/不可逆后果"
redline_flag:   "布尔，是否升级为红线"
topic_tags:     "字符串数组，关联话题标签"
linked_task_id: "字符串或 null，关联 TaskLedger 的任务 id（复盘产生时有值）"
reinforcement_count: "整数，被引用/回顾的次数（防止遗忘）"
last_reviewed:  "ISO 时间戳或 null，上次回顾时间"
```

**redline（红线）**

```yaml
condition:      "触发条件，如'单票仓位 > 50%'或'止损不设置'"
consequence:    "违规后果描述"
mitigation:     "如果已触发，最小缓解措施"
block_action:   "布尔，是否阻断执行（大部分红线应设为 true）"
severity:       "始终为 5"
derived_from:   "字符串数组，引用教训 ID"
```

**postmortem（复盘）**

```yaml
task_id:        "关联 TaskLedger 的任务 id（必填，复盘必须有来源）"
plan:           "原计划"
actual:         "实际发生了什么"
delta:          "计划与实际的关键差异"
root_cause:     "根因分析"
extracted_lesson_ids: "字符串数组，从中蒸馏出的教训 id"
extracted_rule_ids:   "字符串数组，从中蒸馏出的规则 id"
should_precipitate:   "布尔，是否应沉淀进 InnerBrainStore（由 Quality Filter 判断）"
rating:         "整数 1-5，复盘质量评分（1=敷衍，5=深度分析）"
```

---

## 二、类型索引

### 2.1 类型索引结构

```json
{
  "knowledge":   ["kn_*", ...],
  "rule":        ["ru_*", ...],
  "lesson":      ["ls_*", ...],
  "redline":     ["rl_*", ...],
  "postmortem":  ["pm_*", ...]
}
```

### 2.2 红线独立索引（常驻内存）

```json
[
  {
    "id": "rl_X7k2p1m3",
    "condition": "单票仓位 > 50%",
    "trigger_keywords": ["满仓", "重仓", "梭哈", "all in"],
    "block_action": true,
    "mitigation": "立即减仓至 ≤ 30% 或设置严格止损"
  },
  {
    "id": "rl_L9a4b5c6",
    "condition": "止损不设置",
    "trigger_keywords": ["不止损", "扛", "死扛", "补仓摊平"],
    "block_action": true,
    "mitigation": "必须设置止损价，不得加仓摊平"
  },
  ...  ← 最多 15-30 条
]
```

红线条目极少，brain_consult 第一步就是在红线索引里做关键词匹配，O(n) 也完全可接受（n≤30）。

### 2.3 关键词倒排索引（可选优化）

如果知识量超过 500 条，建议构建一个简单的 TF-IDF 倒排索引加速检索：

```
{maibot_data_root}/inner_brain/keyword_index.json
{
  "追高":   ["ru_001", "ls_003", "ls_012"],
  "VWAP":   ["kn_005", "ls_008", "pm_002"],
  ...
}
```

brain_digest 时自动更新关键词索引。

---

## 三、brain_* 接口与 InnerBrainStore 的映射

| 接口 | 内部操作 | 查哪些索引 |
|------|---------|-----------|
| `brain_search(query, top_k, scope)` | 关键词匹配（tag + title + trigger_keywords）→ 返回 top_k | 倒排索引 → 主表 |
| `brain_consult(topic, risk_level)` | 见 QC-02 决策咨询规则草案 | 红线索引 → 类型索引 → 倒排索引 |
| `brain_digest(text, title, source, kind)` | 解析 kind → 写入对应类型的条目 → 更新类型索引 → 更新倒排索引 | 写操作 |
| `brain_read(node_id, relation_depth)` | 查主表 + 递归展开 related_ids | 主表 |
| `brain_export(filter, format)` | 按 filter 筛选 → 输出 JSONL 或 JSON 数组 | 主表全量 |

---

## 四、与 A_Memorix 的边界检查清单

写 InnerBrainStore 前必须确认：

- [ ] 本条不包含用户昵称、偏好、关系状态 → 否则属于 A_Memorix
- [ ] 本条不包含聊天原文（message_id / 时间戳聊天）→ 否则属于 A_Memorix
- [ ] 本条不是任务运行状态（如"正在执行第3步"）→ 否则属于 TaskLedger
- [ ] 本条的 source 是 digest 时 → 原始聊天上下文留在 A_Memorix，只把"消化后的知识"写入 InnerBrainStore

---

## 五、迁移友好性

### 导出格式

```json
{
  "version": "inner_brain_v1",
  "exported_at": "2026-07-15T10:30:00Z",
  "items": [ /* 所有 core item 的完整 JSON 数组 */ ],
  "indexes": {
    "type_index": { /* 类型索引拷贝 */ },
    "redline_index": [ /* 红线索引拷贝 */ ]
  }
}
```

### 迁移到外挂第二大脑时

1. 遍历 items → 过滤出 `should_precipitate = true` 的条目及 `importance ≥ 3` 的条目
2. 按 第二大脑 的 12 类分类重新归类
3. 保留 item.id 作为 `source_inner_brain_id`，方便溯源
4. 低价值条目（importance=1、无任何引用、超过 180 天未访问）→ 丢弃

---

## 六、未决事项（需 WorkBuddy/Codex 确认本地后再定）

1. JSONL 文件大小上限是否需要分段（单文件 > 10MB 时是否分片）—— 一期大概率不会超
2. 倒排索引是每次写入后全量重建，还是增量追加 —— 一期建议增量（添加新条目时只追加新 token）
3. 是否需要支持条目"软删除"（deleted 标记而非物理删除）—— 建议有，迁移时清理
4. brain_digest 的自动分类逻辑（从文本推断 item_type）—— 可用简单规则：含"必须/禁止/不要"→rule，含"上次/之前/踩坑/教训"→lesson，含"复盘/回顾"→postmortem，其余→knowledge

---

*本草案由 QC-01 任务产出。WorkBuddy 落地时请根据 MaiBot 本地存储规范调整文件路径和格式。*
