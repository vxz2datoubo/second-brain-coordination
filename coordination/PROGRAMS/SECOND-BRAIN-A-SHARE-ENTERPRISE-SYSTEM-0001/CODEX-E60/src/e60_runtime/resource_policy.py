"""Fail-closed local resource profiles for E60 synthetic-only canaries.

The controller intentionally starts in ``FOREGROUND_PRIORITY``.  It promotes
to ``IDLE_BATCH`` only from explicit, repeated low-load observations.  It does
not infer that a game, video editor, or another agent is absent from a process
name; an unknown foreground state is insufficient to promote.

This is an admission controller, not a throughput optimizer.  Heavy matrices
and fan-out validation must use remote CI and are rejected for local launch.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping


class ResourceProfile(str, Enum):
    FOREGROUND_PRIORITY = "FOREGROUND_PRIORITY"
    IDLE_BATCH = "IDLE_BATCH"


class WorkloadClass(str, Enum):
    LIFECYCLE_CANARY = "LIFECYCLE_CANARY"
    HEAVY_MATRIX = "HEAVY_MATRIX"
    HIGH_CONCURRENCY_VALIDATION = "HIGH_CONCURRENCY_VALIDATION"


class ResourcePolicyViolation(RuntimeError):
    """A local launch has no safe resource admission path."""


@dataclass(frozen=True, slots=True)
class ResourceSample:
    monotonic_seconds: float
    cpu_percent: float | None
    available_ram_gib: float | None
    foreground_contention: bool | None
    user_reported_stutter: bool
    unexpected_process_growth: bool

    @classmethod
    def from_mapping(cls, values: Mapping[str, object], *, monotonic_seconds: float) -> "ResourceSample":
        def optional_float(name: str) -> float | None:
            value = values.get(name)
            return None if value is None else float(value)

        def optional_bool(name: str) -> bool | None:
            value = values.get(name)
            return None if value is None else bool(value)

        return cls(
            monotonic_seconds=monotonic_seconds,
            cpu_percent=optional_float("cpu_percent"),
            available_ram_gib=optional_float("available_ram_gib"),
            foreground_contention=optional_bool("foreground_contention"),
            user_reported_stutter=bool(values.get("user_reported_stutter", False)),
            unexpected_process_growth=bool(values.get("unexpected_process_growth", False)),
        )


@dataclass(frozen=True, slots=True)
class ResourceDecision:
    profile: ResourceProfile
    allow_local_spawn: bool
    reason: str
    max_task_owned_python_processes: int
    max_cpu_workers: int
    remote_ci_required: bool


_IDLE_PROMOTION_SAMPLES = 3
_IDLE_PROMOTION_CPU_PERCENT = 20.0
_IDLE_PROMOTION_RAM_GIB = 12.0
_FOREGROUND_BACKOFF_CPU_PERCENT = 35.0
_LOCAL_HARD_FAIL_CPU_PERCENT = 40.0
_CPU_BACKOFF_SUSTAIN_SECONDS = 3.0
_CPU_HARD_FAIL_SUSTAIN_SECONDS = 5.0
_NO_NEW_CHILD_RAM_GIB = 10.0
_HARD_FAIL_RAM_GIB = 8.0


class AdaptiveResourceController:
    """Profile selection with evidence-preserving, monotonic safety decisions."""

    def __init__(self, sample_provider: Callable[[], Mapping[str, object]], monotonic_clock: Callable[[], float]) -> None:
        self._sample_provider = sample_provider
        self._monotonic_clock = monotonic_clock
        self._profile = ResourceProfile.FOREGROUND_PRIORITY
        self._idle_clean_samples = 0
        self._cpu_backoff_since: float | None = None
        self._cpu_hard_fail_since: float | None = None
        self._events: list[str] = ["PROFILE_INITIAL:FOREGROUND_PRIORITY"]

    @property
    def profile(self) -> ResourceProfile:
        return self._profile

    @property
    def events(self) -> tuple[str, ...]:
        return tuple(self._events)

    def observe(self) -> ResourceSample:
        return ResourceSample.from_mapping(self._sample_provider(), monotonic_seconds=self._monotonic_clock())

    def _demote(self, reason: str) -> None:
        if self._profile is not ResourceProfile.FOREGROUND_PRIORITY:
            self._events.append(f"PROFILE_DEMOTED:{reason}")
        self._profile = ResourceProfile.FOREGROUND_PRIORITY
        self._idle_clean_samples = 0

    def _safety_reason(self, sample: ResourceSample) -> str | None:
        if sample.user_reported_stutter:
            return "USER_REPORTED_STUTTER"
        if sample.unexpected_process_growth:
            return "UNEXPECTED_PROCESS_GROWTH"
        if sample.available_ram_gib is not None and sample.available_ram_gib < _HARD_FAIL_RAM_GIB:
            return "AVAILABLE_RAM_BELOW_8_GIB"
        if sample.available_ram_gib is not None and sample.available_ram_gib < _NO_NEW_CHILD_RAM_GIB:
            return "NO_NEW_CHILD_BELOW_10_GIB"
        cpu = sample.cpu_percent
        if cpu is None:
            self._cpu_backoff_since = None
            self._cpu_hard_fail_since = None
            return None
        if cpu >= _LOCAL_HARD_FAIL_CPU_PERCENT:
            if self._cpu_hard_fail_since is None:
                self._cpu_hard_fail_since = sample.monotonic_seconds
            if sample.monotonic_seconds - self._cpu_hard_fail_since >= _CPU_HARD_FAIL_SUSTAIN_SECONDS:
                return "CPU_HARD_FAIL_OVER_40_PERCENT"
        else:
            self._cpu_hard_fail_since = None
        if cpu >= _FOREGROUND_BACKOFF_CPU_PERCENT:
            if self._cpu_backoff_since is None:
                self._cpu_backoff_since = sample.monotonic_seconds
            if sample.monotonic_seconds - self._cpu_backoff_since >= _CPU_BACKOFF_SUSTAIN_SECONDS:
                return "CPU_BACKOFF_OVER_35_PERCENT"
        else:
            self._cpu_backoff_since = None
        return None

    def _maybe_promote(self, sample: ResourceSample) -> None:
        clean_idle_sample = (
            sample.foreground_contention is False
            and not sample.user_reported_stutter
            and not sample.unexpected_process_growth
            and sample.cpu_percent is not None
            and sample.cpu_percent <= _IDLE_PROMOTION_CPU_PERCENT
            and sample.available_ram_gib is not None
            and sample.available_ram_gib >= _IDLE_PROMOTION_RAM_GIB
        )
        if clean_idle_sample:
            self._idle_clean_samples += 1
            if self._profile is ResourceProfile.FOREGROUND_PRIORITY and self._idle_clean_samples >= _IDLE_PROMOTION_SAMPLES:
                self._profile = ResourceProfile.IDLE_BATCH
                self._events.append("PROFILE_PROMOTED:THREE_EXPLICIT_CLEAN_IDLE_SAMPLES")
            return
        self._idle_clean_samples = 0

    def decide(self, workload: WorkloadClass = WorkloadClass.LIFECYCLE_CANARY) -> ResourceDecision:
        sample = self.observe()
        reason = self._safety_reason(sample)
        if reason is not None:
            self._demote(reason)
            return ResourceDecision(
                profile=self._profile,
                allow_local_spawn=False,
                reason=reason,
                max_task_owned_python_processes=2,
                max_cpu_workers=1,
                remote_ci_required=workload is not WorkloadClass.LIFECYCLE_CANARY,
            )
        # A foreground application means that batch mode is inappropriate, not
        # that a bounded one-root/one-grandchild lifecycle canary is unsafe.
        # Actual stutter, process growth, memory pressure, and sustained CPU
        # pressure remain hard admission failures above.
        if sample.foreground_contention is True:
            self._demote("FOREGROUND_CONTENTION")
        self._maybe_promote(sample)
        if workload is not WorkloadClass.LIFECYCLE_CANARY:
            return ResourceDecision(
                profile=self._profile,
                allow_local_spawn=False,
                reason="REMOTE_CI_REQUIRED_FOR_HEAVY_OR_FANOUT_WORKLOAD",
                max_task_owned_python_processes=2 if self._profile is ResourceProfile.FOREGROUND_PRIORITY else 3,
                max_cpu_workers=1 if self._profile is ResourceProfile.FOREGROUND_PRIORITY else 2,
                remote_ci_required=True,
            )
        # E60 local lifecycle canaries remain deliberately smaller than the
        # generic IDLE_BATCH allowance: one root plus one observed grandchild.
        return ResourceDecision(
            profile=self._profile,
            allow_local_spawn=True,
            reason="LOCAL_LIFECYCLE_CANARY_ADMITTED",
            max_task_owned_python_processes=2,
            max_cpu_workers=1,
            remote_ci_required=False,
        )

    def require_local_spawn(self, workload: WorkloadClass = WorkloadClass.LIFECYCLE_CANARY) -> ResourceDecision:
        decision = self.decide(workload)
        if not decision.allow_local_spawn:
            raise ResourcePolicyViolation(decision.reason)
        return decision
