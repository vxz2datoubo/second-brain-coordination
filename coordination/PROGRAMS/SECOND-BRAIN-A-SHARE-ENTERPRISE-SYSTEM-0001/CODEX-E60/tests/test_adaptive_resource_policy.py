from __future__ import annotations

import unittest
import time

from e60_runtime.execution import WholeTaskResourceLease
from e60_runtime.resource_policy import (
    AdaptiveResourceController,
    ResourcePolicyViolation,
    ResourceProfile,
    WorkloadClass,
)
from e60_runtime.resource_tree import ProcessLifecycleError, ResourceGate, descendant_root_program


class _Samples:
    def __init__(self, *samples: dict[str, object]) -> None:
        self._samples = list(samples)
        self._index = 0
        self.clock = 0.0

    def __call__(self) -> dict[str, object]:
        sample = self._samples[min(self._index, len(self._samples) - 1)]
        self._index += 1
        return sample

    def monotonic(self) -> float:
        value = self.clock
        self.clock += 1.0
        return value


def _sample(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "cpu_percent": 10.0,
        "available_ram_gib": 16.0,
        "foreground_contention": False,
        "user_reported_stutter": False,
        "unexpected_process_growth": False,
    }
    value.update(overrides)
    return value


class AdaptiveResourcePolicyTests(unittest.TestCase):
    def test_default_is_foreground_priority_even_when_idle(self) -> None:
        samples = _Samples(_sample())
        controller = AdaptiveResourceController(samples, samples.monotonic)
        decision = controller.decide()
        self.assertEqual(decision.profile, ResourceProfile.FOREGROUND_PRIORITY)
        self.assertEqual(decision.max_task_owned_python_processes, 2)
        self.assertEqual(decision.max_cpu_workers, 1)

    def test_idle_batch_requires_three_explicit_clean_samples(self) -> None:
        samples = _Samples(_sample(), _sample(), _sample())
        controller = AdaptiveResourceController(samples, samples.monotonic)
        self.assertEqual(controller.decide().profile, ResourceProfile.FOREGROUND_PRIORITY)
        self.assertEqual(controller.decide().profile, ResourceProfile.FOREGROUND_PRIORITY)
        self.assertEqual(controller.decide().profile, ResourceProfile.IDLE_BATCH)

    def test_unknown_foreground_state_cannot_promote(self) -> None:
        samples = _Samples(*[_sample(foreground_contention=None) for _ in range(4)])
        controller = AdaptiveResourceController(samples, samples.monotonic)
        for _ in range(4):
            self.assertEqual(controller.decide().profile, ResourceProfile.FOREGROUND_PRIORITY)

    def test_foreground_contention_demotes_but_keeps_tiny_canary_available(self) -> None:
        samples = _Samples(_sample(), _sample(), _sample(), _sample(foreground_contention=True))
        controller = AdaptiveResourceController(samples, samples.monotonic)
        controller.decide(); controller.decide(); controller.decide()
        decision = controller.decide()
        self.assertEqual(decision.profile, ResourceProfile.FOREGROUND_PRIORITY)
        self.assertTrue(decision.allow_local_spawn)

    def test_stutter_demotes_and_denies_new_child_immediately(self) -> None:
        samples = _Samples(_sample(), _sample(), _sample(), _sample(user_reported_stutter=True))
        controller = AdaptiveResourceController(samples, samples.monotonic)
        controller.decide(); controller.decide(); controller.decide()
        denied = controller.decide()
        self.assertEqual(denied.profile, ResourceProfile.FOREGROUND_PRIORITY)
        self.assertFalse(denied.allow_local_spawn)
        self.assertEqual(denied.reason, "USER_REPORTED_STUTTER")

    def test_growth_and_low_memory_fail_closed(self) -> None:
        growth = _Samples(_sample(unexpected_process_growth=True))
        with self.assertRaisesRegex(ResourcePolicyViolation, "UNEXPECTED_PROCESS_GROWTH"):
            AdaptiveResourceController(growth, growth.monotonic).require_local_spawn()
        memory = _Samples(_sample(available_ram_gib=9.99))
        with self.assertRaisesRegex(ResourcePolicyViolation, "NO_NEW_CHILD_BELOW_10_GIB"):
            AdaptiveResourceController(memory, memory.monotonic).require_local_spawn()

    def test_sustained_cpu_backoff_denies_after_three_seconds(self) -> None:
        samples = _Samples(*[_sample(cpu_percent=36.0) for _ in range(5)])
        controller = AdaptiveResourceController(samples, samples.monotonic)
        controller.decide(); controller.decide(); controller.decide()
        denied = controller.decide()
        self.assertFalse(denied.allow_local_spawn)
        self.assertEqual(denied.reason, "CPU_BACKOFF_OVER_35_PERCENT")

    def test_sustained_cpu_over_40_escalates_to_hard_failure(self) -> None:
        samples = _Samples(*[_sample(cpu_percent=41.0) for _ in range(7)])
        controller = AdaptiveResourceController(samples, samples.monotonic)
        for _ in range(5):
            controller.decide()
        hard_fail = controller.decide()
        self.assertFalse(hard_fail.allow_local_spawn)
        self.assertEqual(hard_fail.reason, "CPU_HARD_FAIL_OVER_40_PERCENT")

    def test_heavy_and_fanout_workloads_are_remote_ci_only(self) -> None:
        samples = _Samples(_sample())
        controller = AdaptiveResourceController(samples, samples.monotonic)
        for workload in (WorkloadClass.HEAVY_MATRIX, WorkloadClass.HIGH_CONCURRENCY_VALIDATION):
            decision = controller.decide(workload)
            self.assertFalse(decision.allow_local_spawn)
            self.assertTrue(decision.remote_ci_required)
            self.assertEqual(decision.reason, "REMOTE_CI_REQUIRED_FOR_HEAVY_OR_FANOUT_WORKLOAD")

    def test_lease_refuses_more_than_one_expected_descendant(self) -> None:
        samples = _Samples(_sample())
        with WholeTaskResourceLease(task_id="E60-descendant-cap", sample_provider=samples, monotonic_clock=samples.monotonic) as lease:
            with self.assertRaisesRegex(ProcessLifecycleError, "LOCAL_CANARY_DESCENDANT_CAP_EXCEEDED"):
                lease.execute(
                    descendant_root_program(grandchildren=1, root_exit_first=True),
                    purpose="over-cap",
                    expected_descendants=2,
                )

    def test_observed_process_recording_remains_available_for_cleanup_under_pressure(self) -> None:
        gate = ResourceGate("E60-observation-only", cpu_throttle_percent=0.0, cpu_throttle_sustain_seconds=0.0)
        with gate:
            gate._last_snapshot = {"available_ram_gib": 16.0, "cpu_percent": 100.0}
            gate._sampled_at = time.monotonic()
            with self.assertRaisesRegex(RuntimeError, "CPU_THROTTLE_REQUIRED"):
                gate.admit(1)
            gate.record_observed(1)


if __name__ == "__main__":
    unittest.main()
