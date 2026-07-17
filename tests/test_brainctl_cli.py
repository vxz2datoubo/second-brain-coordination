from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

from apps.cli.brainctl import main


def build_sample_csv() -> str:
    rows = ["date,open,high,low,close,volume"]
    current = date(2026, 1, 5)
    close_price = 10.0
    drift_pattern = [0.18, 0.11, -0.06, 0.24, -0.08, 0.15, -0.03, 0.19]
    volume_pattern = [120000, 145000, 132000, 188000, 165000, 210000, 176000, 225000]
    generated = 0
    while generated < 96:
        if current.weekday() >= 5:
            current += timedelta(days=1)
            continue
        drift = drift_pattern[generated % len(drift_pattern)]
        open_price = close_price
        close_price = round(max(8.5, close_price + drift), 2)
        high_price = round(max(open_price, close_price) + 0.22 + (generated % 3) * 0.03, 2)
        low_price = round(min(open_price, close_price) - 0.18 - (generated % 2) * 0.02, 2)
        volume = volume_pattern[generated % len(volume_pattern)] + generated * 3500
        rows.append(
            f"{current.isoformat()},{open_price:.2f},{high_price:.2f},{low_price:.2f},{close_price:.2f},{volume}"
        )
        current += timedelta(days=1)
        generated += 1
    return "\n".join(rows) + "\n"


