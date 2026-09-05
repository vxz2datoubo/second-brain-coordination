import copy
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


class RegistryParsingTests(unittest.TestCase):
    def test_canonical_registry_keeps_legacy_active_pointer_registered(self):
        data = (
            ROOT / registry.REGISTRY_REF
        ).read_bytes()
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


class MultiTaskCollisionTests(unittest.TestCase):
    def _snapshot(self, task_id, collision_domain):
        payload = {
            "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
            "execution_repository": "vxz2datoubo/second-brain-coordination",
            "project_id": "SECOND_BRAIN",
            "task_id": task_id,
            "route_epoch": 1,
            "exact_base_sha": "c" * 40,
            "implementation_branch": f"workbuddy/{task_id.lower()}",
            "collision_domain": collision_domain,
            "canonical_main_sha": MAIN,
        }
        return base._issue_authority(payload)

    def test_duplicate_task_identity_fails_closed(self):
        first = self._snapshot("TASK-X", "WRITESET_SHA256:a")
        second = self._snapshot("TASK-X", "WRITESET_SHA256:b")
        with patch.object(
            registry,
            "registered_task_index_refs",
            return_value=(MAIN, ("coordination/a.yaml", "coordination/b.yaml")),
        ), patch.object(
            registry,
            "build_verified_canonical_authority_for_task_index",
            side_effect=[first, second],
        ):
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_distinct_tasks_same_collision_domain_fail_closed(self):
        first = self._snapshot("TASK-X", "WRITESET_SHA256:same")
        second = self._snapshot("TASK-Y", "WRITESET_SHA256:same")
        with patch.object(
            registry,
            "registered_task_index_refs",
            return_value=(MAIN, ("coordination/a.yaml", "coordination/b.yaml")),
        ), patch.object(
            registry,
            "build_verified_canonical_authority_for_task_index",
            side_effect=[first, second],
        ):
            with self.assertRaises(base.ExecutionContractError):
                registry.build_registered_authorities(".")

    def test_distinct_tasks_distinct_collisions_can_coexist(self):
        first = self._snapshot("TASK-X", "WRITESET_SHA256:a")
        second = self._snapshot("TASK-Y", "WRITESET_SHA256:b")
        with patch.object(
            registry,
            "registered_task_index_refs",
            return_value=(MAIN, ("coordination/a.yaml", "coordination/b.yaml")),
        ), patch.object(
            registry,
            "build_verified_canonical_authority_for_task_index",
            side_effect=[first, second],
        ):
            result = registry.build_registered_authorities(".")
        self.assertEqual(len(result), 2)


if __name__ == "__main__":
    unittest.main()
