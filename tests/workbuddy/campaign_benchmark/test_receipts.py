"""Receipt, environment-declaration and end-to-end probe tests (WB-S1)."""

from __future__ import annotations

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


class Sha256ReceiptTest(unittest.TestCase):
    def test_digest_is_stable(self) -> None:
        payload = {"b": 2, "a": 1}
        self.assertEqual(receipts.sha256_of(payload), receipts.sha256_of(payload))

    def test_digest_ignores_key_order(self) -> None:
        self.assertEqual(receipts.sha256_of({"a": 1, "b": 2}), receipts.sha256_of({"b": 2, "a": 1}))

    def test_digest_changes_with_content(self) -> None:
        self.assertNotEqual(receipts.sha256_of({"a": 1}), receipts.sha256_of({"a": 2}))

    def test_digest_is_64_hex(self) -> None:
        digest = receipts.sha256_of({"a": 1})
        self.assertEqual(len(digest), 64)
        int(digest, 16)


class EnvironmentTest(unittest.TestCase):
    def test_environment_declares_runtime(self) -> None:
        env = receipts.environment()
        for key in ("python_version", "platform", "machine", "schema"):
            self.assertIn(key, env)
        self.assertEqual(env["schema"], "WorkBuddyCampaignBenchmarkProbe/v1")


class VariationTest(unittest.TestCase):
    def test_identical_samples_have_zero_variation(self) -> None:
        self.assertEqual(receipts.variation([5.0, 5.0, 5.0]), 0.0)

    def test_single_sample_has_zero_variation(self) -> None:
        self.assertEqual(receipts.variation([5.0]), 0.0)

    def test_varied_samples_report_positive_variation(self) -> None:
        self.assertGreater(receipts.variation([1.0, 10.0, 100.0]), 0.0)


class ReplayProbeTest(unittest.TestCase):
    """End-to-end probe on a deliberately small stratum set to keep tests fast."""

    def test_probe_returns_one_row_per_stratum(self) -> None:
        report = receipts.run_replay_probe(strata=(10, 40), rounds=3, warmup=1)
        self.assertEqual([row["event_count"] for row in report["rows"]], [10, 40])

    def test_probe_rows_carry_required_measurements(self) -> None:
        report = receipts.run_replay_probe(strata=(10, 40), rounds=3, warmup=1)
        for row in report["rows"]:
            for key in ("sample_count", "median_ms", "p95_ms", "ledger_bytes", "coefficient_of_variation"):
                self.assertIn(key, row)
            self.assertEqual(row["sample_count"], 3)
            self.assertGreater(row["p95_ms"], 0.0)
            self.assertGreater(row["ledger_bytes"], 0)

    def test_probe_declares_measurement_method(self) -> None:
        report = receipts.run_replay_probe(strata=(10,), rounds=2, warmup=1)
        self.assertEqual(report["method"]["sampling"], "interleaved_round_robin")
        self.assertEqual(report["method"]["warmup_runs"], 1)
        self.assertEqual(report["method"]["rounds"], 2)

    def test_probe_receipt_is_stable_across_rows(self) -> None:
        report = receipts.run_replay_probe(strata=(10,), rounds=2, warmup=1)
        self.assertEqual(len(report["receipt_sha256"]), 64)

    def test_latency_grows_with_event_count(self) -> None:
        report = receipts.run_replay_probe(strata=(10, 200), rounds=3, warmup=1)
        small, large = report["rows"]
        self.assertGreater(large["median_ms"], small["median_ms"])

    def test_measure_replay_latency_honours_sample_count(self) -> None:
        ledger = synthetic.build_campaign(seed=1, event_count=20)
        self.assertEqual(len(receipts.measure_replay_latency(ledger, samples=4, warmup=1)), 4)

    def test_measure_replay_latency_rejects_bad_counts(self) -> None:
        ledger = synthetic.build_campaign(seed=1, event_count=10)
        with self.assertRaises(ValueError):
            receipts.measure_replay_latency(ledger, samples=0)
        with self.assertRaises(ValueError):
            receipts.measure_replay_latency(ledger, samples=2, warmup=-1)

    def test_probe_rejects_zero_rounds(self) -> None:
        with self.assertRaises(ValueError):
            receipts.run_replay_probe(strata=(10,), rounds=0)


class StorageProbeTest(unittest.TestCase):
    def test_probe_returns_one_row_per_corpus(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(1, 3), event_count=20)
        self.assertEqual([row["campaign_count"] for row in report["rows"]], [1, 3])

    def test_rows_inside_real_limit_are_not_extrapolated(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(1, 5), event_count=20)
        for row in report["rows"]:
            self.assertFalse(row["extrapolated"])

    def test_rows_above_real_limit_are_flagged_extrapolated(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(50,), event_count=20)
        self.assertTrue(report["rows"][0]["extrapolated"])

    def test_total_bytes_grow_with_corpus_size(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(1, 4), event_count=20)
        small, large = report["rows"]
        self.assertGreater(large["total_bytes"], small["total_bytes"])

    def test_breakdown_has_all_five_buckets(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(1,), event_count=20)
        self.assertEqual(set(report["rows"][0]["breakdown"]), set(storage.BUCKETS))

    def test_per_campaign_hour_is_finite_and_positive(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(2,), event_count=20)
        value = report["rows"][0]["bytes_per_campaign_hour"]
        self.assertGreater(value, 0.0)
        self.assertEqual(value, value)  # not NaN


class RenderTest(unittest.TestCase):
    def test_render_produces_parseable_json(self) -> None:
        report = receipts.run_storage_probe(corpora_sizes=(1,), event_count=10)
        parsed = json.loads(receipts.render(report))
        self.assertEqual(parsed["metric_id"], "M-STORAGE-BYTES-PER-CAMPAIGN-HOUR-v1")

    def test_render_replay_report_is_parseable(self) -> None:
        report = receipts.run_replay_probe(strata=(10,), rounds=2, warmup=1)
        parsed = json.loads(receipts.render(report))
        self.assertEqual(parsed["metric_id"], "M-CAMPAIGN-REPLAY-P95-v1")


if __name__ == "__main__":
    unittest.main()
