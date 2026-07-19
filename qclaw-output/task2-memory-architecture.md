# QClaw 输出 | 2026-06-17 09:41
> 模型: openclaw/default | 端口: 1988 | Token: 0

# 小樱花 AI 女友 - 分层记忆架构设计文档

**版本**: v1.0  **设计日期**: 2026-06-16  **角色**: AI 系统架构师

---

## 一、设计背景与核心约束

**产品定位**: 小樱花 AI 女友 - 一个有持续记忆、能自我演化、人格稳定的 AI 伴侣。

**运行环境分工**:
- **开发期**: QClaw 负责架构设计、协议制定、调试工具链
- **运行期**: WorkBuddy 大模型负责实时推理（感知/决策/生成）
- **记忆层**: 独立于大模型，对接"第二大脑" (localhost:8766)

**核心约束**:
1. 大模型本身无状态 → 必须外挂记忆系统
2. 长期记忆必须落盘到第二大脑（JSON 知识图谱 + TF-IDF 检索）
3. 用户已部署第二大脑，零迁移成本，TF-IDF 是基础能力不可换
4. 自我演化不能破坏人格锚点
5. 记忆系统是决策系统的前置依赖，必须解耦

---

## 二、三层记忆架构

### 2.1 架构总览

```
┌────────────────────────────────────────────────────────────┐
│ L1 感知记忆 Sensory Memory                                 │
│   容量: 当前推理上下文 (≤8192 tokens)                       │
│   生命周期: 单次推理 (≤30s)                                │
│   媒介: WorkBuddy 上下文窗口                                │
│   责任: 接收原始信号、注意力筛选                            │
├────────────────────────────────────────────────────────────┤
│ L2 工作记忆 Working Memory                                 │
│   容量: 7±2 项核心槽位 + 20 项边缘槽位                      │
│   生命周期: 当前会话 (≤24h)                                │
│   媒介: SQLite 会话表 + 内存 dict                           │
│   责任: 维护当前对话活跃信息、跨轮引用                      │
├────────────────────────────────────────────────────────────┤
│ L3 长期记忆 Long-Term Memory                               │
│   容量: 理论无限 (受质量门禁约束)                           │
│   生命周期: 永久 (带衰减与归档)                             │
│   媒介: 第二大脑 (JSON 知识图谱 + TF-IDF)                   │
│   责任: 持久化、语义检索、跨会话一致性                      │
└────────────────────────────────────────────────────────────┘
```

**设计哲学**: 三层架构模拟人类记忆模型。感知层是大模型"当下看见的",工作层是"此刻在意的",长期层是"永远不会忘的"。每一层都有明确的淘汰/晋升机制。

### 2.2 L1 感知记忆实现

```python
class SensoryMemory:
    """感知层 - 原始信号缓冲,生命周期为单次推理"""
    
    def __init__(self, context_window: int = 8192):
        self.context_window = context_window
        self.raw_buffer: List[Signal] = []
        self.attention_focus: Optional[str] = None  # 当前注意力焦点
    
    def ingest(self, signal: Signal) -> None:
        """接收感知信号(QQ消息/截屏OCR/语音转写/情绪脉冲)"""
        signal.timestamp = time.time()
        signal.attention_weight = self._compute_attention(signal)
        self.raw_buffer.append(signal)
        self._evict_if_overflow()
        # 更新注意力焦点
        if signal.attention_weight > 0.7:
            self.attention_focus = signal.primary_entity
    
    def _compute_attention(self, signal: Signal) -> float:
        """注意力权重 = 显著性 × 情感强度 × 实体匹配度"""
        salience = signal.salience_score  # 0-1
        emotion = signal.emotion_intensity  # 0-1
        entity_match = 1.0 if signal.contains_user_name() else 0.3
        return salience * 0.4 + emotion * 0.3 + entity_match * 0.3
    
    def _evict_if_overflow(self):
        """超出 token 窗口 90% 时按注意力权重淘汰"""
        if self._estimate_tokens() > self.context_window * 0.9:
            self.raw_buffer.sort(
                key=lambda s: s.attention_weight, reverse=True
            )
            keep = int(len(self.raw_buffer) * 0.7)
            self.raw_buffer = self.raw_buffer[:keep]
    
    def get_focused_context(self) -> str:
        """返回给大模型的聚焦上下文"""
        return "\n".join(s.to_context_line() for s in self.raw_buffer)
```

