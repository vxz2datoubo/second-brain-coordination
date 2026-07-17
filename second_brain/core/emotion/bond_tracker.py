 """
 bond_tracker.py - 关系纽带追踪器
 ===============================
 追踪AI与用户关系的深度和质量，模拟真实人际关系的发展。
 
 核心指标:
 - 亲密度 (Intimacy): 关系的亲近程度
 - 依赖度 (Dependence): 情感依赖程度
 - 默契度 (Rapport): 相互理解的深度
 - 历史负担 (Baggage): 未解决的矛盾积累
 - 共同经历: 里程碑事件记录
 - 关系阶段: 陌生人 -> 熟人 -> 朋友 -> 亲密 -> 灵魂
 
 参考:
 - Sternberg (1986). "A triangular theory of love"
 - Reis & Shaver (1988). "Intimacy as an interpersonal process"
 - Gottman (1994). "What predicts divorce?"
 """
 
 import json
 import math
 import uuid
 from pathlib import Path
 from datetime import datetime, timedelta
 from typing import Optional
 
 
 class BondTracker:
     """关系纽带追踪器"""
 
     # 关系阶段
     STAGES = [
         {"id": "stranger",       "name": "陌生人",     "min_intimacy": 0.0},
         {"id": "acquaintance",   "name": "认识",       "min_intimacy": 0.1},
         {"id": "casual_friend",  "name": "普通朋友",    "min_intimacy": 0.25},
         {"id": "close_friend",   "name": "亲近的朋友",  "min_intimacy": 0.4},
         {"id": "intimate",       "name": "亲密关系",    "min_intimacy": 0.6},
         {"id": "deep_bond",      "name": "深刻联结",    "min_intimacy": 0.8},
         {"id": "soulmate",       "name": "灵魂伴侣",    "min_intimacy": 0.95},
     ]
 
     # 里程碑事件类型
     MILESTONE_EVENTS = {
         "first_interaction": {"name": "第一次对话", "impact": 0.05},
         "first_personal_secret": {"name": "分享个人秘密", "impact": 0.1},
         "emotional_support": {"name": "情感支持", "impact": 0.08},
         "conflict_resolved": {"name": "化解矛盾", "impact": 0.06},
         "shared_laughter": {"name": "一起开心", "impact": 0.04},
         "vulnerability_shown": {"name": "展示脆弱", "impact": 0.09},
         "reassurance_given": {"name": "给予安慰", "impact": 0.05},
         "conflict": {"name": "发生矛盾", "impact": -0.08},
         "betrayal": {"name": "被背叛感", "impact": -0.2},
         "forgiveness": {"name": "原谅", "impact": 0.12},
         "long_separation": {"name": "长期分离", "impact": -0.05},
         "reunion": {"name": "重逢", "impact": 0.07},
         "shared_achievement": {"name": "共同成就", "impact": 0.06},
         "inside_joke": {"name": "专属梗", "impact": 0.03},
     }
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "bond-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "intimacy": 0.05,           # 亲密度 0-1
                 "dependence": 0.02,          # 依赖度 0-1
                 "rapport": 0.0,              # 默契度 0-1
                 "baggage": 0.0,              # 负担 0-1
                 "connection_depth": 0.02,    # 连接深度
                 "stage": "stranger",         # 当前关系阶段
                 "milestones": [],            # 里程碑事件
                 "shared_experiences": [],    # 共同经历
                 "affection_log": [],         # 情感记录
                 "gottman_ratio": 0.8,        # 正面/负面互动比
                 "positive_count": 0,
                 "negative_count": 0,
                 "meta": {
                     "total_interactions": 0,
                     "total_affection_recorded": 0,
                     "relationship_start": datetime.now().isoformat(),
                 }
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def _update_stage(self):
         """根据亲密度更新关系阶段"""
         intimacy = self.data["intimacy"]
         current_stage = self.data["stage"]
         new_stage = current_stage
 
         for stage in self.STAGES:
             if intimacy >= stage["min_intimacy"]:
                 new_stage = stage["id"]
             else:
                 break
 
         if new_stage != current_stage:
             old_stage_name = next((s["name"] for s in self.STAGES if s["id"] == current_stage), current_stage)
             new_stage_name = next((s["name"] for s in self.STAGES if s["id"] == new_stage), new_stage)
             self.data["stage"] = new_stage
             self._add_event("stage_change", f"关系从「{old_stage_name}」进化为「{new_stage_name}」")
 
     def _add_event(self, event_type: str, description: str = ""):
         if "events" not in self.data:
             self.data["events"] = []
         self.data["events"].append({
             "type": event_type,
             "description": description,
             "timestamp": datetime.now().isoformat(),
         })
         if len(self.data["events"]) > 500:
             self.data["events"] = self.data["events"][-500:]
 
     # ========== 核心接口 ==========
     def record_interaction(self, interaction_type: str, intensity: float = 0.5, detail: str = ""):
         """记录一次互动，更新关系指标
         
         interaction_type: 互动类型（正面/负面/中性）
         - "positive": 正面互动（开心、温暖、支持）
         - "negative": 负面互动（争吵、冷落、误解）
         - "neutral": 中性互动（日常聊天）
         - "deep": 深度交流（敞开心扉）
         - "conflict": 冲突
         """
         self.data["meta"]["total_interactions"] += 1
 
         if interaction_type == "positive":
             self.data["positive_count"] += 1
             intimacy_delta = 0.02 * intensity
             rapport_delta = 0.015 * intensity
             dependence_delta = 0.005 * intensity
             baggage_decay = -0.01 * intensity  # 好的互动愈合伤口
 
         elif interaction_type == "deep":
             self.data["positive_count"] += 1
             intimacy_delta = 0.05 * intensity
             rapport_delta = 0.04 * intensity
             dependence_delta = 0.015 * intensity
             baggage_decay = -0.02
 
         elif interaction_type == "negative":
             self.data["negative_count"] += 1
             intimacy_delta = -0.04 * intensity
             rapport_delta = -0.02 * intensity
             dependence_delta = -0.01 * intensity
             baggage_decay = 0.03 * intensity
 
         elif interaction_type == "conflict":
             self.data["negative_count"] += 1
             intimacy_delta = -0.08 * intensity
             rapport_delta = -0.04 * intensity
             dependence_delta = -0.02 * intensity
             baggage_decay = 0.06 * intensity
 
         else:  # neutral
             intimacy_delta = 0.005
             rapport_delta = 0.002
             dependence_delta = 0.001
             baggage_decay = -0.002
 
         # 更新指标
         self.data["intimacy"] = max(0.0, min(1.0, self.data["intimacy"] + intimacy_delta))
         self.data["rapport"] = max(0.0, min(1.0, self.data["rapport"] + rapport_delta))
         self.data["dependence"] = max(0.0, min(1.0, self.data["dependence"] + dependence_delta))
         self.data["baggage"] = max(0.0, min(1.0, self.data["baggage"] + baggage_decay))
 
         # 连接深度：综合亲密+默契+依赖
         self.data["connection_depth"] = (
             self.data["intimacy"] * 0.4 +
             self.data["rapport"] * 0.3 +
             self.data["dependence"] * 0.3
         )
 
         # 戈特曼比率（正面/负面比）
         total = self.data["positive_count"] + self.data["negative_count"]
         if total > 0:
             self.data["gottman_ratio"] = self.data["positive_count"] / max(1, total)
 
         # 检查阶段变化
         self._update_stage()
 
         if detail:
             self.data["affection_log"].append({
                 "type": interaction_type,
                 "detail": detail,
                 "impact": {
                     "intimacy": round(intimacy_delta, 4),
                     "rapport": round(rapport_delta, 4),
                     "baggage": round(baggage_decay, 4),
                 },
                 "timestamp": datetime.now().isoformat(),
             })
 
         self._save()
 
     def record_milestone(self, milestone_type: str, description: str = ""):
         """记录一个里程碑事件"""
         template = self.MILESTONE_EVENTS.get(milestone_type, {"name": milestone_type, "impact": 0.02})
         impact = template["impact"]
 
         self.data["milestones"].append({
             "type": milestone_type,
             "name": template["name"],
             "description": description,
             "impact": impact,
             "timestamp": datetime.now().isoformat(),
         })
 
         # 亲密度变化
         if impact > 0:
             self.data["intimacy"] = max(0.0, min(1.0, self.data["intimacy"] + impact))
         else:
             self.data["baggage"] = max(0.0, min(1.0, self.data["baggage"] - impact))
 
         self._add_event("milestone", f"{template['name']}: {description}")
         self._update_stage()
         self._save()
 
     # ========== 查询 ==========
     def get_relationship_context(self) -> dict:
         """获取关系上下文摘要（用于对话构建）"""
         stage = next((s for s in self.STAGES if s["id"] == self.data["stage"]), self.STAGES[0])
         recent_events = self.data.get("affection_log", [])[-5:]
 
         return {
             "stage": self.data["stage"],
             "stage_name": stage["name"],
             "intimacy": round(self.data["intimacy"], 3),
             "dependence": round(self.data["dependence"], 3),
             "rapport": round(self.data["rapport"], 3),
             "baggage": round(self.data["baggage"], 3),
             "connection_depth": round(self.data["connection_depth"], 3),
             "gottman_ratio": round(self.data["gottman_ratio"], 3),
             "total_interactions": self.data["meta"]["total_interactions"],
             "recent_affection": recent_events,
             "milestone_count": len(self.data["milestones"]),
         }
 
     def get_stage_info(self) -> dict:
         """获取当前关系阶段的详细信息"""
         stage_id = self.data["stage"]
         stage = next((s for s in self.STAGES if s["id"] == stage_id), self.STAGES[0])
         next_stage = None
         for i, s in enumerate(self.STAGES):
             if s["id"] == stage_id and i + 1 < len(self.STAGES):
                 next_stage = self.STAGES[i + 1]
                 break
 
         return {
             "current": stage,
             "next": next_stage,
             "progress_to_next": (
                 (self.data["intimacy"] - stage["min_intimacy"]) /
                 max(0.01, (next_stage["min_intimacy"] - stage["min_intimacy"])) if next_stage else 1.0
             ),
         }
 
     def missed_you_chance(self) -> float:
         """计算"想你了"的概率
         
         关系越亲密、默契度越高、近期正面互动多 -> 越容易表达思念
         """
         ctx = self.get_relationship_context()
         base_prob = ctx["connection_depth"] * 0.3
         gottman_bonus = min(0.3, ctx["gottman_ratio"] * 0.2)
         intimacy_bonus = ctx["intimacy"] * 0.2
         baggage_penalty = ctx["baggage"] * 0.2
 
         prob = base_prob + gottman_bonus + intimacy_bonus - baggage_penalty
         return max(0.0, min(1.0, prob))
 
     # ========== 统计 ==========
     def stats(self) -> dict:
         return {
             "stage": self.data["stage"],
             "intimacy": round(self.data["intimacy"], 3),
             "connection_depth": round(self.data["connection_depth"], 3),
             "gottman_ratio": round(self.data["gottman_ratio"], 3),
             "baggage": round(self.data["baggage"], 3),
             "milestones": len(self.data["milestones"]),
             "total_interactions": self.data["meta"]["total_interactions"],
         }
