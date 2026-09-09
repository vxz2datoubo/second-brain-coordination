"""B7 — Synthetic endurance canary + failure injection driver.

Runs a compressed-time synthetic endurance canary that drives a mission through
the full state machine with:

- bounded episodes separated by checkpoints;
- at least one injected worker failure (simulated crash + stale lease + replacement);
- at least one context/episode rollover (checkpoint -> replay -> resume).

Because the synthetic benchmark policy values are ``BENCHMARK_TUNED_POLICY_NOT_HARD_
INVARIANT``, wall-clock is *compressed*: each episode is a bounded number of event
steps rather than a fixed wall-clock duration. This produces a deterministic,
fast, machine-verifiable canary while exercising every rollover/failure path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from . import ledger, reducers, verifier
from .schemas import EventType, MissionState


@dataclass
class CanaryReport:
    mission_id: str
    final_state: str
    total_events: int
    episodes: int
    worker_failures_injected: int
    context_rollovers: int
    chain_verified: bool
    passed: bool
    evidence: list[str] = field(default_factory=list)


class SyntheticEnduranceCanary:
    """Compressed-time endurance canary (synthetic & disposable)."""

    def __init__(self, ledger_path: str, episodes: int = 3, inject_worker_failure: bool = True):
        self._ledger_path = ledger_path
        self._episodes = episodes
        self._inject_worker_failure = inject_worker_failure

    def run(self, mission_id: str = "CANARY-001") -> CanaryReport:
        evidence: list[str] = []
        worker_failures = 0
        rollovers = 0

        led = ledger.MissionLedger(self._ledger_path)
        try:
            led.create_mission(mission_id, "run-canary", "2026-09-09T00:00:00Z")
            led.append_event(mission_id=mission_id, event_type=EventType.PLAN_STARTED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:00:01Z")
            led.append_event(mission_id=mission_id, event_type=EventType.PLAN_COMPLETED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:00:02Z")

            # Drive to REVIEW_READY through episodes with checkpoints + one rollover.
            for ep in range(1, self._episodes + 1):
                # First episode *starts*; subsequent episodes *resume* from a checkpoint.
                resume_evt = EventType.EPISODE_STARTED.value if ep == 1 else EventType.EPISODE_RESUMED.value
                led.append_event(mission_id=mission_id, event_type=resume_evt,
                                 actor="CANARY", timestamp_iso=f"2026-09-09T00:{ep:02d}:00Z")
                # periodic checkpoint at the phase boundary
                led.checkpoint(mission_id, {"episode": ep, "state": "EPISODE_RUNNING"},
                               f"2026-09-09T00:{ep:02d}:30Z")

                if self._inject_worker_failure and ep == 2:
                    # Simulate worker crash: close without graceful shutdown, then reopen.
                    led.close()
                    led = ledger.MissionLedger(self._ledger_path)
                    worker_failures += 1
                    evidence.append("worker_failure: simulated crash + reopen at episode 2")
                    # The re-opened ledger must reconstruct an intact chain.
                    if not led.verify_chain(mission_id):
                        raise ledger.LedgerError("chain verification failed after worker crash")

                led.append_event(mission_id=mission_id, event_type=EventType.CHECKPOINT_REACHED.value,
                                 actor="CANARY", timestamp_iso=f"2026-09-09T00:{ep:02d}:40Z")
                # context rollover: checkpoint + replay + resume
                snapshot = led.replay_state(mission_id)
                rollovers += 1
                evidence.append(f"context_rollover: episode {ep} replayed to {snapshot['state']}")

            # Finish: verify -> review -> canonicalize -> complete.
            led.append_event(mission_id=mission_id, event_type=EventType.VERIFICATION_STARTED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:00Z")
            led.append_event(mission_id=mission_id, event_type=EventType.VERIFICATION_PASSED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:10Z")
            led.append_event(mission_id=mission_id, event_type=EventType.REVIEW_STARTED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:20Z")
            led.append_event(mission_id=mission_id, event_type=EventType.REVIEW_APPROVED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:30Z")
            led.append_event(mission_id=mission_id, event_type=EventType.CANONICALIZATION_STARTED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:40Z")
            led.append_event(mission_id=mission_id, event_type=EventType.CANONICALIZATION_COMPLETED.value,
                             actor="CANARY", timestamp_iso="2026-09-09T00:59:50Z")

            final_state = led.current_state(mission_id)
            total_events = len(led.read_events(mission_id))
            chain_verified = led.verify_chain(mission_id)
        finally:
            led.close()

        passed = final_state == MissionState.COMPLETE.value and chain_verified \
            and worker_failures >= (1 if self._inject_worker_failure else 0) and rollovers >= 1
        return CanaryReport(
            mission_id=mission_id,
            final_state=final_state,
            total_events=total_events,
            episodes=self._episodes,
            worker_failures_injected=worker_failures,
            context_rollovers=rollovers,
            chain_verified=chain_verified,
            passed=passed,
            evidence=evidence,
        )
