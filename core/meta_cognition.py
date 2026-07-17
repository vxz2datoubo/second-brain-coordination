"""
meta_cognition.py — 元认知监控引擎
自动识别思维盲区和推理漏洞
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field


# 常见思维偏见
COGNITIVE_BIASES = {
    "confirmation_bias": {"name": "确认偏见", "desc": "倾向于寻找支持自己观点的信息", "severity": 3},
    "anchoring_bias": {"name": "锚定偏见", "desc": "过度依赖第一个获得的信息", "severity": 2},
    "availability_bias": {"name": "可得性偏见", "desc": "用最容易想到的例子做判断", "severity": 2},
    "overconfidence_bias": {"name": "过度自信", "desc": "高估自己的判断准确性", "severity": 3},
    "loss_aversion": {"name": "损失厌恶", "desc": "对损失的敏感度高于收益", "severity": 3},
    "gamblers_fallacy": {"name": "赌徒谬误", "desc": "认为随机事件会自我纠正", "severity": 4},
    "recency_bias": {"name": "近因偏见", "desc": "过度重视最近的经验", "severity": 2},
    "authority_bias": {"name": "权威偏见", "desc": "过度依赖权威意见", "severity": 2},
    "survivorship_bias": {"name": "幸存者偏差", "desc": "只看到成功案例", "severity": 4},
    "groupthink": {"name": "群体思维", "desc": "为达成共识而忽视反对意见", "severity": 3}
}


# 推理漏洞模式
REASONING_FALLACIES = {
    "circular_reasoning": {"name": "循环论证", "desc": "用结论证明前提"},
    "false_causality": {"name": "虚假因果", "desc": "错误地认为相关性就是因果性"},
    "black_or_white": {"name": "非黑即白", "desc": "忽略中间可能性"},
    "strawman": {"name": "稻草人谬误", "desc": "攻击一个虚假的对手观点"},
    "appeal_to_emotion": {"name": "诉诸情感", "desc": "用情感而非逻辑说服"},
    "hasty_generalization": {"name": "草率概括", "desc": "基于少量案例得出普遍结论"},
    "appeal_to_authority": {"name": "诉诸权威", "desc": "权威说的就是对的"},
    "bandwagon": {"name": "从众谬误", "desc": "因为大家都这么做所以正确"}
}


@dataclass
class CognitiveCheck:
    id: str
    timestamp: str
    context: str
    detected_biases: List[str] = field(default_factory=list)
    detected_fallacies: List[str] = field(default_factory=list)
    reasoning_gaps: List[str] = field(default_factory=list)
    missing_perspectives: List[str] = field(default_factory=list)
    confidence_adjustment: float = 0.0  # 负数表示需要降低置信度
    recommendations: List[str] = field(default_factory=list)


class MetaCognitionEngine:
    """元认知监控引擎"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent / "second-brain"
        self.checks_file = self.data_dir / "meta_cognition_checks.json"
        self.blind_spots_file = self.data_dir / "cognitive_blind_spots.json"
        self.checks = self._load_checks()
        self.blind_spots = self._load_blind_spots()
    
    def _load_checks(self) -> List[Dict]:
        try:
            with open(self.checks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def _save_checks(self):
        self.checks_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checks_file, "w", encoding="utf-8") as f:
            json.dump(self.checks, f, ensure_ascii=False, indent=2)
    
    def _load_blind_spots(self) -> Dict:
        try:
            with open(self.blind_spots_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"patterns": {}, "statistics": {}}
    
    def _save_blind_spots(self):
        self.blind_spots_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blind_spots_file, "w", encoding="utf-8") as f:
            json.dump(self.blind_spots, f, ensure_ascii=False, indent=2)
    
    def check_cognitive_bias(self, text: str, context: Dict) -> CognitiveCheck:
        """检查认知偏见"""
        import uuid
        
        check = CognitiveCheck(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now().isoformat(),
            context=context.get("topic", ""),
            detected_biases=[],
            detected_fallacies=[],
            reasoning_gaps=[],
            missing_perspectives=[],
            recommendations=[]
        )
        
        text_lower = text.lower()
        
        # 检测认知偏见
        if any(w in text_lower for w in ["肯定", "一定", "绝对", "必然"]):
            check.detected_biases.append("overconfidence_bias")
        
        if context.get("recent_wins", 0) > context.get("recent_losses", 0) * 2:
            check.detected_biases.append("recency_bias")
        
        if "买" in text and "追" in text:
            check.detected_biases.append("gamblers_fallacy")
        
        if context.get("source") == "authority" and not context.get("verified"):
            check.detected_biases.append("authority_bias")
        
        if context.get("sample_size", 999999) < 5:
            check.detected_biases.append("hasty_generalization")
        
        # 检测推理谬误
        if "因为之前" in text and "所以" in text:
            check.detected_fallacies.append("false_causality")
        
        if "不是...就是..." in text:
            check.detected_fallacies.append("black_or_white")
        
        # 检测推理漏洞
        if not context.get("has_contrary_evidence"):
            check.reasoning_gaps.append("缺少反面证据")
        
        if not context.get("has_alternative_hypotheses"):
            check.reasoning_gaps.append("缺少备选假设")
        
        if not context.get("has_probability_estimation"):
            check.reasoning_gaps.append("缺少概率估计")
        
        # 检测缺失视角
        if context.get("decision_type") == "buy":
            check.missing_perspectives.append("没有考虑卖出时机")
            check.missing_perspectives.append("没有考虑止损点")
        
        if context.get("decision_type") == "sell":
            check.missing_perspectives.append("没有考虑卖飞风险")
            check.missing_perspectives.append("没有考虑持仓理由")
        
        # 计算置信度调整
        severity_sum = sum(COGNITIVE_BIASES.get(b, {}).get("severity", 1) for b in check.detected_biases)
        fallacy_sum = len(check.detected_fallacies) * 2
        gap_sum = len(check.reasoning_gaps) * 3
        
        check.confidence_adjustment = -(severity_sum + fallacy_sum + gap_sum) / 100.0
        
        # 生成建议
        for bias_id in check.detected_biases:
            bias = COGNITIVE_BIASES.get(bias_id, {})
            check.recommendations.append(f"注意{bias.get('name', bias_id)}: {bias.get('desc', '')}")
        
        for fallacy_id in check.detected_fallacies:
            fallacy = REASONING_FALLACIES.get(fallacy_id, {})
            check.recommendations.append(f"避免{fallacy.get('name', fallacy_id)}")
        
        for gap in check.reasoning_gaps:
            check.recommendations.append(f"补充{gap}")
        
        self.checks.append(check.__dict__)
        if len(self.checks) > 100:
            self.checks = self.checks[-100:]
        
        self._update_blind_spot_patterns(check)
        self._save_checks()
        
        return check
    
    def _update_blind_spot_patterns(self, check: CognitiveCheck):
        """更新盲点模式"""
        for bias_id in check.detected_biases:
            self.blind_spots.setdefault("patterns", {}).setdefault(bias_id, {"count": 0, "recent": []})
            self.blind_spots["patterns"][bias_id]["count"] += 1
            self.blind_spots["patterns"][bias_id]["recent"].append(check.timestamp)
            if len(self.blind_spots["patterns"][bias_id]["recent"]) > 10:
                self.blind_spots["patterns"][bias_id]["recent"] = self.blind_spots["patterns"][bias_id]["recent"][-10:]
        
        # 更新统计
        total_checks = len(self.checks)
        self.blind_spots["statistics"] = {
            "total_checks": total_checks,
            "bias_rate": sum(len(c.get("detected_biases", [])) for c in self.checks[-50:]) / min(50, total_checks),
            "top_biases": self._get_top_biases(5)
        }
        
        self._save_blind_spots()
    
    def _get_top_biases(self, limit: int = 5) -> List[Dict]:
        counts = []
        for bias_id, data in self.blind_spots.get("patterns", {}).items():
            bias_info = COGNITIVE_BIASES.get(bias_id, {})
            counts.append({"id": bias_id, "name": bias_info.get("name", bias_id), "count": data["count"]})
        counts.sort(key=lambda x: -x["count"])
        return counts[:limit]
    
    def format_check_result(self, check: CognitiveCheck) -> str:
        """格式化检查结果"""
        lines = ["## 元认知检查报告", ""]
        
        if check.detected_biases:
            lines.append("### 检测到的认知偏见")
            for bias_id in check.detected_biases:
                bias = COGNITIVE_BIASES.get(bias_id, {})
                lines.append(f"- **{bias.get('name', bias_id)}**: {bias.get('desc', '')}")
            lines.append("")
        
        if check.detected_fallacies:
            lines.append("### 推理谬误")
            for fallacy_id in check.detected_fallacies:
                fallacy = REASONING_FALLACIES.get(fallacy_id, {})
                lines.append(f"- **{fallacy.get('name', fallacy_id)}**: {fallacy.get('desc', '')}")
            lines.append("")
        
        if check.reasoning_gaps:
            lines.append("### 推理漏洞")
            for gap in check.reasoning_gaps:
                lines.append(f"- ⚠️ {gap}")
            lines.append("")
        
        if check.missing_perspectives:
            lines.append("### 缺失视角")
            for p in check.missing_perspectives:
                lines.append(f"- 👁️ {p}")
            lines.append("")
        
        if check.confidence_adjustment != 0:
            adj = check.confidence_adjustment * 100
            lines.append(f"**置信度调整**: {adj:+.1f}%")
            lines.append("")
        
        if check.recommendations:
            lines.append("### 改进建议")
            for rec in check.recommendations[:5]:
                lines.append(f"- 💡 {rec}")
            lines.append("")
        
        return "\n".join(lines)
    
    def get_overall_assessment(self) -> Dict:
        """获取整体评估"""
        recent_checks = self.checks[-20:]
        
        return {
            "bias_frequency": len(recent_checks) > 0 and sum(len(c.get("detected_biases", [])) for c in recent_checks) / len(recent_checks) or 0,
            "common_biases": self._get_top_biases(3),
            "recommendations": self._generate_improvement_recommendations(),
            "stats": self.blind_spots.get("statistics", {})
        }
    
    def _generate_improvement_recommendations(self) -> List[str]:
        recs = []
        stats = self.blind_spots.get("statistics", {})
        
        if stats.get("bias_rate", 0) > 0.5:
            recs.append("认知偏见频率较高，建议决策前增加冷静期")
        
        top_biases = stats.get("top_biases", [])
        if top_biases:
            recs.append(f"最常见的偏见: {', '.join(b['name'] for b in top_biases[:2])}")
        
        return recs