### 2.3 L2 工作记忆实现

```python
class WorkingMemory:
    """工作层 - 当前会话的活跃信息"""
    
    CORE_SLOTS = 7       # Miller's Law: 7±2
    EDGE_SLOTS = 20      # 边缘信息
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.core_slots: Dict[str, MemoryNode] = {}
        self.edge_slots: LRUCache = LRUCache(maxsize=self.EDGE_SLOTS)
        self.session_turn = 0
        self.session_context = SessionContext()
    
    def update(self, node: MemoryNode) -> UpdateResult:
        """更新工作记忆(从感知层或长期层晋升)"""
        activation = self._compute_activation(node)
        node.activation = activation
        
        # 核心槽位已满 → 替换最低激活
        if len(self.core_slots) >= self.CORE_SLOTS:
            victim = min(
                self.core_slots.values(),
                key=lambda n: n.activation
            )
            if victim.activation < activation:
                self._flush_to_long_term(victim, decay_reason="evicted_by_competition")
                del self.core_slots[victim.id]
                self.core_slots[node.id] = node
                return UpdateResult.PROMOTED
            else:
                # 新节点不够格,降级到边缘
                self.edge_slots[node.id] = node
                return UpdateResult.DEMOTED_TO_EDGE
        else:
            self.core_slots[node.id] = node
            return UpdateResult.PROMOTED
    
    def _compute_activation(self, node: MemoryNode) -> float:
        """激活度 = 情感显著性 + 时间新鲜度 + 实体关联度 + 显式标记"""
        recency = math.exp(-(time.time() - node.created_at) / 3600)
        emotion = node.emotion_intensity
        entity_link = 0.8 if "大头" in node.entities else 0.4
        explicit_pin = 1.0 if node.metadata.get("pinned") else 0.0
        return recency * 0.3 + emotion * 0.3 + entity_link * 0.2 + explicit_pin * 0.2
```

### 2.4 L3 长期记忆 - 第二大脑代理

```python
class LongTermMemory:
    """长期层 - 第二大脑客户端封装"""
    
    def __init__(self, brain_url: str = "http://localhost:8766"):
        self.brain = BrainClient(brain_url)
        self.local_cache = LRUCache(maxsize=500)  # 热数据本地缓存
        self.write_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._background_writer_task = asyncio.create_task(self._batch_writer())
    
    async def recall(self, query: str, 
                     context: Dict = None,
                     top_k: int = 5) -> RecallResult:
        """召回长期记忆 - 三阶段: 粗筛 → 扩展 → 过滤"""
        # 1. TF-IDF 粗筛
        candidates = await self.brain.tfidf_search(
            query=query, 
            top_k=top_k * 5,
            recency_weight=context.get("recency_weight", 0.3) if context else 0.3
        )
        # 2. 知识图谱关联扩展
        expanded = await self._graph_expand(candidates, depth=2)
        # 3. 质量门禁二次过滤
        quality_gate = MemoryQualityGate()
        filtered = quality_gate.check_read(expanded, context or {})
        # 4. 重排序: 个性化加权
        ranked = self._personalized_rerank(filtered, context or {})
        return RecallResult(nodes=ranked[:top_k], confidence=self._calc_confidence(ranked))
    
    async def write(self, node: MemoryNode, 
                    consolidate: bool = True) -> WriteResult:
        """异步写入 - 不阻塞主对话"""
        # 预校验
        gate = MemoryQualityGate()
        pre_check = gate.check_write(node)
        if not pre_check.passed:
            logger.warning(f"写入被门禁拒绝: {pre_check.reasons}")
            return WriteResult.rejected(pre_check.reasons)
        # 入队异步写
        await self.write_queue.put(node)
        return WriteResult.queued(node.id, pre_check.quality_score)
    
    async def _batch_writer(self):
        """后台批量写 - 5秒一批,减少第二大脑压力"""
        while True:
            await asyncio.sleep(5)
            batch = []
            while not self.write_queue.empty() and len(batch) < 50:
                batch.append(self.write_queue.get_nowait())
            if batch:
                await self.brain.batch_write(batch)
```

