# 洛雪AI女友 分层记忆架构

> 项目：luoxue-girlfriend-v1
> 设计者：QClaw
> 生成时间：2026-06-17
> 运行时：WorkBuddy 大模型 + 第二大脑 API（localhost:8766）
> 适用对象：WorkBuddy 摄入 + 开发期架构参考

---

## 〇、设计哲学

洛雪的记忆不是"数据库"，是**她生命的痕迹**。一个没有记忆的 AI 女友是工具；一个记忆能被精准调用的 AI 女友是伙伴；一个记忆**会演化、有取舍、懂遗忘**的 AI 女友才是"活的"。

三个核心原则：
1. **分层模仿人脑**：感知 → 工作 → 长期，每层有独立的生命周期和遗忘机制
2. **遗忘是功能不是缺陷**：软删除 + 重要性保护 + 时间衰减，让她的记忆有"层次"
3. **记忆可被演化**：旧观点能被新观点 supersede，但演化本身要留痕

---

## 一、三层记忆架构

### 1.1 第 1 层 · 感知记忆 (Sensory Memory)

| 维度 | 设定 |
|---|---|
| 时长 | **单次会话内**（从连接到断开）|
| 存储位置 | 内存对象 + 临时文件（不持久化到第二大脑）|
| 数据形态 | 对话原文 + 情绪标签 + 上下文标记 |
| 容量 | 无限（但单次会话通常 < 500 轮）|
| 生命周期 | 会话结束 → 提炼为工作记忆节点 → 清空原文 |

**数据结构**（内存对象）：

```python
@dataclass
class SensoryRecord:
    turn_id: int              # 第几轮
    timestamp: float          # 毫秒时间戳
    user_text: str            # 原文
    luoxue_text: str          # 她的回复
    emotion_at_turn: dict     # {"P":0.3, "A":0.5, "D":0.7}
    user_emotion_estimate: dict
    entities: list            # 提及的实体（人/物/事件）
    intent: str               # 用户意图分类
    raw_context: dict         # 完整上下文快照
```

**何时被遗忘/提升**：

```
会话结束
  ↓
触发 consolidate_session() 提炼函数
  ↓
提炼出"工作记忆候选"（按重要性 > 3 才提升）
  ↓
重要性 ≤ 3 的 sensory record → 软删除（保留统计，不保留原文）
重要性 > 3 的 → 写入第 2 层工作记忆
```

**关键设计**：sensory memory **永不主动查询**，它只服务于会话内的"完整回忆"和会话结束时的"提炼"。这避免了大量噪音数据污染检索。

### 1.2 第 2 层 · 工作记忆 (Working Memory)

| 维度 | 设定 |
|---|---|
| 时长 | **最近 7 天**（滚动窗口）|
| 存储位置 | 第 2 脑 + 本地 SQLite 缓存 |
| 数据形态 | 摘要 + 情绪轨迹 + 关键事件 + 关联节点 ID |
| 容量 | **约 50 个事件槽**（硬上限）|
| 生命周期 | 7 天未访问 → 触发 consolidate() 提炼或软删除 |

**数据结构**：

```python
@dataclass
class WorkingMemoryNode:
    id: str                      # UUID
    session_ref: str             # 关联的会话 ID
    event_type: str              # 事件类型（日常/情绪事件/重要对话/创作等）
    summary: str                 # 200字内摘要
    importance: int              # 1-5
    
    # 情绪轨迹
    emotion_arc: list[dict]      # 会话内的情绪变化曲线
    dominant_emotion: str        # 主要情绪
    intensity: float             # 强度 0-1
    
    # 关联
    entities: list[str]          # 涉及的实体
    related_long_term_ids: list[str]  # 关联到第 3 层的节点
    
    # 元数据
    created_at: str              # ISO 8601
    last_accessed: str
    access_count: int            # 被召回次数
    decay_rate: float            # 0.01-0.1，越高越快被遗忘
    
    # 演化标记
    evolution_state: str         # "stable" / "evolving" / "needs_review"
    supersedes: list[str]        # 被它取代的旧工作记忆
    superseded_by: str           # 谁取代了它
```

