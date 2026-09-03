"""Unit tests for the deterministic benchmark statistics (WB-S1)."""

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

from campaign_benchmark import metrics  # noqa: E402


class PercentileTest(unittest.TestCase):
    def test_percentile_returns_observed_sample(self) -> None:
        samples = [float(value) for value in range(1, 101)]
        self.assertEqual(metrics.percentile(samples, 0.95), 95.0)

    def test_percentile_is_order_independent(self) -> None:
        forward = [1.0, 2.0, 3.0, 4.0, 5.0]
        shuffled = [3.0, 1.0, 5.0, 2.0, 4.0]
        self.assertEqual(metrics.percentile(forward, 0.95), metrics.percentile(shuffled, 0.95))

    def test_percentile_on_single_sample(self) -> None:
        self.assertEqual(metrics.percentile([42.0], 0.95), 42.0)

    def test_percentile_of_one_is_max(self) -> None:
        self.assertEqual(metrics.percentile([5.0, 1.0, 9.0], 1.0), 9.0)

    def test_percentile_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            metrics.percentile([], 0.95)

    def test_percentile_rejects_zero_quantile(self) -> None:
        with self.assertRaises(ValueError):
            metrics.percentile([1.0], 0.0)

    def test_percentile_rejects_quantile_above_one(self) -> None:
        with self.assertRaises(ValueError):
            metrics.percentile([1.0], 1.5)


class MedianTest(unittest.TestCase):
    def test_median_odd_count(self) -> None:
        self.assertEqual(metrics.median([3.0, 1.0, 2.0]), 2.0)

    def test_median_even_count_averages_middle_pair(self) -> None:
        self.assertEqual(metrics.median([1.0, 2.0, 3.0, 4.0]), 2.5)

    def test_median_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            metrics.median([])


class DescribeTest(unittest.TestCase):
    def test_describe_reports_all_required_fields(self) -> None:
        described = metrics.describe([10.0, 20.0, 30.0])
        for key in ("sample_count", "min_ms", "median_ms", "p95_ms", "max_ms"):
            self.assertIn(key, described)
        self.assertEqual(described["sample_count"], 3)
        self.assertEqual(described["min_ms"], 10.0)
        self.assertEqual(described["max_ms"], 30.0)

    def test_median_never_exceeds_p95(self) -> None:
        samples = [5.0, 1.0, 9.0, 3.0, 7.0, 2.0]
        described = metrics.describe(samples)
        self.assertLessEqual(described["median_ms"], described["p95_ms"])
        self.assertLessEqual(described["p95_ms"], described["max_ms"])

    def test_describe_rejects_empty(self) -> None:
        with self.assertRaises(ValueError):
            metrics.describe([])


class BytesPerCampaignHourTest(unittest.TestCase):
    def test_division_is_exact(self) -> None:
        self.assertEqual(metrics.bytes_per_campaign_hour(3600, 1.0), 3600.0)
        self.assertEqual(metrics.bytes_per_campaign_hour(1800, 0.5), 3600.0)

    def test_zero_hours_rejected(self) -> None:
        with self.assertRaises(ValueError):
            metrics.bytes_per_campaign_hour(100, 0.0)

    def test_negative_hours_rejected(self) -> None:
        with self.assertRaises(ValueError):
            metrics.bytes_per_campaign_hour(100, -1.0)


class MeasurementRowTest(unittest.TestCase):
    def test_replay_row_carries_fixed_contract_fields(self) -> None:
        row = metrics.replay_measurement(
            event_count=100, style="noir_chamber", samples=[1.0, 2.0, 3.0], ledger_bytes=500
        )
        self.assertEqual(row["metric_id"], "M-CAMPAIGN-REPLAY-P95-v1")
        self.assertEqual(row["formula_revision"], "p95_wall_clock_replay/v1")
        self.assertEqual(row["unit"], "milliseconds")
        self.assertEqual(row["direction"], "LOWER_IS_BETTER")
        self.assertEqual(row["evidence_class"], "WORKBUDDY_EXECUTOR_VERIFIED")

    def test_storage_row_carries_fixed_contract_fields(self) -> None:
        breakdown = {
            "immutable_package_bytes": 10,
            "ledger_bytes": 20,
            "snapshot_bytes": 30,
            "private_refs_bytes": 40,
            "media_metadata_bytes": 50,
        }
        row = metrics.storage_measurement(
            campaign_count=4, breakdown=breakdown, total_bytes=150, campaign_hours=2.0
        )
        self.assertEqual(row["metric_id"], "M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1")
        self.assertEqual(row["formula_revision"], "ledger_plus_snapshot_plus_metadata_bytes/v1")
        self.assertEqual(row["bytes_per_campaign_hour"], 75.0)
        self.assertEqual(row["evidence_class"], "WORKBUDDY_EXECUTOR_VERIFIED")


if __name__ == "__main__":
    unittest.main()
