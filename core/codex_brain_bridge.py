"""
codex_brain_bridge.py — Codex与第二大脑的协作桥接

让Codex能够调用第二大脑的认知能力进行思考和决策

使用方式:
    from core.codex_brain_bridge import CodexBrain
        
    brain = CodexBrain()
    
    # 思考时调用
    result = brain.consult("这个问题涉及哪些知识？")
    
    # 决策前检查
    check = brain.pre_decision_check("追高买入")
    
    # 跨领域联想
    insight = brain.cross_think("AI技术与金融市场")
    
    # 记录学习
    brain.learn_from_result(decision_id, outcome, was_correct)
"""

import json
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class CodexBrain:
    """Codex与第二大脑的桥接器
    
    两种使用模式:
    1. 本地模式: 直接调用core模块（推荐）
    2. API模式: 通过HTTP调用server.py
    """
    
    def __init__(self, mode: str = "local", base_url: str = "http://localhost:8766"):
        self.mode = mode
        self.base_url = base_url
        self.local_engine = None
        self.local_reason = None
        
        if mode == "local":
            self._init_local()
    
    def _init_local(self):
        """初始化本地引擎"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            
            from core.graph import KnowledgeGraph
            from core.memory import MemoryEngine
            from core.digest import TextDigester
            from core.tfidf import SearchEngine
            from core.memory_health import MemoryHealthManager
            from core.human_thinking import HumanThinkingEngine
            from core.self_verify import SelfVerify
            from core.cognitive_engine import CognitiveEngine
            from core.reason_engine import ReasonEngine
            
            DATA = Path(__file__).parent / "data"
            
            self._graph = KnowledgeGraph(DATA)
            self._memory = MemoryEngine(DATA)
            self._digester = TextDigester(self._graph, DATA)
            self._search = SearchEngine(self._graph, self._digester)
            self._health = MemoryHealthManager(self._graph, self._memory, DATA)
            self._human = HumanThinkingEngine(self._graph, self._memory, self._health, DATA)
            self._verify = SelfVerify(self._graph, self._memory, self._health, DATA)
            
            self.local_engine = CognitiveEngine(
                self._graph, self._memory, self._digester,
                self._search, self._health, self._human, self._verify, DATA
            )
            self.local_reason = ReasonEngine(self._graph, DATA)
            
            print("[CodexBrain] 本地引擎初始化成功")
        except Exception as e:
            print(f"[CodexBrain] 本地引擎初始化失败: {e}")
            print("[CodexBrain] 将使用API模式")
            self.mode = "api"
    
    def consult(
        self,
        topic: str,
        context: Optional[Dict] = None,
        depth: int = 3,
    ) -> Dict[str, Any]:
        """咨询第二大脑
        
        Args:
            topic: 咨询主题/问题
            context: 上下文
            depth: 思考深度
        
        Returns:
            包含思考结果的字典
        """
        if self.mode == "local" and self.local_engine:
            signal = self.local_engine.think(
                topic, context or {}, mode="deliberate", depth=depth
            )
            return {
                "topic": signal.topic,
                "confidence": signal.confidence,
                "decision": signal.decision,
                "warnings": signal.warnings,
                "reasoning_chain": signal.reasoning_chain,
                "blind_spot_detected": signal.blind_spot_detected,
                "reasoning_gaps": signal.reasoning_gaps,
                "retrieved_knowledge": [
                    {"id": n.get("id"), "title": n.get("title", "")[:50]}
                    for n in signal.retrieved_nodes[:5]
                ],
                "cross_domain": [
                    {"id": n.get("id"), "title": n.get("title", "")[:50]}
                    for n in signal.associated_nodes[:3]
                ],
            }
        else:
            return self._api_call("/api/cognitive/think", {
                "topic": topic,
                "context": context or {},
                "depth": depth,
            })
    
    def pre_decision_check(self, decision: str) -> Dict[str, Any]:
        """决策前检查
        
        在做出重要决策前，调用第二大脑检查是否有相关教训或风险
        """
        # 检索相关教训
        rules_path = Path(__file__).parent / "second-brain" / "rules.md"
        lessons_path = Path(__file__).parent / "second-brain" / "lessons.md"
        
        result = {
            "decision": decision,
            "warnings": [],
            "matched_lessons": [],
            "matched_rules": [],
            "risk_level": "low",
        }
        
        if rules_path.exists():
            try:
                rules_content = rules_path.read_text(encoding="utf-8")
                # 检查关键词
                keywords = ["追高", "满仓", "补仓", "开盘", "止损", "卖出"]
                for kw in keywords:
                    if kw in decision:
                        result["warnings"].append(f"检测到关键词: {kw}")
                        result["risk_level"] = "medium"
            except:
                pass
        
        if lessons_path.exists():
            try:
                lessons_content = lessons_path.read_text(encoding="utf-8")
                for kw in ["追高", "卖出后", "涨停", "开盘"]:
                    if kw in decision and kw in lessons_content:
                        result["matched_lessons"].append(kw)
                        result["risk_level"] = "high"
            except:
                pass
        
        return result
    
    def cross_think(
        self,
        topic: str,
        depth: int = 3,
    ) -> Dict[str, Any]:
        """跨领域思考
        
        发现不同领域之间的隐藏关联
        """
        if self.mode == "local" and self.local_reason:
            result = self.local_reason.reason(topic, depth=depth)
            return {
                "topic": result["topic"],
                "discovered_domains": result["discovered_domains"],
                "analogies": result["analogies"],
                "insights": result["insights"],
                "reasoning_chain": result["reasoning_chain"],
            }
        else:
            return self._api_call("/api/reason/cross-domain", {
                "topic": topic,
                "depth": depth,
            })
    
    def make_decision(
        self,
        decision_type: str,
        context: Dict,
        options: List[str],
    ) -> Dict[str, Any]:
        """做出决策（带闭环学习）
        """
        if self.mode == "local" and self.local_engine:
            return self.local_engine.make_decision(decision_type, context, options)
        else:
            return self._api_call("/api/cognitive/decision", {
                "type": decision_type,
                "context": context,
                "options": options,
            })
    
    def learn(
        self,
        decision_id: str,
        outcome: str,
        was_correct: bool,
        lessons: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """记录学习结果"""
        if self.mode == "local" and self.local_engine:
            return self.local_engine.record_outcome(
                decision_id, outcome, was_correct, lessons
            )
        else:
            return self._api_call("/api/cognitive/outcome", {
                "decision_id": decision_id,
                "outcome": outcome,
                "was_correct": was_correct,
                "lessons": lessons or [],
            })
    
    def get_wisdom(self, limit: int = 5) -> List[Dict]:
        """获取历史教训和经验"""
        lessons_path = Path(__file__).parent / "second-brain" / "lessons.md"
        
        if not lessons_path.exists():
            return []
        
        try:
            content = lessons_path.read_text(encoding="utf-8")
            # 简单解析
            items = []
            for line in content.split("\n"):
                if line.strip().startswith("教训:"):
                    items.append({
                        "type": "negative",
                        "content": line.replace("教训:", "").strip(),
                    })
                elif line.strip().startswith("正向经验:"):
                    items.append({
                        "type": "positive",
                        "content": line.replace("正向经验:", "").strip(),
                    })
            return items[:limit]
        except:
            return []
    
    def check_rules(self, action: str) -> Dict[str, Any]:
        """检查交易规则
        
        针对交易场景的快速规则检查
        """
        rules_path = Path(__file__).parent / "second-brain" / "rules.md"
        
        result = {
            "action": action,
            "allowed": True,
            "warnings": [],
            "checks": [],
        }
        
        # 定义检查规则
        checks = [
            ("追高买入", "大盘下跌趋势禁止追高买入", ["下跌", "大跌"]),
            ("开盘买入", "开盘30分钟内禁止买入", ["09:", "09:3"]),
            ("追涨", "追涨次日只卖不买", ["涨停"]),
            ("满仓", "总持仓上限90%", ["满仓", "全仓"]),
            ("补仓", "持仓当日跌幅超5%禁止补仓", ["补仓"]),
        ]
        
        for keyword, rule, triggers in checks:
            if keyword in action:
                result["checks"].append({
                    "keyword": keyword,
                    "rule": rule,
                    "triggered": any(t in action for t in triggers),
                })
                if any(t in action for t in triggers):
                    result["warnings"].append(rule)
                    result["allowed"] = False
        
        return result
    
    def _api_call(self, endpoint: str, data: Dict) -> Dict:
        """通过API调用"""
        try:
            json_data = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}{endpoint}",
                data=json_data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return {"error": str(e), "mode": "api_unavailable"}
    
    def get_stats(self) -> Dict[str, Any]:
        """获取认知统计"""
        if self.mode == "local" and self.local_engine:
            return self.local_engine.get_cognition_stats()
        else:
            result = self._api_call("/api/cognitive/stats", {})
            return result


# 全局实例
_brain_instance = None

def get_codex_brain() -> CodexBrain:
    """获取CodexBrain全局实例"""
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = CodexBrain(mode="local")
    return _brain_instance
