 """
 emotional_recall.py - 情感回忆引擎
 ================================
 让记忆检索不仅有"相关性"和"强度"，还有"情感染色"。
 
 核心机制:
 1. 情感标记 (Emotional Tagging): 每次交互时自动记录情感状态标签
 2. 情感一致性检索 (Mood-Congruent Recall): 当前情绪状态偏向检索同情绪的记忆
 3. 情感觉醒 (Emotional Arousal): 高唤醒度的记忆更容易被回忆
 4. 情感对比增强 (Contrast Enhancement): 与当前情感形成强烈对比的记忆也突出
 5. 情感衰减曲线 (Affective Decay): 情感强度随时间平缓衰减，但不会完全消失
 6. 气味/场景/声音触发: 模拟感官触发的回忆机制
 
 参考:
 - Bower (1981). "Mood and memory"
 - LeDoux (2000). "Emotion circuits in the brain"
 - Phelps (2004). "Human emotion and memory: interactions of the amygdala and hippocampal complex"
 - Kensinger & Schacter (2008). "Memory and emotion"
 """
 
 import json
 import math
 import random
 import uuid
 from pathlib import Path
 from datetime import datetime, timedelta
 from collections import defaultdict
 from typing import Optional
 
 
 class EmotionalRecallEngine:
     """情感回忆引擎 - 让记忆带有情感染色"""
 
     # 情感维度的基础标签
     EMOTION_DIMENSIONS = {
         "joy": {"valence": 0.8, "arousal": 0.6, "dominance": 0.7},
         "sadness": {"valence": 0.2, "arousal": 0.3, "dominance": 0.3},
         "anger": {"valence": 0.2, "arousal": 0.9, "dominance": 0.6},
         "fear": {"valence": 0.1, "arousal": 0.8, "dominance": 0.2},
         "surprise": {"valence": 0.5, "arousal": 0.8, "dominance": 0.5},
         "disgust": {"valence": 0.1, "arousal": 0.5, "dominance": 0.4},
         "trust": {"valence": 0.7, "arousal": 0.3, "dominance": 0.6},
         "anticipation": {"valence": 0.6, "arousal": 0.6, "dominance": 0.5},
     }
 
     # 复杂情感的组成（基础情感的混合）
     COMPLEX_EMOTIONS = {
         "love": [("joy", 0.5), ("trust", 0.4), ("surprise", 0.1)],
         "remorse": [("sadness", 0.5), ("disgust", 0.3), ("anger", 0.2)],
         "nostalgia": [("joy", 0.4), ("sadness", 0.4), ("surprise", 0.2)],
         "anxiety": [("fear", 0.6), ("anticipation", 0.3), ("anger", 0.1)],
         "hope": [("anticipation", 0.5), ("joy", 0.3), ("trust", 0.2)],
         "gratitude": [("trust", 0.4), ("joy", 0.4), ("surprise", 0.2)],
         "wonder": [("surprise", 0.4), ("anticipation", 0.3), ("joy", 0.3)],
         "melancholy": [("sadness", 0.5), ("nostalgia", 0.3), ("trust", 0.2)],
     }
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "emotional-recall-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "emotion_tags": {},             # node_id -> {tags, PAD, intensity, timestamp}
                 "current_mod": {"emotion": "neutral", "intensity": 0.0},
                 "trigger_phrases": {},          # phrase -> [node_id, ...]
                 "emotion_history": [],          # 情感历史记录
                 "meta": {"total_tagged": 0, "total_triggers": 0}
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     # ========== 1. 情感标记 ==========
     def tag_memory_emotion(self, node_id: str, content: str, context_pad: Optional[dict] = None) -> dict:
         """为记忆节点添加情感标记
         
         Args:
             node_id: 目标记忆节点
             content: 内容文本
             context_pad: 可选的PAD情感上下文
         
         Returns: 情感标记结果
         """
         # 简化情感检测（基于关键词）
         detected_emotions = []
         emotion_keywords = {
             "joy": ["开心", "快乐", "高兴", "喜欢", "爱", "幸福", "美好", "笑", "喜悦", "满足", "温暖"],
             "sadness": ["难过", "伤心", "哭", "悲伤", "失落", "孤独", "痛苦", "失望", "心痛", "委屈"],
             "anger": ["生气", "愤怒", "气死", "烦", "讨厌", "恨", "受够了", "不满", "暴躁"],
             "fear": ["害怕", "担心", "焦虑", "担心", "恐惧", "不安", "紧张", "慌"],
             "surprise": ["惊讶", "意外", "没想到", "惊喜", "震惊", "居然", "竟然"],
             "trust": ["相信", "信任", "可靠", "放心", "理解", "支持", "依靠"],
             "anticipation": ["期待", "希望", "盼望", "想", "计划", "准备", "等"],
         }
 
         content_lower = content.lower()
         for emotion, keywords in emotion_keywords.items():
             for kw in keywords:
                 if kw in content_lower:
                     dim = self.EMOTION_DIMENSIONS.get(emotion, {"valence": 0.5, "arousal": 0.5, "dominance": 0.5})
                     detected_emotions.append({
                         "emotion": emotion,
                         "intensity": min(1.0, 0.3 + random.random() * 0.5),
                         "pad": dim,
                         "keyword": kw,
                     })
                     break
 
         if not detected_emotions and context_pad:
             # 如果没有检测到情感但有PAD上下文，使用PAD推断最近情感
             p = context_pad.get("P", 0.5)
             a = context_pad.get("A", 0.5)
             d = context_pad.get("D", 0.5)
 
             distances = []
             for em, dim in self.EMOTION_DIMENSIONS.items():
                 dist = math.sqrt((p - dim["valence"])**2 + (a - dim["arousal"])**2 + (d - dim["dominance"])**2)
                 distances.append((em, dist))
             distances.sort(key=lambda x: x[1])
             best = distances[0][0]
             detected_emotions.append({
                 "emotion": best,
                 "intensity": 0.3,
                 "pad": self.EMOTION_DIMENSIONS[best],
                 "keyword": "pad_inferred",
             })
 
         if not detected_emotions:
             # 中性
             detected_emotions.append({
                 "emotion": "neutral",
                 "intensity": 0.0,
                 "pad": {"valence": 0.5, "arousal": 0.5, "dominance": 0.5},
                 "keyword": "neutral",
             })
 
         # 取最强情感
         strongest = max(detected_emotions, key=lambda x: x["intensity"])
 
         tag = {
             "emotion": strongest["emotion"],
             "intensity": strongest["intensity"],
             "pad": strongest["pad"],
             "all_emotions": detected_emotions,
             "tagged_at": datetime.now().isoformat(),
             "last_accessed": datetime.now().isoformat(),
         }
 
         self.data["emotion_tags"][node_id] = tag
         self.data["meta"]["total_tagged"] += 1
 
         # 提取可能的触发短语
         self._extract_trigger_phrases(node_id, content)
 
         self._save()
         return tag
 
     def _extract_trigger_phrases(self, node_id: str, content: str):
         """提取可能触发回忆的短语或场景"""
         trigger_patterns = [
             "第一次", "那天", "记得", "以前", "上次", "曾经",
             "在", "的时候", "遇到", "看见", "听到",
         ]
         for phrase in trigger_patterns:
             if phrase in content:
                 if phrase not in self.data["trigger_phrases"]:
                     self.data["trigger_phrases"][phrase] = []
                 if node_id not in self.data["trigger_phrases"][phrase]:
                     self.data["trigger_phrases"][phrase].append(node_id)
                     self.data["meta"]["total_triggers"] += 1
 
     # ========== 2. 情感一致性检索 ==========
     def mood_congruent_retrieve(
         self, current_emotion: str, current_intensity: float,
         base_results: list[dict], weight: float = 0.3
     ) -> list[dict]:
         """情感一致性检索
         
         当前心情为X时，偏向回忆起同样是X情感的记忆。
         比如心情低落时更容易想起难过的事（但不过度）。
 
         Args:
             current_emotion: 当前情感状态
             current_intensity: 当前情感强度 (0-1)
             base_results: 基础检索结果
             weight: 情感觉醒权重
 
         Returns: 情感加权后的检索结果
         """
         if current_emotion == "neutral" or current_intensity < 0.2:
             return base_results  # 中性状态下不加权
 
         modified = []
         for item in base_results:
             nid = item.get("id", "")
             tag = self.data["emotion_tags"].get(nid, {})
             if not tag:
                 modified.append(item)
                 continue
 
             mem_emotion = tag.get("emotion", "neutral")
             mem_intensity = tag.get("intensity", 0)
 
             # 情感一致性
             congruent = 1.0
             if mem_emotion == current_emotion:
                 congruent = 1.0 + current_intensity * 0.5  # 最多+50%
 
             # 高唤醒度加成
             aro = tag.get("pad", {}).get("arousal", 0.5)
             arousal_boost = 1.0 + (aro - 0.5) * 0.4
 
             # 情感衰减
             try:
                 tagged_at = datetime.fromisoformat(tag.get("tagged_at", ""))
                 age_days = (datetime.now() - tagged_at).days
                 # 情感衰减：前7天快速衰减，之后缓慢（半衰期30天）
                 affective_decay = 1.0 / (1.0 + (age_days / 15) ** 0.7)
             except (ValueError, TypeError):
                 affective_decay = 0.5
 
             score = item.get("score", 0.5)
             new_score = score * congruent * arousal_boost * (0.5 + 0.5 * affective_decay)
 
             item["emotional_score"] = round(new_score, 4)
             item["mood_congruence"] = round(congruent, 2)
             item["affective_decay"] = round(affective_decay, 3)
             modified.append(item)
 
         modified.sort(key=lambda x: x.get("emotional_score", x.get("score", 0)), reverse=True)
         return modified
 
     # ========== 3. 情感触发回忆 ==========
     def trigger_recall(self, trigger_text: str, nodes_table: dict, max_results: int = 5) -> list[dict]:
         """基于触发词/场景的回忆
         
         模拟"闻到儿时厨房的味道突然想起奶奶"这类触发机制。
         触发源可以是: 对话中的词、时间、场景描述等。
         """
         results = []
         for phrase, node_ids in self.data["trigger_phrases"].items():
             if phrase in trigger_text:
                 for nid in node_ids[:3]:  # 每个短语最多3个
                     node = nodes_table.get(nid, {})
                     tag = self.data["emotion_tags"].get(nid, {})
                     if node:
                         results.append({
                             "id": nid,
                             "title": node.get("title", ""),
                             "trigger": phrase,
                             "emotion": tag.get("emotion", "neutral"),
                             "intensity": tag.get("intensity", 0),
                         })
 
         # 去重
         seen = set()
         unique = []
         for r in results:
             if r["id"] not in seen:
                 seen.add(r["id"])
                 unique.append(r)
 
         return unique[:max_results]
 
     # ========== 4. 更新当前情感状态 ==========
     def update_current_mood(self, emotion: str, intensity: float):
         """更新当前情感状态
         
         情感状态会持续影响后续的检索和行为。
         随时间自然回归到中性。
         """
         self.data["current_mod"] = {
             "emotion": emotion,
             "intensity": min(1.0, intensity),
             "updated_at": datetime.now().isoformat(),
         }
 
         # 记录情感历史
         self.data["emotion_history"].append({
             "emotion": emotion,
             "intensity": intensity,
             "timestamp": datetime.now().isoformat(),
         })
 
         # 保持历史记录不超过1000条
         if len(self.data["emotion_history"]) > 1000:
             self.data["emotion_history"] = self.data["emotion_history"][-1000:]
 
         self._save()
 
     def get_current_mood(self) -> dict:
         """获取当前情感状态（随时间自然衰减）"""
         current = self.data.get("current_mod", {"emotion": "neutral", "intensity": 0.0})
         updated_at = current.get("updated_at", "")
         try:
             if updated_at:
                 hours_since = (datetime.now() - datetime.fromisoformat(updated_at)).total_seconds() / 3600
                 decay = math.exp(-hours_since / 4)  # 4小时半衰
                 current["intensity"] = current["intensity"] * decay
                 if current["intensity"] < 0.1:
                     current["emotion"] = "neutral"
                     current["intensity"] = 0.0
         except (ValueError, TypeError):
             pass
         return current
 
     # ========== 5. 情感衰减 ==========
     def natural_mood_decay(self):
         """模拟情感的自然衰减过程"""
         current = self.get_current_mood()
         if current["emotion"] != "neutral" and current["intensity"] < 0.1:
             self.data["current_mod"] = {
                 "emotion": "neutral",
                 "intensity": 0.0,
                 "updated_at": datetime.now().isoformat(),
             }
             self._save()
 
     # ========== 6. 统计 ==========
     def stats(self) -> dict:
         return {
             "total_emotion_tags": self.data["meta"]["total_tagged"],
             "total_triggers": self.data["meta"]["total_triggers"],
             "current_mood": self.get_current_mood(),
             "emotion_tags_breakdown": Counter(
                 t.get("emotion", "unknown") for t in self.data["emotion_tags"].values()
             ),
         }
 
 
