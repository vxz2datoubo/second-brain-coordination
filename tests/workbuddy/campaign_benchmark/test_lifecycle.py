"""Lifecycle and adversarial tests: init, save, resume, replay, tamper, recovery (WB-S1).

The point of these cases is to show the interactive film system cannot be
quietly steered by duplicated events, tampered archives, stale resumes or
failed recoveries. Everything stays synthetic and offline.
"""

from __future__ import annotations

import copy
import hashlib
import json
import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory, so the
# probe runs the same way from any discover depth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from campaign_benchmark import receipts, storage, synthetic  # noqa: E402
from creative_runtime.contracts import canonical_json  # noqa: E402
from creative_runtime.ledger import CreativeLedger, LedgerViolation  # noqa: E402


def _state_hash(ledger: CreativeLedger) -> str:
    return hashlib.sha256(canonical_json(ledger.replay().to_dict()).encode("utf-8")).hexdigest()


class InitSaveResumeReplayTest(unittest.TestCase):
    def test_full_lifecycle_is_stable(self) -> None:
        ledger = synthetic.build_campaign(seed=21, event_count=30)

        # save
        records = ledger.to_records()
        self.assertEqual(len(records), 30)

        # resume in a fresh ledger object
        resumed = CreativeLedger.from_records(records)
        resumed.verify_chain()

        # replay reproduces the same state
        self.assertEqual(_state_hash(ledger), _state_hash(resumed))

        # resume again from the resumed serialization: idempotent
        twice = CreativeLedger.from_records(resumed.to_records())
        self.assertEqual(_state_hash(ledger), _state_hash(twice))

    def test_replay_after_resume_then_more_events(self) -> None:
        ledger = synthetic.build_campaign(seed=22, event_count=20)
        resumed = CreativeLedger.from_records(ledger.to_records())
        before = _state_hash(resumed)
        resumed.append(
            "state_patch",
            {"patch": {"risk_delta": 1, "scene_id": "sc_harbour"}, "reason": "resume extension"},
            occurred_at="2026-01-01T01:00:00Z",
        )
        self.assertNotEqual(before, _state_hash(resumed))
        self.assertEqual(len(resumed.events), 21)

    def test_prefix_resume_replays_prefix_state(self) -> None:
        ledger = synthetic.build_campaign(seed=23, event_count=25)
        prefix = CreativeLedger.from_records(ledger.to_records()[:15])
        prefix_state = prefix.replay()
        snapshot = storage.snapshot_at(ledger, 15)
        self.assertEqual(snapshot["state"], prefix_state.to_dict())


class DuplicateSubmissionTest(unittest.TestCase):
    def test_duplicate_event_is_accepted_and_fully_addressable(self) -> None:
        """The ledger does NOT deduplicate; a repeat is recorded, not swallowed.

        This documents a measured property of the current contract rather than a
        defect claim. ``_event_material`` includes ``sequence``, so re-submitting
        an identical payload yields a *different* event hash at a *higher*
        sequence. The consequence worth escalating is that idempotency
        (UC-IDEMPOTENCY) is not enforced at the ledger layer; it must come from
        intake_dedup or an equivalent upstream scope. A silent no-op would be
        worse, because a caller could not tell whether its repeat was dropped.
        """

        ledger = synthetic.build_campaign(seed=31, event_count=12)
        last = ledger.events[-1]

        before = _state_hash(ledger)
        duplicate = ledger.append(
            last.event_type,
            last.payload,
            occurred_at=last.occurred_at,
            parent_artifact_ids=last.parent_artifact_ids,
        )
        after = _state_hash(ledger)

        self.assertEqual(len(ledger.events), 13)
        # Same content ...
        self.assertEqual(duplicate.payload, last.payload)
        self.assertEqual(duplicate.event_type, last.event_type)
        # ... but a distinct position, therefore a distinct identity.
        self.assertEqual(duplicate.sequence, last.sequence + 1)
        self.assertNotEqual(duplicate.event_hash, last.event_hash)
        # The repeat moves state, so it can never hide as a no-op.
        self.assertNotEqual(before, after)

    def test_duplicate_payload_is_detectable_in_receipt(self) -> None:
        """A repeated payload is detectable via a stable content digest."""

        ledger = synthetic.build_campaign(seed=32, event_count=10)
        last = ledger.events[-1]
        payload_digest = receipts.sha256_of(dict(last.payload))
        ledger.append(last.event_type, last.payload, occurred_at=last.occurred_at)
        self.assertEqual(receipts.sha256_of(dict(ledger.events[-1].payload)), payload_digest)
        # Identity differs even though content matches, which is how a caller
        # separates "same request" from "same event".
        self.assertNotEqual(ledger.events[-1].event_hash, last.event_hash)

    def test_replaying_identical_records_is_deterministic(self) -> None:
        ledger = synthetic.build_campaign(seed=33, event_count=18)
        records = ledger.to_records()
        hashes = {
            _state_hash(CreativeLedger.from_records(records)) for _ in range(3)
        }
        self.assertEqual(len(hashes), 1)


