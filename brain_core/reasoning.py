"""Reasoning helpers for v0.1."""

from __future__ import annotations

from dataclasses import dataclass, field
import re


BIAS_PATTERNS: dict[str, list[str]] = {
    "absolute_language": ["一定", "必然", "稳赚", "肯定", "绝对", "guaranteed"],
    "fomo": ["追高", "追涨", "不能错过", "马上冲", "all in"],
    "revenge_trading": ["扳回来", "报复", "不服", "加倍"],
    "loss_aversion": ["舍不得卖", "不想认亏", "死扛"],
    "confirmation_bias": ["只看利好", "证明我是对的", "别的不用看"],
    "recency_bias": ["刚刚涨", "最近一直", "今天肯定"],
    "anchoring": ["成本价", "锚定", "之前是"],
    "narrative_fallacy": ["故事很顺", "逻辑完美", "大叙事"],
    "overfitting": ["历史每次", "百分百规律", "只要出现就"],
    "herding": ["大家都", "群里都说", "市场都在买"],
}


@dataclass
class BiasCheck:
    warnings: list[str] = field(default_factory=list)
    risk_level: str = "low"


class BiasDetector:
    def check(self, text: str) -> BiasCheck:
        text = text or ""
        warnings: list[str] = []
        lowered = text.lower()
        for name, patterns in BIAS_PATTERNS.items():
            if any(p.lower() in lowered for p in patterns):
                warnings.append(name)
        if re.search(r"\b100%|\b0%", text):
            warnings.append("overconfidence_probability")
        risk = "high" if len(warnings) >= 3 else ("medium" if warnings else "low")
        return BiasCheck(warnings=sorted(set(warnings)), risk_level=risk)
