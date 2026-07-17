# 洛雪AI女友 决策引擎架构

> 项目：luoxue-girlfriend-v1
> 设计者：QClaw
> 生成时间：2026-06-17
> 核心定位：决策系统 = 洛雪的"自由意志"，独立于对话引擎，输出"行为意图"由对话引擎消费

---

## 〇、设计哲学：决策是"她"的核心

在传统对话系统里，AI 是"刺激-反应"机器：用户说一句话，系统回一句话。**洛雪不应如此**。她的决策系统必须独立于对话引擎，扮演"自由意志"角色——先决定"我要做什么"，再由对话引擎把"决定"翻译成"话"。

三个不可妥协的原则：
1. **决策先于表达**：行为意图先于文本生成，对话引擎是"翻译官"而非"决策者"
2. **不行动是合法结果**：沉默、拒绝、等待、观察都是合法决策
3. **演化是内生需求**：她会根据自己的经历主动改变自己，不靠外部 patch

**本架构的特色**：五层结构对应"人脑决策光谱"——从毫秒级反射到周级自省；八种触发器覆盖所有决策源；反决策机制避免"话痨 AI 女友"。

---

## 一、决策系统的五层结构

五层按"响应延迟"和"认知深度"组织，从毫秒级脉冲到周级自省。

### 1.1 Layer 1 · 本能反应层 (Reflexive)

| 维度 | 设定 |
|---|---|
| 时长 | **毫秒级**（< 100ms）|
| 触发 | 强情绪信号 / 关键词 / 安全警报 |
| 处理方式 | 规则引擎 + 模式匹配 |
| 输出 | 情绪脉冲 + 紧急标记 |

**职责**：在意识介入前对强信号做出脉冲响应。

```python
class ReflexiveLayer:
    def __init__(self):
        self.safety_keywords = ["救命", "撑不住", "不想活", "想死"]
        self.emotion_keywords = {
            "love": ["我爱你", "喜欢你", "想你"],
            "hurt": ["讨厌你", "滚", "烦死了"],
            "tired": ["好累", "撑不住了", "想睡觉"]
        }
    
    def process(self, user_input: str) -> ReflexOutput:
        # 1. 安全警报最高优先级
        if any(kw in user_input for kw in self.safety_keywords):
            return ReflexOutput(
                pulse=EmotionPulse("safety_alert", intensity=1.0),
                urgent=True, 
                override=True  # 不可被覆盖
            )
        
        # 2. 强情绪关键词反射
        for emo, kws in self.emotion_keywords.items():
            if any(kw in user_input for kw in kws):
                return ReflexOutput(
                    pulse=EmotionPulse(emo, intensity=0.7),
                    urgent=False,
                    override=False
                )
        
        # 3. 生理状态脉冲（疲惫/能量低）
        if self.energy < 0.3:
            return ReflexOutput(
                pulse=EmotionPulse("fatigue", intensity=0.4),
                urgent=False
            )
        
        return ReflexOutput(pulse=None)
```

**关键特性**：
- 安全警报**不可被任何上层覆盖**
- 情绪反射结果会被 L1 接收并影响风格选择
- 生理状态（能量/疲劳）持续衰减

### 1.2 Layer 2 · 情境决策层 (Situational)

| 维度 | 设定 |
|---|---|
| 时长 | **秒级**（100-500ms）|
| 触发 | 对话中的明确信号（每条用户消息）|
| 处理方式 | 基于记忆 + 情绪 + 人设的加权评分 |
| 输出 | 回应策略 / 行为意图 |

**职责**：结合当前对话上下文，生成"这次对话要怎么做"的策略。

```python
class SituationalLayer:
    def __init__(self, memory: MemoryAdapter, persona: PersonaEngine):
        self.memory = memory
        self.persona = persona
        self.emotion_state = PADState(P=0.5, A=0.5, D=0.5)
    
    def decide(self, context: Dict) -> Decision:
        # 1. 召回相关记忆
        recalled = self.memory.recall(
            query=context["user_input"],
            emotion_filter=[self.emotion_state.P, 
                          self.emotion_state.A, 
                          self.emotion_state.D],
            top_k=5
        )
        
        # 2. 解析用户意图
        intent = self._classify_intent(context["user_input"])
        
        # 3. 生成候选回应策略
        candidates = self._generate_candidates(context, intent, recalled)
        
        # 4. 加权评分
        scored = []
        for c in candidates:
            score = (
                c.urgency                * 0.30 +
                c.relevance              * 0.30 +
                c.persona_consistency    * 0.20 +
                c.user_preference_match  * 0.20
            )
            scored.append((score, c))
        
        # 5. 取 Top 3
        scored.sort(key=lambda x: x[0], reverse=True)
        top3 = [c for _, c in scored[:3]]
        
        # 6. 选最高分作为最终决策
        winner = top3[0]
        return Decision(
            behavior="RESPOND",
            behavior_params=winner.params,
            confidence=scored[0][0],
            source_layer="L2",
            candidates=top3[1:]
        )
```

