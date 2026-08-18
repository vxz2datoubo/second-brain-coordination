"""R142 F03 evidence-first derivation helpers.

Expected dispositions are deliberately absent from every evidence-construction
API. Current evidence is verified first; disposition remains the responsibility
of the existing retrospective reconciler.
"""
from __future__ import annotations

import copy
from collections import Counter
from typing import Any, Mapping

FACT_CLASSES = frozenset({
    "CURRENT_CANONICAL_MATCH",
    "CURRENT_CAPABILITY_SATISFIED",
    "DOMAIN_CURRENT_ONLY",
    "UNRESOLVED_CURRENT_STATE",
    "CURRENT_UNMET",
})

_CLASS_TO_SLOT = {
    "CURRENT_CANONICAL_MATCH": "current_signal_refs",
    "CURRENT_CAPABILITY_SATISFIED": "satisfied_refs",
    "DOMAIN_CURRENT_ONLY": "domain_canonical_refs",
    "UNRESOLVED_CURRENT_STATE": "needs_revalidation_refs",
}

_EVIDENCE_ARRAYS = (
    "current_signal_refs", "historical_signal_refs", "satisfied_refs",
    "duplicate_refs", "extends_refs", "reinforces_refs", "contradicts_refs",
    "superseded_refs", "domain_canonical_refs", "needs_revalidation_refs",
    "active_dependency_refs", "closed_task_refs", "issue_pr_review_refs",
    "capability_refs",
)


def expand_source_fragment_refs(package: Mapping[str, Any]) -> dict[str, Any]:
    """Expand package-local fragment refs to the real File Library artifact."""
    out = copy.deepcopy(dict(package))
    metadata = out.get("package_metadata")
    if not isinstance(metadata, Mapping):
        raise ValueError("R142_SOURCE_METADATA_REQUIRED")
    source = metadata.get("source_artifact_ref")
    if not isinstance(source, str) or not source:
        raise ValueError("R142_SOURCE_ARTIFACT_REF_REQUIRED")

    def expand(value: Any) -> Any:
        if isinstance(value, str):
            if value == "artifact":
                return source
            if value.startswith("fragment:"):
                fragment = value.split(":", 1)[1]
                if not fragment:
                    raise ValueError("R142_EMPTY_SOURCE_FRAGMENT")
                return f"{source}#{fragment}"
            return value
        if isinstance(value, list):
            return [expand(item) for item in value]
        if isinstance(value, dict):
            return {key: expand(item) for key, item in value.items()}
        return value

    candidates = out.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("R142_CANDIDATES_REQUIRED")
    out["candidates"] = [expand(item) for item in candidates]
    return out


def verify_fact_catalog(
    plan: Mapping[str, Any],
    text_by_alias: Mapping[str, str],
    exact_ref_by_alias: Mapping[str, str],
) -> dict[str, dict[str, Any]]:
    """Verify literal predicates against exact-current-main content.

    No expected disposition, count, or oracle value is accepted here.
    """
    catalog = plan.get("fact_catalog")
    if not isinstance(catalog, Mapping) or not catalog:
        raise ValueError("R142_FACT_CATALOG_REQUIRED")
    results: dict[str, dict[str, Any]] = {}
    for fact_id, raw in catalog.items():
        if not isinstance(raw, Mapping):
            raise ValueError("R142_FACT_SPEC_INVALID")
        fact_class = raw.get("fact_class")
        checks = raw.get("checks")
        if fact_class not in FACT_CLASSES or not isinstance(checks, list) or not checks:
            raise ValueError("R142_FACT_SPEC_INVALID")
        check_results = []
        refs: list[str] = []
        all_verified = True
        for check in checks:
            if not isinstance(check, Mapping):
                raise ValueError("R142_FACT_CHECK_INVALID")
            alias = check.get("alias")
            terms = check.get("contains_all")
            if alias not in text_by_alias or alias not in exact_ref_by_alias:
                raise ValueError(f"R142_FACT_ALIAS_UNBOUND:{alias}")
            if not isinstance(terms, list) or not terms or not all(isinstance(term, str) and term for term in terms):
                raise ValueError("R142_FACT_TERMS_INVALID")
            text = text_by_alias[alias]
            missing = [term for term in terms if term not in text]
            verified = not missing
            all_verified = all_verified and verified
            ref = exact_ref_by_alias[alias]
            refs.append(ref)
            check_results.append({
                "alias": alias,
                "verified": verified,
                "missing_predicates": missing,
                "evidence_ref": ref,
            })
        results[str(fact_id)] = {
            "fact_class": fact_class,
            "verified": all_verified,
            "evidence_refs": sorted(set(refs)),
            "checks": check_results,
        }
    return results


