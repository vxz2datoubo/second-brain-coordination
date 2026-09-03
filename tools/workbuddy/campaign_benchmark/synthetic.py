"""Deterministic synthetic campaign construction for offline benchmarking.

Every campaign is a pure function of ``(seed, event_count, style)``. Nothing here
touches the network, the filesystem, credentials or real player data.

The generator only emits payloads that ``creative_runtime.ledger`` already
accepts, so it stays a consumer of the fixed contract rather than a new one.
"""

from __future__ import annotations

import random
from typing import Any, Mapping

from creative_runtime.contracts import StoryState
from creative_runtime.ledger import CreativeLedger

# Fixed, offline vocabulary. Names are invented and carry no real-person meaning.
STYLES: tuple[str, ...] = ("noir_chamber", "daylight_docu", "neon_procedural")
CHARACTERS: tuple[str, ...] = ("lia", "moran", "inspector_vu", "the_archivist")
FACT_POOL: tuple[str, ...] = (
    "harbour_ledger_missing_page",
    "second_key_found",
    "archivist_lied_about_alibi",
    "storm_cut_the_ferry",
    "radio_relay_still_live",
)
SCENE_POOL: tuple[str, ...] = ("sc_harbour", "sc_archive", "sc_ferry", "sc_relay")
BEAT_POOL: tuple[str, ...] = ("bt_open", "bt_pressure", "bt_reversal", "bt_aftermath")


def initial_state(seed: int) -> StoryState:
    """Return the deterministic starting state for a synthetic campaign."""

    rng = random.Random(f"init/{seed}")
    return StoryState(
        scene_id=rng.choice(SCENE_POOL),
        beat_id="bt_open",
        relationships={name: rng.randint(-2, 2) for name in CHARACTERS},
        known_facts=(),
        risk_level=0,
        flags={"style": STYLES[seed % len(STYLES)]},
    )


def _patch(rng: random.Random, index: int, state_scene: str) -> dict[str, Any]:
    """Build one legal state patch inside the runtime's small patch language."""

    patch: dict[str, Any] = {
        "scene_id": rng.choice(SCENE_POOL),
        "beat_id": BEAT_POOL[index % len(BEAT_POOL)],
    }
    patch["relationship_delta"] = {rng.choice(CHARACTERS): rng.randint(-3, 3)}
    if rng.random() < 0.45:
        patch["reveal_facts"] = [rng.choice(FACT_POOL)]
    patch["risk_delta"] = rng.randint(-1, 2)
    if rng.random() < 0.25:
        patch["flags"] = {"tone": rng.choice(("tense", "calm", "grim"))}
    patch["scene_id"] = state_scene if rng.random() < 0.3 else patch["scene_id"]
    return patch


def build_campaign(seed: int, event_count: int, style: str | None = None) -> CreativeLedger:
    """Build a replayable synthetic campaign ledger of exactly ``event_count`` events.

    ``event_count`` counts the ``story_initialized`` event, so the minimum is 1.
    """

    if event_count < 1:
        raise ValueError("event_count must be >= 1")
    resolved_style = style or STYLES[seed % len(STYLES)]
    if resolved_style not in STYLES:
        raise ValueError("unknown style: " + resolved_style)

    rng = random.Random(f"campaign/{seed}/{event_count}/{resolved_style}")
    state = initial_state(seed)
    state = StoryState(
        scene_id=state.scene_id,
        beat_id=state.beat_id,
        relationships=dict(state.relationships),
        known_facts=state.known_facts,
        risk_level=state.risk_level,
        flags={**state.flags, "style": resolved_style},
    )

    ledger = CreativeLedger()
    ledger.append(
        "story_initialized",
        {"state": state.to_dict(), "style": resolved_style, "seed": seed},
        occurred_at="2026-01-01T00:00:00Z",
    )

    for index in range(1, event_count):
        patch = _patch(rng, index, state.scene_id)
        # Alternate the two legal patch-carrying event types so replay exercises
        # both branches of CreativeLedger.replay.
        if index % 2 == 0:
            ledger.append(
                "player_action",
                {
                    "action_id": "act_%05d" % index,
                    "kind": "dialogue" if index % 4 else "movement",
                    "text": "synthetic line %d" % index,
                    "resulting_patch": patch,
                },
                occurred_at="2026-01-01T00:%02d:%02dZ" % (index // 60 % 60, index % 60),
            )
        else:
            ledger.append(
                "state_patch",
                {"patch": patch, "reason": "synthetic drift %d" % index},
                occurred_at="2026-01-01T00:%02d:%02dZ" % (index // 60 % 60, index % 60),
            )

    return ledger


def campaign_records(ledger: CreativeLedger) -> list[dict[str, Any]]:
    """Serialize a ledger for storage accounting and resume/replay simulation."""

    return ledger.to_records()


def simulate_campaign_hours(seed: int, event_count: int) -> float:
    """Return a deterministic SIMULATED campaign duration in hours.

    The population for M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1 is described as
    "synthetic 45-60 minute complete campaigns", so simulated durations are
    pinned inside that window and derived only from deterministic inputs.
    This is a modelling input, never measured user time.
    """

    if event_count < 1:
        raise ValueError("event_count must be >= 1")
    rng = random.Random(f"hours/{seed}/{event_count}")
    minutes = 45.0 + rng.random() * 15.0  # 45..60 minutes inclusive-ish
    return round(minutes / 60.0, 6)


def summary(ledger: CreativeLedger) -> Mapping[str, Any]:
    """Return a small deterministic summary used in receipts."""

    state = ledger.replay()
    return {
        "event_count": len(ledger.events),
        "head_event_hash": ledger.events[-1].event_hash if ledger.events else None,
        "final_scene_id": state.scene_id,
        "final_beat_id": state.beat_id,
        "final_risk_level": state.risk_level,
        "known_fact_count": len(state.known_facts),
    }
