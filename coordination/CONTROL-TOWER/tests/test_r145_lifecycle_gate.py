from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

CONTROL_TOWER = Path(__file__).resolve().parents[1]
if str(CONTROL_TOWER) not in sys.path:
    sys.path.insert(0, str(CONTROL_TOWER))

from r145_lifecycle_gate import (
    ACCEPTED_RUNTIME_HEAD,
    ACCEPTED_RUNTIME_MERGE,
    ACTIVE_MODE,
    CLOSED_MODE,
    CLOSEOUT_REQUIRED_DIFF,
    INVALID_MODE,
    evaluate_closeout_diff_entries,
    evaluate_documents,
)


TASK_ID = "GPT-GLOBAL-SIGNAL-TOWER-S0F-CROSS-DOMAIN-ROUTING-ISOLATION-R145"
SLOT_ID = "GPT-WORKER-R145-PROGRAMMING-1"
LANE_ID = "LANE-A-HARNESS-INTEGRATION"


def closed_docs():
    worker = {"worker_slots": []}
    claims = {
        "claims": [
            {
                "lane_id": LANE_ID,
                "claim_state": "CLOSED_NO_ACTIVE_IMPLEMENTATION",
                "execution_agent": None,
                "worker_slot_id": None,
                "resource_class": "NO_ACTIVE_IMPLEMENTATION",
                "route_binding": None,
                "write_paths": [],
                "read_paths": [],
                "interfaces": [],
                "read_domains": [],
                "write_domains": [],
                "authority_claims": [],
            }
        ]
    }
    route = {
        "status": "CLOSED_HISTORY_ONLY",
        "execution_allowed": False,
        "runtime_code_change_allowed": False,
        "automatic_resume": False,
        "merge_authorized": False,
        "binding": {
            "task_id": TASK_ID,
            "route_epoch": 145,
            "implementation_pr": 418,
        },
        "executor": {"worker_slot_id": SLOT_ID},
        "write_scope": {"implementation": [], "exact_action_constraints": [], "cross_repo": []},
    }
    release = {
        "lane_specific_release_state": {
            LANE_ID: {
                "state": "R145_S0F_ACCEPTED_MERGED / NO_ACTIVE_IMPLEMENTATION",
                "worker_slot_id": None,
                "runtime_write_allowed": False,
                "implementation_route_allowed": False,
            }
        }
    }
    lanes = {
        "program_lanes": [
            {
                "lane_id": LANE_ID,
                "observed_state": "R145_S0F_ACCEPTED_MERGED / NO_ACTIVE_IMPLEMENTATION",
                "active_execution_route": None,
                "implementation_owner": None,
            }
        ]
    }
    receipt = {
        "status": "READY_FOR_INDEPENDENT_EXACT_HEAD_REVIEW",
        "accepted_runtime": {
            "task_id": TASK_ID,
            "runtime_pr": 418,
            "accepted_exact_head": ACCEPTED_RUNTIME_HEAD,
            "runtime_merge_commit": ACCEPTED_RUNTIME_MERGE,
            "review_disposition": "ACCEPT",
            "blocker_count": 0,
        },
        "closeout_effects": {
            "gpt_engineering_worker": {"expected_active_slots": 0},
            "lane_a_work_claim": {"expected_state": "CLOSED_NO_ACTIVE_IMPLEMENTATION"},
            "r145_route": {"expected_state": "CLOSED_HISTORY_ONLY"},
        },
    }
    return worker, claims, route, release, lanes, receipt


def active_docs():
    worker, claims, route, release, lanes, receipt = closed_docs()
    worker["worker_slots"] = [
        {
            "worker_slot_id": SLOT_ID,
            "task_id": TASK_ID,
            "route_epoch": 145,
            "issue": 415,
            "pr": 418,
            "status": "ACTIVE_IMPLEMENTATION",
            "execution_allowed": True,
        }
    ]
    claim = claims["claims"][0]
    claim.update(
        {
            "claim_state": "ACTIVE_IMPLEMENTATION",
            "execution_agent": "GPT_ENGINEERING_WORKER",
            "worker_slot_id": SLOT_ID,
        }
    )
    route.update(
        {
            "status": "ACTIVE_IMPLEMENTATION",
            "execution_allowed": True,
            "runtime_code_change_allowed": True,
        }
    )
    return worker, claims, route, release, lanes, receipt


def exact_closeout_entries():
    return [(status, (path,)) for path, status in sorted(CLOSEOUT_REQUIRED_DIFF.items())]


