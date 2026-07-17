"""
maibot_bridge.py — 第二大脑与Maibot的桥接模块

让Maibot能够调用第二大脑的认知能力，实现:
1. Maibot发起请求 → 第二大脑决策 → 返回结果
2. 第二大脑发现问题 → 咨询Maibot → 获取反馈
3. 两者共享知识库和学习成果
"""

import json
import uuid
import httpx
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


class MaibotBridge:
    """第二大脑与Maibot的桥接器
    
    两种集成模式:
    1. 被动模式: Maibot调用第二大脑API获取决策支持
    2. 主动模式: 第二大脑遇到复杂问题，主动咨询Maibot
    """
    
    def __init__(self, cognitive_engine, reason_engine, data_dir: Path):
        self.cognitive = cognitive_engine
        self.reason = reason_engine
        self.data_dir = data_dir
        self.state_path = data_dir / "maibot_bridge_state.json"
        self.state = self._load()
        
        # Maibot连接配置
        self.maibot_url = "http://localhost:5000"  # Maibot默认端口
        self.sync_interval = 300  # 5分钟同步一次
    
    def _load(self) -> dict:
        try:
            with open(self.state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {
                "sync_history": [],
                "pending_questions": [],
                "shared_knowledge": [],
                "meta": {"last_sync": "", "total_syncs": 0}
            }
    
    def _save(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def think_with_maibot(
        self,
        topic: str,
        context: Optional[dict] = None,
        require_maibot_input: bool = False,
    ) -> dict:
        """与Maibot协作思考
        
        流程:
        1. 第二大脑先独立思考
        2. 如果需要Maibot输入，发送请求
        3. 合并结果
        """
        result = {
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "brain_thought": None,
            "maibot_input": None,
            "merged_result": None,
        }
        
        # 1. 第二大脑独立思考
        signal = self.cognitive.think(topic, context, mode="deliberate")
        result["brain_thought"] = {
            "confidence": signal.confidence,
            "decision": signal.decision,
            "warnings": signal.warnings,
            "reasoning_chain": signal.reasoning_chain,
        }
        
        # 2. 检查是否需要Maibot输入
        needs_maibot = (
            require_maibot_input or
            signal.confidence < 0.5 or
            len(signal.reasoning_gaps) > 2
        )
        
        if needs_maibot:
            # 记录需要Maibot输入
            question = {
                "id": str(uuid.uuid4())[:8],
                "topic": topic,
                "context": context,
                "brain_confidence": signal.confidence,
                "reasoning_gaps": signal.reasoning_gaps,
                "created_at": datetime.now().isoformat(),
            }
            self.state["pending_questions"].append(question)
            
            # 尝试调用Maibot
            maibot_response = self._call_maibot(topic, context)
            if maibot_response:
                result["maibot_input"] = maibot_response
                
                # 合并结果
                result["merged_result"] = self._merge_results(signal, maibot_response)
        
        self._save()
        return result
    
    def _call_maibot(self, topic: str, context: Optional[dict] = None) -> Optional[dict]:
        """调用Maibot获取输入"""
        try:
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    f"{self.maibot_url}/api/consult",
                    json={"question": topic, "context": context}
                )
                if response.status_code == 200:
                    return response.json()
        except:
            pass
        return None
    
    def _merge_results(
        self,
        brain_signal,
        maibot_response: dict
    ) -> dict:
        """合并第二大脑和Maibot的结果"""
        merged = {
            "topic": brain_signal.topic,
            "final_confidence": min(1.0, brain_signal.confidence + 0.2),
            "decisions": [brain_signal.decision],
            "sources": ["second_brain"],
            "reasoning": brain_signal.reasoning_chain,
        }
        
        if maibot_response:
            merged["final_confidence"] = min(1.0, brain_signal.confidence + 0.2)
            merged["decisions"].append(maibot_response.get("answer", ""))
            merged["sources"].append("maibot")
            merged["maibot_insight"] = maibot_response.get("insight", "")
        
        return merged
    
    def share_learned_rules(self) -> list:
        """共享第二大脑学习到的规则给Maibot"""
        rules = self.cognitive.get_learned_rules()
        
        shared = []
        for rule in rules:
            shared_rule = {
                "id": str(uuid.uuid4())[:8],
                "type": rule.get("type", ""),
                "lesson": rule.get("lesson", ""),
                "trigger": rule.get("trigger", {}),
                "created_at": rule.get("created_at", ""),
                "success_count": rule.get("success_count", 0),
                "failure_count": rule.get("failure_count", 0),
            }
            shared.append(shared_rule)
            self.state["shared_knowledge"].append(shared_rule)
        
        self._save()
        return shared
    
    def receive_feedback(
        self,
        question_id: str,
        feedback: dict,
    ) -> dict:
        """接收Maibot的反馈，更新知识库"""
        # 查找对应的问题
        question = None
        for q in self.state["pending_questions"]:
            if q.get("id") == question_id:
                question = q
                break
        
        if not question:
            return {"error": "question not found"}
        
        # 更新问题状态
        question["feedback"] = feedback
        question["resolved_at"] = datetime.now().isoformat()
        
        # 如果有学习内容，更新认知引擎
        if feedback.get("learned_rules"):
            for rule in feedback["learned_rules"]:
                self.cognitive.state["learned_patterns"][f"maibot_{rule['id']}"] = rule
        
        # 如果有教训，更新
        if feedback.get("lessons"):
            for lesson in feedback["lessons"]:
                self.cognitive._learn_from_error(
                    {"type": "maibot_consult", "context": question.get("context"), "chosen": "", "reasoning": ""},
                    lesson.get("outcome", ""),
                    [lesson.get("content", "")]
                )
        
        self._save()
        return {"success": True, "question_id": question_id}
    
    def sync_with_maibot(self) -> dict:
        """与Maibot同步知识和状态"""
        sync_result = {
            "timestamp": datetime.now().isoformat(),
            "shared_rules": 0,
            "received_rules": 0,
            "pending_questions_resolved": 0,
        }
        
        # 1. 分享学习到的规则
        shared = self.share_learned_rules()
        sync_result["shared_rules"] = len(shared)
        
        # 2. 尝试从Maibot获取新规则
        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.maibot_url}/api/rules/updates")
                if response.status_code == 200:
                    new_rules = response.json().get("rules", [])
                    for rule in new_rules:
                        self.cognitive.state["learned_patterns"][f"maibot_{rule['id']}"] = rule
                    sync_result["received_rules"] = len(new_rules)
        except:
            pass
        
        # 3. 清理已解决的问题
        before = len(self.state["pending_questions"])
        self.state["pending_questions"] = [
            q for q in self.state["pending_questions"]
            if not q.get("resolved_at")
        ]
        sync_result["pending_questions_resolved"] = before - len(self.state["pending_questions"])
        
        # 更新同步状态
        self.state["sync_history"].append(sync_result)
        self.state["meta"]["last_sync"] = datetime.now().isoformat()
        self.state["meta"]["total_syncs"] += 1
        self._save()
        
        return sync_result
    
    def get_bridge_status(self) -> dict:
        """获取桥接状态"""
        return {
            "connected": self._check_maibot_connection(),
            "pending_questions": len(self.state["pending_questions"]),
            "shared_knowledge_count": len(self.state["shared_knowledge"]),
            "last_sync": self.state["meta"].get("last_sync", ""),
            "total_syncs": self.state["meta"].get("total_syncs", 0),
        }
    
    def _check_maibot_connection(self) -> bool:
        """检查Maibot连接状态"""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.maibot_url}/api/health")
                return response.status_code == 200
        except:
            return False
