from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from worker_lifecycle import (  # noqa: E402
    CANONICAL_REGISTRY_SCHEMA_VERSION,
    LIFECYCLE_ACCEPTED,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_CANONICAL_MERGED,
    LIFECYCLE_CHANGES_REQUIRED,
    LIFECYCLE_FROZEN,
    LIFECYCLE_RELEASED,
    LIFECYCLE_RESERVED,
    LIFECYCLE_REVIEW_WAIT,
    LIFECYCLE_UNKNOWN,
    occupied_capacity_count,
    registry_schema_findings,
    registry_schema_supported,
    resolve_worker_lifecycle,
)
from worker_slots import R6_COMPAT_BLOB, R6_COMPAT_PATH, validate_worker_slots  # noqa: E402


def _slot(**overrides):
    slot = {
        "worker_slot_id": "SLOT-A",
        "task_id": "TASK-A",
        "route_epoch": 565,
        "issue": 565,
        "pr": 600,
        "branch": "gpt/test",
        "exact_head": "a" * 40,
        "activation_state": "ACTIVE",
        "closure_state": None,
        "status": "ACTIVE_GOVERNED_EXECUTION",
        "execution_allowed": True,
        "resource_class": "LIGHT_TO_MEDIUM_IMPLEMENTATION",
    }
    slot.update(overrides)
    return slot


def _event(kind: str, **overrides):
    event = {
        "kind": kind,
        "worker_slot_id": "SLOT-A",
        "task_id": "TASK-A",
        "route_epoch": 565,
        "issue": 565,
        "pr": 600,
        "exact_head": "a" * 40,
        "observed_at": "2026-09-02T23:00:00Z",
    }
    event.update(overrides)
    return event


class RegistrySchemaTests(unittest.TestCase):
    def test_canonical_15_is_supported_without_error(self) -> None:
        self.assertEqual(CANONICAL_REGISTRY_SCHEMA_VERSION, "1.5")
        self.assertTrue(registry_schema_supported("1.5"))
        self.assertEqual(registry_schema_findings("1.5"), ())

    def test_legacy_10_is_explicit_compatibility_only(self) -> None:
        self.assertTrue(registry_schema_supported("1.0"))
        self.assertEqual(
            registry_schema_findings("1.0"),
            ("WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY",),
        )

    def test_unknown_future_schema_fails_closed(self) -> None:
        self.assertFalse(registry_schema_supported("999"))
        self.assertEqual(
            registry_schema_findings("999"),
            ("WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED",),
        )


class LifecycleProjectionTests(unittest.TestCase):
    def test_active_is_executable_and_occupies_capacity(self) -> None:
        result = resolve_worker_lifecycle(_slot())
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACTIVE)
        self.assertTrue(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertTrue(result.current_write_authority)

    def test_reserved_is_not_executable_but_occupies_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="RESERVED", execution_allowed=False, status="PREWRITE_RESERVED")
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_review_wait_is_not_executable_but_occupies_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
                execution_allowed=False,
                resource_class="REVIEW_WAIT_SLOT_OCCUPIED",
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.terminal)

    def test_review_wait_ignores_stale_true_execution_flag(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
                execution_allowed=True,
            )
        )
        self.assertFalse(result.executable)
        self.assertIn("STALE_EXECUTION_FLAG_IGNORED_BY_REVIEW_WAIT", result.findings)

    def test_accepted_awaiting_canonicalization_occupies_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACCEPTED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_explicit_released_state_beats_legacy_accepted_status(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="RELEASED",
                closure_state="RELEASED",
                status="INDEPENDENTLY_ACCEPTED_AWAITING_SEPARATE_CANONICALIZATION",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RELEASED)
        self.assertFalse(result.occupies_capacity)
        self.assertTrue(result.terminal)

    def test_frozen_superseded_is_historical_only(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="FROZEN",
                closure_state="SUPERSEDED_BY_CLEAN_SUCCESSOR",
                status="FROZEN_SUPERSEDED_ROUTE_BRANCH_BINDING",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_FROZEN)
        self.assertFalse(result.executable)
        self.assertFalse(result.occupies_capacity)
        self.assertTrue(result.terminal)

    def test_legacy_closed_canonical_record_is_released(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="CANONICAL_MERGED_AND_WORKER_RELEASED",
                status="CANONICAL_MERGED_WORKER_CLOSED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RELEASED)
        self.assertFalse(result.occupies_capacity)

    def test_prewrite_reserved_stale_true_execution_is_not_executable(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="PREWRITE_RESERVED",
                status="ACTIVE_GOVERNED_PREWRITE",
                execution_allowed=True,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertIn("RESERVED_EXECUTION_FLAG_IGNORED", result.findings)

    def test_unknown_state_fails_closed_and_occupies_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="ALIEN_FUTURE_STATE", status="ALIEN", execution_allowed=True)
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.current_write_authority)
        self.assertIn("UNKNOWN_LIFECYCLE_FAIL_CLOSED", result.findings)