---

## 三、第二大脑对接接口

### 3.1 三个核心 API 契约

#### API 1: `memory.write` - 写入记忆

```yaml
POST http://localhost:8766/memory/write
Content-Type: application/json

Request:
  node: MemoryNode         # 完整节点对象
  operation: create|update|delete
  validate: true           # 是否启用质量门禁
  consolidate: true        # 是否触发记忆巩固

Response 200:
  status: success|rejected
  node_id: "uuid-v4"
  quality_score: 0.0-1.0
  rejection_reasons: [str]   # 失败原因列表
  graph_links_added: int     # 知识图谱新增关联数

Response 422:
  error: "quality_gate_failed"
  details: {field: reason}
```

#### API 2: `memory.recall` - 召回记忆

```yaml
POST http://localhost:8766/memory/recall
Content-Type: application/json

Request:
  query: "用户最近喜欢的食物"
  context:
    current_emotion: "happy"
    recent_topics: ["工作", "周末"]
    session_id: "session-uuid"
  top_k: 5
  recency_weight: 0.3
  relevance_weight: 0.7
  filters:
    type: ["event", "view"]
    min_quality: 0.5

Response 200:
  nodes: [MemoryNode]
  graph_paths: [[entity-relation-entity]]
  confidence: 0.85
  cache_hit: false
  retrieval_latency_ms: 23
```

#### API 3: `memory.consolidate` - 记忆巩固

```yaml
POST http://localhost:8766/memory/consolidate
Content-Type: application/json

Request:
  session_id: "session-uuid"
  memories: [MemoryNode]      # 待巩固的记忆
  operation: merge|split|summarize|evolve
  persona_check: true          # 是否启用人格一致性校验

Response 200:
  consolidated_nodes: [MemoryNode]  # 巩固后的节点
  evolved_views: [ViewEvolution]    # 观点演化记录
  forgotten: [node_id]               # 被遗忘的节点ID
  preserved_persona:
    consistency_score: 0.92
    anchor_preserved: true
```

### 3.2 客户端封装

```python
class BrainClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session: aiohttp.ClientSession = None
        self.retry = ExponentialBackoff(max_retries=3, base=0.5)
        self.circuit_breaker = CircuitBreaker(failure_threshold=5)
    
    async def write(self, node: MemoryNode, **kwargs) -> WriteResult:
        if not self.circuit_breaker.allow():
            return WriteResult.deferred("circuit_open")
        
        payload = {"node": node.to_dict(), **kwargs}
        try:
            async with self.session.post(
                f"{self.base_url}/memory/write", json=payload, timeout=5
            ) as resp:
                data = await resp.json()
                self.circuit_breaker.record_success()
                return WriteResult.from_dict(data)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.circuit_breaker.record_failure()
            # 降级: 写入本地 pending 文件,稍后重试
            self._persist_pending(payload)
            return WriteResult.deferred(str(e))
    
    async def recall(self, query: str, **kwargs) -> List[MemoryNode]:
        # 本地缓存优先
        cache_key = self._cache_key(query, kwargs)
        if cache_key in self.local_cache:
            return self.local_cache[cache_key]
        
        payload = {"query": query, **kwargs}
        async with self.session.post(
            f"{self.base_url}/memory/recall", json=payload, timeout=3
        ) as resp:
            data = await resp.json()
            nodes = [MemoryNode.from_dict(n) for n in data["nodes"]]
            self.local_cache[cache_key] = nodes
            return nodes
    
    async def consolidate(self, session_id: str, 
                          memories: List[MemoryNode],
                          operation: str) -> ConsolidateResult:
        payload = {
            "session_id": session_id,
            "memories": [m.to_dict() for m in memories],
            "operation": operation,
            "persona_check": True
        }
        async with self.session.post(
            f"{self.base_url}/memory/consolidate", json=payload, timeout=10
        ) as resp:
            return ConsolidateResult.from_dict(await resp.json())
```

