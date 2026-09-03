from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import yaml

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
    audit_worker_registry_lifecycle,
    occupied_capacity_count,
    registry_schema_findings,
    registry_schema_supported,
    resolve_worker_lifecycle,
)

PRE_R6_WORKER_SLOTS_BLOB = "00a863a79a35524cb6db950529dabc9ff32761fa"
R6_AUTHORITY = "coordination/CONTROL-TOWER/R144-GPT-MAINTENANCE-ADOPTION-R6.yaml"
WORKER_SLOTS = "coordination/CONTROL-TOWER/worker_slots.py"


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


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


class RegistrySchemaTests(unittest.TestCase):
    def test_canonical_15_is_supported(self) -> None:
        self.assertEqual(CANONICAL_REGISTRY_SCHEMA_VERSION, "1.5")
        self.assertTrue(registry_schema_supported("1.5"))
        self.assertEqual(registry_schema_findings("1.5"), ())

    def test_legacy_10_is_compatibility_only(self) -> None:
        self.assertTrue(registry_schema_supported("1.0"))
        self.assertEqual(registry_schema_findings("1.0"), ("WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY",))

    def test_unknown_schema_fails_closed(self) -> None:
        self.assertFalse(registry_schema_supported("999"))
        self.assertEqual(registry_schema_findings("999"), ("WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED",))


