"""Typed owner-understanding cards and numeric drift anchors.

This is deliberately a local review packet, not automatic long-term memory.
Its job is to make each product statement traceable to evidence and to expose
when a metric or authority reference stops matching its recorded expectation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable, Mapping


class UnderstandingViolation(ValueError):
    """Raised for malformed understanding records or unsupported metrics."""


LAYERS = frozenset({"explicit_known", "implicit_known", "explainable_unknown", "opaque_unknown"})
EVIDENCE_TIERS = frozenset({"E0_observed", "E1_deterministic", "E2_clean_reproduced", "E3_independently_attested"})
DECISION_IMPACTS = frozenset({"none", "informs", "blocks"})
METRIC_DIRECTIONS = frozenset({"higher_is_better", "lower_is_better", "exact_match", "bounded_range"})


def _require_text(value: str, field_name: str) -> str:
    result = str(value).strip()
    if not result:
        raise UnderstandingViolation(field_name + " must be non-empty")
    return result


def _require_finite_ratio(value: float, field_name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise UnderstandingViolation(field_name + " must be a finite value in [0, 1]")
    return result


def _require_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise UnderstandingViolation(field_name + " must be numeric, not boolean")
    result = float(value)
    if not math.isfinite(result):
        raise UnderstandingViolation(field_name + " must be finite")
    return result


@dataclass(frozen=True)
class UnderstandingCard:
    card_id: str
    subject: str
    layer: str
    statement: str
    authority_ref: str
    evidence_tier: str
    confidence: float
    valid_from: str
    supersedes: tuple[str, ...] = ()
    numeric_anchor_ids: tuple[str, ...] = ()
    decision_impact: str = "informs"
    owner: str = "CODEX"
    human_explanation: str = ""

    def __post_init__(self) -> None:
        if not self.card_id.startswith("UC-"):
            raise UnderstandingViolation("card_id must start with UC-")
        for value, field_name in ((self.subject, "subject"), (self.statement, "statement"), (self.authority_ref, "authority_ref"), (self.valid_from, "valid_from"), (self.owner, "owner"), (self.human_explanation, "human_explanation")):
            _require_text(value, field_name)
        if self.layer not in LAYERS:
            raise UnderstandingViolation("Unsupported understanding layer: " + self.layer)
        if self.evidence_tier not in EVIDENCE_TIERS:
            raise UnderstandingViolation("Unsupported evidence tier: " + self.evidence_tier)
        if self.decision_impact not in DECISION_IMPACTS:
            raise UnderstandingViolation("Unsupported decision impact: " + self.decision_impact)
        _require_finite_ratio(self.confidence, "confidence")
        if self.decision_impact == "blocks" and self.evidence_tier == "E0_observed":
            raise UnderstandingViolation("A blocking card needs deterministic or stronger evidence")
        if self.card_id in self.supersedes:
            raise UnderstandingViolation("A card may not supersede itself")

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_id": self.card_id,
            "subject": self.subject,
            "layer": self.layer,
            "statement": self.statement,
            "authority_ref": self.authority_ref,
            "evidence_tier": self.evidence_tier,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "supersedes": list(self.supersedes),
            "numeric_anchor_ids": list(self.numeric_anchor_ids),
            "decision_impact": self.decision_impact,
            "owner": self.owner,
            "human_explanation": self.human_explanation,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnderstandingCard":
        return cls(
            card_id=str(value["card_id"]),
            subject=str(value["subject"]),
            layer=str(value["layer"]),
            statement=str(value["statement"]),
            authority_ref=str(value["authority_ref"]),
            evidence_tier=str(value["evidence_tier"]),
            confidence=float(value["confidence"]),
            valid_from=str(value["valid_from"]),
            supersedes=tuple(str(item) for item in value.get("supersedes", ())),
            numeric_anchor_ids=tuple(str(item) for item in value.get("numeric_anchor_ids", ())),
            decision_impact=str(value.get("decision_impact", "informs")),
            owner=str(value.get("owner", "CODEX")),
            human_explanation=str(value.get("human_explanation", "No explanation recorded.")),
        )


@dataclass(frozen=True)
class MetricAnchor:
    metric_id: str
    name: str
    unit: str
    direction: str
    baseline: Any
    current: Any
    target: Any
    source_ref: str
    measured_at: str
    hard_gate: bool
    warning_threshold: Any | None = None
    failure_threshold: Any | None = None
    formula_version: str = "MetricFormula/v1"

    def __post_init__(self) -> None:
        if not self.metric_id.startswith("M-"):
            raise UnderstandingViolation("metric_id must start with M-")
        for value, field_name in ((self.name, "name"), (self.unit, "unit"), (self.source_ref, "source_ref"), (self.measured_at, "measured_at"), (self.formula_version, "formula_version")):
            _require_text(value, field_name)
        if self.direction not in METRIC_DIRECTIONS:
            raise UnderstandingViolation("Unsupported metric direction: " + self.direction)
        if self.direction == "exact_match":
            for value, field_name in ((self.baseline, "baseline"), (self.current, "current"), (self.target, "target")):
                _require_text(str(value), field_name)
        elif self.direction == "bounded_range":
            for value, field_name in ((self.baseline, "baseline"), (self.current, "current")):
                _require_number(value, field_name)
            if not isinstance(self.target, Mapping) or set(self.target) != {"min", "max"}:
                raise UnderstandingViolation("bounded_range target must be {min, max}")
            minimum = _require_number(self.target["min"], "target.min")
            maximum = _require_number(self.target["max"], "target.max")
            if minimum > maximum:
                raise UnderstandingViolation("bounded_range target.min must be <= target.max")
        else:
            for value, field_name in ((self.baseline, "baseline"), (self.current, "current"), (self.target, "target")):
                _require_number(value, field_name)
            if self.unit == "ratio":
                for value, field_name in ((self.baseline, "baseline"), (self.current, "current"), (self.target, "target")):
                    _require_finite_ratio(float(value), field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "unit": self.unit,
            "direction": self.direction,
            "baseline": self.baseline,
            "current": self.current,
            "target": self.target,
            "source_ref": self.source_ref,
            "measured_at": self.measured_at,
            "hard_gate": self.hard_gate,
            "warning_threshold": self.warning_threshold,
            "failure_threshold": self.failure_threshold,
            "formula_version": self.formula_version,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MetricAnchor":
        return cls(
            metric_id=str(value["metric_id"]),
            name=str(value["name"]),
            unit=str(value["unit"]),
            direction=str(value["direction"]),
            baseline=value["baseline"],
            current=value["current"],
            target=value["target"],
            source_ref=str(value["source_ref"]),
            measured_at=str(value["measured_at"]),
            hard_gate=bool(value["hard_gate"]),
            warning_threshold=value.get("warning_threshold"),
            failure_threshold=value.get("failure_threshold"),
            formula_version=str(value.get("formula_version", "MetricFormula/v1")),
        )


@dataclass(frozen=True)
class DriftAssessment:
    metric_id: str
    status: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"metric_id": self.metric_id, "status": self.status, "message": self.message}


def assess_anchor(anchor: MetricAnchor) -> DriftAssessment:
    """Compare one metric with its versioned target without concealing drift."""

    if anchor.direction == "exact_match":
        passed = str(anchor.current) == str(anchor.target)
    elif anchor.direction == "higher_is_better":
        passed = _require_number(anchor.current, "current") >= _require_number(anchor.target, "target")
    elif anchor.direction == "lower_is_better":
        passed = _require_number(anchor.current, "current") <= _require_number(anchor.target, "target")
    else:
        minimum = _require_number(anchor.target["min"], "target.min")
        maximum = _require_number(anchor.target["max"], "target.max")
        current = _require_number(anchor.current, "current")
        passed = minimum <= current <= maximum
    if passed:
        return DriftAssessment(anchor.metric_id, "pass", "Current value matches the versioned target.")
    status = "fail" if anchor.hard_gate else "warning"
    return DriftAssessment(anchor.metric_id, status, "Current value diverges from the versioned target.")


@dataclass
class UnderstandingMap:
    """Append-only-style local packet with explicit supersession links."""

    cards: dict[str, UnderstandingCard] = field(default_factory=dict)
    anchors: dict[str, MetricAnchor] = field(default_factory=dict)

    def add_card(self, card: UnderstandingCard) -> None:
        if card.card_id in self.cards:
            raise UnderstandingViolation("Duplicate card_id: " + card.card_id)
        if any(anchor_id not in self.anchors for anchor_id in card.numeric_anchor_ids):
            raise UnderstandingViolation("Card references a missing numeric anchor")
        if any(previous not in self.cards for previous in card.supersedes):
            raise UnderstandingViolation("Card supersedes an unknown prior card")
        self.cards[card.card_id] = card

    def add_anchor(self, anchor: MetricAnchor) -> None:
        if anchor.metric_id in self.anchors:
            raise UnderstandingViolation("Duplicate metric_id: " + anchor.metric_id)
        self.anchors[anchor.metric_id] = anchor

    def assess(self) -> tuple[DriftAssessment, ...]:
        return tuple(assess_anchor(self.anchors[key]) for key in sorted(self.anchors))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "UnderstandingMap/v1",
            "cards": [self.cards[key].to_dict() for key in sorted(self.cards)],
            "anchors": [self.anchors[key].to_dict() for key in sorted(self.anchors)],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnderstandingMap":
        if value.get("schema") != "UnderstandingMap/v1":
            raise UnderstandingViolation("Unsupported understanding map schema")
        result = cls()
        for anchor in value.get("anchors", ()):
            result.add_anchor(MetricAnchor.from_dict(anchor))
        for card in value.get("cards", ()):
            result.add_card(UnderstandingCard.from_dict(card))
        return result


def bind_verified_timeline(
    timeline: Any,
    event_count: int,
    observed_at: str,
    *,
    owner: str = "CODEX",
) -> UnderstandingMap:
    """Map one verified story timeline into owner-visible evidence records."""

    if int(event_count) < 1:
        raise UnderstandingViolation("event_count must be at least one")
    digest = _require_text(str(timeline.timeline_hash), "timeline_hash")
    final_event_id = _require_text(str(timeline.final_event_id), "final_event_id")
    graph_revision = _require_text(str(timeline.graph_revision), "graph_revision")
    suffix = digest[:16]
    result = UnderstandingMap()
    anchor = MetricAnchor(
        metric_id="M-timeline-hash-" + suffix,
        name="Verified creative timeline hash",
        unit="sha256",
        direction="exact_match",
        baseline=digest,
        current=digest,
        target=digest,
        source_ref="event:" + final_event_id,
        measured_at=observed_at,
        hard_gate=True,
    )
    result.add_anchor(anchor)
    result.add_card(
        UnderstandingCard(
            card_id="UC-verified-timeline-" + suffix,
            subject="interactive-film timeline",
            layer="explainable_unknown",
            statement="The director input is derived from a graph-validated replay of every recorded story prefix.",
            authority_ref="event:" + final_event_id,
            evidence_tier="E1_deterministic",
            confidence=1.0,
            valid_from=observed_at,
            numeric_anchor_ids=(anchor.metric_id,),
            decision_impact="blocks",
            owner=owner,
            human_explanation=(
                "这条剧情不是只看最后结果；每一步都按同一张剧情图重放并核对。"
                "时间线哈希和图版本固定后，任何偷偷改后果的记录都会被拦住。"
                f" 图版本：{graph_revision}。"
            ),
        )
    )
    return result
