"""Self-evolution log helpers."""

from __future__ import annotations

from typing import Any

from .contracts import SelfEvolutionLog
from .storage import BrainStore


class EvolutionManager:
    def __init__(self, store: BrainStore):
        self.store = store

    def record(
        self,
        trigger: str,
        observation: str,
        change_type: str = "learning",
        affected_ids: list[str] | None = None,
        proposed_update: str = "",
        applied: bool = False,
        metrics: dict[str, Any] | None = None,
    ) -> SelfEvolutionLog:
        log = SelfEvolutionLog(
            trigger=trigger,
            observation=observation,
            change_type=change_type,
            affected_ids=affected_ids or [],
            proposed_update=proposed_update,
            applied=applied,
            metrics=metrics or {},
        )
        self.store.save("evolution_logs", log)
        return log

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.store.list_records("evolution_logs", limit=limit)
