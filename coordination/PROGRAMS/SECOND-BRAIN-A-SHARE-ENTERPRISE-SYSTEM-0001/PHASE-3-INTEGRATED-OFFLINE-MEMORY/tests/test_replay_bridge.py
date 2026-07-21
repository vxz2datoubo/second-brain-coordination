from __future__ import annotations

import dataclasses
import hashlib
import sys
import unittest
from datetime import date
from pathlib import Path


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
    PROGRAM_ROOT / "PHASE-2-OFFLINE-VERTICAL-SLICE" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.contracts import SourceActivationPolicy
from integrated_offline_memory.fixtures import SyntheticDayRecord, encode_records
from integrated_offline_memory.replay_bridge import CloseAvailabilityPolicy, run_p2_replay, to_p2_bars
from integrated_offline_memory.tdx_day import TdxDayParser
from local_adapter.contracts import AdapterCapability, LocalArtifactReference, SourceManifest
from offline_research.engine import Bar, DeterministicReplay, SimulationConfig


SHA = "1" * 64


def source_manifest() -> SourceManifest:
    return SourceManifest(
        manifest_id="manifest-replay-test",
        source_id="tdx-day-test",
        source_class="historical_verified",
        artifact=LocalArtifactReference("artifact-replay-test", "local-only", SHA, "PRIVATE_LOCAL_ONLY", "UNKNOWN"),
        license="UNKNOWN",
        privacy_class="PRIVATE_LOCAL_ONLY",
        timezone="Asia/Shanghai",
        time_semantics="END_OF_BAR",
        available_at="2026-01-01T07:00:01Z",
        adjusted=False,
        adjustment_method="none",
        suspension_policy="unknown",
        st_policy="unknown",
        limit_rule_version="ashare-v1",
        corporate_action_policy="unknown",
        capability=AdapterCapability("day", "HISTORICAL_BAR", "confirmed", "DAILY_AGGREGATE_BAR"),
        synthetic=False,
        field_semantics_version="tdx-day-partial-v1",
    )


def parsed_records(count: int = 8):
    records = []
    for index in range(count):
        records.append(SyntheticDayRecord(
            date_raw=20260105 + index,
            open_raw=1000 + index * 10,
            high_raw=1120 + index * 10,
            low_raw=900 + index * 10,
            close_raw=1050 + index * 10,
            volume_raw=10000 + index * 100,
        ))
    payload = encode_records(*records)
    return TdxDayParser().parse_bytes(
        payload,
        manifest_id="manifest-replay-test",
        policy_id="policy-replay-test",
        artifact_sha256=hashlib.sha256(payload).hexdigest(),
        requested_as_of_date=date(2026, 12, 31),
    )


class ReplayBridgeTestCase(unittest.TestCase):
    def test_101_maps_to_existing_p2_bar(self):
        bars = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertIsInstance(bars[0], Bar)

    def test_102_event_time_is_ashare_close(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertEqual(bar.event_time, "2026-01-05T07:00:00Z")

    def test_103_available_at_uses_versioned_delay(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertEqual(bar.available_at, "2026-01-05T07:00:01Z")

    def test_104_policy_version_is_explicit(self):
        self.assertEqual(CloseAvailabilityPolicy().version, "ashare-daily-close-plus-1s-v1")

    def test_105_event_id_is_deterministic(self):
        args = (parsed_records(1), source_manifest())
        first = to_p2_bars(*args, symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        second = to_p2_bars(*args, symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertEqual(first.event_id, second.event_id)

    def test_106_amount_does_not_enter_bar(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertFalse(hasattr(bar, "amount"))

    def test_107_reserved_does_not_enter_bar(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertFalse(hasattr(bar, "reserved"))

    def test_108_volume_value_is_preserved_without_unit_claim(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertEqual(bar.volume, 10000.0)

    def test_109_manifest_source_is_lineage(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertEqual(bar.source_id, "tdx-day-test")

    def test_110_mtime_is_not_part_of_bar(self):
        bar = to_p2_bars(parsed_records(1), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")[0]
        self.assertFalse(hasattr(bar, "mtime"))

    def test_111_replay_core_hash_is_deterministic(self):
        parsed = parsed_records()
        first = run_p2_replay(parsed, source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        second = run_p2_replay(parsed, source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertEqual(first.replay_core_hash, second.replay_core_hash)

    def test_112_run_id_is_deterministic(self):
        parsed = parsed_records()
        first = run_p2_replay(parsed, source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        second = run_p2_replay(parsed, source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertEqual(first.run_id, second.run_id)

    def test_113_source_status_is_only_partial(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertEqual(receipt.source_validation_status, "PARTIALLY_VERIFIED")

    def test_114_strategy_status_is_not_production(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertIn(receipt.strategy_validation_status, {"EXPERIMENTAL_ONLY", "ABSTAIN"})

    def test_115_receipt_is_no_trade(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertTrue(receipt.no_trade_gate)

    def test_116_receipt_never_authority_writes(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertFalse(receipt.authority_write)

    def test_117_receipt_has_no_raw_records(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertNotIn("records", receipt.public_payload())

    def test_118_cost_model_is_retained(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertIn("cost_proxy", receipt.validation_report)

    def test_119_unknown_field_semantics_are_explicit(self):
        receipt = run_p2_replay(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        self.assertIn("volume_unit_unknown", receipt.unknowns)

    def test_120_p2_replay_sorts_out_of_order_bars(self):
        bars = to_p2_bars(parsed_records(), source_manifest(), symbol="300418", exchange="SZ", requested_as_of="2026-12-31T00:00:00Z")
        result = DeterministicReplay("2026-12-31T00:00:00Z", "run-test", "trace-test").run(reversed(bars))
        self.assertEqual(result.events, bars)

    def test_121_config_remains_no_trade(self):
        self.assertTrue(SimulationConfig().no_trade_gate)


if __name__ == "__main__":
    unittest.main()
