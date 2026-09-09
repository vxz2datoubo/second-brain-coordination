"""B3 — Action/effect ledger: outbox, idempotency, budgets.

Side effects are recorded *before* execution (outbox), keyed by an idempotency
key, and reconciled after execution. On timeout/ACK-loss the outcome is
``OUTCOME_UNKNOWN`` (never silently ``NOT_EXECUTED``), forcing explicit
reconciliation. A budget envelope caps wall time, episode time, retries and
effect count.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .schemas import EffectStatus


class EffectsError(RuntimeError):
    """Raised on budget exhaustion or idempotency violation (fail closed)."""


@dataclass(frozen=True)
class BudgetEnvelope:
    """Bounded budget envelope (policy values, benchmark-tuned, not hard invariant)."""

    max_wall_time_ms: int = 3_600_000
    max_episode_ms: int = 600_000
    max_retries: int = 3
    max_effects: int = 1000
    allowed_paths: tuple[str, ...] = field(default_factory=tuple)
    forbidden_actions: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class EffectRecord:
    effect_id: str
    mission_id: str
    idempotency_key: str
    status: str
    attempts: int = 0
    created_at: float = 0.0
    executed_at: Optional[float] = None
    outcome: Optional[dict[str, Any]] = None


class EffectLedger:
    """In-memory effect ledger (outbox) with idempotency + budget enforcement.

    In the full kernel this is backed by the SQLite ledger; for the synthetic
    fixture it is a deterministic in-memory implementation with identical
    semantics so the invariants can be tested independently of persistence.
    """

    def __init__(self, budget: BudgetEnvelope | None = None):
        self._budget = budget or BudgetEnvelope()
        self._by_key: dict[str, EffectRecord] = {}
        self._by_id: dict[str, EffectRecord] = {}
        self._count = 0

    @property
    def budget(self) -> BudgetEnvelope:
        return self._budget

    def register(self, effect_id: str, mission_id: str, idempotency_key: str) -> EffectRecord:
        """Register a pending effect. Returns the existing record if the key repeats."""
        existing = self._by_key.get((mission_id, idempotency_key))
        if existing is not None:
            return existing  # idempotent: same key -> same effect
        if self._count >= self._budget.max_effects:
            raise EffectsError("BUDGET_EXCEEDED: max_effects reached")
        rec = EffectRecord(
            effect_id=effect_id,
            mission_id=mission_id,
            idempotency_key=idempotency_key,
            status=EffectStatus.PENDING.value,
            created_at=time.time(),
        )
        self._by_key[(mission_id, idempotency_key)] = rec
        self._by_id[effect_id] = rec
        self._count += 1
        return rec

    def mark_executed(self, effect_id: str, outcome: dict[str, Any] | None = None) -> None:
        rec = self._by_id[effect_id]
        rec.attempts += 1
        rec.status = EffectStatus.EXECUTED.value
        rec.executed_at = time.time()
        rec.outcome = outcome

    def mark_outcome_unknown(self, effect_id: str, reason: str) -> None:
        """ACK-loss / timeout -> OUTCOME_UNKNOWN (never NOT_EXECUTED)."""
        rec = self._by_id[effect_id]
        rec.attempts += 1
        rec.status = EffectStatus.OUTCOME_UNKNOWN.value
        rec.outcome = {"reason": reason}

    def get(self, effect_id: str) -> EffectRecord:
        return self._by_id[effect_id]

    def check_budget(self, elapsed_wall_ms: int, elapsed_episode_ms: int) -> None:
        if elapsed_wall_ms > self._budget.max_wall_time_ms:
            raise EffectsError("BUDGET_EXCEEDED: max_wall_time_ms")
        if elapsed_episode_ms > self._budget.max_episode_ms:
            raise EffectsError("BUDGET_EXCEEDED: max_episode_ms")

    def forbid_action(self, action: str) -> None:
        if action in self._budget.forbidden_actions:
            raise EffectsError(f"FORBIDDEN_ACTION: {action}")

    def is_path_allowed(self, path: str) -> bool:
        if not self._budget.allowed_paths:
            return True
        p = path.replace("\\", "/")
        for prefix in self._budget.allowed_paths:
            if prefix.endswith("/**"):
                base = prefix[: -len("/**")]
                if p == base or p.startswith(base + "/"):
                    return True
            elif p == prefix:
                return True
        return False
