from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from creative_runtime.ledger import CreativeLedger
from creative_runtime.migration import MigrationViolation, migrate_legacy_session
import creative_runtime.migration as migration


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("legacy_creativectl", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
legacy_cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(legacy_cli)


class MigrationPublicationTests(unittest.TestCase):
    def _legacy_workspace(self, root: Path) -> tuple[bytes, dict[str, object]]:
        legacy_cli.run(["--workspace", str(root), "init"])
        legacy_cli.run(["--workspace", str(root), "choose", "listen"])
        legacy_cli.run(["--workspace", str(root), "choose", "approach"])
        original = (root / "session.json").read_bytes()
        state = legacy_cli.run(["--workspace", str(root), "replay"])["state"]
        return original, state

    def test_lossless_migration_preserves_source_and_replayed_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, state = self._legacy_workspace(workspace)
            target = migrate_legacy_session(workspace)
            document = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            self.assertEqual(document["schema"], "CreativeSession/v2")
            self.assertEqual(document["replayed_state"], state)
            self.assertEqual(CreativeLedger.from_records(document["events"]).replay().to_dict(), state)

    def test_race_mutation_after_staging_fails_without_shadow_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._legacy_workspace(workspace)
            source = workspace / "session.json"
            real_stage = migration._write_staged

            def mutate_after_stage(target_directory: Path, payload: bytes) -> Path:
                staged = real_stage(target_directory, payload)
                source.write_bytes(original + b" ")
                return staged

            with mock.patch.object(migration, "_write_staged", side_effect=mutate_after_stage):
                with self.assertRaises(MigrationViolation):
                    migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())
            self.assertEqual(source.read_bytes(), original + b" ")

    def test_preexisting_target_is_never_removed_or_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            target = workspace / "saves" / "default.json"
            target.parent.mkdir(parents=True)
            sentinel = b"preexisting-private-save"
            target.write_bytes(sentinel)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(target.read_bytes(), sentinel)

    def test_identical_completed_migration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._legacy_workspace(workspace)
            first = migrate_legacy_session(workspace, "slot-1")
            first_bytes = first.read_bytes()
            second = migrate_legacy_session(workspace, "slot-1")
            self.assertEqual(second, first)
            self.assertEqual(first.read_bytes(), first_bytes)
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_cli_migration_exposes_safe_operational_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original, _state = self._legacy_workspace(workspace)
            result = legacy_cli.run(["--workspace", str(workspace), "migrate", "--slot", "manual-1"])
            self.assertEqual(result["status"], "migrated")
            self.assertTrue(result["source_preserved"])
            self.assertTrue((workspace / "saves" / "manual-1.json").is_file())
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_save_directory_symlink_is_rejected_without_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            try:
                (workspace / "saves").symlink_to(Path(outside), target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                self.skipTest(f"symlink creation unavailable: {error}")
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_corrupt_matching_existing_target_fails_and_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            target = migrate_legacy_session(workspace)
            document = json.loads(target.read_text(encoding="utf-8"))
            document["events"][-1]["event_hash"] = "0" * 64
            corrupt = json.dumps(document, sort_keys=True).encode("utf-8")
            target.write_bytes(corrupt)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(target.read_bytes(), corrupt)

    def test_tampered_existing_replayed_state_fails_and_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            target = migrate_legacy_session(workspace)
            document = json.loads(target.read_text(encoding="utf-8"))
            document["replayed_state"]["risk_level"] += 100
            corrupt = json.dumps(document, sort_keys=True).encode("utf-8")
            target.write_bytes(corrupt)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertEqual(target.read_bytes(), corrupt)

    def test_unsafe_slot_and_corrupt_ledger_fail_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace, "../escape")
            data = json.loads((workspace / "session.json").read_text(encoding="utf-8"))
            data["events"][-1]["event_hash"] = "0" * 64
            (workspace / "session.json").write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())

    def test_duplicate_legacy_json_keys_fail_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self._legacy_workspace(workspace)
            source = workspace / "session.json"
            document = source.read_text(encoding="utf-8")
            source.write_text(document.replace('{"events":', '{"schema":"CreativeSession/v1","events":', 1), encoding="utf-8")
            with self.assertRaises(MigrationViolation):
                migrate_legacy_session(workspace)
            self.assertFalse((workspace / "saves" / "default.json").exists())


if __name__ == "__main__":
    unittest.main()
