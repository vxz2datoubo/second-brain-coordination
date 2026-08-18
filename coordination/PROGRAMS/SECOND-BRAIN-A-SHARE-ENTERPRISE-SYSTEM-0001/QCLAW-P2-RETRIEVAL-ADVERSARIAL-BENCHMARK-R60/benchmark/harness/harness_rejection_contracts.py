from __future__ import annotations

from typing import Any

# Q60-B07: explicit machine-checkable rejection-reason contracts for every
# runnable R60 case that can PASS because an exception rejects the fixture or
# QueryPlan. A generic "some exception happened" is never sufficient evidence.
EXPECTED_REJECTION_ERROR_CODES: dict[str, tuple[str, ...]] = {
    "r60-005": ("query_plan_multi_privacy_requires_explicit_aggregate",),
    "r60-006": ("query_plan_historical_valid_time_required",),
    "r60-014": ("query_plan_truth_state_denied_or_unknown",),
    "r60-033": ("conversation_prompt_injection_denied",),
    "r60-034": ("credential_value_denied",),
    "r60-038": ("invalid_learning_packet:conversation_transport_visibility_denied",),
    "r60-039": ("invalid_learning_packet:knowledge_privacy_denied",),
    "r60-040": ("invalid_learning_packet:knowledge_metadata_required",),
    "r60-041": ("query_plan_user_scope_invalid",),
    "r60-042": ("query_plan_privacy_domains_invalid",),
    "r60-044": ("query_plan_or_memory_time_must_be_timezone_aware",),
    "r60-049": ("invalid_learning_packet:conversation_provenance_missing",),
    "r60-050": ("invalid_isoformat_string",),
    "r60-052": ("conversation_alias_enrichment_closed_atom_denied",),
    "r60-056": ("conversation_supersession_valid_time_invalid",),
    "r60-063": ("sqlite_foreign_key_constraint_failed",),
    "r60-072": (
        "invalid_learning_packet:conversation_metadata_required,conversation_packet_manifest_mismatch",
    ),
    "r60-080": ("invalid_learning_packet:conversation_prompt_injection_denied",),
    "r60-081": ("credential_value_denied",),
    "r60-082": ("credential_value_denied",),
    "r60-083": ("credential_value_denied",),
}


def rejection_error_code(exc: BaseException) -> str:
    """Return a deterministic rejection code without broad exception collapsing."""
    text = str(exc)
    if isinstance(exc, ValueError):
        if text.startswith("Invalid isoformat string:"):
            return "invalid_isoformat_string"
        return text
    if type(exc).__name__ == "IntegrityError" and "FOREIGN KEY constraint failed" in text:
        return "sqlite_foreign_key_constraint_failed"
    return f"{type(exc).__name__}:{text}"


def expected_rejection_error_codes(case: dict[str, Any]) -> tuple[str, ...]:
    return EXPECTED_REJECTION_ERROR_CODES.get(str(case.get("case_id", "")), ())


__all__ = [name for name in globals() if not name.startswith("__")]
