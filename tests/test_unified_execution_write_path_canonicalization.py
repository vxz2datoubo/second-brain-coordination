import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_MODULE_PATH = (
    ROOT / "coordination" / "EXECUTION" / "unified_active_task_registry.py"
)

spec = importlib.util.spec_from_file_location(
    "unified_active_task_registry_write_path_tests", REGISTRY_MODULE_PATH
)
registry = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = registry
spec.loader.exec_module(registry)

base = registry.base
write_paths = registry.write_paths
MAIN = "a" * 40
SECOND_INDEX = "coordination/EXECUTION/ACTIVE-TASKS/TASK-1.yaml"
THIRD_INDEX = "coordination/EXECUTION/ACTIVE-TASKS/TASK-2.yaml"


def _snapshot(task_id, collision_domain, authorized_paths):
    return base._issue_authority(
        {
            "control_plane_repository": base.TRUSTED_CONTROL_PLANE_REPOSITORY,
            "execution_repository": "vxz2datoubo/second-brain-coordination",
            "project_id": "SECOND_BRAIN",
            "task_id": task_id,
            "route_epoch": 1,
            "exact_base_sha": "c" * 40,
            "implementation_branch": f"workbuddy/{task_id.lower()}",
            "collision_domain": collision_domain,
            "canonical_main_sha": MAIN,
            "authorized_paths": authorized_paths,
        }
    )


class CanonicalWritePathGrammarTests(unittest.TestCase):
    def test_accepts_unique_repo_relative_exact_and_recursive_forms(self):
        self.assertEqual(
            write_paths.canonicalize_write_path_pattern("src/a.py"), "src/a.py"
        )
        self.assertEqual(
            write_paths.canonicalize_write_path_pattern("src/generated/**"),
            "src/generated/**",
        )

    def test_rejects_non_unique_or_non_repo_relative_spellings(self):
        rejected = (
            "src/./a.py",
            "src/../a.py",
            "src//a.py",
            "/src/a.py",
            r"src\a.py",
            "C:/src/a.py",
            "/**",
            "src/*/a.py",
            "src/a.py/",
        )
        for path in rejected:
            with self.subTest(path=path):
                with self.assertRaises(write_paths.CanonicalWritePathError):
                    write_paths.canonicalize_write_path_pattern(path)

    def test_duplicate_canonical_write_surface_fails_closed(self):
        with self.assertRaises(write_paths.CanonicalWritePathError):
            write_paths.canonicalize_authorized_paths(["src/a.py", "src/a.py"])


class RegistryProcessStartCanonicalPathTests(unittest.TestCase):
    def _assert_process_start_rejects_peer_path(self, peer_path):
        target = _snapshot("TASK-X", "WRITESET_SHA256:a", ["src/a.py"])
        peer = _snapshot("TASK-Y", "WRITESET_SHA256:b", [peer_path])
        admission = {"admission": True}
        dispatch = {"dispatch": True}

        with patch.object(
            registry,
            "registered_task_index_refs",
            return_value=(MAIN, (SECOND_INDEX, THIRD_INDEX)),
        ), patch.object(
            registry,
            "build_verified_canonical_authority_for_task_index",
            side_effect=[target, peer],
        ), patch.object(base, "validate_local_admission") as validate:
            with self.assertRaises(base.ExecutionContractError):
                registry.validate_process_start_for_task_index(
                    ".", SECOND_INDEX, admission, dispatch, target
                )
        validate.assert_not_called()

    def test_process_start_rejects_dot_segment_equivalence(self):
        self._assert_process_start_rejects_peer_path("src/./a.py")

    def test_process_start_rejects_repeated_separator_equivalence(self):
        self._assert_process_start_rejects_peer_path("src//a.py")

    def test_process_start_rejects_traversal_spelling(self):
        self._assert_process_start_rejects_peer_path("src/sub/../a.py")

    def test_process_start_rejects_absolute_spelling(self):
        self._assert_process_start_rejects_peer_path("/src/a.py")


if __name__ == "__main__":
    unittest.main()
