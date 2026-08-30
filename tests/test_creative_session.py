from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.contracts import PlayerAction, StoryState, canonical_json
from creative_runtime.ledger import CreativeLedger
from creative_runtime.session import SessionViolation, load_v2_session, migrate_legacy_session, v2_session_path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("creativectl_session", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


class CreativeSessionTests(unittest.TestCase):
    def legacy_route(self, workspace: Path) -> Path:
        creativectl.run(["--workspace", str(workspace), "init"])
        creativectl.run(["--workspace", str(workspace), "choose", "listen"])
        creativectl.run(["--workspace", str(workspace), "choose", "approach"])
        return workspace / "session.json"

    def test_migration_preserves_legacy_bytes_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            legacy = self.legacy_route(workspace)
            before = legacy.read_bytes()
            command = creativectl.run(["--workspace", str(workspace), "migrate"])
            first = migrate_legacy_session(workspace, "2030-01-01T00:02:00Z")
            second = migrate_legacy_session(workspace, "2030-01-01T00:02:00Z")
            loaded = load_v2_session(workspace)
            self.assertEqual(command["status"], "migrated")
            self.assertEqual(first.status, "already_migrated")
            self.assertEqual(second.status, "already_migrated")
            self.assertEqual(legacy.read_bytes(), before)
            self.assertTrue(v2_session_path(workspace).is_file())
            self.assertEqual(loaded.timeline_hash, first.timeline_hash)
            self.assertEqual(loaded.ledger.replay().beat_id, "threshold")

    def test_semantically_forged_but_hash_valid_legacy_never_creates_default_shadow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            ledger = CreativeLedger()
            ledger.append(
                "story_initialized",
                {"state": StoryState("synthetic_archive", "arrival", {"mira": 0}).to_dict()},
                "2030-01-01T00:00:00Z",
            )
            # This new event has a legal hash chain, but its patch tries to add a
            # fact that no canonical `listen` transition grants.
            ledger.append(
                "player_action",
                {
                    "action": PlayerAction("listen", "choice", "Listen at the door").to_dict(),
                    "resulting_patch": {"beat_id": "echo", "reveal_facts": ["a witness is inside", "invented"], "risk_delta": 1},
                },
                "2030-01-01T00:01:00Z",
            )
            legacy = workspace / "session.json"
            legacy.write_text(canonical_json({"schema": "CreativeSession/v1", "events": ledger.to_records()}) + "\n", encoding="utf-8")
            before = legacy.read_bytes()
            with self.assertRaisesRegex(SessionViolation, "losslessly"):
                migrate_legacy_session(workspace, "2030-01-01T00:01:00Z")
            self.assertEqual(legacy.read_bytes(), before)
            self.assertFalse(v2_session_path(workspace).exists())

    def test_tampered_v2_provenance_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.legacy_route(workspace)
            migrate_legacy_session(workspace, "2030-01-01T00:02:00Z")
            target = v2_session_path(workspace)
            record = json.loads(target.read_text(encoding="utf-8"))
            record["migration"]["timeline_hash"] = "0" * 64
            target.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(SessionViolation, "timeline hash"):
                load_v2_session(workspace)


if __name__ == "__main__":
    unittest.main()