class LifecycleEvidencePrecedenceTests(unittest.TestCase):
    def test_engineering_stop_beats_stale_route_projection_even_if_route_event_is_later(self) -> None:
        slot = _slot(execution_allowed=True)
        stop = _event("ENGINEERING_STOP", observed_at="2026-09-02T20:00:00Z")
        stale_route = _event(
            "ROUTE_OR_LEASE_PROJECTION",
            observed_at="2026-09-02T23:59:59Z",
            execution_allowed=True,
        )
        result = resolve_worker_lifecycle(slot, [stop, stale_route])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertIn("STALE_EXECUTION_FLAG_IGNORED_BY_STRONGER_EVIDENCE", result.findings)

    def test_accept_beats_engineering_stop_but_does_not_release_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False),
            [_event("ENGINEERING_STOP"), _event("INDEPENDENT_ACCEPT")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACCEPTED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_canonical_merge_still_occupies_until_closeout(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False),
            [_event("INDEPENDENT_ACCEPT"), _event("CANONICAL_MERGE")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CANONICAL_MERGED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.terminal)

    def test_closeout_releases_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False),
            [
                _event("ENGINEERING_STOP"),
                _event("INDEPENDENT_ACCEPT"),
                _event("CANONICAL_MERGE"),
                _event("CLOSEOUT_RELEASED"),
            ],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RELEASED)
        self.assertFalse(result.executable)
        self.assertFalse(result.occupies_capacity)
        self.assertTrue(result.terminal)

    def test_changes_required_freezes_old_head_and_remains_fail_closed(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=True),
            [_event("CHANGES_REQUIRED")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CHANGES_REQUIRED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertTrue(result.terminal)

    def test_old_head_accept_cannot_accept_moved_head(self) -> None:
        moved = _slot(exact_head="b" * 40, execution_allowed=False, activation_state="REVIEW_WAIT")
        old_accept = _event("INDEPENDENT_ACCEPT", exact_head="a" * 40)
        result = resolve_worker_lifecycle(moved, [old_accept])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("STALE_OR_FOREIGN_LIFECYCLE_EVIDENCE_IGNORED", result.findings)

    def test_foreign_issue_event_cannot_change_state(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False, activation_state="REVIEW_WAIT"),
            [_event("CLOSEOUT_RELEASED", issue=999)],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertTrue(result.occupies_capacity)

    def test_unknown_evidence_kind_is_inert(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False, activation_state="REVIEW_WAIT"),
            [_event("CALLER_SAYS_RELEASED")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("UNKNOWN_LIFECYCLE_EVIDENCE_KIND_IGNORED", result.findings)


class CapacityAndAuthorityTests(unittest.TestCase):
    def test_two_review_wait_slots_fill_two_slot_capacity(self) -> None:
        slots = [
            _slot(worker_slot_id="A", task_id="A", activation_state="REVIEW_WAIT", execution_allowed=False),
            _slot(worker_slot_id="B", task_id="B", activation_state="REVIEW_WAIT", execution_allowed=False),
        ]
        self.assertEqual(occupied_capacity_count(slots), 2)

    def test_review_wait_plus_active_plus_third_active_counts_three(self) -> None:
        slots = [
            _slot(worker_slot_id="A", task_id="A", activation_state="REVIEW_WAIT", execution_allowed=False),
            _slot(worker_slot_id="B", task_id="B"),
            _slot(worker_slot_id="C", task_id="C"),
        ]
        self.assertEqual(occupied_capacity_count(slots), 3)

    def test_release_decrements_capacity_exactly_once_per_slot(self) -> None:
        slots = [
            _slot(worker_slot_id="A", task_id="A", activation_state="RELEASED", closure_state="RELEASED", execution_allowed=False),
            _slot(worker_slot_id="B", task_id="B", activation_state="REVIEW_WAIT", execution_allowed=False),
        ]
        self.assertEqual(occupied_capacity_count(slots), 1)

    def test_resolution_never_mints_accept_merge_or_trade_authority(self) -> None:
        for event_kind in (
            "PREWRITE_AUTHORIZATION",
            "ENGINEERING_STOP",
            "INDEPENDENT_ACCEPT",
            "CANONICAL_MERGE",
            "CLOSEOUT_RELEASED",
        ):
            result = resolve_worker_lifecycle(_slot(), [_event(event_kind, execution_allowed=True)])
            self.assertFalse(result.acceptance_authority)
            self.assertFalse(result.merge_authority)
            self.assertFalse(result.trade_authority)

    def test_resolution_is_deterministic_and_event_order_independent(self) -> None:
        events = [
            _event("ENGINEERING_STOP"),
            _event("INDEPENDENT_ACCEPT"),
            _event("CANONICAL_MERGE"),
        ]
        left = resolve_worker_lifecycle(_slot(execution_allowed=False), events)
        right = resolve_worker_lifecycle(_slot(execution_allowed=False), list(reversed(events)))
        self.assertEqual(left, right)
        self.assertEqual(left.fingerprint, right.fingerprint)


class R6RepositoryIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]

    def test_r5_compatibility_file_is_exact_pre_r6_git_blob(self) -> None:
        data = (self.repo_root / R6_COMPAT_PATH).read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        self.assertEqual(digest, R6_COMPAT_BLOB)

    def test_canonical_registry_15_is_not_rejected_by_frozen_10_validator(self) -> None:
        report = validate_worker_slots(self.repo_root)
        error_codes = {item["code"] for item in report["errors"]}
        self.assertNotIn("WORKER_REGISTRY_IDENTITY_INVALID", error_codes)
        self.assertNotIn("WORKER_SLOT_ACTIVATION_STATE_INVALID", error_codes)
        self.assertNotIn("WORKER_SLOT_CLOSURE_STATE_INVALID", error_codes)
        self.assertNotIn("WORKER_SLOT_LIFECYCLE_UNKNOWN_FAIL_CLOSED", error_codes)

    def test_current_historical_and_live_slots_resolve_to_expected_lifecycles(self) -> None:
        report = validate_worker_slots(self.repo_root)
        by_id = {item["worker_slot_id"]: item for item in report["worker_lifecycle_resolutions"]}
        self.assertEqual(by_id["GPT-WORKER-R163-INTERACTIVE-FILM-REMEDIATION-1"]["lifecycle_state"], LIFECYCLE_FROZEN)
        self.assertEqual(by_id["GPT-WORKER-R164-W5-EVENT-COVERAGE-2"]["lifecycle_state"], LIFECYCLE_FROZEN)
        self.assertEqual(by_id["GPT-WORKER-R166-W5-EVENT-COVERAGE-2"]["lifecycle_state"], LIFECYCLE_RELEASED)
        self.assertEqual(by_id["GPT-WORKER-R168-CANONICAL-CI-STATE-ISOLATION-1"]["lifecycle_state"], LIFECYCLE_RELEASED)
        self.assertEqual(by_id["GPT-WORKER-R182-W2-MARKET-SEMANTICS-1"]["lifecycle_state"], LIFECYCLE_REVIEW_WAIT)
        self.assertEqual(by_id["GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1"]["lifecycle_state"], LIFECYCLE_RESERVED)

    def test_current_capacity_counts_review_wait_and_prewrite_reservation(self) -> None:
        report = validate_worker_slots(self.repo_root)
        self.assertEqual(
            set(report["occupied_capacity_slots"]),
            {
                "GPT-WORKER-R182-W2-MARKET-SEMANTICS-1",
                "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1",
            },
        )
        self.assertEqual(report["occupied_capacity_count"], 2)

    def test_r6_authority_is_structurally_bound_and_maintenance_only(self) -> None:
        report = validate_worker_slots(self.repo_root)
        witness = report["r6_maintenance_adoption"]
        self.assertTrue(witness["present"])
        self.assertEqual(witness["structural_check"], "PASS")
        self.assertEqual(report["r6_maintenance_authority_state"], "ACTIVE")
        self.assertTrue(report["r6_maintenance_write_allowed"])


if __name__ == "__main__":
    unittest.main()
