from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import director_sequence
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.review import review_packet
from creative_runtime.saves import SaveStore, SavedSession, V2, _derive_from_source
from creative_runtime.timeline import build_timeline

ROOT = Path(__file__).resolve().parents[1]

def make_real_v1(workspace: Path, actions: list[str]) -> bytes:
    spec = importlib.util.spec_from_file_location("legacy_cli", ROOT / "apps" / "cli" / "creativectl.py")
    assert spec and spec.loader
    cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
    cli.initialize(workspace)
    for action in actions: cli.choose(workspace, action)
    return (workspace / "session.json").read_bytes()

class ImmutableSourceBindingTests(unittest.TestCase):
    def test_swapped_canonical_receipt_and_ledger_cannot_rebind_source_a(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            root_path = Path(root); source_a_dir = root_path / "source-a"; source_b_dir = root_path / "source-b"
            source_a = make_real_v1(source_a_dir, ["approach"])
            source_b = make_real_v1(source_b_dir, ["approach", "listen"])
            store = SaveStore(source_a_dir)
            original = store.load()
            self.assertEqual(source_a_dir.joinpath("session.json").read_bytes(), source_a)
            receipt_b, ledger_b = _derive_from_source(source_b)
            store.save_path.write_text(json.dumps({"schema": V2, "events": ledger_b.to_records(), "migration": receipt_b}, sort_keys=True), encoding="utf-8")
            forged = SavedSession(ledger_b, receipt_b, source_a_dir / "session.json")
            for surface in (lambda: store.load(), lambda: forged.state(), lambda: build_timeline(forged), lambda: director_sequence(forged), lambda: review_packet(forged)):
                with self.assertRaisesRegex(LedgerViolation, "immutable legacy source"):
                    surface()
            self.assertEqual(source_a_dir.joinpath("session.json").read_bytes(), source_a)

    def test_bridge_set_remains_exact_and_a_real_terminal_bridge_survives(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root); original = make_real_v1(workspace, ["approach", "listen"])
            session = SaveStore(workspace).load()
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            bridges = [event for event in session.ledger.events if event.event_type == "migration_bridge"]
            self.assertEqual(len(bridges), 1)
            forged = CreativeLedger.from_records(session.ledger.to_records())
            forged.append("migration_bridge", dict(bridges[0].payload), "2030-01-01T00:59:00Z")
            with self.assertRaisesRegex(LedgerViolation, "Migration bridge positions"):
                SavedSession(forged, session.migration, workspace / "session.json").state()

    def test_no_bridge_source_rejects_a_hash_valid_suffix_bridge(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root); make_real_v1(workspace, ["approach"])
            session = SaveStore(workspace).load()
            forged = CreativeLedger.from_records(session.ledger.to_records())
            forged.append("migration_bridge", {"kind": "legacy_terminal_resolution", "source_digest": session.migration["source_digest"], "state_neutral": True}, "2030-01-01T00:59:00Z")
            with self.assertRaisesRegex(LedgerViolation, "Migration bridge positions"):
                SavedSession(forged, session.migration, workspace / "session.json").state()

    def test_lossy_legacy_never_creates_shadow_save(self) -> None:
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root); original = make_real_v1(workspace, ["listen", "approach", "leave"])
            store = SaveStore(workspace)
            with self.assertRaisesRegex(LedgerViolation, "lossy"):
                store.load()
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            self.assertFalse(store.save_path.exists())

if __name__ == "__main__": unittest.main()
