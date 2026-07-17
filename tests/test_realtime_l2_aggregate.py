from __future__ import annotations

import csv
import json
from pathlib import Path
import unittest

from brain_core.foundation_data_governance import TdxMcpSnapshotAdapter
from brain_core.realtime_l2_aggregate import (
    BLOCKED_RAW_CAPABILITIES,
    classify_broker_market_data_response,
    compute_l2_aggregate_deltas,
    low_cost_broker_permission_questions,
    normalize_tdx_l2_aggregate_payload,
    public_crawler_auxiliary_policy,
)


class RealtimeL2AggregateTests(unittest.TestCase):
    TASK_DIR = Path(__file__).resolve().parents[1] / "coordination" / "TASKS" / "TDX-L2-AGGREGATE-EXHAUST-0010"

    def test_normalizes_tdx_l2_aggregates_without_promoting_raw_ticks(self):
        payload = {
            "L2TicNum": "128",
            "L2OrderNum": "431",
            "TotalBVol": "120000",
            "TotalSVol": "98000",
            "BCancel": "3000",
            "SCancel": "2500",
            "Zjl": "123.45",
            "Zjl_HB": "0.67",
            "OpenAmo": "4567.89",
            "OpenZTBuy": "0",
            "Wtb": "12.3",
            "FzAmo": "88.8",
            "VOpenZAF": "1.2",
        }

        result = normalize_tdx_l2_aggregate_payload(payload, symbol="300418", local_sequence=7)

        self.assertEqual(result["raw_payload"]["symbol"], "300418")
        self.assertEqual(result["raw_payload"]["capability_level"], ["L2_AGGREGATE"])
        self.assertEqual(len(result["aggregate_fields"]), 13)
        self.assertEqual(result["missing_verified_fields"], [])
        self.assertIn("RAW_TRADE_TICK", result["blocked_capabilities"])
        self.assertIn("RAW_ORDER_EVENT", result["blocked_capabilities"])
        self.assertFalse(result["governance"]["raw_tick_verified"])
        self.assertFalse(result["governance"]["raw_order_verified"])
        self.assertFalse(result["governance"]["true_ddx_ddy_connected"])

        by_name = {item["raw_name"]: item for item in result["aggregate_fields"]}
        self.assertIn("RAW_TRADE_TICK", by_name["L2TicNum"]["not_equivalent_to"])
        self.assertIn("RAW_ORDER_EVENT", by_name["L2OrderNum"]["not_equivalent_to"])
        self.assertTrue(by_name["Zjl"]["vendor_defined"])
        self.assertTrue(by_name["Zjl_HB"]["vendor_defined"])
        self.assertIn("TRUE_DDX", by_name["Zjl"]["not_equivalent_to"])
        self.assertEqual(by_name["OpenZTBuy"]["numeric_value"], 0.0)
        self.assertEqual(by_name["OpenZTBuy"]["missing_kind"], "zero_value")

    def test_numeric_conversion_and_missing_kind_semantics(self):
        cases = [
            (None, None, "missing"),
            ("", None, "empty"),
            (" ", None, "empty"),
            ("0", 0.0, "zero_value"),
            (0, 0.0, "zero_value"),
            ("123.45", 123.45, "present_numeric"),
            (123, 123.0, "present_numeric"),
            ("-5.2", -5.2, "present_numeric"),
            ("abc", None, "present_non_numeric"),
            (object(), None, "present_non_numeric"),
            ("permission_denied", None, "permission_denied"),
            ("interface_error", None, "interface_error"),
            ("N/A", None, "not_applicable"),
            ("unknown", None, "unknown_sentinel"),
        ]
        for value, numeric, missing_kind in cases:
            with self.subTest(value=repr(value)):
                result = normalize_tdx_l2_aggregate_payload({"L2TicNum": value}, symbol="300418")
                field = next(item for item in result["aggregate_fields"] if item["raw_name"] == "L2TicNum")
                self.assertEqual(field["numeric_value"], numeric)
                self.assertEqual(field["missing_kind"], missing_kind)

        missing_result = normalize_tdx_l2_aggregate_payload({}, symbol="300418")
        self.assertIn("L2TicNum", missing_result["missing_verified_fields"])
        missing_details = {item["raw_name"]: item["missing_kind"] for item in missing_result["missing_field_details"]}
        self.assertEqual(missing_details["L2TicNum"], "missing")

    def test_partial_all_missing_and_extra_fields_keep_semantics(self):
        partial = normalize_tdx_l2_aggregate_payload({"L2TicNum": "1", "extra": "kept_in_hash_only"}, symbol="300418")
        self.assertEqual(len(partial["aggregate_fields"]), 1)
        self.assertEqual(len(partial["missing_verified_fields"]), 12)
        self.assertEqual(partial["raw_payload"]["field_semantics_version"], "tdx-l2-aggregate-verified-2026-07-16")

        empty = normalize_tdx_l2_aggregate_payload({}, symbol="300418")
        self.assertEqual(len(empty["aggregate_fields"]), 0)
        self.assertEqual(len(empty["missing_verified_fields"]), 13)
        self.assertEqual(empty["quality"]["validation_status"], "missing_verified_aggregate_fields")

    def test_delta_computation_blocks_unconfirmed_same_day_counter_drop(self):
        previous = normalize_tdx_l2_aggregate_payload({"L2TicNum": "100"}, symbol="300418")
        current_lower = normalize_tdx_l2_aggregate_payload({"L2TicNum": "80"}, symbol="300418")

        same_day = compute_l2_aggregate_deltas(previous, current_lower, same_trading_day=True)
        self.assertEqual(same_day["quality"]["validation_status"], "delta_anomaly")
        self.assertEqual(same_day["deltas"][0]["delta_status"], "anomaly_no_delta")
        self.assertIsNone(same_day["deltas"][0]["delta"])

        cross_day = compute_l2_aggregate_deltas(previous, current_lower, same_trading_day=False)
        self.assertEqual(cross_day["deltas"][0]["delta_status"], "reset_allowed")
        self.assertEqual(cross_day["deltas"][0]["delta"], 80.0)

    def test_tdx_snapshot_adapter_declares_l2_aggregates_but_not_true_ddx(self):
        descriptor = TdxMcpSnapshotAdapter(root=".", symbol="300418", timeframe="snapshot").capability_descriptor()
        caps = descriptor.capabilities

        self.assertEqual(caps["realtime_snapshot"]["status"], "available")
        self.assertIn("inside", caps["realtime_snapshot"]["field_coverage"])
        self.assertNotIn("ddx", caps["realtime_snapshot"]["field_coverage"])
        self.assertEqual(caps["l2_aggregate"]["status"], "partial")
        self.assertIn("L2TicNum", caps["l2_aggregate"]["field_coverage"])
        self.assertEqual(caps["true_ddx_ddy"]["status"], "unverified")
        self.assertEqual(caps["raw_trade_tick"]["fallback"], "block_tick_strategies")
        self.assertEqual(caps["raw_order_event"]["fallback"], "block_order_event_strategies")

    def test_low_cost_broker_questions_cover_required_entitlements(self):
        questions = low_cost_broker_permission_questions()
        flattened = " ".join(
            field for item in questions for field in item.get("must_answer_fields", [])
        )

        self.assertIn("ten_level", flattened)
        self.assertIn("raw_trade_tick", flattened)
        self.assertIn("raw_order_event", flattened)
        self.assertIn("order_queue", flattened)
        self.assertIn("market_data_only_mode", flattened)

    def test_public_crawler_policy_stays_auxiliary_only(self):
        policy = public_crawler_auxiliary_policy()

        self.assertEqual(policy["role"], "auxiliary_crosscheck_only")
        self.assertIn("promoting a route to RAW_TRADE_TICK", policy["forbidden_uses"])
        self.assertIn("clearing a_share_proxy_guard_clear by itself", policy["forbidden_uses"])
        self.assertIn("auxiliary_evidence", policy["required_labels"])
        self.assertLess(policy["default_quality"]["source_reliability"], 0.6)
        self.assertEqual(policy["default_quality"]["reliability_calibration_status"], "uncalibrated")
        self.assertEqual(policy["default_quality"]["default_reliability_hint"], 0.55)
        self.assertIn("delay_ms", policy["dynamic_reliability_fields"])
        self.assertIn("RAW_ORDER_EVENT", BLOCKED_RAW_CAPABILITIES)

    def test_broker_outreach_pack_has_schema_and_scorecard_fields(self):
        schema = json.loads((self.TASK_DIR / "BROKER-RESPONSE-SCHEMA.json").read_text(encoding="utf-8"))
        self.assertIn("raw_trade_tick", schema["capabilities"])
        self.assertIn("raw_order_event", schema["capabilities"])
        self.assertIn("order_queue", schema["capabilities"])
        self.assertIn("auction_trajectory", schema["capabilities"])
        self.assertEqual(schema["codex_classification"]["route_status"], "run_classify_broker_market_data_response")
        self.assertIn("RAW_TRADE_TICK", schema["codex_classification"]["blocked_capabilities"])

        with (self.TASK_DIR / "BROKER-ROUTE-SCORECARD.csv").open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
        self.assertIn("ten_level_book", header)
        self.assertIn("raw_trade_tick", header)
        self.assertIn("raw_order_event", header)
        self.assertIn("license_risk", header)

    def test_broker_classifier_keeps_raw_l2_claim_in_review_without_evidence(self):
        response = {
            "broker_name": "Example Broker",
            "official_product_name": "Example QMT L2",
            "market_data_only_mode": "yes",
            "account_or_order_functions_required": "no",
            "capabilities": {
                "five_level_book": "yes",
                "ten_level_book": "yes",
                "raw_trade_tick": "yes",
                "raw_order_event": "yes",
            },
            "timestamp_semantics": {
                "exchange_timestamp": "yes",
                "sequence_no": "yes",
            },
            "license": {
                "local_storage_allowed": "yes",
                "automation_allowed": "yes",
                "redistribution_allowed": "no",
            },
            "cost": {"monthly_fee": "low"},
            "evidence_files": {},
        }

        result = classify_broker_market_data_response(response)

        self.assertEqual(result["route_status"], "needs_documentation")
        self.assertNotIn("FIVE_LEVEL_SNAPSHOT", result["allowed_capabilities"])
        self.assertNotIn("TEN_LEVEL_SNAPSHOT", result["allowed_capabilities"])
        self.assertIn("FIVE_LEVEL_SNAPSHOT", result["candidate_capabilities"])
        self.assertIn("TEN_LEVEL_SNAPSHOT", result["candidate_capabilities"])
        self.assertIn("RAW_TRADE_TICK", result["candidate_capabilities"])
        self.assertIn("RAW_ORDER_EVENT", result["candidate_capabilities"])
        self.assertTrue(any("RAW_TRADE_TICK" in item for item in result["evidence_gaps"]))
        self.assertTrue(result["governance"]["requires_workbuddy_sample_pack"])
        self.assertFalse(result["governance"]["live_trading_enabled"])

    def test_broker_classifier_promotes_complete_reply_only_to_runtime_probe_candidate(self):
        response = {
            "broker_name": "Example Broker",
            "official_product_name": "Example XTP L2",
            "market_data_only_mode": "yes",
            "account_or_order_functions_required": "no",
            "capabilities": {
                "five_level_book": "yes",
                "ten_level_book": "yes",
                "l2_aggregate": "yes",
                "raw_trade_tick": "yes",
                "raw_order_event": "yes",
                "order_queue": "yes",
                "cancel_event": "yes",
                "auction_trajectory": "yes",
            },
            "timestamp_semantics": {
                "exchange_timestamp": "yes",
                "sequence_no": "yes",
                "channel_no": "yes",
            },
            "license": {
                "local_storage_allowed": "yes",
                "automation_allowed": "yes",
                "redistribution_allowed": "no",
                "terms_document": "docs/broker/terms.pdf",
            },
            "cost": {"monthly_fee": "low"},
            "evidence_files": {
                "field_list_path": "evidence/broker/field-list.md",
                "sdk_doc_path": "evidence/broker/sdk.md",
                "sample_payload_path": "evidence/broker/sample.jsonl",
                "license_terms_path": "evidence/broker/terms.md",
                "day_start_baseline_path": "evidence/broker/day-start.md",
                "order_book_recovery_path": "evidence/broker/recovery.md",
                "disconnect_recovery_doc_path": "evidence/broker/disconnect.md",
            },
            "route_isolation": {
                "readonly_process_supported": "yes",
                "method_whitelist_supported": "yes",
                "separate_market_data_entitlement": "yes",
                "trading_password_required": "no",
                "trading_counter_required": "no",
            },
        }

        result = classify_broker_market_data_response(response)

        self.assertEqual(result["route_status"], "qualified_for_readonly_probe")
        self.assertIn("RAW_TRADE_TICK", result["candidate_capabilities"])
        self.assertIn("RAW_ORDER_EVENT", result["candidate_capabilities"])
        self.assertIn("ORDER_QUEUE", result["candidate_capabilities"])
        self.assertEqual(result["evidence_gaps"], [])
        self.assertGreaterEqual(result["score"], 80)
        self.assertTrue(result["governance"]["requires_codex_runtime_validation"])

    def test_classifier_edge_cases_stay_conservative(self):
        base = {
            "broker_name": "Edge Broker",
            "official_product_name": "Edge L2",
            "market_data_only_mode": "yes",
            "account_or_order_functions_required": "no",
            "timestamp_semantics": {"exchange_timestamp": "yes", "sequence_no": "yes", "channel_no": "yes"},
            "license": {"local_storage_allowed": "yes", "automation_allowed": "yes", "redistribution_allowed": "no"},
            "cost": {"monthly_fee": "low"},
            "evidence_files": {
                "field_list_path": "evidence/fields.md",
                "sdk_doc_path": "evidence/sdk.md",
                "sample_payload_path": "evidence/sample.jsonl",
                "license_terms_path": "evidence/terms.md",
                "day_start_baseline_path": "evidence/day-start.md",
                "order_book_recovery_path": "evidence/recovery.md",
                "disconnect_recovery_doc_path": "evidence/disconnect.md",
            },
            "route_isolation": {"readonly_process_supported": "yes", "method_whitelist_supported": "yes"},
        }

        oral = {**base, "capabilities": {"ten_level_book": "yes"}, "evidence_files": {}}
        oral_result = classify_broker_market_data_response(oral)
        self.assertEqual(oral_result["route_status"], "needs_documentation")
        self.assertNotIn("TEN_LEVEL_SNAPSHOT", oral_result["allowed_capabilities"])

        ui_only = {**base, "capabilities": {"ten_level_book": "yes"}, "evidence_files": {"ui_screenshot_path": "shot.png"}}
        self.assertEqual(classify_broker_market_data_response(ui_only)["route_status"], "needs_documentation")

        tick_doc_no_sample = {**base, "capabilities": {"raw_trade_tick": "yes"}, "evidence_files": {"sdk_doc_path": "evidence/sdk.md", "field_list_path": "evidence/fields.md"}}
        self.assertEqual(classify_broker_market_data_response(tick_doc_no_sample)["route_status"], "needs_documentation")

        tick_no_time = {**base, "capabilities": {"raw_trade_tick": "yes"}, "timestamp_semantics": {"sequence_no": "yes"}}
        self.assertIn("RAW_TRADE_TICK:explicit_time_semantics", classify_broker_market_data_response(tick_no_time)["evidence_gaps"])

        tick_no_sequence = {**base, "capabilities": {"raw_trade_tick": "yes"}, "timestamp_semantics": {"exchange_timestamp": "yes"}}
        self.assertIn("RAW_TRADE_TICK:stable_sequence_or_event_key", classify_broker_market_data_response(tick_no_sequence)["evidence_gaps"])

        no_storage = {**base, "capabilities": {"raw_trade_tick": "yes"}, "license": {"local_storage_allowed": "no", "automation_allowed": "yes"}}
        self.assertNotEqual(classify_broker_market_data_response(no_storage)["route_status"], "qualified_for_readonly_probe")

        no_automation = {**base, "capabilities": {"raw_trade_tick": "yes"}, "license": {"local_storage_allowed": "yes", "automation_allowed": "no"}}
        self.assertNotEqual(classify_broker_market_data_response(no_automation)["route_status"], "qualified_for_readonly_probe")

        trading_methods_isolated = {**base, "capabilities": {"raw_trade_tick": "yes"}, "sdk_contains_trading_methods": "yes"}
        self.assertEqual(classify_broker_market_data_response(trading_methods_isolated)["route_status"], "qualified_for_readonly_probe")

        trading_counter_required = {
            **base,
            "capabilities": {"raw_trade_tick": "yes"},
            "market_data_only_mode": "no",
            "route_isolation": {"trading_counter_required": "yes"},
            "account_or_order_functions_required": "yes",
        }
        self.assertEqual(classify_broker_market_data_response(trading_counter_required)["route_status"], "blocked")


if __name__ == "__main__":
    unittest.main()