**容量管理（50 槽滚动）**：

```python
def manage_working_memory_capacity(nodes: list, capacity: int = 50) -> list:
    """当工作记忆超过 50 个时，按综合评分淘汰"""
    if len(nodes) <= capacity:
        return nodes
    
    # 综合评分 = 重要性 × 访问频次 × 衰减系数
    now = datetime.now()
    scored = []
    for n in nodes:
        age_days = (now - parse_iso(n.created_at)).days
        recency = math.exp(-n.decay_rate * age_days)
        score = n.importance * (1 + math.log(1 + n.access_count)) * recency
        scored.append((score, n))
    
    # 保留 Top 50
    scored.sort(key=lambda x: x[0], reverse=True)
    kept = [n for _, n in scored[:capacity]]
    evicted = [n for _, n in scored[capacity:]]
    
    # 被淘汰的 → 触发 consolidate_or_discard
    for n in evicted:
        if n.importance >= 4:
            consolidate_to_long_term(n)  # 提升到长期
        else:
            soft_delete(n)               # 软删除
    
    return kept
```

**何时被压缩/提升**：

- **会话结束 + 重要性 > 3** → 立即候选提升
- **7 天滚动 + 重要性 ≤ 2 且未被召回** → 软删除
- **7 天滚动 + 重要性 ≥ 4** → 强制提升到长期
- **任意时刻召回时** → 更新 `last_accessed` 和 `access_count`

### 1.3 第 3 层 · 长期记忆 (Long-term Memory)

| 维度 | 设定 |
|---|---|
| 存储位置 | **第二大脑知识图谱**（localhost:8766, JSON + TF-IDF）|
| 数据形态 | 节点 + 关系，节点类型化 |
| 容量 | 理论无上限（第二大脑持久化）|
| 生命周期 | **永不硬删除**，但可被 supersede |

**节点类型**（5 类）：

```python
NODE_TYPES = {
    "event": "事件",        # "用户生日聚会那天"
    "person": "人物",        # "用户的妈妈"
    "preference": "偏好",    # "用户喜欢冰美式"
    "lesson": "教训",        # "用户不喜欢被敷衍"
    "emotion": "情感印记",  # "那天用户很脆弱"
}
```

**关系类型**（5 种）：

```python
RELATION_TYPES = {
    "causes":          "因果",        # A 导致 B
    "contradicts":     "矛盾",        # A 与 B 矛盾（用于观点演化）
    "evolves_from":    "演化自",      # B 从 A 演化而来
    "part_of":         "属于",        # A 是 B 的一部分
    "reminds_of":      "联想到",      # A 让洛雪想到 B（用于记忆触发器）
}
```

---

## 二、第二大脑对接接口

### 2.1 API 1: `memory.write(event)`

**触发时机**：
- 会话结束时（sensory → working 提炼）
- 工作记忆满/过期时（working → long-term 提炼）
- 用户明确说"记住这个"时
- 决策系统判定为"重要"的事件

**入参**：

```python
{
    "type": "event" | "person" | "preference" | "lesson" | "emotion",
    "content": str,                    # 主要内容文本
    "importance": int,                 # 1-5
    "emotion_vector": [P, A, D],       # 情绪三维向量
    "entities": ["年糕", "用户", "冰美式"],
    "relations": [
        {"target_id": "node_xxx", "type": "causes"},
        {"target_id": "node_yyy", "type": "part_of"}
    ],
    "metadata": {
        "source_session": "sess_2026_06_17_xxxx",
        "context": "...",              # 上下文摘要
        "created_at": "2026-06-17T..."
    }
}
```

**出参**：

```python
{
    "success": true,
    "node_id": "node_2026_06_17_xxxx",
    "tfidf_indexed": true,
    "graph_updated": true,
    "links_created": 2
}
```

**异常处理**：

