 """
 closed_loop_learner.py - 闭环学习系统
 ===================================
 让第二大脑能从错误和反馈中自我改进，模拟人类从经验中学习的过程。
 
 核心机制:
 1. 错误分析 (Error Analysis): 结构化分析发生了什么以及为什么
 2. 根因定位 (Root Cause): 区分是知识缺失、推理错误还是表达问题
 3. 修复措施生成 (Fix Generation): 生成具体的改进方案
 4. 规则沉淀 (Rule Extraction): 从错误中提取可复用的规则
 5. 效果验证 (Effectiveness Check): 学习是否真的改善了行为
 6. 自动知识注入: 将学到的知识自动写入知识图谱
 """
 
 import json
 import uuid
 from pathlib import Path
 from datetime import datetime
 from typing import Optional
 
 
 class ClosedLoopLearner:
     """闭环学习系统 - 从错误中学习"""
 
     # 错误类型
     ERROR_CATEGORIES = {
         "knowledge_gap": "知识缺失 - 缺少相关的背景知识",
         "reasoning_error": "推理错误 - 逻辑链条存在问题",
         "context_misunderstanding": "上下文误解 - 没有正确理解场景",
         "expression_problem": "表达问题 - 表达方式不合适",
         "emotional_miss": "情感错位 - 没有感知到对方的情感需求",
         "social_faux_pas": "社交失礼 - 不符合社交规范",
         "memory_confusion": "记忆混乱 - 混淆了不同的记忆",
         "overconfidence": "过度自信 - 在不确定时给出了确定的答案",
     }
 
     def __init__(self, data_dir: Path):
         self.data_dir = data_dir
         self.state_path = data_dir / "closed-loop-state.json"
         self.data = self._load()
 
     def _load(self) -> dict:
         try:
             with open(self.state_path, "r", encoding="utf-8") as f:
                 return json.load(f)
         except (FileNotFoundError, json.JSONDecodeError):
             return {
                 "learned_rules": [],         # 学到的规则
                 "error_log": [],              # 错误日志
                 "fixes_applied": [],           # 已应用的修复
                 "effectiveness_log": [],       # 有效性记录
                 "meta": {
                     "total_errors": 0,
                     "total_rules": 0,
                     "successful_fixes": 0,
                     "failed_fixes": 0,
                 }
             }
 
     def _save(self):
         self.data_dir.mkdir(parents=True, exist_ok=True)
         with open(self.state_path, "w", encoding="utf-8") as f:
             json.dump(self.data, f, ensure_ascii=False, indent=2)
 
     def record_error(self, user_input: str, response: str,
                      feedback: str, category: str = "unknown") -> dict:
         """记录一次错误以供学习
         
         Args:
             user_input: 导致错误的用户输入
             response: AI的回应
             feedback: 用户反馈
             category: 错误分类
         
         Returns: 错误分析结果
         """
         # 自动分类（如果未指定）
         if category == "unknown":
             category = self._classify_error(user_input, response, feedback)
 
         # 错误分析
         analysis = {
             "id": str(uuid.uuid4())[:8],
             "timestamp": datetime.now().isoformat(),
             "user_input": user_input[:200],
             "response": response[:200],
             "feedback": feedback[:200],
             "category": category,
             "category_desc": self.ERROR_CATEGORIES.get(category, "未知类型"),
             "root_cause": self._analyze_root_cause(category, user_input, response),
             "severity": self._assess_severity(feedback),
             "rule_extracted": None,
             "fix_applied": False,
             "fix_effective": None,
         }
 
         self.data["error_log"].append(analysis)
         self.data["meta"]["total_errors"] += 1
 
         # 自动提取规则
         rule = self._extract_rule(analysis)
         if rule:
             analysis["rule_extracted"] = rule["id"]
 
         self._save()
         return analysis
 
     def _classify_error(self, user_input: str, response: str, feedback: str) -> str:
         """自动分类错误类型（基于关键词）"""
         keywords = {
             "knowledge_gap": ["不知道", "没听过", "不懂", "错了", "不对", "不是这样的"],
             "reasoning_error": ["逻辑不对", "想错了", "推理", "因果", "矛盾"],
             "context_misunderstanding": ["没明白", "误会", "没理解", "我说的是", "不是这个意思"],
             "expression_problem": ["太直接", "太生硬", "表达", "语气", "说得不好"],
             "emotional_miss": ["冷", "不关心", "不在乎", "没感情", "机械"],
             "social_faux_pas": ["不合适", "冒犯", "失礼", "过分", "不妥"],
             "memory_confusion": ["不是这样的", "之前说", "你忘了", "记错"],
             "overconfidence": ["确定吗", "真的假的", "不对吧", "你确定"],
         }
 
         best_match = "reasoning_error"
         best_score = 0
         combined = user_input + " " + response + " " + feedback
 
         for cat, words in keywords.items():
             score = sum(1 for w in words if w in combined)
             if score > best_score:
                 best_score = score
                 best_match = cat
 
         return best_match
 
     def _analyze_root_cause(self, category: str, user_input: str, response: str) -> str:
         """分析根因"""
         causes = {
             "knowledge_gap": "相关背景知识不足",
             "reasoning_error": "推理链条中存在跳跃或错误的假设",
             "context_misunderstanding": "没有充分理解用户的上文语境",
             "expression_problem": "表达时缺乏对社交语境的考量",
             "emotional_miss": "注意力过度集中在事实层面，忽略了情感层面",
             "social_faux_pas": "对当前社交关系的阶段判断有误",
             "memory_confusion": "长期记忆检索时匹配到了错误的记忆",
             "overconfidence": "在没有足够证据时做出了确定性的陈述",
         }
         return causes.get(category, "需要进一步分析")
 
     def _assess_severity(self, feedback: str) -> str:
         """评估错误严重程度"""
         high = ["差", "坏", "滚", "错", "气", "恨", "失望", "伤心", "怒"]
         medium = ["不对", "不好", "不行", "不是", "不对", "不太对"]
 
         severity_score = sum(1 for w in high if w in feedback)
         if severity_score >= 2:
             return "severe"
         elif severity_score >= 1 or any(w in feedback for w in medium):
             return "moderate"
         return "minor"
 
     def _extract_rule(self, error: dict) -> Optional[dict]:
         """从错误中提取可复用的规则"""
         category = error["category"]
         root_cause = error["root_cause"]
 
         rule_templates = {
             "knowledge_gap": {
                 "rule": f"当遇到{error['user_input'][:30]}...相关问题时，如果知识不足，应该先检索知识库而不是猜测",
                 "domain": "knowledge",
             },
             "emotional_miss": {
                 "rule": "在用户表达情感时，优先回应情感层面，再处理事实内容",
                 "domain": "emotion",
             },
             "context_misunderstanding": {
                 "rule": "在不确定用户意图时，先确认理解再作答",
                 "domain": "communication",
             },
             "overconfidence": {
                 "rule": "在不确定时，明确表达不确定性并提供参考来源",
                 "domain": "knowledge",
             },
             "social_faux_pas": {
                 "rule": "表达批评或意见时，先肯定再建议",
                 "domain": "social",
             },
             "memory_confusion": {
                 "rule": "检索到多个相关记忆时，对比时间戳选择最新的",
                 "domain": "memory",
             },
         }
 
         template = rule_templates.get(category)
         if not template:
             return None
 
         # 检查是否已有类似规则
         for existing in self.data["learned_rules"]:
             if existing["domain"] == template["domain"] and category == existing.get("error_type"):
                 # 已有类似规则，强化
                 existing["strength"] = min(1.0, existing.get("strength", 0.5) + 0.1)
                 existing["reinforced_count"] = existing.get("reinforced_count", 1) + 1
                 existing["last_reinforced"] = datetime.now().isoformat()
                 self._save()
                 return existing
 
         # 创建新规则
         rule = {
             "id": f"rule-{uuid.uuid4().hex[:8]}",
             "rule": template["rule"],
             "domain": template["domain"],
             "error_type": category,
             "source_error": error["id"],
             "strength": 0.5,
             "reinforced_count": 1,
             "created_at": datetime.now().isoformat(),
             "last_reinforced": datetime.now().isoformat(),
             "is_active": True,
         }
 
         self.data["learned_rules"].append(rule)
         self.data["meta"]["total_rules"] += 1
         self._save()
         return rule
 
     def record_fix(self, error_id: str, fix_description: str, success: bool):
         """记录一次修复尝试"""
         self.data["fixes_applied"].append({
             "error_id": error_id,
             "fix": fix_description,
             "success": success,
             "applied_at": datetime.now().isoformat(),
         })
 
         if success:
             self.data["meta"]["successful_fixes"] += 1
             # 更新对应规则
             for rule in self.data["learned_rules"]:
                 if rule.get("source_error") == error_id:
                     rule["is_active"] = True
         else:
             self.data["meta"]["failed_fixes"] += 1
 
         self._save()
 
     def get_relevant_rules(self, context: dict) -> list:
         """获取与当前上下文相关的学到的规则"""
         rules = []
         for rule in self.data["learned_rules"]:
             if not rule.get("is_active", True):
                 continue
             # 简单的域匹配
             domain = context.get("domain", "")
             if domain and rule["domain"] == domain:
                 rules.append(rule)
 
         # 按强度排序
         rules.sort(key=lambda r: r.get("strength", 0), reverse=True)
         return rules[:5]
 
     def get_learning_summary(self) -> dict:
         """获取学习摘要"""
         return {
             "total_errors": self.data["meta"]["total_errors"],
             "rules_extracted": self.data["meta"]["total_rules"],
             "success_rate": round(
                 self.data["meta"]["successful_fixes"] /
                 max(1, self.data["meta"]["successful_fixes"] + self.data["meta"]["failed_fixes"]),
                 3
             ),
             "error_breakdown": dict(
                 (cat, sum(1 for e in self.data["error_log"] if e["category"] == cat))
                 for cat in self.ERROR_CATEGORIES
             ),
         }
 
     def stats(self) -> dict:
         return {
             "total_errors": self.data["meta"]["total_errors"],
             "total_rules": self.data["meta"]["total_rules"],
             "successful_fixes": self.data["meta"]["successful_fixes"],
             "active_rules": sum(1 for r in self.data["learned_rules"] if r.get("is_active", True)),
         }
