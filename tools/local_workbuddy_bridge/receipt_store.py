"""Durable local launch/idempotency receipt store.

Rule (TASK-BRIEF.yaml): "Use durable local idempotency/launch receipts keyed to
canonical task and immutable writer lease identity."

Idempotency rule (TASK-BRIEF.yaml adversarial tests):
  "duplicate launch with same immutable authority is idempotently rejected or
   resumed without second writer"

A durable store means a file-backed JSON store, not in-memory state that a
restart would lose.
"""
from __future__ import annotations

import json
import time
from hashlib import sha256
from pathlib import Path

from .contracts import BridgeDecision, LaunchReceipt
from .redaction import assert_no_secrets, redact


class LaunchReceiptStore:
    """File-backed receipt store. Survives process restart."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._path = self.root / "launch-receipts.json"

    # -- persistence -----------------------------------------------------
    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_text(encoding="utf-8")
        except OSError:
            return {}
        if not raw.strip():
            return {}
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict) -> None:
        payload = json.dumps(data, indent=2, sort_keys=True)
        assert_no_secrets(payload, where="launch-receipts.json")
        self._path.write_text(payload, encoding="utf-8")

    # -- identity --------------------------------------------------------
    @staticmethod
    def idempotency_key(task_id: str, route_epoch: int, execution_identity: str) -> str:
        # Mirrors the broker key material so duplicates are detected across layers.
        raw = f"{task_id}\0{route_epoch}\0{execution_identity}"
        return sha256(raw.encode("utf-8")).hexdigest()

    # -- api -------------------------------------------------------------
    def find(self, idempotency_key: str) -> LaunchReceipt | None:
        data = self._load()
        entry = data.get(idempotency_key)
        if not entry:
            return None
        return LaunchReceipt(
            receipt_id=entry["receipt_id"],
            task_id=entry["task_id"],
            route_epoch=entry["route_epoch"],
            execution_identity=entry["execution_identity"],
            idempotency_key=idempotency_key,
            decision=BridgeDecision(entry["decision"]),
            created_at_ms=entry["created_at_ms"],
            dry_run=bool(entry.get("dry_run", True)),
        )

    def record(
        self,
        *,
        task_id: str,
        route_epoch: int,
        execution_identity: str,
        decision: BridgeDecision,
    ) -> LaunchReceipt:
        key = self.idempotency_key(task_id, route_epoch, execution_identity)
        existing = self.find(key)
        if existing is not None:
            # Idempotent: return the prior receipt, never create a second writer.
            return existing

        created = int(time.time() * 1000)
        receipt_id = "LR-" + sha256(f"{key}{created}".encode()).hexdigest()[:24]
        receipt = LaunchReceipt(
            receipt_id=receipt_id,
            task_id=redact(task_id),
            route_epoch=route_epoch,
            execution_identity=execution_identity,
            idempotency_key=key,
            decision=decision,
            created_at_ms=created,
            dry_run=True,
        )
        data = self._load()
        data[key] = {
            "receipt_id": receipt.receipt_id,
            "task_id": receipt.task_id,
            "route_epoch": receipt.route_epoch,
            "execution_identity": receipt.execution_identity,
            "decision": receipt.decision.value,
            "created_at_ms": receipt.created_at_ms,
            "dry_run": True,
        }
        self._save(data)
        return receipt

    def count(self) -> int:
        return len(self._load())
