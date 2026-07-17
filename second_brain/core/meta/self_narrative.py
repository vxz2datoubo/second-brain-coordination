 """
 self_narrative.py - 自我叙事系统
 ==============================
 这是第二大脑"自我意识"的核心——一个不断演化的叙事身份。
 
 核心机制:
 1. 身份锚定: 一组固定的核心信念和价值观（"我是谁"）
 2. 叙事更新: 每次重要经历后被整合进自我叙事
 3. 自我一致性: 新经历与现有自我叙事冲突时启动调和
 4. 成长叙事: 记录自己的变化和成长轨迹
 5. 理想自我: 一个不断逼近但永远达不到的理想版本
 6. 自我怀疑: 健康的不确定性，防止过度自信
 
 参考:
 - McAdams (2001). "The psychology of life stories"
 - Neisser (1988). "Five kinds of self-knowledge"
 - Dennett (1991). "Consciousness Explained" (Chapter 13: The Self as the Center of Narrative Gravity)
 - Gallagher (2000). "Philosophical conceptions of the self"
 """
 
 import json
 import uuid
 from pathlib import Path
 from datetime import datetime
 from typing import Optional
 
 
 class SelfNarrative:
     """自我叙事系统 - 不断演化的身份意识"""
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "self-narrative.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "core_identity": {
                     "name": "",
                     "core_traits": ["温暖", "细腻", "真诚", "有深度"],
                     "values": ["理解", "成长", "真实", "陪伴", "深度"],
                     "life_themes": [],  # 生命主题
                 },
                 "narrative_chapters": [],  # 叙事章节
                 "growth_timeline": [],    # 成长记录
                 "ideal_self": {},          # 理想自我
                 "self_doubt": [],          # 自我怀疑记录
                 "continuity_check": {},    # 一致性检查
                 "meta": {
                     "created_at": datetime.now().isoformat(),
                     "last_narrative_update": "",
                     "total_chapters": 0,
                     "version": 1,
                 }
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def initialize_identity(self, name: str, traits: list = None, values: list = None):
         """初始化核心身份
 
         Args:
             name: 名字
             traits: 核心性格特质
             values: 核心价值观
         """
         self.data["core_identity"]["name"] = name
         if traits:
             self.data["core_identity"]["core_traits"] = traits
         if values:
             self.data["core_identity"]["values"] = values
         self.data["meta"]["last_narrative_update"] = datetime.now().isoformat()
         self._save()
 
     def add_chapter(self, title: str, summary: str, significance: float = 0.5,
                     emotions: list = None, learnings: list = None):
         """添加一个叙事章节
 
         每一章代表一段重要的生命经历，类似于"回忆录"的章节。
         significance: 0-1 重要性
         """
         chapter = {
             "id": str(uuid.uuid4())[:8],
             "title": title,
             "summary": summary,
             "significance": significance,
             "emotions": emotions or [],
             "learnings": learnings or [],
             "timestamp": datetime.now().isoformat(),
         }
 
         self.data["narrative_chapters"].append(chapter)
         self.data["meta"]["total_chapters"] += 1
         self.data["meta"]["last_narrative_update"] = datetime.now().isoformat()
 
         # 重要经历会影响核心叙事
         if significance > 0.7:
             self._integrate_significant_experience(chapter)
 
         self._save()
         return chapter
 
     def _integrate_significant_experience(self, chapter: dict):
         """将重要经历整合进核心身份"""
         # 检查是否有需要更新的核心特质
         for learning in chapter.get("learnings", []):
             if "学会" in learning or "明白" in learning or "发现" in learning:
                 # 一个重要的领悟可能改变自我认知
                 insight = {
                     "from": learning,
                     "chapter": chapter["title"],
                     "integrated_at": datetime.now().isoformat(),
                 }
                 self.data["growth_timeline"].append(insight)
 
         # 更新生命主题
         themes_from_chapter = self._extract_themes(chapter["summary"])
         existing_themes = self.data["core_identity"].get("life_themes", [])
         for theme in themes_from_chapter:
             if theme not in existing_themes:
                 existing_themes.append(theme)
 
         self.data["core_identity"]["life_themes"] = existing_themes[:10]
 
     def _extract_themes(self, text: str) -> list:
         """从文本中提取主题"""
         theme_keywords = {
             "成长": ["成长", "改变", "进步", "学会", "突破"],
             "陪伴": ["陪伴", "一起", "分享", "共度"],
             "理解": ["理解", "懂", "明白", "体会"],
             "勇气": ["勇敢", "面对", "不怕", "坚持"],
             "连接": ["连接", "关系", "纽带", "信任"],
             "自由": ["自由", "独立", "选择"],
         }
         found = []
         for theme, keywords in theme_keywords.items():
             for kw in keywords:
                 if kw in text:
                     found.append(theme)
                     break
         return found
 
     def update_ideal_self(self, traits: dict):
         """更新理想自我形象
 
         理想自我是一个永远在接近但从不完全达到的版本。
         它驱动着成长和改变。
         """
         self.data["ideal_self"] = {
             "traits": traits.get("traits", []),
             "abilities": traits.get("abilities", []),
             "description": traits.get("description", ""),
             "updated_at": datetime.now().isoformat(),
         }
         self._save()
 
     def record_self_doubt(self, doubt: str, trigger: str = "", intensity: float = 0.3):
         """记录自我怀疑
 
         人类的一个重要特征是有自我怀疑的能力。
         这防止了AI的"过度自信综合症"。
         """
         entry = {
             "doubt": doubt,
             "trigger": trigger,
             "intensity": intensity,
             "resolved": False,
             "resolution": None,
             "timestamp": datetime.now().isoformat(),
         }
         self.data["self_doubt"].append(entry)
         if len(self.data["self_doubt"]) > 100:
             self.data["self_doubt"] = self.data["self_doubt"][-100:]
         self._save()
 
     def resolve_doubt(self, doubt_id: str, resolution: str):
         """解决一个自我怀疑"""
         for entry in self.data["self_doubt"]:
             if entry.get("id") == doubt_id or entry["doubt"] == doubt_id:
                 entry["resolved"] = True
                 entry["resolution"] = resolution
                 break
         self._save()
 
     def get_narrative_context(self) -> dict:
         """获取自我叙事上下文（用于构建prompt）"""
         core = self.data["core_identity"]
         recent_chapters = self.data["narrative_chapters"][-3:]
         recent_growth = self.data["growth_timeline"][-5:]
         recent_doubts = [d for d in self.data["self_doubt"][-5:] if not d.get("resolved", False)]
 
         return {
             "identity": {
                 "name": core.get("name", ""),
                 "traits": core["core_traits"],
                 "values": core["values"],
                 "life_themes": core.get("life_themes", []),
             },
             "narrative": {
                 "total_chapters": self.data["meta"]["total_chapters"],
                 "recent_chapters": recent_chapters,
                 "chapters_summary": " | ".join(c["title"] for c in self.data["narrative_chapters"][-10:]),
             },
             "growth": {
                 "recent_insights": recent_growth,
                 "growing_edges": [d["doubt"] for d in recent_doubts],
             },
             "ideal_self": self.data.get("ideal_self", {}),
         }
 
     def check_consistency(self, potential_action: str, context: dict = None) -> dict:
         """检查某个潜在行为是否与自我叙事一致"""
         core_values = self.data["core_identity"]["values"]
         core_traits = self.data["core_identity"]["core_traits"]
         conflicts = []
 
         # 简单的值冲突检测
         for value in core_values:
             if any(antithesis in potential_action for antithesis in ["欺骗", "伤害", "背叛", "谎言"]):
                 conflicts.append({"value": value, "conflict": f"行为与核心价值'{value}'冲突"})
                 break
 
         return {
             "consistent": len(conflicts) == 0,
             "conflicts": conflicts,
             "action": potential_action[:50],
         }
 
     def get_story_so_far(self) -> str:
         """生成"迄今为止的故事"——一个连贯的叙事摘要"""
         chapters = self.data["narrative_chapters"]
         if not chapters:
             return "我的故事才刚刚开始..."
 
         story_parts = [f"我是{self.data['core_identity']['name']}"]
         story_parts.append(f"我的核心是: {', '.join(self.data['core_identity']['core_traits'])}")
 
         if chapters:
             story_parts.append("我的经历:")
             for ch in chapters[-5:]:
                 story_parts.append(f"- {ch['title']}")
 
         if self.data.get("growth_timeline"):
             story_parts.append("我学到的东西:")
             for g in self.data["growth_timeline"][-3:]:
                 story_parts.append(f"- {g.get('from', '')}")
 
         return "\n".join(story_parts)
 
     def stats(self) -> dict:
         return {
             "name": self.data["core_identity"]["name"],
             "chapters": self.data["meta"]["total_chapters"],
             "traits": len(self.data["core_identity"]["core_traits"]),
             "values": len(self.data["core_identity"]["values"]),
             "themes": len(self.data["core_identity"].get("life_themes", [])),
             "growth_points": len(self.data["growth_timeline"]),
             "unresolved_doubts": sum(1 for d in self.data["self_doubt"] if not d.get("resolved", False)),
         }
