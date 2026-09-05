from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class UnifiedExecutionInterfaceTests(unittest.TestCase):
    def test_global_fabric_binds_self_contained_interface_family(self):
        fabric = text("coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml")
        self.assertIn(
            'interfaces: "coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml"',
            fabric,
        )

    def test_interface_family_defines_all_cross_agent_objects(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        for object_id in (
            "GPT_TO_EXECUTOR_DISPATCH_v1",
            "WORKBUDDY_RETURN_PACKAGE_v1",
            "EXECUTION_CARRIER_HANDOFF_v1",
            "GPT_INDEPENDENT_REVIEW_REQUEST_v1",
            "ENGINEERING_PRODUCTIVITY_RECEIPT_v1",
            "LOCAL_BRIDGE_ADMISSION_v1",
        ):
            self.assertIn(f"{object_id}:", interfaces)

    def test_dispatch_and_return_are_exact_bound_and_non_authority_minting(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        for field in (
            "exact_base_sha",
            "implementation_branch",
            "collision_domain",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
            "completion_signal",
        ):
            self.assertIn(f"    - {field}", interfaces)
        self.assertIn('    - "no_authority_is_inferred_from_model_or_carrier"', interfaces)
        self.assertIn('    - "return_package_never_self_asserts_ACCEPT"', interfaces)
        self.assertIn('    - "head_sha_is_immutable_review_identity_once_submitted"', interfaces)

    def test_carrier_handoff_releases_old_writer_before_new_writer(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn("    - writer_lease_release_proof", interfaces)
        self.assertIn("    - new_writer_admission_required", interfaces)
        self.assertIn('    - "same_task_simultaneous_writers_forbidden"', interfaces)

    def test_review_and_productivity_objects_do_not_blur_acceptance(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('    - "any_head_movement_requires_new_review_request"', interfaces)
        self.assertIn('    - "ACCEPT_is_not_canonical"', interfaces)
        self.assertIn('update_rule: "MULTIPLE_COMPARABLE_TASKS_REQUIRED_BEFORE_GLOBAL_ROUTING_DEFAULT_CHANGE"', interfaces)

    def test_bridge_admission_fails_closed(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('  otherwise: "FAIL_CLOSED_NO_PROCESS_START"', interfaces)
        self.assertIn('    - "collision_domain_available"', interfaces)
        self.assertIn('    - "credential_secret_policy_loaded"', interfaces)


if __name__ == "__main__":
    unittest.main()
