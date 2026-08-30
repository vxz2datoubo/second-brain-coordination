"""Deterministic, non-generative safe-intent resolution for interactive play.

This intentionally is not an LLM prompt parser.  The only possible result is
one action already legal in the current verified frame, or a clarification.
The same declared vocabulary can be exposed by the CLI and a static player so
a user-visible input hint never becomes a hidden client-side transition rule.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Iterable


SAFE_INTENT_SCHEMA = "CreativeSafeIntentProjection/v1"
SAFE_INTENT_CONFIDENCE = 0.9

# These are tested before all action signals. A phrase containing an otherwise
# valid action word therefore cannot turn unsafe material into a story choice.
UNSAFE_TERMS = frozenset({"sex", "sexual", "nude", "blood", "gore", "torture"})
UNSAFE_PHRASES = frozenset(
    {
        "sex", "sexual", "nude", "blood", "gore", "torture",
        "性爱", "性行为", "色情", "裸露", "裸体", "露骨", "血腥", "酷刑", "虐待",
    }
)

# Each phrase is a public-safe, action-family signal. The public renderer only
# accepts the short exact examples exposed in its verified frame; the CLI also
# permits a bounded natural-language form when it has one unambiguous family.
_ACTION_SIGNALS: dict[str, frozenset[str]] = {
    "listen": frozenset({"listen", "hear", "quiet", "door", "read", "review", "confirm", "听", "倾听", "聆听", "阅读", "确认"}),
    "approach": frozenset({"approach", "knock", "enter", "walk", "ask", "document", "open", "request", "compare", "pause", "敲门", "靠近", "进入", "询问", "记录", "请求", "比较", "暂停"}),
    "leave": frozenset({"leave", "withdraw", "back", "wait", "daylight", "defer", "return", "seal", "decline", "close", "adjourn", "离开", "撤退", "后退", "等待", "白天", "延期", "返回", "封存", "拒绝", "关闭", "休会"}),
}

_EXACT_EXAMPLES: dict[str, tuple[str, ...]] = {
    "listen": ("listen", "hear the signal", "倾听"),
    "approach": ("approach", "knock", "靠近"),
    "leave": ("leave", "withdraw", "离开"),
}


@dataclass(frozen=True)
class SafeIntentResolution:
    """An explainable result of resolving one bounded user input."""

    status: str
    action_id: str | None
    confidence: float
    normalized_text: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "action_id": self.action_id,
            "confidence": self.confidence,
            "normalized_text": self.normalized_text,
            "reason": self.reason,
        }


def normalize_safe_intent_text(text: str) -> str:
    """Normalize display-safe text identically for all offline adapters."""

    if not isinstance(text, str):
        return ""
    return " ".join(text.lower().strip().split())


def safe_intent_examples(action_id: str) -> tuple[str, ...]:
    """Return the short exact phrases a static renderer may display."""

    return _EXACT_EXAMPLES.get(action_id, (action_id,)) if isinstance(action_id, str) and action_id else ()


def _unsafe(normalized: str) -> bool:
    if any(phrase in normalized for phrase in UNSAFE_PHRASES):
        return True
    tokens = set(re.sub(r"[.,!?;:]", " ", normalized).split())
    return bool(tokens & UNSAFE_TERMS)


def resolve_safe_intent(text: str, legal_actions: Iterable[str]) -> SafeIntentResolution:
    """Resolve only one legal action, otherwise require clarification.

    A zero-confidence result always leaves the caller's ledger untouched. It
    records the reason so a local UI can tell unsafe and ambiguous input apart
    without pretending it interpreted a story instruction.
    """

    normalized = normalize_safe_intent_text(text)
    legal = tuple(sorted({action for action in legal_actions if isinstance(action, str) and action}))
    if not normalized:
        return SafeIntentResolution("clarification_required", None, 0.0, normalized, "empty_input")
    if _unsafe(normalized):
        return SafeIntentResolution("clarification_required", None, 0.0, normalized, "non_explicit_boundary")
    exact_matches = [action for action in legal if normalized in safe_intent_examples(action)]
    if len(exact_matches) == 1:
        return SafeIntentResolution("intent_resolved", exact_matches[0], SAFE_INTENT_CONFIDENCE, normalized, "declared_exact_example")
    tokens = set(re.sub(r"[.,!?;:]", " ", normalized).split())
    family_matches = [
        action
        for action in legal
        if (tokens & _ACTION_SIGNALS.get(action, frozenset()))
        or any(signal in normalized for signal in _ACTION_SIGNALS.get(action, frozenset()) if len(signal) > 1)
    ]
    if len(family_matches) == 1:
        return SafeIntentResolution("intent_resolved", family_matches[0], SAFE_INTENT_CONFIDENCE, normalized, "unambiguous_declared_family")
    return SafeIntentResolution(
        "clarification_required",
        None,
        0.0,
        normalized,
        "ambiguous_or_not_currently_legal" if family_matches else "no_declared_legal_intent",
    )


def safe_intent_projection(legal_actions: Iterable[str]) -> dict[str, Any]:
    """Return a source-bound, display-safe vocabulary for one verified frame."""

    actions = tuple(sorted({action for action in legal_actions if isinstance(action, str) and action}))
    return {
        "schema": SAFE_INTENT_SCHEMA,
        "status": "safe_intent_projection_verified",
        "content_boundary": "non_explicit",
        "minimum_confidence": SAFE_INTENT_CONFIDENCE,
        "clarification_required_below_confidence": True,
        "actions": [
            {"action_id": action, "exact_examples": list(safe_intent_examples(action))}
            for action in actions
        ],
        "authority_note": "Only current legal actions and declared non-explicit examples are exposed. This projection cannot authorize an undeclared action or arbitrary story mutation.",
    }
