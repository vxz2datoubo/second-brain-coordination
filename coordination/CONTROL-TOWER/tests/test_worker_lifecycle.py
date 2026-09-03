from __future__ import annotations

import hashlib
import sys
import tempfile
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
WORKER_REGISTRY = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
PROGRAM_LANES = "coordination/ACTIVE-PROGRAM-LANES.yaml"
REPOSITORY = "vxz2datoubo/second-brain-coordination"


def _slot(**overrides):
    slot = {
        "repository": REPOSITORY,
        "worker_slot_id": "SLOT-A",
        "task_id": "TASK-A",
        "route_epoch": 565,
        "issue": 565,
        "pr": 600,
        "branch": "gpt/test",
        "exact_head": "a" * 40,
        "review_ref": "PR_REVIEW:123",
        "review_result_ref": "REVIEW_RESULT:456",
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
        "repository": REPOSITORY,
        "worker_slot_id": "SLOT-A",
        "task_id": "TASK-A",
        "route_epoch": 565,
        "issue": 565,
        "pr": 600,
        "exact_head": "a" * 40,
        "review_ref": "PR_REVIEW:123",
        "review_result_ref": "REVIEW_RESULT:456",
        "observed_at": "2026-09-03T17:00:00Z",
    }
    event.update(overrides)
    return event


def _git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def _write_yaml(root: Path, relpath: str, payload) -> None:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


class RegistrySchemaTests(unittest.TestCase):
    def test_canonical_15_is_supported(self) -> None:
        self.assertEqual(CANONICAL_REGISTRY_SCHEMA_VERSION, "1.5")
        self.assertTrue(registry_schema_supported("1.5"))
        self.assertEqual(registry_schema_findings("1.5"), ())

    def test_legacy_10_is_compatibility_only(self) -> None:
        self.assertTrue(registry_schema_supported("1.0"))
        self.assertEqual(
            registry_schema_findings("1.0"),
            ("WORKER_REGISTRY_LEGACY_SCHEMA_COMPATIBILITY",),
        )

    def test_unknown_schema_fails_closed(self) -> None:
        self.assertFalse(registry_schema_supported("999"))
        self.assertEqual(
            registry_schema_findings("999"),
            ("WORKER_REGISTRY_SCHEMA_UNSUPPORTED_FAIL_CLOSED",),
        )


