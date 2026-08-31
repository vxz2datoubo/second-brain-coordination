"""Deterministic, source-bound branch comparison for synthetic replay corpora.

The review board is a read-only explanation layer built from an already
verified corpus. It never decides an action or calculates a new story state:
every shown branch and terminal delta is copied from source-reconstructed
replay evidence and can be rebuilt exactly at the same Git head.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any, Mapping

from .contracts import canonical_json
from .replay_corpus import (
    ReplayCorpusViolation,
    SYNTHETIC_REPLAY_CORPUS_SCHEMA,
    VerifiedSyntheticReplayCorpus,
    verify_verified_synthetic_replay_corpus,
)


SYNTHETIC_REPLAY_REVIEW_SCHEMA = "CreativeSyntheticReplayReviewBoard/v1"


class ReplayReviewViolation(ValueError):
    """Raised when a review board cannot be fully derived from its corpus."""


def _state_hash(state: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(dict(state)).encode("utf-8")).hexdigest()


def _state_delta(initial: Mapping[str, Any], final: Mapping[str, Any]) -> dict[str, Any]:
    """Describe exact terminal consequences without scoring or averaging them."""

    initial_relationships = dict(initial.get("relationships", {}))
    final_relationships = dict(final.get("relationships", {}))
    relationship_delta = {
        key: int(final_relationships.get(key, 0)) - int(initial_relationships.get(key, 0))
        for key in sorted(set(initial_relationships) | set(final_relationships))
        if int(final_relationships.get(key, 0)) != int(initial_relationships.get(key, 0))
    }
    initial_facts = set(initial.get("known_facts", []))
    final_facts = set(final.get("known_facts", []))
    initial_flags = dict(initial.get("flags", {}))
    final_flags = dict(final.get("flags", {}))
    changed_flags = {
        key: final_flags.get(key)
        for key in sorted(set(initial_flags) | set(final_flags))
        if initial_flags.get(key) != final_flags.get(key)
    }
    return {
        "risk_delta": int(final["risk_level"]) - int(initial["risk_level"]),
        "relationship_delta": relationship_delta,
        "new_known_facts": sorted(final_facts - initial_facts),
        "lost_known_facts": sorted(initial_facts - final_facts),
        "flag_changes": changed_flags,
        "final_state_hash": _state_hash(final),
    }


def _route_outcome(entry: Mapping[str, Any], prefix_state: Mapping[str, Any]) -> dict[str, Any]:
    final_state = dict(entry["final_state"])
    return {
        "route_id": entry["route_id"],
        "action_ids": list(entry["action_ids"]),
        "transition_ids": list(entry["transition_ids"]),
        "timeline_hash": entry["timeline_hash"],
        "capsule_id": entry["capsule_id"],
        "final_state": final_state,
        "terminal_delta": _state_delta(prefix_state, final_state),
    }


def build_verified_replay_review_board(head_sha: str, corpus: Mapping[str, Any]) -> dict[str, Any]:
    """Derive every genuine choice point and its terminal alternatives.

    A prefix is included only if the verified corpus shows more than one next
    canonical action from the same state. This avoids inventing a comparison
    merely because different routes happen to have different lengths.
    """

    try:
        verified = verify_verified_synthetic_replay_corpus(head_sha, corpus)
    except ReplayCorpusViolation as error:
        raise ReplayReviewViolation("Replay review board requires a verified exact-head corpus") from error
    raw_groups: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    for entry in verified.entries:
        source = entry["capsule"].get("source")
        if not isinstance(source, Mapping):
            raise ReplayReviewViolation("Replay review route capsule is missing source evidence")
        timeline = source.get("timeline")
        actions = entry.get("action_ids")
        transitions = entry.get("transition_ids")
        if not isinstance(timeline, list) or not isinstance(actions, list) or not isinstance(transitions, list):
            raise ReplayReviewViolation("Replay review route is malformed")
        if len(actions) != len(transitions) or len(timeline) != len(actions) + 1:
            raise ReplayReviewViolation("Replay review route has no exact prefix timeline")
        scenario = str(entry["scenario"])
        for index, action_id in enumerate(actions):
            prefix = tuple(str(value) for value in actions[:index])
            state = timeline[index].get("state")
            if not isinstance(state, Mapping):
                raise ReplayReviewViolation("Replay review prefix state is malformed")
            key = (scenario, prefix)
            group = raw_groups.setdefault(
                key,
                {
                    "scenario": scenario,
                    "prefix_action_ids": list(prefix),
                    "prefix_state": dict(state),
                    "prefix_state_hash": _state_hash(state),
                    "choices": {},
                },
            )
            if canonical_json(group["prefix_state"]) != canonical_json(dict(state)):
                raise ReplayReviewViolation("Same replay prefix resolves to conflicting source states")
            choice = group["choices"].setdefault(
                str(action_id), {"action_id": str(action_id), "transition_ids": set(), "outcomes": []}
            )
            choice["transition_ids"].add(str(transitions[index]))
            choice["outcomes"].append(_route_outcome(entry, group["prefix_state"]))
    branch_points: list[dict[str, Any]] = []
    for group in raw_groups.values():
        if len(group["choices"]) < 2:
            continue
        choices = []
        for action_id, choice in sorted(group["choices"].items()):
            if len(choice["transition_ids"]) != 1:
                raise ReplayReviewViolation("One replay prefix/action pair resolves to conflicting transitions")
            outcomes = sorted(choice["outcomes"], key=lambda value: str(value["route_id"]))
            choices.append(
                {
                    "action_id": action_id,
                    "transition_id": next(iter(choice["transition_ids"])),
                    "terminal_route_count": len(outcomes),
                    "terminal_outcomes": outcomes,
                }
            )
        material = {
            "scenario": group["scenario"],
            "prefix_action_ids": group["prefix_action_ids"],
            "prefix_state_hash": group["prefix_state_hash"],
            "choices": choices,
        }
        branch_points.append(
            {
                "branch_point_id": "branch_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20],
                **material,
                "prefix_state": group["prefix_state"],
            }
        )
    ordered = sorted(branch_points, key=lambda value: (str(value["scenario"]), tuple(value["prefix_action_ids"])))
    material = {
        "schema": SYNTHETIC_REPLAY_REVIEW_SCHEMA,
        "head_sha": verified.head_sha,
        "corpus_id": verified.corpus_id,
        "branch_points": ordered,
    }
    return {
        "schema": SYNTHETIC_REPLAY_REVIEW_SCHEMA,
        "status": "synthetic_replay_review_board_verified",
        "review_board_id": "replay_review_" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:20],
        "head_sha": verified.head_sha,
        "corpus_id": verified.corpus_id,
        "corpus_schema": SYNTHETIC_REPLAY_CORPUS_SCHEMA,
        "scenario_ids": list(corpus["scenario_ids"]),
        "entry_count": len(verified.entries),
        "branch_point_count": len(ordered),
        "branch_points": ordered,
        "boundary": dict(corpus["boundary"]),
        "authority_note": "Read-only synthetic review evidence only; this board does not decide choices, authorize release, deploy, generate media, or process customer data.",
    }


def verify_verified_replay_review_board(head_sha: str, corpus: Mapping[str, Any], board: Mapping[str, Any]) -> dict[str, Any]:
    """Fail closed unless a supplied board equals the exact source derivation."""

    if not isinstance(board, Mapping):
        raise ReplayReviewViolation("Replay review board root must be an object")
    expected = build_verified_replay_review_board(head_sha, corpus)
    if canonical_json(dict(board)) != canonical_json(expected):
        raise ReplayReviewViolation("Replay review board does not exactly match the verified corpus derivation")
    return expected
