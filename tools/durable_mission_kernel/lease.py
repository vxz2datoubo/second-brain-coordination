"""B3 — Runtime lease + fencing + stale-worker replacement.

A runtime lease is separate from the canonical task lease. It fences a single
collision domain to one executor at a time, expires stale leases, and fences an
old attempt before a replacement worker may emit effects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from .schemas import LeaseStatus


class LeaseError(RuntimeError):
    """Raised on lease conflicts or fencing violations (fail closed)."""


@dataclass
class RuntimeLease:
    lease_id: str
    mission_id: str
    executor_id: str
    collision_domain: str
    start_ts: int
    expiry_ts: int
    renewed_ts: int
    status: str = LeaseStatus.ACTIVE.value


class LeaseManager:
    """Single-writer lease fencing per collision domain."""

    def __init__(self, ttl_ms: int = 30_000, clock=time.time):
        self._ttl_ms = ttl_ms
        self._clock = clock
        self._by_domain: dict[str, RuntimeLease] = {}
        self._by_id: dict[str, RuntimeLease] = {}

    def _now_ms(self) -> int:
        return int(self._clock() * 1000)

    def acquire(self, lease_id: str, mission_id: str, executor_id: str,
                collision_domain: str) -> RuntimeLease:
        """Acquire a lease for a collision domain, fencing any stale prior holder."""
        now = self._now_ms()
        existing = self._by_domain.get(collision_domain)
        if existing is not None and existing.status == LeaseStatus.ACTIVE.value:
            if existing.executor_id != executor_id:
                # Same-surface second writer forbidden unless the old lease is stale.
                if existing.expiry_ts > now:
                    raise LeaseError(
                        f"LEASE_CONFLICT: domain {collision_domain} held by "
                        f"{existing.executor_id} until {existing.expiry_ts}"
                    )
                self._fence(existing)
            else:
                # Same executor renewing its own lease.
                return self.renew(existing.lease_id)

        lease = RuntimeLease(
            lease_id=lease_id,
            mission_id=mission_id,
            executor_id=executor_id,
            collision_domain=collision_domain,
            start_ts=now,
            expiry_ts=now + self._ttl_ms,
            renewed_ts=now,
        )
        self._by_domain[collision_domain] = lease
        self._by_id[lease_id] = lease
        return lease

    def renew(self, lease_id: str) -> RuntimeLease:
        lease = self._by_id[lease_id]
        if lease.status != LeaseStatus.ACTIVE.value:
            raise LeaseError(f"Cannot renew non-active lease {lease_id}")
        now = self._now_ms()
        lease.renewed_ts = now
        lease.expiry_ts = now + self._ttl_ms
        return lease

    def release(self, lease_id: str) -> None:
        lease = self._by_id[lease_id]
        lease.status = LeaseStatus.RELEASED.value
        if self._by_domain.get(lease.collision_domain) is lease:
            del self._by_domain[lease.collision_domain]

    def _fence(self, lease: RuntimeLease) -> None:
        lease.status = LeaseStatus.FENCED.value
        if self._by_domain.get(lease.collision_domain) is lease:
            del self._by_domain[lease.collision_domain]

    def is_fenced(self, lease_id: str) -> bool:
        lease = self._by_id.get(lease_id)
        return lease is None or lease.status == LeaseStatus.FENCED.value

    def assert_can_emit_effects(self, lease_id: str) -> None:
        """The old attempt must be fenced before a replacement can emit effects."""
        lease = self._by_id.get(lease_id)
        if lease is None or lease.status != LeaseStatus.ACTIVE.value:
            raise LeaseError(f"FENCED: lease {lease_id} is not active; cannot emit effects")

    def stale_leases(self) -> list[RuntimeLease]:
        now = self._now_ms()
        return [l for l in self._by_id.values()
                if l.status == LeaseStatus.ACTIVE.value and l.expiry_ts <= now]