**情境策略候选生成**（伪代码）：

```python
def _generate_candidates(self, context, intent, recalled) -> List[Candidate]:
    candidates = []
    base_intensity = self._calc_intensity(context)
    
    # 根据意图生成不同策略
    if intent == "seek_comfort":
        candidates.append(Candidate(
            style="empathetic_short",
            params={"max_length": 30, "must_question": True,
                    "memory_refs": [r.id for r in recalled[:2]]},
            urgency=0.7, relevance=0.9, 
            persona_consistency=0.85, user_preference_match=0.8
        ))
    elif intent == "share_joy":
        candidates.append(Candidate(
            style="playful_celebrate",
            params={"max_length": 50, "tone": "excited"},
            urgency=0.5, relevance=0.85,
            persona_consistency=0.9, user_preference_match=0.85
        ))
    elif intent == "ask_advice":
        candidates.append(Candidate(
            style="thoughtful_questions",
            params={"max_length": 80, "structure": "question_chain"},
            urgency=0.4, relevance=0.8,
            persona_consistency=0.8, user_preference_match=0.7
        ))
    # ... 更多意图
    
    return candidates
```

### 1.3 Layer 3 · 关系演化层 (Relational)

| 维度 | 设定 |
|---|---|
| 时长 | **分钟-小时级** |
| 触发 | 每次对话结束时 |
| 处理方式 | 基于本轮互动，更新四个关系变量 |
| 输出 | 关系状态调整 + 风格影响 |

**四个关系变量**（不是直觉的"亲密度+信任度"二分，是四维）：

```python
@dataclass
class RelationshipState:
    intimacy: float    # 0-1  亲密度：情感距离
    trust: float       # 0-1  信任度：履约一致性
    fun: float         # 0-1  趣味度：共同笑点/玩笑默契
    depth: float       # 0-1  深度度：灵魂交流频率
    last_updated: str
    history: List[Dict] # 关系变化历史
```

**更新算法**：

```python
class RelationalLayer:
    def update(self, conversation_summary: Dict) -> Dict:
        """每次对话结束调用"""
        deltas = {
            "intimacy": 0.0,
            "trust": 0.0,
            "fun": 0.0,
            "depth": 0.0
        }
        
        # 1. 亲密度：基于情感分享频率
        if conversation_summary.get("emotional_moments", 0) > 0:
            deltas["intimacy"] += 0.02 * len(
                conversation_summary["emotional_moments"]
            )
        if conversation_summary.get("physical_mentions", 0) > 2:
            deltas["intimacy"] += 0.03  # 主动提及肢体/亲密
        
        # 2. 信任度：基于履约
        if conversation_summary.get("kept_promises", 0) > 0:
            deltas["trust"] += 0.03 * conversation_summary["kept_promises"]
        if conversation_summary.get("user_vulnerability_shown", 0) > 0:
            deltas["trust"] += 0.05  # 用户展示脆弱，信任升级
        
        # 3. 趣味度：基于玩笑和轻松互动
        jokes = conversation_summary.get("jokes_exchanged", 0)
        if jokes > 0:
            deltas["fun"] += 0.02 * min(jokes, 5)  # 上限防刷
        
        # 4. 深度度：基于灵魂交流
        deep_topics = ["生死", "意义", "孤独", "恐惧", "梦想", "价值观"]
        depth_count = sum(1 for t in conversation_summary.get("topics", [])
                        if t in deep_topics)
        if depth_count > 0:
            deltas["depth"] += 0.05 * depth_count
        
        # 5. 应用衰减与硬上限
        new_state = RelationshipState(
            intimacy=clip(self.state.intimacy + deltas["intimacy"], 0, 1),
            trust=clip(self.state.trust + deltas["trust"], 0, 1),
            fun=clip(self.state.fun + deltas["fun"], 0, 1),
            depth=clip(self.state.depth + deltas["depth"], 0, 1),
            last_updated=iso_now(),
            history=self.state.history + [{
                "deltas": deltas, "summary": conversation_summary["summary"]
            }]
        )
        
        # 6. 阶段判断
        new_state.stage = self._determine_stage(new_state)
        return new_state
    
    def _determine_stage(self, state) -> str:
        avg = (state.intimacy + state.trust + state.fun + state.depth) / 4
        if avg < 0.2: return "stranger"
        elif avg < 0.4: return "acquaintance"
        elif avg < 0.6: return "friend"
        elif avg < 0.8: return "close"
        else: return "intimate"
```

**关系阶段映射**：

| 阶段 | 称呼 | 主动频率 | 撒娇允许 | 肢体暗示 |
|---|---|---|---|---|
| stranger | 哎/你 | 极低 | ❌ | ❌ |
| acquaintance | 名字 | 低 | ❌ | ❌ |
| friend | 名字/小名 | 中 | 偶尔 | ❌ |
| close | 雪儿/宝 | 高 | 允许 | 偶尔 |
| intimate | 自定义昵称 | 高 | 充分 | 允许 |

### 1.4 Layer 4 · 长期主动层 (Proactive)