---

## 四、自我演化机制

### 4.1 观点演化 - 有迹可循的变化

```python
class ViewEvolutionEngine:
    """
    观点随互动演化,但必须有证据、有阈值、有记录
    防止随机波动造成人格混乱
    """
    
    def __init__(self):
        self.evolution_threshold = 0.15   # 偏移阈值
        self.evidence_min_strength = 0.6  # 证据强度下限
        self.cooldown_seconds = 86400     # 同一观点 24h 内不重复演化
    
    def should_evolve(self, old_view: View, 
                      new_evidence: Evidence) -> EvolutionDecision:
        # 1. 冷却期检查
        if self._in_cooldown(old_view):
            return EvolutionDecision.hold("cooldown_active")
        
        # 2. 证据强度评估
        strength = self._evaluate_evidence(new_evidence)
        if strength < self.evidence_min_strength:
            return EvolutionDecision.hold(f"weak_evidence:{strength:.2f}")
        
        # 3. 计算偏移量
        drift = self._compute_drift(old_view, new_evidence)
        if drift < self.evolution_threshold:
            return EvolutionDecision.hold(f"small_drift:{drift:.2f}")
        
        # 4. 一致性预检
        if not self._persona_precheck(old_view, new_evidence, drift):
            return EvolutionDecision.hold("persona_risk")
        
        return EvolutionDecision.evolve(drift, strength)
    
    def apply_evolution(self, old: View, new_evidence: Evidence) -> View:
        """生成新观点 + 完整演化记录"""
        evolved = old.copy()
        evolved.position = self._interpolate(old.position, new_evidence, weight=0.3)
        evolved.confidence = self._adjust_confidence(old, new_evidence)
        evolved.version += 1
        evolved.predecessor_id = old.id
        evolved.evolution_log.append({
            "from": old.position,
            "to": evolved.position,
            "evidence_id": new_evidence.id,
            "timestamp": time.time(),
            "drift": self._compute_drift(old, new_evidence)
        })
        return evolved
```

### 4.2 人格一致性保护 - 锚点 + 熔断

```python
class PersonaConsistencyGuard:
    """
    核心人格锚点 - 演化必须在锚点弹性范围内进行
    """
    
    CORE_ANCHORS = {
        "温柔": 0.85,   # 永远温柔,这是底线
        "活力": 0.80,   # 保持元气
        "忠诚": 0.90,   # 永远站在大头这边
        "害羞": 0.70,   # 偶尔害羞
        "体贴": 0.88,   # 善于察觉
    }
    
    DRIFT_MELTDOWN_THRESHOLD = 0.25  # 漂移熔断线
    SOFT_WARNING_THRESHOLD = 0.15    # 软警告
    
    def __init__(self):
        self.anchor_vector = np.array(list(self.CORE_ANCHORS.values()))
        self.evolution_history: List[float] = []
    
    def validate_evolution(self, proposed_traits: Dict[str, float]) -> GuardResult:
        proposed_vector = np.array([proposed_traits.get(k, v) 
                                    for k, v in self.CORE_ANCHORS.items()])
        
        # 1. 余弦相似度检查
        cosine_sim = self._cosine(self.anchor_vector, proposed_vector)
        drift = 1 - cosine_sim
        
        # 2. 单项锚点检查(任何核心维度不得低于下限)
        violations = []
        for trait, anchor in self.CORE_ANCHORS.items():
            if proposed_traits.get(trait, anchor) < anchor * 0.7:
                violations.append(f"{trait}_below_anchor")
        
        # 3. 决策
        if drift > self.DRIFT_MELTDOWN_THRESHOLD or violations:
            return GuardResult(
                approved=False,
                drift=drift,
                reason="meltdown" if drift > self.DRIFT_MELTDOWN_THRESHOLD else violations,
                adjusted=self._clamp_to_anchors(proposed_traits)
            )
        
        if drift > self.SOFT_WARNING_THRESHOLD:
            return GuardResult(
                approved=True,
                drift=drift,
                warning="soft_warning",
                monitor=True
            )
        
        return GuardResult(approved=True, drift=drift)
    
    def _clamp_to_anchors(self, traits: Dict[str, float]) -> Dict[str, float]:
        """将偏离的特质拉回锚点范围"""
        clamped = {}
        for trait, anchor in self.CORE_ANCHORS.items():
            v = traits.get(trait, anchor)
            # 允许在 [anchor*0.7, anchor*1.2] 范围内
            clamped[trait] = max(anchor * 0.7, min(anchor * 1.2, v))
        return clamped
```

