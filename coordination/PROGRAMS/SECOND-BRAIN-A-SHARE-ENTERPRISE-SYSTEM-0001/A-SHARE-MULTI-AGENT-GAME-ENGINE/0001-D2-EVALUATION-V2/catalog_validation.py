"""Fail-closed validation for execution-derived Evaluation V2 catalogs."""
from __future__ import annotations

from typing import Iterable

from evaluation_v2_contract import canonical_sha256


def assert_distinct_execution_cases(kind: str, cases: Iterable[dict[str, object]], minimum: int = 1) -> None:
    """Reject coverage credit unless the executed input and observed relation differ.

    The caller supplies the public input actually consumed by the fixture and
    the relation actually checked by its named predicate/oracle.  Author
    supplied labels and identifiers deliberately never participate.
    """
    rows = tuple(cases)
    if len(rows) < minimum:
        raise AssertionError("E24_CATALOG_MINIMUM_NOT_MET:" + kind)
    seen_cases: set[tuple[str, str]] = set()
    for case in rows:
        if not {"id", "executed_input", "observed_relation"} <= set(case):
            raise AssertionError("E24_EXECUTION_CASE_MISSING:" + kind)
        input_signature = canonical_sha256({"kind": kind, "input": case["executed_input"]})
        relation_signature = canonical_sha256({"kind": kind, "relation": case["observed_relation"]})
        semantic_case = (input_signature, relation_signature)
        if semantic_case in seen_cases:
            raise AssertionError("E24_DUPLICATE_EXECUTION_SIGNATURE:" + kind + ":" + input_signature)
        seen_cases.add(semantic_case)
        case["execution_signatures"] = semantic_case


def assert_catalogs_distinct(catalogs: dict[str, Iterable[dict[str, object]]]) -> None:
    for kind, cases in sorted(catalogs.items()):
        assert_distinct_execution_cases(kind, cases)