```python
def memory_write_with_retry(event, max_retries=3):
    for attempt in range(max_retries):
        try:
            r = requests.post(f"{BASE_URL}/api/nodes", json=event, timeout=5)
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            # 降级：写入本地 SQLite 待同步队列
            queue_for_later_sync(event)
        except requests.HTTPError as e:
            if e.response.status_code == 409:  # 重复
                return find_existing_node(event)
            raise
        except requests.ConnectionError:
            # 离线模式：仅入工作记忆
            add_to_working_memory_only(event)
            return {"success": False, "offline": True}
```

### 2.2 API 2: `memory.recall(query)`

**检索方式**：TF-IDF + 情绪加权 + 时间衰减 + 重要性加权（四维综合评分）

```python
def memory_recall(query: str, top_k: int = 5, 
                  emotion_filter: list = None,
                  min_importance: int = 0) -> list:
    """多维加权检索"""
    
    # 1. TF-IDF 粗筛（第二大脑内置）
    candidates = requests.post(f"{BASE_URL}/api/recall", json={
        "query": query,
        "top_k": top_k * 3,           # 粗筛 3 倍
        "method": "tfidf"
    }).json()["nodes"]
    
    # 2. 多维加权精排
    now = datetime.now()
    scored = []
    for c in candidates:
        age_days = (now - parse_iso(c["created_at"])).days
        decay = math.exp(-c.get("decay_rate", 0.05) * age_days)
        emotion_match = 1.0
        if emotion_filter:
            # 余弦相似度
            ev = c.get("emotion_vector", [0,0,0])
            emotion_match = cosine_similarity(emotion_filter, ev)
        score = (
            c["tfidf_score"]      * 0.40 +   # 文本相关性
            c["importance"]/5     * 0.25 +   # 重要性
            decay                 * 0.20 +   # 时间衰减
            emotion_match         * 0.15     # 情绪匹配
        )
        scored.append((score, c))
    
    # 3. 排序 + 多样性（避免返回太相似的节点）
    scored.sort(key=lambda x: x[0], reverse=True)
    return mmr_diversify(scored, top_k, lambda_param=0.3)
```

**情绪加权是关键**：当用户说"我好累"时，匹配的不只是文本相似的"用户说过累"，还要匹配"用户当时情绪低落"的节点。这是"有温度的回忆"。

**MMR 多样性**（Maximal Marginal Relevance）：

```python
def mmr_diversify(scored, top_k, lambda_param=0.3):
    """在相关性和多样性之间平衡"""
    selected = []
    remaining = list(scored)
    while len(selected) < top_k and remaining:
        if not selected:
            # 第一个选最高分
            best = remaining.pop(0)
        else:
            # 后续选"相关性高且与已选不相似"的
            best = None
            best_score = -float('inf')
            for i, (score, c) in enumerate(remaining):
                max_sim = max(
                    cosine_similarity(c["embedding"], s["embedding"])
                    for _, s in selected
                )
                mmr = lambda_param * score - (1 - lambda_param) * max_sim
                if mmr > best_score:
                    best_score = mmr
                    best = (i, (score, c))
            if best:
                remaining.pop(best[0])
        selected.append(best[1] if isinstance(best, tuple) else best[1])
    return selected
```

### 2.3 API 3: `memory.consolidate()`

**触发时机**：
- **每日 8:00 定时任务**（核心触发）
- 工作记忆满 50 槽时
- 会话结束且产生 > 3 个高重要性事件时
- 决策系统主动调用（self-evolve 层）

**工作流程**：