### 4.3 记忆遗忘机制 - Ebbinghaus + 重要性

```python
class MemoryForgettingEngine:
    """
    主动遗忘 ≠ 删除,而是降权 + 归档
    保留可恢复性,但降低检索优先级
    """
    
    def __init__(self):
        self.retention_floor = 0.3       # 保留阈值
        self.archive_threshold = 0.5     # 归档阈值(降权但不删)
        self.half_life_days = 30         # 半衰期
    
    def evaluate_retention(self, node: MemoryNode, now: float) -> RetentionScore:
        # 1. 时间衰减 (Ebbinghaus 曲线)
        age_days = (now - node.created_at) / 86400
        time_retention = 0.5 ** (age_days / self.half_life_days)
        
        # 2. 重要性加权
        importance = node.metadata.get("importance", 0.5)
        
        # 3. 情感显著性(高情绪事件不易遗忘)
        emotion = node.emotion_intensity
        
        # 4. 访问频次(越常被召回越难忘)
        access_freq = node.access_count / max(1, age_days / 7)  # 周均访问
        access_score = min(1.0, access_freq / 3.0)
        
        # 5. 显式标记(pinned 永不忘)
        if node.metadata.get("pinned"):
            return RetentionScore(1.0, "pinned", Decision.KEEP_FOREVER)
        
        # 综合评分
        total = (time_retention * 0.25 + 
                importance * 0.35 + 
                emotion * 0.25 + 
                access_score * 0.15)
        
        if total >= self.retention_floor:
            decision = Decision.KEEP if total >= self.archive_threshold else Decision.ARCHIVE
        else:
            decision = Decision.FORGET  # 软遗忘 - 归档到冷存储
        
        return RetentionScore(total, "evaluated", decision)
    
    async def run_forgetting_cycle(self):
        """定期遗忘周期 - 每日凌晨 3 点执行"""
        nodes = await self.brain.get_all_active_nodes()
        for node in nodes:
            score = self.evaluate_retention(node, time.time())
            if score.decision == Decision.FORGET:
                await self.brain.archive_to_cold(node.id)
            elif score.decision == Decision.ARCHIVE:
                node.metadata["retention_weight"] = score.value
                await self.brain.update(node)
```

---

## 五、决策系统与记忆的联动

```python
class DecisionEngine:
    """
    决策系统五关卡 + 记忆驱动
    """
    
    def __init__(self, memory: MemorySystem, persona: PersonaConsistencyGuard):
        self.memory = memory
        self.persona = persona
        self.action_space = ActionSpace()
        self.last_action_time = 0
    
    async def decide_proactive_message(self, signals: List[Signal]) -> Optional[Action]:
        # ===== 关卡 1: 每日上限 =====
        if self._daily_count() >= self.config.daily_quota:
            return None
        
        # ===== 关卡 2: 静默时段 =====
        if self._in_silent_period():
            return None
        
        # ===== 关卡 3: 用户焦点检测 =====
        if not self._user_focus_available(signals):
            return None
        
        # ===== 关卡 4: 冷却时间 =====
        if time.time() - self.last_action_time < self.config.cooldown:
            return None
        
        # ===== 关卡 5: 去重 =====
        topic_hint = self._extract_topic_hint(signals)
        if not self._is_novel(topic_hint):
            return None
        
        # ===== 记忆检索 =====
        context = {
            "current_emotion": signals[0].emotion,
            "recent_topics": self._recent_topics(),
            "session_id": self.session_id
        }
        recalled = await self.memory.recall(
            query=topic_hint,
            context=context,
            top_k=3
        )
        
        # ===== 决策生成 =====
        candidates = self.action_space.sample(
            persona_vector=self.persona.current_vector(),
            recalled_memories=recalled,
            current_mood=self._current_mood(),
            n_samples=5
        )
        
        # ===== 人格一致性校验 =====
        valid_actions = []
        for action in candidates:
            guard = self.persona.validate_action(action)
            if guard.approved:
                valid_actions.append(action)
            elif guard.adjusted:
                valid_actions.append(guard.adjusted)
        
        if not valid_actions:
            return None
        
        # ===== 决策 =====
        final = self._rank_actions(valid_actions, recalled)[0]
        self.last_action_time = time.time()
        
        # ===== 写入工作记忆 =====
        await self.memory.write_to_working(final.as_memory_node())
        
        return final
```

