"""Durable Mission Kernel (R188 Phase B) — synthetic & disposable fixture implementation.

This package implements a Windows-local resumable Durable Mission Kernel that
*reuses* the existing Unified Execution Fabric rather than creating a second
control plane. It preserves long-horizon progress across bounded episodes,
context rollover and worker failure using:

- deterministic state reducers (B1)
- RFC8785/JCS-compatible canonical event bytes + SHA-256 hash chain (B1)
- a single-controller SQLite mission ledger with checkpoint/replay (B2)
- an action/effect ledger with outbox + idempotency + budgets + lease fencing (B3)
- Windows Job Object hard process-tree containment + orphan reaper (B4)
- a WorkBuddy headless adapter + runtime/model attestation (B5)
- reviewer/canonicalizer independence protocols (B6)

IMPORTANT: This is a SYNTHETIC_AND_DISPOSABLE_FIXTURE_ONLY implementation.
A synthetic PASS does NOT imply production/real-canonicalizer readiness.
"""

from __future__ import annotations

__version__ = "0.1.0"
__task_id__ = "WORKBUDDY-R188-PHASE-B-DURABLE-MISSION-KERNEL"

from . import canonical, containment, effects, endurance, headless, lease, ledger, protocols, reducers, schemas, verifier  # noqa: E402,F401

__all__ = [
    "__version__",
    "__task_id__",
    "canonical",
    "containment",
    "effects",
    "endurance",
    "headless",
    "lease",
    "ledger",
    "protocols",
    "reducers",
    "schemas",
    "verifier",
]
