from __future__ import annotations

import dataclasses
import hashlib
import io
import json
import math
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import yaml


PHASE_ROOT = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = PHASE_ROOT.parent
for source_root in (
    PHASE_ROOT / "src",
    PROGRAM_ROOT / "PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION" / "src",
):
    sys.path.insert(0, str(source_root))

from integrated_offline_memory.cli import main as cli_main
from integrated_offline_memory.contracts import (
    SourceActivationPolicy,
    deserialize_phase_contract,
    field_semantic_decisions,
    serialize_phase_contract,
)
from integrated_offline_memory.fixtures import SyntheticDayRecord, encode_records
from integrated_offline_memory.schema_validation import SchemaValidationError, validate_schema_subset
from integrated_offline_memory.tdx_day import TdxDayParser, TdxDaySourceAdapter
from local_adapter.contracts import (
    AdapterCapability,
    AdapterStatus,
    ContractError,
    LocalArtifactReference,
    SourceManifest,
    serialize_contract,
)


def policy(sha256: str, **changes) -> SourceActivationPolicy:
    values = {
        "policy_id": "activation-local-test",
        "manifest_id": "manifest-local-test",
        "artifact_sha256": sha256,
    }
    values.update(changes)
    return SourceActivationPolicy(**values)


def manifest(sha256: str, **changes) -> SourceManifest:
    values = {
        "manifest_id": "manifest-local-test",
        "source_id": "tdx-local-test",
        "source_class": "historical_verified",
        "artifact": LocalArtifactReference(
            reference_id="artifact-local-test",
            local_location_hint="local-only/day-file",
            sha256=sha256,
            content_class="PRIVATE_LOCAL_ONLY",
            license_status="UNKNOWN",
        ),
        "license": "UNKNOWN",
        "privacy_class": "PRIVATE_LOCAL_ONLY",
        "timezone": "Asia/Shanghai",
        "time_semantics": "END_OF_BAR",
        "available_at": "2026-01-05T07:00:01Z",
        "adjusted": False,
        "adjustment_method": "none",
        "suspension_policy": "preserve_explicit_or_unknown",
        "st_policy": "versioned_rule_required",
        "limit_rule_version": "ashare-v1",
        "corporate_action_policy": "unadjusted_vendor_values",
        "capability": AdapterCapability(
            capability_id="tdx-day-historical",
            capability_level="HISTORICAL_BAR",
            entitlement_status="confirmed",
            provider_semantics="DAILY_AGGREGATE_BAR",
        ),
        "synthetic": False,
        "field_semantics_version": "tdx-day-partial-v1",
    }
    values.update(changes)
    return SourceManifest(**values)


class ParserTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = TdxDayParser()
        self.record = SyntheticDayRecord()
        self.payload = self.record.encode()
        self.sha = hashlib.sha256(self.payload).hexdigest()

    def parse(self, payload: bytes | None = None, as_of: date = date(2026, 12, 31)):
        content = self.payload if payload is None else payload
        return self.parser.parse_bytes(
            content,
            manifest_id="manifest-local-test",
            policy_id="activation-local-test",
            artifact_sha256=hashlib.sha256(content).hexdigest(),
            requested_as_of_date=as_of,
        )

    def test_001_record_is_32_bytes(self):
        self.assertEqual(len(self.payload), 32)

    def test_002_empty_payload_is_valid_empty_partial_report(self):
        result = self.parse(b"")
        self.assertEqual(result.report.status, "PARTIALLY_VERIFIED")
        self.assertEqual(result.report.source_record_count, 0)

    def test_003_truncated_record_rejected(self):
        result = self.parse(self.payload[:-1])
        self.assertEqual(result.report.status, "REJECTED")

    def test_004_truncated_record_has_issue(self):
        result = self.parse(self.payload[:-7])
        self.assertEqual(result.report.issues[0].code, "TRUNCATED_RECORD")

    def test_005_single_record_accepted(self):
        self.assertEqual(self.parse().report.accepted_record_count, 1)

    def test_006_multiple_records_accepted(self):
        payload = encode_records(self.record, dataclasses.replace(self.record, date_raw=20260106))
        self.assertEqual(self.parse(payload).report.accepted_record_count, 2)

    def test_007_date_decodes(self):
        self.assertEqual(self.parse().records[0].trade_date, "2026-01-05")

    def test_008_invalid_short_date_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, date_raw=202601).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_DATE")

    def test_009_invalid_month_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, date_raw=20261301).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_DATE")

    def test_010_invalid_day_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, date_raw=20260230).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_DATE")

    def test_011_valid_leap_day_accepted(self):
        result = self.parse(dataclasses.replace(self.record, date_raw=20240229).encode())
        self.assertEqual(result.report.accepted_record_count, 1)

    def test_012_invalid_nonleap_day_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, date_raw=20250229).encode())
        self.assertEqual(result.report.accepted_record_count, 0)

    def test_013_future_date_quarantined(self):
        result = self.parse(as_of=date(2026, 1, 4))
        self.assertEqual(result.report.issues[0].code, "FUTURE_DATE")

    def test_014_price_divisor_is_100(self):
        record = self.parse().records[0]
        self.assertEqual((record.open, record.high, record.low, record.close), (10.0, 11.0, 9.0, 10.5))

    def test_015_zero_open_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, open_raw=0).encode())
        self.assertEqual(result.report.issues[0].code, "NON_POSITIVE_PRICE")

    def test_016_zero_high_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, high_raw=0).encode())
        self.assertEqual(result.report.issues[0].code, "NON_POSITIVE_PRICE")

    def test_017_zero_low_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, low_raw=0).encode())
        self.assertEqual(result.report.issues[0].code, "NON_POSITIVE_PRICE")

    def test_018_zero_close_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, close_raw=0).encode())
        self.assertEqual(result.report.issues[0].code, "NON_POSITIVE_PRICE")

    def test_019_open_above_high_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, open_raw=1200).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_OHLC")

    def test_020_close_above_high_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, close_raw=1200).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_OHLC")

    def test_021_open_below_low_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, open_raw=800).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_OHLC")

    def test_022_close_below_low_quarantined(self):
        result = self.parse(dataclasses.replace(self.record, close_raw=800).encode())
        self.assertEqual(result.report.issues[0].code, "INVALID_OHLC")

    def test_023_equal_ohlc_is_accepted(self):
        equal = SyntheticDayRecord(open_raw=1000, high_raw=1000, low_raw=1000, close_raw=1000)
        self.assertEqual(self.parse(equal.encode()).report.accepted_record_count, 1)

    def test_024_duplicate_date_quarantined(self):
        result = self.parse(encode_records(self.record, self.record))
        self.assertEqual(result.report.duplicate_date_count, 1)

    def test_025_duplicate_date_not_accepted_twice(self):
        result = self.parse(encode_records(self.record, self.record))
        self.assertEqual(result.report.accepted_record_count, 1)

    def test_026_out_of_order_is_reported(self):
        payload = encode_records(dataclasses.replace(self.record, date_raw=20260106), self.record)
        self.assertEqual(self.parse(payload).report.out_of_order_count, 1)

    def test_027_out_of_order_record_remains_parseable(self):
        payload = encode_records(dataclasses.replace(self.record, date_raw=20260106), self.record)
        self.assertEqual(self.parse(payload).report.accepted_record_count, 2)

    def test_028_amount_float_candidate_preserved(self):
        self.assertAlmostEqual(self.parse().records[0].amount_float32_candidate, 123456.0)

    def test_029_amount_uint_candidate_preserved(self):
        self.assertIsInstance(self.parse().records[0].amount_uint32_candidate, int)

    def test_030_amount_raw_hex_preserved(self):
        self.assertEqual(len(self.parse().records[0].amount_raw_hex), 8)

    def test_031_nan_amount_has_no_float_candidate(self):
        payload = struct.pack("<IIIII4sII", 20260105, 1000, 1100, 900, 1050, b"\x00\x00\xc0\x7f", 10000, 0)
        self.assertIsNone(self.parse(payload).records[0].amount_float32_candidate)

    def test_032_negative_amount_has_no_float_candidate(self):
        payload = SyntheticDayRecord(amount_float=-1.0).encode()
        self.assertIsNone(self.parse(payload).records[0].amount_float32_candidate)

    def test_033_zero_amount_is_a_candidate_not_authority(self):
        result = self.parse(SyntheticDayRecord(amount_float=0.0).encode())
        self.assertEqual(result.records[0].amount_float32_candidate, 0.0)

    def test_034_volume_vendor_value_preserved(self):
        self.assertEqual(self.parse().records[0].volume_vendor_raw, 10000)

    def test_035_zero_volume_preserved(self):
        result = self.parse(SyntheticDayRecord(volume_raw=0).encode())
        self.assertEqual(result.records[0].volume_vendor_raw, 0)

    def test_036_reserved_value_preserved(self):
        result = self.parse(SyntheticDayRecord(reserved_raw=65536).encode())
        self.assertEqual(result.records[0].reserved_vendor_raw, 65536)

    def test_037_nonzero_reserved_counted(self):
        result = self.parse(SyntheticDayRecord(reserved_raw=1).encode())
        self.assertEqual(result.report.nonzero_reserved_count, 1)

    def test_038_record_offsets_are_stable(self):
        result = self.parse(encode_records(self.record, dataclasses.replace(self.record, date_raw=20260106)))
        self.assertEqual([item.byte_offset for item in result.records], [0, 32])

    def test_039_record_indexes_are_stable(self):
        result = self.parse(encode_records(self.record, dataclasses.replace(self.record, date_raw=20260106)))
        self.assertEqual([item.record_index for item in result.records], [0, 1])

    def test_040_hash_is_deterministic(self):
        self.assertEqual(self.parse().report.parse_core_hash, self.parse().report.parse_core_hash)

    def test_041_different_content_changes_core_hash(self):
        other = self.parse(dataclasses.replace(self.record, close_raw=1040).encode())
        self.assertNotEqual(self.parse().report.parse_core_hash, other.report.parse_core_hash)

    def test_042_public_receipt_has_no_records(self):
        self.assertNotIn("records", self.parse().report.public_receipt())

    def test_043_public_receipt_keeps_no_trade(self):
        self.assertTrue(self.parse().report.public_receipt()["no_trade_gate"])

    def test_044_parse_report_never_authority_writes(self):
        self.assertFalse(self.parse().report.authority_write)

    def test_045_amount_semantics_not_authoritative(self):
        decision = {item.field_name: item for item in field_semantic_decisions()}["amount"]
        self.assertFalse(decision.authority_feature_allowed)

    def test_046_volume_unit_is_unknown(self):
        decision = {item.field_name: item for item in field_semantic_decisions()}["volume"]
        self.assertEqual(decision.status, "UNKNOWN")

    def test_047_reserved_semantics_are_unknown(self):
        decision = {item.field_name: item for item in field_semantic_decisions()}["reserved"]
        self.assertEqual(decision.status, "UNKNOWN")

    def test_048_ohlc_semantics_are_verified(self):
        decisions = {item.field_name: item for item in field_semantic_decisions()}
        self.assertTrue(all(decisions[key].status == "VERIFIED" for key in ("open", "high", "low", "close")))

    def test_049_report_tracks_source_count(self):
        payload = encode_records(self.record, dataclasses.replace(self.record, date_raw=20260106))
        self.assertEqual(self.parse(payload).report.source_record_count, 2)

    def test_050_report_tracks_first_and_last_date(self):
        payload = encode_records(self.record, dataclasses.replace(self.record, date_raw=20260106))
        report = self.parse(payload).report
        self.assertEqual((report.first_date, report.last_date), ("2026-01-05", "2026-01-06"))


class ActivationAndAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "sample.day"
        self.payload = SyntheticDayRecord().encode()
        self.path.write_bytes(self.payload)
        self.sha = hashlib.sha256(self.payload).hexdigest()

    def test_051_valid_policy_digest_is_deterministic(self):
        self.assertEqual(policy(self.sha).digest(), policy(self.sha).digest())

    def test_052_policy_rejects_authority_write(self):
        with self.assertRaisesRegex(ContractError, "authority_write"):
            policy(self.sha, authority_write=True).validate()

    def test_053_policy_requires_no_trade(self):
        with self.assertRaisesRegex(ContractError, "no_trade"):
            policy(self.sha, no_trade_gate=False).validate()

    def test_054_policy_rejects_realtime(self):
        with self.assertRaisesRegex(ContractError, "realtime"):
            policy(self.sha, realtime_enabled=True).validate()

    def test_055_policy_rejects_raw_export(self):
        with self.assertRaisesRegex(ContractError, "raw_export"):
            policy(self.sha, raw_export_allowed=True).validate()

    def test_056_policy_rejects_wrong_purpose(self):
        with self.assertRaisesRegex(ContractError, "purpose"):
            policy(self.sha, purpose="PRODUCTION").validate()

    def test_057_policy_rejects_bad_hash(self):
        with self.assertRaisesRegex(ContractError, "sha256"):
            policy("bad").validate()

    def test_058_adapter_returns_partial_not_verified(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.PARTIALLY_VERIFIED)

    def test_059_adapter_hash_mismatch_rejected(self):
        bad = "0" * 64
        result = TdxDaySourceAdapter(self.path, policy(bad)).load(manifest(bad), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_060_adapter_manifest_id_mismatch_rejected(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha, manifest_id="other")).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_061_adapter_policy_manifest_hash_mismatch_rejected(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest("0" * 64), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_062_adapter_rejects_synthetic_manifest(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha, synthetic=True), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_063_adapter_rejects_wrong_suffix(self):
        other = Path(self.temp.name) / "sample.bin"
        other.write_bytes(self.payload)
        result = TdxDaySourceAdapter(other, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_064_adapter_rejects_missing_file(self):
        missing = Path(self.temp.name) / "missing.day"
        result = TdxDaySourceAdapter(missing, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertIs(result.status, AdapterStatus.REJECTED)

    def test_065_adapter_payload_is_aggregate_only(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertNotIn("records", result.payload)

    def test_066_adapter_keeps_authority_write_false(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertFalse(result.authority_write)

    def test_067_adapter_keeps_no_trade_true(self):
        result = TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertTrue(result.no_trade_gate)

    def test_068_cli_outputs_json_receipt(self):
        manifest_path = Path(self.temp.name) / "manifest.yaml"
        policy_path = Path(self.temp.name) / "policy.yaml"
        manifest_path.write_text(yaml.safe_dump(serialize_contract(manifest(self.sha))), encoding="utf-8")
        policy_path.write_text(yaml.safe_dump(dataclasses.asdict(policy(self.sha))), encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli_main(["validate-day", "--manifest", str(manifest_path), "--activation-policy", str(policy_path), "--artifact", str(self.path), "--as-of", "2026-12-31T00:00:00Z"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "PARTIALLY_VERIFIED")

    def test_069_cli_receipt_has_no_raw_records(self):
        manifest_path = Path(self.temp.name) / "manifest.yaml"
        policy_path = Path(self.temp.name) / "policy.yaml"
        manifest_path.write_text(yaml.safe_dump(serialize_contract(manifest(self.sha))), encoding="utf-8")
        policy_path.write_text(yaml.safe_dump(dataclasses.asdict(policy(self.sha))), encoding="utf-8")
        output = io.StringIO()
        with redirect_stdout(output):
            cli_main(["validate-day", "--manifest", str(manifest_path), "--activation-policy", str(policy_path), "--artifact", str(self.path), "--as-of", "2026-12-31T00:00:00Z"])
        self.assertNotIn("records", json.loads(output.getvalue())["payload"])

    def test_070_file_is_not_modified(self):
        before = self.path.read_bytes()
        TdxDaySourceAdapter(self.path, policy(self.sha)).load(manifest(self.sha), "2026-12-31T00:00:00Z")
        self.assertEqual(self.path.read_bytes(), before)

    def test_071_activation_round_trip(self):
        original = policy(self.sha)
        restored = deserialize_phase_contract("SourceActivationPolicy", serialize_phase_contract(original))
        self.assertEqual(restored, original)

    def test_072_unknown_contract_field_rejected(self):
        payload = serialize_phase_contract(policy(self.sha))
        payload["unexpected"] = True
        with self.assertRaisesRegex(ContractError, "unknown_phase_contract_field"):
            deserialize_phase_contract("SourceActivationPolicy", payload)

    def test_073_incompatible_major_rejected(self):
        payload = serialize_phase_contract(policy(self.sha))
        payload["schema_version"] = "2.0.0"
        with self.assertRaisesRegex(ContractError, "schema_version"):
            deserialize_phase_contract("SourceActivationPolicy", payload)

    def test_074_activation_schema_accepts_valid_contract(self):
        schema = json.loads((PHASE_ROOT / "schemas" / "SourceActivationPolicy.schema.json").read_text(encoding="utf-8"))
        validate_schema_subset(schema, serialize_phase_contract(policy(self.sha)))

    def test_075_activation_schema_rejects_unknown_field(self):
        schema = json.loads((PHASE_ROOT / "schemas" / "SourceActivationPolicy.schema.json").read_text(encoding="utf-8"))
        payload = serialize_phase_contract(policy(self.sha))
        payload["unexpected"] = True
        with self.assertRaises(SchemaValidationError):
            validate_schema_subset(schema, payload)

    def test_076_parse_report_round_trip(self):
        parsed = TdxDaySourceAdapter(self.path, policy(self.sha)).load_parsed(manifest(self.sha), "2026-12-31T00:00:00Z")
        restored = deserialize_phase_contract("ParseReport", serialize_phase_contract(parsed.report))
        self.assertEqual(restored, parsed.report)


if __name__ == "__main__":
    unittest.main()
