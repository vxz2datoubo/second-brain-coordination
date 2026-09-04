"""Director coverage matrix: prove the fail-closed compile contract across states.

For every state in the registered reachable corpus, exactly one of these must be
true:

    * ``compiles_deterministic`` -- a full asset index yields a generateable plan
      whose shot/brief identifiers are stable under repeated compilation;
    * ``explicit_missing_asset`` -- an incomplete asset index yields an explicit
      ``missing_asset`` finding (never a silent partial plan, empty shot list, or
      exception).

``unclassified`` is the failure class: a state that neither compiles nor declares
a missing asset would silently break the ``M-REACHABLE-STATE-DIRECTOR-COMPILABILITY-v1``
hard gate (ratio < 1.0). The probe asserts no such state exists.
"""

from __future__ import annotations

from typing import Any, Mapping

from creative_runtime.contracts import StoryState, canonical_json
from creative_runtime.director import compile_director

from . import FORMULA_REVISION, METRIC_ID, SCHEMA, states


CLASS_COMPILES = "compiles_deterministic"
CLASS_MISSING = "explicit_missing_asset"
CLASS_UNCLASSIFIED = "unclassified"


def classify(state: StoryState, assets: Mapping[str, Mapping[str, Any]]) -> str:
    """Classify one state under one asset index into exactly one contract class."""

    compilation = compile_director(state, dict(assets))
    report = compilation.quality_report
    finding_codes = {finding.code for finding in report.findings}

    if report.can_generate:
        return CLASS_COMPILES
    if "missing_asset" in finding_codes:
        return CLASS_MISSING
    return CLASS_UNCLASSIFIED


def _shot_signature(state: StoryState, assets: Mapping[str, Mapping[str, Any]]) -> str:
    """Return a canonical digest of the compiled plan for determinism checks."""

    compilation = compile_director(state, dict(assets))
    payload = {
        "brief_id": compilation.brief.brief_id,
        "shots": [shot.to_dict() for shot in compilation.shots],
        "can_generate": compilation.quality_report.can_generate,
    }
    return canonical_json(payload)


def run_matrix() -> dict[str, Any]:
    """Run the full coverage matrix and return its receipt body (pre-hash)."""

    corpus = states.reachable_states()
    full_assets = states.full_asset_index()
    variants = states.missing_asset_variants()

    rows: list[dict[str, Any]] = []
    unclassified: list[str] = []
    nondeterministic: list[str] = []

    for state in corpus:
        key = states.state_key(state)

        # Full index: must compile deterministically.
        full_class = classify(state, full_assets)
        signature_a = _shot_signature(state, full_assets)
        signature_b = _shot_signature(state, full_assets)
        deterministic = signature_a == signature_b
        if full_class != CLASS_COMPILES:
            unclassified.append(key + " [full_assets -> " + full_class + "]")
        if not deterministic:
            nondeterministic.append(key + " [full_assets nondeterministic]")

        # Each missing-asset variant: must declare missing_asset explicitly.
        variant_results: list[dict[str, Any]] = []
        for label, assets in variants:
            variant_class = classify(state, assets)
            variant_results.append(
                {"variant": label, "classification": variant_class}
            )
            if variant_class != CLASS_MISSING:
                unclassified.append(key + " [" + label + " -> " + variant_class + "]")

        rows.append(
            {
                "state_key": key,
                "scene_id": state.scene_id,
                "beat_id": state.beat_id,
                "known_facts": list(state.known_facts),
                "risk_level": state.risk_level,
                "full_assets_classification": full_class,
                "deterministic": deterministic,
                "missing_asset_variants": variant_results,
            }
        )

    total_states = len(corpus)
    total_scenarios = total_states * (1 + len(variants))
    covered_scenarios = total_scenarios - len(unclassified)
    coverage_ratio = covered_scenarios / total_scenarios if total_scenarios else 1.0

    return {
        "schema": SCHEMA,
        "metric_id": METRIC_ID,
        "formula_revision": FORMULA_REVISION,
        "population": "registered reachable synthetic story states",
        "reachable_states": total_states,
        "scenarios": total_scenarios,
        "covered_scenarios": covered_scenarios,
        "coverage_ratio": coverage_ratio,
        "target": 1.0,
        "unclassified_count": len(unclassified),
        "unclassified": unclassified,
        "nondeterministic_count": len(nondeterministic),
        "nondeterministic": nondeterministic,
        "rows": rows,
    }