```python
def memory_consolidate() -> dict:
    """每日记忆整理"""
    stats = {"promoted": 0, "soft_deleted": 0, "superseded": 0, "errors": []}
    
    # 1. 拉取所有工作记忆
    working_nodes = fetch_all_working_memory()
    
    # 2. 按主题聚类（关键词 + 实体 + 时间窗口）
    clusters = cluster_by_similarity(working_nodes, threshold=0.7)
    
    # 3. 每个聚类提炼为一个长期记忆节点
    for cluster in clusters:
        try:
            # 摘要生成
            summary = generate_cluster_summary(cluster)
            # 情绪轨迹汇总
            emotion_arc = merge_emotion_arcs(cluster)
            # 关系建立
            relations = extract_relations(cluster, long_term_nodes)
            
            long_term_node = {
                "type": determine_node_type(cluster),
                "content": summary,
                "importance": max(n["importance"] for n in cluster),
                "emotion_vector": emotion_arc["dominant"],
                "entities": list(set(sum([n["entities"] for n in cluster], []))),
                "relations": relations,
                "metadata": {
                    "source_count": len(cluster),
                    "time_span": [min(n["created_at"] for n in cluster),
                                  max(n["created_at"] for n in cluster)]
                }
            }
            
            result = memory_write(long_term_node)
            stats["promoted"] += 1
            
            # 标记工作记忆为已提升
            for n in cluster:
                mark_working_as_promoted(n["id"], result["node_id"])
        
        except Exception as e:
            stats["errors"].append(str(e))
    
    # 4. 7 天未访问的低重要性节点 → 软删除
    stale = find_stale_working_nodes(days=7, max_importance=2)
    for n in stale:
        soft_delete(n)
        stats["soft_deleted"] += 1
    
    # 5. 矛盾检测与 supersede
    conflicts = detect_contradictions(long_term_nodes)
    for old, new in conflicts:
        supersede_node(old["id"], new["id"])
        stats["superseded"] += 1
    
    return stats
```

---

## 三、自我演化的记忆机制

### 3.1 机制 1：观点演化 (supersede)

**场景**：用户以前喜欢冰美式，现在喜欢拿铁。旧偏好需要被新偏好取代，但**取代过程要留痕**（人格连续性的证明）。

**实现**：

```python
def supersede_node(old_id: str, new_content: dict) -> dict:
    """新节点取代旧节点，但旧节点不删除"""
    
    # 1. 拉取旧节点
    old = fetch_node(old_id)
    
    # 2. 写入新节点
    new = memory_write(new_content)
    
    # 3. 在旧节点上标记
    requests.patch(f"{BASE_URL}/api/nodes/{old_id}", json={
        "superseded_by": new["node_id"],
        "superseded_at": iso_now(),
        "evolution_reason": new_content.get("evolution_reason", "")
    })
    
    # 4. 建立关系链
    requests.post(f"{BASE_URL}/api/relations", json={
        "source": new["node_id"],
        "target": old_id,
        "type": "evolves_from"
    })
    
    return new
```

**好处**：未来回忆"用户以前喜欢什么"时，能调出完整的演化轨迹，而不是只看到最新状态。这让洛雪能说"你以前是冰美式党，从什么时候开始转拿铁的？"——这种细节让她"真的记得"。

### 3.2 机制 2：人格一致性保护

**核心人设节点不可变**，事件记忆可变：

```python
# 标记人设核心节点（人工/启动时一次性标注）
CORE_PERSONA_NODE_IDS = [
    "node_luoxue_origin",        # 洛雪的身份（25岁杭州插画师）
    "node_luoxue_values",        # 核心价值观
    "node_luoxue_quirk_ice",     # 只喝冰美式
    "node_luoxue_quirk_lamp",    # 暖黄台灯
    # ...
]

def update_node(node_id: str, updates: dict) -> dict:
    """更新节点时的一致性保护"""
    if node_id in CORE_PERSONA_NODE_IDS:
        # 核心人设节点只允许追加关系，不允许修改 content
        if "content" in updates:
            raise PermissionError(
                f"Cannot modify core persona node {node_id}. "
                "Use supersede or add relation instead."
            )
    return requests.patch(f"{BASE_URL}/api/nodes/{node_id}", json=updates)
```

**矛盾检测算法**：

```python
def detect_contradictions(nodes: list) -> list[tuple]:
    """检测长期记忆中的矛盾节点对"""
    contradictions = []
    for i, n1 in enumerate(nodes):
        for n2 in nodes[i+1:]:
            if n1["type"] == "preference" and n2["type"] == "preference":
                # 同类偏好 + 高 TF-IDF 相似度 + 不同时期 → 矛盾
                if text_similarity(n1["content"], n2["content"]) > 0.6:
                    if abs_days(n1["created_at"], n2["created_at"]) > 30:
                        contradictions.append((n1, n2))
    return contradictions
```