class R145LifecycleGateTests(unittest.TestCase):
    def assert_invalid(self, docs, code):
        result = evaluate_documents(*docs)
        self.assertEqual(INVALID_MODE, result["mode"])
        self.assertEqual("FAIL", result["status"])
        self.assertIn(code, {item["code"] for item in result["findings"]})

    def test_complete_closed_triplet_passes_closeout_mode(self):
        result = evaluate_documents(*closed_docs())
        self.assertEqual("PASS", result["status"])
        self.assertEqual(CLOSED_MODE, result["mode"])

    def test_exact_active_triplet_preserves_original_active_path_mode(self):
        result = evaluate_documents(*active_docs())
        self.assertEqual("PASS", result["status"])
        self.assertEqual(ACTIVE_MODE, result["mode"])

    def test_slot_removed_while_claim_stays_active_fails_closed(self):
        docs = list(active_docs())
        docs[0]["worker_slots"] = []
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_CLAIM_NOT_CLOSED")

    def test_claim_closed_while_route_stays_executable_fails_closed(self):
        docs = list(closed_docs())
        docs[2]["status"] = "ACTIVE_IMPLEMENTATION"
        docs[2]["execution_allowed"] = True
        docs[2]["runtime_code_change_allowed"] = True
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_ROUTE_NOT_CLOSED")

    def test_closed_route_cannot_retain_runtime_write_surface(self):
        docs = list(closed_docs())
        docs[2]["write_scope"]["implementation"] = ["coordination/PROGRAMS/example/**"]
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_ROUTE_WRITE_PATHS_RETAINED")

    def test_release_gate_cannot_retain_runtime_write_authority(self):
        docs = list(closed_docs())
        docs[3]["lane_specific_release_state"][LANE_ID]["runtime_write_allowed"] = True
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_RELEASE_GATE_RUNTIME_WRITE_RETAINED")

    def test_program_lane_cannot_retain_active_execution_route(self):
        docs = list(closed_docs())
        docs[4]["program_lanes"][0]["active_execution_route"] = "gpt/r145-cross-domain-routing-isolation-runtime"
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_PROGRAM_LANE_ROUTE_RETAINED")

    def test_closeout_receipt_must_bind_accepted_runtime(self):
        docs = list(closed_docs())
        docs[5]["accepted_runtime"]["review_disposition"] = "CHANGES_REQUIRED"
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_RECEIPT_REVIEW_NOT_ACCEPT")

    def test_closeout_receipt_must_bind_exact_accepted_head(self):
        docs = list(closed_docs())
        docs[5]["accepted_runtime"]["accepted_exact_head"] = "0" * 40
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_RECEIPT_HEAD_MISMATCH")

    def test_partial_closeout_with_stale_slot_fails_closed(self):
        docs = list(closed_docs())
        stale = copy.deepcopy(active_docs()[0]["worker_slots"][0])
        stale["execution_allowed"] = False
        stale["status"] = "CLOSED"
        docs[0]["worker_slots"] = [stale]
        self.assert_invalid(tuple(docs), "R145_CLOSEOUT_SLOT_STILL_PRESENT")

    def test_exact_closeout_diff_surface_passes(self):
        result = evaluate_closeout_diff_entries(exact_closeout_entries())
        self.assertEqual("PASS", result["status"])
        self.assertEqual(CLOSEOUT_REQUIRED_DIFF, result["actual"])

    def test_closed_mode_rejects_s0e_runtime_mutation(self):
        entries = exact_closeout_entries() + [
            (
                "M",
                (
                    "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
                    "GLOBAL-SIGNAL-PLANE/S0E-EXPLICIT-INTAKE-ADAPTIVE-GATEWAY/src/global_signal_gateway/domain_authority.py",
                ),
            )
        ]
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_DIFF_OUTSIDE_AUTHORIZED_SURFACE", {item["code"] for item in result["findings"]})

    def test_closed_mode_rejects_runtime_governance_root_mutation(self):
        entries = exact_closeout_entries() + [("M", (".github/workflows/runtime-governance-root.yml",))]
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_DIFF_OUTSIDE_AUTHORIZED_SURFACE", {item["code"] for item in result["findings"]})

    def test_closed_mode_rejects_path_action_policy_mutation(self):
        entries = exact_closeout_entries() + [("M", ("coordination/CONTROL-TOWER/path_action_policy.py",))]
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_DIFF_OUTSIDE_AUTHORIZED_SURFACE", {item["code"] for item in result["findings"]})

    def test_closed_mode_rejects_rename_even_inside_allowlist(self):
        entries = exact_closeout_entries()
        entries[0] = ("R100", (entries[0][1][0], "coordination/CONTROL-TOWER/renamed.yml"))
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_RENAME_OR_MULTI_PATH_DIFF_FORBIDDEN", {item["code"] for item in result["findings"]})

    def test_closed_mode_requires_complete_exact_closeout_topology(self):
        entries = exact_closeout_entries()[1:]
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_REQUIRED_DIFF_STATUS_MISMATCH", {item["code"] for item in result["findings"]})

    def test_closed_mode_rejects_wrong_action_on_allowed_path(self):
        entries = exact_closeout_entries()
        path = "coordination/ACTIVE-GPT-ENGINEERING-WORKERS.yaml"
        entries = [("D" if paths == (path,) else status, paths) for status, paths in entries]
        result = evaluate_closeout_diff_entries(entries)
        self.assertEqual("FAIL", result["status"])
        self.assertIn("R145_CLOSEOUT_REQUIRED_DIFF_STATUS_MISMATCH", {item["code"] for item in result["findings"]})


if __name__ == "__main__":
    unittest.main()