class LifecycleProjectionTests(unittest.TestCase):
    def test_active_executes_and_occupies(self) -> None:
        result = resolve_worker_lifecycle(_slot())
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACTIVE)
        self.assertTrue(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertTrue(result.current_write_authority)

    def test_reserved_is_non_executable_but_occupies(self) -> None:
        result = resolve_worker_lifecycle(_slot(activation_state="RESERVED", execution_allowed=False))
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_prewrite_stale_true_is_non_executable(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="PREWRITE_RESERVED",
                status="ACTIVE_GOVERNED_PREWRITE",
                execution_allowed=True,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RESERVED)
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

    def test_accepted_status_beats_old_review_wait_projection(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACCEPTED)
        self.assertTrue(result.occupies_capacity)

    def test_canonical_governed_changes_required_projection_is_terminal(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="CHANGES_REQUIRED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CHANGES_REQUIRED)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertTrue(result.terminal)
        self.assertEqual(result.source_kind, "CANONICAL_AGGREGATE_PROJECTION")

    def test_canonical_merged_projection_still_occupies(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="CANONICAL_MERGED_AWAITING_CLOSEOUT",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CANONICAL_MERGED)
        self.assertTrue(result.occupies_capacity)

    def test_explicit_released_projection_beats_old_accepted_status(self) -> None:
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

    def test_frozen_projection_is_historical_only(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="FROZEN",
                closure_state="SUPERSEDED_BY_CLEAN_SUCCESSOR",
                status="FROZEN_SUPERSEDED_ROUTE_BRANCH_BINDING",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_FROZEN)
        self.assertFalse(result.occupies_capacity)

    def test_legacy_closed_released_record_is_released(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="CANONICAL_MERGED_AND_WORKER_RELEASED",
                status="CANONICAL_MERGED_WORKER_CLOSED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_RELEASED)

    def test_active_plus_released_closure_fails_closed_and_holds_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="ACTIVE",
                closure_state="RELEASED",
                status="ACTIVE_GOVERNED_EXECUTION",
                execution_allowed=True,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.current_write_authority)
        self.assertIn("CONTRADICTORY_TERMINAL_PROJECTION_FAILS_CLOSED", result.findings)

    def test_frozen_plus_positive_active_status_fails_closed_and_holds_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="FROZEN",
                closure_state="SUPERSEDED_BY_CLEAN_SUCCESSOR",
                status="ACTIVE_GOVERNED_EXECUTION",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertIn("TERMINAL_CONFLICTS_WITH_ACTIVE_STATUS", result.findings)

    def test_closed_released_plus_execution_true_fails_closed_and_holds_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="CANONICAL_MERGED_AND_WORKER_RELEASED",
                status="CANONICAL_MERGED_WORKER_CLOSED",
                execution_allowed=True,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)
        self.assertIn("TERMINAL_CONFLICTS_WITH_EXECUTION_ALLOWED", result.findings)

    def test_valid_released_and_frozen_records_still_release_capacity(self) -> None:
        released = resolve_worker_lifecycle(
            _slot(
                activation_state="RELEASED",
                closure_state="RELEASED",
                status="RELEASED",
                execution_allowed=False,
            )
        )
        frozen = resolve_worker_lifecycle(
            _slot(
                activation_state="FROZEN",
                closure_state="SUPERSEDED_BY_CLEAN_SUCCESSOR",
                status="FROZEN_SUPERSEDED_ROUTE_BRANCH_BINDING",
                execution_allowed=False,
            )
        )
        self.assertEqual(released.lifecycle_state, LIFECYCLE_RELEASED)
        self.assertFalse(released.occupies_capacity)
        self.assertEqual(frozen.lifecycle_state, LIFECYCLE_FROZEN)
        self.assertFalse(frozen.occupies_capacity)

    def test_terminal_conflict_resolution_is_mapping_order_independent(self) -> None:
        slot = _slot(
            activation_state="ACTIVE",
            closure_state="RELEASED",
            status="ACTIVE_GOVERNED_EXECUTION",
            execution_allowed=True,
        )
        reversed_slot = dict(reversed(list(slot.items())))
        self.assertEqual(
            resolve_worker_lifecycle(slot),
            resolve_worker_lifecycle(reversed_slot),
        )

    def test_ambiguous_closed_fails_closed(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="UNKNOWN_CLOSE",
                status="CLOSED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertTrue(result.occupies_capacity)

    def test_unknown_state_fails_closed_and_holds_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="ALIEN", status="ALIEN", execution_allowed=True)
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_negated_release_text_cannot_free_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="NOT_RELEASED",
                status="NOT_WORKER_CLOSED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertTrue(result.occupies_capacity)
        self.assertFalse(result.terminal)

    def test_negated_frozen_text_cannot_free_capacity(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="ALIEN",
                status="NOT_FROZEN",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertTrue(result.occupies_capacity)

    def test_negated_accept_text_cannot_override_review_wait(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="REVIEW_WAIT",
                status="NOT_INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertTrue(result.occupies_capacity)

    def test_almost_closed_status_cannot_release_closed_projection(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(
                activation_state="CLOSED",
                closure_state="UNKNOWN_CLOSE",
                status="ALMOST_CANONICAL_MERGED_WORKER_CLOSED",
                execution_allowed=False,
            )
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_UNKNOWN)
        self.assertTrue(result.occupies_capacity)


class AdvisoryAndGovernedEvidenceSafetyTests(unittest.TestCase):
    def test_engineering_stop_can_only_tighten_to_review_wait(self) -> None:
        stop = _event("ENGINEERING_STOP")
        stale_route = _event("ROUTE_OR_LEASE_PROJECTION", execution_allowed=True)
        result = resolve_worker_lifecycle(_slot(), [stale_route, stop])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)
        self.assertTrue(result.occupies_capacity)

    def test_complete_caller_forged_changes_required_cannot_terminalize_active(self) -> None:
        result = resolve_worker_lifecycle(_slot(), [_event("CHANGES_REQUIRED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACTIVE)
        self.assertFalse(result.terminal)
        self.assertIn(
            "EXTERNAL_AUTHORITY_EVENT_REQUIRES_GOVERNED_PROJECTION:CHANGES_REQUIRED",
            result.findings,
        )

    def test_complete_caller_forged_changes_required_cannot_terminalize_review_wait(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [_event("CHANGES_REQUIRED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.terminal)
        self.assertTrue(result.occupies_capacity)

    def test_old_head_changes_required_is_inert_after_head_move(self) -> None:
        moved = _slot(
            exact_head="b" * 40,
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(moved, [_event("CHANGES_REQUIRED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("LIFECYCLE_EVIDENCE_IDENTITY_INVALID:exact_head", result.findings)

    def test_foreign_repository_changes_required_is_inert(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(
            baseline,
            [_event("CHANGES_REQUIRED", repository="foreign/example")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("LIFECYCLE_EVIDENCE_IDENTITY_INVALID:repository", result.findings)

    def test_foreign_review_result_is_inert(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(
            baseline,
            [_event("CHANGES_REQUIRED", review_result_ref="REVIEW_RESULT:FOREIGN")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn(
            "LIFECYCLE_EVIDENCE_PROVENANCE_INVALID:review_result_ref",
            result.findings,
        )
        self.assertIn("UNVERIFIED_OR_FOREIGN_REVIEW_EVIDENCE_IGNORED", result.findings)

    def test_missing_review_provenance_is_inert(self) -> None:
        event = _event("CHANGES_REQUIRED")
        event.pop("review_ref")
        result = resolve_worker_lifecycle(_slot(), [event])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACTIVE)
        self.assertIn("LIFECYCLE_EVIDENCE_PROVENANCE_INVALID:review_ref", result.findings)

    def test_complete_caller_accept_event_cannot_mint_acceptance(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [_event("INDEPENDENT_ACCEPT")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn(
            "EXTERNAL_AUTHORITY_EVENT_REQUIRES_GOVERNED_PROJECTION:INDEPENDENT_ACCEPT",
            result.findings,
        )

    def test_complete_caller_merge_event_cannot_mint_merge(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="INDEPENDENTLY_ACCEPTED_AWAITING_CANONICALIZATION",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [_event("CANONICAL_MERGE")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_ACCEPTED)
        self.assertIn(
            "EXTERNAL_AUTHORITY_EVENT_REQUIRES_GOVERNED_PROJECTION:CANONICAL_MERGE",
            result.findings,
        )

    def test_complete_caller_closeout_event_cannot_free_capacity(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="CANONICAL_MERGED_AWAITING_CLOSEOUT",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [_event("CLOSEOUT_RELEASED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_CANONICAL_MERGED)
        self.assertTrue(result.occupies_capacity)

    def test_complete_caller_frozen_event_cannot_free_capacity(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [_event("FROZEN_SUPERSEDED")])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertTrue(result.occupies_capacity)

    def test_incomplete_closeout_identity_is_rejected(self) -> None:
        event = {"kind": "CLOSEOUT_RELEASED", "worker_slot_id": "SLOT-A"}
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=False,
        )
        result = resolve_worker_lifecycle(baseline, [event])
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("INCOMPLETE_OR_FOREIGN_LIFECYCLE_EVIDENCE_IGNORED", result.findings)

    def test_unknown_evidence_kind_is_inert(self) -> None:
        result = resolve_worker_lifecycle(
            _slot(activation_state="REVIEW_WAIT", execution_allowed=False),
            [_event("CALLER_SAYS_RELEASED")],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertIn("UNKNOWN_LIFECYCLE_EVIDENCE_KIND_IGNORED", result.findings)

    def test_stale_route_alone_cannot_resurrect_review_wait(self) -> None:
        baseline = _slot(
            activation_state="REVIEW_WAIT",
            status="ENGINEERING_STOPPED_WAITING_INDEPENDENT_REVIEW",
            execution_allowed=True,
        )
        result = resolve_worker_lifecycle(
            baseline,
            [_event("ROUTE_OR_LEASE_PROJECTION", execution_allowed=True)],
        )
        self.assertEqual(result.lifecycle_state, LIFECYCLE_REVIEW_WAIT)
        self.assertFalse(result.executable)
        self.assertIn("ADVISORY_EVENT_AUTHORITY_ESCALATION_BLOCKED", result.findings)


class CapacityAndAuthorityTests(unittest.TestCase):
    def test_two_review_wait_slots_fill_two_slots(self) -> None:
        slots = [
            _slot(worker_slot_id="A", task_id="A", activation_state="REVIEW_WAIT", execution_allowed=False),
            _slot(worker_slot_id="B", task_id="B", activation_state="REVIEW_WAIT", execution_allowed=False),
        ]
        self.assertEqual(occupied_capacity_count(slots), 2)

    def test_resolution_never_mints_authorities(self) -> None:
        for kind in (
            "PREWRITE_AUTHORIZATION",
            "ENGINEERING_STOP",
            "CHANGES_REQUIRED",
            "INDEPENDENT_ACCEPT",
            "CANONICAL_MERGE",
            "CLOSEOUT_RELEASED",
            "FROZEN_SUPERSEDED",
        ):
            with self.subTest(kind=kind):
                result = resolve_worker_lifecycle(_slot(), [_event(kind, execution_allowed=True)])
                self.assertFalse(result.acceptance_authority)
                self.assertFalse(result.merge_authority)
                self.assertFalse(result.trade_authority)
                self.assertFalse(result.successor_release_authority)

    def test_resolution_is_deterministic_and_event_order_independent(self) -> None:
        events = [
            _event("ROUTE_OR_LEASE_PROJECTION", execution_allowed=True),
            _event("ENGINEERING_STOP"),
            _event("CHANGES_REQUIRED"),
        ]
        self.assertEqual(
            resolve_worker_lifecycle(_slot(), events),
            resolve_worker_lifecycle(_slot(), list(reversed(events))),
        )


class AuditFailClosedTests(unittest.TestCase):
    def _program(self):
        return {
            "portfolio_capacity_policy": {
                "gpt_engineering_worker_active_slots_max": 2,
            }
        }

    def test_missing_registry_never_reports_free_capacity_truth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_yaml(root, PROGRAM_LANES, self._program())
            audit = audit_worker_registry_lifecycle(root)
            self.assertFalse(audit.valid_for_observability)
            self.assertIsNone(audit.occupied_capacity_count)
            self.assertIsNone(audit.free_capacity_count)
            self.assertEqual(audit.capacity_state, "UNKNOWN_FAIL_CLOSED")
            self.assertFalse(audit.successor_release_authority)

    def test_unknown_registry_schema_has_no_free_capacity_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_yaml(root, PROGRAM_LANES, self._program())
            _write_yaml(
                root,
                WORKER_REGISTRY,
                {
                    "schema_version": "9.9",
                    "registry_id": "ACTIVE-GPT-ENGINEERING-WORKERS-0001",
                    "agent_type": "GPT_ENGINEERING_WORKER",
                    "worker_slots": [_slot()],
                },
            )
            audit = audit_worker_registry_lifecycle(root)
            self.assertFalse(audit.valid_for_observability)
            self.assertIsNone(audit.free_capacity_count)
            self.assertEqual(audit.capacity_state, "UNKNOWN_FAIL_CLOSED")

    def test_duplicate_slot_id_blocks_free_capacity_claim(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_yaml(root, PROGRAM_LANES, self._program())
            slot = _slot(activation_state="REVIEW_WAIT", execution_allowed=False)
            _write_yaml(
                root,
                WORKER_REGISTRY,
                {
                    "schema_version": "1.5",
                    "registry_id": "ACTIVE-GPT-ENGINEERING-WORKERS-0001",
                    "agent_type": "GPT_ENGINEERING_WORKER",
                    "worker_slots": [slot, dict(slot)],
                },
            )
            audit = audit_worker_registry_lifecycle(root)
            self.assertFalse(audit.valid_for_observability)
            self.assertIsNone(audit.free_capacity_count)
            self.assertIn("WORKER_SLOT_ID_DUPLICATE:SLOT-A", audit.findings)


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
        self.assertEqual(audit.free_capacity_count, 0)
        self.assertEqual(audit.capacity_state, "KNOWN_OBSERVATION")
        self.assertFalse(audit.successor_release_authority)
        self.assertEqual(
            set(audit.occupied_capacity_slots),
            {
                "GPT-WORKER-R182-W2-MARKET-SEMANTICS-1",
                "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1",
            },
        )

    def test_current_slots_resolve_to_expected_lifecycles(self) -> None:
        audit = audit_worker_registry_lifecycle(self.repo_root)
        by_id = {item["worker_slot_id"]: item for item in audit.slot_resolutions}
        expected = {
            "GPT-WORKER-R163-INTERACTIVE-FILM-REMEDIATION-1": LIFECYCLE_FROZEN,
            "GPT-WORKER-R164-W5-EVENT-COVERAGE-2": LIFECYCLE_FROZEN,
            "GPT-WORKER-R166-W5-EVENT-COVERAGE-2": LIFECYCLE_RELEASED,
            "GPT-WORKER-R168-CANONICAL-CI-STATE-ISOLATION-1": LIFECYCLE_RELEASED,
            "GPT-WORKER-R182-W2-MARKET-SEMANTICS-1": LIFECYCLE_REVIEW_WAIT,
            "GPT-WORKER-R183-DS10-RESEARCH-INTEGRITY-1": LIFECYCLE_RESERVED,
        }
        for slot_id, lifecycle in expected.items():
            with self.subTest(slot_id=slot_id):
                self.assertEqual(by_id[slot_id]["lifecycle_state"], lifecycle)

    def test_r6_authority_is_narrow_non_runtime_non_merge(self) -> None:
        authority = yaml.safe_load((self.repo_root / R6_AUTHORITY).read_text(encoding="utf-8"))
        self.assertEqual(
            authority["authority_id"],
            "R144-GPT-ARCHITECTURE-OWNER-MAINTENANCE-ADOPTION-R6-0001",
        )
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
            {
                "coordination/CONTROL-TOWER/worker_slots.py",
                "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml",
                "coordination/ACTIVE-PROGRAM-LANES.yaml",
            },
        )


if __name__ == "__main__":
    unittest.main()