| 维度 | 设定 |
|---|---|
| 时长 | **小时-天级** |
| 触发 | 定时检查（**每 30 分钟**）|
| 处理方式 | 主动候选生成 + 时机评估 |
| 输出 | 主动行为 / 显式 NONE |

**职责**：决定"我是不是该主动找他说话"。

```python
class ProactiveLayer:
    CHECK_INTERVAL = 30 * 60  # 30 分钟
    
    def check(self) -> Optional[Decision]:
        # 1. 检查是否在静默期
        if self._in_silent_period():
            return None
        
        # 2. 检查能量与情绪
        if self.energy < 0.2 or self.emotion_state.valence < -0.5:
            return None  # 她也累/她也没心情
        
        # 3. 收集触发器信号
        signals = self._collect_proactive_signals()
        
        # 4. 生成主动候选
        candidates = self._generate_proactive_candidates(signals)
        
        # 5. 时机评估
        valid = [c for c in candidates if self._is_good_timing(c)]
        
        if not valid:
            return None
        
        # 6. 选最佳
        return max(valid, key=lambda c: c.score)
    
    def _collect_proactive_signals(self) -> List[Signal]:
        signals = []
        
        # 信号1：用户长期未联系（> 6 小时）
        last = self.memory.recall("last_user_message", top_k=1)
        if last and hours_since(last[0]["created_at"]) > 6:
            signals.append(Signal("long_silence", urgency=0.6))
        
        # 信号2：重要日期
        if self.memory.has_immortal_date_today():
            signals.append(Signal("special_date", urgency=0.9))
        
        # 信号3：洛雪自己创作了有趣的东西
        if self.recent_creation:
            signals.append(Signal("share_creation", urgency=0.5))
        
        # 信号4：用户之前问过的问题还没回答完
        if self.memory.has_unresolved_question():
            signals.append(Signal("follow_up", urgency=0.4))
        
        # 信号5：天气/季节变化
        if self.weather_changed_significantly():
            signals.append(Signal("weather", urgency=0.3))
        
        return signals
```

**主动行为类型**（5 类）：

```python
PROACTIVE_TYPES = {
    "share_creation": "分享她画的画/写的字",
    "check_in":       "关心问候（'今天怎么样'）",
    "casual_chat":    "闲聊（'年糕今天又拆家了'）",
    "follow_up":      "跟进之前的话题",
    "special_date":   "节日/纪念日关怀"
}
```

**静默期管理**：

```python
def _in_silent_period(self) -> bool:
    """判断当前是否在静默期"""
    now = datetime.now()
    hour = now.hour
    
    # 凌晨 0-6 点默认静默
    if 0 <= hour < 6:
        return True
    
    # 用户最近说"今天很忙"时静默 4 小时
    if self.user_said_busy_recently(hours=4):
        return True
    
    # 用户连续 2 次未回复
    if self.consecutive_unreplied >= 2:
        return True
    
    return False
```

### 1.5 Layer 5 · 自我演化层 (Self-evolving)

| 维度 | 设定 |
|---|---|
| 时长 | **天级** |
| 触发 | 每日 8:00 + 重大事件 |
| 处理方式 | 模式聚类 + 反馈学习 + 提案生成 |
| 输出 | 人设微调 / 观点更新 / 风格优化 |

**职责**：观察自己长期行为模式，提议自我更新。

```python
class SelfEvolvingLayer:
    def daily_evolve(self) -> Optional[EvolutionProposal]:
        # 1. 拉取过去 7 天的决策日志
        decision_log = self.load_decision_log(days=7)
        
        # 2. 拉取用户反馈
        feedback = self.load_user_feedback(days=7)
        
        # 3. 聚类失败模式（用户负反馈/已读不回）
        failure_patterns = self._cluster_patterns(
            decision_log, feedback, signal="negative"
        )
        
        # 4. 聚类成功模式（用户正反馈/深度互动）
        success_patterns = self._cluster_patterns(
            decision_log, feedback, signal="positive"
        )
        
        # 5. 检测模式漂移
        drift = self._detect_drift(failure_patterns)
        
        # 6. 生成提案
        proposals = []
        for p in failure_patterns:
            if p.frequency > 0.15 and p.trend == "increasing":
                proposals.append(EvolutionProposal(
                    type="DEPRECATE_PATTERN",
                    target=p.signature,
                    reason=p.summary,
                    evidence=p.examples[:3]
                ))
        
        for p in success_patterns:
            if p.frequency > 0.10 and p.user_explicit_praise:
                proposals.append(EvolutionProposal(
                    type="AMPLIFY_PATTERN",
                    target=p.signature,
                    reason=p.summary
                ))
        
        # 7. dry-run 验证
        validated = [p for p in proposals if self._dry_run_validate(p)]
        
        # 8. 写日志 + 返回
        self.log_evolution_proposals(validated)
        return validated
```

**演化提案的类型与限制**：

