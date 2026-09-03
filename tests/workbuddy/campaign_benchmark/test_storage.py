"""Storage-accounting tests, including fail-closed private-reference guards (WB-S1)."""

from __future__ import annotations

import unittest

import sys
from pathlib import Path

# Resolve imports without relying on discover's top-level directory, so the
# probe runs the same way from any discover depth.
_REPO_ROOT = Path(__file__).resolve().parents[3]
for _candidate in (str(_REPO_ROOT), str(_REPO_ROOT / "tools" / "workbuddy")):
    if _candidate not in sys.path:
        sys.path.insert(0, _candidate)

from campaign_benchmark import storage, synthetic  # noqa: E402
from creative_runtime.ledger import CreativeLedger  # noqa: E402


class BucketTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ledger = synthetic.build_campaign(seed=1, event_count=40, style="noir_chamber")
        self.breakdown = storage.account_campaign(self.ledger, seed=1, style="noir_chamber")

    def test_all_five_buckets_present(self) -> None:
        self.assertEqual(set(self.breakdown), set(storage.BUCKETS))

    def test_every_bucket_is_non_negative_int(self) -> None:
        for bucket in storage.BUCKETS:
            self.assertIsInstance(self.breakdown[bucket], int)
            self.assertGreaterEqual(self.breakdown[bucket], 0)

    def test_ledger_bucket_dominates_small_campaign(self) -> None:
        # The ledger is the append-only event record; at this size it must be the
        # largest single bucket, which is the fact a retention policy needs.
        self.assertGreater(
            self.breakdown["ledger_bytes"], self.breakdown["immutable_package_bytes"]
        )

    def test_accounting_is_deterministic(self) -> None:
        again = storage.account_campaign(
            synthetic.build_campaign(seed=1, event_count=40, style="noir_chamber"),
            seed=1,
            style="noir_chamber",
        )
        self.assertEqual(self.breakdown, again)

    def test_total_equals_bucket_sum(self) -> None:
        self.assertEqual(
            storage.total_bytes(self.breakdown),
            sum(self.breakdown[bucket] for bucket in storage.BUCKETS),
        )

    def test_storage_grows_with_event_count(self) -> None:
        small = storage.total_bytes(
            storage.account_campaign(
                synthetic.build_campaign(seed=1, event_count=20, style="noir_chamber"),
                seed=1,
                style="noir_chamber",
            )
        )
        large = storage.total_bytes(
            storage.account_campaign(
                synthetic.build_campaign(seed=1, event_count=80, style="noir_chamber"),
                seed=1,
                style="noir_chamber",
            )
        )
        self.assertGreater(large, small)


class TotalAndAggregateTest(unittest.TestCase):
    def test_total_rejects_unknown_bucket(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.total_bytes({"mystery_bytes": 10})

    def test_total_rejects_missing_bucket(self) -> None:
        partial = {bucket: 1 for bucket in storage.BUCKETS[:3]}
        with self.assertRaises(storage.StorageAccountingError):
            storage.total_bytes(partial)

    def test_aggregate_sums_bucket_wise(self) -> None:
        one = {bucket: 1 for bucket in storage.BUCKETS}
        two = {bucket: 2 for bucket in storage.BUCKETS}
        self.assertEqual(storage.aggregate([one, two]), {bucket: 3 for bucket in storage.BUCKETS})

    def test_aggregate_rejects_empty(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.aggregate([])


class PrivateReferenceGuardTest(unittest.TestCase):
    """A private reference must stay synthetic; real assets never enter GitHub."""

    def test_synthetic_ref_accepted(self) -> None:
        self.assertEqual(
            storage.guard_private_ref("synth://private/1/10/ref-0001"),
            "synth://private/1/10/ref-0001",
        )

    def test_windows_drive_path_rejected(self) -> None:
        for ref in ("C:\\Users\\someone\\clip.mp4", "D:/media/clip.mp4"):
            with self.assertRaises(storage.StorageAccountingError):
                storage.guard_private_ref(ref)

    def test_unc_path_rejected(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.guard_private_ref("\\\\nas\\share\\clip.mp4")

    def test_url_locators_rejected(self) -> None:
        for ref in ("file:///C:/clip.mp4", "https://cdn.example/clip.mp4", "http://x/y"):
            with self.assertRaises(storage.StorageAccountingError):
                storage.guard_private_ref(ref)

    def test_home_directory_paths_rejected(self) -> None:
        for ref in ("/home/someone/clip.mp4", "/Users/someone/clip.mp4"):
            with self.assertRaises(storage.StorageAccountingError):
                storage.guard_private_ref(ref)

    def test_traversal_paths_rejected(self) -> None:
        for ref in ("../escape.mp4", ".\\escape.mp4"):
            with self.assertRaises(storage.StorageAccountingError):
                storage.guard_private_ref(ref)

    def test_empty_ref_rejected(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.guard_private_ref("")

    def test_non_string_ref_rejected(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.guard_private_ref(123)  # type: ignore[arg-type]

    def test_generated_private_refs_all_pass_guard(self) -> None:
        for ref in storage.private_refs(seed=1, event_count=50):
            storage.guard_private_ref(ref)


class SnapshotTest(unittest.TestCase):
    def test_snapshot_matches_prefix_replay(self) -> None:
        ledger = synthetic.build_campaign(seed=2, event_count=40)
        snapshot = storage.snapshot_at(ledger, 20)
        prefix = CreativeLedger.from_records(ledger.to_records()[:20])
        self.assertEqual(snapshot["state"], prefix.replay().to_dict())
        self.assertEqual(snapshot["head_event_hash"], prefix.events[-1].event_hash)

    def test_snapshot_index_out_of_range_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=2, event_count=10)
        with self.assertRaises(storage.StorageAccountingError):
            storage.snapshot_at(ledger, 11)
        with self.assertRaises(storage.StorageAccountingError):
            storage.snapshot_at(ledger, -1)

    def test_empty_prefix_rejected(self) -> None:
        ledger = synthetic.build_campaign(seed=2, event_count=10)
        with self.assertRaises(storage.StorageAccountingError):
            storage.snapshot_at(ledger, 0)


class MediaMetadataTest(unittest.TestCase):
    def test_metadata_never_claims_generation(self) -> None:
        for item in storage.media_metadata(seed=1, event_count=40):
            self.assertFalse(item["generated"])
            self.assertEqual(item["provider"], "none_offline_simulation")

    def test_metadata_is_deterministic(self) -> None:
        self.assertEqual(
            storage.media_metadata(seed=3, event_count=30),
            storage.media_metadata(seed=3, event_count=30),
        )


class ImmutablePackageTest(unittest.TestCase):
    def test_known_style_accepted(self) -> None:
        for style in synthetic.STYLES:
            self.assertEqual(storage.immutable_package(style)["style"], style)

    def test_unknown_style_rejected(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.immutable_package("licensed_footage")

    def test_accounting_rejects_unknown_style(self) -> None:
        ledger = synthetic.build_campaign(seed=1, event_count=10)
        with self.assertRaises(storage.StorageAccountingError):
            storage.account_campaign(ledger, seed=1, style="licensed_footage")

    def test_accounting_rejects_empty_campaign(self) -> None:
        with self.assertRaises(storage.StorageAccountingError):
            storage.account_campaign(CreativeLedger(), seed=1, style="noir_chamber")


if __name__ == "__main__":
    unittest.main()
