"""Truthful per-event prefix timeline built only from validated saved sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .saves import SavedSession, SaveViolation


class TimelineViolation(SaveViolation):
    pass


@dataclass(frozen=True)
class TimelineEntry:
    index: int
    event_id: str
    state: dict[str, Any]
    consequence: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.index, "event_id": self.event_id, "state": self.state, "consequence": self.consequence}


def build_prefix_timeline(session: SavedSession) -> tuple[TimelineEntry, ...]:
    """Replay each prefix independently; never backfill final state into history."""

    # Validate the complete envelope first.  This establishes that every
    # prefix is either a deterministic migration prefix or legal graph action;
    # only then may the rendering loop replay the individual immutable prefix.
    session.state()
    entries: list[TimelineEntry] = []
    records = session.ledger.to_records()
    for index, record in enumerate(records):
        from .ledger import CreativeLedger
        prefix = CreativeLedger.from_records(records[: index + 1])
        try:
            state = prefix.replay(allow_migration_bridge=True)
        except (SaveViolation, ValueError) as error:
            raise TimelineViolation("Timeline prefix is not authoritative") from error
        payload = record["payload"]
        consequence = {
            "action_id": (payload.get("action") or {}).get("action_id"),
            "transition_id": payload.get("transition_id"),
            "event_type": record["event_type"],
        }
        entries.append(TimelineEntry(index, str(record["event_id"]), state.to_dict(), consequence))
    return tuple(entries)
