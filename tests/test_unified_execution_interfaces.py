from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]

def text(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')

class UnifiedExecutionInterfaceTests(unittest.TestCase):

    def test_global_fabric_binds_self_contained_interface_family(self):
        fabric = text('coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml')
        self.assertIn('interfaces: "coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml"', fabric)

    def test_interface_family_defines_all_cross_agent_objects(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        for object_id in ('CANONICAL_EXECUTION_AUTHORITY_CHAIN_v1', 'GPT_TO_EXECUTOR_DISPATCH_v1', 'WORKBUDDY_RETURN_PACKAGE_v1', 'EXECUTION_CARRIER_RELEASE_v1', 'EXECUTION_CARRIER_HANDOFF_v1', 'GPT_INDEPENDENT_REVIEW_REQUEST_v1', 'ENGINEERING_PRODUCTIVITY_RECEIPT_v1', 'OWNER_PROGRESS_REPORT_v1', 'LOCAL_BRIDGE_ADMISSION_v1', 'PROJECT_EXECUTION_ADAPTER_VALIDATION_v1'):
            self.assertIn(f'{object_id}:', interfaces)

    def test_dispatch_and_return_are_exact_bound_and_non_authority_minting(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        for field in ('control_plane_repository', 'execution_repository', 'exact_base_sha', 'implementation_branch', 'collision_domain', 'authority_chain_receipt_digest', 'authority_refs', 'authority_digests', 'authorized_paths', 'authority_grants', 'authority_denials', 'writer_lease_identity', 'completion_signal'):
            self.assertIn(f'    - {field}', interfaces)
        self.assertIn('    - "authorized_paths_must_be_subset_of_canonical_authorized_paths"', interfaces)
        self.assertIn('    - "authority_grants_must_be_subset_of_canonical_authority_grants"', interfaces)
        self.assertIn('    - "writer_lease_identity_exactly_matches_trusted_authority"', interfaces)
        self.assertIn('    - "no_authority_is_inferred_from_model_or_carrier"', interfaces)
        self.assertIn('    - "return_package_never_self_asserts_ACCEPT"', interfaces)

    def test_full_authority_chain_is_semantically_closed(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('semantic_validation_closes_over_every_authority_bearing_document: true', interfaces)
        self.assertIn('cross_document_refs_and_backrefs_must_match: true', interfaces)
        self.assertIn('all_authority_bearing_write_surfaces_must_agree: true', interfaces)
        self.assertIn('writer_lease_identity_derived_from_canonical_task_lease_ref_digest_and_common_identity: true', interfaces)
        for source in ('work_claim_ref', 'task_lease_ref', 'executor_reservation_ref', 'prewrite_snapshot_ref', 'executable_batch_ref'):
            self.assertIn(f'    - {source}', interfaces)

    def test_carrier_handoff_requires_verified_release_and_canonical_new_writer(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('trusted_builder: "build_verified_release_witness(repo_path, release_ref)"', interfaces)
        self.assertIn('    - "release_witness_must_be_VerifiedReleaseWitness_from_fresh_canonical_main"', interfaces)
        self.assertIn('    - "released_lease_ref_and_digest_must_match_old_trusted_authority"', interfaces)
        self.assertIn('    - "new_writer_must_pass_full_validate_local_admission_against_new_trusted_authority"', interfaces)
        self.assertIn('    - "new_writer_lease_identity_must_match_new_trusted_authority"', interfaces)
        self.assertIn('    - "same_task_simultaneous_writers_forbidden"', interfaces)

    def test_bridge_admission_requires_trusted_builder_and_fails_closed(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('trusted_builder: "build_verified_canonical_authority(repo_path)"', interfaces)
        self.assertIn('caller_supplied_authority_mapping: "REJECT"', interfaces)
        self.assertIn('    - "trusted_builder_fresh_readback_succeeds"', interfaces)
        self.assertIn('    - "writer_lease_identity_matches_canonical_task_lease"', interfaces)
        self.assertIn('    - "collision_domain_available"', interfaces)
        self.assertIn('    - "credential_secret_policy_loaded"', interfaces)
        self.assertIn('  otherwise: "FAIL_CLOSED_NO_PROCESS_START"', interfaces)

    def test_adapter_semantic_validation_is_closed_over_known_projects(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('actual_adapter_files_must_be_executed_in_CI: true', interfaces)
        self.assertIn('known_project_registry_is_closed: true', interfaces)
        self.assertIn('unknown_project_adapter: "FAIL_CLOSED_UNTIL_SEMANTIC_FLOOR_IS_REGISTERED"', interfaces)
        self.assertIn('    - "TRADING_ORDER_AUTHORITY_MUST_EQUAL_SEPARATE_EXPLICIT_OWNER_GATE"', interfaces)
        self.assertIn('    - "TRADING_MARKET_DATA_TOOL_MUST_REMAIN_READ_ONLY_AND_PLACE_ORDER_FALSE"', interfaces)
        for section in ('repositories', 'canonical_entrypoints', 'authority', 'allowed_execution_carriers', 'default_model_profiles', 'collision_domains', 'tool_interfaces', 'hard_boundaries', 'acceptance', 'handoff'):
            self.assertIn(f'    - {section}', interfaces)

    def test_review_and_productivity_objects_do_not_blur_acceptance(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('    - "any_head_movement_requires_new_review_request"', interfaces)
        self.assertIn('    - "ACCEPT_is_not_canonical"', interfaces)
        self.assertIn('update_rule: "MULTIPLE_COMPARABLE_TASKS_REQUIRED_BEFORE_GLOBAL_ROUTING_DEFAULT_CHANGE"', interfaces)

    def test_owner_progress_report_is_action_first_and_recommendation_complete(self):
        interfaces = text('coordination/GOVERNANCE/UNIFIED-EXECUTION-INTERFACE-SCHEMAS-v1.0.yaml')
        self.assertIn('OWNER_PROGRESS_REPORT_v1:', interfaces)
        self.assertIn('owner_action_first_when_required: true', interfaces)
        self.assertIn('invented_progress_percent_forbidden: true', interfaces)
        self.assertIn('short_cross_window_prompt_default: true', interfaces)
        self.assertIn('technical_review_detail_stays_in_canonical_ticket: true', interfaces)
        self.assertIn('    - "material_recommendation_or_warning_must_not_be_silently_omitted"', interfaces)
        self.assertIn('    - "recommendation_strength_and_confidence_are_separate_dimensions"', interfaces)
        self.assertIn('    - "candidate_CI_ACCEPT_canonical_deployed_active_must_not_be_collapsed"', interfaces)
        self.assertIn('    - "owner_report_is_not_authority_and_cannot_mint_execution_or_merge_permission"', interfaces)

    def test_gpt_orchestrator_wires_owner_action_recommendation_and_short_prompt_rules(self):
        orchestrator = text('coordination/GPT-UNIFIED-ORCHESTRATOR-START-HERE.md')
        for marker in ('Owner Action Check', 'Recommendation Check', 'Visual Check', '强烈建议 / 建议 / 可选优化 / 不建议 / 强烈不建议', '跨窗口提示词默认**短而明确**', '自动续行规则'):
            self.assertIn(marker, orchestrator)

if __name__ == '__main__':
    unittest.main()
