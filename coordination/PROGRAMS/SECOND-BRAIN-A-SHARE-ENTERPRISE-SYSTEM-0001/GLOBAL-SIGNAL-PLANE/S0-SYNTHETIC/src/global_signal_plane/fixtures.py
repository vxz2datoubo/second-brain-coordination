"""Synthetic event/snapshot builders. No connector, live GitHub, or private source is used."""
from __future__ import annotations

from typing import Any


def event(event_id: str, *, signal_id: str | None = None, source_sequence: int = 1, **overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "schema_version": "SignalEvent/v1", "signal_id": signal_id or f"signal-{event_id}", "event_id": event_id,
        "event_source": "synthetic://r134", "event_type": "synthetic.signal", "occurred_at": "2026-08-15T00:00:00+00:00",
        "observed_at": "2026-08-15T00:00:01+00:00", "source_type": "SYNTHETIC_FIXTURE", "source_ref": f"opaque://{event_id}",
        "source_project": "second-brain-synthetic", "source_actor": "synthetic-owner", "primary_domain": "W8",
        "related_domains": [], "signal_kind": "REQUIREMENT", "planning_state": "CAPTURED", "execution_state": "NOT_STARTED",
        "epistemic_state": "CONFIRMED_FACT", "privacy_scope_ref": "PUBLIC_SAFE", "authority_targets": [], "touch_set": ["S0C"],
        "related_signal_refs": [], "supersedes_refs": [], "revokes_refs": [], "cross_domain_candidate": False,
        "summary_ref": f"summary://{event_id}", "source_sequence": source_sequence, "idempotency_key": f"idem-{event_id}",
        "public_safe_metadata": {"fixture": True},
    }
    value.update(overrides)
    return value


def snapshot(**overrides: Any) -> dict[str, Any]:
    value = {"ledger_watermark": 1, "projection_version": 1, "main_sha": "main-A", "pr_head": "head-A", "pr_state": "OPEN", "active_routes": "route-134", "work_claim": "claim-active", "program_lane": "ACTIVE", "domain_snapshots": ["opaque-domain-ref-A"], "user_approval_state": "ACTIVE", "route_state": "READY", "same_agent_double_booked": False}
    value.update(overrides)
    return value