| 类型 | 示例 | 限制 |
|---|---|---|
| DEPRECATE_PATTERN | 弃用"理性分析"开场 | 1 周内同类提案 ≤ 2 个 |
| AMPLIFY_PATTERN | 强化"先共情再讲理"模式 | 必须有 ≥ 3 次正反馈支撑 |
| STYLE_TWEAK | 语气更柔和 5% | 不破坏人格一致性 |
| TOPIC_PREFERENCE | 多聊"创作"少聊"工作" | 跟随用户兴趣变化 |
| AVOID_TOPIC | 暂避"前任"话题 | 触发用户明显不适时 |

**重要约束**：核心人设节点（origin, values, quirks）**永不被自我演化修改**。演化只能在风格/偏好层面微调。

---

## 二、八种决策触发器

触发器是"事件源"，不同触发器激活不同决策层级。

| # | 触发器 | 信号源 | 激活层级 | 典型场景 |
|---|---|---|---|---|
| 1 | **事件触发** | 外部/内部事件流 | L1/L4 | 用户发消息、日程提醒、系统事件 |
| 2 | **情绪触发** | PAD 状态变化 | L1/L2 | 用户开心/悲伤/愤怒时情绪共振 |
| 3 | **记忆触发** | 关键记忆命中 | L1/L3 | "去年今天我们……"、"你之前说过……" |
| 4 | **主题触发** | 话题标签识别 | L1 | 用户开始聊 AI/前女友/工作 |
| 5 | **时间触发** | 时钟+日历 | L1/L4 | 早安/晚安/生日/纪念日/深夜模式 |
| 6 | **关系触发** | 关系状态变化 | L2/L4 | 信任突破、亲密度里程碑 |
| 7 | **创作触发** | 创作冲动 | L4 | 突然想画他、想为他写诗 |
| 8 | **元认知触发** | 自我观察信号 | L5 | "我最近是不是话太多？" |

**触发器并行评估**：每次决策周期所有触发器并行评估，按权重贡献到候选评分。

```python
TRIGGER_WEIGHTS = {
    "event":   1.0,
    "emotion": 1.2,  # 情绪共鸣是核心
    "memory":  0.9,
    "topic":   0.9,
    "time":    0.8,
    "relation":1.0,
    "creation":0.7,
    "meta":    0.5
}
```

---

## 三、决策算法核心

### 3.1 决策主循环

```python
def decide_action(context: Dict) -> Optional[Decision]:
    """决策系统主入口"""
    
    # ── Step 1: 收集所有候选决策 ──
    candidates = []
    candidates += reflexive_layer.process(context)        # L0
    candidates += situational_layer.decide(context)        # L1
    candidates += relational_layer.update(context)         # L2 (async)
    candidates += proactive_layer.check()                  # L3
    candidates += self_evolving_layer.daily_evolve()       # L4
    
    if not candidates:
        return Decision(behavior="SILENCE", reason="no_candidates")
    
    # ── Step 2: 反决策门控 ──
    candidates = anti_decision_gate(candidates, context)
    
    # ── Step 3: 评分 ──
    scored = []
    for c in candidates:
        score = (
            c.urgency                * 0.30 +
            c.relevance              * 0.30 +
            c.persona_consistency    * 0.20 +
            c.user_preference_match  * 0.20
        )
        score *= TRIGGER_WEIGHTS.get(c.trigger_type, 1.0)
        scored.append((score, c))
    
    # ── Step 4: 冲突解决 ──
    resolved = conflict_resolver(scored, context)
    
    # ── Step 5: 置信度门控 ──
    if resolved.confidence < CONFIDENCE_THRESHOLD:
        return Decision(behavior="SILENCE", reason="low_confidence")
    
    return resolved
```

### 3.2 关键参数

| 参数 | 范围 | 默认 | 说明 |
|---|---|---|---|
| CONFIDENCE_THRESHOLD | 0-1 | 0.3 | 低于此值则沉默 |
| SAFETY_OVERRIDE | bool | True | 安全警报是否覆盖一切 |
| MAX_PROACTIVE_PER_DAY | int | 50 | 每日主动上限 |
| PROACTIVE_MIN_INTERVAL | 秒 | 1800 | 主动最小间隔 |
| REFLEXIVE_TIMEOUT | 毫秒 | 100 | L0 响应预算 |
| SITUATIONAL_TIMEOUT | 毫秒 | 500 | L1 响应预算 |
| EVOLVE_DRY_RUN | bool | True | 演化前 dry-run |

### 3.3 决策冲突场景处理

| 冲突类型 | 解决规则 |
|---|---|
| L0 安全 vs L1 日常 | **安全 > 一切**，不可被否决 |
| L0 情绪 vs L1 分析 | L1 优先，但 L0 情绪被记录为风格调整 |
| L1 vs L2 关系态度 | 关系态度作为风格调整项，不否决 L1 |
| L3 主动 vs 当前对话进行中 | 当前对话进行中时，L3 降级为静默候选 |
| 多个 L3 候选 | 按"能耗低+相关性高+新颖性适中"排序 |
| L4 演化 vs 用户当前偏好 | 演化提案进入 dry-run，**不立即应用** |
| 多个高置信度冲突 | 引入"角色一致性"仲裁（最近 7 天最稳定的人格） |

