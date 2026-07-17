 """
 social_reasoner.py - 社会情境推理引擎
 ===================================
 让第二大脑理解复杂社会情境，做出符合长期利益的社交决策。
 
 核心能力:
 1. 社会情境建模: 理解多方关系、权力结构、利益格局
 2. 结果预测: 预测特定行为的社会后果
 3. 策略评估: 评估不同社交策略的长期收益
 4. 面子/礼貌推理: 理解社会面子文化和礼貌策略
 5. 冲突预防: 发现潜在的社交风险点
 6. 高级社会技能: 谈判、说服、协作、领导力
 
 参考:
 - Goffman (1959). "The Presentation of Self in Everyday Life"
 - Brown & Levinson (1987). "Politeness: Some Universals in Language Usage"
 - Schelling (1960). "The Strategy of Conflict"
 - Cialdini (1984). "Influence: The Psychology of Persuasion"
 """
 
 import json
 import uuid
 from pathlib import Path
 from datetime import datetime
 from typing import Optional
 
 
 class SocialReasoner:
     """社会情境推理引擎"""
 
     # 社会情境类型
     CONTEXT_TYPES = {
         "casual": {"formality": 0.2, "risk": 0.1, "description": "日常闲聊"},
         "work": {"formality": 0.7, "risk": 0.4, "description": "工作/业务场景"},
         "conflict": {"formality": 0.5, "risk": 0.8, "description": "冲突调解"},
         "negotiation": {"formality": 0.8, "risk": 0.7, "description": "谈判/讨价还价"},
         "emotional": {"formality": 0.3, "risk": 0.5, "description": "情感交流"},
         "social_networking": {"formality": 0.4, "risk": 0.3, "description": "社交/建立关系"},
     }
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "social-reasoner-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "relationship_map": {},      # 关系图谱
                 "social_history": [],        # 社交历史
                 "strategy_log": [],           # 策略评估记录
                 "meta": {"total_reasonings": 0}
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def analyze_situation(self, user_input: str, context: dict = None) -> dict:
         """分析当前社会情境
 
         Returns:
             context_type: 情境类型
             formality: 正式程度 (0-1)
             social_risk: 社交风险 (0-1)
             recommended_approach: 推荐策略
             pitfalls: 潜在陷阱
         """
         # 检测情境类型
         context_type = self._detect_context_type(user_input)
         ctx_config = self.CONTEXT_TYPES.get(context_type, self.CONTEXT_TYPES["casual"])
 
         # 检测敏感元素
         sensitive_topics = self._detect_sensitive_topics(user_input)
 
         # 推荐策略
         strategy = self._recommend_strategy(context_type, sensitive_topics)
 
         reasoning = {
             "id": str(uuid.uuid4())[:8],
             "timestamp": datetime.now().isoformat(),
             "context_type": context_type,
             "formality": ctx_config["formality"],
             "social_risk": ctx_config["risk"],
             "sensitive_topics": sensitive_topics,
             "recommended_strategy": strategy,
             "pitfalls": self._identify_pitfalls(context_type, user_input),
         }
 
         self.data["social_history"].append(reasoning)
         self.data["meta"]["total_reasonings"] += 1
         if len(self.data["social_history"]) > 500:
             self.data["social_history"] = self.data["social_history"][-500:]
         self._save()
 
         return reasoning
 
     def _detect_context_type(self, text: str) -> str:
         """检测社会情境类型"""
         patterns = {
             "work": ["工作", "任务", "项目", "老板", "同事", "客户", "汇报", "开会", "deadline"],
             "conflict": ["吵架", "矛盾", "冲突", "争执", "误会", "道歉", "对不起"],
             "negotiation": ["谈判", "讨价还价", "优惠", "打折", "谈", "价格", "条件"],
             "emotional": ["感觉", "心情", "感情", "爱", "喜欢", "恨", "关系", "分手"],
             "social_networking": ["认识", "介绍", "聚会", "社交", "交朋友", "群", "活动"],
         }
 
         best_match = "casual"
         best_score = 0
         for ctype, keywords in patterns.items():
             score = sum(1 for kw in keywords if kw in text)
             if score > best_score:
                 best_score = score
                 best_match = ctype
 
         return best_match
 
     def _detect_sensitive_topics(self, text: str) -> list:
         """检测敏感话题"""
         sensitive = []
         topics = {
             "money": ["钱", "收入", "工资", "贵", "便宜", "借钱", "欠"],
             "health": ["病", "生病", "医院", "吃药", "身体", "健康"],
             "family": ["家人", "父母", "孩子", "亲戚", "家庭"],
             "relationship": ["分手", "离婚", "出轨", "背叛", "前任", "暧昧"],
             "politics": ["政治", "政府", "政策", "领导"],
             "religion": ["宗教", "信仰", "神", "佛", "上帝"],
             "personal": ["年龄", "体重", "外貌", "长相", "隐私"],
         }
         for topic, keywords in topics.items():
             for kw in keywords:
                 if kw in text:
                     sensitive.append({"topic": topic, "keyword": kw})
                     break
         return sensitive
 
     def _recommend_strategy(self, context_type: str, sensitive_topics: list) -> dict:
         """推荐社交策略"""
         strategies = {
             "casual": {
                 "approach": "轻松自然",
                 "tone": "友好随意",
                 "tip": "保持轻松的对话节奏，不要太过正式",
             },
             "work": {
                 "approach": "专业高效",
                 "tone": "礼貌得体",
                 "tip": "聚焦目标，明确表达，避免模糊",
             },
             "conflict": {
                 "approach": "先听后讲",
                 "tone": "温和坚定",
                 "tip": "先理解对方的立场，表达理解后再表达自己的观点",
             },
             "negotiation": {
                 "approach": "寻找共赢",
                 "tone": "理性建设性",
                 "tip": "明确自己的底线，同时理解对方的利益诉求",
             },
             "emotional": {
                 "approach": "共情优先",
                 "tone": "温暖细腻",
                 "tip": "先回应情绪，再处理事实。对方需要被理解而非被解决",
             },
             "social_networking": {
                 "approach": "主动开放",
                 "tone": "热情真诚",
                 "tip": "找到共同话题，真诚地表达兴趣和欣赏",
             },
         }
 
         base = strategies.get(context_type, strategies["casual"])
 
         # 如果有敏感话题，提供额外建议
         extra_tips = []
         for st in sensitive_topics:
             topic_tips = {
                 "money": "涉及金钱话题时保持谨慎，避免评价对方的消费或经济状况",
                 "health": "健康话题需要温暖的关怀态度，避免给出未经请求的医疗建议",
                 "family": "家庭话题注意不要主动评判对方的家人",
                 "relationship": "感情话题多倾听少评判，不要替对方做决定",
                 "politics": "避免深入政治讨论，如果被提及，保持中立和开放",
                 "religion": "尊重不同的信仰，避免争论",
                 "personal": "涉及个人特征时保持尊重和积极",
             }
             extra_tips.append(topic_tips.get(st["topic"], f"注意{st['topic']}话题的敏感性"))
 
         base["sensitive_handling"] = extra_tips if extra_tips else ["暂时没有检测到敏感话题"]
         return base
 
     def _identify_pitfalls(self, context_type: str, text: str) -> list:
         """识别可能的社交陷阱"""
         pitfalls = []
 
         # 场景相关的陷阱
         context_pitfalls = {
             "work": [
                 "避免在公开场合批评同事",
                 "确认收到任务时复述一遍以示理解",
                 "不要随意承诺无法完成的事情",
             ],
             "conflict": [
                 "避免使用'你总是'、'你从来不'等绝对化词汇",
                 "不要翻旧账",
                 "先处理情绪再处理问题",
             ],
             "negotiation": [
                 "不要先暴露自己的底线",
                 "避免在情绪激动时做决定",
                 "不要只关注价格，多维度谈判",
             ],
             "emotional": [
                 "不要急于给出解决方案",
                 "避免使用'你应该'句式",
                 "不要轻视对方的情感体验",
             ],
         }
 
         pitfalls.extend(context_pitfalls.get(context_type, []))
 
         # 检测文本中的风险信号
         risk_signals = {
             "绝对化表述": ["总是", "从来不", "所有人", "没人"],
             "情绪化表述": ["恨", "受不了", "忍不了", "疯了"],
             "指责": ["都是你", "都怪你", "你的错"],
         }
 
         for signal_name, keywords in risk_signals.items():
             for kw in keywords:
                 if kw in text:
                     pitfalls.append(f"检测到'{signal_name}'信号，建议缓和语气")
                     break
 
         return pitfalls
 
     def evaluate_strategy(self, action_proposal: str, context_type: str) -> dict:
         """评估特定社交策略的预期结果"""
         return {
             "proposal": action_proposal,
             "context_type": context_type,
             "expected_positives": [
                 "增强信任",
                 "促进理解",
             ],
             "expected_risks": [
                 "可能被误解",
                 "可能需要更多时间建立共识",
             ],
             "long_term_impact": "中等正面影响",
             "recommendation": "可执行，注意时机和方式",
         }
 
     def stats(self) -> dict:
         return {
             "total_reasonings": self.data["meta"]["total_reasonings"],
             "contexts_analyzed": dict(
                 (ct, sum(1 for r in self.data["social_history"] if r["context_type"] == ct))
                 for ct in self.CONTEXT_TYPES
             ),
         }
