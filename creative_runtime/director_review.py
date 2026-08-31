"""Human-readable, exact-rebuild review boards for every AI-director prefix.

The director compiler already rejects invalid story inputs.  A review board
turns its exhaustive prefix coverage into a compact inspection artifact: every
reachable state has its verified timeline identity, cinematic profile, asset
references, shot plan, and quality gate in one deterministic object.  It is
not a generator, media asset, provider request, or approval action.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .continuity import graph_for_initial_state
from .contracts import canonical_json
from .coverage import DirectorCoverageReport, director_coverage_for_scenario, ledger_for_route
from .director import compile_verified_director


class DirectorReviewViolation(ValueError):
    """Raised when a review board cannot prove complete director coverage."""


@dataclass(frozen=True)
class DirectorReviewBoard:
    """A complete, source-bound review surface for one synthetic scenario."""

    board_id: str
    scenario: str
    graph_revision: str
    coverage_report_hash: str
    cards: tuple[Mapping[str, Any], ...]
    covered_transition_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "CreativeDirectorReviewBoard/v1",
            "status": "director_review_board_verified",
            "board_id": self.board_id,
            "scenario": self.scenario,
            "graph_revision": self.graph_revision,
            "coverage_report_hash": self.coverage_report_hash,
            "card_count": len(self.cards),
            "covered_transition_ids": list(self.covered_transition_ids),
            "cards": [dict(card) for card in self.cards],
            "boundary": {
                "synthetic_only": True,
                "customer_data_present": False,
                "external_provider_called": False,
                "publication_authorized": False,
                "canonical_knowledge_write": False,
            },
            "authority_note": "Read-only director inspection evidence. It cannot generate media, alter story state, approve a release, or promote knowledge.",
        }


def _card_for_entry(report: DirectorCoverageReport, entry: Any) -> Mapping[str, Any]:
    graph = graph_for_initial_state(report.initial_state)
    ledger = ledger_for_route(graph, report.initial_state, entry.action_ids)
    compiled = compile_verified_director(ledger, graph=graph)
    verified = compiled.verified_input
    quality = compiled.compilation.quality_report
    if verified.timeline_hash != entry.timeline_hash:
        raise DirectorReviewViolation("Director coverage timeline identity diverges during review-board reconstruction")
    if verified.state != entry.state:
        raise DirectorReviewViolation("Director coverage state diverges during review-board reconstruction")
    if not quality.can_generate or quality.metrics.hard_finding_count != 0:
        raise DirectorReviewViolation("Director review board cannot include a quality-gated state")
    shots = [shot.to_dict() for shot in compiled.compilation.shots]
    if not shots or any("art_scene_" + entry.state.scene_id not in shot["reference_artifact_ids"] for shot in shots):
        raise DirectorReviewViolation("Director review board card lacks the current source scene asset")
    material = {
        "schema": "CreativeDirectorReviewCard/v1",
        "prefix_id": entry.prefix_id,
        "timeline_hash": entry.timeline_hash,
        "state": entry.state.to_dict(),
        "action_ids": list(entry.action_ids),
        "scene_profile_id": entry.scene_profile_id,
        "scene_asset_id": entry.scene_asset_id,
        "brief_id": compiled.compilation.brief.brief_id,
        "quality_metrics": quality.metrics.to_dict(),
        "shots": shots,
    }
    return {
        **material,
        "review_card_id": "director_review_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20],
        "content_rating": compiled.compilation.brief.content_rating,
        "final_transition_id": verified.final_transition_id,
        "final_consequence": dict(verified.final_consequence),
        "activated_skill_ids": list(compiled.compilation.brief.activated_skill_ids),
        "skill_trigger_reasons": dict(compiled.compilation.brief.skill_trigger_reasons),
        "quality_report": quality.to_dict(),
        "human_visible_cues": {
            "caption": " / ".join((shot["shot_role"] + ": " + shot["camera"]) for shot in shots),
            "lighting": [shot["lighting"] for shot in shots],
            "sound": [shot["sound"] for shot in shots],
            "axis": [shot["axis"] for shot in shots],
            "performance_tasks": [shot["performance_task"] for shot in shots],
        },
    }


def build_director_review_board(scenario: str) -> DirectorReviewBoard:
    """Build a deterministic board for every reachable director-ready prefix."""

    report = director_coverage_for_scenario(scenario)
    if not report.complete:
        raise DirectorReviewViolation("Director coverage must be complete before a review board is built")
    cards = tuple(sorted((_card_for_entry(report, entry) for entry in report.entries), key=lambda card: str(card["review_card_id"])))
    if len(cards) != len(report.entries) or len({card["timeline_hash"] for card in cards}) != len(cards):
        raise DirectorReviewViolation("Director review board must contain exactly one card per verified prefix")
    if {card["prefix_id"] for card in cards} != {entry.prefix_id for entry in report.entries}:
        raise DirectorReviewViolation("Director review board prefix identities do not match coverage")
    material = {
        "schema": "CreativeDirectorReviewBoard/v1",
        "scenario": scenario,
        "graph_revision": report.graph_revision,
        "coverage_report_hash": report.report_hash,
        "cards": list(cards),
        "covered_transition_ids": list(report.covered_transition_ids),
    }
    board_id = "director_review_board_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return DirectorReviewBoard(
        board_id=board_id,
        scenario=scenario,
        graph_revision=report.graph_revision,
        coverage_report_hash=report.report_hash,
        cards=cards,
        covered_transition_ids=report.covered_transition_ids,
    )


def verify_director_review_board(scenario: str, board: Mapping[str, Any]) -> DirectorReviewBoard:
    """Fail closed unless an inspection board equals its exact local rebuild."""

    try:
        supplied = dict(board)
    except (TypeError, ValueError) as error:
        raise DirectorReviewViolation("Director review board must be a JSON object") from error
    expected = build_director_review_board(scenario)
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise DirectorReviewViolation("Director review board does not exactly match exhaustive verified coverage")
    return expected