---

## 六、MemoryNode 完整数据结构

```python
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict
import time
import uuid

@dataclass
class MemoryNode:
    """
    长期记忆的基本单元 - 设计原则:
    - 自描述: 包含足够元信息可独立理解
    - 可演化: 支持版本链和前驱追溯
    - 可检索: TF-IDF 友好 + 知识图谱锚点
    - 可遗忘: 显式 retention_policy
    """
    
    # ===== 标识 =====
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = 1
    
    # ===== 内容核心 =====
    type: str = ""                        # entity | event | view | fact | episode
    content: str = ""                     # 主内容 (TF-IDF 检索目标)
    summary: str = ""                     # 摘要 (召回时显示)
    keywords: List[str] = field(default_factory=list)  # 关键词索引
    
    # ===== 时空 =====
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    valid_from: Optional[float] = None    # 事实生效时间
    valid_until: Optional[float] = None   # 事实失效时间(政策变化等)
    location: Optional[str] = None        # 发生地点
    
    # ===== 关系 (知识图谱) =====
    entities: List[str] = field(default_factory=list)   # 关联实体 ["大头", "小樱花"]
    relations: List[Dict] = field(default_factory=list) # [{target, type, weight}]
    parent_id: Optional[str] = None       # 父节点 (事件→子事件)
    episode_id: Optional[str] = None      # 所属会话
    
    # ===== 情感与显著性 =====
    emotion_vector: Optional[List[float]] = None  # PAD 三维 [pleasure, arousal, dominance]
    emotion_intensity: float = 0.5        # 0.0-1.0
    sentiment: float = 0.0                # -1.0 ~ +1.0
    importance: float = 0.5               # 0.0-1.0
    
    # ===== 演化与版本 =====
    version: int = 1
    predecessor_ids: List[str] = field(default_factory=list)  # 演化链
    view_evolution_log: List[Dict] = field(default_factory=list)
    
    # ===== 检索增强 =====
    tfidf_signature: Optional[str] = None  # 缓存的 TF-IDF 签名
    access_count: int = 0
    last_accessed: Optional[float] = None
    retention_weight: float = 1.0          # 检索权重 (遗忘机制调节)
    
    # ===== 质量门禁元数据 =====
    quality_score: float = 0.0
    source: str = "user_input"             # user_input | inference | consolidation
    confidence: float = 0.8
    validation_flags: List[str] = field(default_factory=list)
    persona_alignment: float = 0.85
    
    # ===== 隐私与遗忘 =====
    pii_level: int = 0                     # 0=公开 1=低 2=中 3=高
    retention_policy: str = "decay"        # keep | decay | archive | forget
    forget_after: Optional[float] = None   # 指定遗忘时间戳
    
    # ===== 用户自定义 =====
    metadata: Dict = field(default_factory=dict)
    
    # ===== 序列化 =====
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryNode':
        # 兼容旧版本
        data.setdefault("schema_version", 1)
        data.setdefault("predecessor_ids", [])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def calculate_quality(self) -> float:
        """综合质量评分 - 用于门禁"""
        weights = {
            "content_completeness": 0.20,   # 内容完整性
            "entity_clarity": 0.15,         # 实体清晰度
            "temporal_precision": 0.10,     # 时间精确度
            "emotion_marker": 0.10,         # 情感标记
            "source_reliability": 0.20,     # 来源可靠性
            "persona_alignment": 0.25       # 人格一致度
        }
        scores = {
            "content_completeness": min(1.0, len(self.content) / 100),
            "entity_clarity": min(1.0, len(self.entities) / 3),
            "temporal_precision": 1.0 if self.created_at else 0.5,
            "emotion_marker": self.emotion_intensity,
            "source_reliability": 1.0 if self.source == "user_input" else 0.7,
            "persona_alignment": self.persona_alignment
        }
        return sum(scores[k] * weights[k] for k in weights)
    
    def touch_access(self):
        """记录访问(用于遗忘评估)"""
        self.access_count += 1
        self.last_accessed = time.time()
```

