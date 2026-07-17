"""
decision_tree.py — 决策树推理引擎
用于情景模拟和后果推演
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict


@dataclass
class DecisionNode:
    id: str
    type: str  # "condition" | "action" | "outcome"
    description: str
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    probability: float = 1.0  # 到达此节点的概率
    value: float = 0.0  # 此节点的预期价值
    conditions: Dict = field(default_factory=dict)  # 如果是条件节点
    action: str = ""  # 如果是动作节点
    metadata: Dict = field(default_factory=dict)


@dataclass
class Scenario:
    id: str
    name: str
    description: str
    root_node_id: str
    nodes: Dict[str, Dict] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)


class DecisionTreeEngine:
    """决策树推理引擎"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.scenarios_dir = self.data_dir / "scenarios"
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.current_scenario = None
        self._node_counter = 0
    
    def _generate_node_id(self) -> str:
        self._node_counter += 1
        return f"node_{self._node_counter:04d}"
    
    def create_scenario(self, name: str, description: str = "", tags: Optional[List[str]] = None) -> str:
        import uuid
        scenario_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        
        scenario = Scenario(id=scenario_id, name=name, description=description, root_node_id="", created_at=now, updated_at=now, tags=tags or [])
        self.current_scenario = scenario
        return scenario_id
    
    def add_condition_node(self, description: str, conditions: Dict[str, Any], parent_id: Optional[str] = None) -> str:
        if not self.current_scenario:
            return ""
        
        node_id = self._generate_node_id()
        node = DecisionNode(id=node_id, type="condition", description=description, parent_id=parent_id, conditions=conditions)
        
        self.current_scenario.nodes[node_id] = asdict(node)
        
        if parent_id and parent_id in self.current_scenario.nodes:
            self.current_scenario.nodes[parent_id]["children"].append(node_id)
        elif not self.current_scenario.root_node_id:
            self.current_scenario.root_node_id = node_id
        
        return node_id
    
    def add_action_node(self, description: str, action: str, parent_id: Optional[str] = None, probability: float = 1.0, value: float = 0.0) -> str:
        if not self.current_scenario:
            return ""
        
        node_id = self._generate_node_id()
        node = DecisionNode(id=node_id, type="action", description=description, parent_id=parent_id, action=action, probability=probability, value=value)
        
        self.current_scenario.nodes[node_id] = asdict(node)
        
        if parent_id and parent_id in self.current_scenario.nodes:
            self.current_scenario.nodes[parent_id]["children"].append(node_id)
        
        return node_id
    
    def add_outcome_node(self, description: str, parent_id: Optional[str] = None, probability: float = 1.0, value: float = 0.0) -> str:
        if not self.current_scenario:
            return ""
        
        node_id = self._generate_node_id()
        node = DecisionNode(id=node_id, type="outcome", description=description, parent_id=parent_id, probability=probability, value=value)
        
        self.current_scenario.nodes[node_id] = asdict(node)
        
        if parent_id and parent_id in self.current_scenario.nodes:
            self.current_scenario.nodes[parent_id]["children"].append(node_id)
        
        return node_id
    
    def evaluate_conditions(self, conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
        for key, expected in conditions.items():
            actual = context.get(key)
            if isinstance(expected, dict):
                op = expected.get("op", "==")
                val = expected.get("value")
                if op == "==":
                    if actual != val:
                        return False
                elif op == ">":
                    if not (actual is not None and actual > val):
                        return False
                elif op == "<":
                    if not (actual is not None and actual < val):
                        return False
                elif op == ">=":
                    if not (actual is not None and actual >= val):
                        return False
                elif op == "<=":
                    if not (actual is not None and actual <= val):
                        return False
                elif op == "in":
                    if actual not in val:
                        return False
            else:
                if actual != expected:
                    return False
        return True
    
    def simulate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if not self.current_scenario or not self.current_scenario.root_node_id:
            return {"error": "No scenario loaded"}
        
        results = {"path": [], "outcomes": [], "total_value": 0.0, "probability": 1.0}
        
        def traverse(node_id: str, prob: float, value: float):
            node = self.current_scenario.nodes.get(node_id)
            if not node:
                return
            
            current_prob = prob * node.get("probability", 1.0)
            
            if node["type"] == "condition":
                if self.evaluate_conditions(node.get("conditions", {}), context):
                    results["path"].append({"node": node_id, "type": "condition", "result": "PASS", "probability": current_prob})
                    for child_id in node.get("children", []):
                        traverse(child_id, current_prob, value)
                else:
                    results["path"].append({"node": node_id, "type": "condition", "result": "FAIL", "probability": current_prob})
            
            elif node["type"] == "action":
                results["path"].append({"node": node_id, "type": "action", "action": node.get("action"), "probability": current_prob})
                new_value = value + node.get("value", 0)
                for child_id in node.get("children", []):
                    traverse(child_id, current_prob, new_value)
            
            elif node["type"] == "outcome":
                final_value = value + node.get("value", 0)
                results["outcomes"].append({"node": node_id, "description": node["description"], "probability": current_prob, "value": final_value})
                results["total_value"] += final_value * current_prob
        
        traverse(self.current_scenario.root_node_id, 1.0, 0.0)
        
        return results
    
    def save_scenario(self) -> bool:
        if not self.current_scenario:
            return False
        
        scenario_file = self.scenarios_dir / f"{self.current_scenario.id}.json"
        data = asdict(self.current_scenario)
        
        with open(scenario_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return True
    
    def load_scenario(self, scenario_id: str) -> Optional[Scenario]:
        scenario_file = self.scenarios_dir / f"{scenario_id}.json"
        if not scenario_file.exists():
            return None
        
        with open(scenario_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.current_scenario = Scenario(**data)
        return self.current_scenario
    
    def build_trading_scenario(self) -> str:
        """构建标准交易决策场景"""
        scenario_id = self.create_scenario("交易决策树", "标准A股T仓交易决策流程")
        
        # 根节点：市场状态判断
        mkt_node = self.add_condition_node(
            "市场状态评估",
            {"market_trend": {"op": "in", "value": ["TREND_UP", "HIGH_VOL_RANGE"]}}
        )
        
        # 高风险条件
        high_risk = self.add_condition_node(
            "高风险检查",
            {"change_pct": {"op": ">", "value": 5}, "volume_ratio": {"op": ">", "value": 2}},
            parent_id=mkt_node
        )
        
        self.add_outcome_node("风险过高，停止操作", parent_id=high_risk, probability=1.0, value=-2.0)
        
        # 低风险路径：买入条件
        buy_conditions = self.add_condition_node(
            "买入条件",
            {"buy_score": {"op": ">=", "value": 60}, "time_window": {"op": "in", "value": ["T2", "T6"]}},
            parent_id=mkt_node
        )
        
        # 买入动作
        buy_action = self.add_action_node("买入5000元", "BUY", parent_id=buy_conditions, probability=0.8, value=1.0)
        
        # 盈利预期
        profit = self.add_outcome_node("盈利2%以上", parent_id=buy_action, probability=0.6, value=3.0)
        loss = self.add_outcome_node("亏损1%", parent_id=buy_action, probability=0.4, value=-1.0)
        
        self.save_scenario()
        return scenario_id
