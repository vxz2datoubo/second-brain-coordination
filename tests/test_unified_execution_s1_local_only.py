from contextlib import ExitStack
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from coordination.EXECUTION import unified_active_task_registry as registry


ROOT = Path(__file__).resolve().parents[1]
MAIN = "f" * 40
R175_INDEX = registry.LEGACY_DEFAULT_REF
R184_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R184-LOCAL-BRIDGE.yaml"
S1_INDEX = "coordination/EXECUTION/ACTIVE-WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE.yaml"
S1_RESERVATION = "coordination/EXECUTION/WORKBUDDY-S1-LUOXUE-SOURCE-PROBE/**"
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


class S1LocalOnlyRegisteredProcessStartTests(unittest.TestCase):
    def _trusted_tree(self):
        def read(path):
            return (ROOT / path).read_bytes()

        stack = ExitStack()
        stack.enter_context(
            patch.object(registry.gate, "_protected_open", return_value=(MAIN, read))
        )
        stack.enter_context(
            patch.object(registry.gate, "_revalidate_project_adapter_at_sha")
        )
        stack.enter_context(
            patch.object(registry.gate, "_terminal_remote_main_recheck")
        )
        return stack

    def _authority(self, index_ref):
        return registry.build_verified_canonical_authority_for_task_index(".", index_ref)

    def _process_start(self, index_ref, authority, dispatch):
        admission = _admission(authority, dispatch)
        return registry.validate_process_start_for_task_index(
            ".", index_ref, admission, dispatch, authority
        )

    def _assert_s1_process_start_rejects_after_generic_accepts(self, dispatch):
        s1 = self._authority(S1_INDEX)
        admission = _admission(s1, dispatch)
        base.validate_local_admission(admission, dispatch, s1)
        with self.assertRaises(base.ExecutionContractError):
            registry.validate_process_start_for_task_index(
                ".", S1_INDEX, admission, dispatch, s1
            )

    def test_registry_wide_r175_r184_r186_and_full_s1_chain_pass(self):
        with self._trusted_tree():
            authorities = registry.build_registered_authorities(".")
            by_task = {item.as_mapping()["task_id"]: item for item in authorities}
            self.assertEqual(len(authorities), 3)
            self.assertEqual(
                set(by_task),
                {
                    "WORKBUDDY-R175-ORDERED-BATCH",
                    "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
                    "WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE",
                },
            )
            s1 = by_task["WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE"].as_mapping()
            self.assertEqual(
                s1.get("task_execution_mode"),
                registry.LOCAL_ONLY_NO_GITHUB_WRITE_MODE,
            )
            self.assertEqual(list(s1["authorized_paths"]), [S1_RESERVATION])
            self.assertIn("WRITE_AUTHORIZED_PATHS", s1["authority_grants"])

    def test_s1_exact_valid_local_only_dispatch_passes(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            dispatch = _dispatch(s1, paths=[], grants=["EXECUTE_TASK"])
            self.assertTrue(
                registry.LOCAL_ONLY_REQUIRED_DENIALS
                <= set(dispatch["authority_denials"])
            )
            returned = self._process_start(S1_INDEX, s1, dispatch)
            self.assertEqual(
                returned.as_mapping()["task_id"],
                "WORKBUDDY-R186-S1-LUOXUE-SOURCE-PROBE",
            )

    def test_s1_nonempty_authorized_paths_fail_process_start(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            dispatch = _dispatch(s1, paths=[S1_RESERVATION], grants=["EXECUTE_TASK"])
            self._assert_s1_process_start_rejects_after_generic_accepts(dispatch)

    def test_s1_write_authorized_paths_grant_fails_process_start(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            dispatch = _dispatch(
                s1,
                paths=[],
                grants=["EXECUTE_TASK", "WRITE_AUTHORIZED_PATHS"],
            )
            self._assert_s1_process_start_rejects_after_generic_accepts(dispatch)

    def test_s1_nonempty_paths_plus_write_grant_fail_process_start(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            dispatch = _dispatch(
                s1,
                paths=[S1_RESERVATION],
                grants=["EXECUTE_TASK", "WRITE_AUTHORIZED_PATHS"],
            )
            self._assert_s1_process_start_rejects_after_generic_accepts(dispatch)

    def test_s1_full_denials_do_not_make_git_capability_legal(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            dispatch = _dispatch(
                s1,
                paths=[S1_RESERVATION],
                grants=["EXECUTE_TASK", "WRITE_AUTHORIZED_PATHS"],
            )
            self.assertTrue(
                registry.LOCAL_ONLY_REQUIRED_DENIALS
                <= set(dispatch["authority_denials"])
            )
            self._assert_s1_process_start_rejects_after_generic_accepts(dispatch)

    def test_s1_collision_reservation_never_materializes_as_dispatch_path(self):
        with self._trusted_tree():
            s1 = self._authority(S1_INDEX)
            valid = _dispatch(s1, paths=[], grants=["EXECUTE_TASK"])
            self.assertNotIn(S1_RESERVATION, valid["authorized_paths"])
            self._process_start(S1_INDEX, s1, valid)

            invalid = _dispatch(
                s1,
                paths=[S1_RESERVATION],
                grants=["EXECUTE_TASK", "WRITE_AUTHORIZED_PATHS"],
            )
            with self.assertRaises(base.ExecutionContractError):
                self._process_start(S1_INDEX, s1, invalid)

    def test_r175_existing_git_write_dispatch_still_passes(self):
        with self._trusted_tree():
            r175 = self._authority(R175_INDEX)
            dispatch = _dispatch(r175)
            self.assertTrue(dispatch["authorized_paths"])
            self.assertIn("WRITE_AUTHORIZED_PATHS", dispatch["authority_grants"])
            returned = self._process_start(R175_INDEX, r175, dispatch)
            self.assertEqual(
                returned.as_mapping()["task_id"], "WORKBUDDY-R175-ORDERED-BATCH"
            )

    def test_r184_existing_git_write_dispatch_still_passes(self):
        with self._trusted_tree():
            r184 = self._authority(R184_INDEX)
            dispatch = _dispatch(r184)
            self.assertTrue(dispatch["authorized_paths"])
            self.assertIn("WRITE_AUTHORIZED_PATHS", dispatch["authority_grants"])
            returned = self._process_start(R184_INDEX, r184, dispatch)
            self.assertEqual(
                returned.as_mapping()["task_id"],
                "WORKBUDDY-R184-LOCAL-WORKBUDDY-BRIDGE",
            )


if __name__ == "__main__":
    unittest.main()
