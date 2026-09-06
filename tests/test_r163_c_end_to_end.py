from __future__ import annotations

from dataclasses import replace
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from creative_runtime.continuity import compile_director_sequence, validate_sequence
from creative_runtime.contracts import StoryState
from creative_runtime.director import synthetic_asset_index
from creative_runtime.ledger import CreativeLedger, LedgerViolation
from creative_runtime.scene_graph import SceneGraph, synthetic_three_scene_manifest


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "r163"
SPEC = importlib.util.spec_from_file_location("creativectl_r163_c", ROOT / "apps" / "cli" / "creativectl.py")
assert SPEC and SPEC.loader
creativectl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(creativectl)


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def finish_from_threshold(workspace: Path) -> None:
    self_promise = creativectl.run(["--workspace", str(workspace), "choose", "promise"])
    if self_promise["status"] != "chosen":
        raise AssertionError(self_promise)
    self_depart = creativectl.run(["--workspace", str(workspace), "choose", "depart"])
    if self_depart["status"] != "chosen":
        raise AssertionError(self_depart)


class R163CEndToEndEvidenceTests(unittest.TestCase):
    def test_real_legacy_resume_migrates_then_continues_across_all_three_scenes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = fixture_bytes("legacy_session_v1_resume.json")
            (workspace / "session.json").write_bytes(original)

            migrated = creativectl.run(["--workspace", str(workspace), "init"])
            self.assertEqual(migrated["status"], "migrated_legacy")
            self.assertEqual((migrated["state"]["scene_id"], migrated["state"]["beat_id"]), ("interior_archive", "threshold"))
            self.assertEqual((workspace / "session.json").read_bytes(), original)
            default_record = json.loads((workspace / "saves" / "default.json").read_text(encoding="utf-8"))
            self.assertEqual(default_record["migration_receipt"]["source_baseline"], "027642a231e214f8649b273f44de65c82a4901f9")
            self.assertEqual(default_record["migration_receipt"]["event_mappings"][0]["legacy_action_id"], "approach")
            self.assertEqual(default_record["migration_receipt"]["event_mappings"][0]["new_action_id"], "knock")

            finish_from_threshold(workspace)
            timeline = creativectl.run(["--workspace", str(workspace), "timeline"])["entries"]
            transcript = creativectl.run(["--workspace", str(workspace), "transcript"])["turns"]
            self.assertEqual(
                [(item["state"]["scene_id"], item["state"]["beat_id"]) for item in timeline],
                [
                    ("archive_gate", "arrival"),
                    ("interior_archive", "threshold"),
                    ("interior_archive", "accord"),
                    ("dawn_courtyard", "return"),
                ],
            )
            self.assertEqual({item["state"]["scene_id"] for item in timeline}, {"archive_gate", "interior_archive", "dawn_courtyard"})
            self.assertEqual([item["state"] for item in transcript], [item["state"] for item in timeline])
            final = transcript[-1]["state"]
            self.assertEqual(final["relationships"]["mira"], 2)
            self.assertEqual(final["risk_level"], -1)
            self.assertEqual(final["flags"], {"accord": "kept", "arrival": "announced"})
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_save_restore_is_deterministic_and_branch_compare_exposes_real_differences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            creativectl.run(["--workspace", str(workspace), "slot", "save", "root"])

            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "slot", "save", "mid"])
            creativectl.run(["--workspace", str(workspace), "choose", "knock"])
            finish_from_threshold(workspace)
            uninterrupted = creativectl._load_session(workspace).to_records()
            creativectl.run(["--workspace", str(workspace), "slot", "save", "heard_final"])

            restored = creativectl.run(["--workspace", str(workspace), "slot", "load", "mid"])
            self.assertTrue(restored["restored_to_default"])
            self.assertEqual((restored["state"]["scene_id"], restored["state"]["beat_id"]), ("archive_gate", "echo"))
            creativectl.run(["--workspace", str(workspace), "choose", "knock"])
            finish_from_threshold(workspace)
            self.assertEqual(creativectl._load_session(workspace).to_records(), uninterrupted)

            creativectl.run(["--workspace", str(workspace), "slot", "load", "root"])
            creativectl.run(["--workspace", str(workspace), "choose", "knock"])
            finish_from_threshold(workspace)
            creativectl.run(["--workspace", str(workspace), "slot", "save", "direct_final"])

            comparison = creativectl.run(
                ["--workspace", str(workspace), "compare", "heard_final", "direct_final"]
            )
            self.assertEqual(comparison["status"], "compared")
            self.assertFalse(comparison["same_event_digest"])
            self.assertFalse(comparison["same_final_state"])
            self.assertEqual(comparison["left_state"]["scene_id"], "dawn_courtyard")
            self.assertEqual(comparison["right_state"]["scene_id"], "dawn_courtyard")
            left_transitions = [item.get("transition_id") for item in comparison["left_event_summary"]]
            right_transitions = [item.get("transition_id") for item in comparison["right_event_summary"]]
            self.assertIn("gate_listen", left_transitions)
            self.assertNotIn("gate_listen", right_transitions)
            self.assertNotEqual(comparison["left_state"]["known_facts"], comparison["right_state"]["known_facts"])

    def test_corrupt_incompatible_and_unsafe_slots_do_not_damage_valid_sibling_or_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            creativectl.run(["--workspace", str(workspace), "slot", "save", "good"])
            default_before = (workspace / "saves" / "default.json").read_bytes()
            (workspace / "saves" / "broken.json").write_text("not-json", encoding="utf-8")
            (workspace / "saves" / "incompatible.json").write_text(
                json.dumps({"schema": "CreativeSession/v9", "manifest_hash": "wrong", "events": []}),
                encoding="utf-8",
            )

            for slot in ("broken", "incompatible", "../escape"):
                with self.subTest(slot=slot):
                    with self.assertRaises(LedgerViolation):
                        creativectl.run(["--workspace", str(workspace), "slot", "load", slot])
                    self.assertEqual((workspace / "saves" / "default.json").read_bytes(), default_before)

            good = creativectl.run(["--workspace", str(workspace), "slot", "load", "good"])
            self.assertEqual(good["status"], "loaded")
            self.assertEqual((good["state"]["scene_id"], good["state"]["beat_id"]), ("archive_gate", "echo"))

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            source = fixture_bytes("legacy_session_v1_multi_action.json")
            (workspace / "session.json").write_bytes(source)
            output = io.StringIO()
            result = creativectl.terminal_loop(workspace, io.StringIO("quit\n"), output)
            self.assertEqual(result["status"], "legacy_incompatible")
            self.assertEqual((workspace / "session.json").read_bytes(), source)
            self.assertFalse((workspace / "saves" / "default.json").exists())
            self.assertIn("original preserved", output.getvalue())

    def test_director_and_review_packet_are_stable_diagnostic_only_and_bound_to_final_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            original = fixture_bytes("legacy_session_v1_resume.json")
            (workspace / "session.json").write_bytes(original)
            creativectl.run(["--workspace", str(workspace), "init"])
            finish_from_threshold(workspace)

            director = creativectl.run(["--workspace", str(workspace), "director", "--duration-budget", "40"])
            self.assertEqual(director["status"], "director_packet")
            self.assertFalse(director["generation_called"])
            self.assertTrue(director["can_generate"])
            self.assertEqual(director["diagnostics"], [])
            self.assertEqual((director["final_state_handoff"]["scene_id"], director["final_state_handoff"]["beat_id"]), ("dawn_courtyard", "return"))
            self.assertEqual(
                [item["transition_id"] for item in director["cross_cut_contract"]],
                ["gate_knock", "threshold_promise", "accord_depart"],
            )

            first = creativectl.run(["--workspace", str(workspace), "review-packet", "--duration-budget", "40"])
            second = creativectl.run(["--workspace", str(workspace), "review-packet", "--duration-budget", "40"])
            self.assertEqual(first["review_digest"], second["review_digest"])
            self.assertEqual(first["manifest_hash"], creativectl._graph().manifest_hash)
            self.assertEqual(first["session_schema"], "CreativeSession/v2")
            self.assertFalse(first["generation_called"])
            self.assertFalse(first["canonical_knowledge_written"])
            self.assertEqual(first["final_state"], director["final_state_handoff"]["state"])
            self.assertEqual([item["state"] for item in first["transcript"]], [item["state"] for item in first["timeline"]])

            ledger = creativectl._load_session(workspace)
            before = ledger.to_records()
            graph = SceneGraph(synthetic_three_scene_manifest())
            sequence = compile_director_sequence(ledger, graph, duration_budget_seconds=90)
            altered_beats = list(sequence.beats)
            target = altered_beats[1]
            altered_beats[1] = replace(
                target,
                action_id=None,
                transition_id=None,
                revealed_facts=(),
                state=StoryState(
                    scene_id=target.state.scene_id,
                    beat_id=target.state.beat_id,
                    relationships=target.state.relationships,
                    known_facts=("unearned spoiler",),
                    risk_level=target.state.risk_level,
                    flags=target.state.flags,
                ),
            )
            altered_packets = list(sequence.packets)
            shot = altered_packets[1].shots[0]
            changed_shot = replace(
                shot,
                axis="opposite-axis",
                reference_artifact_ids=("art_scene_synthetic_archive", "art_character_mira"),
            )
            altered_packets[1] = replace(altered_packets[1], shots=(changed_shot,))
            diagnostics = validate_sequence(
                tuple(altered_beats),
                tuple(altered_packets),
                synthetic_asset_index(),
                10,
            )
            repeated = validate_sequence(
                tuple(altered_beats),
                tuple(altered_packets),
                synthetic_asset_index(),
                10,
            )
            codes = {item.code for item in diagnostics}
            self.assertTrue(
                {
                    "screen_direction_violation",
                    "spatial_relation_violation",
                    "identity_continuity_violation",
                    "knowledge_reveal_order_violation",
                    "action_causality_violation",
                    "duration_budget_exceeded",
                }
                <= codes
            )
            self.assertEqual([item.to_dict() for item in diagnostics], [item.to_dict() for item in repeated])
            self.assertEqual(ledger.to_records(), before)
            self.assertEqual((workspace / "session.json").read_bytes(), original)

    def test_cli_surface_is_offline_replayable_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "init"])["status"], "initialized")
            said = creativectl.run(["--workspace", str(workspace), "say", "knock"])
            self.assertEqual(said["status"], "chosen")
            self.assertEqual(said["action_id"], "knock")
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "slot", "save", "checkpoint"])["status"], "saved")
            resumed = creativectl.run(["--workspace", str(workspace), "resume"])
            self.assertEqual((resumed["state"]["scene_id"], resumed["state"]["beat_id"]), ("interior_archive", "threshold"))
            creativectl.run(["--workspace", str(workspace), "choose", "promise"])
            replayed = creativectl.run(["--workspace", str(workspace), "replay"])
            self.assertEqual(replayed["status"], "replayed")
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "transcript"])["status"], "transcript")
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "director"])["generation_called"], False)
            packet = creativectl.run(["--workspace", str(workspace), "review-packet"])
            self.assertFalse(packet["generation_called"])
            self.assertFalse(packet["canonical_knowledge_written"])
            self.assertIn("checkpoint", creativectl.run(["--workspace", str(workspace), "slot", "list"])["slots"])
            loaded = creativectl.run(["--workspace", str(workspace), "slot", "load", "checkpoint"])
            self.assertEqual(loaded["state"]["beat_id"], "threshold")
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "slot", "delete", "checkpoint"])["status"], "deleted")
            self.assertTrue(creativectl.run(["--workspace", str(workspace), "interactive"])["offline"])
            before = creativectl.run(["--workspace", str(workspace), "resume"])["state"]
            invalid = creativectl.run(["--workspace", str(workspace), "choose", "invent"])
            self.assertEqual(invalid["status"], "clarification_required")
            self.assertEqual(creativectl.run(["--workspace", str(workspace), "resume"])["state"], before)


if __name__ == "__main__":
    unittest.main()
