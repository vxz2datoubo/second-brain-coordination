"""Exhaustive, exact-head replay evidence for every registered synthetic route.

The corpus is deliberately constructed from bounded graph coverage, not from
local workspaces.  It therefore exercises all reachable safe endings without
exporting a player session, caller text, customer material, or any provider
output.  Every entry retains a complete replay capsule so a later verifier can
rebuild the story, director and sequence contracts independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from typing import Any, Mapping

from .continuity import graph_for_initial_state
from .contracts import canonical_json
from .coverage import coverage_for_scenario, ledger_for_route
from .replay_capsule import ReplayCapsuleViolation, build_verified_replay_capsule


SYNTHETIC_REPLAY_CORPUS_SCHEMA = "CreativeSyntheticReplayCorpus/v1"
SYNTHETIC_REPLAY_CORPUS_SCENARIOS = (
    "harbor_protocol",
    "legacy_archive",
    "night_signal",
    "three_scene",
)


class ReplayCorpusViolation(ValueError):
    """Raised when exhaustive synthetic replay evidence cannot be rebuilt."""


def _require_head(head_sha: str) -> str:
    if not isinstance(head_sha, str) or len(head_sha) != 40 or any(character not in "0123456789abcdef" for character in head_sha):
        raise ReplayCorpusViolation("Replay corpus requires a lowercase full 40-character Git SHA")
    return head_sha


@dataclass(frozen=True)
class VerifiedSyntheticReplayCorpus:
    """A full, deterministic corpus of source-bound synthetic terminal routes."""

    corpus_id: str
    head_sha: str
    entries: tuple[Mapping[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        scenario_counts: dict[str, int] = {scenario: 0 for scenario in SYNTHETIC_REPLAY_CORPUS_SCENARIOS}
        for entry in self.entries:
            scenario_counts[str(entry["scenario"])] += 1
        return {
            "schema": SYNTHETIC_REPLAY_CORPUS_SCHEMA,
            "status": "synthetic_replay_corpus_verified",
            "corpus_id": self.corpus_id,
            "head_sha": self.head_sha,
            "scenario_ids": list(SYNTHETIC_REPLAY_CORPUS_SCENARIOS),
            "entry_count": len(self.entries),
            "scenario_route_counts": scenario_counts,
            "entries": [dict(entry) for entry in self.entries],
            "boundary": {
                "synthetic_only": True,
                "customer_data_present": False,
                "caller_free_text_present": False,
                "external_provider_called": False,
                "publication_authorized": False,
                "canonical_knowledge_write": False,
                "client_story_authority": False,
            },
            "authority_note": "Offline exhaustive synthetic regression evidence only; this corpus cannot authorize release, deployment, paid generation, or customer intake.",
        }


def _entry_for(scenario: str, route: Any, initial_state: Any) -> dict[str, Any]:
    graph = graph_for_initial_state(initial_state)
    ledger = ledger_for_route(graph, initial_state, route.action_ids)
    try:
        capsule = build_verified_replay_capsule(ledger, slot="corpus")
    except ReplayCapsuleViolation as error:
        raise ReplayCorpusViolation("Replay corpus route cannot produce a verified synthetic capsule") from error
    if capsule.scenario != scenario:
        raise ReplayCorpusViolation("Replay corpus route resolved to a different scenario identity")
    if capsule.timeline_hash != route.timeline_hash or capsule.payload["source"]["final_state"] != route.final_state.to_dict():
        raise ReplayCorpusViolation("Replay corpus capsule diverges from exhaustive route coverage")
    return {
        "scenario": scenario,
        "route_id": route.route_id,
        "action_ids": list(route.action_ids),
        "transition_ids": list(route.transition_ids),
        "timeline_hash": route.timeline_hash,
        "final_state": route.final_state.to_dict(),
        "capsule_id": capsule.capsule_id,
        "capsule": capsule.to_dict(),
    }


def _build_verified_synthetic_replay_corpus_uncached(head: str) -> VerifiedSyntheticReplayCorpus:
    """Build every bounded terminal route through production replay contracts."""

    entries: list[Mapping[str, Any]] = []
    for scenario in SYNTHETIC_REPLAY_CORPUS_SCENARIOS:
        report = coverage_for_scenario(scenario)
        if not report.complete:
            raise ReplayCorpusViolation("Replay corpus requires complete route coverage before export")
        for route in report.routes:
            entries.append(_entry_for(scenario, route, report.initial_state))
    ordered = tuple(sorted(entries, key=lambda entry: (str(entry["scenario"]), str(entry["route_id"]))))
    if len({str(entry["route_id"]) for entry in ordered}) != len(ordered):
        raise ReplayCorpusViolation("Replay corpus contains duplicate route identities")
    material = {
        "schema": SYNTHETIC_REPLAY_CORPUS_SCHEMA,
        "head_sha": head,
        "entries": [dict(entry) for entry in ordered],
    }
    corpus_id = "replay_corpus_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20]
    return VerifiedSyntheticReplayCorpus(corpus_id=corpus_id, head_sha=head, entries=ordered)


@lru_cache(maxsize=4)
def _canonical_corpus_json_for_head(head: str) -> str:
    """Compute one immutable corpus source per exact head in this Python process.

    This is a local performance cache only. A command-line build or verifier
    starts a new process and therefore still performs its own complete source
    reconstruction. Returning canonical JSON rather than a cached mutable
    object prevents a caller from poisoning later in-process verifications.
    """

    return canonical_json(_build_verified_synthetic_replay_corpus_uncached(head).to_dict())


def build_verified_synthetic_replay_corpus(head_sha: str) -> VerifiedSyntheticReplayCorpus:
    """Return a fresh object rebuilt from the immutable per-head cache payload."""

    head = _require_head(head_sha)
    payload = json.loads(_canonical_corpus_json_for_head(head))
    entries = tuple(payload["entries"])
    return VerifiedSyntheticReplayCorpus(corpus_id=payload["corpus_id"], head_sha=head, entries=entries)


def verify_verified_synthetic_replay_corpus(head_sha: str, corpus: Mapping[str, Any]) -> VerifiedSyntheticReplayCorpus:
    """Fail closed unless every corpus entry equals the exact source rebuild."""

    head = _require_head(head_sha)
    try:
        supplied = dict(corpus)
        entries = supplied["entries"]
        scenarios = tuple(supplied["scenario_ids"])
    except (KeyError, TypeError, ValueError) as error:
        raise ReplayCorpusViolation("Replay corpus has malformed entries or scenario identities") from error
    if not isinstance(entries, list) or scenarios != SYNTHETIC_REPLAY_CORPUS_SCENARIOS:
        raise ReplayCorpusViolation("Replay corpus must contain the complete registered scenario set in stable order")
    if supplied.get("head_sha") != head:
        raise ReplayCorpusViolation("Replay corpus exact Git head does not match the verifier source")
    for entry in entries:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("capsule"), Mapping):
            raise ReplayCorpusViolation("Replay corpus entry does not contain a replay capsule")
    expected = build_verified_synthetic_replay_corpus(head)
    if canonical_json(supplied) != canonical_json(expected.to_dict()):
        raise ReplayCorpusViolation("Replay corpus does not exactly match the clean exact-head exhaustive rebuild")
    return expected