def build_candidate_evidence(
    binding: Mapping[str, Any],
    fact_results: Mapping[str, Mapping[str, Any]],
    *,
    provider_ref: str,
    capability_ref: str,
    domain_current_ref: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build reconciler evidence only from verified fact results.

    Intentionally has no expected-disposition/oracle parameter.
    """
    fact_ids = binding.get("fact_ids")
    if not isinstance(fact_ids, list) or not fact_ids:
        raise ValueError("R142_CANDIDATE_FACT_BINDING_REQUIRED")
    selected = []
    attempted_refs: list[str] = []
    for fact_id in fact_ids:
        result = fact_results.get(str(fact_id))
        if not isinstance(result, Mapping):
            raise ValueError(f"R142_FACT_RESULT_MISSING:{fact_id}")
        attempted_refs.extend(map(str, result.get("evidence_refs", [])))
        if result.get("verified") is True:
            selected.append((str(fact_id), result))

    arrays: dict[str, Any] = {name: [] for name in _EVIDENCE_ARRAYS}
    arrays["issue_pr_review_refs"] = [provider_ref]
    arrays["capability_refs"] = [capability_ref]
    arrays["provenance_complete"] = True
    arrays["desired_effect_unmet"] = False

    if not selected:
        arrays["needs_revalidation_refs"] = sorted(set(attempted_refs + [provider_ref]))
        return arrays, {
            "derivation": "FAIL_CLOSED_UNVERIFIED_CURRENT_FACT",
            "verified_fact_ids": [],
            "fact_classes": [],
            "attempted_evidence_refs": sorted(set(attempted_refs)),
        }

    classes = {str(result["fact_class"]) for _, result in selected}
    if len(classes) != 1:
        arrays["needs_revalidation_refs"] = sorted(set(attempted_refs + [provider_ref]))
        return arrays, {
            "derivation": "FAIL_CLOSED_AMBIGUOUS_FACT_CLASSES",
            "verified_fact_ids": sorted(fact_id for fact_id, _ in selected),
            "fact_classes": sorted(classes),
            "attempted_evidence_refs": sorted(set(attempted_refs)),
        }

    fact_class = next(iter(classes))
    refs = sorted(set(
        ref for _, result in selected for ref in map(str, result.get("evidence_refs", []))
    ))
    if fact_class == "CURRENT_UNMET":
        arrays["desired_effect_unmet"] = True
    else:
        slot = _CLASS_TO_SLOT[fact_class]
        if fact_class == "DOMAIN_CURRENT_ONLY":
            if not domain_current_ref:
                arrays["needs_revalidation_refs"] = sorted(set(refs + [provider_ref]))
                return arrays, {
                    "derivation": "FAIL_CLOSED_DOMAIN_CURRENT_EVIDENCE_MISSING",
                    "verified_fact_ids": sorted(fact_id for fact_id, _ in selected),
                    "fact_classes": [fact_class],
                    "attempted_evidence_refs": refs,
                }
            refs = sorted(set(refs + [domain_current_ref]))
        arrays[slot] = refs

    return arrays, {
        "derivation": "VERIFIED_CURRENT_FACT",
        "verified_fact_ids": sorted(fact_id for fact_id, _ in selected),
        "fact_classes": [fact_class],
        "evidence_refs": refs,
    }


def compare_post_hoc_oracle(
    actual: Mapping[str, str],
    oracle: Mapping[str, Any],
) -> dict[str, Any]:
    """Report legacy expectation drift without affecting pass/fail or evidence."""
    counts = dict(sorted(Counter(actual.values()).items()))
    legacy_counts = oracle.get("legacy_disposition_counts", {})
    legacy_candidate_count = oracle.get("legacy_candidate_count")
    return {
        "authoritative": False,
        "label": oracle.get("label", "NON_AUTHORITATIVE_POST_HOC_ORACLE"),
        "mismatch_is_failure": False,
        "actual_candidate_count": len(actual),
        "actual_disposition_counts": counts,
        "legacy_candidate_count": legacy_candidate_count,
        "legacy_disposition_counts": dict(legacy_counts) if isinstance(legacy_counts, Mapping) else {},
        "candidate_count_matches_legacy": str(len(actual)) == str(legacy_candidate_count),
        "disposition_counts_match_legacy": counts == dict(legacy_counts) if isinstance(legacy_counts, Mapping) else False,
    }