class BrainCtlCliTests(unittest.TestCase):
    def test_trading_replay_summary_only_emits_compact_summary(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-replay",
                "--data-path",
                str(sample),
                "--symbol",
                "300418",
                "--summary-only",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["symbol"], "300418")
        self.assertEqual(payload["market"], "CN-A")
        self.assertIn("selected_candidate_summary", payload)
        self.assertIn("candidate_summaries", payload)
        self.assertIn("sample_comparison", payload)
        self.assertNotIn("trade_journal", payload)
        self.assertIn(payload["selected_candidate_summary"]["portfolio_action"], {"trade", "no_trade"})
        self.assertIn(payload["selected_candidate_summary"]["out_of_sample_result"], {"pass", "fail", "not_run"})
        self.assertIn("out_of_sample_result_reason", payload["selected_candidate_summary"])
        self.assertIn("out_of_sample_coverage_status", payload["selected_candidate_summary"])
        self.assertIn("oos_trade_pairs_count", payload["selected_candidate_summary"])
        self.assertIn("min_promotable_oos_trade_pairs", payload["selected_candidate_summary"])
        self.assertIn("promotion_ready", payload["selected_candidate_summary"])
        self.assertIn(payload["selected_candidate_summary"]["sample_consistency"], {"aligned", "train_stronger_than_test", "oos_stronger_than_train", "diverged", "not_run"})
        self.assertIn("primary_gate", payload["selected_candidate_summary"])
        self.assertIn("queue_recommendation", payload["selected_candidate_summary"])
        self.assertIn("upgrade_candidate_status", payload["selected_candidate_summary"])
        self.assertIn("freeze_candidate_status", payload["selected_candidate_summary"])
        self.assertIn("a_share_redline_summary", payload["selected_candidate_summary"])
        self.assertIn("a_share_redline_blocks_action", payload["selected_candidate_summary"])
        self.assertIn("a_share_redline_warning_count", payload["selected_candidate_summary"])
        self.assertTrue(payload["selected_candidate_summary"]["primary_gate"])
        self.assertTrue(payload["selected_candidate_summary"]["queue_recommendation"])
        self.assertTrue(payload["candidate_summaries"])
        self.assertTrue(any(item["sample_consistency"] != "not_run" for item in payload["candidate_summaries"]))
        self.assertTrue(all("primary_gate" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all(item["primary_gate"] for item in payload["candidate_summaries"]))
        self.assertTrue(all("out_of_sample_result_reason" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all("out_of_sample_coverage_status" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all("oos_trade_pairs_count" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all("min_promotable_oos_trade_pairs" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all("promotion_ready" in item for item in payload["candidate_summaries"]))
        self.assertTrue(all("a_share_redline_summary" in item for item in payload["candidate_summaries"]))
        pair_summaries = []
        for item in payload["candidate_summaries"]:
            sample_summary = str(item.get("sample_comparison_summary", "") or "")
            if "recent_pairs=[" in sample_summary:
                pair_summaries.append(sample_summary)
        if pair_summaries:
            self.assertTrue(all("->:+" not in item for item in pair_summaries))

    def test_trading_manual_approval_cli_writes_back_research_queue_state(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")

        replay_payload = {}
        replay_exit = 0
        for _ in range(4):
            replay_stdout = io.StringIO()
            with redirect_stdout(replay_stdout):
                replay_exit = main([
                    "--root",
                    str(root),
                    "trading-replay",
                    "--data-path",
                    str(sample),
                    "--symbol",
                    "300418",
                ])
            replay_payload = json.loads(replay_stdout.getvalue())

        self.assertEqual(replay_exit, 0)
        self.assertIn("research_queue_skill_registry_entry", replay_payload)
        self.assertEqual(replay_payload["research_queue_skill_registry_entry"]["metadata"]["candidate_slug"], "vwap")

        approval_stdout = io.StringIO()
        with redirect_stdout(approval_stdout):
            approval_exit = main([
                "--root",
                str(root),
                "trading-confirm-research-queue-manual-approval",
                "--candidate-slug",
                "vwap",
                "--decision",
                "deferred",
                "--reviewer",
                "cli-tester",
                "--rationale",
                "证据清单还没补齐，先保持 ResearchQueue。",
                "--follow-up-item",
                "补齐 consistency_guard",
                "--evidence-note",
                "仍是 daily_proxy scaffold",
            ])

        self.assertEqual(approval_exit, 0)
        payload = json.loads(approval_stdout.getvalue())
        self.assertTrue(payload["success"])
        self.assertEqual(payload["learning_entry"]["entry_type"], "trading_research_queue_manual_promotion_approval_result")
        self.assertEqual(payload["learning_entry"]["metadata"]["candidate_slug"], "vwap")
        self.assertEqual(payload["learning_entry"]["metadata"]["decision"], "deferred")
        self.assertEqual(payload["learning_entry"]["metadata"]["reviewer"], "cli-tester")
        self.assertEqual(payload["self_evolution_log"]["trigger"], "trading_research_queue_manual_promotion_approval_result_learning")
        self.assertEqual(payload["module_status_record"]["module_name"], "trading_research_queue_vwap_v0_1")
        self.assertEqual(payload["module_status_record"]["status"], "Experimental")
        self.assertEqual(payload["bulletin_state_record"]["metadata"]["candidate_slug"], "vwap")
        self.assertEqual(payload["approval_summary"]["summary"]["approval_record_count"], 1)
        self.assertEqual(payload["approval_summary"]["summary"]["deferred_count"], 1)
        self.assertEqual(payload["approval_summary"]["summary"]["human_reviewed_count"], 1)
        self.assertTrue(payload["approval_summary"]["candidate_rows"][0]["human_reviewed"])
        self.assertTrue(payload["approval_summary"]["candidate_rows"][0]["latest_reviewed_at"])
        self.assertEqual(payload["approval_summary"]["integration_note"]["workflow_status"], "Implemented")

    def test_workbuddy_context_snapshot_cli_accepts_candidate_slug_and_snapshot_file(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")
        for _ in range(4):
            replay_stdout = io.StringIO()
            with redirect_stdout(replay_stdout):
                replay_exit = main([
                    "--root",
                    str(root),
                    "trading-replay",
                    "--data-path",
                    str(sample),
                    "--symbol",
                    "300418",
                ])
            self.assertEqual(replay_exit, 0)
        snapshot = root / "workbuddy-context.json"
        snapshot.write_text(json.dumps({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI应用", "strength": 0.63, "leader": "300418"},
            "macro_context": {"market_pressure": 0.04, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.8},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.6},
            ],
            "fund_flow_context": {"context_score": 0.42, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:30:00+08:00"
        }, ensure_ascii=False), encoding="utf-8")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-a-share-workbuddy-context-snapshot",
                "--snapshot-path",
                str(snapshot),
                "--candidate-slug",
                "vwap",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["candidate_slug"], "vwap")
        self.assertEqual(payload["symbol"], "300418")
        self.assertTrue(payload["proxy_guard_source_coverage_report"])
        self.assertTrue(payload["research_queue_sync"])
        self.assertEqual(payload["workbuddy_context_snapshot"]["provider"], "workbuddy_neodata_market_context")

    def test_tencent_qt_snapshot_cli_accepts_candidate_slug_and_orderbook_json(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")
        for _ in range(4):
            replay_stdout = io.StringIO()
            with redirect_stdout(replay_stdout):
                replay_exit = main([
                    "--root",
                    str(root),
                    "trading-replay",
                    "--data-path",
                    str(sample),
                    "--symbol",
                    "300418",
                ])
            self.assertEqual(replay_exit, 0)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-a-share-tencent-qt-snapshot",
                "--symbol",
                "300418",
                "--price",
                "49.94",
                "--change-pct",
                "2.85",
                "--volume",
                "951000",
                "--amount",
                "47483940",
                "--northbound-flow",
                "1420000",
                "--quote-crosscheck",
                "aligned_with_tdx_sample",
                "--bids-json",
                '[{"price":49.93,"size":12000},{"price":49.92,"size":9000}]',
                "--asks-json",
                '[{"price":49.95,"size":8000},{"price":49.96,"size":7600}]',
                "--quote-ts",
                "2026-07-14T10:45:00+08:00",
                "--candidate-slug",
                "vwap",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["candidate_slug"], "vwap")
        self.assertEqual(payload["symbol"], "300418")
        self.assertTrue(payload["proxy_guard_source_coverage_report"])
        self.assertTrue(payload["research_queue_sync"])
        self.assertEqual(payload["tencent_qt_snapshot"]["provider"], "tencent_qt_realtime_orderbook")

    def test_proxy_guard_source_coverage_cli_reports_route_gap_without_samples(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")
        for _ in range(4):
            replay_stdout = io.StringIO()
            with redirect_stdout(replay_stdout):
                replay_exit = main([
                    "--root",
                    str(root),
                    "trading-replay",
                    "--data-path",
                    str(sample),
                    "--symbol",
                    "300418",
                ])
            self.assertEqual(replay_exit, 0)

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-a-share-proxy-guard-source-coverage",
                "--candidate-slug",
                "vwap",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["candidate_slug"], "vwap")
        self.assertEqual(payload["symbol"], "300418")
        self.assertEqual(payload["timeframe"], "1d")
        self.assertFalse(payload["proxy_diagnostics"]["blocked"])
        self.assertEqual(payload["proxy_diagnostics"]["priority_source_clearance_stage"], "waiting_for_sample")
        self.assertEqual(payload["proxy_diagnostics"]["priority_source_key"], "tdx_realtime_quotes")
        self.assertEqual(payload["proxy_diagnostics"]["sample_attached_count"], 0)
        self.assertIn("TDX realtime quotes", payload["proxy_diagnostics"]["route_plan_summary"])
        self.assertEqual(
            payload["module_status_record"]["module_name"],
            "trading_a_share_proxy_guard_source_coverage",
        )
        self.assertEqual(
            payload["self_evolution_log"]["trigger"],
            "trading_a_share_proxy_guard_source_coverage_reported",
        )

    def test_trading_replay_cli_accepts_a_share_redline_context(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-replay",
                "--data-path",
                str(sample),
                "--symbol",
                "300418",
                "--requested-action",
                "trade",
                "--quote-ts",
                "2026-07-14T09:35:00+08:00",
                "--market-trend",
                "TREND_DOWN",
                "--day-loss-pct",
                "-0.03",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        redline = payload["risk_check_result"]["metadata"]["a_share_redline_check"]
        blocked_rule_keys = {item["rule_key"] for item in redline["blocked_rules"]}
        self.assertEqual(payload["risk_check_result"]["action"], "no_trade")
        self.assertFalse(payload["risk_check_result"]["allowed"])
        self.assertTrue(redline["blocks_action"])
        self.assertIn("a_share_redline_opening_30m_no_new_buy", blocked_rule_keys)
        self.assertIn("a_share_redline_downtrend_chase_buy", blocked_rule_keys)
        self.assertIn("a_share_redline_daily_loss_circuit_breaker", blocked_rule_keys)
        self.assertIn("Redline summary:", payload["trade_journal"]["summary"])
        self.assertTrue(payload["decision_record"]["context"]["a_share_redline_check"]["blocks_action"])

    def test_trading_replay_summary_only_includes_redline_summary_when_triggered(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(build_sample_csv(), encoding="utf-8")

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = main([
                "--root",
                str(root),
                "trading-replay",
                "--data-path",
                str(sample),
                "--symbol",
                "300418",
                "--requested-action",
                "trade",
                "--quote-ts",
                "2026-07-14T09:35:00+08:00",
                "--market-trend",
                "TREND_DOWN",
                "--day-loss-pct",
                "-0.03",
                "--summary-only",
            ])

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        selected_summary = payload["selected_candidate_summary"]
        self.assertTrue(selected_summary["a_share_redline_blocks_action"])
        self.assertGreaterEqual(selected_summary["a_share_redline_warning_count"], 3)
        self.assertIn("final_action=no_trade", selected_summary["a_share_redline_summary"])
        self.assertIn("session=opening_30m_lock", selected_summary["a_share_redline_summary"])


if __name__ == "__main__":
    unittest.main()