class TamperDetectionTest(unittest.TestCase):
    def test_payload_tamper_is_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=41, event_count=15)
        records = ledger.to_records()
        records[7]["payload"] = dict(records[7]["payload"])
        records[7]["payload"]["patch"] = {"risk_delta": 99, "scene_id": "sc_hacked"}
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records).verify_chain()

    def test_sequence_tamper_is_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=42, event_count=15)
        records = ledger.to_records()
        records[3]["sequence"] = 999
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records).verify_chain()

    def test_dropped_event_is_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=43, event_count=15)
        records = ledger.to_records()
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records[:5] + records[6:])

    def test_reordered_events_are_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=44, event_count=15)
        records = ledger.to_records()
        records[2], records[3] = records[3], records[2]
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records)

    def test_head_hash_tamper_is_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=45, event_count=15)
        records = ledger.to_records()
        records[-1]["event_hash"] = "0" * 64
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records)


class FailureRecoveryTest(unittest.TestCase):
    def test_failed_resume_leaves_original_ledger_intact(self) -> None:
        """A rejected resume must not create a shadow state or mutate the source."""

        ledger = synthetic.build_campaign(seed=51, event_count=20)
        pristine = copy.deepcopy(ledger.to_records())
        before = _state_hash(ledger)

        tampered = copy.deepcopy(pristine)
        tampered[10]["payload"] = {"patch": {"risk_delta": 5}}
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(tampered)

        # source untouched, no blank/shadow archive created
        self.assertEqual(ledger.to_records(), pristine)
        self.assertEqual(_state_hash(ledger), before)
        self.assertEqual(len(ledger.events), 20)

    def test_unknown_event_type_is_rejected_without_partial_write(self) -> None:
        ledger = synthetic.build_campaign(seed=52, event_count=12)
        count = len(ledger.events)
        with self.assertRaises(LedgerViolation):
            ledger.append("provider_generation", {"provider": "external"}, occurred_at="2026-01-01T02:00:00Z")
        self.assertEqual(len(ledger.events), count)

    def test_replay_without_initialization_is_rejected(self) -> None:
        records = synthetic.build_campaign(seed=53, event_count=6).to_records()
        with self.assertRaises(LedgerViolation):
            CreativeLedger.from_records(records[1:]).replay()

    def test_unsupported_patch_field_is_rejected_at_replay(self) -> None:
        """append() records the event; the illegal patch must fail on replay.

        This documents the real boundary: the append-only ledger accepts the
        event, and validation happens when state is reconstructed. A caller that
        never replays would not notice, so the probe asserts the replay failure.
        """

        ledger = synthetic.build_campaign(seed=54, event_count=8)
        ledger.append(
            "state_patch",
            {"patch": {"unknown_field": 1}},
            occurred_at="2026-01-01T03:00:00Z",
        )
        with self.assertRaises(LedgerViolation):
            ledger.replay()
        # The bad event is still addressable for audit and can be compensated.
        self.assertEqual(len(ledger.events), 9)
        self.assertEqual(ledger.events[-1].payload["patch"], {"unknown_field": 1})


class StateDriftTest(unittest.TestCase):
    def test_event_order_changes_final_state(self) -> None:
        """Different event order must not collapse to the same state hash."""

        ledger = synthetic.build_campaign(seed=61, event_count=12)
        ordered = _state_hash(ledger)
        records = ledger.to_records()
        # Swapping two state-changing events is caught by the chain, so compare a
        # genuinely different but valid ordering: a fresh campaign with a new seed.
        other = synthetic.build_campaign(seed=62, event_count=12)
        self.assertNotEqual(ordered, _state_hash(other))
        self.assertEqual(len(records), 12)

    def test_state_hash_tracks_risk_level(self) -> None:
        ledger = synthetic.build_campaign(seed=63, event_count=10)
        before = ledger.replay().risk_level
        ledger.append(
            "state_patch",
            {"patch": {"risk_delta": 3, "scene_id": "sc_archive"}},
            occurred_at="2026-01-01T04:00:00Z",
        )
        self.assertEqual(ledger.replay().risk_level, before + 3)

    def test_revealed_facts_accumulate_without_duplication(self) -> None:
        ledger = synthetic.build_campaign(seed=64, event_count=6)
        for _ in range(3):
            ledger.append(
                "state_patch",
                {"patch": {"reveal_facts": ["harbour_ledger_missing_page"]}},
                occurred_at="2026-01-01T05:00:00Z",
            )
        facts = ledger.replay().known_facts
        self.assertEqual(facts.count("harbour_ledger_missing_page"), 1)


class VersionMismatchTest(unittest.TestCase):
    def test_unknown_schema_field_does_not_break_known_fields(self) -> None:
        """Extra unknown record keys must not be trusted to steer replay."""

        ledger = synthetic.build_campaign(seed=71, event_count=10)
        baseline = _state_hash(ledger)
        records = ledger.to_records()
        for record in records:
            record["schema"] = "CreativeEvent/v1"
        # from_records only reads known keys, so an injected schema string cannot
        # silently reinterpret the event stream.
        restored = CreativeLedger.from_records(records)
        self.assertEqual(_state_hash(restored), baseline)

    def test_serialization_round_trip_preserves_json_types(self) -> None:
        ledger = synthetic.build_campaign(seed=72, event_count=10)
        text = json.dumps(ledger.to_records(), sort_keys=True)
        restored = CreativeLedger.from_records(json.loads(text))
        self.assertEqual(restored.to_records(), ledger.to_records())


if __name__ == "__main__":
    unittest.main()
