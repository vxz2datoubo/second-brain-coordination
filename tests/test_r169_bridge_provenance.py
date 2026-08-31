from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import director_sequence
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.review import review_packet
from creative_runtime.review_ticket import validate_review_ticket
from creative_runtime.saves import SaveStore, SavedSession, V2_SCHEMA
from creative_runtime.timeline import build_timeline


ROOT = Path(__file__).resolve().parents[1]


def legacy_workspace(workspace: Path, actions: list[str]) -> bytes:
    """Build an actual S00-S06 v1 file with its original action vocabulary."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("old_cli", ROOT / "apps" / "cli" / "creativectl.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.initialize(workspace)
    for action in actions:
        module.choose(workspace, action)
    return (workspace / "session.json").read_bytes()


class R169MigrationBridgeProvenanceTests(unittest.TestCase):
    def test_bridge_positions_and_ids_are_whole_history_bound(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = legacy_workspace(workspace, ["approach"])
            store = SaveStore(workspace)
            migrated = store.load()
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            self.assertEqual([event.event_type for event in migrated.ledger.events].count("migration_bridge"), 0)

            forged = CreativeLedger.from_records(migrated.ledger.to_records())
            forged.append("migration_bridge", {
                "kind": "legacy_terminal_resolution", "source_digest": migrated.migration["source_digest"],
                "state_neutral": True,
            }, "2030-01-01T00:59:00Z")
            payload = {"schema": V2_SCHEMA, "events": forged.to_records(), "migration": migrated.migration}
            store.save_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

            for consumer in (
                lambda: store.load(),
                lambda: SavedSession(forged, migrated.migration).state(),
                lambda: build_timeline(SavedSession(forged, migrated.migration)),
                lambda: director_sequence(SavedSession(forged, migrated.migration)),
                lambda: review_packet(SavedSession(forged, migrated.migration)),
            ):
                with self.assertRaisesRegex(LedgerViolation, "Migration bridge positions"):
                    consumer()

    def test_expected_terminal_bridge_is_source_bound_and_cannot_move_or_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = legacy_workspace(workspace, ["approach", "listen"])
            session = SaveStore(workspace).load()
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            expected = [(event.sequence, event.event_id) for event in session.ledger.events if event.event_type == "migration_bridge"]
            self.assertEqual(len(expected), 1)
            self.assertEqual(review_packet(session)["event_count"], len(session.ledger.events))

            records = session.ledger.to_records()
            moved = records[:]
            bridge = moved.pop(expected[0][0])
            moved.insert(1, bridge)
            # Reconstructing this list cannot silently repair sequence/hash IDs.
            with self.assertRaises(LedgerViolation):
                SavedSession(CreativeLedger.from_records(moved), session.migration).validate()

            duplicate = CreativeLedger.from_records(records)
            duplicate.append("migration_bridge", dict(session.ledger.events[-1].payload), "2030-01-01T00:59:00Z")
            with self.assertRaisesRegex(LedgerViolation, "Migration bridge positions"):
                SavedSession(duplicate, session.migration).validate()

    def test_lossy_route_remains_rejected_without_shadow_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = legacy_workspace(workspace, ["listen", "approach", "leave"])
            store = SaveStore(workspace)
            with self.assertRaisesRegex(LedgerViolation, "lossy"):
                store.load()
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertFalse(store.save_path.exists())

    def test_terminal_loop_migrates_before_default_and_preserves_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = legacy_workspace(workspace, ["approach"])
            import importlib.util
            spec = importlib.util.spec_from_file_location("cli_again", ROOT / "apps" / "cli" / "creativectl.py")
            assert spec and spec.loader
            cli = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cli)
            result = cli.terminal_loop(workspace)
            self.assertEqual(result["status"], "resumed")
            self.assertTrue((workspace / "saves" / "default.json").exists())
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_direct_state_patch_is_not_a_saved_session_escape_hatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            session = SaveStore(workspace).create()
            forged = CreativeLedger.from_records(session.ledger.to_records())
            forged.append("state_patch", {"patch": {"risk_delta": -100}}, "2030-01-01T00:01:00Z")
            with self.assertRaisesRegex(LedgerViolation, "event type"):
                SavedSession(forged).state()

    def test_review_ticket_requires_all_exact_head_binding_fields(self) -> None:
        ticket = {
            "effective_spec_snapshot_id": "SECOND-BRAIN-R169-ISSUE507-SNAPSHOT-001",
            "effective_spec_snapshot_ref": "issuecomment-5466107846",
            "canonical_base": "3a48f402fedde6fe0e6ecc96708a8dc271ec23e0",
            "exact_head": "a" * 40,
            "engineering_handoff_ref": "issuecomment-pending",
        }
        validate_review_ticket(ticket)
        del ticket["engineering_handoff_ref"]
        with self.assertRaises(ValueError):
            validate_review_ticket(ticket)


if __name__ == "__main__":
    unittest.main()