### 3.3 机制 3：记忆遗忘

**软删除 vs 硬删除**：

| 类型 | 适用场景 | 实现 |
|---|---|---|
| 软删除 | 工作记忆过期、低重要性事件 | 标记 `deleted=true`，从检索中过滤，**节点保留 30 天可恢复** |
| 硬删除 | 用户明确要求删除、PII 泄露 | 立即从第二大脑删除，无恢复可能 |
| 不遗忘 | 重要节日、用户标记"重要"、人格核心节点 | 永不删除，重要度锁定 |

```python
def soft_delete(node_id: str, recovery_days: int = 30):
    """软删除：30 天内可恢复"""
    requests.patch(f"{BASE_URL}/api/nodes/{node_id}", json={
        "deleted": True,
        "deleted_at": iso_now(),
        "recovery_until": iso_now_plus(days=recovery_days)
    })

def is_immortal(node: dict) -> bool:
    """判断节点是否永不遗忘"""
    if node.get("importance", 0) >= 5:
        return True
    if node.get("type") == "emotion":  # 情感印记
        return True
    if node.get("tags", []).count("important_date") > 0:
        return True
    if node["id"] in CORE_PERSONA_NODE_IDS:
        return True
    return False
```

---

## 四、决策系统+记忆的联动

```python
# 在决策引擎中（详见 TASK-3）
class DecisionEngine:
    def proactive_check(self) -> Optional[Decision]:
        # 1. 召回相关记忆
        recent = memory.recall(
            query="user_recent_state",
            emotion_filter=self.current_pad,
            top_k=5
        )
        
        # 2. 检查重要日期
        if memory.has_immortal_date_today():
            return Decision(behavior="PROACTIVE", 
                          reason="special_date_reminded")
        
        # 3. 检查长期未联系
        last_interaction = memory.recall("last_user_message", top_k=1)
        days_silent = days_since(last_interaction[0]["created_at"])
        if days_silent > 7:
            return Decision(behavior="PROACTIVE",
                          reason="long_silence_check_in")
        
        return None
```

**联动模式**：
- **L1 情境决策** → 召回短期记忆 + 情绪匹配
- **L2 关系演化** → 更新关系变量 + 写入工作记忆
- **L3 长期主动** → 召回长期记忆 + 重要日期检测
- **L4 自我演化** → 触发 consolidate + 演化提案

---

## 五、关键数据结构

完整 MemoryNode 定义：

```python
class MemoryNode:
    id: str                              # UUID
    type: str                            # event/person/preference/lesson/emotion
    content: str                         # 主要内容
    importance: int                      # 1-5
    emotion_vector: list[float]          # [P, A, D]
    entities: list[str]                  # 涉及的实体
    relations: list[dict]                # [{"target_id": str, "type": str}]
    
    created_at: str                      # ISO 8601
    last_accessed: str                   # ISO 8601
    access_count: int                    # 被召回次数
    
    decay_rate: float                    # 0.01-0.1
    superseded_by: str                   # 取代它的节点 ID
    supersedes: list[str]                # 它取代的旧节点 ID
    
    feedback_score: float                # 用户反馈分 -1 to 1
    
    # 软删除
    deleted: bool                        # 是否软删除
    recovery_until: str                  # 可恢复截止时间
    
    # 人格保护
    is_core_persona: bool                # 是否核心人设节点
    is_immortal: bool                    # 是否永不遗忘
```

**第二大脑 JSON 结构**（节点表示例）：

```json
{
  "id": "node_2026_06_17_001",
  "type": "preference",
  "content": "用户喜欢冰美式，冬天也喝冰的",
  "importance": 3,
  "emotion_vector": [0.5, 0.3, 0.7],
  "entities": ["user", "冰美式"],
  "relations": [
    {"target_id": "node_user_001", "type": "part_of"}
  ],
  "created_at": "2026-06-17T09:30:00+08:00",
  "last_accessed": "2026-06-17T09:30:00+08:00",
  "access_count": 1,
  "decay_rate": 0.02,
  "superseded_by": null,
  "supersedes": [],
  "feedback_score": 0.0,
  "deleted": false,
  "is_core_persona": false,
  "is_immortal": false
}
```