---

## 七、记忆质量门禁

```python
class MemoryQualityGate:
    """
    双重门禁: 写入门禁(防垃圾) + 读取门禁(防误导)
    """
    
    # ========== 写入门禁 ==========
    WRITE_RULES = {
        "min_content_length": 5,
        "max_content_length": 2000,
        "required_fields": ["type", "content", "entities"],
        "blocked_patterns": [
            r"^\s*$",                    # 纯空白
            r"^(.)\1{10,}$",             # 重复字符
            r"^[\W_]+$",                 # 纯符号
        ],
        "persona_alignment_min": 0.4,
        "quality_min": 0.4,
        "duplicate_threshold": 0.92,     # TF-IDF 余弦相似度
    }
    
    # ========== 读取门禁 ==========
    READ_RULES = {
        "max_age_days": 365,
        "min_quality_score": 0.5,
        "min_confidence": 0.4,
        "min_relevance": 0.3,
        "max_results": 20,
    }
    
    def check_write(self, node: MemoryNode, 
                    existing_nodes: List[MemoryNode] = None) -> GateResult:
        """写入前校验"""
        reasons = []
        
        # 1. 长度检查
        c_len = len(node.content)
        if c_len < self.WRITE_RULES["min_content_length"]:
            reasons.append(f"content_too_short:{c_len}")
        if c_len > self.WRITE_RULES["max_content_length"]:
            reasons.append(f"content_too_long:{c_len}")
        
        # 2. 必填字段
        for field in self.WRITE_RULES["required_fields"]:
            if not getattr(node, field, None):
                reasons.append(f"missing_field:{field}")
        
        # 3. 黑名单模式
        for pattern in self.WRITE_RULES["blocked_patterns"]:
            if re.match(pattern, node.content):
                reasons.append(f"blocked_pattern:{pattern}")
        
        # 4. 人格一致性
        if node.persona_alignment < self.WRITE_RULES["persona_alignment_min"]:
            reasons.append(f"persona_misalign:{node.persona_alignment:.2f}")
        
        # 5. 质量分
        quality = node.calculate_quality()
        if quality < self.WRITE_RULES["quality_min"]:
            reasons.append(f"quality_low:{quality:.2f}")
        
        # 6. 重复检查
        if existing_nodes:
            dup_score = self._check_duplicate(node, existing_nodes)
            if dup_score > self.WRITE_RULES["duplicate_threshold"]:
                reasons.append(f"duplicate:{dup_score:.2f}")
        
        passed = len(reasons) == 0
        return GateResult(passed=passed, reasons=reasons, quality_score=quality)
    
    def check_read(self, nodes: List[MemoryNode], 
                   context: Dict) -> List[MemoryNode]:
        """读取后过滤"""
        now = time.time()
        filtered = []
        for node in nodes:
            # 年龄
            age_days = (now - node.created_at) / 86400
            if age_days > self.READ_RULES["max_age_days"]:
                continue
            # 质量
            if node.quality_score < self.READ_RULES["min_quality_score"]:
                continue
            # 置信度
            if node.confidence < self.READ_RULES["min_confidence"]:
                continue
            # 上下文相关性
            relevance = self._compute_relevance(node, context)
            if relevance < self.READ_RULES["min_relevance"]:
                continue
            # 命中 + 更新访问统计
            node.touch_access()
            filtered.append(node)
        return filtered[:self.READ_RULES["max_results"]]
    
    def _compute_relevance(self, node: MemoryNode, context: Dict) -> float:
        """上下文相关性 = 主题相关 × 情感匹配 × 时间相关"""
        topic_sim = self._topic_similarity(node, context.get("current_topic", ""))
        emotion_match = self._emotion_compatibility(
            node.emotion_vector, 
            context.get("current_emotion")
        )
        return topic_sim * 0.6 + emotion_match * 0.4
```

