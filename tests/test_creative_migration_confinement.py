from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from creative_runtime.ledger import CreativeLedger
from creative_runtime.migration import MigrationViolation, migrate_legacy_session
import creative_runtime.migration as migration


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("r175_legacy_cli", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
legacy_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(legacy_cli)


class BoundMigrationTests(unittest.TestCase):
    def _workspace(self, root: Path) -> tuple[bytes, dict[str, object]]:
        legacy_cli.run(["--workspace", str(root), "init"])
        legacy_cli.run(["--workspace", str(root), "choose", "listen"])
        legacy_cli.run(["--workspace", str(root), "choose", "approach"])
        source = (root / "session.json").read_bytes()
        state = legacy_cli.run(["--workspace", str(root), "replay"])["state"]
        return source, state

    def test_lossless_cli_migration_preserves_source_and_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source, state = self._workspace(workspace)
            result = legacy_cli.run(["--workspace", str(workspace), "migrate", "--slot", "manual-1"])
            target = Path(result["session"])
            document = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["publication_binding"], "descriptor_lock_identity_pre_and_post_publish")
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertEqual(document["replayed_state"], state)
            self.assertEqual(CreativeLedger.from_records(document["events"]).replay().to_dict(), state)

    def test_mutation_after_final_revalidation_before_publish_leaves_no_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._workspace(workspace)
            source = workspace / "session.json"
            real_publish = migration._publish_create_only

            def mutate_then_publish(staged: Path, target: Path) -> tuple[int, int]:
                source.write_bytes(original + b" ")
                return real_publish(staged, target)

            with mock.patch.object(migration, "_publish_create_only", side_effect=mutate_then_publish):
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_mutation_during_publish_rolls_back_only_created_target(self) -> None:
        if os.name == "nt":
            self.skipTest("Windows byte-range lock proves this path by preventing mutation before publication")
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._workspace(workspace)
            source = workspace / "session.json"
            real_publish = migration._publish_create_only

            def publish_then_mutate(staged: Path, target: Path) -> tuple[int, int]:
                published = real_publish(staged, target)
                source.write_bytes(original + b" ")
                return published

            with mock.patch.object(migration, "_publish_create_only", side_effect=publish_then_mutate):
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_detected_post_publish_identity_failure_rolls_back_created_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._workspace(workspace)
            original_verify = migration._BoundSource.verify_unchanged

            def fail_post_publish(binding: object, phase: str) -> None:
                if phase == "post_publication":
                    raise MigrationViolation("synthetic post-publication identity drift")
                original_verify(binding, phase)

            with mock.patch.object(migration._BoundSource, "verify_unchanged", new=fail_post_publish):
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    @unittest.skipUnless(os.name == "nt", "Windows byte-range append lock regression")
    def test_windows_lock_blocks_append_beyond_current_eof(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._workspace(workspace)
            source = workspace / "session.json"
            real_publish = migration._publish_create_only
            append_blocked = False

            def append_then_publish(staged: Path, target: Path) -> tuple[int, int]:
                nonlocal append_blocked
                try:
                    with source.open("ab", buffering=0) as stream:
                        stream.write(b" ")
                except OSError:
                    append_blocked = True
                return real_publish(staged, target)

            with mock.patch.object(migration, "_publish_create_only", side_effect=append_then_publish):
                target = migrate_legacy_session(workspace)
            self.assertTrue(append_blocked)
            self.assertTrue(target.exists())
            self.assertEqual(source.read_bytes(), original)

    def test_preexisting_target_is_never_overwritten_or_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._workspace(workspace)
            target = workspace / "saves" / "default.json"
            target.parent.mkdir()
            sentinel = b"preexisting-private-data"
            target.write_bytes(sentinel)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(target.read_bytes(), sentinel)

    def test_hardlinked_existing_target_is_rejected_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._workspace(workspace)
            target = migrate_legacy_session(workspace)
            twin = workspace / "saves" / "twin.json"
            os.link(target, twin)
            before = target.read_bytes()
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(target.read_bytes(), before)
            self.assertEqual(twin.read_bytes(), before)

    def test_idempotent_exact_target_and_unsafe_slot(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source, _state = self._workspace(workspace)
            first = migrate_legacy_session(workspace, "slot-1")
            saved = first.read_bytes()
            self.assertEqual(migrate_legacy_session(workspace, "slot-1"), first)
            self.assertEqual(first.read_bytes(), saved)
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace, "../escape")

    def test_symlinked_save_directory_and_workspace_fail_confinement(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            self._workspace(workspace)
            try:
                (workspace / "saves").symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink unavailable: {error}")
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(list(Path(outside).iterdir()), [])

    @unittest.skipUnless(os.name == "nt", "Windows junction regression")
    def test_windows_save_junction_and_workspace_junction_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            self._workspace(workspace)
            junction = workspace / "saves"
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), outside],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if command.returncode != 0:
                self.skipTest("junction creation unavailable: " + command.stderr)
            try:
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace)
                self.assertEqual(list(Path(outside).iterdir()), [])
            finally:
                junction.rmdir()
        with tempfile.TemporaryDirectory() as parent, tempfile.TemporaryDirectory() as real_directory:
            real_workspace = Path(real_directory)
            self._workspace(real_workspace)
            workspace_junction = Path(parent) / "workspace-junction"
            command = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(workspace_junction), str(real_workspace)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            if command.returncode != 0:
                self.skipTest("workspace junction creation unavailable: " + command.stderr)
            try:
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace_junction)
            finally:
                workspace_junction.rmdir()

    def test_duplicate_or_corrupt_legacy_fails_without_shadow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._workspace(workspace)
            source = workspace / "session.json"
            text = source.read_text(encoding="utf-8")
            source.write_text(text.replace('{"events":', '{"schema":"CreativeSession/v1","events":', 1), encoding="utf-8")
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())


if __name__ == "__main__":
    unittest.main()