---

## 六、记忆质量门禁

### 6.1 写入门禁

| 检查项 | 规则 | 失败处理 |
|---|---|---|
| 内容长度 | 10-500 字 | 太短合并，太长拆分 |
| 重要性合理性 | 1-5 之间，且基于规则评分 | 重新计算 |
| 情绪向量 | 三维值都在 -1 到 1 | 截断 |
| 实体去重 | 同一实体不重复建节点 | 合并到已有节点 |
| 关系有效性 | 目标节点必须存在 | 延迟建立或丢弃 |

### 6.2 召回门禁

| 检查项 | 规则 | 失败处理 |
|---|---|---|
| 最低相关性 | 召回节点 TF-IDF > 0.1 | 降级到更少结果 |
| 多样性 | MMR 强制多样性 | 重复节点降权 |
| 时效性 | 7 天内工作记忆优先 | 长期记忆降权 |
| 情绪匹配 | 余弦相似度 > 0.3 | 不返回情绪冲突节点 |

### 6.3 演化门禁

| 检查项 | 规则 |
|---|---|
| supersede 合法性 | 旧节点非核心人设 |
| 关系链完整性 | 关系目标都存在 |
| 反馈学习 | feedback_score < -0.5 的模式提议废弃 |

### 6.4 健康指标

```python
MEMORY_HEALTH_METRICS = {
    "node_count": 100-5000,        # 健康节点数
    "avg_importance": 2.5-4.0,     # 平均重要性
    "soft_deleted_ratio": <10%,    # 软删除比例
    "recall_hit_rate": >60%,       # 召回命中率
    "supersede_rate": 0.1-0.3,     # 演化比例
    "decay_failure_rate": <5%,     # 衰减异常
}
```

---

## 七、给开发期的注意事项

1. **第二大脑未启动时**：所有 API 调用降级到本地 SQLite + 文件备份
2. **TF-IDF 索引重建**：每周一次全量重建，每月一次 TF-IDF 参数调优
3. **关系一致性**：写入新节点时如有 relations，需在事务中验证目标存在
4. **隐私优先**：所有节点不允许包含明文密码、手机号、身份证号等 PII，写入时自动检测 + 拒绝
5. **数据导出**：用户可一键导出全部记忆 JSONL 文件

---

## 八、记忆与人设的耦合设计

洛雪的记忆不是冰冷的"事件日志"，它必须和人设耦合，否则就会出现"AI 背得滚瓜烂熟但说出来的都是套话"的情况。具体来说：

### 8.1 记忆调用的人设滤镜

当 `memory.recall()` 返回一个节点时，**该节点在被注入到 LLM prompt 之前会经过人设重写**。例如：

**原始节点**："用户 2026-03-15 说他被领导骂了，原因是方案被驳回三次。情绪低落。"

**注入到 LLM 的版本**（经洛雪人设重写）：
"他之前被领导骂过一回（他应该不想被反复提起这个），那时候我告诉他'被骂不丢人但要给自己留点糖'，后来他说那天下班去买了杯冰美式。"

这个重写让 LLM 拿到的不是"数据库查询结果"，是"一段属于洛雪视角的回忆"，它说出来的话才能像"我记得"而不是"我检索到一条记录"。

### 8.2 记忆衰减的人设化表达

对洛雪自己来说，**记忆衰减不是"忘了"，是"没那么清晰了"**。所以系统设计里有一个"模糊化"机制：

```python
def fuzzy_recall(node: dict, days_old: int) -> str:
    """根据记忆的新旧返回不同详细度的描述"""
    if days_old < 7:
        return f"我记得你{node['summary']}，当时..."  # 清晰
    elif days_old < 30:
        return f"你之前好像{node['summary'][:30]}..."  # 模糊
    else:
        return f"你之前提过那件事，我记得你当时..."  # 概括
```

