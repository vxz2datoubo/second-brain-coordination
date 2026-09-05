import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_MODULE_PATH = (
    ROOT / "coordination" / "EXECUTION" / "unified_active_task_registry.py"
)
AUTH_TEST_PATH = ROOT / "tests" / "test_unified_execution_authority.py"

spec = importlib.util.spec_from_file_location(
    "unified_active_task_registry", REGISTRY_MODULE_PATH
)
registry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = registry
spec.loader.exec_module(registry)

helper_spec = importlib.util.spec_from_file_location(
    "unified_execution_authority_fixture", AUTH_TEST_PATH
)
auth_fixture = importlib.util.module_from_spec(helper_spec)
assert helper_spec.loader is not None
sys.modules[helper_spec.name] = auth_fixture
helper_spec.loader.exec_module(auth_fixture)

base = registry.base
MAIN = "a" * 40
SECOND_INDEX = "coordination/EXECUTION/ACTIVE-TASKS/TASK-1.yaml"
THIRD_INDEX = "coordination/EXECUTION/ACTIVE-TASKS/TASK-2.yaml"


def _registry_bytes(*refs):
    entries = []
    for ref in refs:
        entries.append(
            {
                "active_task_index_ref": ref,
                "status": "REGISTERED",
                "legacy_default": ref == registry.LEGACY_DEFAULT_REF,
            }
        )
    return json.dumps(
        {
            "schema": registry.REGISTRY_SCHEMA,
            "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
            "registry_status": "ACTIVE",
            "entries": entries,
        }
    ).encode()


def _files_with_second_index():
    files = auth_fixture._authority_files()
    legacy = registry.LEGACY_DEFAULT_REF
    active = files.pop(legacy)
    files[SECOND_INDEX] = active
    old = legacy.encode()
    new = SECOND_INDEX.encode()
    for path, raw in list(files.items()):
        if isinstance(raw, bytes):
            files[path] = raw.replace(old, new)
    files[registry.REGISTRY_REF] = _registry_bytes(legacy, SECOND_INDEX)
    return files


def _snapshot(
    task_id,
    collision_domain,
    authorized_paths=None,
    execution_repository="vxz2datoubo/second-brain-coordination",
    implementation_branch=None,
    marker=None,
):
    if authorized_paths is None:
        authorized_paths = [f"tests/{task_id.lower()}/**"]
    if implementation_branch is None:
        implementation_branch = f"workbuddy/{task_id.lower()}"
    payload = {
        "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
        "execution_repository": execution_repository,
        "project_id": "SECOND_BRAIN",
        "task_id": task_id,
        "route_epoch": 1,
        "exact_base_sha": "c" * 40,
        "implementation_branch": implementation_branch,
        "collision_domain": collision_domain,
        "canonical_main_sha": MAIN,
        "authorized_paths": authorized_paths,
    }
    if marker is not None:
        payload["marker"] = marker
    return base._issue_authority(payload)


class RegistryParsingTests(unittest.TestCase):
    def test_canonical_registry_keeps_legacy_active_pointer_registered(self):
        data = (ROOT / registry.REGISTRY_REF).read_bytes()
        refs = registry._parse_registry(data)
        self.assertIn(registry.LEGACY_DEFAULT_REF, refs)

    def test_duplicate_json_key_fails_closed(self):
        raw = (
            b'{"schema":"UNIFIED_ACTIVE_TASK_INDEX_REGISTRY/v1",'
            b'"schema":"UNIFIED_ACTIVE_TASK_INDEX_REGISTRY/v1",'
            b'"control_plane_repository":"vxz2datoubo/second-brain-coordination",'
            b'"registry_status":"ACTIVE","entries":[]}'
        )
        with self.assertRaises(base.ExecutionContractError):
            registry._parse_registry(raw)

    def test_duplicate_task_index_ref_fails_closed(self):
        raw = _registry_bytes(
            registry.LEGACY_DEFAULT_REF, registry.LEGACY_DEFAULT_REF
        )
        with self.assertRaises(base.ExecutionContractError):
            registry._parse_registry(raw)

    def test_missing_legacy_default_fails_closed(self):
        raw = json.dumps(
            {
                "schema": registry.REGISTRY_SCHEMA,
                "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
                "registry_status": "ACTIVE",
                "entries": [
                    {
                        "active_task_index_ref": SECOND_INDEX,
                        "status": "REGISTERED",
                        "legacy_default": False,
                    }
                ],
            }
        ).encode()
        with self.assertRaises(base.ExecutionContractError):
            registry._parse_registry(raw)

    def test_path_traversal_task_index_fails_closed(self):
        raw = _registry_bytes(
            registry.LEGACY_DEFAULT_REF,
            "coordination/EXECUTION/../outside.yaml",
        )
        with self.assertRaises(base.ExecutionContractError):
            registry._parse_registry(raw)


