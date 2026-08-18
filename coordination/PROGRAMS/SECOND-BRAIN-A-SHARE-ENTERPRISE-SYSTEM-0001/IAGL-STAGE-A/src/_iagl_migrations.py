from __future__ import annotations

from _iagl_contracts import *


def audit_legacy_reconciliation_snapshot(store) -> None:
    store.connection.execute(
        """
        CREATE TABLE IF NOT EXISTS reconciliation_migration_audit (
            audit_id TEXT PRIMARY KEY,
            reconciliation_identity TEXT NOT NULL,
            reconciliation_generation INTEGER NOT NULL,
            event_key TEXT NOT NULL,
            decision TEXT NOT NULL,
            decision_ref TEXT NOT NULL,
            authority_source TEXT NOT NULL,
            outcome TEXT NOT NULL,
            legacy_item_digest TEXT NOT NULL
        )
        """
    )
    row = store.connection.execute(
        "SELECT identity,generation,snapshot FROM reconciliation WHERE slot=1"
    ).fetchone()
    if not row:
        return
    identity, generation, raw = row
    for item in legacy_unbound_p0_dispositions(raw):
        event_key = str(item.get("event_key", ""))
        decision = str(item.get("decision", ""))
        decision_ref = str(item.get("decision_ref", ""))
        authority_source = str(item.get("authority_source", "USER_DECISION"))
        item_digest = digest(item)
        outcome = "LEGACY_UNBOUND_P0_DISPOSITION_DROPPED_FAIL_CLOSED"
        audit_id = digest({
            "identity": identity,
            "generation": int(generation),
            "event_key": event_key,
            "decision_ref": decision_ref,
            "legacy_item_digest": item_digest,
            "outcome": outcome,
        })
        store.connection.execute(
            "INSERT OR IGNORE INTO reconciliation_migration_audit VALUES (?,?,?,?,?,?,?,?,?)",
            (
                audit_id,
                identity,
                int(generation),
                event_key,
                decision,
                decision_ref,
                authority_source,
                outcome,
                item_digest,
            ),
        )


__all__ = ("audit_legacy_reconciliation_snapshot",)