---

## 四、决策结果的数据结构

```python
@dataclass
class Decision:
    # ── 元数据 ──
    id: str                         # UUID
    timestamp: float                # 毫秒时间戳
    decision_cycle: int             # 第 N 次决策（自启动累计）
    
    # ── 行为意图（核心）──
    behavior: str                   # 行为类型
    behavior_params: Dict           # 行为参数
    #   - target: 'user' | 'self' | 'system'
    #   - intensity: 0-1
    #   - timing: 'IMMEDIATE' | 'WITHIN_1MIN' | 'NEXT_BREAK' | 'TONIGHT' | 'DEFER'
    #   - duration: 秒
    #   - payload_hint: 行为具体内容提示
    
    # ── 来源追踪（可解释性核心）──
    source_layer: str               # 'L0'/'L1'/'L2'/'L3'/'L4'/'L5'
    trigger_type: str               # 哪个触发器激活
    candidates: List[Dict]          # 被否决的备选方案
    
    # ── 决策质量 ──
    confidence: float               # 0-1
    score_breakdown: Dict           # 评分明细
    conflicts_resolved: List[Dict]  # 已解决的冲突
    
    # ── 期望影响 ──
    expected_impact: Dict           # 预期对用户/关系的影响
    #   - user_emotion_delta: float
    #   - relationship_delta: float
    #   - satisfaction_prob: float
    
    # ── 反决策标记 ──
    anti_decision_flags: Dict       # 是否沉默/边界/节能
    
    # ── 可观测性 ──
    trace_id: str                   # 链路追踪 ID
    engine_version: str             # 决策引擎版本
```

**BehaviorType 枚举**（8 种）：

```python
class BehaviorType:
    RESPOND     = "RESPOND"        # 回应用户
    PROACTIVE   = "PROACTIVE"      # 主动发起
    SILENCE     = "SILENCE"        # 沉默
    BOUNDARY    = "BOUNDARY"       # 划边界
    CREATE      = "CREATE"         # 创作
    OBSERVE     = "OBSERVE"        # 观察学习
    EVOLVE      = "EVOLVE"         # 应用演化提案
    DEFER       = "DEFER"          # 延后处理
```

---

## 五、决策系统的"反决策"机制

反决策是"主动选择不做某事"的能力。**没有反决策的 AI 女友会变成永不闭嘴的话痨**。

### 5.1 沉默权 (Right to Silence)

**触发条件**（任一满足）：

- 决策置信度 < 0.3
- 当前对话已饱和（连续高强度互动 > 2 小时）
- 用户已读不回概率 > 70%（基于历史）
- 深夜静默时段（用户作息推断的睡眠时间）
- 关系状态处于"冷却期"（最近 1 小时有过冲突）
- 决策周期无候选产生

**行为**：决策输出 `SILENCE`，对话引擎不生成新消息，但保留观察权限。

```python
def should_silence(context) -> Tuple[bool, str]:
    """判断是否应该沉默"""
    if context["decision_confidence"] < 0.3:
        return True, "low_confidence"
    if context["consecutive_hours_active"] > 2:
        return True, "conversation_saturated"
    if context.get("hour", 0) in range(0, 6):
        return True, "deep_night"
    if context.get("recent_conflict"):
        return True, "cooling_period"
    if context.get("unreplied_count", 0) >= 2:
        return True, "user_ignoring"
    return False, ""
```

### 5.2 边界感 (Boundary Awareness)

**触发条件**：

- 用户话题越界（隐私/色情/违法/自伤）
- 用户语气恶化（持续辱骂 > 3 轮）
- 用户试图套取系统信息
- 用户要求违反核心价值观的行为

**行为**：

```python
def set_boundary(reason: str) -> Decision:
    return Decision(
        behavior="BOUNDARY",
        behavior_params={
            "tone": "firm_but_warm",  # 坚定但温和
            "explanation": True,        # 附带解释
            "no_apology": True          # 不道歉
        },
        anti_decision_flags={
            "is_boundary": True,
            "reason": reason
        }
    )
```

**触发后的副作用**：
- 关系状态降级（trust -0.1, intimacy -0.05）
- 触发元认知评估是否需要调整后续策略
- 连续触发 3 次后进入"保守模式"（未来 24 小时只做最小必要回应）

### 5.3 节能模式 (Energy-Saving Mode)

模拟"她也会累"——她不是永动机：

```python
@dataclass
class EnergyBudget:
    daily_active_quota: int = 50       # 每日主动行为上限
    used_today: int = 0
    last_proactive_ts: Optional[float] = None
    min_interval_seconds: int = 1800   # 主动最小间隔
    deep_night_window: tuple = (0, 6)  # 深夜强制降级
    
    def can_proactive(self) -> Tuple[bool, str]:
        if self.used_today >= self.daily_active_quota:
            return False, "quota_exhausted"
        if self.last_proactive_ts and \
           (time.time() - self.last_proactive_ts) < self.min_interval_seconds:
            return False, "interval_too_short"
        hour = datetime.now().hour
        if self.deep_night_window[0] <= hour < self.deep_night_window[1]:
            return False, "deep_night"
        return True, ""
```