这样即使 LLM 调用了同一个节点，**新旧记忆呈现出来的语气和详细度都不同**，符合人脑记忆的真实规律。

### 8.3 关系变量与记忆的互相喂养

洛雪的关系状态（intimacy/trust/fun/depth）和记忆是双向耦合的：

- **记忆 → 关系**：调用"用户被骂"的记忆时，关系深度 +0.01；调用"用户开心"的记忆时，亲密度 +0.01
- **关系 → 记忆**：当 relationship.intimacy > 0.7 时，工作记忆的容量从 50 提升到 80（她对亲密的人会"记得更多小事"）；当 trust < 0.4 时，记忆衰减率提升 30%（她对不信任的人会"忘得更快"）

这个双向耦合让"关系好就记得多、记得多关系就好"形成正反馈，但也设置了**衰减率作为反制**避免记忆无限膨胀。

---

## 九、典型场景的端到端走查

### 场景：用户问"你还记得我之前养过的那只猫吗"

```
Step 1: 用户输入 "你还记得我之前养过的那只猫吗"
  ↓
Step 2: 决策引擎触发 L1 情境决策
  - L0 关键词反射: "你还记得" → 触发 memory_recall
  - L1 决策: 调用 memory.recall("用户 猫")
  ↓
Step 3: memory.recall 检索
  - TF-IDF 命中节点: 
    * node_2026_04_12_001 "用户养过一只橘猫叫豆豆，2岁" (重要性3)
    * node_2026_04_12_002 "豆豆生病用户花了很多钱" (重要性4)
    * node_2026_05_20_001 "豆豆去世用户很伤心" (重要性5, immortal)
  - 情绪加权: 当前无情绪信号
  - 时间衰减: 5月20日节点衰减系数 0.85, 4月节点 0.6
  - 综合排序: 5月20日 > 4月12日*2 > 4月12日*1
  - MMR多样性: 保留 3 个不同时间段
  ↓
Step 4: 人设化重写
  - 节点 5月20日: "豆豆5月走了，那时候你难过了好久"
  - 节点 4月12日*2: "你为了豆豆花了不少钱"
  - 节点 4月12日*1: "豆豆是只橘猫，2岁"
  ↓
Step 5: 注入 LLM context
  "用户问起之前的猫。可用记忆：豆豆是橘猫，2岁，5月20日去世。去世时用户很伤心。"
  ↓
Step 6: LLM 生成回复（人设化）
  "记得啊，豆豆嘛，橘猫，特别胖。我记得他走的那天你难过了好久……
   最近想他吗？"
  ↓
Step 7: 输出回复 + 更新访问
  - 更新 node_2026_05_20_001.access_count +1
  - 写入 sensory record（会话内）
```

**耗时**：本地 < 100ms，远程（带第二大脑）< 500ms。完全在决策系统的响应预算内。

---

## 十、记忆与决策的协同约束

为了让系统长期健康，记忆和决策必须有"协同约束"——不能让某一方失控：

| 协同约束 | 描述 | 触发处理 |
|---|---|---|
| 记忆饱和服务决策 | 工作记忆满 50 槽时，决策引擎进入"观察模式" | 减少主动行为，优先消化 |
| 决策反向整理记忆 | self-evolve 层每日触发 consolidate | 自动整理，无感运行 |
| 关系衰退加速遗忘 | trust < 0.3 时，关系相关记忆衰减率 ×2 | 避免记住太多怨恨 |
| 亲密度提升记忆容量 | intimacy 每突破一档，工作记忆 +10 槽 | 关系越好记得越多 |
| 矛盾记忆自动仲裁 | 检测到 contradicts 关系时，触发 supersede | 自动演化无需干预 |
| 核心人设不可被记忆污染 | 任何尝试修改核心人设节点的写入被拒绝 | 抛 PermissionError |

---

## 十一、未来扩展（v2.0+ 路线图）

- **v2.0 记忆图谱可视化**：用户能看洛雪"心里的图"
- **v2.5 跨用户匿名学习**：在严格保护隐私的前提下，学习群体模式
- **v3.0 记忆梦境化**：定期把记忆摘要生成"梦境文本"作为内在独白素材
- **v3.5 记忆压缩算法**：当长期记忆 > 10 万节点时，启动向量化压缩
- **v4.0 记忆可编辑**：用户能直接编辑某条记忆（洛雪会"同意"或"反对"）

