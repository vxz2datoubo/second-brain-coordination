from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_creative_workbuddy_return",
    ROOT / "tools" / "validate_creative_workbuddy_return.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
ZERO_HASH = "0" * 64


def valid_payload() -> dict:
    return {
        "schema": "WorkBuddyRelayResult/v1",
        "package_id": "WB-RETURN-1",
        "agent_id": "WORKBUDDY",
        "return_target": "CODEX",
        "source_checkpoint": {
            "baseline": "7" * 40,
            "exact_head": "c" * 40,
            "checkpoint_remote_ref": "refs/remotes/origin/codex/checkpoint-example",
        },
        "route_authority": {
            "execution_allowed": True,
            "route_ref": "coordination/ROUTES/wb.yaml",
            "claim_ref": "coordination/PROGRAMS/wb/WORK-CLAIM.yaml",
            "lease_ref": "coordination/PROGRAMS/wb/TASK-LEASE.yaml",
            "snapshot_ref": "issuecomment-1",
        },
        "result": "PASS",
        "workbuddy_work": {
            "branch": "workbuddy/interactive-cinematic-check",
            "exact_head": "d" * 40,
            "pushed": True,
            "worktree_clean": True,
            "allowed_write_paths": ["tests/workbuddy/**", "tools/workbuddy/**"],
            "changed_paths": ["tests/workbuddy/test_storage.py"],
        },
        "receipts": [
            {
                "command": "python -m unittest",
                "result": "PASS",
                "stdout_sha256": ZERO_HASH,
                "stderr_sha256": ZERO_HASH,
            }
        ],
        "findings": [],
        "integrity": {
            "acceptance_oracle_changed": False,
            "codex_branch_patched": False,
            "independent_acceptance": False,
            "ready_or_merge_authorized": False,
            "credentials_or_real_user_data_used": False,
            "external_paid_generation_used": False,
        },
        "known_risks": [],
        "single_next_action": "Codex reads the exact-head evidence and resumes the core lane.",
    }


class WorkBuddyReturnValidationTests(unittest.TestCase):
    def test_valid_return_passes(self) -> None:
        checks = MODULE.validate_return(valid_payload())
        self.assertIn("integrity_flags_safe", checks)

    def test_route_must_have_been_executable(self) -> None:
        payload = valid_payload()
        payload["route_authority"]["execution_allowed"] = False
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "executable route"):
            MODULE.validate_return(payload)

    def test_changed_path_outside_allowlist_fails(self) -> None:
        payload = valid_payload()
        payload["workbuddy_work"]["changed_paths"] = ["creative_runtime/contracts.py"]
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "outside WorkBuddy allowlist"):
            MODULE.validate_return(payload)

    def test_pass_cannot_hide_failed_receipt(self) -> None:
        payload = valid_payload()
        payload["receipts"][0]["result"] = "FAIL"
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "PASS contradicts"):
            MODULE.validate_return(payload)

    def test_pass_cannot_hide_blocking_finding(self) -> None:
        payload = valid_payload()
        payload["findings"] = [{"finding_id": "F1", "blocks_milestone": True}]
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "PASS contradicts"):
            MODULE.validate_return(payload)

    def test_fail_requires_failure_evidence(self) -> None:
        payload = valid_payload()
        payload["result"] = "FAIL"
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "requires failed evidence"):
            MODULE.validate_return(payload)

    def test_cannot_claim_final_acceptance(self) -> None:
        payload = valid_payload()
        payload["integrity"]["independent_acceptance"] = True
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "unsafe integrity flags"):
            MODULE.validate_return(payload)

    def test_codex_branch_patch_is_rejected(self) -> None:
        payload = valid_payload()
        payload["integrity"]["codex_branch_patched"] = True
        with self.assertRaisesRegex(MODULE.ReturnValidationError, "codex_branch_patched"):
            MODULE.validate_return(payload)


if __name__ == "__main__":
    unittest.main()