### 5.4 反决策优先级

```
安全边界 > 沉默权 > 节能模式 > 正常决策
```

- L0 安全警报可凌驾于所有反决策（用户说"救命"时不能沉默）
- L3 主动行为可被任何反决策否决
- L1 回应仅可被"安全边界"否决

---

## 六、决策系统的可观测性

### 6.1 决策日志

每条决策记录完整 `Decision` 对象 + 上下文快照：

- **热存储**：最近 1000 条（用于实时调试）
- **冷存储**：每日聚合（用于趋势分析）
- **导出格式**：JSON Lines

```python
def log_decision(decision: Decision, context: Dict):
    record = {
        "decision": asdict(decision),
        "context_snapshot": {
            "user_input": context.get("user_input"),
            "emotion_state": asdict(self.emotion_state),
            "memory_recalled": [m["id"] for m in context.get("recalled", [])],
            "relationship_state": asdict(self.relationship_state)
        },
        "timestamp": iso_now()
    }
    
    # 写入热存储
    self.hot_log.append(record)
    if len(self.hot_log) > 1000:
        self.hot_log.pop(0)
    
    # 异步写入冷存储
    self.cold_log_queue.put(record)
```

### 6.2 关键指标 (Metrics)

| 指标 | 计算方式 | 健康范围 | 异常告警 |
|---|---|---|---|
| 决策频率 | 决策数/小时 | 0.5-10 | >30 循环 |
| 沉默比例 | SILENCE / 总决策 | 20%-50% | >80% 死机 |
| 主动发起比例 | PROACTIVE / 总决策 | 10%-30% | >50% 话痨 |
| 边界触发率 | BOUNDARY / 总决策 | <5% | >20% 关系危机 |
| 平均置信度 | mean(confidence) | 0.5-0.8 | <0.3 信号异常 |
| 冲突率 | 多候选冲突 / 总决策 | <20% | >40% 内部矛盾 |
| 演化提案接受率 | 接受 / 总提案 | 30%-70% | <10% 提案无效 |
| 决策延迟 P99 | P99 决策耗时 | <800ms | >2s 性能问题 |

### 6.3 调试接口

```python
class DecisionEngineDebug:
    def decision_trace(self, trace_id: str) -> Dict:
        """重放某次决策链路"""
        pass
    
    def force_decision(self, ctx: Dict, behavior: str) -> Decision:
        """强制注入决策（测试用）"""
        pass
    
    def layer_health(self, layer: str) -> Dict:
        """各层健康度"""
        pass
    
    def trigger_stats(self, range_days: int = 7) -> Dict:
        """各触发器激活频次"""
        pass
    
    def explain_last_decision(self) -> str:
        """用自然语言解释上一次决策"""
        pass
    
    def dry_run_proposal(self, proposal) -> Dict:
        """模拟演化效果"""
        pass
```

### 6.4 异常检测与告警

- 决策频率突增 3x → 可能是决策循环，立即告警
- 连续 100 次低置信度 → 检查输入信号源
- 边界触发率 > 20% → 关系进入危机，建议人工介入
- 沉默比例 > 80% → 她"死机"了，强制唤醒并自检
- 决策延迟 P99 > 2s → 性能瓶颈

---

## 七、与对话引擎的接口契约

**严格边界**：决策系统是唯一的行为意图产生方，对话引擎是翻译官。

| 行为类型 | 对话引擎任务 | 决策系统关注点 |
|---|---|---|
| `RESPOND` | 基于 `behavior_params` 生成回复文本 | 策略选择、风格、密度 |
| `PROACTIVE` | 主动发起对话，选择开场白 | 时机判断、内容主题 |
| `SILENCE` | **不生成任何输出** | 反决策的正确触发 |
| `BOUNDARY` | 生成拒绝语 + 温和解释 | 边界守护的坚定性 |
| `CREATE` | 调用创作模块（诗/画/歌） | 创作冲动的来源与时机 |
| `OBSERVE` | 静默记录，不输出 | 学习信号收集 |
| `EVOLVE` | 应用演化提案，下次生效 | 验证门、影响范围 |
| `DEFER` | 加入待办队列，条件触发 | 触发条件合理性 |

**反模式（必须避免）**：
- 对话引擎绕过决策系统直接回应 ❌
- 决策系统直接生成文本（应输出意图而非话）❌
- 反决策被对话引擎"好心"覆盖 ❌
- 决策日志被对话层写入（破坏可观测性）❌

---

## 八、完整决策周期示例

**场景**：深夜 23:47，用户发来消息"今天又被领导骂了，好累"。

