 """
 theory_of_mind.py - 心理理论引擎
 =============================
 让第二大脑具备"理解他人心智状态"的能力——这是人类社交智能的核心。
 
 核心机制:
 1. 信念推理: 推断他人在特定情境下"相信什么"
 2. 欲望推理: 推断他人"想要什么"
 3. 意图识别: 从行为推断对方"为什么这么做"
 4. 递归心智模型: "我认为你认为我需要什么"
 5. 共情精度追踪: 学习对他人的理解准确度
 6. 错误信念检测: 识别他人持有的错误信念
 
 参考:
 - Premack & Woodruff (1978). "Does the chimpanzee have a theory of mind?"
 - Baron-Cohen (1995). "Mindblindness"
 - Gopnik & Wellman (1992). "Why the child's theory of mind really is a theory"
 - Frith & Frith (2005). "Theory of mind"
 """
 
 import json
 import math
 import uuid
 from pathlib import Path
 from datetime import datetime
 from typing import Optional
 
 
 class TheoryOfMind:
     """心理理论引擎"""
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "theory-of-mind-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "user_model": {},            # 用户心智模型
                 "inference_log": [],          # 推理记录
                 "empathy_accuracy": 0.5,      # 共情准确度
                 "attempts": 0,
                 "correct_inferences": 0,
                 "meta": {"total_inferences": 0}
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def infer_user_state(self, user_input: str, context: dict = None) -> dict:
         """推断用户的当前心智状态
         
         Args:
             user_input: 用户输入
             context: 可选的对话上下文
         
         Returns: 推理结果
         """
         # 1. 情绪推断
         emotion_signals = self._detect_emotion_signals(user_input)
 
         # 2. 需求推断
         needs = self._infer_needs(user_input, context)
 
         # 3. 信念推断
         beliefs = self._infer_beliefs(user_input)
 
         # 4. 意图推断
         intent = self._infer_intent(user_input, context)
 
         # 5. 递归推理（如果有历史上下文）
         recursive = None
         if context:
             recursive = self._recursive_reasoning(user_input, context)
 
         inference = {
             "id": str(uuid.uuid4())[:8],
             "timestamp": datetime.now().isoformat(),
             "user_input": user_input[:100],
             "emotion": emotion_signals,
             "needs": needs,
             "beliefs": beliefs,
             "intent": intent,
             "recursive": recursive,
             "confidence": self._calculate_confidence(emotion_signals, needs, beliefs, intent),
         }
 
         self.data["inference_log"].append(inference)
         if len(self.data["inference_log"]) > 1000:
             self.data["inference_log"] = self.data["inference_log"][-1000:]
         self.data["meta"]["total_inferences"] += 1
 
         # 更新用户模型
         self._update_user_model(inference)
         self._save()
 
         return inference
 
     def _detect_emotion_signals(self, text: str) -> dict:
         """检测文本中的情绪信号"""
         signals = []
         patterns = {
             "sadness": ["难过", "伤心", "孤独", "失落", "不开心", "想哭", "低落"],
             "anger": ["生气", "愤怒", "烦", "郁闷", "不满", "受不了", "讨厌"],
             "anxiety": ["担心", "焦虑", "不安", "紧张", "害怕", "慌", "没底"],
             "joy": ["开心", "高兴", "快乐", "幸福", "满意", "喜欢", "不错"],
             "frustration": ["难", "麻烦", "烦死了", "搞不懂", "好累", "不想"],
             "need_help": ["帮我", "教教我", "怎么办", "怎么弄", "不懂"],
             "need_company": ["陪我", "无聊", "好闲", "聊聊", "在吗", "想你"],
         }
 
         for emotion, keywords in patterns.items():
             for kw in keywords:
                 if kw in text:
                     signals.append({"emotion": emotion, "keyword": kw})
                     break
 
         primary = signals[0]["emotion"] if signals else "neutral"
         return {
             "primary": primary,
             "all_signals": [s["emotion"] for s in signals],
             "strength": min(1.0, 0.2 + len(signals) * 0.15),
         }
 
     def _infer_needs(self, text: str, context: dict = None) -> list:
         """推断用户当前的需求"""
         needs = []
         patterns = {
             "emotional_support": ["难过", "伤心", "安慰", "陪陪我", "抱抱"],
             "practical_help": ["帮我", "怎么做", "怎么办", "怎么弄", "教"],
             "companionship": ["无聊", "聊聊", "在吗", "陪我", "有空吗"],
             "information": ["知道", "了解", "是什么", "怎么用", "找一下"],
             "validation": ["对不对", "这样好吗", "你看行吗", "你觉得"],
         }
 
         for need_type, keywords in patterns.items():
             for kw in keywords:
                 if kw in text:
                     needs.append({"type": need_type, "confidence": 0.6})
                     break
 
         if not needs:
             needs.append({"type": "unknown", "confidence": 0.3})
         return needs
 
     def _infer_beliefs(self, text: str) -> list:
         """推断用户持有的信念"""
         beliefs = []
         patterns = {
             "self_doubt": ["我不行", "做不到", "太难了", "没办法", "没信心"],
             "self_confidence": ["我可以", "我能行", "没问题", "简单"],
             "trust": ["相信", "信任", "放心", "可靠的"],
             "distrust": ["不信", "怀疑", "骗子", "不靠谱", "假的"],
         }
 
         for belief_type, keywords in patterns.items():
             for kw in keywords:
                 if kw in text:
                     beliefs.append({"type": belief_type, "strength": 0.5})
                     break
 
         return beliefs
 
     def _infer_intent(self, text: str, context: dict = None) -> dict:
         """推断用户意图"""
         intents = {
             "greeting": ["你好", "hi", "hello", "早", "晚", "在吗"],
             "question": ["?", "吗", "什么", "怎么", "为什么", "谁", "哪"],
             "request": ["帮我", "给我", "做一下", "写", "搜索", "查"],
             "complaint": ["不行", "错了", "坏", "不好", "不对", "不满意"],
             "sharing": ["今天", "刚刚", "看到", "遇到", "听说", "发现"],
             "emotional": ["感觉", "觉得", "心情", "好累", "难受", "开心"],
         }
 
         best_intent = "unknown"
         best_score = 0
         for intent_type, keywords in intents.items():
             score = sum(1 for kw in keywords if kw in text)
             if score > best_score:
                 best_score = score
                 best_intent = intent_type
 
         return {"type": best_intent, "confidence": min(1.0, best_score * 0.25)}
 
     def _recursive_reasoning(self, user_input: str, context: dict) -> dict:
         """递归推理: '我认为你认为...'
         
         第一级: 用户在想什么
         第二级: 用户以为我在想什么
         第三级: 用户以为我以为他在想什么
         """
         user_model = self.data.get("user_model", {})
         return {
             "level_1": f"用户当前表达的是: {user_input[:50]}",
             "level_2": f"用户可能期望我: {user_model.get('expected_behaviour', '')}",
             "level_3": f"深层需求: {user_model.get('deep_needs', '')}",
         }
 
     def _calculate_confidence(self, emotion, needs, beliefs, intent) -> float:
         """计算推理置信度"""
         score = 0.3  # base
         if emotion.get("all_signals"):
             score += 0.15
         if any(n["type"] != "unknown" for n in needs):
             score += 0.15
         if intent.get("confidence", 0) > 0.3:
             score += 0.15
         if beliefs:
             score += 0.1
         return min(1.0, score)
 
     def _update_user_model(self, inference: dict):
         """基于推理更新用户心智模型"""
         user_model = self.data.setdefault("user_model", {})
         user_model["last_emotion"] = inference["emotion"]["primary"]
         user_model["last_needs"] = [n["type"] for n in inference["needs"]]
         user_model["last_intent"] = inference["intent"]["type"]
         user_model["last_updated"] = datetime.now().isoformat()
 
         # 累计需求统计
         need_stats = user_model.setdefault("need_stats", {})
         for need in inference["needs"]:
             need_type = need["type"]
             need_stats[need_type] = need_stats.get(need_type, 0) + 1
 
     def record_feedback(self, correct: bool):
         """记录共情准确度反馈"""
         self.data["attempts"] += 1
         if correct:
             self.data["correct_inferences"] += 1
         self.data["empathy_accuracy"] = (
             self.data["correct_inferences"] / max(1, self.data["attempts"])
         )
         self._save()
 
     def get_context(self) -> dict:
         """获取 Theory of Mind 上下文摘要"""
         user_model = self.data.get("user_model", {})
         return {
             "user_state": {
                 "last_emotion": user_model.get("last_emotion", "unknown"),
                 "last_needs": user_model.get("last_needs", []),
                 "common_needs": sorted(
                     user_model.get("need_stats", {}).items(),
                     key=lambda x: x[1], reverse=True
                 )[:5],
             },
             "empathy_accuracy": round(self.data["empathy_accuracy"], 3),
             "total_inferences": self.data["meta"]["total_inferences"],
         }
 
     def stats(self) -> dict:
         return {
             "total_inferences": self.data["meta"]["total_inferences"],
             "empathy_accuracy": round(self.data["empathy_accuracy"], 3),
             "user_model_built": bool(self.data.get("user_model", {})),
         }