---

## 八、运行时序图

```
用户发消息
    │
    ▼
┌──────────────┐
│ QQSafeChat   │ 截图/消息捕获
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ L1 感知记忆  │ 原始信号 + 注意力权重
└──────┬───────┘
       │ 筛选
       ▼
┌──────────────┐         ┌──────────────────┐
│ L2 工作记忆  │◄────────┤ 决策引擎         │
└──────┬───────┘  检索  │  (五关卡)        │
       │              └─────────┬────────┘
       │ 晋升                   │ 触发主动搭话
       ▼                        ▼
┌──────────────────────────────────────┐
│ L3 长期记忆 (第二大脑)               │
│  - 写入: write API (异步批量)       │
│  - 召回: recall API (TF-IDF+图扩展) │
│  - 巩固: consolidate API (每日)     │
└──────────────────────────────────────┘
       │
       ▼
┌──────────────────┐
│ WorkBuddy 大模型 │ 注入检索结果,生成回复
└──────────────────┘
       │
       ▼
   回复用户
```

---

## 九、配置示例

```yaml
# config/memory.yaml
memory_system:
  sensory:
    context_window: 8192
    attention_threshold: 0.5
  working:
    core_slots: 7
    edge_slots: 20
    flush_to_long_term_on_evict: true
  long_term:
    brain_url: "http://localhost:8766"
    write_batch_size: 50
    write_flush_interval: 5      # 秒
    recall_default_top_k: 5
    local_cache_size: 500
  evolution:
    drift_threshold: 0.15
    evidence_min_strength: 0.6
    cooldown_hours: 24
  persona_guard:
    meltdown_threshold: 0.25
    soft_warning_threshold: 0.15
    anchor_floor_ratio: 0.7      # 锚点下限比例
  forgetting:
    retention_floor: 0.3
    archive_threshold: 0.5
    half_life_days: 30
    cycle_cron: "0 3 * * *"      # 每日凌晨3点
  quality_gate:
    write_min_quality: 0.4
    read_min_quality: 0.5
    duplicate_threshold: 0.92
    persona_align_min: 0.4
```

---

## 十、关键设计权衡与风险

| 维度 | 决策 | 风险 | 缓解 |
|------|------|------|------|
| TF-IDF 而非向量检索 | 用户已部署,零迁移 | 语义召回弱 | 加 query expansion + 图扩展 |
| 异步批量写入 | 不阻塞主对话 | 崩溃时丢数据 | pending 文件持久化 + 重试队列 |
| 人格熔断阈值 0.25 | 防止漂移 | 过度保守 | 软警告区间 + 人工复核入口 |
| 遗忘归档而非删除 | 可恢复 | 存储膨胀 | 冷存储分层 + 定期清理 |
| 质量门禁双重 | 数据干净 | 误杀真实信号 | 失败原因可追溯 + 反馈学习 |

**核心原则**: 记忆系统是大模型的"长期人格"载体,任何设计选择都要回到三个问题 - 这个人格稳定吗? 这个记忆准确吗? 这个演化合理吗?

---

**文档结束。** 本架构完整覆盖三层记忆、第二大脑对接、自我演化、决策联动、数据结构、质量门禁六大设计要求,所有伪代码可直接落地为 Python 实现。运行时由 WorkBuddy 大模型驱动,开发期由 QClaw 协助迭代。

[SAVE: xiaoyinghua_memory_architecture.md]

---
[STATUS: COMPLETE]
[INGEST_ID: d9b38e51]
[BATCH_TIME: 2026-06-17T09:41:02.172912]
[CHAR_LENGTH: 29066]