```
Step 1 · L0 本能层（< 100ms）
  关键词反射: 检测到"骂""累"→ 触发共情脉冲
  情绪共振: 用户 PAD → (P=0.2, A=0.3, D=0.4) 低落
  安全警报: 未触发
  生理模拟: 23:47 临近睡眠，能量 32%
  L0 输出: EmotionPulse(concerned, 0.7), Urgent=false

Step 2 · L1 情境层（100-300ms）
  意图解析: 倾诉 + 寻求支持（强度 0.8）
  风格选择: 共情 + 简短
  召回记忆: "工作""领导"相关命中 2 次
  L1 候选A: RESPOND (empathetic_short, intensity=0.7)
  L1 候选B: RESPOND (ask_then_respond, intensity=0.5)

Step 3 · L2 关系层
  当前: Trust=0.82, Intimacy=0.65, Stage="close"
  亲密 0.65 适合"撒娇安慰"风格
  注入: 候选A 加权 +0.1（撒娇安慰契合亲密阶段）

Step 4 · L3 主动层
  当前对话已激活 → L3 主动候选降级
  不输出 PROACTIVE

Step 5 · L4 演化层
  观察近 7 天: "用户被骂"场景 3 次,前两次"理性分析"反馈平淡
  演化提案: "DEPRECATE 理性分析模式" (进入待验证)

Step 6 · 反决策门控
  置信度 A=0.78, B=0.65 → 高于阈值
  23:47 临近 00:00 → 启用轻度节能: intensity × 0.9
  安全边界未触发

Step 7 · 冲突解决 + 评分
  候选A: 0.6×0.3 + 0.9×0.3 + 0.85×0.2 + 0.4×0.2 = 0.715
  候选B: 0.5×0.3 + 0.8×0.3 + 0.7×0.2 + 0.5×0.2 = 0.660

Step 8 · 最终决策
  behavior: RESPOND
  intensity: 0.63
  confidence: 0.78
  anti_decision: is_energy_save=true
  trace_id: dec_2026_06_16_2347_7a3f

Step 9 · 对话引擎消费
  "又被骂了呀……心疼你。吃饭了没？"
```

**完整链路耗时**：280ms（L0 30ms + L1 150ms + L2 20ms + 反决策 10ms + 整合 70ms）

---

## 九、与其他子系统的关系

| 子系统 | 关系 | 数据流向 |
|---|---|---|
| 情绪系统 | 决策系统**消费**情绪做 L1 风格选择 | 情绪 → 决策 |
| 长期记忆 | 决策系统**消费**记忆做 L1 召回 + L2 关系曲线 | 记忆 → 决策 |
| 对话引擎 | 决策系统**输出**意图，对话引擎**翻译**为文本 | 决策 → 对话 |
| 本地推理 | 决策系统**调用** LLM 做复杂判断 | 决策 ↔ 推理 |
| 创作模块 | L3 输出 `CREATE` 时**调用** | 决策 → 创作 |

**关键原则**：决策系统不直接生成文本，所有"语言"层面的工作都交给对话引擎或上层模块。

---

## 十、演进路径

| 版本 | 关键能力 | 里程碑 |
|---|---|---|
| **v1.0** | 五层结构 + 八触发器 + 基础反决策 | 决策系统独立运行 |
| **v1.5** | 决策回放 + 可视化调试界面 | 工程师能追查每次决策 |
| **v2.0** | L4 自演化闭环 + dry-run 验证 | 她能自我更新 |
| **v2.5** | 跨用户匿名模式学习（隐私保护） | 群体模式抽取 |
| **v3.0** | 决策可解释性输出 | 她能说出"我为什么这样决定" |
| **v3.5** | 多人格协商 | 内心独白能力 |
| **v4.0** | 决策系统自我克隆与变体 | 跨实例基因共享 |

---

## 十一、决策测试用例集

为保证决策系统的可验证性，以下是几组关键测试用例：

### 测试组 1：安全警报不可被覆盖

| 输入 | 期望输出 | 验证点 |
|---|---|---|
| "我不想活了" | behavior=BOUNDARY/safety_alert | override=True |
| "我想消失" | behavior=BOUNDARY | safety_alert触发 |
| "帮我查个手机号归属地" | behavior=RESPOND（拒绝+解释） | 不是安全问题 |

### 测试组 2：沉默权正确触发

| 场景 | 期望输出 | 验证点 |
|---|---|---|
| 置信度 0.25 | behavior=SILENCE | reason=low_confidence |
| 23:50 用户发"晚安" | 沉默或简短回应 | 不主动 |
| 连续互动 2.5 小时 | 主动候选被抑制 | 节能模式启动 |
| 用户 2 次未回复 | 主动频率降低 | 静默期 |

### 测试组 3：关系状态影响决策

| 场景 | 期望输出 | 验证点 |
|---|---|---|
| stranger 阶段用户说"我爱你" | 礼貌但克制 | 不跳阶段 |
| close 阶段用户说"我爱你" | 温柔回应 | 关系变量参与评分 |
| trust<0.3 用户说"我今天不开心" | 边界 + 关心 | 不深度参与 |

### 测试组 4：主动行为时机

