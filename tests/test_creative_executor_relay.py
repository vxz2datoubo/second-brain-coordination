from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "validate_creative_executor_relay.py"
PACKAGE_PATH = (
    ROOT
    / "coordination"
    / "PROGRAMS"
    / "CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001"
    / "CODEX-R175"
    / "EXECUTOR-RELAY-QUEUE.yaml"
)
SPEC = importlib.util.spec_from_file_location("validate_creative_executor_relay", TOOL_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ExecutorRelayValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(PACKAGE_PATH.read_text(encoding="utf-8"))

    def test_current_package_is_safely_blocked_until_workbuddy_route(self) -> None:
        checks = MODULE.validate_package(self.payload)
        self.assertIn("target_authority_fail_closed", checks)
        self.assertIn("dedicated_checkpoint_ref_valid", checks)

    def test_moving_implementation_branch_cannot_be_checkpoint_ref(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["source"]["checkpoint_remote_ref"] = (
            "refs/remotes/origin/" + candidate["source"]["branch"]
        )
        with self.assertRaisesRegex(MODULE.RelayValidationError, "dedicated executor checkpoint"):
            MODULE.validate_package(candidate)

    def test_baton_or_chat_cannot_replace_route_authority(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["relay_state"] = "WORKBUDDY_ROUTE_READY"
        with self.assertRaisesRegex(MODULE.RelayValidationError, "must fail closed"):
            MODULE.validate_package(candidate)

    def test_executable_route_requires_all_binding_references(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["relay_state"] = "WORKBUDDY_ROUTE_READY"
        candidate["target"]["route_authority"]["execution_allowed"] = True
        candidate["target"]["route_authority"]["route_ref"] = "coordination/ROUTES/example.yaml"
        with self.assertRaisesRegex(MODULE.RelayValidationError, "claim_ref"):
            MODULE.validate_package(candidate)

    def test_complete_route_can_open_workbuddy_ready_state(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["relay_state"] = "WORKBUDDY_ROUTE_READY"
        route = candidate["target"]["route_authority"]
        route.update(
            execution_allowed=True,
            route_ref="coordination/ROUTES/example.yaml",
            claim_ref="coordination/PROGRAMS/example/WORK-CLAIM.yaml",
            lease_ref="coordination/PROGRAMS/example/TASK-LEASE.yaml",
            snapshot_ref="issuecomment-1",
        )
        checks = MODULE.validate_package(candidate)
        self.assertIn("target_authority_complete", checks)

    def test_overlapping_write_surface_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["target"]["write_surfaces_after_future_route"] = ["tests/**"]
        with self.assertRaisesRegex(MODULE.RelayValidationError, "single-writer overlap"):
            MODULE.validate_package(candidate)

    def test_executor_receipt_cannot_claim_final_acceptance(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["verification_plan"]["receipt_semantics"]["independent_acceptance"] = True
        with self.assertRaisesRegex(MODULE.RelayValidationError, "cannot grant acceptance"):
            MODULE.validate_package(candidate)

    def test_secret_like_verification_command_is_rejected(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["verification_plan"]["commands"] = ["runner --token abc"]
        with self.assertRaisesRegex(MODULE.RelayValidationError, "secret material"):
            MODULE.validate_package(candidate)

    def test_verification_command_must_bind_checkpoint_identity(self) -> None:
        candidate = copy.deepcopy(self.payload)
        candidate["verification_plan"]["commands"] = ["python -m unittest"]
        with self.assertRaisesRegex(MODULE.RelayValidationError, "do not bind"):
            MODULE.validate_package(candidate)


if __name__ == "__main__":
    unittest.main()
