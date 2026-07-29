"""Fail-closed validation for semantically distinct Evaluation V2 catalogs."""
from __future__ import annotations

from typing import Iterable


def assert_distinct_semantic_signatures(kind: str, specs: Iterable[object], minimum: int) -> None:
    rows = tuple(specs)
    if len(rows) < minimum:
        raise AssertionError("E23_CATALOG_MINIMUM_NOT_MET:" + kind)
    seen_cases: set[tuple[str, str]] = set()
    for spec in rows:
        signatures = getattr(spec, "signatures", None)
        if type(signatures) is not tuple or len(signatures) != 2:
            raise AssertionError("E23_CATALOG_SIGNATURE_MISSING:" + kind)
        input_signature, relation_signature = signatures
        semantic_case = (input_signature, relation_signature)
        if semantic_case in seen_cases:
            raise AssertionError("E23_DUPLICATE_NORMALIZED_SEMANTIC_SIGNATURE:" + kind + ":" + input_signature)
        seen_cases.add(semantic_case)


def assert_catalogs_distinct(
    scenarios: Iterable[object],
    invariants: Iterable[object],
    negatives: Iterable[object],
    episodes: Iterable[object],
    counterfactuals: Iterable[object],
    cross_family: Iterable[object],
) -> None:
    assert_distinct_semantic_signatures("scenarios", scenarios, 72)
    assert_distinct_semantic_signatures("invariants", invariants, 80)
    assert_distinct_semantic_signatures("negatives", negatives, 37)
    assert_distinct_semantic_signatures("episodes", episodes, 24)
    assert_distinct_semantic_signatures("counterfactuals", counterfactuals, 36)
    assert_distinct_semantic_signatures("cross_family", cross_family, 24)
