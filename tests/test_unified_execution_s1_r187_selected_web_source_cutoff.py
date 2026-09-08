from contextlib import ExitStack
import copy
from hashlib import sha256
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordination.EXECUTION import unified_active_task_registry as registry


ROOT = Path(__file__).resolve().parents[1]
MOCK_MAIN = "f" * 40
R175_INDEX = registry.LEGACY_DEFAULT_REF
R184_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R184-LOCAL-BRIDGE.yaml"
R186_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE.yaml"
R187_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE.yaml"
R187_RESERVATION = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/**"
R187_COLLISION = "WRITESET_SHA256:8e4ef1f93b06aa396a0a53f72f4fff4f0f06a7b677d2003a64876e5bb830101a"
DISPATCH_CONTRACT = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/LOCAL-ONLY-DISPATCH-CONTRACT.yaml"
EVIDENCE_CONTRACT = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/EVIDENCE-CONTRACT.yaml"
BATCH = "coordination/EXECUTION/WORKBUDDY-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE/EXECUTABLE-BATCH.json"
base = registry.base


def _thaw(value):
    if isinstance(value, dict) or hasattr(value, "items"):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_thaw(item) for item in value]
    return value


def _dispatch(authority, *, paths=None, grants=None):
    current = authority.as_mapping()
    fields = (
        *base.COMMON_IDENTITY_FIELDS,
        "canonical_main_sha",
        "authority_chain_receipt_digest",
        "authority_refs",
        "authority_digests",
        "authorized_paths",
        "authority_grants",
        "authority_denials",
        "writer_lease_identity",
    )
    result = {key: _thaw(current[key]) for key in fields}
    if paths is not None:
        result["authorized_paths"] = list(paths)
    if grants is not None:
        result["authority_grants"] = list(grants)
    result.update(
        {
            "executor": "WORKBUDDY_ENGINEERING_EXECUTOR",
            "carrier": "WORKBUDDY_DESKTOP_INTERACTIVE",
            "compute_class": "STANDARD",
            "model_profile": "DEEP_ENGINEERING",
            "resolved_model_display_name": "Deepseek-V4-Pro",
            "model_resolution_status": "RESOLVED",
        }
    )
    result["compute_lane_receipt_digest"] = base.compute_lane_receipt_digest(result)
    return result


def _admission(authority, dispatch):
    result = copy.deepcopy(dispatch)
    result.update(
        {
            "route_status": "READY",
            "execution_allowed": True,
            "writer_lease_identity": authority.as_mapping()["writer_lease_identity"],
        }
    )
    return result


class S1R187SelectedWebSourceCutoffTests(unittest.TestCase):
    def _read(self, path):
        return (ROOT / path).read_bytes()

    def _trusted_tree(self):
        stack = ExitStack()
        stack.enter_context(
            patch.object(registry.gate, "_protected_open", return_value=(MOCK_MAIN, self._read))
        )
        stack.enter_context(patch.object(registry.gate, "_revalidate_project_adapter_at_sha"))
        stack.enter_context(patch.object(registry.gate, "_terminal_remote_main_recheck"))
        return stack

    def _authority(self):
        return registry.build_verified_canonical_authority_for_task_index(".", R187_INDEX)

    def test_registry_wide_r175_r184_r187_and_full_r187_chain_pass(self):
        with self._trusted_tree():
            authorities = registry.build_registered_authorities(".")
        by_task = {item.as_mapping()["task_id"]: item.as_mapping() for item in authorities}
        self.assertEqual(
            set(by_task),
            {
                "WORKBUDDY-R175-ORDERED-BATCH",
                "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
                "WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE",
            },
        )
        r187 = by_task["WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE"]
        self.assertEqual(r187.get("task_execution_mode"), registry.LOCAL_ONLY_NO_GITHUB_WRITE_MODE)
        self.assertEqual(list(r187["authorized_paths"]), [R187_RESERVATION])
        self.assertEqual(r187["collision_domain"], R187_COLLISION)
        self.assertIn("WRITE_AUTHORIZED_PATHS", r187["authority_grants"])

    def test_r187_collision_domain_matches_canonical_reservation_surface(self):
        digest = sha256(
            json.dumps(sorted([R187_RESERVATION]), separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        self.assertEqual("WRITESET_SHA256:" + digest, R187_COLLISION)

    def test_r187_exact_valid_local_only_dispatch_passes(self):
        with self._trusted_tree():
            authority = self._authority()
            dispatch = _dispatch(authority, paths=[], grants=["EXECUTE_TASK"])
            admission = _admission(authority, dispatch)
            returned = registry.validate_process_start_for_task_index(
                ".", R187_INDEX, admission, dispatch, authority
            )
        self.assertEqual(
            returned.as_mapping()["task_id"],
            "WORKBUDDY-R187-S1-SELECTED-WEB-SOURCE-CUTOFF-FRONTIER-PROBE",
        )
        self.assertEqual(dispatch["authorized_paths"], [])
        self.assertEqual(dispatch["authority_grants"], ["EXECUTE_TASK"])

    def test_r187_git_write_projection_fails_closed(self):
        with self._trusted_tree():
            authority = self._authority()
            dispatch = _dispatch(
                authority,
                paths=[R187_RESERVATION],
                grants=["EXECUTE_TASK", "WRITE_AUTHORIZED_PATHS"],
            )
            admission = _admission(authority, dispatch)
            base.validate_local_admission(admission, dispatch, authority)
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", R187_INDEX, admission, dispatch, authority
                )

    def test_registry_replaces_terminal_r186_with_new_identity_without_replay(self):
        text = self._read(registry.REGISTRY_REF).decode("utf-8")
        self.assertIn(R175_INDEX, text)
        self.assertIn(R184_INDEX, text)
        self.assertIn(R187_INDEX, text)
        self.assertNotIn(R186_INDEX, text)

    def test_dispatch_contract_preserves_full_canonical_denial_surface(self):
        text = self._read(DISPATCH_CONTRACT).decode("utf-8")
        required = (
            "authorized_paths: []",
            '    - "EXECUTE_TASK"',
            '    - "NO_GITHUB_WRITE"',
            '    - "NO_REPOSITORY_EDIT"',
            '    - "NO_BRANCH_WRITE"',
            '    - "NO_DIRECT_MAIN_WRITE"',
            '    - "NO_R175_MUTATION"',
            '    - "NO_R184_MUTATION"',
            '    - "NO_LOCAL_BRIDGE_START"',
            '    - "NO_REAL_CAPTURE"',
            '    - "NO_OPERATIONAL_W3_WRITE"',
            '    - "NO_S2_START"',
            '    - "NO_SECRET_CREDENTIAL_READ"',
            '    - "NO_BROWSER_HISTORY_CRAWL"',
            '    - "NO_HOME_PROFILE_CRAWL"',
            '    - "NO_ARBITRARY_CONVERSATION_DISCOVERY"',
            '    - "NO_UNRELATED_LOCAL_FILE_DISCOVERY"',
            '    - "NO_OPENAI_API_DEPENDENCY"',
            '    - "NO_RAW_PRIVATE_MESSAGE_DURABLE_PERSISTENCE"',
        )
        for literal in required:
            self.assertIn(literal, text)

    def test_evidence_contract_freezes_target_cutoff_and_post_cutoff_exclusion(self):
        text = self._read(EVIDENCE_CONTRACT).decode("utf-8")
        required = (
            'allowed_source: "ONE_EXPLICITLY_OWNER_SELECTED_CURRENT_CHATGPT_WEB_CONVERSATION"',
            'mounted_subset_is_not_complete_by_default: true',
            'if_any_full_scope_requirement_unproved: "EXACT_SOURCE_SCOPE_REMAINS_PARTIAL"',
            'cutoff_record_for_both_trigger_modes: "TRIGGER_RECORD_INCLUSIVE"',
            'target_and_cutoff_are_distinct_for_trigger_only_mode: true',
            'capture_context_must_not_admit_records_after_cutoff: true',
            'frozen_identity_mutation_allowed: false',
            'action: "RECONSTRUCT_AND_COMPARE_TO_FROZEN_IDENTITY_NEVER_REFREEZE_SILENTLY"',
            'changed_pre_cutoff_membership_or_order_result: "FAIL_CLOSED_IDENTITY_DRIFT_OR_SOURCE_INCOMPLETE"',
            'raw_private_message_durable_persistence: false',
        )
        for literal in required:
            self.assertIn(literal, text)

    def test_r186_findings_and_unrelated_capability_unknowns_are_carried_forward(self):
        text = self._read(EVIDENCE_CONTRACT).decode("utf-8")
        required = (
            "NBF-R186-01",
            "NBF-R186-02",
            "NBF-R186-03",
            "NBF-R186-04",
            'LIVE_OWNER_TRIGGER: "UNKNOWN"',
            'CURRENT_CONVERSATION_BINDING: "PASS_FOR_OWNER_SELECTED_WEB_PROBE_ONLY"',
            'EXACT_SOURCE_SCOPE: "PARTIAL"',
            'EXACT_CUTOFF_FRONTIER: "UNKNOWN"',
            'AUTHENTICATED_INCREMENTAL_CAPTURE_TRANSPORT: "UNKNOWN"',
            'MOBILE_OFFLINE_DURABLE_INTAKE: "UNKNOWN"',
            'HARD_CAPTURE_CHECKPOINT_COMPLETE: "BLOCKED"',
            'PROGRAM_S2_STARTED: false',
        )
        for literal in required:
            self.assertIn(literal, text)

    def test_batch_is_structural_only_and_does_not_dispatch_workbuddy(self):
        batch = json.loads(self._read(BATCH).decode("utf-8"))
        self.assertEqual(batch["runtime_dispatch"]["authorized_paths"], [])
        self.assertEqual(batch["runtime_dispatch"]["authority_grants"], ["EXECUTE_TASK"])
        self.assertTrue(batch["selected_source"]["owner_selection_required_before_read"])
        self.assertFalse(batch["local_workspace"]["raw_private_message_durable_persistence_allowed"])
        self.assertEqual(
            [item["item_id"] for item in batch["items"]],
            ["S1-R187-V1", "S1-R187-S1", "S1-R187-S2", "S1-R187-S3", "S1-R187-S4", "S1-R187-S5"],
        )
        self.assertTrue(all(item["status"] == "PLANNED" for item in batch["items"]))


if __name__ == "__main__":
    unittest.main()