class LifecycleProjectionTests(unittest.TestCase):
    def test_active_executes_and_occupies(self) -> None:
        result = resolve_worker_lifecycle(_slot())
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACTIVE)
        self.assertTrue(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_reserved_is_non_executable_but_occupies(self) -> None:
        result = resolve_worker_lifecycle(_slot(activation_state="RESERVED", execution_allowed=False))
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_prewrite_stale_true_is_still_non_executable(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="PREWRITE_RESERVED", status="ACTIVE_GOVERNED_PREWRITE", execution_allowed=True)
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertIn("RESERVED_EXECUTION_FLAG_IGNORED", result.findings)

    def test_review_wait_occupies_but_never_executes(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
                execution_allowed=True,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_accepted_occupies_until_later_closeout(self) -> None:
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

    def test_explicit_released_beats_old_accepted_presentation(self) -> None:
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

    def test_frozen_is_historical_only(self) -> None:
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

    def test_unknown_state_fails_closed_and_holds_capacity(self) -> None:
        result = resolve_worker_lifecycle(_slot(activation_state="ALIEN", status="ALIEN", execution_allowed=True))
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.current_write_authority)


class EvidencePrecedenceTests(unittest.TestCase):
    def test_engineering_stop_beats_later_stale_route_projection(self) -> None:
        stop = _event("ENGINEERING_STOP", observed_at="2026-09-02T20:00:00Z")
        stale_route = _event("ROUTE_OR_LEASE_PROJECTION", observed_at="2026-09-03T00:00:00Z", execution_allowed=True)
        result = resolve_worker_lifecycle(_slot(), [stop, stale_route])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)

    def test_accept_does_not_release_capacity(self) -> None:
        result = resolve_worker_lifecycle(_slot(execution_allowed=False), [_event("ENGINEERING_STOP"), _event("INDEPENDENT_ACCEPT")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACCEPTED)
        self.assertTrue(result.occupies_capacity)

    def test_merge_does_not_release_capacity(self) -> None:
        result = resolve_worker_lifecycle(_slot(execution_allowed=False), [_event("INDEPENDENT_ACCEPT"), _event("CANONICAL_MERGE")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CANONICAL_MERGED)
        self.assertTrue(result.occupies_capacity)

    def test_closeout_releases(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(execution_allowed=False),
            [_event("ENGINEERING_STOP"), _event("INDEPENDENT_ACCEPT"), _event("CANONICAL_MERGE"), _event("CLOSEOUT_RELEASED")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RELEASED)
        self.assertFalse(result.occupies_capacity)

    def test_changes_required_freezes_reviewed_head(self) -> None:
        result = resolve_worker_lifecycle(_slot(), [_event("CHANGES_REQUIRED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CHANGES_REQUIRED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertTrue(result.terminal)

    def test_accept_for_old_head_is_inert_after_head_move(self) -> None:
        moved = _slot(exact_head="b" * 40, activation_state="REVIEW_WAIT", execution_allowed=False)
        result = resolve_worker_lifecycle(moved, [_event("INDEPENDENT_ACCEPT", exact_head="a" * 40)])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("STALE_OR_FOREIGN_LIFECYCLE_EVIDENCE_IGNORED", result.findings)

    def test_foreign_issue_event_is_inert(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="REVIEW_WAIT", execution_allowed=False),
            [_event("CLOSEOUT_RELEASED", issue=999)],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)

    def test_unknown_evidence_kind_is_inert(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="REVIEW_WAIT", execution_allowed=False),
            [_event("CALLER_SAYS_RELEASED")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("UNKNOWN_LIFECYCLE_EVIDENCE_KIND_IGNORED", result.findings)


class CapacityAndAuthorityTests(unittest.TestCase):
    def test_two_review_wait_slots_fill_two_slots(self) -> None:
        slots = [
            _slot(worker_slot_id="A", task_id="A", activation_state="REVIEW_WAIT", execution_allowed=False),
            _slot(worker_slot_id="B", task_id="B", activation_state="REVIEW_WAIT", execution_allowed=False),
        ]
        self.assertEqual(occupied_capacity_count(slots), 2)

    def test_resolution_never_mints_accept_merge_or_trade_authority(self) -> None:
        for kind in ("PREWRITE_AUTHORIZATION", "ENGINEERING_STOP", "INDEPENDENT_ACCEPT", "CANONICAL_MERGE", "CLOSEOUT_RELEASED"):
            result = resolve_worker_lifecycle(_slot(), [_event(kind, execution_allowed=True)])
            self.assertFalse(result.acceptance_authority)
            self.assertFalse(result.merge_authority)
            self.assertFalse(result.trade_authority)

    def test_resolution_is_deterministic_and_event_order_independent(self) -> None:
        events = [_event("ENGINEERING_STOP"), _event("INDEPENDENT_ACCEPT"), _event("CANONICAL_MERGE")]
        left = resolve_worker_lifecycle(_slot(execution_allowed=False), events)
        right = resolve_worker_lifecycle(_slot(execution_allowed=False), list(reversed(events)))
        self.assertEqual(left, right)


class RepositoryAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]

    def test_first_slice_does_not_modify_legacy_worker_slots_validator(self) -> None:
        data = (self.repo_root / WORKER_SLOTS).read_bytes()
        self.assertEqual(_git_blob_sha(data), PRE_R6_WORKER_SLOTS_BLOB)

    def test_current_registry_audit_is_valid_and_capacity_full(self) -> None:
        audit = audit_worker_registry_lifecycle(self.repo_root)
        self.assertTrue(audit.valid_for_observability)
        self.assertEqual(audit.schema_version, "1.5")
        self.assertEqual(audit.configured_capacity_limit, 2)
        self.assertEqual(audit.occupied_capacity_count, 2)
        self.assertEqual(
            set(audit.occupied_capacity_slots),
            {"GPT-WORKER-R182-W2-MARKET-SEMANTICS-1", "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1"},
        )

    def test_current_slots_resolve_to_expected_lifecycles(self) -> None:
        audit = audit_worker_registry_lifecycle(self.repo_root)
        by_id = {item["worker_slot_id"]: item for item in audit.slot_resolutions}
        self.assertEqual(by_id["GPT-WORKER-R163-INTERACTIVE-FILM-REMEDIATION-1"]["lifecycle_state"], LIFECYCLE_FROZEN)
        self.assertEqual(by_id["GPT-WORKER-R164-W5-EVENT-COVERAGE-2"]["lifecycle_state"], LIFECYCLE_FROZEN)
        self.assertEqual(by_id["GPT-WORKER-R166-W5-EVENT-COVERAGE-2"]["lifecycle_state"], LIFECYCLE_RELEASED)
        self.assertEqual(by_id["GPT-WORKER-R168-CANONICAL-CI-STATE-ISOLATION-1"]["lifecycle_state"], LIFECYCLE_RELEASED)
        self.assertEqual(by_id["GPT-WORKER-R182-W2-MARKET-SEMANTICS-1"]["lifecycle_state"], LIFECYCLE_REVIEW_WAIT)
        self.assertEqual(by_id["GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1"]["lifecycle_state"], LIFECYCLE_RESERVED)

    def test_r6_authority_is_narrow_non_runtime_non_merge(self) -> None:
        authority = yaml.safe_load((self.repo_root / R6_AUTHORITY).read_text(encoding="utf-8"))
        self.assertEqual(authority["authority_id"], "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R6-0001")
        self.assertEqual(authority["state"], "ACTIVE")
        for field in (
            "execution_allowed",
            "runtime_write_allowed",
            "trade_allowed",
            "merge_authority",
            "acceptance_authority",
            "self_review_allowed",
        ):
            self.assertIs(authority[field], False)
        self.assertEqual(
            set(authority["explicitly_forbidden_write_paths"]),
            {"coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml", "coordination/ACTIVE-PROGRAM-LANES.yaml"},
        )


if __name__ == "__main__":
    unittest.main()
