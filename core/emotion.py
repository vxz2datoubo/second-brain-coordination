"""
emotion.py — 情绪与关系引擎 (Phase 4)

蓝图 §4 情绪与关系模型:
- UserEmotionSnapshot: 定期采集用户情绪状态
- EmotionalPatternMemory: 触发词→情绪模式映射
- RelationshipMemory: 长期关系状态 (亲密度/信任度/熟悉度)
- BotAffectivePolicy: 9 维度表达策略 (温暖/幽默/理性/关心/活泼/沉稳/鼓励/共情/好奇)
- 呼吸感规则: 回复频次/长度/主动性 自适应

设计原则:
- 零外部依赖 (纯 Python 计算)
- 基于事件日志 + 触发词词典
- 输出标准化情绪快照供 Plugin/MaiBot 消费
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Optional


class EmotionEngine:
    """情绪与关系引擎 — Phase 4 核心"""

    # ── 情绪触发词词典 ──
    EMOTION_TRIGGERS: dict[str, list[str]] = {
        "joy":      ["哈哈", "开心", "高兴", "快乐", "笑死", "棒", "太棒了", "牛", "妙", "nice", "❤", "😊", "😄", "👍"],
        "sadness":  ["难过", "伤心", "哭", "泪", "emo", "丧", "低落", "😢", "😭", "唉"],
        "anger":    ["气死", "愤怒", "烦", "恶心", "sb", "卧槽", "草", "操", "😡", "🤬"],
        "anxiety":  ["紧张", "担心", "焦虑", "慌", "怎么办", "压力", "不安", "😰", "😨"],
        "surprise": ["哇", "天哪", "不会吧", "真的假的", "震惊", "竟然", "😲", "😮"],
        "curiosity":["为什么", "什么意思", "？", "好奇", "咋回事", "🤔"],
        "boredom":  ["无聊", "没意思", "好烦", "乏味", "🥱"],
        "excitement":["刺激", "爽", "冲", "来了", "哦哦", "🔥", "🚀"],
        "tiredness":["累", "困", "疲惫", "睡了", "困死", "😴"],
        "affection": ["想你", "爱你", "喜欢", "抱抱", "贴贴", "🥰", "💕", "亲"],
        "loneliness":["孤独", "没人", "一个人", "寂寞"],
        "pride":    ["我做到了", "搞定", "完成", "还行吧", "👏"],
        "gratitude":["谢谢", "感谢", "多亏", "好运"],
        "frustration":["不行", "没用", "失败", "又", "崩溃", "🤯"],
    }

    EMOTION_INTENSITY_MAP: dict[str, float] = {
        # 轻度/中度/重度触发词对应强度
        "轻度": 0.3, "中度": 0.6, "重度": 0.9,
    }

    # ── 关系状态维度 ──
    RELATIONSHIP_DIMENSIONS = [
        "closeness",       # 亲密度 (0-100)
        "trust",           # 信任度 (0-100)
        "familiarity",     # 熟悉度 (0-100)
        "playfulness",     # 玩闹度 (0-100)
        "dependence",      # 依赖度 (0-100)
        "respect",         # 尊重度 (0-100)
    ]

    # ── Bot 表达策略 (9 维度) ──
    AFFECTIVE_POLICIES = [
        "warmth",          # 温暖
        "humor",           # 幽默
        "rationality",     # 理性
        "care",            # 关心
        "liveliness",      # 活泼
        "calmness",        # 沉稳
        "encouragement",   # 鼓励
        "empathy",         # 共情
        "curiosity",       # 好奇
    ]

    # ── 呼吸感规则 (基于时间/情绪/关系动态调整) ──
    BREATHING_DEFAULTS = {
        "max_replies_per_hour": 20,
        "idle_timeout_minutes": 30,       # 超时后降低主动度
        "active_multiplier": 1.5,          # 活跃时回复长度乘数
        "quiet_multiplier": 0.6,           # 安静时回复长度乘数
        "emotional_boost_threshold": 0.5,  # 情绪强度触发主动搭话阈值
    }

    def __init__(self, data_dir: Path, graph=None, memory=None):
        self.data_dir = data_dir
        self.graph = graph
        self.memory = memory
        self.path = data_dir / "emotion_state.json"
        self.state = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return self._default_state()

    def _default_state(self) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "user_emotion": {
                "current": "neutral",
                "confidence": 0.5,
                "valence": 0.0,          # -1(负) ~ +1(正)
                "arousal": 0.0,          # 0(平静) ~ 1(激动)
                "dominant_emotions": [],
                "last_updated": now,
            },
            "relationship": {
                "closeness": 50,
                "trust": 50,
                "familiarity": 50,
                "playfulness": 50,
                "dependence": 30,
                "respect": 60,
                "last_interaction": now,
                "total_interactions": 0,
                "milestones": [],
            },
            "affective_policy": {
                "active_dimensions": ["warmth", "care", "liveliness"],
                "weights": {
                    "warmth": 0.3, "humor": 0.15, "rationality": 0.1, "care": 0.2,
                    "liveliness": 0.15, "calmness": 0.05, "encouragement": 0.05,
                    "empathy": 0.0, "curiosity": 0.0,
                },
                "breathing": dict(self.BREATHING_DEFAULTS),
            },
            "emotion_history": [],
            "pattern_memory": {},
            "conflict_history": [],
        }

    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)

    # ═══════════════════════════════════════════
    # 情绪快照: 分析用户最新消息
    # ═══════════════════════════════════════════

    def analyze_message(self, text: str, context: dict = None) -> dict:
        """分析一条用户消息，返回情绪快照 + 更新内部状态

        Returns:
            {
                "dominant": str,         # 主导情绪
                "valence": float,        # -1 ~ +1
                "arousal": float,        # 0 ~ 1
                "intensity": float,      # 0 ~ 1
                "emotions": dict,        # 各情绪得分
                "suggested_response_tone": str,
                "relationship_change": dict,
            }
        """
        now = datetime.now(timezone.utc)

        # 1. 情绪检测
        emotions = self._detect_emotions(text)
        dominant = max(emotions, key=emotions.get) if emotions else "neutral"
        intensity = emotions.get(dominant, 0.3)

        # 2. 效价 + 唤醒度
        valence_map = {
            "joy": 0.8, "sadness": -0.7, "anger": -0.8, "anxiety": -0.5,
            "surprise": 0.3, "curiosity": 0.3, "boredom": -0.3, "excitement": 0.9,
            "tiredness": -0.2, "affection": 0.9, "loneliness": -0.6, "pride": 0.7,
            "gratitude": 0.7, "frustration": -0.6,
        }
        arousal_map = {
            "joy": 0.6, "sadness": 0.2, "anger": 0.8, "anxiety": 0.7,
            "surprise": 0.7, "curiosity": 0.4, "boredom": 0.1, "excitement": 0.9,
            "tiredness": 0.1, "affection": 0.5, "loneliness": 0.3, "pride": 0.6,
            "gratitude": 0.5, "frustration": 0.7,
        }
        valence = valence_map.get(dominant, 0.0) * intensity
        arousal = arousal_map.get(dominant, 0.3) * intensity

        # 3. 更新用户情绪状态
        old_valence = self.state["user_emotion"]["valence"]
        old_arousal = self.state["user_emotion"]["arousal"]
        # 指数平滑 (70% 新 / 30% 旧)
        smooth = 0.7
        self.state["user_emotion"]["valence"] = smooth * valence + (1 - smooth) * old_valence
        self.state["user_emotion"]["arousal"] = smooth * arousal + (1 - smooth) * old_arousal
        self.state["user_emotion"]["current"] = dominant
        self.state["user_emotion"]["confidence"] = intensity
        self.state["user_emotion"]["dominant_emotions"] = sorted(
            [(e, s) for e, s in emotions.items() if s > 0.2],
            key=lambda x: -x[1]
        )[:3]
        self.state["user_emotion"]["last_updated"] = now.isoformat()

        # 4. 更新关系状态
        rel = self.state["relationship"]
        rel["total_interactions"] += 1
        rel["last_interaction"] = now.isoformat()

        # 正效价事件提升亲密/信任
        rel_changes = {}
        if valence > 0.5:
            rel["closeness"] = min(100, rel["closeness"] + 1)
            rel["trust"] = min(100, rel["trust"] + 0.5)
            rel_changes = {"closeness": +1, "trust": +0.5}
        elif valence < -0.5:
            # 不降低关系 (只标记需要关心)
            rel_changes = {"note": "negative_valence_needs_care"}
        if dominant in ("affection", "gratitude"):
            rel["closeness"] = min(100, rel["closeness"] + 2)
            rel_changes["closeness"] = rel_changes.get("closeness", 0) + 2
        if dominant in ("anger", "frustration"):
            rel_changes["note"] = "user_upset_handle_with_care"

        # 5. 记录情绪历史
        self.state["emotion_history"].append({
            "timestamp": now.isoformat(),
            "text_snippet": text[:100],
            "dominant": dominant,
            "intensity": round(intensity, 2),
            "valence": round(valence, 2),
            "arousal": round(arousal, 2),
            "emotions": {e: round(s, 2) for e, s in emotions.items() if s > 0.1},
        })
        # 保留最近 200 条
        if len(self.state["emotion_history"]) > 200:
            self.state["emotion_history"] = self.state["emotion_history"][-200:]

        # 6. 更新情感模式记忆
        self._update_patterns(text, dominant)

        # 7. 调整表达策略
        self._adapt_affective_policy(dominant, intensity, valence)

        self._save()

        # 8. 建议回复语气
        tone = self._suggest_tone(dominant, valence, intensity)

        return {
            "dominant": dominant,
            "valence": round(valence, 2),
            "arousal": round(arousal, 2),
            "intensity": round(intensity, 2),
            "emotions": {e: round(s, 2) for e, s in emotions.items() if s > 0.1},
            "suggested_response_tone": tone,
            "relationship_change": rel_changes,
        }

    def _detect_emotions(self, text: str) -> dict[str, float]:
        """检测文本包含的各情绪得分 (0-1)"""
        scores = defaultdict(float)
        for emotion, triggers in self.EMOTION_TRIGGERS.items():
            for trigger in triggers:
                count = text.count(trigger)
                if count > 0:
                    # 权重: 长触发词 > 短触发词
                    weight = min(1.0, len(trigger) / 3)
                    scores[emotion] += count * weight * 0.3
        # 归一化到 0-1
        if scores:
            max_s = max(scores.values())
            if max_s > 0:
                scores = {k: min(1.0, v / max_s) for k, v in scores.items()}
        return dict(scores)

    def _update_patterns(self, text: str, dominant: str):
        """更新情感模式记忆 — 关联触发词→情绪"""
        pm = self.state["pattern_memory"]
        # 提取消息中的关键词 (2-4字)
        keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', text)
        for kw in keywords:
            if kw not in pm:
                pm[kw] = {}
            if dominant not in pm[kw]:
                pm[kw][dominant] = 0
            pm[kw][dominant] += 1

        # 限制模式记忆大小 (最多 500 条)
        if len(pm) > 500:
            # 保留出现次数最多的
            sorted_kw = sorted(pm.items(), key=lambda x: sum(x[1].values()), reverse=True)
            self.state["pattern_memory"] = dict(sorted_kw[:500])

    def _adapt_affective_policy(self, dominant: str, intensity: float, valence: float):
        """根据当前情绪调整 Bot 表达策略权重"""
        policy = self.state["affective_policy"]
        weights = policy["weights"]

        # 重置到基础权重
        base = {
            "warmth": 0.3, "humor": 0.15, "rationality": 0.1, "care": 0.2,
            "liveliness": 0.15, "calmness": 0.05, "encouragement": 0.05,
            "empathy": 0.0, "curiosity": 0.0,
        }

        # 情绪调整
        adjustments = {
            "sadness":    {"empathy": +0.3, "care": +0.15, "warmth": +0.1, "humor": -0.1, "liveliness": -0.1},
            "anger":      {"calmness": +0.2, "rationality": +0.1, "warmth": +0.1, "humor": -0.15},
            "anxiety":    {"calmness": +0.15, "encouragement": +0.15, "care": +0.1, "rationality": +0.05},
            "joy":        {"liveliness": +0.15, "humor": +0.1, "curiosity": +0.05},
            "excitement": {"liveliness": +0.2, "humor": +0.1, "curiosity": +0.1},
            "boredom":    {"curiosity": +0.2, "humor": +0.15, "liveliness": +0.1},
            "affection":  {"warmth": +0.2, "care": +0.1, "empathy": +0.1},
            "loneliness": {"warmth": +0.2, "care": +0.15, "encouragement": +0.1, "liveliness": +0.1},
            "pride":      {"encouragement": +0.15, "liveliness": +0.1},
            "tiredness":  {"calmness": +0.2, "care": +0.1, "warmth": +0.1, "humor": -0.05},
            "frustration":{"empathy": +0.2, "encouragement": +0.1, "rationality": +0.1},
        }

        adj = adjustments.get(dominant, {})
        for dim, delta in adj.items():
            weights[dim] = max(0.0, min(1.0, base.get(dim, 0.1) + delta * intensity))

        # 确保所有权重归一化
        total = sum(weights.values())
        if total > 0:
            for k in weights:
                weights[k] /= total

        policy["active_dimensions"] = sorted(
            [d for d, w in weights.items() if w > 0.05],
            key=lambda d: -weights[d]
        )[:5]

        # 呼吸感: 情绪强烈时提高主动度
        if intensity > 0.6 and valence < -0.3:
            policy["breathing"]["active_multiplier"] = 1.2      # 需要安慰时多说点
            policy["breathing"]["idle_timeout_minutes"] = 15    # 更快响应
        else:
            policy["breathing"] = dict(self.BREATHING_DEFAULTS)

    def _suggest_tone(self, dominant: str, valence: float, intensity: float) -> str:
        """根据情绪推荐回复语气"""
        if dominant == "neutral" or intensity < 0.2:
            return "warm_casual"

        tone_map = {
            "joy":        "enthusiastic",
            "sadness":    "gentle_supportive",
            "anger":      "calm_understanding",
            "anxiety":    "reassuring",
            "surprise":   "curious_engaged",
            "curiosity":  "informative_playful",
            "boredom":    "energetic_playful",
            "excitement": "energetic_enthusiastic",
            "tiredness":  "soft_caring",
            "affection":  "warm_reciprocal",
            "loneliness": "warm_company",
            "pride":      "celebratory",
            "gratitude":  "warm_humble",
            "frustration":"patient_supportive",
        }
        return tone_map.get(dominant, "warm_casual")

    # ═══════════════════════════════════════════
    # 关系查询 API
    # ═══════════════════════════════════════════

    def get_user_snapshot(self) -> dict:
        """获取当前用户情绪 + 关系快照 (供 MaiBot Prompt 注入)"""
        ue = self.state["user_emotion"]
        rel = self.state["relationship"]
        ap = self.state["affective_policy"]

        # 关系等级描述
        closeness = rel.get("closeness", 50)
        if closeness >= 80:
            rel_level = "亲密无间"
        elif closeness >= 60:
            rel_level = "熟悉亲近"
        elif closeness >= 40:
            rel_level = "友好"
        elif closeness >= 20:
            rel_level = "初步认识"
        else:
            rel_level = "初识"

        return {
            "emotion": {
                "current": ue["current"],
                "intensity": round(ue["confidence"], 2),
                "valence": round(ue["valence"], 2),
                "arousal": round(ue["arousal"], 2),
            },
            "relationship": {
                "level": rel_level,
                "closeness": closeness,
                "trust": rel.get("trust", 50),
                "total_interactions": rel.get("total_interactions", 0),
            },
            "suggested_tone": self._suggest_tone(ue["current"], ue["valence"], ue["confidence"]),
            "active_policy": ap["active_dimensions"][:3],
        }

    def get_relationship(self) -> dict:
        """获取完整关系状态"""
        return dict(self.state["relationship"])

    def get_emotion_timeline(self, hours: int = 24) -> list[dict]:
        """获取最近 N 小时的情绪时间线"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [
            h for h in self.state["emotion_history"]
            if datetime.fromisoformat(h["timestamp"]) >= cutoff
        ]

    def get_patterns(self, keyword: str = "", top_k: int = 10) -> dict:
        """查询情感模式记忆"""
        pm = self.state["pattern_memory"]
        if keyword:
            return {k: v for k, v in pm.items() if keyword in k}
        sorted_patterns = sorted(pm.items(), key=lambda x: sum(x[1].values()), reverse=True)
        return dict(sorted_patterns[:top_k])

    def get_affective_policy(self) -> dict:
        """获取当前 Bot 表达策略"""
        return dict(self.state["affective_policy"])

    def record_conflict(self, conflict_type: str, resolution: str, note: str = ""):
        """记录一次人际冲突及解决"""
        self.state["conflict_history"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": conflict_type,
            "resolution": resolution,
            "note": note,
        })
        # 冲突后轻微降低信任，但解决后恢复
        if resolution == "resolved":
            self.state["relationship"]["trust"] = min(100, self.state["relationship"]["trust"] + 2)
        elif resolution == "unresolved":
            self.state["relationship"]["trust"] = max(0, self.state["relationship"]["trust"] - 3)
        elif resolution == "apology_accepted":
            self.state["relationship"]["trust"] = min(100, self.state["relationship"]["trust"] + 5)
        self._save()

    def add_milestone(self, milestone: str):
        """添加关系里程碑"""
        self.state["relationship"]["milestones"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "milestone": milestone,
        })
        self._save()

    # ═══════════════════════════════════════════
    # 聚合分析
    # ═══════════════════════════════════════════

    def analyze_trend(self, days: int = 7) -> dict:
        """分析情绪趋势 (最近 N 天)"""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        recent = [h for h in self.state["emotion_history"] if h["timestamp"] >= cutoff]

        if not recent:
            return {"trend": "insufficient_data", "days": days, "samples": 0}

        valences = [h["valence"] for h in recent]
        avg_valence = sum(valences) / len(valences)
        trend = "improving" if avg_valence > 0.2 else ("declining" if avg_valence < -0.2 else "stable")

        # 主导情绪统计
        emotion_counts = defaultdict(int)
        for h in recent:
            emotion_counts[h["dominant"]] += 1
        top_emotions = sorted(emotion_counts.items(), key=lambda x: -x[1])[:5]

        return {
            "trend": trend,
            "days": days,
            "samples": len(recent),
            "avg_valence": round(avg_valence, 2),
            "avg_arousal": round(sum(h["arousal"] for h in recent) / len(recent), 2),
            "top_emotions": top_emotions,
            "dominant_mood": top_emotions[0][0] if top_emotions else "neutral",
        }

    def relationship_health(self) -> dict:
        """关系健康度评估"""
        rel = self.state["relationship"]
        dims = {d: rel.get(d, 50) for d in self.RELATIONSHIP_DIMENSIONS}
        avg = sum(dims.values()) / len(dims)

        if avg >= 80:
            status = "excellent"
        elif avg >= 60:
            status = "healthy"
        elif avg >= 40:
            status = "ok"
        elif avg >= 20:
            status = "strained"
        else:
            status = "critical"

        return {
            "health": status,
            "average": round(avg, 1),
            "dimensions": dims,
            "total_interactions": rel.get("total_interactions", 0),
            "milestones": rel.get("milestones", []),
        }

    def breathing_advice(self) -> dict:
        """当前呼吸感建议 (用于 MaiBot 调整回复行为)"""
        ue = self.state["user_emotion"]
        bp = self.state["affective_policy"]["breathing"]
        rel = self.state["relationship"]

        hours_since_last = 0
        if rel.get("last_interaction"):
            try:
                lt = datetime.fromisoformat(rel["last_interaction"])
                hours_since_last = (datetime.now(timezone.utc) - lt).total_seconds() / 3600
            except:
                pass

        idle_too_long = hours_since_last > (bp["idle_timeout_minutes"] / 60)

        return {
            "should_reach_out": idle_too_long and ue["valence"] > -0.3,
            "reply_length_multiplier": bp["active_multiplier"] if abs(ue["valence"]) > 0.4 else bp["quiet_multiplier"],
            "idle_hours": round(hours_since_last, 1),
            "emotional_boost": ue["confidence"] > bp["emotional_boost_threshold"],
            "suggested_max_replies": bp["max_replies_per_hour"],
        }
