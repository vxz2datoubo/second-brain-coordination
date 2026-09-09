"""B1 — Independent hash-chain verifier.

This verifier is deliberately independent from the ledger write path: it takes a
list of already-serialized event records and re-computes every hash from scratch,
re-checking monotonic ``state_seq`` and the ``previous_event_hash`` linkage.
"""

from __future__ import annotations

from typing import Any

from . import canonical, schemas
from .schemas import EventType


class ChainVerificationError(ValueError):
    """Raised when the event chain is invalid (hash, order, or linkage)."""


def verify_event_chain(events: list[dict[str, Any]]) -> bool:
    """Verify a full event chain in order.

    Each event dict must contain at least: ``state_seq``, ``event_type``,
    ``previous_event_hash``, ``event_hash``, ``mission_id``, ``run_id``,
    ``actor``, ``timestamp_iso``, ``payload``, ``digests``.

    Returns True when every linkage, hash, and sequence invariant holds; raises
    :class:`ChainVerificationError` otherwise (fail closed).
    """
    if not events:
        raise ChainVerificationError("empty event chain")

    expected_seq = 0
    prev_hash = canonical.GENESIS_PREVIOUS_HASH
    seen_hashes: set[str] = set()

    for i, ev in enumerate(events):
        state_seq = ev["state_seq"]
        event_type = ev["event_type"]

        if state_seq != expected_seq:
            raise ChainVerificationError(
                f"state_seq out of order at index {i}: expected {expected_seq}, got {state_seq}"
            )
        expected_seq += 1

        if ev["previous_event_hash"] != prev_hash:
            raise ChainVerificationError(
                f"previous_event_hash mismatch at index {i}: expected {prev_hash}, got {ev['previous_event_hash']}"
            )

        if i == 0 and event_type != EventType.GENESIS.value:
            raise ChainVerificationError("first event must be GENESIS")

        recomputed = canonical.event_hash(
            prev_hash,
            mission_id=ev["mission_id"],
            run_id=ev["run_id"],
            state_seq=state_seq,
            event_type=event_type,
            actor=ev["actor"],
            timestamp_iso=ev["timestamp_iso"],
            payload=ev["payload"],
            digests=ev.get("digests", {}),
        )
        if recomputed != ev["event_hash"]:
            raise ChainVerificationError(
                f"event_hash mismatch at index {i}: stored {ev['event_hash']} != recomputed {recomputed}"
            )

        if ev["event_hash"] in seen_hashes:
            raise ChainVerificationError(f"duplicate event_hash at index {i}")
        seen_hashes.add(ev["event_hash"])
        prev_hash = ev["event_hash"]

    return True


def build_genesis_event(*, mission_id: str, run_id: str, actor: str,
                        timestamp_iso: str, payload: Any = None) -> dict[str, Any]:
    """Construct the GENESIS event for a mission (state_seq=0)."""
    payload = {} if payload is None else payload
    prev = canonical.GENESIS_PREVIOUS_HASH
    h = canonical.event_hash(
        prev,
        mission_id=mission_id,
        run_id=run_id,
        state_seq=0,
        event_type=EventType.GENESIS.value,
        actor=actor,
        timestamp_iso=timestamp_iso,
        payload=payload,
    )
    return {
        "mission_id": mission_id,
        "run_id": run_id,
        "state_seq": 0,
        "event_type": EventType.GENESIS.value,
        "previous_event_hash": prev,
        "event_hash": h,
        "actor": actor,
        "timestamp_iso": timestamp_iso,
        "payload": payload,
        "digests": {},
    }
