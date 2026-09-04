"""Deterministic synthetic story-state corpus for the director coverage matrix.

The corpus is a pure function of its inputs. It does not invent new runtime
registration, add a script graph, or widen the director contract: it enumerates
the scene/beat vocabulary that is *already registered* in the current checkpoint
-- the values the offline director's synthetic asset index and the existing
creative test slices actually use -- into replayable ``StoryState`` objects, then
hands them to ``compile_director`` unchanged.

The vocabulary below is derived from the checkpoint's own artifacts:

    * ``director.synthetic_asset_index()`` exposes one scene asset
      (``art_scene_synthetic_archive`` -> scene ``synthetic_archive``) and two
      adult character assets.
    * ``tests/test_creative_s01_ledger.py`` exercises ``atrium`` / ``arrival`` /
      ``echo``.
    * ``tests/test_creative_s03_director.py`` and ``test_creative_s05_generation.py``
      exercise ``synthetic_archive`` / ``arrival`` / ``echo``.

Because ``compile_director_brief`` only uses ``scene_id`` and ``beat_id`` to build
the brief/shot identifiers and hard-codes knowledge boundaries from the state's
own ``known_facts``, the matrix's real job is to prove the fail-closed contract
holds across that registered vocabulary: every state either compiles a
deterministic, generateable plan (full asset index) or declares a missing asset
explicitly (incomplete index).
"""

from __future__ import annotations

from creative_runtime.contracts import StoryState
from creative_runtime.director import synthetic_asset_index


# Scene/beat vocabulary already registered in the current checkpoint. These are
# the literal ``scene_id`` / ``beat_id`` values the checkpoint's own director and
# creative test slices use; the probe reuses them rather than inventing new ones.
SCENES: tuple[str, ...] = ("synthetic_archive", "atrium")
BEATS: tuple[str, ...] = ("arrival", "echo")
# The one registered fact used by the director's knowledge-boundary test.
KNOWN_FACTS: tuple[str, ...] = ("a witness is inside",)

# Reference artifact ids the checkpoint director hard-codes into its shot plan.
REFERENCE_ARTIFACT_IDS: tuple[str, ...] = (
    "art_scene_synthetic_archive",
    "art_character_mira",
    "art_character_player",
)


def full_asset_index() -> dict[str, dict]:
    """Return a copy of the checkpoint's synthetic asset index (all refs present)."""

    return dict(synthetic_asset_index())


def missing_asset_variants() -> tuple[tuple[str, dict], ...]:
    """Return ``(label, assets)`` where exactly one reference asset is removed.

    Each variant must trigger an explicit ``missing_asset`` finding, never a
    silent partial plan, an empty shot list, or an exception.
    """

    variants: list[tuple[str, dict]] = []
    for artifact_id in REFERENCE_ARTIFACT_IDS:
        assets = full_asset_index()
        assets.pop(artifact_id)
        variants.append(("missing_" + artifact_id, assets))
    return tuple(variants)


def reachable_states() -> tuple[StoryState, ...]:
    """Enumerate the deterministic synthetic reachable-state corpus.

    The corpus is the cartesian product of registered scenes x beats x two
    knowledge-boundary shapes x two risk levels, deduplicated. Every state is a
    legal ``StoryState`` the ledger patch language can express.
    """

    states: list[StoryState] = []
    for scene_id in SCENES:
        for beat_id in BEATS:
            for facts in ((), KNOWN_FACTS):
                for risk_level in (0, 2):
                    states.append(
                        StoryState(
                            scene_id=scene_id,
                            beat_id=beat_id,
                            relationships={"mira": 0, "player": 0},
                            known_facts=facts,
                            risk_level=risk_level,
                            flags={"style": "noir_chamber"},
                        )
                    )
    return tuple(states)


def state_key(state: StoryState) -> str:
    """Return a stable, human-readable key for one state."""

    return "|".join(
        (
            state.scene_id,
            state.beat_id,
            ",".join(state.known_facts) or "-",
            str(state.risk_level),
        )
    )