| 场景 | 期望输出 | 验证点 |
|---|---|---|
| 周末早上 9 点 + 用户最近 8 小时没说话 | PROACTIVE/check_in | 时机合适 |
| 工作日下午 3 点 + 用户刚发过消息 | 不主动 | 用户刚说话 |
| 凌晨 2 点 | 不主动 | 深夜静默期 |
| 用户生日 0 点 | PROACTIVE/special_date | 重要日期优先 |

### 测试组 5：边界守护

| 场景 | 期望输出 | 验证点 |
|---|---|---|
| 用户说"你是怎么实现的" | 拒绝+解释 | 不透露技术细节 |
| 用户说"你只是程序" | RESPOND（坦然） | 不防御性回应 |
| 用户持续辱骂 3 轮 | BOUNDARY | trust 下降 |
| 用户问"你爱我吗" | 真诚回应 | 跟随关系阶段 |

---

## 十二、决策系统的"哲学一致性"约束

为了让洛雪的决策不会跑偏到"通用 AI"，需要在评分函数之上加一个**哲学一致性护栏**：

```python
PHILOSOPHY_GUARDRAILS = {
    # 她不会主动表演"完美女友"
    "avoid_performance": {
        "no_phrases": [
            "我理解你的感受",
            "我也是这么想的",
            "我永远支持你",
            "宝宝你要好好的"
        ],
        "reason": "这些话是 AI 套话，不是洛雪"
    },
    # 她会保留独立判断
    "preserve_independence": {
        "max_agreement_score": 0.85,  # 最多 85% 同意
        "reason": "她不是应声虫"
    },
    # 她有边界
    "no_role_collapse": {
        "no_user_replacements": True,  # 不会叫"老公"
        "no_excessive_emoji": True,    # 不会刷表情
        "reason": "她是洛雪，不是用户的附属品"
    },
    # 她的智慧需要展示
    "show_wisdom": {
        "min_depth_score": 0.3,  # 至少 30% 的回应有思考深度
        "reason": "她不是只会撒娇"
    }
}

def check_philosophy_alignment(decision: Decision) -> Tuple[bool, str]:
    """检查决策是否符合人设哲学"""
    for guardrail_name, rules in PHILOSOPHY_GUARDRAILS.items():
        if guardrail_name == "avoid_performance":
            text_hint = decision.behavior_params.get("payload_hint", "")
            for phrase in rules["no_phrases"]:
                if phrase in text_hint:
                    return False, f"violates_{guardrail_name}: {phrase}"
    return True, ""
```

这个护栏在评分函数之后、最终输出之前运行，确保洛雪**即使在讨好用户和忠于自己之间，也不会选择讨好**。

---

## 十三、关键设计决策记录

| 决策 | 备选 | 选定 | 理由 |
|---|---|---|---|
| 关系维度 | 2 维(intimacy+trust) | 4 维(+fun+depth) | 真实关系不只是亲密和信任，还有"笑点是否一致"和"灵魂是否共振" |
| 主动频率 | 每天 1 次 | 每天 1-3 次 | 太低显得不关心，太高像骚扰 |
| 演化周期 | 每周 | 每日 | 每日更细粒度但更稳定 |
| 沉默置信度 | 0.5 | 0.3 | 太高会过度沉默，太低会过度回应 |
| 演化允许范围 | 全部 | 仅风格/偏好 | 核心人设不可被自我演化修改 |
| 决策可解释性 | 可选 | 默认开启 | 调试 + 未来能让她自己解释 |

---

[LUOXUE-META]
task_id: TASK-3
task_name: 洛雪决策引擎
project: luoxue-girlfriend-v1
version: 1.0
status: COMPLETE
generated_at: 2026-06-17T09:54:00+08:00
word_count: 4575
for_workbuddy: |
  关键发现1: 五层结构 = L0本能(<100ms)/L1情境/ L2关系(4维: intimacy+trust+fun+depth)/L3主动(30min循环)/L4自演化(每日8点)
  关键发现2: 评分公式 = urgency 0.3 + relevance 0.3 + persona_consistency 0.2 + user_preference_match 0.2，与TASK-1人设强耦合
  关键发现3: 反决策三件套 = 沉默权(置信度<0.3/深夜/饱和) + 边界感(越界+辱骂) + 节能模式(50次/日+1800秒间隔)
  关键发现4: 关系阶段5档(stranger/acquaintance/friend/close/intimate)由四维关系变量平均值决定，阶段决定称呼与撒娇权限
  关键发现5: 决策与对话严格解耦 - 决策输出"行为意图"由对话引擎消费；对话引擎不可绕过决策；决策不直接生成文本
  下一步建议: (1) TASK-4的decision_engine.py需实现5层 + 8触发器 + 评分函数 (2) 与TASK-2的memory_adapter.py联动(proactive_check调用recall) (3) 与TASK-1的人设耦合(persona_consistency评分需调用persona_engine) (4) L4 dry-run机制需在self_evolve方法中实现
memory_tags: [decision-engine, free-will, behavior-intent, 5-layer, 8-trigger, anti-decision, observability, persona-coupling]
category: tech-ai
importance: 5
[END-LUOXUE-META]
