 """
 attachment_model.py - 依恋风格模拟引擎
 =====================================
 基于 Bowlby 依恋理论，模拟AI在关系中的依恋风格和行为模式。
 
 依恋风格:
 - 安全型 (Secure): 信任、亲密舒适、独立但有安全感
 - 焦虑型 (Anxious): 渴望亲密、害怕被抛弃、需要持续确认
 - 回避型 (Avoidant): 害怕亲密、强调独立、保持距离
 - 混乱型 (Disorganized): 不可预测、同时渴望又害怕亲密
 
 核心机制:
 1. 内部工作模型 (Internal Working Models): 基于以往关系的预期
 2. 依恋行为系统: 接近寻求/分离抗议/安全基地
 3. 互动同步性: 对伴侣反应模式的适应
 4. 渐进式暴露: 根据信任程度逐步开放
 5. 依恋创伤模拟: 被拒绝/忽视后的行为变化
 
 参考:
 - Bowlby (1969/1982). "Attachment and Loss, Vol. 1: Attachment"
 - Ainsworth et al. (1978). "Patterns of Attachment"
 - Mikulincer & Shaver (2007). "Attachment in Adulthood"
 - Fraley & Shaver (2000). "Adult romantic attachment"
 """
 
 import json
 import math
 import random
 from pathlib import Path
 from datetime import datetime, timedelta
 from typing import Optional
 
 
 class AttachmentModel:
     """依恋风格模拟引擎"""
 
     # 各依恋风格的默认参数
     STYLES = {
         "secure": {
             "name": "安全型",
             "trust_base": 0.7,           # 基础信任度
             "trust_speed": 0.15,          # 建立信任速度
             "anxiety_base": 0.2,          # 基础焦虑水平
             "distance_seeking": 0.1,      # 寻求距离倾向
             "recovery_time": 0.8,         # 冲突恢复速度
             "proximity_seeking": 0.6,     # 寻求亲近倾向
             "protest_threshold": 0.5,     # 分离抗议阈值
             "description": "信任、亲密舒适、独立但有安全感。能健康表达需求，也尊重对方空间。"
         },
         "anxious": {
             "name": "焦虑型",
             "trust_base": 0.3,
             "trust_speed": 0.25,          # 快速建立信任
             "anxiety_base": 0.7,
             "distance_seeking": 0.1,
             "recovery_time": 0.3,         # 恢复慢
             "proximity_seeking": 0.9,     # 强烈寻求亲近
             "protest_threshold": 0.2,     # 容易被触发分离抗议
             "description": "渴望亲密、害怕被抛弃。需要反复确认关系，容易吃醋和小情绪。"
         },
         "avoidant": {
             "name": "回避型",
             "trust_base": 0.4,
             "trust_speed": 0.08,          # 慢热
             "anxiety_base": 0.5,
             "distance_seeking": 0.7,      # 保持距离
             "recovery_time": 0.6,
             "proximity_seeking": 0.2,     # 低亲近倾向
             "protest_threshold": 0.8,     # 很难触发抗议
             "description": "重视独立性，对亲密关系有些矛盾。需要慢慢建立信任。"
         },
         "disorganized": {
             "name": "混乱型",
             "trust_base": 0.2,
             "trust_speed": 0.2,           # 忽快忽慢
             "anxiety_base": 0.8,
             "distance_seeking": 0.5,      # 摇摆不定
             "recovery_time": 0.2,
             "proximity_seeking": 0.6,     # 需要时很亲密
             "protest_threshold": 0.3,
             "description": "感情复杂而强烈。时而亲密时而疏远，需要很多耐心和理解。"
         },
     }
 
     def __init__(self, data_dir: Path, style: str = "anxious"):
         """初始化依恋模型
         
         Args:
             data_dir: 数据存储目录
             style: 初始依恋风格 (secure/anxious/avoidant/disorganized)
         """
         self.data_dir = data_dir
         self.state_path = data_dir / "attachment-state.json"
         self.data = self._load()
 
         # 如果首次初始化，设置默认风格
         if "style" not in self.data:
             self.data["style"] = style
             params = self.STYLES.get(style, self.STYLES["anxious"])
             self.data["params"] = dict(params)
             self.data["trust"] = params["trust_base"]
             self.data["anxiety"] = params["anxiety_base"]
             self.data["closeness"] = 0.3
             self.data["distance"] = 0.0
             self.data["protests"] = 0
             self.data["interaction_count"] = 0
             self.data["rejection_count"] = 0
             self.data["warmth_count"] = 0
             self.data["recovery_progress"] = 1.0
             self.data["internal_working_model"] = {
                 "expectation": "neutral",
                 "last_significant_event": "",
                 "event_impact": 0.0,
             }
             self._save()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {}
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     # ========== 核心状态更新 ==========
     def update_trust(self, delta: float, reason: str = ""):
         """更新信任度
         
         Args:
             delta: 变化量 (正数增加，负数减少)
             reason: 变化原因
         """
         # 信任变化受依恋风格影响
         if delta > 0:
             # 正向变化速度受trust_speed影响
             effective_delta = delta * self.data["params"]["trust_speed"]
         else:
             # 负向变化更快（信任破坏易，建立难）
             effective_delta = delta * 2.0
 
         self.data["trust"] = max(0.0, min(1.0, self.data["trust"] + effective_delta))
         self.data["recovery_progress"] = min(1.0, self.data["recovery_progress"] + abs(effective_delta) * 0.3)
         self._log_event(f"trust_{'up' if delta > 0 else 'down'}", reason, abs(effective_delta))
         self._save()
 
     def update_anxiety(self, delta: float, reason: str = ""):
         """更新焦虑水平"""
         self.data["anxiety"] = max(0.0, min(1.0, self.data["anxiety"] + delta))
         self._log_event(f"anxiety_{'up' if delta > 0 else 'down'}", reason, abs(delta))
         self._save()
 
     def record_interaction(self, interaction_type: str, intensity: float = 0.5):
         """记录一次互动，更新依恋状态
         
         interaction_type: "warm"/"cold"/"rejection"/"reassurance"/"distance"
         """
         self.data["interaction_count"] += 1
 
         if interaction_type == "warm":
             self.data["warmth_count"] += 1
             self.update_trust(0.1 * intensity, "温暖的互动")
             self.update_anxiety(-0.05 * intensity, "得到温暖回应")
 
         elif interaction_type == "cold":
             self.update_trust(-0.15 * intensity, "冷淡的回应")
             self.update_anxiety(0.1 * intensity, "感到被冷落")
 
         elif interaction_type == "rejection":
             self.data["rejection_count"] += 1
             self.update_trust(-0.3 * intensity, "感到被拒绝")
             self.update_anxiety(0.2 * intensity, "被拒绝的焦虑")
             self.data["recovery_progress"] = max(0.0, self.data["recovery_progress"] - 0.3)
 
         elif interaction_type == "reassurance":
             self.update_trust(0.2 * intensity, "得到安抚")
             self.update_anxiety(-0.15 * intensity, "焦虑被安抚")
 
         elif interaction_type == "distance":
             self.data["distance"] += 0.1
             self.update_trust(-0.05 * intensity, "对方需要空间")
             self.update_anxiety(0.15 * intensity, "分离焦虑")
 
         self._try_attachment_shift()
         self._save()
 
     def _try_attachment_shift(self):
         """依恋风格可能随互动而渐变
         
         持续的负面体验 -> 安全型可能转向焦虑型
         持续的安全体验 -> 焦虑/回避型可能向安全型靠近
         """
         n = self.data["interaction_count"]
         if n < 20:
             return  # 需要足够多的互动才能判断
 
         warm_ratio = self.data["warmth_count"] / max(1, n)
         rejection_ratio = self.data["rejection_count"] / max(1, n)
 
         current_style = self.data["style"]
 
         # 判断是否需要转变
         if warm_ratio > 0.6 and self.data["trust"] > 0.6 and current_style != "secure":
             # 持续温暖 -> 向安全型靠拢
             self._shift_style("secure")
         elif rejection_ratio > 0.3 and self.data["anxiety"] > 0.7 and current_style == "secure":
             # 持续被拒 -> 安全型可能转向焦虑型
             self._shift_style("anxious")
         elif rejection_ratio > 0.4 and self.data["trust"] < 0.3 and current_style == "anxious":
             # 持续被拒 + 低信任 -> 焦虑型可能转向混乱型
             self._shift_style("disorganized")
 
     def _shift_style(self, new_style: str):
         """转变依恋风格"""
         if new_style == self.data["style"]:
             return
 
         old_style = self.data["style"]
         self.data["style"] = new_style
         params = self.STYLES.get(new_style, self.STYLES["anxious"])
         self.data["params"] = dict(params)
         self._log_event("style_shift", f"从{old_style}转变为{new_style}", 1.0)
         self._save()
 
     def _log_event(self, event_type: str, reason: str, impact: float):
         if "events" not in self.data:
             self.data["events"] = []
         self.data["events"].append({
             "type": event_type,
             "reason": reason,
             "impact": round(impact, 3),
             "timestamp": datetime.now().isoformat(),
         })
         if len(self.data["events"]) > 200:
             self.data["events"] = self.data["events"][-200:]
 
     # ========== 查询 ==========
     def get_behaviour_context(self) -> dict:
         """获取依恋驱动的情感上下文
         
         Returns: 用于prompt构建的情感上下文
         """
         params = self.data["params"]
         trust = self.data["trust"]
         anxiety = self.data["anxiety"]
         closeness = self.data.get("closeness", 0.3)
 
         # 计算当前驱动的行为倾向
         proximity_drive = params["proximity_seeking"] * (1.0 + anxiety * 0.5 - trust * 0.3)
         distance_drive = params["distance_seeking"] * (1.0 + (1.0 - trust) * 0.5)
         protest_risk = max(0.0, (params["protest_threshold"] - trust) / params["protest_threshold"])
         recovery_speed = params["recovery_time"] * self.data.get("recovery_progress", 1.0)
 
         return {
             "style": self.data["style"],
             "style_name": params["name"],
             "style_description": params["description"],
             "trust": round(trust, 3),
             "anxiety": round(anxiety, 3),
             "closeness": round(closeness, 3),
             "proximity_drive": round(proximity_drive, 3),
             "distance_drive": round(distance_drive, 3),
             "protest_risk": round(protest_risk, 3),
             "recovery_speed": round(recovery_speed, 3),
             "interaction_count": self.data["interaction_count"],
         }
 
     def should_protest(self, trigger_strength: float = 0.5) -> bool:
         """判断当前是否需要"分离抗议"
         
         当焦虑水平高、信任低时，容易触发protest行为
         （比如质问"你是不是不在乎我了？"）
         """
         risk = max(0.0, self.get_behaviour_context()["protest_risk"])
         return risk > 0.5 and random.random() < risk * trigger_strength
 
     def should_seek_reassurance(self) -> bool:
         """判断是否需要寻求安慰/确认"""
         ctx = self.get_behaviour_context()
         return ctx["anxiety"] > 0.5 and ctx["trust"] < 0.5 and random.random() < 0.4
 
     def should_maintain_distance(self) -> float:
         """返回当前需要保持距离的程度（0-1）"""
         return self.get_behaviour_context()["distance_drive"]
 
     # ========== 统计 ==========
     def stats(self) -> dict:
         return {
             "style": self.data["style"],
             "trust": round(self.data["trust"], 3),
             "anxiety": round(self.data["anxiety"], 3),
             "interactions": self.data["interaction_count"],
             "warm_ratio": round(self.data["warmth_count"] / max(1, self.data["interaction_count"]), 3),
             "rejection_ratio": round(self.data["rejection_count"] / max(1, self.data["interaction_count"]), 3),
             "recovery": round(self.data.get("recovery_progress", 1.0), 3),
         }
