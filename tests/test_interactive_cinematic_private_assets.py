from __future__ import annotations

import unittest
import tempfile
from dataclasses import replace
from pathlib import Path

from apps.cli import creativectl
from creative_runtime.cinematic_media import CinematicMediaViolation, OfflineMediaQueue, build_cinematic_segment
from creative_runtime.director_context import compile_verified_director_v2
from creative_runtime.private_assets import PrivateAssetViolation, continuity_record, create_appearance_change, create_avatar_identity


class PrivateAssetTests(unittest.TestCase):
    def test_identity_and_explicit_future_appearance_revision_are_reference_only(self) -> None:
        identity = create_avatar_identity("private://owners/player_0001", "consent-v1", "private://media/avatar_0001")
        revision = create_appearance_change(identity, "整容", "player", "private://media/avatar_0002", "private://approvals/a_0001", "evt_0123456789abcdef0123")
        self.assertEqual(identity.avatar_id, revision.avatar_id)
        self.assertEqual("appearance_change:player", revision.replacement_reason)
        record = continuity_record("segment_001", "camp_0123456789abcdef0123", (revision.avatar_revision_id,), "a" * 64)
        self.assertEqual("references_verified_no_media_read", record.validation_status)

    def test_paths_implicit_changes_and_bad_event_fail_closed(self) -> None:
        with self.assertRaises(PrivateAssetViolation):
            create_avatar_identity("C:/user", "consent", "private://media/avatar_0001")
        identity = create_avatar_identity("private://owners/player_0001", "consent", "private://media/avatar_0001")
        with self.assertRaises(PrivateAssetViolation):
            create_appearance_change(identity, "change", "player", "private://media/avatar_0002", "private://approvals/a_0001", "evt_0123456789abcdef0123")
        with self.assertRaises(PrivateAssetViolation):
            create_appearance_change(identity, "整容", "", "private://media/avatar_0002", "private://approvals/a_0001", "bad")

    def test_director_bound_segment_queue_is_campaign_scoped_idempotent_and_offline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            creativectl.run(["--workspace", str(workspace), "choose", "listen"])
            ledger = creativectl._load_session(workspace)
            compiled = compile_verified_director_v2(
                ledger,
                script_id="synthetic-night-signal",
                script_revision="SyntheticNightSignal/v1",
                style_profile_id="cinematic_live_action",
            )
            continuity = continuity_record(
                "segment_001", compiled.brief_v2.campaign_id, compiled.brief_v2.cast_revision_ids,
                compiled.brief_v2.continuity_ledger_hash,
            )
            segment = build_cinematic_segment(compiled, continuity)
            self.assertEqual("CinematicSegment/v1", segment.schema)
            self.assertGreaterEqual(segment.duration_seconds, 4)
            self.assertLessEqual(segment.duration_seconds, 15)
            queue = OfflineMediaQueue()
            job, report, created = queue.enqueue(segment)
            duplicate, duplicate_report, created_again = queue.enqueue(segment)
            self.assertTrue(created)
            self.assertFalse(created_again)
            self.assertEqual(job, duplicate)
            self.assertEqual(job.job_id, duplicate_report.job_id)
            result = queue.execute(job, report, occurred_at="2026-08-31T00:00:00Z")
            self.assertEqual("simulated", result.status)
            self.assertTrue(result.result_ref.startswith("offline://"))
            self.assertEqual(result, queue.execute(job, report, occurred_at="different-safe-time"))

    def test_media_segment_rejects_campaign_mismatch_duration_and_failed_quality(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            creativectl.run(["--workspace", str(workspace), "init", "--scenario", "night_signal"])
            ledger = creativectl._load_session(workspace)
            compiled = compile_verified_director_v2(
                ledger,
                script_id="synthetic-night-signal",
                script_revision="SyntheticNightSignal/v1",
                style_profile_id="ink_wash_animation",
            )
            valid = continuity_record("segment_001", compiled.brief_v2.campaign_id, compiled.brief_v2.cast_revision_ids, compiled.brief_v2.continuity_ledger_hash)
            with self.assertRaisesRegex(CinematicMediaViolation, "another campaign"):
                build_cinematic_segment(compiled, replace(valid, campaign_id="camp_0123456789abcdef0123"))
            segment = build_cinematic_segment(compiled, valid)
            queue = OfflineMediaQueue()
            with self.assertRaisesRegex(CinematicMediaViolation, "4--15"):
                queue.enqueue(replace(segment, duration_seconds=16))
            job, report, _ = queue.enqueue(segment)
            with self.assertRaisesRegex(CinematicMediaViolation, "does not permit"):
                queue.execute(job, replace(report, verdict="blocked"), occurred_at="2026-08-31T00:00:00Z")
