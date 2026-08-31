"""Shadow-only MIDS opportunity detector.

This module is deliberately non-authoritative. It detects whether a user request is a
candidate for Mixed-Initiative Discovery & Specification. It does not create tasks,
requirements, signals, domain truth, or canonical decisions.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Detection:
    level: str
    score: int
    reasons: tuple[str, ...]
    suggested_behavior: str


STRONG_PATTERNS = (
    "不知道怎么落地",
    "不知道具体怎么",
    "不知道该怎么实现",
    "不清楚怎么实现",
    "没办法像程序员",
    "很多想法",
    "想法和思路",
    "方向但是",
    "需求不完整",
    "我也不知道最终",
    "我不一定知道",
    "帮我确认整体",
    "一起推演",
    "共同设计",
    "一起设计",
    "帮我把需求问出来",
    "主动问我",
    "先发现再规格",
    "mids",
    "don't know how to implement",
    "not sure what to build",
    "many ideas",
    "help me figure out the requirements",
)

MEDIUM_PATTERNS = (
    "可能",
    "大概",
    "方向",
    "想做一个",
    "想增加",
    "应该怎样",
    "怎么设计",
    "怎么规划",
    "有没有更好的",
    "帮我想",
    "brainstorm",
    "explore options",
    "design direction",
)

SUPPRESS_PATTERNS = (
    "不要问",
    "别问我",
    "不要用mids",
    "不用mids",
    "直接执行",
    "只执行",
    "只回复",
    "只翻译",
    "只改错字",
    "do not ask",
    "don't ask",
    "do not use mids",
)

LOW_COMPLEXITY_PATTERNS = (
    "翻译成",
    "什么意思",
    "拼写",
    "错别字",
    "计算",
    "单位换算",
    "几点",
    "天气",
    "translate",
    "spelling",
    "unit conversion",
)


def _count(text: str, patterns: tuple[str, ...]) -> int:
    return sum(1 for pattern in patterns if pattern in text)


def detect_mids_opportunity(
    request_text: str,
    *,
    material_project_decision: bool = False,
    unresolved_dependencies: bool = False,
    explicit_spec_is_sufficient: bool = False,
    user_declined_for_slice: bool = False,
) -> Detection:
    """Return a deterministic shadow classification: HIGH, MEDIUM, LOW, or SUPPRESSED."""
    text = " ".join(str(request_text).casefold().split())

    if user_declined_for_slice or any(pattern in text for pattern in SUPPRESS_PATTERNS):
        return Detection(
            level="SUPPRESSED",
            score=0,
            reasons=("explicit_user_suppression",),
            suggested_behavior="answer_normally_without_MIDS_reminder",
        )

    if explicit_spec_is_sufficient:
        return Detection(
            level="LOW",
            score=0,
            reasons=("sufficient_explicit_spec",),
            suggested_behavior="execute_normally",
        )

    strong_hits = _count(text, STRONG_PATTERNS)
    medium_hits = _count(text, MEDIUM_PATTERNS)
    low_complexity_hits = _count(text, LOW_COMPLEXITY_PATTERNS)

    score = strong_hits * 3 + min(medium_hits, 3)
    reasons: list[str] = []

    if strong_hits:
        reasons.append("semantic_discovery_need")
    if medium_hits:
        reasons.append("open_design_language")
    if material_project_decision:
        score += 2
        reasons.append("material_project_decision")
    if unresolved_dependencies:
        score += 2
        reasons.append("unresolved_dependencies")

    if low_complexity_hits and not material_project_decision and strong_hits == 0:
        score -= 3
        reasons.append("low_complexity_direct_task")

    score = max(score, 0)

    if score >= 6:
        level = "HIGH"
        behavior = "briefly_recall_MIDS_then_start_1_to_3_high_value_questions"
    elif score >= 3:
        level = "MEDIUM"
        behavior = "use_micro_MIDS_and_mention_method_only_if_helpful"
    else:
        level = "LOW"
        behavior = "answer_normally_without_interrupting"

    return Detection(level=level, score=score, reasons=tuple(reasons), suggested_behavior=behavior)
