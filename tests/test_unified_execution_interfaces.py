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
            "CANONICAL_EXECUTION_AUTHORITY_CHAIN_v1",
            "GPT_TO_EXECUTOR_DISPATCH_v1",
            "WORKBUDDY_RETURN_PACKAGE_v1",
            "EXECUTION_CARRIER_RELEASE_v1",
            "EXECUTION_CARRIER_HANDOFF_v1",
            "GPT_INDEPENDENT_REVIEW_REQUEST_v1",
            "ENGINEERING_PRODUCTIVITY_RECEIPT_v1",
            "LOCAL_BRIDGE_ADMISSION_v1",
            "PROJECT_EXECUTION_ADAPTER_VALIDATION_v1",
        ):
            self.assertIn(f"{object_id}:", interfaces)

    def test_dispatch_and_return_are_exact_bound_and_non_authority_minting(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        for field in (
            "control_plane_repository",
            "execution_repository",
            "exact_base_sha",
            "implementation_branch",
            "collision_domain",
            "authority_chain_receipt_digest",
            "authority_refs",
            "authority_digests",
            "authorized_paths",
            "authority_grants",
            "authority_denials",
            "completion_signal",
        ):
            self.assertIn(f"    - {field}", interfaces)
        self.assertIn('    - "authorized_paths_must_be_subset_of_canonical_authorized_paths"', interfaces)
        self.assertIn('    - "authority_grants_must_be_subset_of_canonical_authority_grants"', interfaces)
        self.assertIn('    - "no_authority_is_inferred_from_model_or_carrier"', interfaces)
        self.assertIn('    - "return_package_never_self_asserts_ACCEPT"', interfaces)

    def test_carrier_handoff_requires_verified_release_and_full_new_admission(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('trusted_builder: "build_verified_release_witness(repo_path, release_ref)"', interfaces)
        self.assertIn('    - "release_witness_must_be_VerifiedReleaseWitness_from_fresh_canonical_main"', interfaces)
        self.assertIn('    - "released_lease_ref_and_digest_must_match_old_trusted_authority"', interfaces)
        self.assertIn('    - "new_writer_must_pass_full_validate_local_admission_against_new_trusted_authority"', interfaces)
        self.assertIn('    - "same_task_simultaneous_writers_forbidden"', interfaces)

    def test_bridge_admission_requires_trusted_builder_and_fails_closed(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('trusted_builder: "build_verified_canonical_authority(repo_path)"', interfaces)
        self.assertIn('caller_supplied_authority_mapping: "REJECT"', interfaces)
        self.assertIn('    - "trusted_builder_fresh_readback_succeeds"', interfaces)
        self.assertIn('    - "collision_domain_available"', interfaces)
        self.assertIn('    - "credential_secret_policy_loaded"', interfaces)
        self.assertIn('  otherwise: "FAIL_CLOSED_NO_PROCESS_START"', interfaces)

    def test_adapter_semantic_validation_is_explicit(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('actual_adapter_files_must_be_executed_in_CI: true', interfaces)
        for section in (
            "repositories",
            "canonical_entrypoints",
            "authority",
            "allowed_execution_carriers",
            "default_model_profiles",
            "collision_domains",
            "tool_interfaces",
            "hard_boundaries",
            "acceptance",
            "handoff",
        ):
            self.assertIn(f"    - {section}", interfaces)

    def test_review_and_productivity_objects_do_not_blur_acceptance(self):
        interfaces = text("coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml")
        self.assertIn('    - "any_head_movement_requires_new_review_request"', interfaces)
        self.assertIn('    - "ACCEPT_is_not_canonical"', interfaces)
        self.assertIn('update_rule: "MULTIPLE_COMPARABLE_TASKS_REQUIRED_BEFORE_GLOBAL_ROUTING_DEFAULT_CHANGE"', interfaces)


if __name__ == "__main__":
    unittest.main()