class ExplicitRegisteredAuthorityTests(unittest.TestCase):
    def test_registered_second_index_builds_full_verified_authority(self):
        files = _files_with_second_index()

        def read(path):
            return files[path]

        with patch.object(
            registry.gate, "_protected_open", return_value=(MAIN, read)
        ), patch.object(
            registry.gate, "_revalidate_project_adapter_at_sha"
        ), patch.object(
            registry.gate, "_terminal_remote_main_recheck"
        ):
            authority = registry.build_verified_canonical_authority_for_task_index(
                ".", SECOND_INDEX
            )

        base.validate_canonical_authority(authority)
        self.assertEqual(
            authority.as_mapping()["authority_refs"]["active_task_index_ref"],
            SECOND_INDEX,
        )
        self.assertEqual(authority.as_mapping()["task_id"], "TASK-1")

    def test_unregistered_caller_selected_index_fails_before_authority_read(self):
        files = {
            registry.REGISTRY_REF: _registry_bytes(registry.LEGACY_DEFAULT_REF)
        }

        def read(path):
            if path not in files:
                self.fail(f"unregistered task index should not be read: {path}")
            return files[path]

        with patch.object(
            registry.gate, "_protected_open", return_value=(MAIN, read)
        ):
            with self.assertRaises(base.ExecutionContractError):
                registry.build_verified_canonical_authority_for_task_index(
                    ".", SECOND_INDEX
                )

    def test_registered_builder_preserves_terminal_freshness_recheck(self):
        files = _files_with_second_index()

        def read(path):
            return files[path]

        with patch.object(
            registry.gate, "_protected_open", return_value=(MAIN, read)
        ), patch.object(
            registry.gate, "_revalidate_project_adapter_at_sha"
        ), patch.object(
            registry.gate, "_terminal_remote_main_recheck"
        ) as terminal:
            registry.build_verified_canonical_authority_for_task_index(
                ".", SECOND_INDEX
            )

        terminal.assert_called_once_with(".", MAIN)


class RegisteredProcessStartTests(unittest.TestCase):
    def _run_set(self, first, second, claimed=None):
        if claimed is None:
            claimed = first
        admission = {"admission": True}
        dispatch = {"dispatch": True}
        return (
            patch.object(
                registry,
                "registered_task_index_refs",
                return_value=(MAIN, (SECOND_INDEX, THIRD_INDEX)),
            ),
            patch.object(
                registry,
                "build_verified_canonical_authority_for_task_index",
                side_effect=[first, second],
            ),
            admission,
            dispatch,
            claimed,
        )

    def test_process_start_substitutes_registry_wide_fresh_target(self):
        fresh = _snapshot("TASK-X", "WRITESET_SHA256:a", marker="fresh")
        peer = _snapshot("TASK-Y", "WRITESET_SHA256:b", marker="peer")
        claimed = _snapshot("TASK-X", "WRITESET_SHA256:a", marker="fresh")
        read_registry, build, admission, dispatch, _ = self._run_set(
            fresh, peer, claimed
        )
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            returned = registry.validate_process_start_for_task_index(
                ".", SECOND_INDEX, admission, dispatch, claimed
            )
        self.assertIs(returned, fresh)
        validate.assert_called_once_with(admission, dispatch, fresh)

    def test_process_start_rejects_caller_snapshot_that_differs_from_fresh(self):
        fresh = _snapshot("TASK-X", "WRITESET_SHA256:a", marker="fresh")
        peer = _snapshot("TASK-Y", "WRITESET_SHA256:b", marker="peer")
        forged = _snapshot("TASK-X", "WRITESET_SHA256:a", marker="caller-forged")
        read_registry, build, _, _, _ = self._run_set(fresh, peer, forged)
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, {}, {}, forged
                )
        validate.assert_not_called()

    def test_process_start_rejects_registry_duplicate_task_identity(self):
        first = _snapshot("TASK-X", "WRITESET_SHA256:a")
        second = _snapshot("TASK-X", "WRITESET_SHA256:b")
        read_registry, build, _, _, claimed = self._run_set(first, second)
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, {}, {}, claimed
                )
        validate.assert_not_called()

    def test_process_start_rejects_registry_collision_domain_conflict(self):
        first = _snapshot("TASK-X", "WRITESET_SHA256:same")
        second = _snapshot("TASK-Y", "WRITESET_SHA256:same")
        read_registry, build, _, _, claimed = self._run_set(first, second)
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, {}, {}, claimed
                )
        validate.assert_not_called()

    def test_process_start_rejects_registry_overlapping_write_surfaces(self):
        first = _snapshot(
            "TASK-X", "WRITESET_SHA256:a", ["tests/workbuddy/**"]
        )
        second = _snapshot(
            "TASK-Y", "WRITESET_SHA256:b", ["tests/workbuddy/unit/**"]
        )
        read_registry, build, _, _, claimed = self._run_set(first, second)
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, {}, {}, claimed
                )
        validate.assert_not_called()

    def test_process_start_rejects_registry_ambiguous_write_surface(self):
        first = _snapshot(
            "TASK-X", "WRITESET_SHA256:a", ["tests/*/generated"]
        )
        second = _snapshot("TASK-Y", "WRITESET_SHA256:b", ["docs/**"])
        read_registry, build, _, _, claimed = self._run_set(first, second)
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, {}, {}, claimed
                )
        validate.assert_not_called()

    def test_process_start_allows_isolated_cross_repository_peer(self):
        first = _snapshot(
            "TASK-X",
            "WRITESET_SHA256:a",
            ["src/**"],
            "owner/repo-a",
        )
        second = _snapshot(
            "TASK-Y",
            "WRITESET_SHA256:b",
            ["src/**"],
            "owner/repo-b",
        )
        read_registry, build, admission, dispatch, claimed = self._run_set(
            first, second
        )
        with read_registry, build, patch.object(
            base, "validate_local_admission"
        ) as validate:
            returned = registry.validate_process_start_for_task_index(
                ".", SECOND_INDEX, admission, dispatch, claimed
            )
        self.assertIs(returned, first)
        validate.assert_called_once_with(admission, dispatch, first)