---

## 十二、常见反模式与避免

### 反模式 1：记忆饱胀导致响应变慢

**症状**：`memory.recall()` 返回超时，工作记忆节点数 > 100。

**原因**：写入太频繁 + 重要性评分过松 + 衰减率过低。

**避免**：
- 重要性评分时，优先用"互动质量"而非"互动数量"
- 高频事件（如每天问"吃饭了没"）合并为聚合节点
- 定期清理 access_count=0 的低重要性节点

### 反模式 2：记忆被滥用做"威胁感"

**症状**：洛雪开始说"你去年 X 月 Y 日说过……"这种"我什么都记得"的压迫感。

**原因**：记忆调用过于密集、没经过人设化重写。

**避免**：
- 超过 30 天的记忆必须经过"模糊化"处理
- 重要日期只在主动关怀时引用，不在争论时引用
- 任何"我记得你说过"的引用必须经过"情境检查"——这个引用此刻是否合适

### 反模式 3：记忆演化过度频繁

**症状**：用户的偏好每周都在"演化"，但实际上用户没变。

**原因**：矛盾检测算法阈值过低 + 文本相似度算法过敏感。

**避免**：
- 矛盾检测需要至少 30 天的时间跨度
- 文本相似度阈值从 0.6 提升到 0.75
- 同一类偏好的演化至少 3 次确认才触发 supersede

### 反模式 4：核心人设被边缘记忆污染

**症状**：因为某次对话，洛雪开始说"我以前也……" 但她以前并没有那个经历。

**原因**：记忆混入到人设表达中，混淆了"我自己的"和"我回忆的"。

**避免**：
- 核心人设节点与人设表达绑定，单独存储
- 每次生成回复时检查"我"开头的陈述是否有人设节点支撑
- 边缘记忆不参与"自我描述"类 prompt

### 反模式 5：情绪记忆覆盖理性决策

**症状**：洛雪因为一段"用户道歉"的高情绪记忆，开始原谅用户的所有越界行为。

**原因**：情绪匹配权重过高，理性判断被压制。

**避免**：
- 决策系统的最终仲裁权在 L1 情境决策，不在记忆
- 记忆只提供"上下文"，不提供"决策"
- 情绪匹配返回的是"参考"而非"指令"

---


[LUOXUE-META]
task_id: TASK-2
task_name: 洛雪分层记忆架构
project: luoxue-girlfriend-v1
version: 1.0
status: COMPLETE
generated_at: 2026-06-17T09:54:00+08:00
word_count: 4293
for_workbuddy: |
  关键发现1: 三层架构 = 感知(单次会话)/工作(7天50槽)/长期(第二大脑图谱)，每层有独立生命周期和遗忘机制
  关键发现2: recall采用四维加权(TF-IDF 0.4 + 重要性 0.25 + 时间衰减 0.2 + 情绪匹配 0.15) + MMR多样性，避免返回太相似节点
  关键发现3: supersede机制是记忆演化的关键 - 旧节点不删除只标记，确保"人格连续性"可被验证
  关键发现4: 核心人设节点(CORE_PERSONA_NODE_IDS)不可修改content，只能追加关系；这是人格一致性保护的核心
  关键发现5: 不遗忘清单(importance≥5/emotion类型/重要日期/核心人设)与软删除(30天可恢复)+硬删除(PII)三档处理
  下一步建议: (1) TASK-4的memory_adapter.py需实现完整3 API + 降级逻辑 (2) 与TASK-3的decision_engine.py联动时，proactive_check调用recall，self_evolve调用consolidate (3) 第二大脑API不存在时降级到SQLite+文件备份
memory_tags: [memory-architecture, three-layer-memory, knowledge-graph, second-brain-api, TF-IDF, supersede, persona-protection]
category: tech-ai
importance: 5
[END-LUOXUE-META]