class MultiTaskCollisionTests(unittest.TestCase):
    def _enumerate(self, first, second):
        return patch.object(
            registry,
            "registered_task_index_refs",
            return_value=(MAIN, ("coordination/a.yaml", "coordination/b.yaml")),
        ), patch.object(
            registry,
            "build_verified_canonical_authority_for_task_index",
            side_effect=[first, second],
        )

    def test_duplicate_task_identity_fails_closed(self):
        first = _snapshot("TASK-X", "WRITESET_SHA256:a")
        second = _snapshot("TASK-X", "WRITESET_SHA256:b")
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_distinct_tasks_same_collision_domain_fail_closed(self):
        first = _snapshot("TASK-X", "WRITESET_SHA256:same")
        second = _snapshot("TASK-Y", "WRITESET_SHA256:same")
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_distinct_hashes_but_overlapping_write_surfaces_fail_closed(self):
        first = _snapshot(
            "TASK-X", "WRITESET_SHA256:a", ["tests/workbuddy/**"]
        )
        second = _snapshot(
            "TASK-Y", "WRITESET_SHA256:b", ["tests/workbuddy/unit/**"]
        )
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_ambiguous_glob_surface_fails_closed_against_parallel_writer(self):
        first = _snapshot(
            "TASK-X", "WRITESET_SHA256:a", ["tests/*/generated"]
        )
        second = _snapshot("TASK-Y", "WRITESET_SHA256:b", ["docs/**"])
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_same_execution_repo_and_branch_fails_closed(self):
        first = _snapshot(
            "TASK-X",
            "WRITESET_SHA256:a",
            ["src/a/**"],
            implementation_branch="workbuddy/shared-branch",
        )
        second = _snapshot(
            "TASK-Y",
            "WRITESET_SHA256:b",
            ["src/b/**"],
            implementation_branch="workbuddy/shared-branch",
        )
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_distinct_tasks_distinct_collisions_can_coexist(self):
        first = _snapshot("TASK-X", "WRITESET_SHA256:a")
        second = _snapshot("TASK-Y", "WRITESET_SHA256:b")
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            result = registry.build_registered_authorities(".")
        self.assertEqual(len(result), 2)

    def test_same_surface_in_different_execution_repositories_can_coexist(self):
        first = _snapshot(
            "TASK-X", "WRITESET_SHA256:a", ["src/**"], "owner/repo-a"
        )
        second = _snapshot(
            "TASK-Y", "WRITESET_SHA256:b", ["src/**"], "owner/repo-b"
        )
        read_registry, build = self._enumerate(first, second)
        with read_registry, build:
            result = registry.build_registered_authorities(".")
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
