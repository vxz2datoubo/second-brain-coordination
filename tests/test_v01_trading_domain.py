from __future__ import annotations

import json
from pathlib import Path
import tempfile
import textwrap
import unittest

from brain_core import SuperBrainV01
from brain_core.contracts import (
    BulletinStateRecord,
    LearningEntry,
    ModuleStatusRecord,
    SelfEvolutionLog,
    SkillRegistryEntry,
    SourceRecord,
)
from brain_core.trading_domain import TradingDomainV01


REAL_REPLAY_JSON = Path(r"F:\aidanao\data\kl_300418_1y.json")
REAL_DDX_REPLAY_JSON = Path(r"F:\aidanao\data\kl_ddx_1y.json")
SAMPLE_CSV = """\
date,open,high,low,close,volume
2026-05-01,10.00,10.20,9.90,10.10,100000
2026-05-04,10.10,10.30,10.00,10.20,120000
2026-05-05,10.20,10.50,10.10,10.45,180000
2026-05-06,10.45,10.70,10.30,10.60,210000
2026-05-07,10.60,10.80,10.40,10.55,190000
2026-05-08,10.55,10.90,10.50,10.85,240000
2026-05-11,10.85,11.10,10.70,11.00,260000
2026-05-12,11.00,11.30,10.90,11.20,300000
2026-05-13,11.20,11.40,11.00,11.10,260000
2026-05-14,11.10,11.50,11.00,11.45,330000
2026-05-15,11.45,11.80,11.30,11.70,390000
2026-05-18,11.70,12.10,11.60,12.00,450000
2026-05-19,12.00,12.20,11.80,11.90,400000
2026-05-20,11.90,12.30,11.80,12.25,470000
2026-05-21,12.25,12.60,12.10,12.50,520000
2026-05-22,12.50,12.80,12.30,12.70,560000
2026-05-25,12.70,12.90,12.40,12.55,500000
2026-05-26,12.55,12.70,12.20,12.30,470000
2026-05-27,12.30,12.50,12.00,12.10,430000
2026-05-28,12.10,12.40,11.90,12.35,490000
2026-05-29,12.35,12.80,12.30,12.65,530000
2026-06-01,12.65,13.00,12.60,12.95,590000
2026-06-02,12.95,13.20,12.70,13.10,610000
2026-06-03,13.10,13.40,12.95,13.32,650000
2026-06-04,13.32,13.60,13.10,13.55,700000
2026-06-05,13.55,13.90,13.30,13.80,760000
"""


class TradingDomainTests(unittest.TestCase):
    def make_brain_with_data(self) -> tuple[SuperBrainV01, Path]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sample = root / "sample.csv"
        sample.write_text(textwrap.dedent(SAMPLE_CSV), encoding="utf-8")
        return SuperBrainV01(root), sample

    def test_trading_replay_wires_into_mother_system(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["a_share_context"]["market"], "CN-A")
        self.assertEqual(result["a_share_context"]["trading_regime"], "T+1")
        self.assertEqual(
            result["a_share_context"]["auction_sessions"],
            ["09:15-09:20_cancelable", "09:20-09:25_non_cancelable"],
        )
        self.assertFalse(result["a_share_context"]["true_money_flow_connected"])
        self.assertEqual(result["a_share_context"]["seasoned_fresh_inference_status"], "Experimental")
        self.assertEqual(result["a_share_context"]["seasoned_fresh_true_data_status"], "Not Implemented Yet")
        self.assertEqual(result["a_share_context"]["seasoned_fresh_proxy_mode"], "ohlcv_behavioral_proxy")
        self.assertEqual(
            result["a_share_context"]["authority_constraints_snapshot"]["authority_document_version"],
            "2026-07-10",
        )
        self.assertEqual(
            result["a_share_context"]["authority_constraints_snapshot"]["probability_fusion_policy"]["implementation_status"],
            "Interface",
        )
        self.assertEqual(
            result["a_share_context"]["authority_constraints_snapshot"]["a_share_unique_cognition"]["participant_decision_profiles"]["behavior_model_status"],
            "Experimental",
        )
        self.assertIn(
            "turnover_information_exposure",
            result["a_share_context"]["authority_constraints_snapshot"]["a_share_unique_cognition"],
        )
        self.assertIn(
            "fresh_unlock_branching_uncertainty",
            result["a_share_context"]["authority_constraints_snapshot"]["a_share_unique_cognition"],
        )
        self.assertIn(
            "single_day_chip_exchange_limit",
            result["a_share_context"]["authority_constraints_snapshot"]["a_share_unique_cognition"],
        )
        self.assertIn(
            "ohlcv_money_flow_proxy",
            result["a_share_context"]["authority_constraints_snapshot"]["prohibited_proxies"],
        )
        self.assertEqual(result["a_share_context"]["true_money_flow_readiness"]["connection_status"], "Not Implemented Yet")
        self.assertEqual(result["a_share_context"]["true_money_flow_readiness"]["required_sources"][0]["source_key"], "tdx_realtime_quotes")
        self.assertEqual(
            result["a_share_context"]["true_money_flow_readiness"]["required_sources"][1]["source_key"],
            "tencent_qt_realtime_orderbook",
        )
        self.assertEqual(
            result["a_share_context"]["true_money_flow_readiness"]["required_sources"][2]["source_key"],
            "workbuddy_neodata_market_context",
        )
        self.assertIn(result["a_share_proxy_snapshot"]["bias_label"], {"fresh_bias", "seasoned_release_bias", "overnight_lock_pressure_bias", "mixed_bias", "low_signal"})
        self.assertEqual(result["a_share_proxy_snapshot"]["proxy_status"], "Experimental")
        self.assertIn("blocks_promotion", result["a_share_proxy_guard"])
        self.assertIn("preferred_action", result["a_share_proxy_guard"])
        self.assertEqual(result["market_data_record"]["symbol"], "300418")
        self.assertEqual(result["market_data_record"]["metadata"]["a_share_semantics"]["market"], "CN-A")
        self.assertEqual(result["market_data_record"]["metadata"]["a_share_semantics"]["ohlcv_money_flow_interpretation"], "Forbidden")
        self.assertEqual(result["strategy_definition"]["research_mode"], True)
        self.assertEqual(result["strategy_definition"]["live_trading_enabled"], False)
        self.assertIn(result["validation_report"]["verdict"], {"pass", "needs_review"})
        self.assertIn(result["validation_report"]["governance_action"], {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"})
        self.assertIn(result["validation_report"]["out_of_sample_result"], {"pass", "fail", "not_run"})
        self.assertIn("a_share_t1_context_disclosed", result["validation_report"]["checks"])
        self.assertIn("seasoned_fresh_proxy_disclosed", result["validation_report"]["checks"])
        self.assertIn("ohlcv_proxy_not_used_as_true_money_flow", result["validation_report"]["checks"])
        self.assertIn("a_share_authority_constraints_snapshot_attached", result["validation_report"]["checks"])
        self.assertIn("true_money_flow_interface_declared", result["validation_report"]["checks"])
        self.assertIn("true_ddx_ddy_not_connected", result["validation_report"]["warnings"])
        self.assertIn("seasoned_fresh_proxy_only", result["validation_report"]["warnings"])
        self.assertIn("a_share_true_money_flow_interface_not_connected", result["validation_report"]["warnings"])
        self.assertIn("a_share_probability_fusion_not_enforced", result["validation_report"]["warnings"])
        self.assertFalse(result["validation_report"]["metadata"]["a_share_semantics"]["true_money_flow_connected"])
        self.assertEqual(result["validation_report"]["metadata"]["a_share_proxy_snapshot"]["proxy_status"], "Experimental")
        self.assertIn("summary", result["validation_report"]["metadata"]["a_share_proxy_guard"])
        self.assertEqual(
            result["validation_report"]["metadata"]["authority_constraints_snapshot"]["probability_fusion_policy"]["minimum_aligned_signals"],
            3,
        )
        self.assertEqual(result["validation_report"]["metadata"]["commission_pct"], 0.00025)
        self.assertEqual(result["validation_report"]["metadata"]["slippage_pct"], 0.001)
        self.assertAlmostEqual(result["validation_report"]["metadata"]["cost_pct"], 0.00125)
        self.assertIn("total_cost_pct=0.00125", result["validation_report"]["metadata"]["cost_assumption_summary"])
        self.assertEqual(result["validation_report"]["metadata"]["true_money_flow_readiness"]["connection_status"], "Not Implemented Yet")
        self.assertEqual(
            result["validation_report"]["metadata"]["workbuddy_constraint_guard"]["blocks_promotion"],
            False,
        )
        self.assertEqual(
            result["validation_report"]["metadata"]["workbuddy_constraint_snapshot"]["status"],
            "not_reported",
        )
        self.assertIn("train_test_split", result["backtest_result"]["metadata"])
        self.assertEqual(result["backtest_result"]["metadata"]["a_share_semantics"]["data_granularity"], "daily_bar_proxy")
        split_summary = result["backtest_result"]["metadata"]["train_test_split"]
        self.assertIn("out_of_sample_result_reason", split_summary)
        self.assertIn("out_of_sample_coverage_status", split_summary)
        self.assertIn("oos_trade_pairs_count", split_summary)
        self.assertIn("min_promotable_oos_trade_pairs", split_summary)
        self.assertIn("promotion_ready", split_summary)
        self.assertIn("pass_checklist", split_summary)
        self.assertIn("failed_conditions", split_summary)
        self.assertIn(
            split_summary["out_of_sample_coverage_status"],
            {"not_run", "insufficient", "thin_pass", "sufficient"},
        )
        self.assertIsInstance(split_summary["pass_checklist"], dict)
        self.assertIsInstance(split_summary["failed_conditions"], list)
        self.assertTrue(
            all("cost_assumption_summary" in item for item in result["strategy_comparison"]["candidates"])
        )
        self.assertTrue(
            all(abs(float(item["cost_pct"]) - 0.00125) < 1e-9 for item in result["strategy_comparison"]["candidates"])
        )
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.replay_backtest_v0_1")
        self.assertEqual(result["skill_registry_entry"]["validation_status"], result["validation_report"]["verdict"])
        self.assertEqual(result["skill_registry_entry"]["out_of_sample_result"], result["module_status_record"]["out_of_sample_result"])
        self.assertEqual(result["skill_registry_entry"]["out_of_sample_result"], result["bulletin_state_record"]["out_of_sample_result"])
        self.assertEqual(result["skill_registry_entry"]["metadata"]["selection_governance_action"], result["strategy_comparison"]["selection_governance_action"])
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(result["skill_registry_entry"]["metadata"]["a_share_semantics"]["market"], "CN-A")
        self.assertEqual(result["skill_registry_entry"]["metadata"]["commission_pct"], 0.00025)
        self.assertEqual(result["skill_registry_entry"]["metadata"]["slippage_pct"], 0.001)
        self.assertAlmostEqual(result["skill_registry_entry"]["metadata"]["cost_pct"], 0.00125)
        self.assertIn(
            "total_cost_pct=0.00125",
            result["skill_registry_entry"]["metadata"]["cost_assumption_summary"],
        )
        self.assertGreaterEqual(result["skill_registry_entry"]["failure_count"], 0)
        self.assertEqual(result["module_status_record"]["module_name"], "trading_domain_v0_1")
        self.assertEqual(result["module_status_record"]["quality_action"], result["strategy_comparison"]["selection_governance_action"])
        self.assertEqual(result["module_status_record"]["metadata"]["selection_status"], result["strategy_comparison"]["selection_status"])
        self.assertEqual(
            result["module_status_record"]["metadata"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(result["module_status_record"]["metadata"]["a_share_semantics"]["trading_regime"], "T+1")
        self.assertEqual(result["module_status_record"]["metadata"]["commission_pct"], 0.00025)
        self.assertEqual(result["module_status_record"]["metadata"]["slippage_pct"], 0.001)
        self.assertAlmostEqual(result["module_status_record"]["metadata"]["cost_pct"], 0.00125)
        self.assertIn(
            "total_cost_pct=0.00125",
            result["module_status_record"]["metadata"]["cost_assumption_summary"],
        )
        self.assertEqual(result["module_status_record"]["failure_count"], result["skill_registry_entry"]["failure_count"])
        self.assertEqual(result["bulletin_state_record"]["failure_count"], result["skill_registry_entry"]["failure_count"])
        self.assertEqual(result["bulletin_state_record"]["metadata"]["portfolio_action"], result["strategy_comparison"]["portfolio_action"])
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(result["bulletin_state_record"]["metadata"]["commission_pct"], 0.00025)
        self.assertEqual(result["bulletin_state_record"]["metadata"]["slippage_pct"], 0.001)
        self.assertAlmostEqual(result["bulletin_state_record"]["metadata"]["cost_pct"], 0.00125)
        self.assertIn(
            "total_cost_pct=0.00125",
            result["bulletin_state_record"]["metadata"]["cost_assumption_summary"],
        )
        self.assertIn(
            result["validation_report"]["metadata"]["sample_comparison"]["consistency"],
            result["bulletin_state_record"]["metadata"]["selected_sample_consistency"],
        )
        self.assertIn(
            "train_return=",
            result["bulletin_state_record"]["metadata"]["selected_sample_summary"],
        )
        self.assertIn(
            "oos=",
            result["bulletin_state_record"]["metadata"]["top_ranked_candidate_summary"],
        )
        self.assertIn("Train/OOS snapshot:", result["trade_journal"]["summary"])
        self.assertIn("Selection gate:", result["trade_journal"]["summary"])
        self.assertIn("Cost assumptions:", result["trade_journal"]["summary"])
        self.assertIn("Top ranked candidate:", result["trade_journal"]["summary"])
        self.assertTrue(result["bulletin_state_record"]["summary"])
        self.assertIn("Train/OOS snapshot:", result["bulletin_state_record"]["summary"])
        self.assertIn("Costs:", result["bulletin_state_record"]["summary"])
        self.assertIn("true DDX/DDY is not connected yet.", result["bulletin_state_record"]["summary"])
        self.assertEqual(result["strategy_comparison"]["selection_state_summary"]["selection_engine"], "direct_replay_ranking")
        self.assertEqual(result["strategy_comparison"]["selection_state_summary"]["selection_engine_status"], "Transitional")
        self.assertTrue(result["strategy_comparison"]["selection_state_summary"]["pending_probability_fusion_override"])
        self.assertEqual(
            result["strategy_comparison"]["selection_state_summary"]["target_override_engine"],
            "workbuddy_probability_fusion",
        )
        self.assertEqual(result["bulletin_state_record"]["metadata"]["a_share_semantics"]["ohlcv_usage"], "price_volume_structure_only")
        self.assertTrue(result["price_bars"])
        self.assertTrue(result["feature_preview"])
        latest_feature = result["feature_preview"][-1]["features"]
        self.assertIn("vwap_proxy_anchor", latest_feature)
        self.assertIn("vwap_proxy_20", latest_feature)
        self.assertIn("vwap_deviation_proxy_20", latest_feature)
        self.assertIn("vwap_position_proxy", latest_feature)
        self.assertIn("vwap_slope_proxy_5", latest_feature)
        self.assertIn("market_regime_proxy", latest_feature)
        self.assertIn("market_regime_proxy_reason", latest_feature)
        self.assertIn("range_pct_1d", latest_feature)
        self.assertIn("volatility_proxy_5", latest_feature)
        self.assertIn("fresh_participation_proxy", latest_feature)
        self.assertIn("seasoned_release_proxy", latest_feature)
        self.assertIn("t1_lock_pressure_proxy", latest_feature)
        self.assertIn("seasoned_fresh_proxy_label", latest_feature)
        self.assertTrue(any(item["name"] == "AnchoredVWAPDataset" for item in result["indicator_definitions"]))
        self.assertTrue(any(item["name"] == "VWAPDeviationProxy20" for item in result["indicator_definitions"]))
        self.assertTrue(any(item["name"] == "FreshParticipationProxy" for item in result["indicator_definitions"]))
        self.assertTrue(any(item["name"] == "SeasonedReleaseProxy" for item in result["indicator_definitions"]))
        self.assertTrue(any(item["name"] == "T1LockPressureProxy" for item in result["indicator_definitions"]))
        self.assertEqual(
            result["validation_report"]["metadata"]["research_queue_scaffolds"]["vwap"]["feature_scaffold_status"],
            "Implemented",
        )
        self.assertEqual(
            result["validation_report"]["metadata"]["research_queue_scaffolds"]["vwap"]["mode"],
            "daily_proxy",
        )
        sample_compare = result["validation_report"]["metadata"]["sample_comparison"]
        self.assertIn("train_total_return", sample_compare)
        self.assertIn("test_total_return", sample_compare)
        self.assertIn("consistency", sample_compare)
        self.assertIn("summary", sample_compare)
        self.assertIn("train_max_drawdown", sample_compare)
        self.assertIn("test_max_drawdown", sample_compare)
        self.assertIn("train_win_rate", sample_compare)
        self.assertIn("test_win_rate", sample_compare)
        self.assertIn("drawdown_gap", sample_compare)
        self.assertIn("win_rate_gap", sample_compare)
        self.assertIn("trades_count_gap", sample_compare)
        self.assertIn("trade_breakdown", sample_compare)
        self.assertIn("market_regime_split", sample_compare)
        self.assertIn("market_regime_alignment", sample_compare)
        self.assertIn("train", sample_compare["trade_breakdown"])
        self.assertIn("test", sample_compare["trade_breakdown"])
        self.assertIn("summary", sample_compare["trade_breakdown"]["train"])
        self.assertIn("summary", sample_compare["trade_breakdown"]["test"])
        self.assertIn("recent_pairs_count", sample_compare["trade_breakdown"]["test"])
        self.assertIn("train", sample_compare["market_regime_split"])
        self.assertIn("test", sample_compare["market_regime_split"])
        self.assertIn("dominant_regime", sample_compare["market_regime_split"]["train"])
        self.assertIn("dominant_regime", sample_compare["market_regime_split"]["test"])
        self.assertIn(sample_compare["market_regime_alignment"], {"aligned", "shifted", "not_run"})
        self.assertIn("regime_train=", sample_compare["summary"])
        self.assertIn("regime_test=", sample_compare["summary"])
        governance_explanation = result["validation_report"]["metadata"]["governance_explanation"]
        self.assertIn("action", governance_explanation)
        self.assertIn("primary_reason", governance_explanation)
        self.assertIn("reasons", governance_explanation)
        self.assertIn("summary", governance_explanation)
        historical_validation_snapshot = result["validation_report"]["metadata"]["historical_validation_snapshot"]
        self.assertIn("recent_validation_count", historical_validation_snapshot)
        self.assertIn("consecutive_hard_failures", historical_validation_snapshot)
        self.assertIn("consecutive_review_failures", historical_validation_snapshot)
        self.assertIn("out_of_sample_counts", historical_validation_snapshot)
        self.assertIn("governance_action_counts", historical_validation_snapshot)
        self.assertIn("latest_validation", historical_validation_snapshot)
        self.assertIn("summary", historical_validation_snapshot)
        self.assertEqual(
            historical_validation_snapshot["consecutive_hard_failures"],
            result["validation_report"]["metadata"]["historical_failure_count"],
        )
        self.assertEqual(
            result["strategy_review"]["metadata"]["historical_validation_snapshot"]["summary"],
            historical_validation_snapshot["summary"],
        )
        retire_thresholds = result["validation_report"]["metadata"]["retire_candidate_thresholds"]
        self.assertIn("historical_failure_threshold", retire_thresholds)
        self.assertIn("gap_assisted_failure_threshold", retire_thresholds)
        self.assertIn("summary", retire_thresholds)
        freeze_thresholds = result["validation_report"]["metadata"]["freeze_thresholds"]
        self.assertIn("expected_oos_result", freeze_thresholds)
        self.assertIn("sample_divergence_guard", freeze_thresholds)
        self.assertIn("summary", freeze_thresholds)
        downgrade_thresholds = result["validation_report"]["metadata"]["downgrade_thresholds"]
        self.assertIn("non_positive_total_return_triggered", downgrade_thresholds)
        self.assertIn("sample_size_total_bars_triggered", downgrade_thresholds)
        self.assertIn("sample_size_trade_pairs_triggered", downgrade_thresholds)
        self.assertIn("sample_size_oos_trade_pairs_triggered", downgrade_thresholds)
        self.assertIn("downgrade_triggered", downgrade_thresholds)
        self.assertIn("summary", downgrade_thresholds)
        sample_size_thresholds = result["validation_report"]["metadata"]["sample_size_thresholds"]
        self.assertIn("min_total_bars", sample_size_thresholds)
        self.assertIn("min_completed_trade_pairs", sample_size_thresholds)
        self.assertIn("min_oos_completed_trade_pairs", sample_size_thresholds)
        self.assertIn("out_of_sample_result_reason", sample_size_thresholds)
        self.assertIn("out_of_sample_coverage_status", sample_size_thresholds)
        self.assertIn("promotion_ready", sample_size_thresholds)
        self.assertIn("blocks_promotion", sample_size_thresholds)
        self.assertIn("summary", sample_size_thresholds)
        out_of_sample_guard = result["validation_report"]["metadata"]["out_of_sample_guard_summary"]
        self.assertIn("gate_status", out_of_sample_guard)
        self.assertIn("promotion_blocked", out_of_sample_guard)
        self.assertIn("severity", out_of_sample_guard)
        self.assertIn("reason_key", out_of_sample_guard)
        self.assertIn("preferred_action", out_of_sample_guard)
        self.assertIn("summary", out_of_sample_guard)
        if result["validation_report"]["out_of_sample_result"] == "fail":
            self.assertEqual(out_of_sample_guard["gate_status"], "failed")
            self.assertTrue(out_of_sample_guard["promotion_blocked"])
        elif result["validation_report"]["out_of_sample_result"] == "not_run":
            self.assertEqual(out_of_sample_guard["gate_status"], "not_run")
            self.assertTrue(out_of_sample_guard["promotion_blocked"])
        else:
            self.assertIn(
                out_of_sample_guard["gate_status"],
                {"passed", "pass_with_thin_oos", "pass_but_consistency_gap"},
            )
        governance_rule_snapshot = result["validation_report"]["metadata"]["governance_rule_snapshot"]
        self.assertEqual(
            governance_rule_snapshot["selected_action"],
            result["validation_report"]["governance_action"],
        )
        self.assertEqual(
            governance_rule_snapshot["selected_rule"]["action"],
            result["validation_report"]["governance_action"],
        )
        self.assertTrue(governance_rule_snapshot["rule_evaluations"])
        self.assertTrue(any(item["rule_key"] == "sample_size_guard" for item in governance_rule_snapshot["rule_evaluations"]))
        self.assertTrue(
            any(
                item["rule_key"] == "workbuddy_constraint_research_only_no_trade"
                for item in governance_rule_snapshot["rule_evaluations"]
            )
        )
        self.assertIn("summary", governance_rule_snapshot)
        self.assertTrue(any(item.startswith("Train/OOS comparison:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("A-share context:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("A-share authority constraints:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Seasoned/Fresh proxy snapshot:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("True money-flow readiness:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Governance explanation:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Governance rule snapshot:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Historical validation snapshot:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Retire thresholds:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Freeze thresholds:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Downgrade thresholds:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Sample-size thresholds:") for item in result["strategy_review"]["lessons"]))
        self.assertTrue(any(item.startswith("Out-of-sample guard:") for item in result["strategy_review"]["lessons"]))
        self.assertEqual(
            result["strategy_review"]["metadata"]["governance_rule_snapshot"]["selected_action"],
            result["validation_report"]["governance_action"],
        )
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_replay_validation")
        self.assertEqual(
            result["self_evolution_log"]["metrics"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(result["self_evolution_log"]["metrics"]["commission_pct"], 0.00025)
        self.assertEqual(result["self_evolution_log"]["metrics"]["slippage_pct"], 0.001)
        self.assertAlmostEqual(result["self_evolution_log"]["metrics"]["cost_pct"], 0.00125)
        self.assertIn(
            "total_cost_pct=0.00125",
            result["self_evolution_log"]["metrics"]["cost_assumption_summary"],
        )
        trading_status = brain.status()["trading_status"]
        self.assertEqual(
            trading_status["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(
            trading_status["primary_gate"],
            result["strategy_comparison"]["selection_state_summary"]["primary_gate"],
        )
        self.assertEqual(
            trading_status["queue_recommendation"],
            result["strategy_comparison"]["selection_state_summary"]["queue_recommendation"],
        )
        expected_selected_validation = result["selected_validation_report"] or result["validation_report"]
        expected_selected_thresholds = expected_selected_validation["metadata"]["sample_size_thresholds"]
        expected_selected_split = (
            (result["selected_backtest_result"] or result["backtest_result"])["metadata"]["train_test_split"]
        )
        self.assertEqual(
            trading_status["out_of_sample_result_reason"],
            expected_selected_thresholds["out_of_sample_result_reason"],
        )
        self.assertEqual(
            trading_status["out_of_sample_coverage_status"],
            expected_selected_thresholds["out_of_sample_coverage_status"],
        )
        self.assertEqual(
            trading_status["oos_trade_pairs_count"],
            expected_selected_split["oos_trade_pairs_count"],
        )
        self.assertEqual(
            trading_status["min_promotable_oos_trade_pairs"],
            expected_selected_split["min_promotable_oos_trade_pairs"],
        )
        self.assertEqual(
            trading_status["oos_promotion_ready"],
            expected_selected_thresholds["promotion_ready"],
        )
        self.assertIn("candidate_history_snapshots", result["self_evolution_log"]["metrics"])
        self.assertEqual(len(result["self_evolution_log"]["metrics"]["candidate_history_snapshots"]), 3)
        self.assertTrue(
            all(
                "sample_consistency" in item and "governance_primary_reason" in item and "governance_rule_summary" in item
                for item in result["self_evolution_log"]["metrics"]["candidate_history_snapshots"]
            )
        )
        self.assertEqual(len(result["candidate_validations"]), 3)
        self.assertEqual(len(result["candidate_strategies"]), 3)
        self.assertEqual(len(result["candidate_backtests"]), 3)
        self.assertTrue(all(item["governance_action"] in {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"} for item in result["candidate_validations"]))
        vwap_candidate = next(item for item in result["candidate_strategies"] if item["name"] == "VWAP Proxy Research v0.1")
        self.assertEqual(vwap_candidate["metadata"]["queue_type"], "ResearchQueue")
        self.assertEqual(vwap_candidate["metadata"]["scaffold_mode"], "daily_proxy")
        self.assertFalse(vwap_candidate["metadata"]["tradable"])
        self.assertIn(result["strategy_comparison"]["selection_status"], {"selected", "abstain"})
        self.assertIn("scorecard", result["strategy_comparison"])
        self.assertEqual(len(result["strategy_comparison"]["scorecard"]), 3)
        self.assertIn("scorecard_summary", result["strategy_comparison"])
        self.assertIn("governance_rollup", result["strategy_comparison"])
        self.assertTrue(
            {
                "retire_watch",
                "downgrade_watch",
            }.intersection(result["strategy_comparison"]["governance_rollup"]["bucket_counts"])
        )
        self.assertIn("governance_actions", result["strategy_comparison"])
        self.assertTrue(result["strategy_comparison"]["governance_actions"]["bucket_actions"])
        self.assertTrue(
            any(
                item["quality_action"] in {"retire", "downgrade", "rewrite", "freeze", "keep", "needs_review"}
                for item in result["strategy_comparison"]["governance_actions"]["by_strategy"]
            )
        )
        self.assertEqual(
            [item["rank"] for item in result["strategy_comparison"]["scorecard"]],
            [1, 2, 3],
        )
        self.assertTrue(
            any(item["strategy_name"] == "Breakout v0.1" for item in result["strategy_comparison"]["scorecard"])
        )
        self.assertEqual(result["decision_record"]["context"]["a_share_semantics"]["market"], "CN-A")
        self.assertEqual(result["decision_record"]["context"]["a_share_proxy_snapshot"]["proxy_status"], "Experimental")
        self.assertIn("preferred_action", result["decision_record"]["context"]["a_share_proxy_guard"])
        self.assertIn("true_ddx_ddy_context_missing", result["forecast_record"]["invalidation_conditions"])
        self.assertIn("cn_a_t1_proxy_context", result["forecast_record"]["risk_exposure"])
        if all(item["governance_action"] != "keep" for item in result["strategy_comparison"]["candidates"]):
            self.assertEqual(result["strategy_comparison"]["selection_status"], "abstain")
            self.assertEqual(result["strategy_comparison"]["selected_strategy_id"], "")
            self.assertEqual(result["strategy_comparison"]["selected_strategy_name"], "NO_TRADE")
            self.assertEqual(result["strategy_comparison"]["portfolio_action"], "no_trade")
            self.assertEqual(result["decision_record"]["action"], "no_trade")
            self.assertEqual(result["trade_decision"]["action"], "no_trade")
            self.assertIn("selection=abstain", result["trade_journal"]["summary"])
            self.assertIn("A-share T+1 proxy context remains active", result["trade_journal"]["summary"])
            self.assertIn("Seasoned/Fresh is proxy-only", result["trade_journal"]["summary"])
            self.assertIn(result["trade_journal"]["status"], {"Frozen", "Retired"})
        else:
            self.assertEqual(result["strategy_comparison"]["selection_status"], "selected")
            self.assertTrue(result["strategy_comparison"]["selected_strategy_id"])
            self.assertEqual(result["strategy_comparison"]["portfolio_action"], "trade")
            self.assertEqual(result["decision_record"]["action"], "trade")
            self.assertEqual(result["trade_decision"]["action"], "trade")
            self.assertIn("selection=selected", result["trade_journal"]["summary"])
            self.assertIn("A-share T+1 proxy context remains active", result["trade_journal"]["summary"])
            self.assertIn("Seasoned/Fresh is proxy-only", result["trade_journal"]["summary"])

        status = brain.status()
        self.assertGreater(status["counts"]["market_data_records"], 0)
        self.assertGreater(status["counts"]["price_bars"], 0)
        self.assertGreater(status["counts"]["feature_sets"], 0)
        self.assertGreater(status["counts"]["backtest_results"], 0)
        self.assertGreater(status["counts"]["validation_reports"], 0)
        self.assertGreater(status["counts"]["trade_journals"], 0)
        self.assertEqual(status["module_status"]["trading_domain"], "Implemented")
        self.assertEqual(status["module_status"]["trading_a_share_true_money_flow_readiness"], "Implemented")
        self.assertEqual(status["module_status"]["live_trading"], "Not Implemented Yet")

    def test_trade_breakdown_summary_pairs_raw_recent_trades_without_blank_pairs(self):
        summary = TradingDomainV01._trade_breakdown_summary(
            "train",
            {
                "recent_trades": [
                    {"date": "2026-05-01", "side": "buy", "price": 10.0},
                    {"date": "2026-05-03", "side": "sell", "price": 10.5, "reason": "cross_exit"},
                    {"date": "2026-05-04", "side": "buy", "price": 10.2},
                    {"date": "2026-05-05", "side": "sell", "price": 10.0, "reason": "stop_loss"},
                ]
            },
        )

        self.assertEqual(summary["recent_pairs_count"], 2)
        self.assertEqual(summary["win_count"], 1)
        self.assertEqual(summary["loss_count"], 1)
        self.assertEqual(summary["latest_exit"], "2026-05-05")
        self.assertEqual(summary["latest_exit_reason"], "stop_loss")
        self.assertTrue(all("->" in item for item in summary["recent_pair_summaries"]))
        self.assertTrue(all("->:" not in item for item in summary["recent_pair_summaries"]))
        self.assertIn("2026-05-01->2026-05-03", summary["recent_pair_summaries"][0])
    def test_trading_replay_keeps_research_only_risk_gate(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
            "position_pct": 0.2,
        })
        risk_check = result["risk_check_result"]
        decision = result["decision_record"]

        self.assertTrue(risk_check["research_mode"])
        self.assertFalse(risk_check["live_trading_enabled"])
        self.assertIn(decision["action"], {"trade", "wait", "no_trade"})
        self.assertIn(result["validation_report"]["validation_status"], {"pass", "needs_review"})
        self.assertEqual(result["strategy_review"]["action_recommendation"], result["validation_report"]["governance_action"])
        self.assertIn(result["strategy_review"]["action_recommendation"], {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"})
        self.assertTrue(all(item["governance_action"] in {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"} for item in result["strategy_comparison"]["candidates"]))
        self.assertIn(result["strategy_comparison"]["selection_governance_action"], {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"})
        self.assertEqual(
            result["strategy_comparison"]["selected_candidate_name"],
            result["strategy_comparison"]["selected_strategy_name"],
        )

    def test_trading_replay_a_share_redline_blocks_opening_window_trade_and_writes_trace(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
            "requested_action": "trade",
            "quote_ts": "2026-07-14T09:35:00+08:00",
            "market_trend": "TREND_DOWN",
            "has_base_position": False,
            "is_t_trade": False,
            "day_loss_pct": -0.03,
        })

        risk_check = result["risk_check_result"]
        redline = risk_check["metadata"]["a_share_redline_check"]
        blocked_rule_keys = {item["rule_key"] for item in redline["blocked_rules"]}
        self.assertTrue(redline["blocks_action"])
        self.assertEqual(risk_check["action"], "no_trade")
        self.assertFalse(risk_check["allowed"])
        self.assertIn("a_share_redline_opening_30m_no_new_buy", blocked_rule_keys)
        self.assertIn("a_share_redline_downtrend_chase_buy", blocked_rule_keys)
        self.assertIn("a_share_redline_daily_loss_circuit_breaker", blocked_rule_keys)
        self.assertIn("a_share_trade_redline_checked", result["validation_report"]["checks"])
        self.assertTrue(result["validation_report"]["metadata"]["a_share_redline_check"]["blocks_action"])
        self.assertIn("A-share trade redline check:", " ".join(result["strategy_review"]["lessons"]))
        self.assertIn("Redline summary:", result["trade_journal"]["summary"])
        self.assertTrue(result["trade_journal"]["metadata"]["a_share_redline_check"]["blocks_action"])
        self.assertTrue(result["decision_record"]["context"]["a_share_redline_check"]["blocks_action"])
        self.assertTrue(result["trade_decision"]["metadata"]["a_share_redline_check"]["blocks_action"])

    def test_resolve_data_path_prefers_symbol_matched_real_history_before_sample_csv(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "qclaw-output").mkdir(parents=True, exist_ok=True)
        (root / "qclaw-output" / "finance-sample-bars.csv").write_text(
            textwrap.dedent(SAMPLE_CSV),
            encoding="utf-8",
        )
        (root / "data" / "kl_300418_1y.json").write_text(
            '[{"date":"2026-01-02","open":10,"high":11,"low":9.8,"close":10.5,"volume":1000}]',
            encoding="utf-8",
        )

        brain = SuperBrainV01(root)
        resolved = brain.trading._resolve_data_path("", symbol="300418")

        self.assertEqual(resolved, root / "data" / "kl_300418_1y.json")

    def test_real_replay_default_symbol_uses_real_history_and_runs_oos_split(self):
        if not REAL_REPLAY_JSON.exists():
            self.skipTest("real replay json is not available in this workspace")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "data").mkdir(parents=True, exist_ok=True)
        (root / "qclaw-output").mkdir(parents=True, exist_ok=True)
        (root / "data" / REAL_REPLAY_JSON.name).write_text(
            REAL_REPLAY_JSON.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (root / "qclaw-output" / "finance-sample-bars.csv").write_text(
            textwrap.dedent(SAMPLE_CSV),
            encoding="utf-8",
        )

        brain = SuperBrainV01(root)
        result = brain.trading_replay({"symbol": "300418"})

        self.assertEqual(result["market_data_record"]["record_path"], str(root / "data" / REAL_REPLAY_JSON.name))
        self.assertGreaterEqual(result["market_data_record"]["bar_count"], 200)
        self.assertIn(
            result["validation_report"]["out_of_sample_result"],
            {"pass", "fail"},
        )
        sample_compare = result["validation_report"]["metadata"]["sample_comparison"]
        self.assertIn(
            sample_compare["consistency"],
            {"aligned", "train_stronger_than_test", "oos_stronger_than_train", "diverged"},
        )
        self.assertEqual(result["decision_record"]["action"], result["strategy_comparison"]["portfolio_action"])
        self.assertEqual(result["trade_decision"]["action"], result["strategy_comparison"]["portfolio_action"])
        self.assertEqual(result["replay_summary"]["symbol"], "300418")
        self.assertEqual(result["replay_summary"]["market"], "CN-A")
        self.assertEqual(
            result["replay_summary"]["selected_candidate_summary"]["selected_candidate_name"],
            result["strategy_comparison"]["selected_candidate_name"],
        )
        self.assertEqual(
            result["selected_candidate_summary"]["portfolio_action"],
            result["strategy_comparison"]["portfolio_action"],
        )
        if result["strategy_comparison"]["selection_status"] == "selected":
            self.assertIsNotNone(result["selected_strategy_definition"])
            self.assertEqual(
                result["selected_strategy_definition"]["name"],
                result["strategy_comparison"]["selected_strategy_name"],
            )
            self.assertEqual(
                result["selected_validation_report"]["target_id"],
                result["selected_strategy_definition"]["id"],
            )
        else:
            self.assertIsNone(result["selected_strategy_definition"])
            self.assertIsNone(result["selected_backtest_result"])
            self.assertIsNone(result["selected_validation_report"])
            self.assertEqual(result["strategy_comparison"]["selected_candidate_name"], "NO_TRADE")
        self.assertIn(result["skill_registry_entry"]["out_of_sample_result"], {"pass", "fail", "not_run"})
        self.assertIn("a_share_proxy_guard", result["skill_registry_entry"]["metadata"])
        board = brain.board_status()
        recent = board["recent_events"][-1]["summary"]
        self.assertTrue(recent)
        self.assertIn("T+1", recent)
        self.assertIn("out_of_sample", recent)
        self.assertIn("freeze_candidate", recent)
        self.assertEqual(
            board["trading_status"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertEqual(
            board["latest_trading_replay_bulletin_state"]["selection_state_summary"],
            result["strategy_comparison"]["selection_state_summary"],
        )
        self.assertTrue(board["latest_trading_replay_bulletin_state"]["summary"])
        self.assertIn("Train/OOS snapshot:", board["latest_trading_replay_bulletin_state"]["summary"])
        if result["strategy_comparison"]["selection_governance_action"] == "retire_candidate":
            self.assertEqual(board["latest_trading_bulletin_state"]["queue_type"], "ResearchQueue")
            self.assertEqual(board["latest_trading_bulletin_state"]["candidate_slug"], "vwap")
            self.assertEqual(board["latest_trading_bulletin_state"]["status"], "Experimental")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["queue_type"], "ResearchQueue")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["candidate_slug"], "vwap")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["approval_status"], "pending_evidence")
            self.assertFalse(board["latest_trading_research_queue_bulletin_state"]["can_submit_now"])
            self.assertIn("consistency_guard", board["latest_trading_research_queue_bulletin_state"]["missing_keys"])
            self.assertGreaterEqual(board["latest_trading_research_queue_bulletin_state"]["ready_count"], 0)
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["total_count"], 7)
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selection_status"], "abstain")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selection_governance_action"], "needs_review")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["portfolio_action"], "no_trade")
            self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selected_strategy_name"], "NO_TRADE")
            self.assertTrue(board["latest_trading_research_queue_bulletin_state"]["upgrade_candidate_status"])
            self.assertTrue(board["latest_trading_research_queue_bulletin_state"]["freeze_candidate_status"])
            self.assertTrue(board["latest_trading_research_queue_bulletin_state"]["sync_source"])
            self.assertEqual(
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"]["primary_gate"],
                board["latest_trading_research_queue_bulletin_state"]["primary_gate"],
            )
            self.assertEqual(
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"]["queue_recommendation"],
                board["latest_trading_research_queue_bulletin_state"]["queue_recommendation"],
            )
            self.assertTrue(board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"])
            self.assertIn(
                "recommendation=",
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"],
            )
            self.assertIn(
                "primary_gate=",
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"],
            )
            self.assertEqual(status["trading_status"]["focus_source"], "latest_trading_research_queue_bulletin_state")
            self.assertEqual(status["trading_status"]["queue_type"], "ResearchQueue")
            self.assertEqual(status["trading_status"]["candidate_slug"], "vwap")
            self.assertEqual(status["trading_status"]["status"], "Experimental")
            self.assertEqual(status["trading_status"]["validation_status"], "needs_review")
            self.assertEqual(status["trading_status"]["out_of_sample_result"], "pass")
            self.assertIn(
                status["trading_status"]["out_of_sample_coverage_status"],
                {"not_run", "insufficient", "thin_pass", "sufficient"},
            )
            self.assertIn("out_of_sample_result_reason", status["trading_status"])
            self.assertIn("oos_trade_pairs_count", status["trading_status"])
            self.assertIn("min_promotable_oos_trade_pairs", status["trading_status"])
            self.assertIn("oos_promotion_ready", status["trading_status"])
            self.assertEqual(status["trading_status"]["selection_governance_action"], "needs_review")
            self.assertEqual(status["trading_status"]["portfolio_action"], "no_trade")
            self.assertEqual(
                status["trading_status"]["selection_state_summary"],
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"],
            )
            self.assertEqual(
                status["latest_trading_bulletin_state"]["candidate_slug"],
                board["latest_trading_bulletin_state"]["candidate_slug"],
            )
            self.assertEqual(
                status["latest_trading_research_queue_bulletin_state"]["candidate_slug"],
                board["latest_trading_research_queue_bulletin_state"]["candidate_slug"],
            )
            self.assertEqual(
                status["latest_trading_research_queue_bulletin_state"]["selection_state_summary"],
                board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"],
            )
            self.assertIn(
                status["latest_trading_research_queue_bulletin_state"]["replay_variant_governance_priority_action"],
                {"continue_targeted_replay", "collect_more_variants", "watch_only", "no_trade"},
            )
            self.assertTrue(
                status["latest_trading_research_queue_bulletin_state"]["replay_variant_governance_summary"]
            )
            self.assertIn(
                status["latest_trading_research_queue_bulletin_state"]["a_share_proxy_preferred_action"],
                {"no_trade", "watch", "wait", "research_only"},
            )
            self.assertTrue(status["latest_trading_research_queue_bulletin_state"]["a_share_proxy_summary"])
        else:
            self.assertEqual(board["latest_trading_bulletin_state"]["queue_type"], "")
            self.assertEqual(board["latest_trading_bulletin_state"]["selection_governance_action"], "freeze")
            self.assertEqual(board.get("latest_trading_research_queue_bulletin_state", {}), {})

    def test_recommended_replay_variant_prefers_coverage_probe_when_oos_pairs_are_thin(self):
        selected = TradingDomainV01._recommended_replay_variant_template(
            replay_variant_templates=[
                {
                    "variant_key": "risk_compare_same_signal_quality",
                    "label": "保留信号只查风险质量",
                },
                {
                    "variant_key": "risk_split_coverage_probe",
                    "label": "给样本外更多覆盖",
                },
            ],
            latest_variant_key="risk_compare_same_signal_quality",
            latest_execution_outcome_status="ready",
            latest_variant_focus_status="",
            target_gap_snapshot={
                "primary_driver": "risk_score_gap",
                "secondary_driver": "trades_count_gap",
            },
            latest_out_of_sample_result="pass",
            latest_out_of_sample_reason="oos_trade_pairs_below_minimum",
            latest_out_of_sample_coverage_status="thin_pass",
            latest_oos_trade_pairs_count=1,
            latest_min_promotable_oos_trade_pairs=2,
            latest_oos_promotion_ready=False,
        )

        self.assertEqual(selected["variant_key"], "risk_split_coverage_probe")
        self.assertIn("out-of-sample coverage is still too thin", selected["selection_reason"])
        self.assertIn("pairs=1/2", selected["selection_reason"])
        self.assertIn("coverage=thin_pass", selected["selection_reason"])

    def test_recommended_replay_variant_rotates_when_latest_variant_worsened_vs_previous(self):
        selected = TradingDomainV01._recommended_replay_variant_template(
            replay_variant_templates=[
                {
                    "variant_key": "risk_compare_same_signal_quality",
                    "label": "保留信号只查风险质量",
                },
                {
                    "variant_key": "risk_split_coverage_probe",
                    "label": "给样本外更多覆盖",
                },
            ],
            latest_variant_key="risk_compare_same_signal_quality",
            latest_execution_outcome_status="mixed",
            latest_variant_focus_status="quality_gap_persists",
            target_gap_snapshot={
                "primary_driver": "risk_score_gap",
                "secondary_driver": "drawdown_gap",
            },
            latest_out_of_sample_result="fail",
            latest_out_of_sample_reason="oos_failed_after_variant_rerun",
            latest_out_of_sample_coverage_status="sufficient",
            latest_oos_trade_pairs_count=3,
            latest_min_promotable_oos_trade_pairs=2,
            latest_oos_promotion_ready=False,
            latest_candidate_vs_previous_variant_status="worsened",
            latest_candidate_vs_previous_variant_oos_shift="worsened",
        )

        self.assertEqual(selected["variant_key"], "risk_split_coverage_probe")
        self.assertIn("worsened versus the previous replay route", selected["selection_reason"])
        self.assertIn("oos_shift=worsened", selected["selection_reason"])

    def test_recommended_replay_variant_keeps_same_route_when_latest_variant_improved_vs_previous(self):
        selected = TradingDomainV01._recommended_replay_variant_template(
            replay_variant_templates=[
                {
                    "variant_key": "risk_compare_same_signal_quality",
                    "label": "保留信号只查风险质量",
                },
                {
                    "variant_key": "risk_split_coverage_probe",
                    "label": "给样本外更多覆盖",
                },
            ],
            latest_variant_key="risk_compare_same_signal_quality",
            latest_execution_outcome_status="improved",
            latest_variant_focus_status="quality_metrics_stabilized",
            target_gap_snapshot={
                "primary_driver": "risk_score_gap",
                "secondary_driver": "drawdown_gap",
            },
            latest_out_of_sample_result="pass",
            latest_out_of_sample_reason="oos_still_needs_more_evidence",
            latest_out_of_sample_coverage_status="sufficient",
            latest_oos_trade_pairs_count=2,
            latest_min_promotable_oos_trade_pairs=2,
            latest_oos_promotion_ready=False,
            latest_candidate_vs_previous_variant_status="improved",
            latest_candidate_vs_previous_variant_oos_shift="improved",
        )

        self.assertEqual(selected["variant_key"], "risk_compare_same_signal_quality")
        self.assertIn("improved relative to the previous replay route", selected["selection_reason"])

    def test_trading_replay_attaches_tdx_true_money_flow_sample_without_overclaiming_connection(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
            "ddx": 0.699,
            "ddy": 1.85,
            "change_pct": 5.13,
            "volume_ratio": 1.92,
            "price": 50.42,
            "turnover_rate": 14.3,
            "quote_ts": "2026-07-09T14:30:00+08:00",
        })

        self.assertTrue(result["a_share_context"]["true_money_flow_sample_attached"])
        self.assertEqual(result["a_share_context"]["true_money_flow_sample_status"], "Experimental")
        self.assertFalse(result["a_share_context"]["true_money_flow_connected"])
        self.assertFalse(result["a_share_context"]["ddx_ddy_connected"])
        self.assertEqual(result["true_money_flow_snapshot"]["provider"], "tdx_realtime_quotes")
        self.assertEqual(result["true_money_flow_snapshot"]["connection_mode"], "payload_injected_sample")
        self.assertIn("true_money_flow_sample_payload_attached", result["a_share_context"]["warnings"])
        self.assertIn("tdx_true_money_flow_sample_attached", result["validation_report"]["checks"])
        self.assertEqual(
            result["validation_report"]["metadata"]["a_share_semantics"]["true_money_flow_snapshot"]["ddx"],
            0.699,
        )
        self.assertEqual(
            result["decision_record"]["context"]["true_money_flow_snapshot"]["ddy"],
            1.85,
        )
        self.assertIn("payload_true_money_flow_sample", result["forecast_record"]["risk_exposure"])
        self.assertIn(
            "payload_true_money_flow_sample_conflicts_with_proxy_or_selection",
            result["forecast_record"]["invalidation_conditions"],
        )
        self.assertIn("payload TDX sample attached", result["trade_journal"]["summary"])
        self.assertIn(
            "true_money_flow_sample_assessment",
            result["validation_report"]["metadata"],
        )
        self.assertIn(
            "True money-flow sample assessment:",
            "\n".join(result["strategy_review"]["lessons"]),
        )
        self.assertEqual(
            len(result["strategy_comparison"]["candidates"]),
            3,
        )
        self.assertTrue(
            all(
                "true_money_flow_sample_assessment" in item
                and item["true_money_flow_sample_assessment"].get("summary")
                for item in result["strategy_comparison"]["candidates"]
            )
        )
        self.assertTrue(
            all(
                "true_money_flow_sample_support" in item
                and "true_money_flow_sample_summary" in item
                for item in result["self_evolution_log"]["metrics"]["candidate_history_snapshots"]
            )
        )
        self.assertIn("True-money-flow sample context:", result["strategy_comparison"]["selection_reason"])
        board = brain.board_status()
        recent = board["recent_events"][-1]["summary"]
        self.assertTrue("TDX" in recent or "true-money-flow" in recent.lower())
        self.assertIn("payload injected Experimental", recent)

    def test_small_sample_replay_marks_sample_size_guard(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })

        sample_size_thresholds = result["validation_report"]["metadata"]["sample_size_thresholds"]
        self.assertTrue(sample_size_thresholds["total_bars_triggered"])
        self.assertTrue(sample_size_thresholds["completed_trade_pairs_triggered"] or sample_size_thresholds["oos_trade_pairs_triggered"])
        self.assertTrue(sample_size_thresholds["blocks_promotion"])
        self.assertEqual(sample_size_thresholds["zero_trade_pairs_reason_key"], "no_completed_pairs_in_train_or_oos")
        self.assertIn("没有形成已完成成交对", sample_size_thresholds["zero_trade_pairs_summary"])
        self.assertGreaterEqual(len(sample_size_thresholds["likely_causes"]), 1)
        self.assertIn("sample_total_bars_below_minimum", result["validation_report"]["warnings"])
        self.assertIn("completed_trade_pairs_below_minimum", result["validation_report"]["warnings"])
        self.assertTrue(result["validation_report"]["metadata"]["downgrade_thresholds"]["sample_size_total_bars_triggered"])
        self.assertTrue(
            any(
                item["rule_key"] == "sample_size_guard" and item["triggered"]
                for item in result["validation_report"]["metadata"]["governance_rule_snapshot"]["rule_evaluations"]
            )
        )

    def test_sample_size_zero_trade_pairs_preview_prefers_density_probe_variant(self):
        brain, _sample = self.make_brain_with_data()
        preview = brain.trading._validation_task_preview(
            candidate_slug="vwap",
            candidate_name="VWAP Research Slice v0.1",
            primary_blocker_key="sample_size_guard_clear",
            target_gap_snapshot={
                "primary_driver": "none",
                "primary_driver_label": "涓€鑷存€у凡婊¤冻",
                "secondary_driver": "none",
                "secondary_driver_label": "鏃犳槑鏄炬绾ф嫋绱」",
                "driver_detail_summary": "No secondary consistency drag item is currently above threshold.",
                "target_test_return_min": 0.0,
                "target_test_score_min": 0.0,
                "return_gap_to_close": 0.0,
                "score_gap_to_close": 0.0,
            },
            normalized_follow_up_plan=["Add more bars / completed_trade_pairs / oos_trade_pairs so the sample-size gate can stop blocking promotion."],
            queue_recommendation="stay_experimental_watch_gap",
            sample_size_diagnostics={
                "blocked": True,
                "bars_count": 249,
                "completed_trade_pairs": 0,
                "oos_completed_trade_pairs": 0,
                "zero_trade_pairs_reason_key": "no_completed_pairs_in_train_or_oos",
                "zero_trade_pairs_summary": "Current train and out-of-sample windows do not yet contain completed trade pairs.",
                "likely_causes": [
                    "Signals are too sparse in the current window to form closed entry-exit pairs.",
                    "The train / out-of-sample split windows are still too short after the current split.",
                ],
            },
        )

        hints = preview["replay_adjustment_hints"]
        self.assertEqual(hints["primary_driver"], "sample_size_zero_trade_pairs")
        self.assertTrue(hints["primary_driver_label"])
        self.assertEqual(hints["suggested_variants"][0]["variant_key"], "sample_size_signal_density_probe")
        self.assertEqual(hints["suggested_variants"][1]["variant_key"], "sample_size_split_coverage_probe")
        self.assertEqual(hints["suggested_variants"][0]["changes"]["vwap_window"], 12)
        self.assertEqual(hints["suggested_variants"][0]["changes"]["vwap_entry_deviation"], 0.008)
        self.assertIn("闆舵垚浜ゅ", hints["summary"])
        self.assertIn("淇″彿瑙﹀彂娆℃暟", hints["priority_checks"][0])
        self.assertEqual(preview["task_status"], "ready_for_next_validation_slice")

    def test_proxy_guard_preview_prefers_real_data_clearance_hints(self):
        brain, _sample = self.make_brain_with_data()
        preview = brain.trading._validation_task_preview(
            candidate_slug="vwap",
            candidate_name="VWAP Research Slice v0.1",
            primary_blocker_key="a_share_proxy_guard_clear",
            target_gap_snapshot={
                "primary_driver": "oos_strength",
                "primary_driver_label": "鏍锋湰澶栧己浜庢牱鏈唴",
                "secondary_driver": "none",
                "secondary_driver_label": "鏃犳槑鏄炬绾ф嫋绱」",
                "driver_detail_summary": "The current consistency gate is not the active blocker for promotion.",
                "target_test_return_min": 0.2404,
                "target_test_score_min": 160.95,
                "return_gap_to_close": 0.0,
                "score_gap_to_close": 0.0,
            },
            normalized_follow_up_plan=["Attach true DDX/DDY or a stronger replacement evidence route before clearing the A-share proxy guard."],
            queue_recommendation="stay_experimental",
            proxy_guard_diagnostics={
                "priority_source_key": "tdx_realtime_quotes",
                "priority_source_label": "TDX realtime quotes",
                "priority_required_fields": ["ddx", "ddy", "change_pct", "volume_ratio"],
                "route_plan_summary": "1.TDX realtime quotes[attached_ready] -> 2.Tencent qt / custom stock MCP[attached_ready]",
                "historical_baseline_summary": "WeStock historical baseline is attached, but it still lacks an explicit ddx field and cannot replace true DDX/DDY.",
                "route_plan_steps": [
                    {
                        "source_key": "tdx_realtime_quotes",
                        "label": "TDX realtime quotes",
                        "required_fields": ["ddx", "ddy", "change_pct", "volume_ratio"],
                        "connection_status": "Not Implemented Yet",
                        "implementation_status": "Interface",
                        "status": "attached_ready",
                        "sample_quality_status": "sample_attached",
                        "command_hint": 'Start TDX live MCP bridge and call `tdx_realtime {"code": "300418"}`.',
                        "route_summary": "Official TDX MCP realtime quotes should remain the first route for true DDX/DDY, change_pct, and volume_ratio fields.",
                    }
                ],
            },
        )

        hints = preview["replay_adjustment_hints"]
        self.assertEqual(hints["primary_driver"], "a_share_proxy_guard_clear")
        self.assertEqual(hints["primary_driver_label"], "A股代理守门未清关")
        self.assertEqual(hints["suggested_variants"][0]["variant_key"], "baseline_replay_compare")
        self.assertIn("TDX realtime quotes", hints["summary"])
        self.assertIn("ddx", hints["priority_checks"][0])
        self.assertIn("tdx_realtime", hints["priority_checks"][1])
        self.assertIn("WeStock", hints["priority_checks"][2])
        self.assertIn("historical baseline", hints["priority_checks"][2])
        self.assertEqual(preview["task_status"], "ready_for_next_validation_slice")

    def test_proxy_guard_next_validation_note_prefers_route_plan_over_gap_text(self):
        note = TradingDomainV01._next_validation_slice_note(
            candidate_name="VWAP Research Slice v0.1",
            primary_blocker_key="a_share_proxy_guard_clear",
            target_gap_snapshot={
                "target_test_return_min": 0.2404,
                "target_test_score_min": 160.95,
                "return_gap_to_close": 0.0,
                "score_gap_to_close": 0.0,
            },
            normalized_follow_up_plan=["Attach true DDX/DDY or a stronger replacement evidence route before clearing the A-share proxy guard."],
            proxy_guard_diagnostics={
                "sample_attached_count": 5,
                "priority_sample_status": "sample_available",
                "priority_sample_connection_mode": "payload_injected_sample",
                "priority_source_label": "TDX realtime quotes",
                "priority_required_fields": ["ddx", "ddy", "change_pct", "volume_ratio"],
                "route_plan_summary": "1.TDX realtime quotes[attached_ready] -> 2.Tencent qt / custom stock MCP[attached_ready]",
                "historical_baseline_summary": "WeStock historical baseline is attached, but it still lacks an explicit ddx field and cannot replace true DDX/DDY.",
            },
        )

        self.assertTrue(note)
        self.assertIn("TDX realtime quotes", note)
        self.assertIn("ddx, ddy, change_pct, volume_ratio", note)
        self.assertIn("1.TDX realtime quotes[attached_ready]", note)
        self.assertIn("sample", note)
        self.assertNotIn("test_return", note)
        self.assertNotIn("test_score", note)

    def test_proxy_guard_consistency_plan_uses_real_data_clearance_language(self):
        plan = TradingDomainV01._consistency_guard_plan(
            candidate_name="VWAP Research Slice v0.1",
            primary_blocker_key="a_share_proxy_guard_clear",
            target_gap_snapshot={
                "primary_driver": "oos_strength",
                "primary_driver_label": "鏍锋湰澶栧己浜庢牱鏈唴",
                "secondary_driver_label": "鏃犳槑鏄炬绾ф嫋绱」",
                "return_gap_to_close": 0.0,
                "score_gap_to_close": 0.0,
            },
            validation_task_preview={
                "task_status": "ready_for_next_validation_slice",
                "required_actions": ["Attach true DDX/DDY or a stronger replacement evidence route before clearing the A-share proxy guard."],
                "replay_adjustment_hints": {
                    "primary_driver": "a_share_proxy_guard_clear",
                    "primary_driver_label": "A鑲′唬鐞嗗畧闂ㄦ湭娓呭叧",
                    "secondary_driver_label": "鐪熷疄璧勯噾閾句粛闇€鏍搁獙",
                    "suggested_variants": [
                        {
                            "variant_key": "baseline_replay_compare",
                            "label": "Keep the baseline replay for comparison first",
                            "changes": {},
                            "why": "Verify the real-data route before changing more strategy parameters.",
                        }
                    ],
                    "priority_checks": [
                        "Verify that TDX realtime quotes really supply ddx, ddy, change_pct, and volume_ratio."
                    ],
                },
            },
            normalized_follow_up_plan=["Attach true DDX/DDY or a stronger replacement evidence route before clearing the A-share proxy guard."],
            next_validation_slice_note="The next validation slice should clear the A-share proxy guard for VWAP Research Slice v0.1 first.",
        )

        self.assertEqual(plan["blocker_key"], "a_share_proxy_guard_clear")
        self.assertEqual(plan["primary_driver"], "a_share_proxy_guard_clear")
        self.assertTrue(plan["summary"])
        self.assertIn("baseline", plan["summary"].lower())
        self.assertIn("TDX realtime quotes", plan["summary"])
        self.assertNotIn("return_gap=", plan["summary"])
        self.assertNotIn("score_gap=", plan["summary"])

    def test_research_queue_scaffold_oos_pass_suppresses_history_only_retire(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        thresholds = brain.trading._retire_candidate_thresholds(
            split_summary={"out_of_sample_result": "pass"},
            warnings=["train_test_gap_large", "research_queue_daily_proxy_only"],
            historical_failure_count=12,
            is_research_queue_candidate=True,
            scaffold_mode="daily_proxy",
        )

        self.assertTrue(thresholds["history_triggered_raw"])
        self.assertTrue(thresholds["history_retire_suppressed"])
        self.assertFalse(thresholds["history_triggered"])
        self.assertFalse(thresholds["oos_fail_with_gap_triggered"])

        action = brain.trading._governance_action(
            effective=False,
            split_summary={"out_of_sample_result": "pass"},
            warnings=["train_test_gap_large", "research_queue_daily_proxy_only"],
            failure_count=1,
            historical_failure_count=12,
            is_research_queue_candidate=True,
            scaffold_mode="daily_proxy",
        )
        self.assertEqual(action, "needs_review")

    def test_research_queue_watch_gap_overrides_stale_retire_candidate_bucket(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        effective_action = brain.trading._research_queue_effective_governance_action(
            queue_recommendation="stay_experimental_watch_gap",
            primary_gate="scaffold",
            freeze_candidate_status="watch_consistency_gap",
            latest_action="retire_candidate",
        )
        self.assertEqual(effective_action, "needs_review")

        bucket = brain.trading._research_queue_effective_state_bucket(
            queue_recommendation="stay_experimental_watch_gap",
            primary_gate="scaffold",
            freeze_candidate_status="watch_consistency_gap",
            latest_action=effective_action,
            latest_out_of_sample_result="pass",
            current_failure_streak=12,
            sample_consistency="train_stronger_than_test",
            workbuddy_constraint_blocked=True,
        )
        self.assertEqual(bucket, "consistency_watch")

        scorecard = brain.trading._apply_research_queue_overrides_to_parallel_scorecard(
            scorecard=[
                {
                    "strategy_id": "strat_vwap",
                    "strategy_name": "VWAP Proxy Research v0.1",
                    "governance_action": "retire_candidate",
                    "out_of_sample_result": "pass",
                    "failure_count": 12,
                    "sample_consistency": "train_stronger_than_test",
                    "freeze_candidate_status": "watch_consistency_gap",
                    "workbuddy_constraint_blocked": True,
                }
            ],
            research_queue_candidates=[
                {
                    "candidate_slug": "vwap",
                    "queue_recommendation": "stay_experimental_watch_gap",
                    "primary_gate": "scaffold",
                    "freeze_candidate_status": "watch_consistency_gap",
                }
            ],
        )
        self.assertEqual(scorecard[0]["governance_action"], "retire_candidate")

        override_scorecard = brain.trading._apply_research_queue_overrides_to_parallel_scorecard(
            scorecard=[
                {
                    "strategy_id": "strat_vwap",
                    "strategy_name": "VWAP Proxy Research v0.1",
                    "governance_action": "retire_candidate",
                    "out_of_sample_result": "pass",
                    "failure_count": 12,
                    "sample_consistency": "train_stronger_than_test",
                    "freeze_candidate_status": "watch_consistency_gap",
                    "workbuddy_constraint_blocked": True,
                }
            ],
            research_queue_candidates=[],
        )
        self.assertEqual(override_scorecard[0]["governance_action"], "retire_candidate")

    def test_research_queue_parallel_scorecard_override_updates_governance_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        bundle_stub = {
            "skill_registry_entry": {
                "metadata": {
                    "strategy_id": "strat_vwap",
                    "state_summary": {
                        "queue_recommendation": "stay_experimental_watch_gap",
                        "primary_gate": "scaffold",
                        "freeze_candidate_status": "watch_consistency_gap",
                    },
                }
            }
        }
        original_bundle = brain.trading._latest_research_queue_candidate_validation_bundle
        brain.trading._latest_research_queue_candidate_validation_bundle = lambda candidate_slug: bundle_stub
        self.addCleanup(
            lambda: setattr(
                brain.trading,
                "_latest_research_queue_candidate_validation_bundle",
                original_bundle,
            )
        )

        scorecard = brain.trading._apply_research_queue_overrides_to_parallel_scorecard(
            scorecard=[
                {
                    "strategy_id": "strat_vwap",
                    "strategy_name": "VWAP Proxy Research v0.1",
                    "governance_action": "retire_candidate",
                    "out_of_sample_result": "pass",
                    "failure_count": 12,
                    "sample_consistency": "train_stronger_than_test",
                    "freeze_candidate_status": "watch_consistency_gap",
                    "workbuddy_constraint_blocked": True,
                    "governance_primary_reason": "stale_history_only",
                }
            ],
            research_queue_candidates=[
                {
                    "candidate_slug": "vwap",
                    "queue_recommendation": "stay_experimental_watch_gap",
                    "primary_gate": "scaffold",
                    "freeze_candidate_status": "watch_consistency_gap",
                }
            ],
        )
        self.assertEqual(scorecard[0]["governance_action"], "needs_review")
        self.assertEqual(scorecard[0]["effective_state_bucket"], "consistency_watch")

        rollup = brain.trading._strategy_parallel_governance_rollup(scorecard=scorecard)
        actions = brain.trading._strategy_parallel_governance_actions(
            scorecard=scorecard,
            governance_rollup=rollup,
        )
        self.assertIn("consistency_watch=VWAP Proxy Research v0.1", rollup["summary"])
        self.assertNotIn("downgrade_watch=VWAP Proxy Research v0.1", rollup["summary"])
        self.assertIn("consistency_watch->rewrite(VWAP Proxy Research v0.1)", actions["summary"])
        self.assertNotIn("downgrade_watch->downgrade(VWAP Proxy Research v0.1)", actions["summary"])

    def test_governance_reason_scaffold_does_not_double_block_readiness(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        gap_summary = brain.trading_research_queue_evidence_gap_summary({"candidate_slug": "vwap"})
        row = gap_summary["rows"][0]
        self.assertIn("consistency_guard", row["missing_keys"])
        self.assertIn("scaffold_exit", row["missing_keys"])
        self.assertIn("a_share_proxy_guard_clear", row["missing_keys"])
        self.assertNotIn("governance_reason_clear", row["missing_keys"])

        governance_gap = next(item for item in row["gap_details"] if item["key"] == "governance_reason_clear")
        self.assertFalse(governance_gap["missing"])
        self.assertFalse(governance_gap["diagnostics"]["blocked"])
        self.assertEqual(governance_gap["diagnostics"]["reason_family"], "research_queue_scaffold")

        readiness = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        readiness_row = readiness["rows"][0]
        self.assertEqual(readiness_row["blocked_count"], 3)
        self.assertEqual(readiness_row["review_checklist"]["blocked_steps"], 3)
        self.assertEqual(
            len([item for item in readiness_row["review_checklist"]["items"] if not item["blocked"]]),
            2,
        )
        self.assertNotIn("补充治理说明，消除 research_queue 主原因拦截", readiness_row["normalized_follow_up_plan"])
        self.assertFalse(readiness_row["review_checklist"]["items"][2]["blocked"])
        self.assertEqual(readiness_row["review_checklist"]["items"][2]["status"], "ready")

    def test_sample_size_zero_trade_pairs_payload_template_uses_preview_variants(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        preview = {
            "blocker": "sample_size_guard_clear",
            "required_actions": ["Add more bars / completed_trade_pairs / oos_trade_pairs so the sample-size gate can stop blocking promotion."],
            "proxy_guard_sample_attached_count": 0,
            "proxy_guard_priority_sample_available": False,
            "proxy_guard_priority_sample_status": "",
            "proxy_guard_priority_sample_ts": "",
            "proxy_guard_priority_sample_connection_mode": "",
            "proxy_guard_priority_sample_quality_status": "",
            "replay_adjustment_hints": {
                "primary_driver": "sample_size_zero_trade_pairs",
                "primary_driver_label": "No completed trade pairs in the current sample",
                "secondary_driver_label": "鏃犳槑鏄炬绾ф嫋绱」",
                "suggested_variants": [
                    {
                        "variant_key": "sample_size_signal_density_probe",
                        "label": "鍏堟煡淇″彿瀵嗗害",
                        "changes": {"vwap_window": 12, "vwap_entry_deviation": 0.008},
                        "why": "Increase VWAP trigger density first.",
                    },
                    {
                        "variant_key": "sample_size_split_coverage_probe",
                        "label": "缁欐牱鏈鏇村瑕嗙洊",
                        "changes": {"train_ratio": 0.6, "vwap_window": 16},
                        "why": "Give the out-of-sample side more bars.",
                    },
                ],
                "priority_checks": ["Compare raw signal trigger counts against completed trade-pair counts first."],
                "summary": "The next replay should first address the zero-trade-pair sample-size issue.",
                "implementation_status": "Implemented",
            },
        }
        payload = brain.trading._next_validation_replay_payload_template(
            candidate_slug="vwap",
            validation_task_preview=preview,
            target_gap_snapshot={
                "primary_driver": "none",
                "primary_driver_label": "涓€鑷存€у凡婊¤冻",
                "secondary_driver": "none",
                "secondary_driver_label": "鏃犳槑鏄炬绾ф嫋绱」",
                "driver_details": [],
                "recommended_validation_focus": [],
            },
            a_share_proxy_guard={"blocks_promotion": False},
            sample_size_thresholds={
                "bars_count": 249,
                "blocks_promotion": True,
                "completed_trade_pairs": 0,
                "oos_completed_trade_pairs": 0,
                "zero_trade_pairs_reason_key": "no_completed_pairs_in_train_or_oos",
                "zero_trade_pairs_summary": "No completed trade pairs formed in either train or out-of-sample windows.",
                "likely_causes": ["Strategy signal density is too sparse."],
            },
        )

        self.assertEqual(payload["recommended_variant_key"], "sample_size_signal_density_probe")
        self.assertEqual(payload["replay_variant_templates"][0]["variant_key"], "sample_size_signal_density_probe")
        self.assertEqual(payload["replay_variant_templates"][0]["payload"]["vwap_window"], 12)
        self.assertEqual(payload["replay_variant_templates"][0]["payload"]["vwap_entry_deviation"], 0.008)
        self.assertEqual(payload["sample_size_zero_trade_pairs_reason_key"], "no_completed_pairs_in_train_or_oos")
        self.assertIn("娌℃湁褰㈡垚宸插畬鎴愭垚浜ゅ", payload["sample_size_zero_trade_pairs_summary"])

    def test_trading_replay_marks_vwap_schema_mismatch_on_ddx_series(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        result = brain.trading_replay({
            "data_path": str(REAL_DDX_REPLAY_JSON),
            "symbol": "300418",
        })

        vwap_strategy = next(item for item in result["candidate_strategies"] if item["name"] == "VWAP Proxy Research v0.1")
        vwap_backtest = next(item for item in result["candidate_backtests"] if item["strategy_id"] == vwap_strategy["id"])
        vwap_validation = next(item for item in result["candidate_validations"] if item["target_id"] == vwap_strategy["id"])
        schema = vwap_backtest["metadata"]["market_data_schema_diagnostics"]
        sample_size = vwap_validation["metadata"]["sample_size_thresholds"]

        self.assertEqual(schema["dataset_family"], "fund_flow_series")
        self.assertFalse(schema["volume_ready_for_vwap"])
        self.assertFalse(schema["ohlcv_ready_for_vwap"])
        self.assertEqual(schema["nonzero_volume_bars"], 0)
        self.assertIn("volume", schema["missing_required_fields"])
        self.assertTrue(schema["suggested_ohlcv_dataset_path"].endswith("kl_300418_1y.json"))
        self.assertEqual(sample_size["zero_trade_pairs_reason_key"], "market_data_schema_missing_volume_for_vwap")
        self.assertTrue(sample_size["data_schema_blocked"])
        self.assertIn("鏁版嵁妯″紡涓嶅吋瀹?", sample_size["zero_trade_pairs_summary"])
        self.assertIn("volume", " ".join(sample_size["likely_causes"]))
        self.assertIn("market_data_schema_incompatible_for_vwap", vwap_validation["warnings"])
        self.assertEqual(vwap_backtest["metadata"]["raw_backtest"]["signal_diagnostics"]["valid_vwap_points"], 0)

    def test_research_queue_schema_mismatch_prefers_switching_to_ohlcv_dataset(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_DDX_REPLAY_JSON),
                "symbol": "300418",
            })

        next_slice = brain.trading_research_queue_next_validation_slice({"candidate_slug": "vwap"})
        payload = next_slice["replay_payload_template"]

        self.assertEqual(payload["sample_size_zero_trade_pairs_reason_key"], "market_data_schema_missing_volume_for_vwap")
        self.assertEqual(payload["recommended_variant_key"], "sample_size_switch_ohlcv_dataset")
        self.assertEqual(payload["replay_variant_templates"][0]["variant_key"], "sample_size_switch_ohlcv_dataset")
        self.assertTrue(payload["replay_variant_templates"][0]["payload"]["data_path"].endswith("kl_300418_1y.json"))
        self.assertEqual(
            next_slice["validation_task_preview"]["replay_adjustment_hints"]["primary_driver"],
            "sample_size_dataset_schema_mismatch",
        )
        self.assertIn("鍒囧洖 OHLCV K绾挎牱鏈?", payload["summary"])

    def test_true_money_flow_sample_rank_bonus_prefers_supportive_candidate(self):
        brain, _sample = self.make_brain_with_data()
        candidates = [
            {
                "strategy_id": "a",
                "strategy_name": "Supportive",
                "family": "trend",
                "risk_adjusted_score": 10.0,
                "total_return": 0.05,
                "max_drawdown": -0.02,
                "out_of_sample_result": "pass",
                "governance_action": "keep",
                "true_money_flow_sample_assessment": {
                    "support_level": "supports_trade_bias",
                    "summary": "Supportive sample.",
                },
            },
            {
                "strategy_id": "b",
                "strategy_name": "Conflict",
                "family": "trend",
                "risk_adjusted_score": 10.0,
                "total_return": 0.05,
                "max_drawdown": -0.02,
                "out_of_sample_result": "pass",
                "governance_action": "keep",
                "true_money_flow_sample_assessment": {
                    "support_level": "conflicts_with_trade_bias",
                    "summary": "Conflicting sample.",
                },
            },
        ]

        selection = brain.trading._select_strategy_candidate(candidates)
        self.assertEqual(selection["selection_status"], "selected")
        self.assertEqual(selection["selected_strategy_id"], "a")
        self.assertEqual(selection["selected_candidate_name"], "Supportive")
        self.assertIn("rank_bonus=0.30", selection["selection_reason"])
        self.assertEqual(
            brain.trading._true_money_flow_sample_rank_bonus(
                {"support_level": "supports_trade_bias"}
            ),
            0.3,
        )
        self.assertEqual(
            brain.trading._true_money_flow_sample_rank_bonus(
                {"support_level": "conflicts_with_trade_bias"}
            ),
            -0.3,
        )

    def test_historical_failures_promote_retire_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            result = brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        self.assertEqual(result["strategy_comparison"]["selection_status"], "abstain")
        self.assertEqual(result["strategy_comparison"]["selection_governance_action"], "retire_candidate")
        self.assertEqual(result["strategy_comparison"]["selected_candidate_name"], "NO_TRADE")
        self.assertIsNone(result["selected_strategy_definition"])
        self.assertIsNone(result["selected_backtest_result"])
        self.assertIsNone(result["selected_validation_report"])
        self.assertEqual(result["replay_summary"]["selected_candidate_summary"]["selected_candidate_name"], "NO_TRADE")
        self.assertFalse(result["replay_summary"]["selected_candidate_summary"]["selected_strategy_definition_attached"])
        self.assertEqual(result["selected_candidate_summary"]["out_of_sample_result"], "fail")
        non_vwap_validations = [item for item in result["candidate_validations"] if item["target_id"] != next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1")]
        self.assertTrue(all(item["governance_action"] == "retire_candidate" for item in non_vwap_validations))
        self.assertTrue(all(item["status"] == "Retired" for item in non_vwap_validations))
        self.assertEqual(result["module_status_record"]["quality_action"], "retire_candidate")
        self.assertEqual(result["module_status_record"]["status"], "Active")
        self.assertEqual(result["module_status_record"]["out_of_sample_result"], "fail")
        self.assertEqual(result["skill_registry_entry"]["out_of_sample_result"], "fail")
        self.assertEqual(result["bulletin_state_record"]["out_of_sample_result"], "fail")
        self.assertGreaterEqual(result["module_status_record"]["failure_count"], 1)
        self.assertEqual(result["module_status_record"]["metadata"]["status_scope"], "workflow_runtime")
        self.assertEqual(result["module_status_record"]["metadata"]["selected_strategy_status"], "Retired")
        self.assertIn(
            "latest selected strategy is governed separately",
            result["module_status_record"]["summary"],
        )
        self.assertEqual(result["skill_registry_entry"]["validation_status"], "needs_review")
        self.assertEqual(result["trade_journal"]["status"], "Retired")
        self.assertEqual(result["trade_decision"]["status"], "Retired")
        self.assertIn("A-share proxy guard stayed active", result["strategy_comparison"]["selection_reason"])
        self.assertIsNotNone(result["research_queue_learning_entry"])
        self.assertEqual(result["research_queue_learning_entry"]["entry_type"], "trading_research_queue")
        self.assertEqual(result["research_queue_learning_entry"]["metadata"]["queue_type"], "ResearchQueue")
        self.assertEqual(result["research_queue_learning_entry"]["metadata"]["queue_status"], "pending")
        self.assertIsNotNone(result["research_queue_evolution_log"])
        self.assertEqual(result["research_queue_evolution_log"]["trigger"], "trading_research_queue_learning")
        self.assertIsNotNone(result["research_queue_atom"])
        self.assertEqual(result["research_queue_atom"]["atom_type"], "research_queue")
        self.assertEqual(result["research_queue_atom"]["implementation_status"], "Interface")
        self.assertIn("ResearchQueue", result["research_queue_atom"]["tags"])
        self.assertIsNotNone(result["research_queue_theory_definition"])
        self.assertEqual(result["research_queue_theory_definition"]["implementation_status"], "Interface")
        self.assertEqual(result["research_queue_theory_definition"]["status"], "Experimental")
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["queue_type"], "ResearchQueue")
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["feature_scaffold_status"], "Implemented")
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["scaffold_mode"], "daily_proxy")
        self.assertIsNotNone(result["research_queue_skill_registry_entry"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["skill_name"], "trading.research_queue.vwap_v0_1")
        self.assertEqual(result["research_queue_skill_registry_entry"]["implementation_status"], "Interface")
        self.assertEqual(result["research_queue_skill_registry_entry"]["status"], "Experimental")
        self.assertFalse(result["research_queue_skill_registry_entry"]["metadata"]["tradable"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["feature_scaffold_status"], "Implemented")
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["scaffold_mode"], "daily_proxy")
        self.assertTrue(any(item["name"] == "VWAP Proxy Research v0.1" for item in result["candidate_strategies"]))
        vwap_validation = next(item for item in result["candidate_validations"] if item["target_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))
        self.assertIn(result["research_queue_atom"]["metadata"]["sample_consistency"], {"aligned", "diverged", "train_stronger_than_test", "oos_stronger_than_train", "not_run"})
        self.assertTrue(result["research_queue_atom"]["metadata"]["sample_comparison_summary"])
        self.assertEqual(result["research_queue_atom"]["metadata"]["out_of_sample_result"], vwap_validation["out_of_sample_result"])
        self.assertIn(result["research_queue_atom"]["metadata"]["trigger_conditions"]["upgrade_candidate_status"], {"ready_for_manual_promotion_review", "blocked_by_scaffold", "blocked_by_consistency", "blocked_by_out_of_sample", "blocked_by_sample_size_guard", "blocked_by_governance_reason", "blocked_by_a_share_proxy_guard"})
        self.assertIn(result["research_queue_atom"]["metadata"]["trigger_conditions"]["freeze_candidate_status"], {"freeze_candidate", "watch_consistency_gap", "observe"})
        self.assertIn(result["research_queue_atom"]["metadata"]["state_summary"]["queue_recommendation"], {"ready_for_manual_promotion_review", "freeze_candidate_watch", "stay_experimental_watch_gap", "stay_experimental"})
        self.assertIn(result["research_queue_atom"]["metadata"]["state_summary"]["primary_gate"], {"none", "scaffold", "consistency_gap", "out_of_sample", "sample_size_guard", "governance_reason", "a_share_proxy_guard"})
        self.assertGreaterEqual(result["research_queue_atom"]["metadata"]["evidence_checklist"]["ready_count"], 0)
        self.assertEqual(result["research_queue_atom"]["metadata"]["evidence_checklist"]["total_count"], 7)
        self.assertEqual(result["research_queue_atom"]["metadata"]["manual_approval_entrypoint"]["entry_type"], "trading_research_queue_manual_promotion_approval")
        self.assertIn("approved", result["research_queue_atom"]["metadata"]["manual_approval_entrypoint"]["decision_options"])
        self.assertEqual(result["research_queue_atom"]["metadata"]["manual_approval_writeback"]["entry_type"], "trading_research_queue_manual_promotion_approval_result")
        self.assertIn("evolution_logs", result["research_queue_atom"]["metadata"]["manual_approval_writeback"]["writeback_targets"])
        self.assertEqual(result["research_queue_atom"]["metadata"]["manual_approval_confirmation_interface"]["entry_type"], "trading_research_queue_manual_promotion_confirmation")
        self.assertIn("decision", result["research_queue_atom"]["metadata"]["manual_approval_confirmation_interface"]["required_fields"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["sample_consistency"], vwap_validation["metadata"]["sample_comparison"]["consistency"])
        self.assertIn("consistency_secondary_driver", result["research_queue_theory_definition"]["metadata"])
        self.assertTrue(result["research_queue_theory_definition"]["metadata"]["consistency_driver_detail_summary"])
        self.assertEqual(result["research_queue_theory_definition"]["out_of_sample_result"], vwap_validation["out_of_sample_result"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["trigger_conditions"]["upgrade_candidate_status"], result["research_queue_atom"]["metadata"]["trigger_conditions"]["upgrade_candidate_status"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["state_summary"]["queue_recommendation"], result["research_queue_atom"]["metadata"]["state_summary"]["queue_recommendation"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["evidence_checklist"]["missing_keys"], result["research_queue_atom"]["metadata"]["evidence_checklist"]["missing_keys"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["manual_approval_entrypoint"]["approval_status"], result["research_queue_atom"]["metadata"]["manual_approval_entrypoint"]["approval_status"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["manual_approval_writeback"]["supported_decisions"], ["approved", "deferred", "rejected"])
        self.assertEqual(result["research_queue_theory_definition"]["metadata"]["manual_approval_confirmation_interface"]["writeback_entry_type"], "trading_research_queue_manual_promotion_approval_result")
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["sample_consistency"], vwap_validation["metadata"]["sample_comparison"]["consistency"])
        self.assertIn("consistency_secondary_driver", result["research_queue_skill_registry_entry"]["metadata"])
        self.assertTrue(result["research_queue_skill_registry_entry"]["metadata"]["consistency_driver_detail_summary"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["out_of_sample_result"], vwap_validation["out_of_sample_result"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["failure_count"], vwap_validation["failure_count"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["trigger_conditions"]["freeze_candidate_status"], result["research_queue_atom"]["metadata"]["trigger_conditions"]["freeze_candidate_status"])
        self.assertTrue(result["research_queue_skill_registry_entry"]["metadata"]["trigger_conditions"]["summary"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["state_summary"]["primary_gate"], result["research_queue_atom"]["metadata"]["state_summary"]["primary_gate"])
        self.assertTrue(result["research_queue_skill_registry_entry"]["metadata"]["state_summary"]["summary"])
        self.assertTrue(result["research_queue_skill_registry_entry"]["metadata"]["evidence_checklist"]["summary"])
        self.assertIn("out_of_sample_pass", [item["key"] for item in result["research_queue_skill_registry_entry"]["metadata"]["evidence_checklist"]["items"]])
        self.assertEqual(
            result["research_queue_skill_registry_entry"]["metadata"]["validation_report_id"],
            vwap_validation["id"],
        )
        self.assertEqual(
            result["research_queue_skill_registry_entry"]["metadata"]["strategy_id"],
            vwap_validation["target_id"],
        )
        self.assertFalse(result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_entrypoint"]["can_submit_now"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_entrypoint"]["approval_status"], "pending_evidence")
        self.assertIn("SelfEvolutionLog", result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_entrypoint"]["current_route"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_writeback"]["decision_writebacks"]["approved"]["evolution_trigger"], "trading_research_queue_manual_promotion_approved")
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_writeback"]["decision_writebacks"]["rejected"]["module_status"], "Frozen")
        self.assertIn("bulletin", result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_writeback"]["current_route"])
        self.assertEqual(result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_confirmation_interface"]["allowed_decisions"], ["approved", "deferred", "rejected"])
        self.assertIn("reviewer", result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_confirmation_interface"]["required_fields"])
        self.assertIn("follow_up_items", result["research_queue_skill_registry_entry"]["metadata"]["manual_approval_confirmation_interface"]["optional_fields"])
        self.assertIsNotNone(result["research_queue_approval_summary_view"])
        self.assertEqual(result["research_queue_approval_summary_view"]["implementation_status"], "Implemented")
        self.assertEqual(result["research_queue_approval_summary_view"]["summary"]["view_scope"], "summary_with_writeback_history")
        self.assertEqual(result["research_queue_approval_summary_view"]["summary"]["approval_record_count"], 0)
        self.assertEqual(result["research_queue_approval_summary_view"]["summary"]["pending_candidates"], 1)
        self.assertEqual(result["research_queue_approval_summary_view"]["summary"]["human_reviewed_count"], 0)
        self.assertEqual(result["research_queue_approval_summary_view"]["candidate_rows"][0]["candidate_slug"], "vwap")
        self.assertTrue(result["research_queue_approval_summary_view"]["candidate_rows"][0]["proxy_guard_blocked"])
        self.assertFalse(result["research_queue_approval_summary_view"]["candidate_rows"][0]["human_reviewed"])
        self.assertEqual(result["research_queue_approval_summary_view"]["candidate_rows"][0]["latest_reviewed_at"], "")
        self.assertEqual(result["research_queue_approval_summary_view"]["candidate_rows"][0]["writeback_entry_type"], "trading_research_queue_manual_promotion_approval_result")
        self.assertEqual(result["research_queue_approval_summary_view"]["candidate_rows"][0]["confirmation_entry_type"], "trading_research_queue_manual_promotion_confirmation")
        self.assertEqual(result["research_queue_approval_summary_view"]["integration_note"]["workflow_status"], "Implemented")
        self.assertIn("research_queue_daily_proxy_only", vwap_validation["warnings"])
        self.assertIn("true_ddx_ddy_not_connected", vwap_validation["warnings"])
        self.assertIn("seasoned_fresh_proxy_only", vwap_validation["warnings"])
        self.assertEqual(vwap_validation["metadata"]["a_share_semantics"]["seasoned_fresh_inference_status"], "Experimental")
        self.assertEqual(vwap_validation["metadata"]["a_share_semantics"]["seasoned_fresh_true_data_status"], "Not Implemented Yet")
        self.assertEqual(vwap_validation["metadata"]["a_share_proxy_snapshot"]["proxy_status"], "Experimental")
        self.assertTrue(vwap_validation["metadata"]["a_share_proxy_guard"]["blocks_promotion"])
        self.assertIn("a_share_proxy_guard_blocks_promotion", vwap_validation["warnings"])
        self.assertIn(vwap_validation["metadata"]["sample_comparison"]["consistency"], {"aligned", "diverged", "train_stronger_than_test", "oos_stronger_than_train", "not_run"})
        self.assertIn("walk_forward_validation", vwap_validation["metadata"])
        self.assertEqual(vwap_validation["metadata"]["walk_forward_validation"]["implementation_status"], "Experimental")
        self.assertIn(
            vwap_validation["metadata"]["walk_forward_validation"]["stability_status"],
            {"stable_pass", "mixed", "unstable", "thin", "not_run"},
        )
        self.assertGreaterEqual(vwap_validation["metadata"]["walk_forward_validation"]["slice_count"], 0)
        self.assertTrue(vwap_validation["metadata"]["walk_forward_validation"]["summary"])
        self.assertEqual(vwap_validation["metadata"]["governance_explanation"]["primary_reason"], "research_queue_daily_proxy_only")
        self.assertFalse(vwap_validation["metadata"]["retire_candidate_thresholds"]["history_triggered"])
        self.assertIn("expected_oos_result", vwap_validation["metadata"]["freeze_thresholds"])
        self.assertIn("downgrade_triggered", vwap_validation["metadata"]["downgrade_thresholds"])
        self.assertEqual(vwap_validation["metadata"]["current_validation_failure_count"], 1)
        self.assertGreaterEqual(vwap_validation["metadata"]["historical_failure_count"], 0)
        self.assertGreaterEqual(
            vwap_validation["metadata"]["combined_failure_count"],
            vwap_validation["metadata"]["current_validation_failure_count"],
        )
        failure_count_guard = next(
            item
            for item in result["research_queue_atom"]["metadata"]["evidence_checklist"]["items"]
            if item["key"] == "failure_count_guard"
        )
        self.assertEqual(failure_count_guard["status"], "ready")
        self.assertIn("current_validation_failure_count=1", failure_count_guard["detail"])
        self.assertIn("historical_failure_count=", failure_count_guard["detail"])
        self.assertIn("Train/OOS comparison:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertIn("Walk-forward validation:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertIn("Governance explanation:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertIn("Retire thresholds:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertIn("Freeze thresholds:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertIn("Downgrade thresholds:", " ".join(next(item for item in result["candidate_strategy_reviews"] if item["strategy_id"] == next(s["id"] for s in result["candidate_strategies"] if s["name"] == "VWAP Proxy Research v0.1"))["lessons"]))
        self.assertEqual(vwap_validation["governance_action"], "needs_review")
        self.assertEqual(vwap_validation["status"], "Experimental")
        self.assertIsNotNone(result["research_queue_relation"])
        self.assertEqual(result["research_queue_relation"]["relation_type"], "retired_pool_promotes_research_queue")
        self.assertIn("VWAP", brain.board_status()["next_step"])
        self.assertTrue(
            "人工升级审批结果写入入口占位" in brain.board_status()["next_step"]
            or "Experimental / ResearchQueue" in brain.board_status()["next_step"]
        )
        summary_view = brain.trading_research_queue_approval_summary({"candidate_slug": "vwap", "limit": 5})
        self.assertEqual(summary_view["summary"]["approval_record_count"], 0)
        self.assertEqual(summary_view["summary"]["pending_candidates"], 1)
        self.assertEqual(summary_view["candidate_rows"][0]["approval_status"], "pending_evidence")
        self.assertEqual(summary_view["candidate_rows"][0]["total_count"], 7)
        self.assertTrue(summary_view["candidate_rows"][0]["proxy_guard_blocked"])
        self.assertEqual(summary_view["candidate_rows"][0]["ready_count"], 4)
        self.assertNotIn("governance_reason_clear", summary_view["candidate_rows"][0]["missing_keys"])
        self.assertEqual(summary_view["integration_note"]["implementation_status"], "Implemented")
        history = brain.trading_replay_history_summary({"limit": 10})
        self.assertEqual(history["implementation_status"], "Implemented")
        self.assertEqual(history["summary"]["total_replay_events"], 4)
        self.assertEqual(history["summary"]["strategy_rollup_count"], 3)
        self.assertEqual(history["summary"]["selection_status_counts"]["abstain"], 4)
        self.assertEqual(history["summary"]["portfolio_action_counts"]["no_trade"], 4)
        self.assertEqual(history["summary"]["candidate_out_of_sample_counts"]["fail"], 8)
        self.assertEqual(history["summary"]["candidate_out_of_sample_counts"]["pass"], 4)
        sma_history = next(item for item in history["strategy_rollups"] if item["strategy_name"] == "SMA Trend v0.1")
        breakout_history = next(item for item in history["strategy_rollups"] if item["strategy_name"] == "Breakout v0.1")
        vwap_history = next(item for item in history["strategy_rollups"] if item["strategy_name"] == "VWAP Proxy Research v0.1")
        self.assertEqual(sma_history["replay_count"], 4)
        self.assertEqual(sma_history["oos_fail_count"], 4)
        self.assertEqual(sma_history["latest_governance_action"], "retire_candidate")
        self.assertGreaterEqual(sma_history["current_failure_streak"], 3)
        self.assertGreaterEqual(breakout_history["retire_candidate_count"], 1)
        self.assertEqual(breakout_history["latest_governance_action"], "retire_candidate")
        self.assertEqual(vwap_history["oos_pass_count"], 4)
        self.assertEqual(vwap_history["latest_out_of_sample_result"], "pass")
        self.assertIn(vwap_history["current_sample_consistency"], {"aligned", "diverged", "train_stronger_than_test", "oos_stronger_than_train", "not_run"})
        self.assertTrue(sma_history["current_governance_rule_summary"])
        self.assertTrue(any(candidate["historical_governance_summary"] for row in history["replay_rows"] for candidate in row["candidates"]))
        self.assertTrue(any(candidate["historical_governance_rule_summary"] for row in history["replay_rows"] for candidate in row["candidates"]))
        self.assertTrue(any(candidate["historical_validation_summary"] for row in history["replay_rows"] for candidate in row["candidates"]))
        self.assertEqual(history["research_queue_candidates"][0]["candidate_slug"], "vwap")
        self.assertIn("consistency_guard", history["research_queue_candidates"][0]["missing_keys"])
        self.assertNotIn("governance_reason_clear", history["research_queue_candidates"][0]["missing_keys"])
        self.assertIn("VWAP", history["summary"]["focus_now"])
        self.assertNotIn("governance_reason_clear", history["summary"]["focus_now"])
        self.assertTrue(all(row["candidates"][0]["snapshot_source"] in {"evolution_log", "latest_validation_fallback"} for row in history["replay_rows"] if row["candidates"]))
        self.assertTrue(any(candidate["snapshot_source"] == "evolution_log" for row in history["replay_rows"] for candidate in row["candidates"]))
        self.assertTrue(any(candidate["historical_sample_summary"] for row in history["replay_rows"] for candidate in row["candidates"]))
        filtered_history = brain.trading_replay_history_summary({"limit": 10, "strategy_name": "vwap"})
        self.assertEqual(filtered_history["summary"]["total_replay_events"], 4)
        self.assertEqual(filtered_history["summary"]["strategy_rollup_count"], 1)
        self.assertEqual(filtered_history["strategy_rollups"][0]["strategy_name"], "VWAP Proxy Research v0.1")
        governance_summary = brain.trading_strategy_governance_summary({"limit": 10})
        self.assertEqual(governance_summary["implementation_status"], "Implemented")
        self.assertEqual(governance_summary["summary"]["strategy_rollup_count"], 3)
        self.assertEqual(governance_summary["summary"]["research_queue_candidate_count"], 1)
        self.assertEqual(governance_summary["summary"]["top_focus_strategy_name"], "SMA Trend v0.1")
        self.assertEqual(governance_summary["summary"]["top_focus_state_bucket"], "retire_watch")
        self.assertEqual(governance_summary["summary"]["state_bucket_counts"]["retire_watch"], 2)
        self.assertEqual(governance_summary["summary"]["state_bucket_counts"]["consistency_watch"], 1)
        self.assertIn("VWAP", governance_summary["summary"]["focus_now"])
        self.assertNotIn("governance_reason_clear", governance_summary["summary"]["focus_now"])
        self.assertEqual(governance_summary["focus_candidates"][0]["strategy_name"], "SMA Trend v0.1")
        self.assertEqual(governance_summary["focus_candidates"][0]["state_bucket"], "retire_watch")
        self.assertEqual(governance_summary["focus_candidates"][1]["strategy_name"], "Breakout v0.1")
        self.assertEqual(governance_summary["focus_candidates"][1]["state_bucket"], "retire_watch")
        self.assertEqual(governance_summary["focus_candidates"][2]["strategy_name"], "VWAP Proxy Research v0.1")
        self.assertEqual(governance_summary["focus_candidates"][2]["state_bucket"], "consistency_watch")
        board_governance = brain.board_status()["trading_strategy_governance_summary"]
        self.assertEqual(
            board_governance["summary"]["top_focus_strategy_name"],
            governance_summary["summary"]["top_focus_strategy_name"],
        )
        self.assertEqual(
            board_governance["summary"]["top_focus_state_bucket"],
            governance_summary["summary"]["top_focus_state_bucket"],
        )
        self.assertNotIn("governance_reason_clear", brain.board_status()["latest_trading_research_queue_bulletin_state"]["missing_keys"])
        self.assertNotIn("governance_reason_clear", brain.board_status()["latest_trading_bulletin_state"]["missing_keys"])
        self.assertNotIn("governance_reason_clear", board_governance["summary"]["focus_now"])
        self.assertEqual(
            brain.status()["module_status"]["trading_strategy_governance_summary"],
            "Implemented",
        )
        gap_summary = brain.trading_research_queue_evidence_gap_summary({"candidate_slug": "vwap"})
        self.assertEqual(gap_summary["implementation_status"], "Implemented")
        self.assertEqual(gap_summary["summary"]["total_candidates"], 1)
        self.assertIn("VWAP", gap_summary["summary"]["focus_now"])
        self.assertEqual(gap_summary["rows"][0]["candidate_slug"], "vwap")
        self.assertEqual(gap_summary["rows"][0]["queue_recommendation"], "stay_experimental_watch_gap")
        self.assertEqual(gap_summary["rows"][0]["approval_status"], "pending_evidence")
        self.assertIn("consistency_guard", gap_summary["rows"][0]["missing_keys"])
        self.assertIn("scaffold_exit", gap_summary["rows"][0]["missing_keys"])
        self.assertNotIn("governance_reason_clear", gap_summary["rows"][0]["missing_keys"])
        self.assertIn("a_share_proxy_guard_clear", gap_summary["rows"][0]["missing_keys"])
        consistency_gap = next(item for item in gap_summary["rows"][0]["gap_details"] if item["key"] == "consistency_guard")
        self.assertTrue(consistency_gap["missing"])
        self.assertTrue(
            "过拟合" in consistency_gap["blocking_reason"]
            or "稳定性不足" in consistency_gap["blocking_reason"]
        )
        self.assertIn("sample_consistency", consistency_gap["current_value"])
        self.assertIn("aligned", consistency_gap["clear_condition"])
        self.assertEqual(consistency_gap["diagnostics"]["current_status"], "train_stronger_than_test")
        self.assertTrue(consistency_gap["diagnostics"]["blocked"])
        self.assertTrue(consistency_gap["diagnostics"]["return_gap_triggered"] or consistency_gap["diagnostics"]["risk_score_gap_triggered"])
        self.assertIn("Need test_return", consistency_gap["diagnostics"]["clear_summary"])
        consistency_diag = brain.trading_research_queue_consistency_diagnostics_summary({"candidate_slug": "vwap"})
        self.assertEqual(consistency_diag["implementation_status"], "Implemented")
        self.assertEqual(consistency_diag["summary"]["total_candidates"], 1)
        self.assertIn("VWAP", consistency_diag["summary"]["focus_now"])
        self.assertEqual(consistency_diag["rows"][0]["candidate_slug"], "vwap")
        self.assertEqual(consistency_diag["rows"][0]["sample_consistency"], "train_stronger_than_test")
        diagnostics = consistency_diag["rows"][0]["diagnostics"]
        self.assertTrue(diagnostics["blocked"])
        self.assertEqual(diagnostics["current_status"], "train_stronger_than_test")
        self.assertEqual(diagnostics["current_status"], consistency_gap["diagnostics"]["current_status"])
        self.assertTrue(diagnostics["return_gap_triggered"] or diagnostics["risk_score_gap_triggered"])
        self.assertGreater(diagnostics["target_test_return_min"], diagnostics["test_return"])
        self.assertGreater(diagnostics["target_test_score_min"], diagnostics["test_score"])
        self.assertIn(diagnostics["primary_driver"], {"return_gap", "risk_score_gap"})
        self.assertTrue(diagnostics["primary_driver_label"])
        self.assertTrue(diagnostics["recommended_validation_focus"])
        self.assertIn("当前一致性主要由", diagnostics["focus_summary"])
        self.assertIn("关键差异", diagnostics["focus_summary"])
        self.assertIn("train_score=", diagnostics["compact_gap_snapshot"])
        self.assertIn("regime_train=", diagnostics["compact_gap_snapshot"])
        self.assertIn("walk_forward_validation", diagnostics)
        self.assertEqual(
            diagnostics["walk_forward_validation"]["implementation_status"],
            "Experimental",
        )
        self.assertIn(
            diagnostics["walk_forward_stability_status"],
            {"stable_pass", "mixed", "unstable", "thin", "not_run"},
        )
        self.assertIn(
            diagnostics["walk_forward_coverage_status"],
            {"sufficient", "thin", "not_run"},
        )
        self.assertIn("Walk-forward", diagnostics["clear_summary"])
        self.assertIn(diagnostics["market_regime_alignment"], {"aligned", "shifted", "not_run"})
        self.assertTrue(diagnostics["market_regime_summary"])
        self.assertIn("Need test_return", diagnostics["clear_summary"])
        scaffold_gap = next(item for item in gap_summary["rows"][0]["gap_details"] if item["key"] == "scaffold_exit")
        self.assertEqual(scaffold_gap["severity"], "medium")
        self.assertIn("daily_proxy", scaffold_gap["blocking_reason"])
        self.assertTrue(scaffold_gap["diagnostics"]["blocked"])
        self.assertEqual(scaffold_gap["diagnostics"]["scaffold_mode"], "daily_proxy")
        self.assertEqual(scaffold_gap["diagnostics"]["feature_scaffold_status"], "Implemented")
        self.assertTrue(scaffold_gap["diagnostics"]["promotion_blocked_even_if_oos_pass"])
        self.assertEqual(scaffold_gap["diagnostics"]["target_scaffold_mode"], "none")
        self.assertIn("Need scaffold_mode == none", scaffold_gap["diagnostics"]["clear_summary"])
        self.assertIn("给出摆脱 daily_proxy scaffold 的替代验证路径或退出说明", scaffold_gap["follow_up_items"])
        sample_size_gap = next(item for item in gap_summary["rows"][0]["gap_details"] if item["key"] == "sample_size_guard_clear")
        self.assertEqual(sample_size_gap["severity"], "high")
        self.assertIn("bars=", sample_size_gap["diagnostics"]["summary"])
        self.assertEqual(sample_size_gap["missing"], sample_size_gap["diagnostics"]["blocked"])
        if sample_size_gap["missing"]:
            self.assertIn("Need sample_size_thresholds.blocks_promotion == False", sample_size_gap["diagnostics"]["clear_summary"])
            self.assertTrue(sample_size_gap["diagnostics"]["zero_trade_pairs_reason_key"])
            self.assertIn("completed_trade_pairs", sample_size_gap["diagnostics"]["clear_summary"])
            self.assertIn("补更多 bars / completed_trade_pairs / oos_trade_pairs，让样本量守门停止阻断升级", sample_size_gap["follow_up_items"])
        else:
            self.assertEqual(sample_size_gap["blocking_reason"], "当前条件已满足。")
        governance_gap = next(item for item in gap_summary["rows"][0]["gap_details"] if item["key"] == "governance_reason_clear")
        self.assertEqual(governance_gap["severity"], "high")
        self.assertFalse(governance_gap["diagnostics"]["blocked"])
        self.assertEqual(governance_gap["diagnostics"]["governance_primary_reason"], "research_queue_daily_proxy_only")
        self.assertEqual(governance_gap["diagnostics"]["reason_family"], "research_queue_scaffold")
        self.assertEqual(governance_gap["diagnostics"]["target_primary_reason"], "validated_keep_or_non_research_queue_reason")
        self.assertIn("no longer blocks", governance_gap["diagnostics"]["clear_summary"])
        self.assertIn("补 train/OOS 一致性说明并缩小样本内外 gap", consistency_gap["follow_up_items"])
        self.assertNotIn("补充治理说明，消除 research_queue 主原因拦截", gap_summary["rows"][0]["normalized_follow_up_plan"])
        proxy_guard_gap = next(item for item in gap_summary["rows"][0]["gap_details"] if item["key"] == "a_share_proxy_guard_clear")
        self.assertEqual(proxy_guard_gap["severity"], "high")
        self.assertTrue(proxy_guard_gap["diagnostics"]["blocked"])
        self.assertEqual(proxy_guard_gap["diagnostics"]["bias_label"], "overnight_lock_pressure_bias")
        self.assertEqual(proxy_guard_gap["diagnostics"]["preferred_action"], "no_trade")
        self.assertEqual(proxy_guard_gap["diagnostics"]["readiness_connection_status"], "Not Implemented Yet")
        self.assertEqual(proxy_guard_gap["diagnostics"]["priority_source_key"], "tdx_realtime_quotes")
        self.assertEqual(proxy_guard_gap["diagnostics"]["priority_source_label"], "TDX realtime quotes")
        self.assertIn("ddx", proxy_guard_gap["diagnostics"]["priority_required_fields"])
        self.assertGreaterEqual(proxy_guard_gap["diagnostics"]["required_source_count"], 3)
        self.assertTrue(proxy_guard_gap["diagnostics"]["next_actions"])
        self.assertIn("先接 TDX realtime quotes 的真 DDX/DDY 字段", proxy_guard_gap["diagnostics"]["next_actions"][0])
        self.assertIn("腾讯自定义股票 MCP", proxy_guard_gap["diagnostics"]["next_actions"][1])
        self.assertIn("WorkBuddy neodata", proxy_guard_gap["diagnostics"]["next_actions"][2])
        self.assertIn("先接 TDX realtime quotes", proxy_guard_gap["diagnostics"]["plan_summary"])
        self.assertIn("Need a_share_proxy_guard.blocks_promotion == False", proxy_guard_gap["diagnostics"]["clear_summary"])
        self.assertIn("补真 DDX/DDY 或更强替代验证，解除 A股代理守门阻塞", proxy_guard_gap["follow_up_items"])
        readiness = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        self.assertEqual(readiness["implementation_status"], "Implemented")
        self.assertEqual(readiness["summary"]["total_candidates"], 1)
        self.assertIn("VWAP", readiness["summary"]["focus_now"])
        self.assertEqual(readiness["rows"][0]["candidate_slug"], "vwap")
        self.assertEqual(readiness["rows"][0]["readiness_status"], "not_ready_for_promotion")
        self.assertEqual(readiness["rows"][0]["blocked_count"], 3)
        self.assertEqual(readiness["rows"][0]["primary_blocker_key"], "consistency_guard")
        self.assertEqual(readiness["rows"][0]["primary_blocker_severity"], "high")
        self.assertIn("train/OOS", readiness["rows"][0]["next_best_action"])
        self.assertFalse(any(item.startswith("??") for item in readiness["rows"][0]["normalized_follow_up_plan"]))
        self.assertIn("补 train/OOS 一致性说明并缩小样本内外 gap", readiness["rows"][0]["normalized_follow_up_plan"])
        self.assertIn("给出摆脱 daily_proxy scaffold 的替代验证路径或退出说明", readiness["rows"][0]["normalized_follow_up_plan"])
        self.assertNotIn("补充治理说明，消除 research_queue 主原因拦截", readiness["rows"][0]["normalized_follow_up_plan"])
        self.assertIn("补真 DDX/DDY 或更强替代验证，解除 A股代理守门阻塞", readiness["rows"][0]["normalized_follow_up_plan"])
        self.assertEqual(readiness["rows"][0]["target_gap_snapshot"]["current_status"], "train_stronger_than_test")
        self.assertGreater(readiness["rows"][0]["target_gap_snapshot"]["return_gap_to_close"], 0.0)
        self.assertGreater(readiness["rows"][0]["target_gap_snapshot"]["score_gap_to_close"], 0.0)
        self.assertIn(
            readiness["rows"][0]["target_gap_snapshot"]["market_regime_alignment"],
            {"aligned", "shifted", "not_run"},
        )
        self.assertIn(
            readiness["rows"][0]["target_gap_snapshot"]["walk_forward_stability_status"],
            {"stable_pass", "mixed", "unstable", "thin", "not_run"},
        )
        self.assertIn(
            readiness["rows"][0]["target_gap_snapshot"]["walk_forward_coverage_status"],
            {"sufficient", "thin", "not_run"},
        )
        self.assertIn(
            "implementation_status",
            readiness["rows"][0]["target_gap_snapshot"]["walk_forward_validation"],
        )
        self.assertTrue(readiness["rows"][0]["target_gap_snapshot"]["market_regime_summary"])
        self.assertIn("Need test_return", readiness["rows"][0]["target_gap_snapshot"]["clear_summary"])
        self.assertIn("下一轮验证切片应围绕", readiness["rows"][0]["next_validation_slice_note"])
        self.assertIn("test_return", readiness["rows"][0]["next_validation_slice_note"])
        self.assertIn("test_score", readiness["rows"][0]["next_validation_slice_note"])
        self.assertEqual(readiness["rows"][0]["validation_task_preview"]["candidate_slug"], "vwap")
        self.assertEqual(readiness["rows"][0]["validation_task_preview"]["blocker"], "consistency_guard")
        self.assertTrue(readiness["rows"][0]["validation_task_preview"]["research_mode"])
        self.assertFalse(readiness["rows"][0]["validation_task_preview"]["live_trading_enabled"])
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["task_status"],
            "ready_for_next_validation_slice",
        )
        self.assertGreater(
            readiness["rows"][0]["validation_task_preview"]["target_test_return_min"],
            0.0,
        )
        self.assertGreater(
            readiness["rows"][0]["validation_task_preview"]["target_test_score_min"],
            0.0,
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["required_actions"],
            readiness["rows"][0]["normalized_follow_up_plan"],
        )
        self.assertTrue(readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan"])
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan"][0]["source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["source_key"],
            "tdx_realtime_quotes",
        )
        self.assertIn(
            "ddx",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["required_fields"],
        )
        self.assertTrue(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["command_hint"]
        )
        self.assertIn(
            "优先处理",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["summary"],
        )
        self.assertIn(
            "TDX realtime quotes",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan_summary"],
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["replay_adjustment_hints"]["primary_driver"],
            readiness["rows"][0]["target_gap_snapshot"]["primary_driver"],
        )
        self.assertTrue(
            readiness["rows"][0]["validation_task_preview"]["replay_adjustment_hints"]["suggested_variants"]
        )
        self.assertTrue(
            readiness["rows"][0]["validation_task_preview"]["replay_adjustment_hints"]["priority_checks"]
        )
        self.assertEqual(len(readiness["rows"][0]["blockers"]), 5)
        blocked_keys = [
            item["blocker_key"]
            for item in readiness["rows"][0]["review_checklist"]["items"]
            if item["blocked"]
        ]
        self.assertEqual(
            readiness["rows"][0]["priority_rationale"]["ordered_blocker_keys"],
            blocked_keys,
        )
        self.assertEqual(
            readiness["rows"][0]["priority_rationale"]["severity_order"],
            [
                item["severity"]
                for item in readiness["rows"][0]["review_checklist"]["items"]
                if item["blocked"]
            ],
        )
        self.assertIn("high severity blockers", " ".join(readiness["rows"][0]["priority_rationale"]["ranking_rules"]))
        self.assertIn("consistency_guard", readiness["rows"][0]["priority_rationale"]["summary"])
        self.assertEqual(
            readiness["summary"]["focus_follow_up_plan"],
            readiness["rows"][0]["normalized_follow_up_plan"],
        )
        self.assertEqual(
            readiness["summary"]["focus_target_gap_snapshot"],
            readiness["rows"][0]["target_gap_snapshot"],
        )
        self.assertEqual(
            readiness["summary"]["focus_next_validation_slice_note"],
            readiness["rows"][0]["next_validation_slice_note"],
        )
        self.assertEqual(
            readiness["summary"]["focus_validation_task_preview"],
            readiness["rows"][0]["validation_task_preview"],
        )
        self.assertEqual(readiness["rows"][0]["review_checklist"]["blocked_steps"], 3)
        self.assertEqual(
            [item["blocker_key"] for item in readiness["rows"][0]["review_checklist"]["items"]],
            ["consistency_guard", "sample_size_guard_clear", "governance_reason_clear", "a_share_proxy_guard_clear", "scaffold_exit"],
        )
        self.assertEqual(readiness["rows"][0]["review_checklist"]["items"][0]["step"], 1)
        self.assertIn("train/OOS", readiness["rows"][0]["review_checklist"]["items"][0]["action_required"])
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["gate_type"],
            "consistency_guard_acceptance",
        )
        self.assertIn(
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["primary_driver"],
            {"return_gap", "risk_score_gap"},
        )
        self.assertTrue(
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["recommended_validation_focus"]
        )
        self.assertGreater(
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["return_gap_to_close"],
            0.0,
        )
        self.assertGreater(
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["score_gap_to_close"],
            0.0,
        )
        self.assertIn(
            "Need test_return",
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"]["summary"],
        )
        self.assertIn(
            "market_regime_summary",
            readiness["rows"][0]["review_checklist"]["items"][0]["acceptance_gate"],
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][1]["acceptance_gate"]["gate_type"],
            "sample_size_guard_acceptance",
        )
        self.assertGreater(
            readiness["rows"][0]["review_checklist"]["items"][1]["acceptance_gate"]["target_min_total_bars"],
            0,
        )
        self.assertIn("bars / completed_trade_pairs / oos_completed_trade_pairs", readiness["rows"][0]["review_checklist"]["items"][1]["acceptance_gate"]["summary"])
        self.assertIn(
            "zero_trade_pairs_summary",
            readiness["rows"][0]["review_checklist"]["items"][1]["acceptance_gate"],
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][2]["acceptance_gate"]["gate_type"],
            "governance_reason_clear_acceptance",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][2]["acceptance_gate"]["current_governance_primary_reason"],
            "research_queue_daily_proxy_only",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][2]["acceptance_gate"]["current_reason_family"],
            "research_queue_scaffold",
        )
        self.assertIn(
            "Need governance_primary_reason",
            readiness["rows"][0]["review_checklist"]["items"][2]["acceptance_gate"]["summary"],
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][2]["status"],
            "ready",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["gate_type"],
            "a_share_proxy_guard_acceptance",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["current_bias_label"],
            "overnight_lock_pressure_bias",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["current_preferred_action"],
            "no_trade",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["readiness_connection_status"],
            "Not Implemented Yet",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertIn(
            "ddx",
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["priority_required_fields"],
        )
        self.assertTrue(
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["next_actions"]
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["plan_summary"],
        )
        self.assertIn(
            "Need a_share_proxy_guard to stop blocking promotion",
            readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]["summary"],
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"]["gate_type"],
            "scaffold_exit_acceptance",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"]["current_scaffold_mode"],
            "daily_proxy",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"]["current_feature_scaffold_status"],
            "Implemented",
        )
        self.assertEqual(
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"]["current_out_of_sample_result"],
            "pass",
        )
        self.assertTrue(
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"][
                "promotion_blocked_even_if_oos_pass"
            ]
        )
        self.assertIn(
            "Need scaffold_mode",
            readiness["rows"][0]["review_checklist"]["items"][4]["acceptance_gate"]["summary"],
        )
        self.assertIn("manual promotion review", readiness["rows"][0]["review_checklist"]["summary"])
        self.assertEqual(gap_summary["rows"][0]["source_refs"]["skill_registry_entry_id"], result["research_queue_skill_registry_entry"]["id"])
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_evidence_gap_summary"], "Implemented")

    def test_proxy_guard_readiness_surfaces_westock_historical_baseline_gap_without_overclaiming_ddx(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        data_path = Path(tmp.name) / "data" / "kl_ddx_1y.json"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for index in range(28):
            rows.append(
                {
                    "d": f"2026-07-{index + 1:02d}",
                    "c": f"{40.0 + index / 10:.2f}",
                    "main": float(1000000 * ((-1) ** index)),
                    "jumbo": float(500000 * ((-1) ** (index + 1))),
                    "mid": 0.0,
                    "small": 0.0,
                    "block": 0.0,
                }
            )
        data_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        brain.trading_a_share_westock_fund_flow_history_snapshot(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "source_path": str(data_path),
            }
        )

        readiness = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        proxy_gate = readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]
        self.assertEqual(proxy_gate["historical_baseline_status"], "westock_missing_required_fields")
        self.assertIn("缺少显式字段 ddx", proxy_gate["historical_baseline_summary"])
        self.assertIn("不能替代真 DDX/DDY", proxy_gate["historical_baseline_summary"])
        self.assertIn("当前已接历史基线", proxy_gate["plan_summary"])
        self.assertTrue(readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan"])
        westock_step = next(
            item
            for item in readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan"]
            if item["source_key"] == "westock_fund_flow_history"
        )
        self.assertEqual(westock_step["status"], "attached_but_incomplete")
        self.assertIn(
            "TDX realtime quotes",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan_summary"],
        )

        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({"candidate_slug": "vwap"})
        self.assertIn("历史基线补充", sync_result["board_state"]["next_step"])
        self.assertIn("不能替代真 DDX/DDY", sync_result["board_state"]["next_step"])
        self.assertIn("westock_missing_required_fields", sync_result["board_state"]["event_log"][-1]["summary"])
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_route_plan_summary"])
        self.assertGreater(sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_route_plan_step_count"], 0)
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_task_summary"])
        latest_status = brain.status()
        self.assertEqual(
            latest_status["latest_trading_self_evolution_log"]["trigger"],
            "trading_research_queue_validation_summary_synced",
        )
        self.assertEqual(
            latest_status["latest_trading_skill_registry_entry"]["skill_name"],
            sync_result["candidate_skill_registry_entry"]["skill_name"],
        )
        self.assertEqual(
            latest_status["latest_trading_module_status_record"]["domain"],
            "trading",
        )
        self.assertTrue(
            "trading" in latest_status["latest_trading_module_status_record"]["module_name"]
        )
        self.assertEqual(
            latest_status["latest_trading_bulletin_state_record"]["candidate_slug"],
            sync_result["bulletin_state_record"]["metadata"]["candidate_slug"],
        )
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_consistency_diagnostics_summary"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_readiness_summary"], "Implemented")
        self.assertGreaterEqual(brain.status()["counts"]["learning_entries"], 1)
        self.assertGreaterEqual(brain.status()["counts"]["atoms"], 3)
        self.assertGreaterEqual(brain.status()["counts"]["theory_definitions"], 4)
        self.assertGreaterEqual(brain.status()["counts"]["strategy_definitions"], 3)
        self.assertGreaterEqual(brain.status()["counts"]["backtest_results"], 3)
        self.assertGreaterEqual(brain.status()["counts"]["skill_registry_entries"], 2)
        self.assertEqual(brain.status()["module_status"]["trading_replay_history_summary"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_approval_summary"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_manual_approval_submission"], "Implemented")
        self.assertTrue(
            "ResearchQueue" in brain.board_status()["next_step"]
            or "阻塞" in brain.board_status()["next_step"]
            or "一致性" in brain.board_status()["next_step"]
        )

    def test_status_prefers_latest_trading_bulletin_state_record_from_metadata_domain(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({"candidate_slug": "vwap"})
        custom_record = BulletinStateRecord(
            bulletin_path=str(brain.board.path),
            state_status="杩涜涓?",
            completed=list(sync_result["board_state"]["completed"]),
            in_progress=list(sync_result["board_state"]["in_progress"]),
            next_step="娌荤悊琛ュ己锛氭樉寮忓尯鍒?payload 鏍锋湰鎸傛帴涓庝唬鐞嗗畧闂ㄦ竻鍏冲畬鎴愩€?",
            recent_event="trading_proxy_guard_clearance_stage_explicit",
            created_at="2099-01-01T00:00:00+00:00",
            quality_score=0.66,
            evidence_level="governance_enrichment",
            source_reliability=0.88,
            freshness=0.97,
            validation_status="needs_review",
            out_of_sample_result="pass",
            failure_count=2,
            human_reviewed=False,
            status="Experimental",
            metadata={
                "domain": "trading",
                "queue_type": "ResearchQueue",
                "candidate_slug": "vwap",
                "sync_source": "trading_proxy_guard_clearance_stage_explicit",
                "priority_source_clearance_stage": "payload_sample_only",
                "priority_source_clearance_summary": "浼樺厛婧愬綋鍓嶅彧鏈?payload 娉ㄥ叆鏍锋湰锛屼笉鑳藉崟鐙В闄?A鑲′唬鐞嗗畧闂ㄣ€?",
                "implementation_status": "Implemented",
            },
        )
        brain.store.save("bulletin_state_records", custom_record)

        latest_status = brain.status()
        self.assertEqual(
            latest_status["latest_trading_bulletin_state_record"]["metadata"]["sync_source"],
            "trading_proxy_guard_clearance_stage_explicit",
        )
        self.assertEqual(
            latest_status["latest_trading_bulletin_state_record"]["metadata"]["priority_source_clearance_stage"],
            "payload_sample_only",
        )
        self.assertEqual(
            latest_status["latest_trading_bulletin_state_record"]["candidate_slug"],
            "vwap",
        )

    def test_status_prefers_latest_trading_self_evolution_log_from_newer_trading_governance_event(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_research_queue_sync_bulletin_from_latest_validation({"candidate_slug": "vwap"})
        custom_log = SelfEvolutionLog(
            trigger="trading_proxy_route_payload_stage_deoverclaimed",
            observation="Payload 娉ㄥ叆鏍锋湰涓嶅簲琚綋鎴?attached_ready銆?",
            proposed_update="淇濇寔 payload_sample_only锛岀洿鍒伴潪 payload 璇佹嵁鐪熸鎺ュ叆銆?",
            change_type="governance_enrichment",
            affected_ids=["trading_a_share_proxy_guard_diagnostics"],
            applied=True,
            created_at="2099-01-01T00:00:00+00:00",
            metrics={
                "candidate_slug": "vwap",
                "priority_route_status": "payload_sample_only",
            },
            metadata={
                "domain": "trading",
                "queue_type": "ResearchQueue",
                "candidate_slug": "vwap",
                "implementation_status": "Implemented",
            },
        )
        brain.store.save("evolution_logs", custom_log)

        latest_status = brain.status()
        self.assertEqual(
            latest_status["latest_trading_self_evolution_log"]["trigger"],
            "trading_proxy_route_payload_stage_deoverclaimed",
        )
        self.assertEqual(
            latest_status["latest_trading_self_evolution_log"]["metrics"]["priority_route_status"],
            "payload_sample_only",
        )

    def test_status_research_queue_snapshot_inherits_latest_priority_route_status_from_newer_trading_bulletin(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_research_queue_sync_bulletin_from_latest_validation({"candidate_slug": "vwap"})
        custom_record = BulletinStateRecord(
            bulletin_path=str(brain.board.path),
            state_status="杩涜涓?",
            completed=list(brain.board_status()["completed"]),
            in_progress=list(brain.board_status()["in_progress"]),
            next_step=brain.board_status()["next_step"],
            recent_event="trading_status_latest_evolution_visibility_fixed",
            created_at="2099-01-01T00:00:00+00:00",
            quality_score=0.69,
            evidence_level="governance_enrichment",
            source_reliability=0.9,
            freshness=0.99,
            validation_status="needs_review",
            out_of_sample_result="pass",
            failure_count=12,
            human_reviewed=False,
            status="Experimental",
            metadata={
                "domain": "trading",
                "queue_type": "ResearchQueue",
                "candidate_slug": "vwap",
                "sync_source": "trading_status_latest_evolution_visibility_fixed",
                "priority_route_status": "payload_sample_only",
                "priority_source_clearance_stage": "payload_sample_only",
                "priority_source_clearance_summary": "鏈€鏂?trading bulletin 宸叉槑纭?payload 娉ㄥ叆鏍锋湰涓嶈兘绛夊悓 attached_ready銆?",
                "replay_variant_governance_hint": "continue_targeted_replay",
                "replay_variant_governance_priority_action": "continue_targeted_replay",
                "replay_variant_governance_summary": "latest replay variant improved without new deterioration; continue targeted replay.",
                "a_share_proxy_preferred_action": "no_trade",
                "a_share_proxy_summary": "bias=overnight_lock_pressure_bias, strength=1.00, blocks_promotion=True, preferred_action=no_trade",
                "implementation_status": "Implemented",
            },
        )
        brain.store.save("bulletin_state_records", custom_record)

        latest_status = brain.status()
        snapshot = latest_status["latest_trading_research_queue_bulletin_state"]
        self.assertEqual(snapshot["candidate_slug"], "vwap")
        self.assertEqual(snapshot["sync_source"], "trading_status_latest_evolution_visibility_fixed")
        self.assertEqual(snapshot["priority_route_status"], "payload_sample_only")
        self.assertEqual(snapshot["priority_source_clearance_stage"], "payload_sample_only")
        self.assertIn("payload", snapshot["priority_source_clearance_summary"])
        self.assertEqual(snapshot["replay_variant_governance_hint"], "continue_targeted_replay")
        self.assertEqual(snapshot["replay_variant_governance_priority_action"], "continue_targeted_replay")
        self.assertTrue(snapshot["replay_variant_governance_summary"])
        self.assertIn("replay", snapshot["replay_variant_governance_summary"])
        self.assertEqual(snapshot["a_share_proxy_preferred_action"], "no_trade")
        self.assertIn("preferred_action=no_trade", snapshot["a_share_proxy_summary"])

    def test_reconcile_a_share_authority_source_is_idempotent_and_marks_duplicates(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        doc_path = root / "SYSTEM_REPLICATION_FOR_CODEX.md"
        doc_path.write_text(
            textwrap.dedent(
                """\
                # A-share Authority
                T+1 only.
                Use true DDX/DDY ahead of generic OHLCV flow proxies.
                """
            ),
            encoding="utf-8",
        )
        brain = SuperBrainV01(root)

        source_a = SourceRecord(
            source_type="authoritative_trading_system_charter",
            title="Authority A",
            uri=str(doc_path).replace("\\", "/"),
            reliability=0.98,
            metadata={"authority_level": "highest", "implementation_status": "Implemented"},
        )
        source_b = SourceRecord(
            source_type="authoritative_trading_system_charter",
            title="Authority B",
            uri=str(doc_path).replace("\\", "/"),
            reliability=0.98,
            metadata={"authority_level": "highest", "implementation_status": "Implemented"},
        )
        brain.store.save("sources", source_a)
        brain.store.save("sources", source_b)
        learning = brain.decisions.create_learning_entry(
            entry_type="authoritative_source_registration",
            target_type="trading_domain_governance",
            target_ids=[source_b.id],
            source_record_id=source_b.id,
            summary="authority registration",
            metadata={"implementation_status": "Implemented"},
        )["learning_entry"]
        skill = SkillRegistryEntry(
            skill_name="trading.a_share_authority",
            capability_type="governance",
            evidence_level="authoritative_doc",
            human_reviewed=True,
            metadata={"precedence": "authoritative", "source_record_id": source_a.id, "implementation_status": "Implemented"},
        )
        module = ModuleStatusRecord(
            module_name="trading_a_share_authority",
            evidence_level="authority_registration",
            human_reviewed=True,
            metadata={"precedence": "authoritative", "source_record_id": source_a.id, "implementation_status": "Implemented"},
        )
        brain.store.save("skill_registry_entries", skill)
        brain.store.save("module_status_records", module)

        result = brain.trading_reconcile_a_share_authority({"doc_path": str(doc_path)})

        self.assertTrue(result["changed"])
        self.assertEqual(result["canonical_source_id"], source_b.id)
        self.assertEqual(result["duplicate_source_ids"], [source_a.id])
        canonical = brain.store.get("sources", source_b.id)
        duplicate = brain.store.get("sources", source_a.id)
        self.assertEqual(canonical["metadata"]["dedupe_status"], "canonical")
        self.assertEqual(canonical["metadata"]["duplicate_source_ids"], [source_a.id])
        self.assertTrue(canonical["metadata"]["authority_registration_verified"])
        self.assertEqual(duplicate["metadata"]["dedupe_status"], "superseded")
        self.assertEqual(duplicate["metadata"]["canonical_source_id"], source_b.id)
        updated_learning = brain.store.get("learning_entries", learning["id"])
        self.assertEqual(updated_learning["source_record_id"], source_b.id)
        self.assertEqual(updated_learning["metadata"]["canonical_source_id"], source_b.id)
        updated_skill = brain.store.get("skill_registry_entries", skill.id)
        self.assertEqual(updated_skill["metadata"]["source_record_id"], source_b.id)
        updated_module = brain.store.get("module_status_records", module.id)
        self.assertEqual(updated_module["metadata"]["source_record_id"], source_b.id)
        self.assertEqual(result["self_evolution_log"]["trigger"], "authoritative_trading_charter_reconciled")
        self.assertEqual(brain.status()["module_status"]["trading_reconcile_a_share_authority"], "Implemented")

        rerun = brain.trading_reconcile_a_share_authority({"doc_path": str(doc_path)})
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["canonical_source_id"], source_b.id)
        self.assertEqual(rerun["duplicate_source_ids"], [source_a.id])
        self.assertEqual(rerun["self_evolution_log"], {})

    def test_true_money_flow_readiness_report_writes_governance_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_true_money_flow_readiness({"symbol": "300418", "timeframe": "1d"})

        self.assertTrue(result["changed"])
        readiness = result["true_money_flow_readiness"]
        self.assertEqual(readiness["connection_status"], "Not Implemented Yet")
        self.assertEqual(readiness["sample_attached_count"], 0)
        self.assertEqual(readiness["sample_attached_source_keys"], [])
        self.assertEqual(readiness["required_sources"][0]["source_key"], "tdx_realtime_quotes")
        self.assertFalse(readiness["required_sources"][0]["latest_sample_available"])
        self.assertEqual(readiness["required_sources"][1]["source_key"], "tencent_qt_realtime_orderbook")
        self.assertEqual(readiness["required_sources"][1]["bridge_entry"], "F:/aidanao/daytrade_system/runner.py")
        self.assertEqual(readiness["required_sources"][2]["source_key"], "workbuddy_neodata_market_context")
        self.assertEqual(readiness["required_sources"][2]["bridge_entry"], "F:/aidanao/mcp/workbuddy_bridge.py")
        self.assertEqual(
            readiness["preferred_source_chain"][:3],
            ["tdx_realtime_quotes", "tencent_qt_realtime_orderbook", "workbuddy_neodata_market_context"],
        )
        self.assertIn("Tencent / WorkBuddy", readiness["summary"])
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.a_share_true_money_flow_readiness")
        self.assertEqual(result["skill_registry_entry"]["status"], "Interface")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["true_money_flow_readiness"]["blocking_reason"],
            "true_ddx_ddy_and_historical_fund_flow_not_connected",
        )
        self.assertEqual(result["module_status_record"]["module_name"], "trading_a_share_true_money_flow_readiness")
        self.assertEqual(result["module_status_record"]["status"], "Interface")
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_a_share_true_money_flow_readiness_reported")
        self.assertEqual(result["bulletin_state_record"]["recent_event"], "trading_a_share_true_money_flow_readiness_reported")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["module_name"], "trading_a_share_true_money_flow_readiness")
        self.assertTrue(
            any(
                "A股真 DDX/DDY / TDX / WeStock readiness 报告已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(brain.status()["module_status"]["trading_a_share_true_money_flow_readiness"], "Implemented")

    def test_workbuddy_mapping_doc_covers_authority_skills_and_conflicts(self):
        doc_path = Path(r"F:\aidanao\docs\workbuddy_trading_system_mapping.md")
        text = doc_path.read_text(encoding="utf-8")

        self.assertIn("WorkBuddy 交易系统 -> 第二大脑母系统 保留映射与覆盖表", text)
        self.assertIn("probability-fusion", text)
        self.assertIn("triple-decision-trees", text)
        self.assertIn("a-stock-data", text)
        self.assertIn("workbuddy_neodata_market_context", text)

        for skill_name in [
            "a-stock-trading-hours",
            "t1-lockup-tracking",
            "turnover-cap-analysis",
            "lockup-depth-analysis",
            "supply-test",
            "phase-c-d-transition",
            "accumulation-detection",
            "absorption-detection",
            "effort-result-climax",
            "money-flow-warfare",
            "a-share-game-theory",
            "anchoring-detection",
            "sector-rotation-detection",
            "opening-range",
            "vwap-analyzer",
            "volume-profile-chip",
            "liquidity-sweep",
            "delta-cvd",
            "stock-catalyst-hunter",
            "a-share-call-auction",
            "imbalance-detection",
            "footprint-detection",
            "hvn-lvn-nodes",
            "lps-upthrust-breakout",
            "market-context",
            "probability-fusion",
        ]:
            self.assertIn(skill_name, text)

        for status_marker in ["已接入", "部分接入", "未接入", "冲突覆盖"]:
            self.assertIn(status_marker, text)

        self.assertIn("SMA Trend v0.1", text)
        self.assertIn("Breakout v0.1", text)
        self.assertIn("VWAP Proxy Research v0.1", text)
        self.assertIn("OHLCV 行为代理", text)

    def test_workbuddy_current_skill_catalog_registers_live_authority_snapshot(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        skills_root = root / "workbuddy_skills"
        for name, disable in [
            ("a-stock-data", True),
            ("a-stock-analysis", False),
            ("probability-fusion", False),
            ("triple-decision-trees", False),
            ("market-context", False),
            ("a-stock-trading-hours", False),
            ("delta-cvd", False),
            ("a-share-game-theory", False),
        ]:
            skill_dir = skills_root / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    f"""\
                    ---
                    name: {name}
                    disable: {"true" if disable else "false"}
                    version: test-1
                    ---

                    # {name}
                    """
                ),
                encoding="utf-8",
            )

        brain = SuperBrainV01(root)
        result = brain.trading_workbuddy_current_skill_catalog({
            "workbuddy_skills_root": str(skills_root),
        })

        self.assertTrue(result["changed"])
        catalog = result["catalog_snapshot"]
        self.assertEqual(catalog["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(catalog["summary"]["present_component_count"], 4)
        self.assertEqual(catalog["summary"]["missing_component_count"], 1)
        self.assertGreater(catalog["summary"]["missing_skill_count"], 0)
        self.assertEqual(catalog["summary"]["disabled_component_count"], 1)
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.workbuddy_current_skill_catalog",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Active")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_workbuddy_current_skill_catalog",
        )
        self.assertEqual(result["module_status_record"]["status"], "Active")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_workbuddy_current_skill_catalog_registered",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_workbuddy_current_skill_catalog_registered",
        )
        self.assertTrue(
            any(
                "WorkBuddy 当前交易技能目录快照已登记" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertTrue(
            any(gap["expected_name"] == "workbuddy_neodata_market_context" for gap in catalog["alias_gaps"])
        )
        status = brain.status()
        self.assertEqual(
            status["latest_workbuddy_authority_catalog"]["skill_name"],
            "trading.workbuddy_current_skill_catalog",
        )
        self.assertEqual(
            status["latest_workbuddy_authority_catalog"]["authority_mode"],
            "workbuddy_current_state_first",
        )
        self.assertEqual(
            status["latest_workbuddy_authority_catalog"]["catalog_summary"]["present_component_count"],
            4,
        )
        self.assertIn(
            "components=4/5",
            status["latest_workbuddy_authority_catalog"]["summary_text"],
        )

        rerun = brain.trading_workbuddy_current_skill_catalog({
            "workbuddy_skills_root": str(skills_root),
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})

    def test_workbuddy_probability_fusion_interface_contract_registers_transition_state(self):
        brain, sample = self.make_brain_with_data()
        replay = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        skills_root = Path(tmp.name) / "workbuddy_skills"
        for name in ["a-stock-data", "a-stock-analysis", "probability-fusion", "triple-decision-trees", "market-context"]:
            skill_dir = skills_root / name
            skill_dir.mkdir(parents=True, exist_ok=True)
            (skill_dir / "SKILL.md").write_text(
                textwrap.dedent(
                    f"""\
                    ---
                    name: {name}
                    disable: false
                    version: test-1
                    ---

                    # {name}
                    """
                ),
                encoding="utf-8",
            )
        brain.trading_workbuddy_current_skill_catalog({
            "workbuddy_skills_root": str(skills_root),
        })

        result = brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        contract = result["probability_fusion_interface"]
        self.assertEqual(contract["runtime_status"], "Interface")
        self.assertEqual(contract["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(contract["effective_authority_order"][0], "workbuddy_current_live_state")
        self.assertEqual(contract["precedence_rule"], "workbuddy_current_state_over_documents_and_legacy_logic")
        self.assertEqual(contract["policy"]["implementation_status"], "Interface")
        self.assertEqual(contract["conflict_behavior"]["minimum_aligned_signals"], 3)
        self.assertEqual(contract["current_engine"]["engine_name"], "direct_replay_ranking")
        self.assertEqual(contract["current_engine"]["engine_status"], "Transitional")
        self.assertEqual(contract["current_engine"]["override_status"], "pending_workbuddy_probability_fusion")
        self.assertEqual(
            contract["current_engine"]["selected_strategy_name"],
            replay["strategy_comparison"]["selected_strategy_name"],
        )
        self.assertEqual(
            contract["current_engine"]["selection_state_summary"]["target_override_engine"],
            "workbuddy_probability_fusion",
        )
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.workbuddy_probability_fusion_interface",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Interface")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["effective_authority_order"][0],
            "workbuddy_current_live_state",
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_workbuddy_probability_fusion_interface",
        )
        self.assertEqual(result["module_status_record"]["status"], "Interface")
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_workbuddy_probability_fusion_interface_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_workbuddy_probability_fusion_interface_reported",
        )
        self.assertTrue(
            any(
                "WorkBuddy probability-fusion Interface contract registered" in item
                for item in result["board_state"]["completed"]
            )
        )
        trading_status = brain.status()["trading_status"]
        self.assertEqual(
            trading_status["authority_mode"],
            "workbuddy_current_state_first",
        )
        self.assertEqual(
            trading_status["authority_catalog_status"],
            "catalog_scanned",
        )
        self.assertIn(
            "components=",
            trading_status["authority_catalog_summary_text"],
        )
        self.assertIn(
            "alias_gaps=1",
            trading_status["authority_catalog_summary_text"],
        )
        self.assertEqual(
            trading_status["authority_catalog_focus_source"],
            "latest_workbuddy_authority_catalog",
        )
        board = brain.board_status()
        self.assertEqual(
            board["latest_workbuddy_authority_catalog"]["skill_name"],
            "trading.workbuddy_current_skill_catalog",
        )
        self.assertIn(
            "trading_skills=",
            board["latest_workbuddy_authority_catalog_summary"],
        )

        rerun = brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})

    def test_workbuddy_triple_decision_trees_interface_registers_phase_constraint_contract(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        contract = result["triple_decision_trees_interface"]
        self.assertEqual(contract["runtime_status"], "Interface")
        self.assertEqual(contract["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(contract["effective_authority_order"][0], "workbuddy_current_live_state")
        self.assertEqual(contract["precedence_rule"], "workbuddy_current_state_over_documents_and_legacy_logic")
        self.assertTrue(contract["phase_gate"]["required"])
        self.assertTrue(contract["phase_gate"]["phase_must_be_identified_before_signal_interpretation"])
        self.assertIn("phase-c-d-transition", contract["phase_gate"]["phase_sources"])
        self.assertEqual(contract["integration_contract"]["upstream_engine"], "workbuddy_probability_fusion")
        self.assertEqual(contract["integration_contract"]["integration_role"], "post_fusion_constraint_layer")
        self.assertIn("main_force", contract["participant_trees"])
        self.assertIn("hot_money", contract["participant_trees"])
        self.assertIn("retail", contract["participant_trees"])
        self.assertIn("current_phase", contract["required_output_fields"])
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.workbuddy_triple_decision_trees_interface",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Interface")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_workbuddy_triple_decision_trees_interface",
        )
        self.assertEqual(result["module_status_record"]["status"], "Interface")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_workbuddy_triple_decision_trees_interface_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_workbuddy_triple_decision_trees_interface_reported",
        )
        self.assertTrue(
            any(
                "WorkBuddy triple-decision-trees Interface contract registered" in item
                for item in result["board_state"]["completed"]
            )
        )

        rerun = brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})

    def test_workbuddy_probability_fusion_mock_registers_research_only_outputs(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        fusion = result["probability_fusion_mock"]
        self.assertEqual(fusion["runtime_status"], "Experimental")
        self.assertEqual(fusion["contract_status"], "Interface")
        self.assertEqual(fusion["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(fusion["effective_authority_order"][0], "workbuddy_current_live_state")
        self.assertEqual(fusion["precedence_rule"], "workbuddy_current_state_over_documents_and_legacy_logic")
        self.assertEqual(fusion["current_engine_override_status"], "pending_workbuddy_probability_fusion")
        self.assertEqual(fusion["decision_constraint_status"], "triple_decision_trees_not_wired")
        self.assertIn("research_only_probability_fusion_mock", fusion["warnings"])
        self.assertIn("direct_replay_ranking_still_transitional", fusion["warnings"])
        self.assertAlmostEqual(
            fusion["p_bullish"] + fusion["p_neutral"] + fusion["p_bearish"],
            1.0,
            places=3,
        )
        self.assertIn(fusion["dominant_direction"], {"bullish", "neutral", "bearish"})

        signal = result["signal_record"]
        self.assertEqual(signal["status"], "Experimental")
        self.assertIn(signal["signal"], {"wait", "watch_long_research", "watch_risk_research"})

        decision = result["decision_record"]
        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["chosen"], "no_trade")
        self.assertEqual(decision["context"]["requested_action"], "no_trade")
        self.assertEqual(decision["context"]["execution_gate"], "research_only_no_trade")
        self.assertEqual(decision["context"]["effective_authority_order"][0], "workbuddy_current_live_state")
        self.assertIn("context_signal_influence", decision["context"])

        forecast = result["forecast_record"]
        self.assertEqual(len(forecast["scenarios"]), 3)
        self.assertIn("context_effect=", forecast["risk_exposure"])
        self.assertEqual(forecast["metadata"]["precedence_rule"], "workbuddy_current_state_over_documents_and_legacy_logic")
        self.assertEqual(result["trade_journal"]["status"], "Experimental")
        self.assertIn("action=no_trade", result["trade_journal"]["summary"])
        self.assertIn("research-only journal entry", result["trade_journal"]["summary"])
        self.assertIn("Promotion is blocked", result["trade_journal"]["summary"])
        self.assertEqual(
            result["trade_journal"]["metadata"]["effective_authority_order"][0],
            "workbuddy_current_live_state",
        )
        governance_entry = next(
            item for item in result["trade_journal"]["entries"] if item["entry_type"] == "governance_blockers"
        )
        self.assertTrue(governance_entry["promotion_blocked"])
        self.assertEqual(governance_entry["precedence_rule"], "workbuddy_current_state_over_documents_and_legacy_logic")
        self.assertIn("probability_fusion_runtime_is_interface", governance_entry["blockers"])
        self.assertIn("triple_decision_trees_not_wired", governance_entry["blockers"])
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.workbuddy_probability_fusion_mock",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_workbuddy_probability_fusion_mock",
        )
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertIn(
            "governance_blocker_summary",
            result["skill_registry_entry"]["metadata"],
        )
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["effective_authority_order"][0],
            "workbuddy_current_live_state",
        )
        self.assertEqual(
            result["module_status_record"]["metadata"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertIn(
            "promotion_blocked=True",
            result["module_status_record"]["summary"],
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_workbuddy_probability_fusion_mock_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_workbuddy_probability_fusion_mock_reported",
        )
        self.assertTrue(
            any(
                "WorkBuddy probability-fusion mock assembler registered" in item
                for item in result["board_state"]["completed"]
            )
        )

        rerun = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })
        self.assertTrue(rerun["changed"])
        self.assertEqual(
            rerun["self_evolution_log"]["trigger"],
            "trading_workbuddy_probability_fusion_mock_reported",
        )
        self.assertEqual(
            rerun["decision_record"]["context"]["execution_gate"],
            "research_only_no_trade",
        )

    def test_workbuddy_probability_fusion_mock_can_consume_context_signal_bundle(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.72, "leader": "300418"},
            "macro_context": {"market_pressure": -0.08, "risk_mode": "mixed"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.1},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.3},
            ],
            "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:15:00+08:00",
        })

        result = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        fusion = result["probability_fusion_mock"]
        self.assertTrue(fusion["context_signal_attached"])
        self.assertEqual(fusion["context_signal_summary"]["direction"], "bullish")
        self.assertIn("workbuddy_context_signal_attached", fusion["warnings"])
        self.assertEqual(
            fusion["context_signal_influence"]["effect_on_dominant"],
            "aligned_with_dominant",
        )
        self.assertTrue(fusion["context_signal_influence"]["aligned_non_context_skills"])
        self.assertNotIn(
            "SMA Trend v0.1",
            fusion["context_signal_influence"]["aligned_non_context_skills"],
        )
        context_lane = next(
            item
            for item in fusion["bundled_signals"]
            if item["strategy_name"] == "workbuddy_market_context_lane"
        )
        self.assertEqual(context_lane["family"], "context")
        self.assertEqual(context_lane["direction"], "bullish")
        self.assertEqual(context_lane["fusion_role"], "context_lane_bias_only")
        self.assertEqual(context_lane["execution_gate"], "research_only_no_trade")
        self.assertEqual(
            result["signal_record"]["metadata"]["probability_fusion_mock"]["context_signal_summary"]["direction"],
            "bullish",
        )
        self.assertEqual(
            result["decision_record"]["context"]["context_signal_influence"]["effect_on_dominant"],
            "aligned_with_dominant",
        )
        self.assertEqual(
            result["forecast_record"]["metadata"]["context_signal_influence"]["effect_on_dominant"],
            "aligned_with_dominant",
        )
        self.assertEqual(
            result["trade_journal"]["metadata"]["context_signal_influence"]["effect_on_dominant"],
            "aligned_with_dominant",
        )
        self.assertEqual(
            result["decision_record"]["context"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertIn(
            "weighted_multi_skill_fusion_not_live",
            result["module_status_record"]["metadata"]["governance_blocker_summary"],
        )
        governance_entry = next(
            item for item in result["trade_journal"]["entries"] if item["entry_type"] == "governance_blockers"
        )
        self.assertTrue(governance_entry["promotion_blocked"])

    def test_workbuddy_probability_fusion_mock_flags_context_conflict_against_dominant(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": -0.72, "leader": "300058"},
            "macro_context": {"market_pressure": -0.22, "risk_mode": "risk_off"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 2, "change_pct": -1.1},
                {"symbol": "300058", "relative_rank": 1, "change_pct": 1.9},
            ],
            "fund_flow_context": {"context_score": -0.41, "northbound_bias": "headwind"},
            "quote_ts": "2026-07-14T10:25:00+08:00",
        })

        result = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        fusion = result["probability_fusion_mock"]
        self.assertTrue(fusion["context_signal_attached"])
        self.assertEqual(fusion["context_signal_summary"]["direction"], "bearish")
        self.assertEqual(
            fusion["context_signal_influence"]["effect_on_dominant"],
            "conflicts_with_dominant",
        )
        self.assertIn("workbuddy_context_signal_conflicts_with_dominant", fusion["warnings"])
        self.assertEqual(fusion["key_risk"], "context_strategy_conflict")
        self.assertTrue(fusion["context_signal_influence"]["conflicting_non_context_skills"])
        self.assertEqual(
            result["trade_journal"]["metadata"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertEqual(
            result["decision_record"]["context"]["context_signal_influence"]["effect_on_dominant"],
            "conflicts_with_dominant",
        )
        self.assertIn("context_effect=conflicts_with_dominant", result["forecast_record"]["risk_exposure"])
        self.assertIn("Context effect=conflicts_with_dominant", result["trade_journal"]["summary"])
        self.assertIn(
            "triple_decision_trees_not_wired",
            result["skill_registry_entry"]["metadata"]["governance_blocker_summary"],
        )
        governance_entry = next(
            item for item in result["trade_journal"]["entries"] if item["entry_type"] == "governance_blockers"
        )
        self.assertIn("weighted_multi_skill_fusion_not_live", governance_entry["blockers"])

    def test_status_surfaces_latest_workbuddy_probability_fusion_mock_snapshot(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.72, "leader": "300418"},
            "macro_context": {"market_pressure": -0.08, "risk_mode": "mixed"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.1},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.3},
            ],
            "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:15:00+08:00",
        })
        result = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        status = brain.status()
        board = brain.board_status()
        latest_mock = status["latest_workbuddy_probability_fusion_mock"]
        self.assertEqual(latest_mock["skill_name"], "trading.workbuddy_probability_fusion_mock")
        self.assertEqual(latest_mock["runtime_status"], "Experimental")
        self.assertEqual(latest_mock["contract_status"], "Interface")
        self.assertEqual(latest_mock["execution_gate"], "research_only_no_trade")
        self.assertTrue(latest_mock["context_signal_attached"])
        self.assertEqual(latest_mock["context_signal_direction"], "bullish")
        self.assertEqual(latest_mock["signal_label"], result["probability_fusion_mock"]["signal_label"])
        self.assertEqual(latest_mock["dominant_direction"], result["probability_fusion_mock"]["dominant_direction"])
        self.assertIn(
            "weighted_multi_skill_fusion_not_live",
            latest_mock["governance_blocker_summary"],
        )
        self.assertEqual(
            status["trading_status"]["probability_fusion_runtime_status"],
            "Experimental",
        )
        self.assertEqual(
            status["trading_status"]["probability_fusion_contract_status"],
            "Interface",
        )
        self.assertEqual(
            status["trading_status"]["probability_fusion_execution_gate"],
            "research_only_no_trade",
        )
        self.assertTrue(status["trading_status"]["probability_fusion_context_signal_attached"])
        self.assertEqual(
            status["trading_status"]["probability_fusion_context_signal_direction"],
            "bullish",
        )
        self.assertEqual(
            status["trading_status"]["probability_fusion_focus_source"],
            "latest_workbuddy_probability_fusion_mock",
        )
        self.assertEqual(
            board["latest_workbuddy_probability_fusion_mock"]["signal_label"],
            latest_mock["signal_label"],
        )
        self.assertEqual(
            board["latest_workbuddy_probability_fusion_mock_summary"],
            latest_mock["summary"],
        )

    def test_workbuddy_probability_fusion_mock_detects_triple_decision_tree_interface_only_state(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        fusion = result["probability_fusion_mock"]
        self.assertEqual(fusion["decision_constraint_status"], "triple_decision_trees_interface_declared")
        self.assertIn("triple_decision_trees_interface_declared_but_not_live", fusion["warnings"])
        governance_entry = next(
            item for item in result["trade_journal"]["entries"] if item["entry_type"] == "governance_blockers"
        )
        self.assertIn("triple_decision_trees_runtime_is_interface", governance_entry["blockers"])
        self.assertNotIn("triple_decision_trees_not_wired", governance_entry["blockers"])
        self.assertIn(
            "triple_decision_trees_runtime_is_interface",
            result["skill_registry_entry"]["metadata"]["governance_blocker_summary"],
        )

    def test_workbuddy_triple_decision_trees_scaffold_consumes_probability_mock(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.72, "leader": "300418"},
            "macro_context": {"market_pressure": -0.08, "risk_mode": "mixed"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.1},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.3},
            ],
            "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:15:00+08:00",
        })
        brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_workbuddy_triple_decision_trees_scaffold({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        scaffold = result["triple_decision_trees_scaffold"]
        self.assertEqual(scaffold["runtime_status"], "Experimental")
        self.assertEqual(scaffold["contract_status"], "Interface")
        self.assertEqual(scaffold["execution_gate"], "research_only_no_trade")
        self.assertEqual(scaffold["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(scaffold["effective_authority_order"][0], "workbuddy_current_live_state")
        self.assertIn(scaffold["current_phase"], {
            "phase_d_markup_candidate",
            "phase_c_to_d_conflict_candidate",
            "phase_e_distribution_candidate",
            "phase_d_pullback_conflict_candidate",
            "phase_b_to_c_uncertain_candidate",
        })
        self.assertIn("main_force", scaffold["participant_trees"])
        self.assertIn("hot_money", scaffold["participant_trees"])
        self.assertIn("retail", scaffold["participant_trees"])
        self.assertIn("strategy_constraint_effect", scaffold)
        self.assertEqual(
            sum(scaffold["strategy_constraint_effect"]["constrained_probabilities"].values()),
            1.0,
        )
        self.assertIn("research_only_triple_decision_trees_scaffold", scaffold["warnings"])
        self.assertIn("phase_locator_not_live", scaffold["warnings"])
        self.assertEqual(result["decision_record"]["action"], "wait")
        self.assertEqual(result["decision_record"]["chosen"], "no_trade")
        self.assertEqual(result["decision_record"]["context"]["current_phase"], scaffold["current_phase"])
        self.assertEqual(result["forecast_record"]["metadata"]["triple_decision_trees_scaffold"]["current_phase"], scaffold["current_phase"])
        self.assertIn("phase=", result["forecast_record"]["risk_exposure"])
        self.assertEqual(result["trade_journal"]["status"], "Experimental")
        self.assertIn("research-only constraint preview", result["trade_journal"]["summary"])
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.workbuddy_triple_decision_trees_scaffold",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_workbuddy_triple_decision_trees_scaffold",
        )
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_workbuddy_triple_decision_trees_scaffold_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_workbuddy_triple_decision_trees_scaffold_reported",
        )
        self.assertTrue(
            any(
                "WorkBuddy triple-decision-trees scaffold registered" in item
                for item in result["board_state"]["completed"]
            )
        )

    def test_workbuddy_triple_decision_trees_scaffold_requires_probability_mock(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })

        with self.assertRaisesRegex(ValueError, "probability fusion mock"):
            brain.trading_workbuddy_triple_decision_trees_scaffold({
                "symbol": "300418",
                "timeframe": "1d",
            })

    def test_trading_replay_validation_respects_workbuddy_research_only_constraint(self):
        brain, sample = self.make_brain_with_data()
        brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "market_trend": "up",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.73, "leader": "300418"},
            "macro_context": {"market_pressure": 0.08, "risk_mode": "risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 2.7}],
            "fund_flow_context": {"context_score": 0.58, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })
        brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })
        scaffold_result = brain.trading_workbuddy_triple_decision_trees_scaffold({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })

        guard = result["validation_report"]["metadata"]["workbuddy_constraint_guard"]
        snapshot = result["validation_report"]["metadata"]["workbuddy_constraint_snapshot"]
        explanation = result["validation_report"]["metadata"]["governance_explanation"]
        rule_snapshot = result["validation_report"]["metadata"]["governance_rule_snapshot"]

        self.assertTrue(guard["blocks_promotion"])
        self.assertEqual(guard["reason_key"], "workbuddy_constraint_research_only_no_trade")
        self.assertEqual(snapshot["status"], "reported")
        self.assertEqual(
            snapshot["current_phase"],
            scaffold_result["triple_decision_trees_scaffold"]["current_phase"],
        )
        self.assertIn(
            "workbuddy_constraint_research_only_no_trade",
            result["validation_report"]["warnings"],
        )
        self.assertFalse(result["validation_report"]["effective"])
        self.assertTrue(
            any("research_only_no_trade" in item for item in explanation["reasons"])
        )
        workbuddy_rule = next(
            item
            for item in rule_snapshot["rule_evaluations"]
            if item["rule_key"] == "workbuddy_constraint_research_only_no_trade"
        )
        self.assertTrue(workbuddy_rule["triggered"])
        self.assertEqual(
            rule_snapshot["workbuddy_constraint_guard"]["reason_key"],
            "workbuddy_constraint_research_only_no_trade",
        )
        self.assertIn("scorecard", result["strategy_comparison"])
        self.assertTrue(
            any(item["workbuddy_constraint_blocked"] for item in result["strategy_comparison"]["scorecard"])
        )
        self.assertIn("wb=blocked", result["strategy_comparison"]["scorecard_summary"])
        self.assertIn("governance_actions", result["strategy_comparison"])
        self.assertTrue(
            all(
                "workbuddy_constraint_blocked" in item
                and "workbuddy_constraint_phase" in item
                and "workbuddy_constraint_summary" in item
                for item in result["strategy_comparison"]["governance_actions"]["by_strategy"]
            )
        )
        self.assertIn(
            "浼樺厛绾ц鏄?",
            result["strategy_comparison"]["governance_rollup"]["summary"],
        )
        self.assertIn(
            "浼樺厛绾ц鏄?",
            result["strategy_comparison"]["governance_actions"]["summary"],
        )
        self.assertTrue(
            any(
                item["priority_override_note"]
                for item in result["strategy_comparison"]["governance_actions"]["by_strategy"]
            )
        )

    def test_workbuddy_skill_mapping_audit_registers_records_and_repairs_board_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        docs_dir = root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        doc_path = docs_dir / "workbuddy_trading_system_mapping.md"
        doc_path.write_text(
            textwrap.dedent(
                """\
                # WorkBuddy 浜ゆ槗绯荤粺 -> 绗簩澶ц剳姣嶇郴缁?淇濈暀鏄犲皠涓庤鐩栬〃

                - 濡傛湁涓嶅悓锛屼互 WorkBuddy 褰撳墠鐜扮姸涓哄噯銆?
                - probability-fusion 瑕嗙洊 direct strategy ranking銆?
                """
            ),
            encoding="utf-8",
        )
        brain = SuperBrainV01(root)
        state = brain.board.get_state()
        state["completed"] = ["WorkBuddy ???? -> ??????? ????????????docs/workbuddy_trading_system_mapping.md??25???????????????????????"]
        state["event_log"] = [
            {
                "timestamp": "2026-07-14T00:00:00+08:00",
                "type": "workbuddy_skill_mapping_audit_registered",
                "summary": "??? WorkBuddy ????????????????? WorkBuddy ???????????? 25 ??????????/????/???/???????",
            }
        ]
        brain.store.set_meta("v0_1_announcement_board", state)
        brain.board._render(state)

        result = brain.trading_workbuddy_skill_mapping_audit({"doc_path": str(doc_path)})

        self.assertTrue(result["changed"])
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.workbuddy_skill_mapping_audit")
        self.assertEqual(result["module_status_record"]["module_name"], "trading_workbuddy_skill_mapping_audit")
        self.assertEqual(result["self_evolution_log"]["trigger"], "workbuddy_skill_mapping_audit_registered")
        self.assertEqual(result["bulletin_state_record"]["recent_event"], "workbuddy_skill_mapping_audit_registered")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(result["skill_registry_entry"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(result["module_status_record"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertTrue(
            any(
                "WorkBuddy" in item and "第二大脑" in item
                for item in result["board_state"]["completed"]
            )
        )
        board_text = brain.board.path.read_text(encoding="utf-8")
        self.assertIn("WorkBuddy", board_text)
        self.assertIn("第二大脑", board_text)
        self.assertNotIn("????", board_text)

        rerun = brain.trading_workbuddy_skill_mapping_audit({"doc_path": str(doc_path)})
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})

    def test_workbuddy_context_snapshot_can_bootstrap_from_live_market_context_skill_definition(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        skills_root = root / "workbuddy_skills" / "market-context"
        skills_root.mkdir(parents=True, exist_ok=True)
        (skills_root / "SKILL.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: market-context
                description: 甯傚満鐜鍒嗘瀽
                agent_created: true
                ---

                # Market Context

                ## 涓冦€佸叧閿鍒欓€熸煡
                | 瑙勫垯 | 鍐呭 |
                |:--|:--|
                | **鍏堟煡鏉垮潡鍐嶅垎鏋愪釜鑲?* | 姘歌繙涓嶈璺宠繃鏉垮潡瀵规瘮 |
                | **澶氭澘鍧楀姞鏉?* | 鏄嗕粦闇€瑕?涓澘鍧楀姞鏉冿紝涓嶆槸1涓?|

                ## 馃 鑱斿姩
                t1-lockup-tracking / anchoring-detection / money-flow-warfare / a-share-game-theory / sector-rotation-detection / supply-test

                ## 馃寠/馃幉/馃尦 绯荤粺鑱斿姩
                - 瑙?rotation-tide-reversal / probability-fusion / triple-decision-trees
                """
            ),
            encoding="utf-8",
        )
        brain = SuperBrainV01(root)

        result = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "workbuddy_skills_root": str(root / "workbuddy_skills"),
        })

        self.assertTrue(result["changed"])
        snapshot = result["workbuddy_context_snapshot"]
        self.assertEqual(snapshot["provider"], "market-context")
        self.assertEqual(snapshot["provider_alias"], "workbuddy_neodata_market_context")
        self.assertEqual(snapshot["connection_mode"], "live_skill_document_snapshot")
        self.assertEqual(snapshot["context_bias"], "definition_only")
        self.assertEqual(snapshot["peer_leadership"], "not_applicable")
        self.assertEqual(snapshot["skill_name"], "market-context")
        self.assertIn("probability-fusion", snapshot["linked_skills"])
        self.assertTrue(snapshot["key_rules"])
        self.assertIn("live_skill_document_only", snapshot["caveats"])
        self.assertEqual(result["context_signal_summary"]["signal_status"], "definition_only")
        self.assertEqual(result["context_signal_summary"]["direction"], "neutral")
        self.assertEqual(result["signal_record"]["signal"], "wait")
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(result["skill_registry_entry"]["validation_status"], "definition_attached")
        self.assertEqual(result["module_status_record"]["validation_status"], "definition_attached")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_workbuddy_context_snapshot_reported",
        )
        self.assertTrue(
            any(
                "A鑲?WorkBuddy 甯傚満涓婁笅鏂囧揩鐓ф帴鍙ｅ凡鎺ュ叆" in item
                for item in result["board_state"]["completed"]
            )
        )

        readiness = brain.trading_a_share_true_money_flow_readiness({"symbol": "300418", "timeframe": "1d"})
        workbuddy_row = next(
            item
            for item in readiness["true_money_flow_readiness"]["required_sources"]
            if item["source_key"] == "workbuddy_neodata_market_context"
        )
        self.assertTrue(workbuddy_row["latest_sample_available"])
        self.assertEqual(workbuddy_row["latest_sample_connection_mode"], "live_skill_document_snapshot")
        self.assertEqual(workbuddy_row["sample_quality_status"], "definition_only")

        rerun = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "workbuddy_skills_root": str(root / "workbuddy_skills"),
        })
        self.assertEqual(rerun["self_evolution_log"], {})
        if rerun["changed"]:
            self.assertEqual(
                rerun["bulletin_state_record"]["recent_event"],
                "trading_a_share_workbuddy_context_snapshot_reported",
            )

    def test_workbuddy_context_snapshot_can_load_from_json_snapshot_file(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        snapshot_path = root / "market_context_snapshot.json"
        snapshot_path.write_text(
            json.dumps(
                {
                    "symbol": "300418",
                    "timeframe": "1d",
                    "quote_ts": "2026-07-14T10:15:00+08:00",
                    "sector_flow": {"sector": "AI搴旂敤", "strength": 0.72, "leader": "300418"},
                    "macro_context": {"market_pressure": -0.08, "risk_mode": "mixed"},
                    "peer_snapshot": [
                        {"symbol": "300418", "relative_rank": 1, "change_pct": 2.1},
                        {"symbol": "300058", "relative_rank": 2, "change_pct": 1.3},
                    ],
                    "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        brain = SuperBrainV01(root)

        result = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "source_path": str(snapshot_path),
        })

        self.assertTrue(result["changed"])
        snapshot = result["workbuddy_context_snapshot"]
        self.assertEqual(snapshot["connection_mode"], "json_file_snapshot")
        self.assertEqual(snapshot["context_bias"], "supportive")
        self.assertEqual(snapshot["peer_leadership"], "leader")
        self.assertTrue(snapshot["source_path"].endswith("market_context_snapshot.json"))
        self.assertIn("json_snapshot_file_only", snapshot["caveats"])
        self.assertEqual(result["context_signal_summary"]["direction"], "bullish")
        self.assertEqual(result["context_signal_summary"]["signal_label"], "watch_long_research")
        self.assertGreater(result["context_signal_summary"]["support_score"], 0.2)
        self.assertEqual(result["signal_record"]["signal"], "watch_long_research")
        self.assertEqual(result["skill_registry_entry"]["validation_status"], "snapshot_file_attached")
        self.assertEqual(result["module_status_record"]["validation_status"], "snapshot_file_attached")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_workbuddy_context_snapshot_reported",
        )

        readiness = brain.trading_a_share_true_money_flow_readiness({"symbol": "300418", "timeframe": "1d"})
        workbuddy_row = next(
            item
            for item in readiness["true_money_flow_readiness"]["required_sources"]
            if item["source_key"] == "workbuddy_neodata_market_context"
        )
        self.assertTrue(workbuddy_row["latest_sample_available"])
        self.assertEqual(workbuddy_row["latest_sample_connection_mode"], "json_file_snapshot")
        self.assertEqual(workbuddy_row["sample_quality_status"], "sample_attached")

    def test_true_money_flow_readiness_reflects_attached_experimental_samples_without_claiming_connectivity(self):
        brain, _sample = self.make_brain_with_data()
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 2.9}],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })

        result = brain.trading_a_share_true_money_flow_readiness({"symbol": "300418", "timeframe": "1d"})

        readiness = result["true_money_flow_readiness"]
        self.assertEqual(readiness["connection_status"], "Not Implemented Yet")
        self.assertEqual(readiness["sample_attached_count"], 2)
        self.assertEqual(
            readiness["sample_attached_source_keys"],
            ["tdx_realtime_quotes", "workbuddy_neodata_market_context"],
        )
        self.assertIn("Experimental sample evidence is already attached", readiness["summary"])
        tdx_row = next(item for item in readiness["required_sources"] if item["source_key"] == "tdx_realtime_quotes")
        self.assertTrue(tdx_row["latest_sample_available"])
        self.assertEqual(tdx_row["latest_sample_status"], "sample_available")
        self.assertEqual(tdx_row["latest_sample_source_type"], "tdx_realtime_quote_snapshot")
        self.assertEqual(tdx_row["latest_sample_connection_mode"], "payload_injected_sample")
        self.assertEqual(tdx_row["sample_quality_status"], "sample_attached")
        self.assertEqual(tdx_row["latest_sample_ts"], "2026-07-11T14:39:00+08:00")
        workbuddy_row = next(item for item in readiness["required_sources"] if item["source_key"] == "workbuddy_neodata_market_context")
        self.assertTrue(workbuddy_row["latest_sample_available"])
        self.assertEqual(workbuddy_row["latest_sample_status"], "sample_available")
        self.assertEqual(workbuddy_row["latest_sample_source_type"], "workbuddy_market_context_snapshot")
        self.assertEqual(workbuddy_row["latest_sample_connection_mode"], "payload_injected_sample")

    def test_research_queue_next_validation_slice_surfaces_proxy_sample_status_in_note_and_preview(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 2.9}],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })

        readiness = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        next_slice = brain.trading_research_queue_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })

        self.assertIn("当前代理守门已挂接 2 条 sample", readiness["rows"][0]["next_validation_slice_note"])
        self.assertIn(
            "sample_available/payload_injected_sample",
            readiness["rows"][0]["next_validation_slice_note"],
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_sample_attached_count"],
            2,
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_sample_status"],
            "sample_available",
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_sample_connection_mode"],
            "payload_injected_sample",
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_source_clearance_stage"],
            "payload_sample_only",
        )
        self.assertIn(
            "payload 注入样本",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_source_clearance_summary"],
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan"][0]["status"],
            "payload_sample_only",
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["current_step_status"],
            "payload_sample_only",
        )
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_task"]["task_status"],
            "needs_live_verification",
        )
        self.assertEqual(
            next_slice["validation_task_preview"]["proxy_guard_sample_attached_count"],
            2,
        )
        self.assertEqual(
            next_slice["validation_task_preview"]["proxy_guard_priority_sample_status"],
            "sample_available",
        )
        self.assertEqual(
            next_slice["validation_task_preview"]["proxy_guard_priority_source_clearance_stage"],
            "payload_sample_only",
        )
        self.assertIn("当前代理守门已挂接 2 条 sample", next_slice["next_validation_slice_note"])
        self.assertIn("clearance_stage=payload_sample_only", next_slice["next_validation_slice_note"])
        self.assertIn(
            "TDX realtime quotes[payload_sample_only]",
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_route_plan_summary"],
        )

    def test_research_queue_next_validation_slice_uses_latest_proxy_guard_coverage_report(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        coverage_report = brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })
        self.assertEqual(
            coverage_report["proxy_diagnostics"]["priority_source_clearance_stage"],
            "waiting_for_sample",
        )

        next_slice = brain.trading_research_queue_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        latest_summary = brain.trading_research_queue_latest_validation_summary({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })

        self.assertEqual(
            next_slice["source_views"]["proxy_guard_source_coverage_report"],
            "trading_a_share_proxy_guard_source_coverage",
        )
        self.assertEqual(
            next_slice["validation_task_preview"]["proxy_guard_priority_source_clearance_stage"],
            "waiting_for_sample",
        )
        self.assertIn(
            "clearance_stage=waiting_for_sample",
            next_slice["next_validation_slice_note"],
        )
        self.assertIn(
            "route_registered_waiting_sample",
            next_slice["validation_task_preview"]["proxy_guard_route_plan_summary"],
        )
        self.assertEqual(
            latest_summary["summary"]["a_share_proxy_guard_priority_source_clearance_stage"],
            "waiting_for_sample",
        )
        self.assertEqual(
            latest_summary["source_refs"]["proxy_guard_source_coverage_source_id"],
            coverage_report["source_record"]["id"],
        )
        self.assertIn(
            "priority_stage=waiting_for_sample",
            sync_result["board_state"]["next_step"],
        )

    def test_real_data_source_registry_registers_source_records_and_governance(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_real_data_source_registry({"symbol": "300418", "timeframe": "1d"})

        self.assertTrue(result["changed"])
        self.assertEqual(result["implementation_status"], "Implemented")
        self.assertEqual(len(result["source_records"]), 6)
        self.assertEqual(result["source_records"][0]["title"], "TDX realtime quotes")
        self.assertEqual(result["source_records"][0]["uri"], "mcp://tdx_live_bridge/tdx_realtime")
        self.assertEqual(result["source_records"][0]["metadata"]["source_key"], "tdx_realtime_quotes")
        self.assertEqual(result["source_records"][1]["metadata"]["source_key"], "tencent_qt_realtime_orderbook")
        self.assertEqual(result["source_records"][1]["uri"], "http://qt.gtimg.cn")
        self.assertEqual(result["source_records"][2]["metadata"]["source_key"], "workbuddy_neodata_market_context")
        self.assertEqual(result["source_records"][2]["uri"], "workbuddy://neodata/market-context")
        self.assertEqual(result["source_records"][2]["metadata"]["bridge_entry"], "F:/aidanao/mcp/workbuddy_bridge.py")
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.a_share_real_data_source_registry")
        self.assertEqual(result["skill_registry_entry"]["status"], "Interface")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["preferred_source_chain"][:3],
            ["tdx_realtime_quotes", "tencent_qt_realtime_orderbook", "workbuddy_neodata_market_context"],
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_real_data_source_registry",
        )
        self.assertEqual(result["module_status_record"]["status"], "Interface")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_real_data_source_registry_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_real_data_source_registry_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["preferred_source_chain"][:3],
            ["tdx_realtime_quotes", "tencent_qt_realtime_orderbook", "workbuddy_neodata_market_context"],
        )
        self.assertTrue(
            any(
                "A股实时数据路线 SourceRecord 注册表已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertIsNotNone(brain.store.get("sources", result["source_records"][0]["id"]))
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_real_data_source_registry"],
            "Implemented",
        )

        rerun = brain.trading_a_share_real_data_source_registry({"symbol": "300418", "timeframe": "1d"})
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_connector_runtime_audit_reads_workbuddy_and_local_tdx_state(self):
        brain, _sample = self.make_brain_with_data()
        mcp_dir = brain.root / "mcp"
        mcp_dir.mkdir(parents=True, exist_ok=True)
        (mcp_dir / "tdx_live_bridge.py").write_text("# test bridge\n", encoding="utf-8")
        (mcp_dir / "tdx_bridge.py").write_text("# test bridge\n", encoding="utf-8")
        (mcp_dir / "workbuddy_bridge.py").write_text("# test bridge\n", encoding="utf-8")

        fake_tdx_home = brain.root / "fake_tdx"
        (fake_tdx_home / "vipdoc").mkdir(parents=True, exist_ok=True)

        tushare_raw_dir = brain.root / "data" / "raw" / "tushare"
        tushare_raw_dir.mkdir(parents=True, exist_ok=True)
        (tushare_raw_dir / "300418_daily.json").write_text("[]", encoding="utf-8")

        workbuddy_dir = brain.root / "workbuddy"
        workbuddy_dir.mkdir(parents=True, exist_ok=True)
        mcp_config = workbuddy_dir / "mcp.json"
        mcp_config.write_text(
            textwrap.dedent(
                """\
                {
                  "mcpServers": {
                    "tdx-live": {"disabled": false},
                    "tushare": {"disabled": false}
                  }
                }
                """
            ),
            encoding="utf-8",
        )

        result = brain.trading_a_share_connector_runtime_audit(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "workbuddy_mcp_path": str(mcp_config),
                "tdx_home": str(fake_tdx_home),
            }
        )

        self.assertTrue(result["changed"])
        self.assertEqual(result["implementation_status"], "Implemented")
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.a_share_connector_runtime_audit")
        self.assertEqual(result["module_status_record"]["module_name"], "trading_a_share_connector_runtime_audit")
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_a_share_connector_runtime_audit_reported")
        self.assertEqual(result["bulletin_state_record"]["recent_event"], "trading_a_share_connector_runtime_audit_reported")
        self.assertEqual(brain.status()["module_status"]["trading_a_share_connector_runtime_audit"], "Implemented")
        self.assertGreaterEqual(result["ready_count"], 2)
        self.assertGreaterEqual(result["partial_count"], 1)

        row_by_key = {item["source_key"]: item for item in result["runtime_rows"]}
        self.assertEqual(row_by_key["tdx_realtime_quotes"]["runtime_readiness"], "configured_enabled")
        self.assertEqual(row_by_key["tdx_minute_kline"]["runtime_readiness"], "local_binary_ready")
        self.assertEqual(
            row_by_key["workbuddy_neodata_market_context"]["runtime_readiness"],
            "bridge_file_with_live_skill_definition",
        )
        self.assertTrue(row_by_key["workbuddy_neodata_market_context"]["live_skill_definition_present"])
        self.assertEqual(row_by_key["tushare_financial_news"]["runtime_readiness"], "configured_enabled_with_local_raw")
        self.assertEqual(row_by_key["tencent_qt_realtime_orderbook"]["runtime_readiness"], "http_route_declared")

        rerun = brain.trading_a_share_connector_runtime_audit(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "workbuddy_mcp_path": str(mcp_config),
                "tdx_home": str(fake_tdx_home),
            }
        )
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_connector_runtime_audit_detects_live_market_context_skill_definition_without_bridge(self):
        brain, _sample = self.make_brain_with_data()
        workbuddy_dir = brain.root / "workbuddy"
        workbuddy_dir.mkdir(parents=True, exist_ok=True)
        skills_root = workbuddy_dir / "skills" / "market-context"
        skills_root.mkdir(parents=True, exist_ok=True)
        (skills_root / "SKILL.md").write_text(
            textwrap.dedent(
                """\
                ---
                name: market-context
                description: 甯傚満鐜鍒嗘瀽
                ---

                # Market Context
                """
            ),
            encoding="utf-8",
        )
        mcp_config = workbuddy_dir / "mcp.json"
        mcp_config.write_text('{"mcpServers": {}}', encoding="utf-8")

        result = brain.trading_a_share_connector_runtime_audit(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "workbuddy_mcp_path": str(mcp_config),
                "workbuddy_skills_root": str(workbuddy_dir / "skills"),
            }
        )

        row_by_key = {item["source_key"]: item for item in result["runtime_rows"]}
        workbuddy_row = row_by_key["workbuddy_neodata_market_context"]
        self.assertEqual(workbuddy_row["runtime_readiness"], "live_skill_definition_only")
        self.assertTrue(workbuddy_row["live_skill_definition_present"])
        self.assertEqual(workbuddy_row["live_skill_name"], "market-context")
        self.assertTrue(workbuddy_row["live_skill_definition_path"].endswith("/market-context/SKILL.md"))
        self.assertTrue(
            any("live market-context" in note for note in workbuddy_row["notes"])
        )
        self.assertGreaterEqual(result["partial_count"], 1)

    def test_connector_runtime_audit_surfaces_sample_quality_metadata(self):
        brain, _sample = self.make_brain_with_data()
        mcp_dir = brain.root / "mcp"
        mcp_dir.mkdir(parents=True, exist_ok=True)
        (mcp_dir / "tdx_live_bridge.py").write_text("# test bridge\n", encoding="utf-8")
        (mcp_dir / "workbuddy_bridge.py").write_text("# test bridge\n", encoding="utf-8")

        workbuddy_dir = brain.root / "workbuddy"
        workbuddy_dir.mkdir(parents=True, exist_ok=True)
        mcp_config = workbuddy_dir / "mcp.json"
        mcp_config.write_text(
            textwrap.dedent(
                """\
                {
                  "mcpServers": {
                    "tdx-live": {"disabled": false}
                  }
                }
                """
            ),
            encoding="utf-8",
        )

        brain.trading_a_share_tdx_quote_snapshot(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "ddx": 0.62,
                "ddy": 1.21,
                "change_pct": 2.84,
                "volume_ratio": 1.76,
                "price": 49.93,
                "volume": 950000,
                "amount": 47433500,
                "turnover_rate": 11.6,
                "quote_ts": "2026-07-11T14:39:00+08:00",
            }
        )
        brain.trading_a_share_tencent_qt_realtime_snapshot(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "price": 49.93,
                "change_pct": 2.9,
                "volume": 1200000,
                "amount": 59800000,
                "quote_crosscheck": "tdx_aligned",
                "bids": [{"price": 49.92, "size": 8000}],
                "asks": [{"price": 49.94, "size": 7500}],
                "quote_ts": "2026-07-11T14:39:10+08:00",
            }
        )
        brain.trading_a_share_workbuddy_context_snapshot(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
                "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
                "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 2.9}],
                "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
                "quote_ts": "2026-07-11T14:39:20+08:00",
            }
        )

        result = brain.trading_a_share_connector_runtime_audit(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "workbuddy_mcp_path": str(mcp_config),
            }
        )

        row_by_key = {item["source_key"]: item for item in result["runtime_rows"]}
        self.assertEqual(result["inadequate_sample_count"], 0)
        self.assertTrue(result["priority_sample_quality_ready"])

        tdx_row = row_by_key["tdx_realtime_quotes"]
        self.assertTrue(tdx_row["latest_sample_available"])
        self.assertEqual(tdx_row["latest_sample_status"], "sample_available")
        self.assertEqual(tdx_row["sample_quality_status"], "sample_attached")
        self.assertEqual(tdx_row["latest_sample_connection_mode"], "payload_injected_sample")
        self.assertEqual(tdx_row["latest_sample_ts"], "2026-07-11T14:39:00+08:00")

        tencent_row = row_by_key["tencent_qt_realtime_orderbook"]
        self.assertTrue(tencent_row["latest_sample_available"])
        self.assertEqual(tencent_row["sample_quality_status"], "sample_attached")
        self.assertEqual(tencent_row["latest_sample_connection_mode"], "payload_injected_sample")

        workbuddy_row = row_by_key["workbuddy_neodata_market_context"]
        self.assertTrue(workbuddy_row["latest_sample_available"])
        self.assertEqual(workbuddy_row["sample_quality_status"], "sample_attached")
        self.assertEqual(workbuddy_row["latest_sample_connection_mode"], "payload_injected_sample")

    def test_real_data_pull_plan_resolves_registry_into_ordered_next_actions(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_real_data_pull_plan({"symbol": "300418", "timeframe": "1d"})

        self.assertTrue(result["changed"])
        self.assertEqual(result["implementation_status"], "Implemented")
        self.assertGreaterEqual(len(result["plan_items"]), 3)
        self.assertEqual(result["plan_items"][0]["source_key"], "tdx_realtime_quotes")
        self.assertEqual(result["plan_items"][1]["source_key"], "tencent_qt_realtime_orderbook")
        self.assertEqual(result["plan_items"][2]["source_key"], "workbuddy_neodata_market_context")
        self.assertEqual(result["next_pull"]["source_key"], "tdx_realtime_quotes")
        self.assertIn("tdx_realtime", result["next_pull"]["command_hint"])
        self.assertTrue(result["next_actions"])
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_real_data_pull_plan",
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_real_data_pull_plan",
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_real_data_pull_plan_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_real_data_pull_plan_reported",
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_real_data_pull_plan"],
            "Implemented",
        )
        self.assertIsNotNone(
            brain.store.get("skill_registry_entries", result["skill_registry_entry"]["id"])
        )
        self.assertIsNotNone(
            brain.store.get("module_status_records", result["module_status_record"]["id"])
        )

        rerun = brain.trading_a_share_real_data_pull_plan({"symbol": "300418", "timeframe": "1d"})
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_authority_constraints_snapshot_report_writes_governance_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_authority_constraints_snapshot({"symbol": "300418", "timeframe": "1d"})

        self.assertTrue(result["changed"])
        snapshot = result["authority_constraints_snapshot"]
        self.assertEqual(snapshot["authority_document_version"], "2026-07-10")
        self.assertEqual(snapshot["authority_document_name"], "SYSTEM_REPLICATION_FOR_CODEX.md")
        self.assertTrue(snapshot["authority_scope"]["highest_precedence"])
        self.assertEqual(snapshot["authority_scope"]["trading_regime"], "T+1")
        self.assertEqual(
            snapshot["authority_source_mapping"]["live_workbuddy_skill_root"],
            "C:/Users/Administrator/.workbuddy/skills",
        )
        self.assertEqual(
            snapshot["authority_source_mapping"]["canonical_external_document"],
            "D:/LiblibAI-workspace/comfyui-deploy-win/ComfyUI/output/SYSTEM_REPLICATION_FOR_CODEX.md",
        )
        self.assertEqual(
            snapshot["authority_source_mapping"]["effective_authority_order"][0],
            "workbuddy_current_live_state",
        )
        self.assertEqual(
            snapshot["authority_source_mapping"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertTrue(
            any(
                item.endswith("/docs/SYSTEM_REPLICATION_FOR_CODEX.md")
                for item in snapshot["authority_source_mapping"]["mirror_documents"]
            )
        )
        self.assertEqual(
            snapshot["authority_source_mapping"]["effective_until"],
            "user_designates_newer_final_authority",
        )
        self.assertEqual(
            snapshot["authority_scope"]["precedence_effective_until"],
            "user_designates_newer_final_authority",
        )
        self.assertIn(
            "legacy_brain_core_proxy_logic",
            snapshot["authority_scope"]["supersedes"],
        )
        self.assertIn(
            "legacy_US_style_intraday_assumptions",
            snapshot["authority_scope"]["supersedes"],
        )
        self.assertEqual(
            snapshot["authority_precedence_policy"]["live_state_role"],
            "highest_priority_trading_runtime_authority",
        )
        self.assertEqual(
            snapshot["authority_precedence_policy"]["replacement_policy"],
            "keep_current_document_until_user_designates_newer_final_authority",
        )
        self.assertEqual(snapshot["system_layers"][1]["declared_skill_count"], 25)
        self.assertEqual(snapshot["probability_fusion_policy"]["conflict_resolution"], "weight_over_majority")
        self.assertIn("no_single_signal_trade_decision", snapshot["critical_prohibitions"])
        self.assertIn("probability-fusion", snapshot["diagnostic_skill_registry"])
        self.assertIn("pull_tdx_realtime_quotes", snapshot["analysis_startup_flow"])
        self.assertIn("pull_tencent_qt_realtime_crosscheck", snapshot["analysis_startup_flow"])
        self.assertIn("pull_workbuddy_neodata_context", snapshot["analysis_startup_flow"])
        self.assertEqual(
            snapshot["a_share_unique_cognition"]["participant_decision_profiles"]["behavior_model_status"],
            "Experimental",
        )
        self.assertIn(
            "A股 T+1 会让日换手率暴露更多筹码交换信息",
            snapshot["a_share_unique_cognition"]["turnover_information_exposure"],
        )
        self.assertIn(
            "昨日入场的 Fresh 资金到次日解锁后",
            snapshot["a_share_unique_cognition"]["fresh_unlock_branching_uncertainty"],
        )
        self.assertIn(
            "单份 Fresh 筹码当日不能完成买入再卖出",
            snapshot["a_share_unique_cognition"]["single_day_chip_exchange_limit"],
        )
        self.assertEqual(
            snapshot["trading_session_constraints"]["call_auction_cancelable"],
            "09:15-09:20",
        )
        self.assertEqual(
            snapshot["trading_session_constraints"]["call_auction_non_cancelable"],
            "09:20-09:25",
        )
        self.assertEqual(
            snapshot["trading_session_constraints"]["same_day_sell_capacity"],
            "seasoned_inventory_only",
        )
        self.assertTrue(
            any(
                item["constraint_key"] == "fresh_chip_unlock_behavior_must_stay_probabilistic"
                for item in snapshot["core_constraints"]
            )
        )
        self.assertEqual(snapshot["probability_fusion_policy"]["implementation_status"], "Interface")
        self.assertEqual(snapshot["probability_fusion_policy"]["minimum_aligned_signals"], 3)
        self.assertEqual(snapshot["required_real_data_sources"][0], "tdx_realtime_quotes")
        self.assertEqual(snapshot["required_real_data_sources"][1], "tencent_qt_realtime_orderbook")
        self.assertEqual(snapshot["required_real_data_sources"][2], "workbuddy_neodata_market_context")
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.a_share_authority_constraints_snapshot")
        self.assertEqual(result["skill_registry_entry"]["status"], "Active")
        self.assertEqual(result["skill_registry_entry"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["authority_constraints_snapshot"]["declared_skill_count"],
            25,
        )
        self.assertEqual(result["module_status_record"]["module_name"], "trading_a_share_authority_constraints_snapshot")
        self.assertEqual(result["module_status_record"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_a_share_authority_constraints_snapshot_reported")
        self.assertEqual(result["bulletin_state_record"]["recent_event"], "trading_a_share_authority_constraints_snapshot_reported")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["module_name"], "trading_a_share_authority_constraints_snapshot")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["authority_rule"], "workbuddy_current_state_first")
        self.assertTrue(
            any(
                "A股权威源映射已固化" in item and "WorkBuddy live skills" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertTrue(
            any(
                "A股最高准则结构化快照已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertTrue(
            any(
                "A股交易最高准则优先级已固化" in item and "WorkBuddy" in item
                for item in result["board_state"]["completed"]
            )
        )

    def test_authority_constraints_snapshot_rerun_repairs_stale_bulletin_state_record(self):
        brain, _sample = self.make_brain_with_data()
        initial = brain.trading_a_share_authority_constraints_snapshot({"symbol": "300418", "timeframe": "1d"})
        stale = BulletinStateRecord(
            id=initial["bulletin_state_record"]["id"],
            bulletin_path=initial["bulletin_state_record"]["bulletin_path"],
            state_status=initial["bulletin_state_record"]["state_status"],
            completed=initial["bulletin_state_record"]["completed"],
            in_progress=initial["bulletin_state_record"]["in_progress"],
            next_step=initial["bulletin_state_record"]["next_step"],
            recent_event=initial["bulletin_state_record"]["recent_event"],
            validation_status="declared",
            out_of_sample_result="not_run",
            status="Active",
            implementation_status="Implemented",
            metadata={
                "event_type": "trading_a_share_authority_constraints_snapshot_reported",
                "module_name": "trading_a_share_authority_constraints_snapshot",
                "skill_name": "trading.a_share_authority_constraints_snapshot",
                "symbol": "300418",
                "implementation_status": "Implemented",
            },
        )
        stale.created_at = initial["bulletin_state_record"]["created_at"]
        brain.store.save("bulletin_state_records", stale)

        rerun = brain.trading_a_share_authority_constraints_snapshot({"symbol": "300418", "timeframe": "1d"})
        board_state = rerun["board_state"] or brain.board.get_state()

        self.assertTrue(rerun["changed"])
        self.assertEqual(
            rerun["bulletin_state_record"]["metadata"]["authority_rule"],
            "workbuddy_current_state_first",
        )
        self.assertEqual(
            rerun["bulletin_state_record"]["metadata"]["authority_constraints_snapshot"]["authority_source_mapping"]["precedence_rule"],
            "workbuddy_current_state_over_documents_and_legacy_logic",
        )
        self.assertTrue(
            any(
                "A股交易最高准则优先级已固化" in item
                for item in board_state["completed"]
            )
        )
        self.assertTrue(
            any(
                "A股 T+1" in item and "母系统" in item
                for item in board_state["completed"]
            )
        )
        self.assertTrue(
            any(
                "A股 25技能" in item and "母系统" in item
                for item in board_state["completed"]
            )
        )
        self.assertEqual(brain.status()["module_status"]["trading_a_share_authority_constraints_snapshot"], "Implemented")

        stable_rerun = brain.trading_a_share_authority_constraints_snapshot({"symbol": "300418", "timeframe": "1d"})
        self.assertFalse(stable_rerun["changed"])
        self.assertEqual(stable_rerun["self_evolution_log"], {})
        self.assertEqual(stable_rerun["bulletin_state_record"], {})

    def test_tdx_quote_snapshot_report_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.699,
            "ddy": 1.85,
            "change_pct": 5.13,
            "volume_ratio": 1.92,
            "price": 50.42,
            "volume": 1280000,
            "amount": 64537600,
            "turnover_rate": 14.3,
            "quote_ts": "2026-07-09T14:30:00+08:00",
        })

        self.assertTrue(result["changed"])
        snapshot = result["true_money_flow_snapshot"]
        self.assertEqual(snapshot["provider"], "tdx_realtime_quotes")
        self.assertEqual(snapshot["connection_mode"], "payload_injected_sample")
        self.assertEqual(snapshot["connector_runtime_status"], "Not Implemented Yet")
        self.assertEqual(snapshot["implementation_status"], "Experimental")
        self.assertEqual(snapshot["fresh_direction"], "bullish")
        self.assertEqual(snapshot["seasoned_direction"], "bullish")
        self.assertEqual(snapshot["alignment"], "aligned")
        self.assertTrue(snapshot["required_fields_present"])
        self.assertIn("payload_injected_sample_only", snapshot["caveats"])
        self.assertEqual(snapshot["volume"], 1280000.0)
        self.assertEqual(snapshot["amount"], 64537600.0)
        self.assertEqual(result["source_record"]["source_type"], "tdx_realtime_quote_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "true_money_flow_quote_snapshot")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "market_snapshot")
        self.assertEqual(result["market_data_record"]["symbol"], "300418")
        self.assertEqual(result["market_data_record"]["bar_count"], 1)
        self.assertEqual(result["market_data_record"]["status"], "Experimental")
        self.assertEqual(
            result["market_data_record"]["metadata"]["snapshot_mode"],
            "single_quote_snapshot",
        )
        self.assertEqual(result["price_bar"]["market_data_id"], result["market_data_record"]["id"])
        self.assertEqual(result["price_bar"]["close"], 50.42)
        self.assertEqual(result["price_bar"]["open"], 50.42)
        self.assertEqual(result["price_bar"]["volume"], 1280000.0)
        self.assertEqual(result["price_bar"]["amount"], 64537600.0)
        self.assertEqual(result["price_bar"]["status"], "Experimental")
        self.assertEqual(result["skill_registry_entry"]["skill_name"], "trading.a_share_tdx_quote_snapshot")
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["market_data_record_id"],
            result["market_data_record"]["id"],
        )
        self.assertEqual(
            result["module_status_record"]["metadata"]["price_bar_id"],
            result["price_bar"]["id"],
        )
        self.assertEqual(result["module_status_record"]["module_name"], "trading_a_share_tdx_quote_snapshot")
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_a_share_tdx_quote_snapshot_reported")
        self.assertEqual(result["bulletin_state_record"]["recent_event"], "trading_a_share_tdx_quote_snapshot_reported")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["module_name"], "trading_a_share_tdx_quote_snapshot")
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["market_data_record_id"],
            result["market_data_record"]["id"],
        )
        self.assertTrue(
            any(
                "A鑲?TDX 瀹炴椂鎶ヤ环鐪熻祫閲戝揩鐓ф帴鍙ｅ凡鎺ュ叆" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(brain.status()["module_status"]["trading_a_share_tdx_quote_snapshot"], "Implemented")
        self.assertIsNotNone(
            brain.store.get("market_data_records", result["market_data_record"]["id"])
        )
        self.assertIsNotNone(brain.store.get("price_bars", result["price_bar"]["id"]))

        rerun = brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.699,
            "ddy": 1.85,
            "change_pct": 5.13,
            "volume_ratio": 1.92,
            "price": 50.42,
            "volume": 1280000,
            "amount": 64537600,
            "turnover_rate": 14.3,
            "quote_ts": "2026-07-09T14:30:00+08:00",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_tdx_quote_snapshot_can_sync_proxy_guard_summary_for_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        result = brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })

        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["proxy_guard_source_coverage_report"])
        self.assertTrue(result["research_queue_sync"])
        self.assertEqual(
            result["proxy_guard_source_coverage_report"]["proxy_diagnostics"]["priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_sample_status"],
            "sample_available",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        latest_skill = next(
            row
            for row in brain.store.list_records("skill_registry_entries", limit=200, newest=True)
            if str((row.get("metadata", {}) or {}).get("candidate_slug", "") or "") == "vwap"
            and str(row.get("skill_name", "") or "") == "trading.research_queue.vwap_v0_1"
        )
        self.assertEqual(latest_skill["metadata"]["candidate_slug"], "vwap")
        self.assertEqual(
            latest_skill["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )

    def test_westock_fund_flow_history_snapshot_reads_local_ddx_style_file_without_overclaiming_ddx(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        data_path = Path(tmp.name) / "data" / "kl_ddx_1y.json"
        data_path.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for index in range(28):
            rows.append(
                {
                    "d": f"2026-07-{index + 1:02d}",
                    "c": f"{40.0 + index / 10:.2f}",
                    "main": float(1000000 * ((-1) ** index)),
                    "jumbo": float(500000 * ((-1) ** (index + 1))),
                    "mid": 0.0,
                    "small": 0.0,
                    "block": 0.0,
                }
            )
        data_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")

        result = brain.trading_a_share_westock_fund_flow_history_snapshot(
            {
                "symbol": "300418",
                "timeframe": "1d",
                "source_path": str(data_path),
            }
        )

        self.assertTrue(result["changed"])
        self.assertEqual(result["westock_fund_flow_snapshot"]["connection_mode"], "json_file_snapshot")
        self.assertEqual(result["westock_fund_flow_snapshot"]["bar_count"], 28)
        self.assertFalse(result["westock_fund_flow_snapshot"]["supports_required_fields"])
        self.assertEqual(result["westock_fund_flow_snapshot"]["missing_required_fields"], ["ddx"])
        self.assertIsNone(result["westock_fund_flow_snapshot"]["latest_ddx"])
        self.assertEqual(result["sample_quality"]["status"], "missing_required_fields")
        self.assertEqual(result["module_status_record"]["quality_action"], "needs_review")
        self.assertIn("explicit DDX field is still missing", result["westock_fund_flow_snapshot"]["summary"])

    def test_tencent_qt_realtime_snapshot_report_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.91,
            "change_pct": 2.41,
            "volume": 938000,
            "amount": 46825580,
            "northbound_flow": 1250000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.90, "size": 8200},
                {"price": 49.89, "size": 6100},
            ],
            "asks": [
                {"price": 49.92, "size": 7900},
                {"price": 49.93, "size": 6800},
            ],
            "quote_ts": "2026-07-11T14:28:00+08:00",
        })

        self.assertTrue(result["changed"])
        snapshot = result["tencent_qt_snapshot"]
        self.assertEqual(snapshot["provider"], "tencent_qt_realtime_orderbook")
        self.assertEqual(snapshot["connection_mode"], "payload_injected_sample")
        self.assertEqual(snapshot["connector_runtime_status"], "Not Implemented Yet")
        self.assertEqual(snapshot["implementation_status"], "Experimental")
        self.assertEqual(snapshot["best_bid"], 49.9)
        self.assertEqual(snapshot["best_ask"], 49.92)
        self.assertEqual(snapshot["spread"], 0.02)
        self.assertEqual(snapshot["order_book_bias"], "balanced")
        self.assertEqual(snapshot["quote_crosscheck"], "aligned_with_tdx_sample")
        self.assertTrue(snapshot["required_fields_present"])
        self.assertIn("payload_injected_sample_only", snapshot["caveats"])
        self.assertEqual(result["source_record"]["source_type"], "tencent_qt_realtime_orderbook_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "realtime_orderbook_crosscheck_snapshot")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "market_snapshot")
        self.assertEqual(result["market_data_record"]["symbol"], "300418")
        self.assertEqual(result["market_data_record"]["bar_count"], 1)
        self.assertEqual(result["market_data_record"]["status"], "Experimental")
        self.assertEqual(result["price_bar"]["market_data_id"], result["market_data_record"]["id"])
        self.assertEqual(result["price_bar"]["close"], 49.91)
        self.assertEqual(result["price_bar"]["high"], 49.92)
        self.assertEqual(result["price_bar"]["low"], 49.9)
        self.assertEqual(result["price_bar"]["status"], "Experimental")
        self.assertEqual(result["order_book_snapshot"]["symbol"], "300418")
        self.assertEqual(result["order_book_snapshot"]["source_id"], result["source_record"]["id"])
        self.assertEqual(result["order_book_snapshot"]["status"], "Experimental")
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_tencent_qt_realtime_snapshot",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["skill_registry_entry"]["metadata"]["order_book_snapshot_id"],
            result["order_book_snapshot"]["id"],
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_tencent_qt_realtime_snapshot",
        )
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_tencent_qt_realtime_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_tencent_qt_realtime_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["order_book_snapshot_id"],
            result["order_book_snapshot"]["id"],
        )
        self.assertTrue(
            any(
                "A股腾讯 qt 实时盘口交叉校验快照接口已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_tencent_qt_realtime_snapshot"],
            "Implemented",
        )
        self.assertIsNotNone(
            brain.store.get("market_data_records", result["market_data_record"]["id"])
        )
        self.assertIsNotNone(brain.store.get("price_bars", result["price_bar"]["id"]))
        self.assertIsNotNone(
            brain.store.get("order_book_snapshots", result["order_book_snapshot"]["id"])
        )

        rerun = brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.91,
            "change_pct": 2.41,
            "volume": 938000,
            "amount": 46825580,
            "northbound_flow": 1250000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.90, "size": 8200},
                {"price": 49.89, "size": 6100},
            ],
            "asks": [
                {"price": 49.92, "size": 7900},
                {"price": 49.93, "size": 6800},
            ],
            "quote_ts": "2026-07-11T14:28:00+08:00",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_tencent_qt_realtime_snapshot_can_sync_proxy_guard_summary_for_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        result = brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.93, "size": 12000},
                {"price": 49.92, "size": 9000},
            ],
            "asks": [
                {"price": 49.95, "size": 8000},
                {"price": 49.96, "size": 7600},
            ],
            "quote_ts": "2026-07-14T10:40:00+08:00",
        })

        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["proxy_guard_source_coverage_report"])
        self.assertTrue(result["research_queue_sync"])
        self.assertEqual(
            result["proxy_guard_source_coverage_report"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        latest_tencent_skill = next(
            row
            for row in brain.store.list_records("skill_registry_entries", limit=200, newest=True)
            if str(row.get("skill_name", "") or "") == "trading.a_share_tencent_qt_realtime_snapshot"
        )
        self.assertEqual(
            latest_tencent_skill["metadata"]["order_book_snapshot_id"],
            result["order_book_snapshot"]["id"],
        )

    def test_workbuddy_context_snapshot_report_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.62, "leader": "300418"},
            "macro_context": {"market_pressure": 0.08, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.8},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.7},
            ],
            "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:35:00+08:00",
        })

        self.assertTrue(result["changed"])
        snapshot = result["workbuddy_context_snapshot"]
        self.assertEqual(snapshot["provider"], "workbuddy_neodata_market_context")
        self.assertEqual(snapshot["connection_mode"], "payload_injected_sample")
        self.assertEqual(snapshot["connector_runtime_status"], "Not Implemented Yet")
        self.assertEqual(snapshot["implementation_status"], "Experimental")
        self.assertEqual(snapshot["context_bias"], "supportive")
        self.assertEqual(snapshot["peer_leadership"], "leader")
        self.assertEqual(snapshot["peer_count"], 2)
        self.assertTrue(snapshot["required_fields_present"])
        self.assertIn("payload_injected_sample_only", snapshot["caveats"])
        self.assertEqual(result["context_signal_summary"]["direction"], "bullish")
        self.assertEqual(result["signal_record"]["signal"], "watch_long_research")
        self.assertEqual(result["signal_record"]["validation_status"], "sample_attached")
        self.assertEqual(result["source_record"]["source_type"], "workbuddy_market_context_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "market_context_snapshot")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "market_context_snapshot")
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_workbuddy_context_snapshot",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_workbuddy_context_snapshot",
        )
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_workbuddy_context_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_workbuddy_context_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["module_name"],
            "trading_a_share_workbuddy_context_snapshot",
        )
        self.assertTrue(
            any(
                "A鑲?WorkBuddy 甯傚満涓婁笅鏂囧揩鐓ф帴鍙ｅ凡鎺ュ叆" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_workbuddy_context_snapshot"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("sources", result["source_record"]["id"]))
        self.assertIsNotNone(brain.store.get("evidence", result["evidence_item"]["id"]))
        self.assertIsNotNone(brain.store.get("atoms", result["knowledge_atom"]["id"]))
        self.assertIsNotNone(brain.store.get("signal_records", result["signal_record"]["id"]))

        rerun = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.62, "leader": "300418"},
            "macro_context": {"market_pressure": 0.08, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.8},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.7},
            ],
            "fund_flow_context": {"context_score": 0.41, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:35:00+08:00",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_workbuddy_context_snapshot_can_sync_proxy_guard_summary_for_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        result = brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.66, "leader": "300418"},
            "macro_context": {"market_pressure": 0.02, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 3.1},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.4},
            ],
            "fund_flow_context": {"context_score": 0.47, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:20:00+08:00",
        })

        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["proxy_guard_source_coverage_report"])
        self.assertTrue(result["research_queue_sync"])
        self.assertEqual(
            result["proxy_guard_source_coverage_report"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        latest_workbuddy_skill = next(
            row
            for row in brain.store.list_records("skill_registry_entries", limit=200, newest=True)
            if str(row.get("skill_name", "") or "") == "trading.a_share_workbuddy_context_snapshot"
        )
        self.assertEqual(
            latest_workbuddy_skill["metadata"]["signal_record_id"],
            result["signal_record"]["id"],
        )

    def test_realtime_crosscheck_summary_aggregates_three_experimental_lanes(self):
        brain, _sample = self.make_brain_with_data()
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.93, "size": 12000},
                {"price": 49.92, "size": 9000},
            ],
            "asks": [
                {"price": 49.95, "size": 8000},
                {"price": 49.96, "size": 7600},
            ],
            "quote_ts": "2026-07-11T14:39:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.9},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.5},
            ],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })

        result = brain.trading_a_share_realtime_crosscheck_summary({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        summary = result["crosscheck_summary"]
        self.assertEqual(summary["tdx_signal"], "supportive")
        self.assertEqual(summary["tencent_signal"], "supportive")
        self.assertEqual(summary["workbuddy_signal"], "supportive")
        self.assertEqual(summary["alignment"], "aligned_supportive")
        self.assertEqual(summary["recommended_action"], "watch")
        self.assertTrue(summary["needs_review"])
        self.assertEqual(summary["primary_risk"], "experimental_connector_gap")
        self.assertIn("read-only research output", summary["warnings"][1])
        self.assertEqual(result["source_record"]["source_type"], "a_share_realtime_crosscheck_summary")
        self.assertEqual(result["evidence_item"]["evidence_type"], "realtime_crosscheck_summary")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "crosscheck_summary")
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_realtime_crosscheck_summary",
        )
        self.assertEqual(result["skill_registry_entry"]["status"], "Experimental")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_realtime_crosscheck_summary",
        )
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_realtime_crosscheck_summary_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_realtime_crosscheck_summary_reported",
        )
        self.assertTrue(
            any(
                "A股三路实时交叉校验摘要接口已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_realtime_crosscheck_summary"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("sources", result["source_record"]["id"]))
        self.assertIsNotNone(brain.store.get("evidence", result["evidence_item"]["id"]))
        self.assertIsNotNone(brain.store.get("atoms", result["knowledge_atom"]["id"]))

        rerun = brain.trading_a_share_realtime_crosscheck_summary({
            "symbol": "300418",
            "timeframe": "1d",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_realtime_crosscheck_summary_can_sync_proxy_guard_summary_for_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-14T10:39:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [{"price": 49.93, "size": 12000}],
            "asks": [{"price": 49.95, "size": 8000}],
            "quote_ts": "2026-07-14T10:39:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.66, "leader": "300418"},
            "macro_context": {"market_pressure": 0.02, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 3.1}],
            "fund_flow_context": {"context_score": 0.47, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:39:20+08:00",
        })

        result = brain.trading_a_share_realtime_crosscheck_summary({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["proxy_guard_source_coverage_report"])
        self.assertTrue(result["research_queue_sync"])
        self.assertEqual(result["proxy_guard_source_coverage_report"]["candidate_slug"], "vwap")
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )

    def test_realtime_crosscheck_research_bridge_writes_research_decision_and_forecast(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.93, "size": 12000},
                {"price": 49.92, "size": 9000},
            ],
            "asks": [
                {"price": 49.95, "size": 8000},
                {"price": 49.96, "size": 7600},
            ],
            "quote_ts": "2026-07-11T14:39:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.9},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.5},
            ],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })
        brain.trading_a_share_realtime_crosscheck_summary({
            "symbol": "300418",
            "timeframe": "1d",
        })

        result = brain.trading_a_share_realtime_crosscheck_research_bridge({
            "symbol": "300418",
            "timeframe": "1d",
        })

        self.assertTrue(result["changed"])
        self.assertEqual(result["decision_record"]["decision_type"], "research_crosscheck")
        self.assertEqual(result["decision_record"]["action"], "watch")
        self.assertIn(result["decision_record"]["action"], {"watch", "wait", "no_trade"})
        self.assertLessEqual(result["decision_record"]["confidence"], 0.7)
        self.assertIn("research_mode_only", result["decision_record"]["warnings"])
        self.assertEqual(result["forecast_record"]["probability"], 0.62)
        self.assertLessEqual(result["forecast_record"]["confidence"], 0.7)
        self.assertIn(
            "cn_a_research_mode_experimental_realtime_crosscheck",
            result["forecast_record"]["risk_exposure"],
        )
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_realtime_crosscheck_research_bridge",
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_realtime_crosscheck_research_bridge",
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_realtime_crosscheck_research_bridge_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_realtime_crosscheck_research_bridge_reported",
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_realtime_crosscheck_research_bridge"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("decisions", result["decision_record"]["id"]))
        self.assertIsNotNone(brain.store.get("forecasts", result["forecast_record"]["id"]))
        self.assertTrue(
            any(
                "A股三路交叉校验研究态判断桥已接入" in item
                for item in result["board_state"]["completed"]
            )
        )

        rerun = brain.trading_a_share_realtime_crosscheck_research_bridge({
            "symbol": "300418",
            "timeframe": "1d",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_realtime_crosscheck_research_bridge_can_sync_proxy_guard_summary_for_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-14T10:41:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [{"price": 49.93, "size": 12000}],
            "asks": [{"price": 49.95, "size": 8000}],
            "quote_ts": "2026-07-14T10:41:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.66, "leader": "300418"},
            "macro_context": {"market_pressure": 0.02, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 3.1}],
            "fund_flow_context": {"context_score": 0.47, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:41:20+08:00",
        })

        result = brain.trading_a_share_realtime_crosscheck_research_bridge({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["proxy_guard_source_coverage_report"])
        self.assertTrue(result["research_queue_sync"])
        self.assertEqual(result["proxy_guard_source_coverage_report"]["candidate_slug"], "vwap")
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            result["research_queue_sync"]["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )

    def test_research_queue_readiness_surfaces_latest_realtime_crosscheck_for_proxy_guard(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-14T10:43:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [{"price": 49.93, "size": 12000}],
            "asks": [{"price": 49.95, "size": 8000}],
            "quote_ts": "2026-07-14T10:43:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.66, "leader": "300418"},
            "macro_context": {"market_pressure": 0.02, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 3.1}],
            "fund_flow_context": {"context_score": 0.47, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-14T10:43:20+08:00",
        })
        brain.trading_a_share_realtime_crosscheck_summary({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        readiness = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        crosscheck = readiness["rows"][0]["validation_task_preview"]["latest_realtime_crosscheck"]
        self.assertTrue(crosscheck["attached"])
        self.assertEqual(crosscheck["alignment"], "aligned_supportive")
        self.assertEqual(crosscheck["clearance_status"], "supportive_but_not_sufficient")
        self.assertIn("涓嶈兘鍗曠嫭瑙ｉ櫎 A鑲′唬鐞嗗畧闂?", crosscheck["clearance_summary"])
        self.assertEqual(
            readiness["rows"][0]["validation_task_preview"]["proxy_guard_priority_source_clearance_stage"],
            "payload_sample_only",
        )
        proxy_gate = readiness["rows"][0]["review_checklist"]["items"][3]["acceptance_gate"]
        self.assertEqual(
            proxy_gate["latest_realtime_crosscheck"]["alignment"],
            "aligned_supportive",
        )
        self.assertEqual(
            proxy_gate["latest_realtime_crosscheck"]["clearance_status"],
            "supportive_but_not_sufficient",
        )
        self.assertEqual(
            proxy_gate["priority_source_clearance_stage"],
            "payload_sample_only",
        )
        self.assertIn("payload 娉ㄥ叆鏍锋湰", proxy_gate["priority_source_clearance_summary"])
        self.assertIn("涓嶈兘鍗曠嫭瑙ｉ櫎 A鑲′唬鐞嗗畧闂?", proxy_gate["summary"])

    def test_tdx_minute_kline_snapshot_report_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_tdx_minute_kline_snapshot({
            "symbol": "300418",
            "timeframe": "5m",
            "period": "5min",
            "minute_bars": [
                {"date": "20260711", "time_str": "09:35", "open": 49.10, "high": 49.30, "low": 49.05, "close": 49.22, "amount": 1200000, "volume": 24000, "up_count": 18, "down_count": 12},
                {"date": "20260711", "time_str": "09:40", "open": 49.22, "high": 49.38, "low": 49.18, "close": 49.34, "amount": 1380000, "volume": 26800, "up_count": 20, "down_count": 11},
                {"date": "20260711", "time_str": "09:45", "open": 49.34, "high": 49.48, "low": 49.28, "close": 49.41, "amount": 1490000, "volume": 28100, "up_count": 22, "down_count": 10},
            ],
        })

        self.assertTrue(result["changed"])
        self.assertEqual(result["period"], "5min")
        self.assertEqual(result["source_record"]["source_type"], "tdx_minute_kline_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "tdx_minute_kline_snapshot")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "market_snapshot")
        self.assertEqual(result["tdx_minute_snapshot"]["bar_count"], 3)
        self.assertEqual(result["tdx_minute_snapshot"]["connection_mode"], "payload_injected_sample")
        self.assertEqual(result["market_data_record"]["bar_count"], 3)
        self.assertEqual(result["market_data_record"]["timeframe"], "5m")
        self.assertEqual(len(result["price_bars_preview"]), 3)
        self.assertEqual(result["price_bars_preview"][-1]["close"], 49.41)
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_tdx_minute_kline_snapshot",
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_tdx_minute_kline_snapshot",
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_tdx_minute_kline_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_tdx_minute_kline_snapshot_reported",
        )
        self.assertTrue(
            any(
                "A鑲?TDX 鍒嗛挓K绾垮揩鐓ф帴鍙ｅ凡鎺ュ叆" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_tdx_minute_kline_snapshot"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("market_data_records", result["market_data_record"]["id"]))

        rerun = brain.trading_a_share_tdx_minute_kline_snapshot({
            "symbol": "300418",
            "timeframe": "5m",
            "period": "5min",
            "minute_bars": [
                {"date": "20260711", "time_str": "09:35", "open": 49.10, "high": 49.30, "low": 49.05, "close": 49.22, "amount": 1200000, "volume": 24000, "up_count": 18, "down_count": 12},
                {"date": "20260711", "time_str": "09:40", "open": 49.22, "high": 49.38, "low": 49.18, "close": 49.34, "amount": 1380000, "volume": 26800, "up_count": 20, "down_count": 11},
                {"date": "20260711", "time_str": "09:45", "open": 49.34, "high": 49.48, "low": 49.28, "close": 49.41, "amount": 1490000, "volume": 28100, "up_count": 22, "down_count": 10},
            ],
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_westock_fund_flow_history_snapshot_report_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        result = brain.trading_a_share_westock_fund_flow_history_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "fund_flow_history": [
                {"trade_date": "20260708", "main_net_flow": 12500000, "jumbo_net_flow": 5100000, "ddx": 0.18},
                {"trade_date": "20260709", "main_net_flow": 18400000, "jumbo_net_flow": 8200000, "ddx": 0.41},
                {"trade_date": "20260710", "main_net_flow": -3200000, "jumbo_net_flow": 1200000, "ddx": -0.07},
            ],
        })

        self.assertTrue(result["changed"])
        self.assertEqual(result["source_record"]["source_type"], "westock_fund_flow_history_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "westock_fund_flow_history_snapshot")
        self.assertEqual(result["knowledge_atom"]["atom_type"], "market_snapshot")
        self.assertEqual(result["westock_fund_flow_snapshot"]["bar_count"], 3)
        self.assertEqual(result["westock_fund_flow_snapshot"]["connection_mode"], "payload_injected_sample")
        self.assertEqual(result["westock_fund_flow_snapshot"]["latest_ddx"], -0.07)
        self.assertEqual(result["westock_fund_flow_snapshot"]["baseline_bias"], "mixed")
        self.assertEqual(result["sample_quality"]["status"], "insufficient_history")
        self.assertEqual(result["market_data_record"]["bar_count"], 3)
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_westock_fund_flow_history_snapshot",
        )
        self.assertEqual(result["skill_registry_entry"]["validation_status"], "needs_review")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_westock_fund_flow_history_snapshot",
        )
        self.assertEqual(result["module_status_record"]["quality_action"], "needs_review")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_westock_fund_flow_history_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_westock_fund_flow_history_snapshot_reported",
        )
        self.assertEqual(result["bulletin_state_record"]["validation_status"], "needs_review")
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["sample_quality"]["status"],
            "insufficient_history",
        )
        self.assertTrue(
            any(
                "A鑲?WeStock 鍘嗗彶璧勯噾娴佸揩鐓ф帴鍙ｅ凡鎺ュ叆" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_westock_fund_flow_history_snapshot"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("market_data_records", result["market_data_record"]["id"]))

        rerun = brain.trading_a_share_westock_fund_flow_history_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "fund_flow_history": [
                {"trade_date": "20260708", "main_net_flow": 12500000, "jumbo_net_flow": 5100000, "ddx": 0.18},
                {"trade_date": "20260709", "main_net_flow": 18400000, "jumbo_net_flow": 8200000, "ddx": 0.41},
                {"trade_date": "20260710", "main_net_flow": -3200000, "jumbo_net_flow": 1200000, "ddx": -0.07},
            ],
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_tushare_moneyflow_fallback_snapshot_reads_local_raw_and_writes_mother_system_records(self):
        brain, _sample = self.make_brain_with_data()
        raw_dir = brain.root / "data" / "raw" / "tushare"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "300418_moneyflow.json"
        raw_path.write_text(
            '[["20260708",1,2,3,4,5,6,7,2,11,1200.5],["20260709",2,1,4,3,6,5,8,3,12,1800.0],["20260710",3,2,5,4,7,6,4,9,-6,-420.25]]',
            encoding="utf-8",
        )

        result = brain.trading_a_share_tushare_moneyflow_history_fallback_snapshot(
            {"symbol": "300418", "timeframe": "1d"}
        )

        self.assertTrue(result["changed"])
        self.assertEqual(result["implementation_status"], "Implemented")
        self.assertEqual(result["source_record"]["source_type"], "tushare_moneyflow_history_fallback_snapshot")
        self.assertEqual(result["evidence_item"]["evidence_type"], "tushare_moneyflow_history_fallback_snapshot")
        self.assertEqual(result["tushare_moneyflow_fallback_snapshot"]["bar_count"], 3)
        self.assertEqual(result["tushare_moneyflow_fallback_snapshot"]["connection_mode"], "local_tushare_raw_snapshot")
        self.assertFalse(result["tushare_moneyflow_fallback_snapshot"]["supports_required_fields"])
        self.assertEqual(result["tushare_moneyflow_fallback_snapshot"]["missing_required_fields"], ["ddx"])
        self.assertEqual(result["sample_quality"]["status"], "missing_required_fields")
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_tushare_moneyflow_history_fallback_snapshot",
        )
        self.assertEqual(result["skill_registry_entry"]["validation_status"], "needs_review")
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_tushare_moneyflow_history_fallback_snapshot",
        )
        self.assertEqual(result["module_status_record"]["quality_action"], "needs_review")
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_tushare_moneyflow_history_fallback_snapshot_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_tushare_moneyflow_history_fallback_snapshot_reported",
        )
        self.assertEqual(result["bulletin_state_record"]["validation_status"], "needs_review")
        self.assertEqual(
            result["bulletin_state_record"]["metadata"]["sample_quality"]["status"],
            "missing_required_fields",
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_tushare_moneyflow_history_fallback_snapshot"],
            "Implemented",
        )

        rerun = brain.trading_a_share_tushare_moneyflow_history_fallback_snapshot(
            {"symbol": "300418", "timeframe": "1d"}
        )
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_tushare_fallback_rerun_repairs_stale_bulletin_state_record(self):
        brain, _sample = self.make_brain_with_data()
        raw_dir = brain.root / "data" / "raw" / "tushare"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / "300418_moneyflow.json"
        raw_path.write_text(
            '[["20260708",1,2,3,4,5,6,7,2,11,1200.5],["20260709",2,1,4,3,6,5,8,3,12,1800.0],["20260710",3,2,5,4,7,6,4,9,-6,-420.25]]',
            encoding="utf-8",
        )

        initial = brain.trading_a_share_tushare_moneyflow_history_fallback_snapshot(
            {"symbol": "300418", "timeframe": "1d"}
        )
        stale = BulletinStateRecord(
            id=initial["bulletin_state_record"]["id"],
            bulletin_path=initial["bulletin_state_record"]["bulletin_path"],
            state_status=initial["bulletin_state_record"]["state_status"],
            completed=initial["bulletin_state_record"]["completed"],
            in_progress=initial["bulletin_state_record"]["in_progress"],
            next_step=initial["bulletin_state_record"]["next_step"],
            recent_event=initial["bulletin_state_record"]["recent_event"],
            validation_status="fallback_attached",
            out_of_sample_result="not_run",
            status="Experimental",
            implementation_status="Implemented",
            metadata={
                "event_type": "trading_a_share_tushare_moneyflow_history_fallback_snapshot_reported",
                "module_name": "trading_a_share_tushare_moneyflow_history_fallback_snapshot",
                "skill_name": "trading.a_share_tushare_moneyflow_history_fallback_snapshot",
                "symbol": "300418",
                "implementation_status": "Implemented",
            },
        )
        stale.created_at = initial["bulletin_state_record"]["created_at"]
        brain.store.save("bulletin_state_records", stale)

        rerun = brain.trading_a_share_tushare_moneyflow_history_fallback_snapshot(
            {"symbol": "300418", "timeframe": "1d"}
        )

        self.assertTrue(rerun["changed"])
        self.assertEqual(rerun["bulletin_state_record"]["validation_status"], "needs_review")
        self.assertEqual(
            rerun["bulletin_state_record"]["metadata"]["sample_quality"]["status"],
            "missing_required_fields",
        )

    def test_a_share_proxy_guard_source_coverage_report_writes_mother_system_records(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [
                {"price": 49.93, "size": 12000},
                {"price": 49.92, "size": 9000},
            ],
            "asks": [
                {"price": 49.95, "size": 8000},
                {"price": 49.96, "size": 7600},
            ],
            "quote_ts": "2026-07-11T14:39:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.9},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.5},
            ],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })

        result = brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        self.assertTrue(result["changed"])
        self.assertEqual(result["candidate_slug"], "vwap")
        self.assertTrue(result["validation_round_key"])
        self.assertEqual(
            result["source_record"]["source_type"],
            "a_share_proxy_guard_source_coverage_report",
        )
        self.assertEqual(
            result["evidence_item"]["evidence_type"],
            "a_share_proxy_guard_source_coverage",
        )
        self.assertEqual(
            result["knowledge_atom"]["atom_type"],
            "proxy_guard_source_coverage",
        )
        self.assertEqual(len(result["coverage_rows"]), 6)
        self.assertTrue(all(item["has_registered_route"] for item in result["coverage_rows"]))
        self.assertEqual(
            len([item for item in result["coverage_rows"] if item["coverage_status"] == "sample_available"]),
            3,
        )
        self.assertTrue(
            any(item["source_key"] == "westock_fund_flow_history" and item["coverage_status"] == "route_only" for item in result["coverage_rows"])
        )
        self.assertTrue(
            any(item["source_key"] == "tdx_minute_kline" and item["coverage_status"] == "route_only" for item in result["coverage_rows"])
        )
        self.assertEqual(
            result["proxy_diagnostics"]["priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            result["skill_registry_entry"]["skill_name"],
            "trading.a_share_proxy_guard_source_coverage",
        )
        self.assertEqual(
            result["module_status_record"]["module_name"],
            "trading_a_share_proxy_guard_source_coverage",
        )
        self.assertEqual(
            result["self_evolution_log"]["trigger"],
            "trading_a_share_proxy_guard_source_coverage_reported",
        )
        self.assertEqual(
            result["bulletin_state_record"]["recent_event"],
            "trading_a_share_proxy_guard_source_coverage_reported",
        )
        self.assertTrue(
            any(
                "A股代理守门证据覆盖报告已接入" in item
                for item in result["board_state"]["completed"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_a_share_proxy_guard_source_coverage"],
            "Implemented",
        )
        self.assertIsNotNone(brain.store.get("sources", result["source_record"]["id"]))
        self.assertIsNotNone(brain.store.get("evidence", result["evidence_item"]["id"]))
        self.assertIsNotNone(brain.store.get("atoms", result["knowledge_atom"]["id"]))

        rerun = brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })
        self.assertFalse(rerun["changed"])
        self.assertEqual(rerun["self_evolution_log"], {})
        self.assertEqual(rerun["bulletin_state_record"], {})

    def test_a_share_proxy_guard_source_coverage_counts_westock_and_tdx_minute_samples(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_tencent_qt_realtime_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "price": 49.94,
            "change_pct": 2.85,
            "volume": 951000,
            "amount": 47483940,
            "northbound_flow": 1420000,
            "quote_crosscheck": "aligned_with_tdx_sample",
            "bids": [{"price": 49.93, "size": 12000}],
            "asks": [{"price": 49.95, "size": 8000}],
            "quote_ts": "2026-07-11T14:39:10+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [
                {"symbol": "300418", "relative_rank": 1, "change_pct": 2.9},
                {"symbol": "300058", "relative_rank": 2, "change_pct": 1.5},
            ],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })
        brain.trading_a_share_westock_fund_flow_history_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "fund_flow_history": [
                {"trade_date": "20260708", "main_net_flow": 12500000, "jumbo_net_flow": 5100000, "ddx": 0.18},
                {"trade_date": "20260709", "main_net_flow": 18400000, "jumbo_net_flow": 8200000, "ddx": 0.41},
                {"trade_date": "20260710", "main_net_flow": -3200000, "jumbo_net_flow": 1200000, "ddx": -0.07},
            ],
        })
        brain.trading_a_share_tdx_minute_kline_snapshot({
            "symbol": "300418",
            "timeframe": "5m",
            "period": "5min",
            "minute_bars": [
                {"date": "20260711", "time_str": "09:35", "open": 49.10, "high": 49.30, "low": 49.05, "close": 49.22, "amount": 1200000, "volume": 24000},
                {"date": "20260711", "time_str": "09:40", "open": 49.22, "high": 49.38, "low": 49.18, "close": 49.34, "amount": 1380000, "volume": 26800},
            ],
        })

        result = brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        self.assertEqual(
            len([item for item in result["coverage_rows"] if item["coverage_status"] == "sample_available"]),
            5,
        )
        self.assertTrue(
            any(
                item["source_key"] == "westock_fund_flow_history"
                and item["coverage_status"] == "sample_available"
                and item["latest_snapshot_connection_mode"] == "payload_injected_sample"
                and item["sample_quality_status"] == "insufficient_history"
                and item["sample_quality_bar_count"] == 3
                for item in result["coverage_rows"]
            )
        )
        self.assertTrue(
            any(
                item["source_key"] == "tdx_minute_kline"
                and item["coverage_status"] == "sample_available"
                for item in result["coverage_rows"]
            )
        )
        self.assertTrue(
            any(item["source_key"] == "tushare_financial_news" and item["coverage_status"] == "route_only" for item in result["coverage_rows"])
        )
        self.assertIn("inadequate_sample=", result["coverage_summary"])
        self.assertIn("sample_available=5/6", result["coverage_summary"])
        self.assertIn("priority_source=TDX realtime quotes", result["coverage_summary"])

    def test_a_share_proxy_guard_source_coverage_marks_tushare_fallback_for_westock_lane(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        raw_dir = Path(tmp.name) / "data" / "raw" / "tushare"
        raw_dir.mkdir(parents=True, exist_ok=True)
        (raw_dir / "300418_moneyflow.json").write_text(
            '[["20260708",1,2,3,4,5,6,7,2,11,1200.5],["20260709",2,1,4,3,6,5,8,3,12,1800.0],["20260710",3,2,5,4,7,6,4,9,-6,-420.25]]',
            encoding="utf-8",
        )
        brain.trading_a_share_tushare_moneyflow_history_fallback_snapshot({"symbol": "300418", "timeframe": "1d"})

        result = brain.trading_a_share_proxy_guard_source_coverage({
            "symbol": "300418",
            "timeframe": "1d",
            "candidate_slug": "vwap",
        })

        westock_row = next(item for item in result["coverage_rows"] if item["source_key"] == "westock_fund_flow_history")
        self.assertEqual(westock_row["coverage_status"], "fallback_sample")
        self.assertEqual(westock_row["latest_source_type"], "tushare_moneyflow_history_fallback_snapshot")
        self.assertEqual(westock_row["latest_snapshot_connection_mode"], "local_tushare_raw_snapshot")
        self.assertEqual(westock_row["missing_required_fields"], ["ddx"])
        self.assertEqual(westock_row["sample_quality_status"], "missing_required_fields")
        self.assertIn("fallback_sample=1", result["coverage_summary"])
        self.assertIn("inadequate_sample=1", result["coverage_summary"])

    def test_research_queue_manual_approval_writeback_syncs_mother_system(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        result = brain.trading_confirm_research_queue_manual_approval({
            "candidate_slug": "vwap",
            "decision": "deferred",
            "reviewer": "test-reviewer",
            "rationale": "鏍锋湰澶栬櫧鏈け鏁堬紝浣嗚瘉鎹竻鍗曟湭婊¤冻锛屽厛鏆傜紦鍗囩骇銆?",
            "follow_up_items": ["琛ラ綈 consistency_guard", "琛ラ綈 governance_reason_clear"],
            "evidence_notes": ["褰撳墠浠嶆槸 daily_proxy scaffold"],
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["learning_entry"]["entry_type"], "trading_research_queue_manual_promotion_approval_result")
        self.assertEqual(result["learning_entry"]["metadata"]["candidate_slug"], "vwap")
        self.assertEqual(result["learning_entry"]["metadata"]["decision"], "deferred")
        self.assertEqual(result["learning_entry"]["metadata"]["reviewer"], "test-reviewer")
        self.assertEqual(result["self_evolution_log"]["trigger"], "trading_research_queue_manual_promotion_approval_result_learning")
        self.assertEqual(result["updated_skill_registry_entry"]["status"], "Experimental")
        self.assertTrue(result["updated_skill_registry_entry"]["human_reviewed"])
        self.assertEqual(result["updated_skill_registry_entry"]["metadata"]["manual_approval_entrypoint"]["approval_status"], "deferred")
        self.assertEqual(result["updated_skill_registry_entry"]["metadata"]["manual_approval_writeback"]["latest_decision"], "deferred")
        self.assertEqual(result["updated_skill_registry_entry"]["metadata"]["manual_approval_confirmation_interface"]["last_decision"], "deferred")
        self.assertEqual(result["module_status_record"]["module_name"], "trading_research_queue_vwap_v0_1")
        self.assertEqual(result["module_status_record"]["quality_action"], "needs_review")
        self.assertEqual(result["module_status_record"]["status"], "Experimental")
        self.assertTrue(result["module_status_record"]["human_reviewed"])
        self.assertEqual(result["bulletin_state_record"]["metadata"]["candidate_slug"], "vwap")
        self.assertEqual(result["bulletin_state_record"]["metadata"]["decision"], "deferred")
        self.assertIn("继续补证据", result["bulletin_state_record"]["next_step"])
        self.assertEqual(result["approval_summary"]["summary"]["approval_record_count"], 1)
        self.assertEqual(result["approval_summary"]["summary"]["deferred_count"], 1)
        self.assertEqual(result["approval_summary"]["summary"]["human_reviewed_count"], 1)
        self.assertEqual(result["approval_summary"]["candidate_rows"][0]["latest_decision"], "deferred")
        self.assertTrue(result["approval_summary"]["candidate_rows"][0]["human_reviewed"])
        self.assertTrue(result["approval_summary"]["candidate_rows"][0]["latest_reviewed_at"])
        self.assertEqual(result["approval_summary"]["integration_note"]["workflow_status"], "Implemented")
        board = brain.board_status()
        self.assertIn("继续补证据", board["next_step"])
        self.assertTrue(any("人工审批结果：deferred" in item["summary"] for item in board["recent_events"]))
        self.assertEqual(board["latest_trading_bulletin_state"]["queue_type"], "ResearchQueue")
        self.assertEqual(board["latest_trading_bulletin_state"]["candidate_slug"], "vwap")
        self.assertEqual(board["latest_trading_bulletin_state"]["decision"], "deferred")
        self.assertEqual(board["latest_trading_bulletin_state"]["status"], "Experimental")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["candidate_slug"], "vwap")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["decision"], "deferred")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["approval_status"], "deferred")
        self.assertFalse(board["latest_trading_research_queue_bulletin_state"]["can_submit_now"])
        self.assertIn("consistency_guard", board["latest_trading_research_queue_bulletin_state"]["missing_keys"])
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["ready_count"], 4)
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["total_count"], 7)
        self.assertTrue(board["latest_trading_research_queue_bulletin_state"]["proxy_guard_blocked"])
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selection_status"], "abstain")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selection_governance_action"], "needs_review")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["portfolio_action"], "no_trade")
        self.assertEqual(board["latest_trading_research_queue_bulletin_state"]["selected_strategy_name"], "NO_TRADE")
        self.assertEqual(
            board["latest_trading_research_queue_bulletin_state"]["upgrade_candidate_status"],
            "blocked_by_scaffold",
        )
        self.assertEqual(
            board["latest_trading_research_queue_bulletin_state"]["freeze_candidate_status"],
            "watch_consistency_gap",
        )
        self.assertEqual(
            board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"]["upgrade_candidate_status"],
            "blocked_by_scaffold",
        )
        self.assertEqual(
            board["latest_trading_research_queue_bulletin_state"]["selection_state_summary"]["freeze_candidate_status"],
            "watch_consistency_gap",
        )
        self.assertIn(
            "recommendation=stay_experimental_watch_gap",
            board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"],
        )
        self.assertIn(
            "primary_gate=scaffold",
            board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"],
        )
        self.assertIn(
            "upgrade_status=blocked_by_scaffold",
            board["latest_trading_research_queue_bulletin_state"]["selection_state_summary_text"],
        )
        self.assertEqual(
            board["latest_trading_replay_bulletin_state"]["selected_strategy_name"],
            "NO_TRADE",
        )
        recent_evolution_triggers = [item["trigger"] for item in brain.store.list_records("evolution_logs", limit=10, newest=True)]
        self.assertIn("trading_research_queue_manual_promotion_approval_result_learning", recent_evolution_triggers)
        recent_learning_types = [item["entry_type"] for item in brain.store.list_records("learning_entries", limit=10, newest=True)]
        self.assertIn("trading_research_queue_manual_promotion_approval_result", recent_learning_types)
        signals = brain.trading_research_queue_approval_signals({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(signals["implementation_status"], "Implemented")
        self.assertEqual(signals["summary"]["signal_counts"]["needs_review"], 1)
        self.assertEqual(signals["signals"][0]["signal"], "needs_review")
        self.assertEqual(signals["signals"][0]["latest_decision"], "deferred")
        self.assertEqual(signals["signals"][0]["next_review_trigger"], "evidence_gap_closed")
        self.assertEqual(signals["integration_note"]["workflow_status"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_approval_signals"], "Implemented")
        watchlist = brain.trading_research_queue_watchlist({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(watchlist["implementation_status"], "Implemented")
        self.assertEqual(watchlist["summary"]["bucket_counts"]["needs_review"], 1)
        self.assertEqual(watchlist["summary"]["total_watch_candidates"], 1)
        self.assertTrue(watchlist["summary"]["focus_now"])
        self.assertEqual(watchlist["needs_review"][0]["candidate_slug"], "vwap")
        self.assertEqual(watchlist["watchlist_rows"][0]["bucket"], "needs_review")
        self.assertEqual(watchlist["watchlist_rows"][0]["next_review_trigger"], "evidence_gap_closed")
        self.assertEqual(watchlist["integration_note"]["workflow_status"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_watchlist"], "Implemented")
        gap_summary = brain.trading_research_queue_evidence_gap_summary({"candidate_slug": "vwap"})
        self.assertEqual(gap_summary["rows"][0]["latest_decision"], "deferred")
        self.assertEqual(gap_summary["rows"][0]["approval_status"], "deferred")
        self.assertTrue(
            any(item for item in gap_summary["rows"][0]["normalized_follow_up_plan"])
            or any("consistency_guard" in item for item in gap_summary["rows"][0]["follow_up_items"])
        )
        self.assertFalse(any(item.startswith("??") for item in gap_summary["rows"][0]["normalized_follow_up_plan"]))
        self.assertIn("补 train/OOS 一致性说明并缩小样本内外 gap", gap_summary["rows"][0]["normalized_follow_up_plan"])
        self.assertIn("给出摆脱 daily_proxy scaffold 的替代验证路径或退出说明", gap_summary["rows"][0]["normalized_follow_up_plan"])
        self.assertNotIn("补充治理说明，消除 research_queue 主原因拦截", gap_summary["rows"][0]["normalized_follow_up_plan"])
        self.assertTrue(
            any("daily_proxy scaffold" in item for item in result["learning_entry"]["metadata"].get("evidence_notes", []))
        )
        agenda = brain.trading_research_queue_review_agenda({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(agenda["implementation_status"], "Implemented")
        self.assertEqual(agenda["summary"]["total_agenda_items"], 1)
        self.assertTrue(agenda["summary"]["focus_now"])
        self.assertEqual(agenda["agenda_items"][0]["candidate_slug"], "vwap")
        self.assertEqual(agenda["top_candidates"][0]["candidate_slug"], "vwap")
        self.assertEqual(agenda["bucket_top_candidates"]["needs_review"][0]["candidate_slug"], "vwap")
        self.assertEqual(agenda["agenda_items"][0]["bucket"], "needs_review")
        self.assertGreater(agenda["agenda_items"][0]["priority_score"], 100.0)
        self.assertEqual(agenda["agenda_items"][0]["agenda_action"], "补证据并准备下一轮验证切片")
        self.assertIn("consistency_guard", agenda["agenda_items"][0]["required_evidence"])
        self.assertIn("scaffold_exit", agenda["agenda_items"][0]["required_evidence"])
        self.assertIn("a_share_proxy_guard_clear", agenda["agenda_items"][0]["required_evidence"])
        self.assertEqual(agenda["agenda_items"][0]["evidence_progress"]["ready_count"], 4)
        self.assertEqual(agenda["agenda_items"][0]["evidence_progress"]["total_count"], 7)
        self.assertEqual(agenda["agenda_items"][0]["source_refs"]["learning_entry_id"], result["approval_summary"]["candidate_rows"][0]["learning_entry_id"])
        self.assertTrue(agenda["agenda_items"][0]["ranking_reason"])
        self.assertIn("score_components", agenda["agenda_items"][0])
        self.assertIn("score_explanation", agenda["agenda_items"][0])
        self.assertEqual(
            round(sum(agenda["agenda_items"][0]["score_components"].values()), 2),
            agenda["agenda_items"][0]["priority_score"],
        )
        self.assertEqual(agenda["agenda_items"][0]["score_components"]["bucket_weight"], 100.0)
        self.assertIn("bucket priority", agenda["agenda_items"][0]["score_explanation"])
        self.assertIn("missing evidence", agenda["agenda_items"][0]["score_explanation"])
        self.assertIn("oos=pass", agenda["agenda_items"][0]["score_explanation"])
        self.assertEqual(agenda["agenda_items"][0]["failure_count"], 1)
        self.assertEqual(agenda["agenda_items"][0]["out_of_sample_result"], "pass")
        self.assertEqual(agenda["agenda_items"][0]["queue_recommendation"], "stay_experimental_watch_gap")
        self.assertEqual(agenda["agenda_items"][0]["replay_variant_governance_hint"], "continue_targeted_replay")
        self.assertEqual(agenda["agenda_items"][0]["replay_variant_governance_priority_action"], "continue_targeted_replay")

        self.assertIn("可以继续围绕当前主阻塞项做定向 replay", agenda["agenda_items"][0]["replay_variant_governance_summary"])
        self.assertEqual(agenda["agenda_items"][0]["score_components"]["replay_governance_weight"], 4.0)
        self.assertFalse(any(item.startswith("??") for item in agenda["agenda_items"][0]["normalized_follow_up_plan"]))
        self.assertIn("补 train/OOS 一致性说明并缩小样本内外 gap", agenda["agenda_items"][0]["normalized_follow_up_plan"])
        self.assertIn("给出摆脱 daily_proxy scaffold 的替代验证路径或退出说明", agenda["agenda_items"][0]["normalized_follow_up_plan"])
        self.assertNotIn("补充治理说明，消除 research_queue 主原因拦截", agenda["agenda_items"][0]["normalized_follow_up_plan"])
        self.assertEqual(agenda["agenda_items"][0]["target_gap_snapshot"]["current_status"], "train_stronger_than_test")
        self.assertGreater(agenda["agenda_items"][0]["target_gap_snapshot"]["return_gap_to_close"], 0.0)
        self.assertGreater(agenda["agenda_items"][0]["target_gap_snapshot"]["score_gap_to_close"], 0.0)
        self.assertIn(
            agenda["agenda_items"][0]["target_gap_snapshot"]["primary_driver"],
            {"return_gap", "risk_score_gap"},
        )
        self.assertTrue(agenda["agenda_items"][0]["target_gap_snapshot"]["recommended_validation_focus"])
        self.assertIn("下一轮验证切片应围绕", agenda["agenda_items"][0]["next_validation_slice_note"])
        self.assertIn("test_return", agenda["agenda_items"][0]["next_validation_slice_note"])
        self.assertIn("test_score", agenda["agenda_items"][0]["next_validation_slice_note"])
        self.assertIn("当前主驱动是", agenda["agenda_items"][0]["next_validation_slice_note"])
        self.assertEqual(agenda["agenda_items"][0]["validation_task_preview"]["candidate_slug"], "vwap")
        self.assertEqual(agenda["agenda_items"][0]["validation_task_preview"]["blocker"], "consistency_guard")
        self.assertTrue(agenda["agenda_items"][0]["validation_task_preview"]["research_mode"])
        self.assertFalse(agenda["agenda_items"][0]["validation_task_preview"]["live_trading_enabled"])
        self.assertEqual(
            agenda["agenda_items"][0]["validation_task_preview"]["task_status"],
            "ready_for_next_validation_slice",
        )
        self.assertIn(
            agenda["agenda_items"][0]["validation_task_preview"]["consistency_primary_driver"],
            {"return_gap", "risk_score_gap"},
        )
        self.assertTrue(
            agenda["agenda_items"][0]["validation_task_preview"]["recommended_validation_focus"]
        )
        self.assertEqual(
            agenda["agenda_items"][0]["validation_task_preview"]["required_actions"],
            agenda["agenda_items"][0]["normalized_follow_up_plan"],
        )
        self.assertTrue(
            agenda["agenda_items"][0]["validation_task_preview"]["replay_adjustment_hints"]["suggested_variants"]
        )
        self.assertIn(
            agenda["agenda_items"][0]["validation_task_preview"]["replay_adjustment_hints"]["primary_driver"],
            {"return_gap", "risk_score_gap"},
        )
        self.assertIn("oos=pass", agenda["agenda_items"][0]["ranking_reason"])
        self.assertIn("replay_governance=continue_targeted_replay", agenda["agenda_items"][0]["ranking_reason"])
        self.assertIn("replay governance", agenda["agenda_items"][0]["score_explanation"])
        self.assertEqual(agenda["summary"]["top_candidate_slug"], "vwap")
        self.assertEqual(agenda["summary"]["top_priority_score"], agenda["agenda_items"][0]["priority_score"])
        self.assertEqual(agenda["summary"]["top_candidate_limit"], 3)
        self.assertEqual(
            agenda["summary"]["focus_follow_up_plan"],
            agenda["agenda_items"][0]["normalized_follow_up_plan"],
        )
        self.assertEqual(
            agenda["summary"]["focus_target_gap_snapshot"],
            agenda["agenda_items"][0]["target_gap_snapshot"],
        )
        self.assertEqual(
            agenda["summary"]["focus_next_validation_slice_note"],
            agenda["agenda_items"][0]["next_validation_slice_note"],
        )
        self.assertEqual(
            agenda["summary"]["focus_validation_task_preview"],
            agenda["agenda_items"][0]["validation_task_preview"],
        )
        self.assertEqual(agenda["integration_note"]["workflow_status"], "Implemented")
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })
        scaffold_result = brain.trading_workbuddy_triple_decision_trees_scaffold({
            "symbol": "300418",
            "timeframe": "1d",
        })
        next_slice = brain.trading_research_queue_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        readiness_again = brain.trading_research_queue_readiness_summary({"candidate_slug": "vwap"})
        self.assertEqual(next_slice["implementation_status"], "Implemented")
        self.assertEqual(next_slice["candidate_slug"], "vwap")
        self.assertEqual(next_slice["candidate_name"], "VWAP Research Slice v0.1")
        self.assertEqual(next_slice["primary_blocker_key"], "consistency_guard")
        self.assertEqual(next_slice["readiness_status"], "not_ready_for_promotion")
        self.assertEqual(next_slice["agenda_action"], "补证据并准备下一轮验证切片")
        self.assertEqual(next_slice["queue_recommendation"], "stay_experimental_watch_gap")
        self.assertTrue(next_slice["a_share_proxy_guard"]["blocks_promotion"])
        self.assertIn("blocks_promotion", next_slice["sample_size_thresholds"])
        self.assertEqual(next_slice["a_share_proxy_guard"]["bias_label"], "overnight_lock_pressure_bias")
        self.assertEqual(next_slice["approval_status"], "deferred")
        self.assertEqual(next_slice["latest_decision"], "deferred")
        self.assertIn("下一轮验证切片", next_slice["summary"]["focus_now"])
        self.assertTrue(next_slice["summary"]["ready_to_run"])
        self.assertEqual(next_slice["workbuddy_constraint_snapshot"]["status"], "reported")
        self.assertIn("关键差异", next_slice["next_validation_slice_note"])
        self.assertEqual(
            next_slice["workbuddy_constraint_snapshot"]["current_phase"],
            scaffold_result["triple_decision_trees_scaffold"]["current_phase"],
        )
        self.assertEqual(
            next_slice["summary"]["workbuddy_constraint_phase"],
            scaffold_result["triple_decision_trees_scaffold"]["current_phase"],
        )
        self.assertEqual(
            next_slice["summary"]["workbuddy_constraint_main_force_top_branch"],
            next_slice["workbuddy_constraint_snapshot"]["main_force_top_branch"],
        )
        self.assertEqual(
            next_slice["summary"]["workbuddy_constraint_context_effect"],
            next_slice["workbuddy_constraint_snapshot"]["context_effect"],
        )
        self.assertEqual(
            next_slice["summary"]["workbuddy_constraint_summary"],
            next_slice["workbuddy_constraint_snapshot"]["summary"],
        )
        self.assertEqual(
            next_slice["validation_task_preview"],
            agenda["agenda_items"][0]["validation_task_preview"],
        )
        self.assertEqual(
            next_slice["normalized_follow_up_plan"],
            agenda["agenda_items"][0]["normalized_follow_up_plan"],
        )
        self.assertEqual(
            next_slice["target_gap_snapshot"],
            agenda["agenda_items"][0]["target_gap_snapshot"],
        )
        self.assertEqual(
            next_slice["next_validation_slice_note"],
            agenda["agenda_items"][0]["next_validation_slice_note"],
        )
        self.assertEqual(next_slice["replay_payload_template"]["candidate_slug"], "vwap")
        self.assertTrue(next_slice["replay_payload_template"]["template_ready"])
        self.assertEqual(next_slice["replay_payload_template"]["symbol"], "300418")
        self.assertEqual(next_slice["replay_payload_template"]["timeframe"], "1d")
        self.assertEqual(next_slice["replay_payload_template"]["short_window"], 5)
        self.assertEqual(next_slice["replay_payload_template"]["long_window"], 20)
        self.assertEqual(next_slice["replay_payload_template"]["train_ratio"], 0.7)
        self.assertTrue(next_slice["replay_payload_template"]["research_mode"])
        self.assertFalse(next_slice["replay_payload_template"]["live_trading_enabled"])
        self.assertIn("sample_size_guard_blocked", next_slice["replay_payload_template"])
        self.assertIn(
            next_slice["replay_payload_template"]["consistency_primary_driver"],
            {"return_gap", "risk_score_gap"},
        )
        self.assertTrue(next_slice["replay_payload_template"]["recommended_validation_focus"])
        self.assertTrue(next_slice["replay_payload_template"]["replay_adjustment_hints"]["suggested_variants"])
        self.assertTrue(next_slice["replay_payload_template"]["replay_adjustment_hints"]["priority_checks"])
        self.assertTrue(next_slice["replay_payload_template"]["replay_variant_templates"])
        self.assertIn(
            "latest_candidate_vs_previous_variant_status",
            next_slice["replay_payload_template"],
        )
        self.assertIn(
            "latest_candidate_vs_previous_variant_oos_shift",
            next_slice["replay_payload_template"],
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["replay_variant_templates"][0]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["recommended_variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertIn(
            "trade coverage",
            next_slice["replay_payload_template"]["recommended_variant_reason"],
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["replay_variant_templates"][0]["payload"]["position_pct"],
            0.03,
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["replay_variant_templates"][0]["payload"]["max_loss_pct"],
            0.015,
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["proxy_guard_sample_attached_count"],
            next_slice["validation_task_preview"]["proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["proxy_guard_priority_sample_status"],
            next_slice["validation_task_preview"]["proxy_guard_priority_sample_status"],
        )
        self.assertEqual(
            next_slice["replay_payload_template"]["proxy_guard_priority_sample_connection_mode"],
            next_slice["validation_task_preview"]["proxy_guard_priority_sample_connection_mode"],
        )
        self.assertIn("execution_plan", next_slice)
        self.assertEqual(next_slice["execution_plan"]["plan_status"], "ready_for_replay")
        self.assertEqual(next_slice["execution_plan"]["target_blocker"], "consistency_guard")
        self.assertEqual(next_slice["execution_plan"]["default_variant_key"], "risk_compare_same_signal_quality")
        self.assertTrue(next_slice["execution_plan"]["default_variant_reason"])
        self.assertIn("out_of_sample_result", next_slice["execution_plan"])
        self.assertIn("out_of_sample_coverage_status", next_slice["execution_plan"])
        self.assertIn("oos_trade_pairs_count", next_slice["execution_plan"])
        self.assertIn("min_promotable_oos_trade_pairs", next_slice["execution_plan"])
        self.assertIn("oos_promotion_ready", next_slice["execution_plan"])
        if next_slice["execution_plan"]["out_of_sample_coverage_status"]:
            self.assertIn(
                "coverage=",
                next_slice["execution_plan"]["summary"],
            )
        self.assertEqual(
            next_slice["execution_plan"]["default_variant_payload"],
            next(
                item["payload"]
                for item in next_slice["replay_payload_template"]["replay_variant_templates"]
                if item["variant_key"] == "risk_compare_same_signal_quality"
            ),
        )
        self.assertEqual(
            next_slice["execution_plan"]["proxy_guard_sample_attached_count"],
            next_slice["replay_payload_template"]["proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            next_slice["execution_plan"]["proxy_guard_priority_sample_status"],
            next_slice["replay_payload_template"]["proxy_guard_priority_sample_status"],
        )
        self.assertEqual(
            next_slice["execution_plan"]["proxy_guard_priority_sample_connection_mode"],
            next_slice["replay_payload_template"]["proxy_guard_priority_sample_connection_mode"],
        )
        self.assertTrue(next_slice["execution_plan"]["preflight_checks"])
        self.assertTrue(next_slice["execution_plan"]["acceptance_gates"])
        self.assertTrue(next_slice["execution_plan"]["post_run_checks"])
        if next_slice["execution_plan"]["out_of_sample_coverage_status"]:
            self.assertTrue(
                any(
                    "样本外覆盖复核" in item
                    for item in next_slice["execution_plan"]["post_run_checks"]
                )
            )
        self.assertIn("ValidationReport", next_slice["execution_plan"]["writeback_targets"])
        self.assertIn("BulletinStateRecord", next_slice["execution_plan"]["writeback_targets"])
        self.assertEqual(
            next_slice["summary"]["execution_plan_summary"],
            next_slice["execution_plan"]["summary"],
        )
        self.assertTrue(
            next_slice["replay_payload_template"]["replay_variant_templates"][0]["research_mode"]
        )
        self.assertFalse(
            next_slice["replay_payload_template"]["replay_variant_templates"][0]["live_trading_enabled"]
        )
        self.assertTrue(next_slice["replay_payload_template"]["a_share_proxy_guard_blocked"])
        self.assertEqual(
            next_slice["replay_payload_template"]["a_share_proxy_guard"]["preferred_action"],
            "no_trade",
        )
        self.assertIn("market_data_record_resolved", next_slice["replay_payload_template"]["data_requirement"])
        self.assertIn("research-mode validation", next_slice["replay_payload_template"]["summary"])
        self.assertTrue(next_slice["execution_hints"]["research_mode"])
        self.assertFalse(next_slice["execution_hints"]["live_trading_enabled"])
        self.assertIn("trading-replay", next_slice["execution_hints"]["command_hint"])
        self.assertEqual(
            next_slice["review_checklist"]["blocked_steps"],
            readiness_again["rows"][0]["review_checklist"]["blocked_steps"],
        )
        self.assertEqual(
            next_slice["source_views"]["readiness_summary"],
            "trading_research_queue_readiness_summary",
        )
        self.assertEqual(
            next_slice["source_views"]["review_agenda"],
            "trading_research_queue_review_agenda",
        )
        self.assertIn("current runnable replay payload template", next_slice["integration_note"]["future_route"])
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_review_agenda"], "Implemented")
        self.assertEqual(brain.status()["module_status"]["trading_research_queue_next_validation_slice"], "Implemented")
        rerun = brain.trading_research_queue_run_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
            "variant_key": "risk_tighten_small_position",
        })
        self.assertTrue(rerun["success"])
        self.assertEqual(rerun["replay_payload_used"]["candidate_slug"], "vwap")
        self.assertEqual(
            rerun["replay_payload_used"]["template_origin"],
            "trading_research_queue_next_validation_slice",
        )
        self.assertEqual(rerun["replay_payload_used"]["variant_key"], "risk_tighten_small_position")
        self.assertTrue(rerun["replay_payload_used"]["research_mode"])
        self.assertFalse(rerun["replay_payload_used"]["live_trading_enabled"])
        self.assertEqual(rerun["replay_payload_used"]["symbol"], "300418")
        self.assertEqual(rerun["replay_payload_used"]["timeframe"], "1d")
        self.assertEqual(rerun["replay_payload_used"]["position_pct"], 0.03)
        self.assertEqual(rerun["replay_payload_used"]["max_loss_pct"], 0.015)
        self.assertEqual(rerun["next_validation_slice"]["candidate_slug"], "vwap")
        self.assertEqual(rerun["validation_slice_execution"]["candidate_slug"], "vwap")
        self.assertTrue(rerun["validation_slice_execution"]["executed_from_template"])
        self.assertTrue(rerun["validation_slice_execution"]["research_mode"])
        self.assertFalse(rerun["validation_slice_execution"]["live_trading_enabled"])
        self.assertEqual(rerun["validation_slice_execution"]["variant_key"], "risk_tighten_small_position")
        self.assertEqual(
            rerun["validation_slice_execution"]["execution_plan_summary"],
            next_slice["execution_plan"]["summary"],
        )
        self.assertIn("execution_outcome_summary", rerun["validation_slice_execution"])
        self.assertIn("execution_outcome_status", rerun["validation_slice_execution"])
        self.assertIn("execution_outcome_assessment", rerun["validation_slice_execution"])
        self.assertEqual(
            rerun["validation_slice_execution"]["execution_outcome_summary"],
            rerun["validation_slice_execution"]["execution_outcome_assessment"]["summary"],
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["id"],
            rerun["validation_slice_execution"]["candidate_validation_report_id"],
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["out_of_sample_result"],
            rerun["validation_slice_execution"]["candidate_out_of_sample_result"],
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["governance_action"],
            rerun["validation_slice_execution"]["candidate_governance_action"],
        )
        self.assertIn(
            "workbuddy_constraint_guard",
            rerun["candidate_validation_report"]["metadata"],
        )
        self.assertIn(
            "workbuddy_constraint_snapshot",
            rerun["candidate_validation_report"]["metadata"],
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["metadata"]["workbuddy_constraint_snapshot"]["status"],
            "reported",
        )
        self.assertTrue(
            rerun["candidate_validation_report"]["metadata"]["workbuddy_constraint_guard"]["blocks_promotion"]
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["metadata"]["sample_comparison"]["consistency"],
            rerun["validation_slice_execution"]["candidate_sample_consistency"],
        )
        self.assertEqual(rerun["replay_variant_used"]["variant_key"], "risk_tighten_small_position")
        self.assertEqual(rerun["replay_variant_used"]["changes"]["position_pct"], 0.03)
        self.assertIn("risk_compare_same_signal_quality", rerun["replay_variant_used"]["available_variant_keys"])
        self.assertEqual(
            rerun["validation_report"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["candidate_validation_report"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["trade_journal"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["candidate_strategy_review"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["skill_registry_entry"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["module_status_record"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["bulletin_state_record"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["self_evolution_log"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["research_queue_skill_registry_entry"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["research_queue_skill_registry_entry"]["metadata"]["latest_validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            rerun["research_queue_skill_registry_entry"]["metadata"]["latest_strategy_review_id"],
            rerun["candidate_strategy_review"]["id"],
        )
        self.assertEqual(
            rerun["research_queue_theory_definition"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            rerun["research_queue_atom"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertIn(
            "consistency_secondary_driver",
            rerun["research_queue_skill_registry_entry"]["metadata"],
        )
        self.assertTrue(
            rerun["research_queue_skill_registry_entry"]["metadata"]["consistency_driver_detail_summary"]
        )
        self.assertEqual(
            rerun["validation_slice_execution"]["focus_now"],
            next_slice["summary"]["focus_now"],
        )
        self.assertIn(
            rerun["decision_record"]["action"],
            {"trade", "wait", "no_trade"},
        )
        board_after_rerun = brain.board_status()
        self.assertTrue(
            any(
                "下一轮验证切片" in item["summary"]
                for item in board_after_rerun["recent_events"]
            )
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_research_queue_run_next_validation_slice"],
            "Implemented",
        )
        latest_summary = brain.trading_research_queue_latest_validation_summary({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(latest_summary["implementation_status"], "Implemented")
        self.assertEqual(latest_summary["summary"]["candidate_slug"], "vwap")
        self.assertEqual(latest_summary["summary"]["candidate_name"], "VWAP Research Slice v0.1")
        self.assertEqual(latest_summary["workbuddy_constraint_snapshot"]["status"], "reported")
        self.assertEqual(
            latest_summary["summary"]["workbuddy_constraint_phase"],
            scaffold_result["triple_decision_trees_scaffold"]["current_phase"],
        )
        self.assertEqual(
            latest_summary["summary"]["workbuddy_constraint_main_force_top_branch"],
            latest_summary["workbuddy_constraint_snapshot"]["main_force_top_branch"],
        )
        self.assertEqual(
            latest_summary["summary"]["workbuddy_constraint_context_effect"],
            latest_summary["workbuddy_constraint_snapshot"]["context_effect"],
        )
        self.assertEqual(
            latest_summary["summary"]["workbuddy_constraint_summary"],
            latest_summary["workbuddy_constraint_snapshot"]["summary"],
        )
        self.assertIn(
            latest_summary["summary"]["sample_consistency"],
            {"aligned", "diverged", "train_stronger_than_test", "oos_stronger_than_train", ""},
        )
        self.assertTrue(latest_summary["summary"]["a_share_proxy_guard_blocked"])
        self.assertIn("sample_size_guard_blocked", latest_summary["summary"])
        self.assertIn(
            latest_summary["summary"]["consistency_primary_driver"],
            {"return_gap", "risk_score_gap", "none", "negative_oos_or_direction_flip"},
        )
        self.assertTrue(latest_summary["summary"]["consistency_primary_driver_label"])
        self.assertTrue(latest_summary["summary"]["consistency_focus_summary"])
        if latest_summary["summary"]["consistency_focus_summary"].startswith("当前一致性主要由"):
            self.assertIn("次级拖累", latest_summary["summary"]["consistency_focus_summary"])
            self.assertIn("关键差异", latest_summary["summary"]["consistency_focus_summary"])
        self.assertIn("consistency_snapshot_summary", latest_summary["summary"])
        self.assertIn(
            "primary_driver=",
            latest_summary["summary"]["consistency_snapshot_summary"],
        )
        self.assertIn(
            "score_gap=",
            latest_summary["summary"]["consistency_snapshot_summary"],
        )
        self.assertIn(
            "regime_train=",
            latest_summary["summary"]["consistency_snapshot_summary"],
        )
        self.assertIn("下一轮 replay 建议优先围绕", latest_summary["summary"]["replay_adjustment_summary"])
        self.assertIn("consistency_guard_plan", latest_summary)
        self.assertIn("consistency_guard_plan_summary", latest_summary["summary"])
        self.assertTrue(latest_summary["summary"]["consistency_guard_plan_summary"])
        self.assertIn("execution_plan", latest_summary)
        self.assertIn("execution_plan_summary", latest_summary["summary"])
        self.assertIn("execution_plan_status", latest_summary["summary"])
        self.assertIn("execution_outcome_assessment", latest_summary)
        self.assertIn("execution_outcome_summary", latest_summary["summary"])
        self.assertIn("execution_outcome_status", latest_summary["summary"])
        self.assertIn("交易拆解：", latest_summary["summary"]["consistency_driver_detail_summary"])
        self.assertIn(
            latest_summary["execution_plan"]["summary"],
            latest_summary["summary"]["execution_plan_summary"],
        )
        self.assertEqual(
            latest_summary["summary"]["execution_plan_status"],
            latest_summary["execution_plan"]["plan_status"],
        )
        self.assertEqual(
            latest_summary["summary"]["execution_outcome_summary"],
            latest_summary["execution_outcome_assessment"]["summary"],
        )
        self.assertEqual(
            latest_summary["summary"]["consistency_guard_plan_summary"],
            latest_summary["consistency_guard_plan"]["summary"],
        )
        self.assertEqual(latest_summary["consistency_guard_plan"]["blocker_key"], "consistency_guard")
        self.assertTrue(latest_summary["consistency_guard_plan"]["required_actions"])
        self.assertGreaterEqual(latest_summary["summary"]["replay_variant_template_count"], 1)
        self.assertTrue(latest_summary["summary"]["default_replay_variant_key"])
        self.assertEqual(
            latest_summary["summary"]["default_replay_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            latest_summary["summary"]["default_replay_variant_label"],
            "收紧风险暴露",
        )
        self.assertIn(
            "improved relative to the previous replay route",
            latest_summary["summary"]["default_replay_variant_reason"],
        )
        self.assertIn(
            latest_summary["summary"]["default_replay_variant_source_status"],
            {"improved", "mixed", "worsened", "not_available", ""},
        )
        self.assertIn(
            latest_summary["summary"]["default_replay_variant_source_oos_shift"],
            {"improved", "mixed", "unchanged", "worsened", "unknown", ""},
        )
        self.assertIn(
            "previous_variant_status=",
            latest_summary["summary"]["default_replay_variant_selection_context"],
        )
        self.assertIn(
            "default_variant=",
            latest_summary["summary"]["default_replay_variant_selection_context"],
        )
        self.assertIn(
            "路由依据：",
            latest_summary["summary"]["execution_plan_summary"],
        )
        self.assertEqual(latest_summary["summary"]["latest_replay_variant_key"], "risk_tighten_small_position")
        self.assertTrue(latest_summary["summary"]["latest_replay_variant_label"])
        next_slice_after_rerun = brain.trading_research_queue_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(
            next_slice_after_rerun["replay_payload_template"]["recommended_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            next_slice_after_rerun["execution_plan"]["default_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            latest_summary["source_refs"]["validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertIn("strategy_parallel_scorecard", latest_summary)
        self.assertEqual(len(latest_summary["strategy_parallel_scorecard"]), 3)
        self.assertEqual(latest_summary["summary"]["strategy_parallel_scorecard_count"], 3)
        self.assertIn("并行策略记分板：", latest_summary["summary"]["strategy_parallel_scorecard_summary"])
        self.assertIn("strategy_parallel_sample_gap_summary", latest_summary["summary"])
        self.assertIn("并行策略样本差距：", latest_summary["summary"]["strategy_parallel_sample_gap_summary"])
        self.assertIn("train_return=", latest_summary["summary"]["strategy_parallel_sample_gap_summary"])
        self.assertIn("test_score=", latest_summary["summary"]["strategy_parallel_sample_gap_summary"])
        self.assertIn("strategy_parallel_governance_rollup", latest_summary)
        self.assertIn("并行策略治理分桶：", latest_summary["summary"]["strategy_parallel_governance_summary"])
        self.assertIn("优先级说明", latest_summary["summary"]["strategy_parallel_governance_summary"])
        self.assertIn(
            "consistency_watch=VWAP Proxy Research v0.1",
            latest_summary["summary"]["strategy_parallel_governance_summary"],
        )
        self.assertNotIn(
            "downgrade_watch=VWAP Proxy Research v0.1",
            latest_summary["summary"]["strategy_parallel_governance_summary"],
        )
        self.assertIn("strategy_parallel_governance_actions", latest_summary)
        self.assertIn("并行策略治理动作：", latest_summary["summary"]["strategy_parallel_governance_action_summary"])
        self.assertIn("优先级说明", latest_summary["summary"]["strategy_parallel_governance_action_summary"])
        self.assertIn(
            "consistency_watch->rewrite(VWAP Proxy Research v0.1)",
            latest_summary["summary"]["strategy_parallel_governance_action_summary"],
        )
        self.assertNotIn(
            "downgrade_watch->downgrade(VWAP Proxy Research v0.1)",
            latest_summary["summary"]["strategy_parallel_governance_action_summary"],
        )
        self.assertTrue(latest_summary["strategy_parallel_governance_actions"]["bucket_actions"])
        self.assertTrue(latest_summary["strategy_parallel_governance_rollup"]["priority_overrides"])
        self.assertTrue(latest_summary["strategy_parallel_governance_actions"]["priority_overrides"])
        self.assertTrue(
            {
                "retire_watch",
                "downgrade_watch",
                "healthy_experimental",
            }.intersection(latest_summary["strategy_parallel_governance_rollup"]["bucket_counts"])
        )
        self.assertTrue(
            any(item["strategy_name"] == "Breakout v0.1" for item in latest_summary["strategy_parallel_scorecard"])
        )
        self.assertTrue(latest_summary["source_refs"]["primary_validation_report_id"])
        self.assertIn("candidate_vs_primary_comparison", latest_summary)
        self.assertEqual(
            latest_summary["candidate_vs_primary_comparison"]["candidate_validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            latest_summary["candidate_vs_primary_comparison"]["primary_validation_report_id"],
            latest_summary["source_refs"]["primary_validation_report_id"],
        )
        self.assertFalse(latest_summary["candidate_vs_primary_comparison"]["same_validation_record"])
        self.assertIn(
            latest_summary["candidate_vs_primary_comparison"]["comparison_status"],
            {"improved", "mixed", "worsened"},
        )
        self.assertIn(
            latest_summary["candidate_vs_primary_comparison"]["oos_shift"],
            {"improved", "mixed", "unchanged", "worsened"},
        )
        self.assertIn("候选验证", latest_summary["summary"]["candidate_vs_primary_summary"])
        self.assertEqual(
            latest_summary["summary"]["candidate_vs_primary_summary"],
            latest_summary["candidate_vs_primary_comparison"]["summary"],
        )
        self.assertIn("candidate_vs_previous_variant_comparison", latest_summary)
        self.assertEqual(
            latest_summary["candidate_vs_previous_variant_comparison"]["candidate_validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            latest_summary["candidate_vs_previous_variant_comparison"]["previous_validation_report_id"],
            latest_summary["source_refs"]["previous_variant_validation_report_id"],
        )
        self.assertEqual(
            latest_summary["candidate_vs_previous_variant_comparison"]["previous_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertIn(
            latest_summary["candidate_vs_previous_variant_comparison"]["comparison_status"],
            {"improved", "mixed", "worsened"},
        )
        self.assertIn(
            latest_summary["candidate_vs_previous_variant_comparison"]["oos_shift"],
            {"improved", "mixed", "unchanged", "worsened"},
        )
        self.assertIn("上一轮 replay 变体", latest_summary["summary"]["candidate_vs_previous_variant_summary"])
        self.assertEqual(
            latest_summary["summary"]["candidate_vs_previous_variant_summary"],
            latest_summary["candidate_vs_previous_variant_comparison"]["summary"],
        )
        self.assertIn("replay_variant_timeline", latest_summary)
        self.assertGreaterEqual(latest_summary["replay_variant_timeline"]["count"], 2)
        self.assertEqual(
            latest_summary["summary"]["replay_variant_timeline_count"],
            latest_summary["replay_variant_timeline"]["count"],
        )
        self.assertEqual(
            latest_summary["summary"]["replay_variant_timeline_status_counts"],
            latest_summary["replay_variant_timeline"]["status_counts"],
        )
        self.assertEqual(
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
            latest_summary["replay_variant_timeline"]["status_summary"],
        )
        self.assertEqual(
            latest_summary["summary"]["replay_variant_governance_hint"],
            "continue_targeted_replay",
        )
        self.assertEqual(
            latest_summary["summary"]["replay_variant_governance_priority_action"],
            "continue_targeted_replay",
        )
        self.assertIn(
            "可以继续围绕当前主阻塞项做定向 replay",
            latest_summary["summary"]["replay_variant_governance_summary"],
        )
        self.assertIn("replay 变体时间线", latest_summary["summary"]["replay_variant_timeline_summary"])
        self.assertEqual(
            latest_summary["summary"]["replay_variant_timeline_summary"],
            latest_summary["replay_variant_timeline"]["summary"],
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["status_counts"]["improved"],
            1,
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["status_counts"]["not_available"],
            1,
        )
        self.assertIn(
            "improved=1",
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertIn(
            "not_available=1",
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["row_type"],
            "current_candidate",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["comparison_status"],
            "improved",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["oos_shift"],
            "improved",
        )
        self.assertIn(
            "status=improved",
            latest_summary["replay_variant_timeline"]["rows"][0]["comparison_summary"],
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][-1]["comparison_status"],
            "not_available",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][-1]["oos_shift"],
            "unknown",
        )
        self.assertIn(
            "risk_tighten_small_position",
            [row["variant_key"] for row in latest_summary["replay_variant_timeline"]["rows"]],
        )
        self.assertIn(
            "status=improved",
            latest_summary["summary"]["replay_variant_timeline_summary"],
        )
        self.assertIn("consistency_secondary_driver", latest_summary["summary"])
        self.assertIn("consistency_secondary_driver_label", latest_summary["summary"])
        self.assertTrue(latest_summary["summary"]["consistency_driver_detail_summary"])
        self.assertGreaterEqual(latest_summary["summary"]["return_gap_to_close"], 0.0)
        self.assertGreaterEqual(latest_summary["summary"]["score_gap_to_close"], 0.0)
        self.assertIn("bars=", latest_summary["summary"]["sample_size_thresholds_summary"])
        self.assertEqual(
            latest_summary["summary"]["out_of_sample_guard_gate_status"],
            "pass_but_consistency_gap",
        )
        self.assertFalse(latest_summary["summary"]["out_of_sample_guard_promotion_blocked"])
        self.assertEqual(
            latest_summary["summary"]["out_of_sample_guard_preferred_action"],
            "continue_targeted_replay",
        )
        self.assertIn(
            "样本外结果为 pass",
            latest_summary["summary"]["out_of_sample_guard_summary"],
        )
        self.assertEqual(latest_summary["summary"]["a_share_proxy_bias_label"], "overnight_lock_pressure_bias")
        self.assertEqual(latest_summary["summary"]["a_share_proxy_preferred_action"], "no_trade")
        self.assertEqual(latest_summary["summary"]["a_share_proxy_guard_priority_source_key"], "tdx_realtime_quotes")
        self.assertEqual(latest_summary["summary"]["a_share_proxy_guard_priority_source_label"], "TDX realtime quotes")
        self.assertIn("先接 TDX realtime quotes", latest_summary["summary"]["a_share_proxy_guard_plan_summary"])
        self.assertGreaterEqual(latest_summary["summary"]["a_share_proxy_guard_sample_attached_count"], 0)
        self.assertIsInstance(latest_summary["summary"]["a_share_proxy_guard_priority_sample_available"], bool)
        self.assertGreaterEqual(latest_summary["summary"]["blocked_steps"], 0)
        self.assertLessEqual(
            latest_summary["summary"]["blocked_steps"],
            rerun["next_validation_slice"]["review_checklist"]["blocked_steps"],
        )
        self.assertEqual(
            latest_summary["source_refs"]["validation_report_id"],
            rerun["research_queue_skill_registry_entry"]["metadata"]["latest_validation_report_id"],
        )
        self.assertEqual(
            latest_summary["summary"]["latest_out_of_sample_result"],
            rerun["research_queue_skill_registry_entry"]["out_of_sample_result"],
        )
        self.assertEqual(
            latest_summary["summary"]["sample_consistency"],
            rerun["research_queue_skill_registry_entry"]["metadata"]["sample_consistency"],
        )
        self.assertGreaterEqual(
            latest_summary["summary"]["validation_round_index"],
            1,
        )
        self.assertIsInstance(latest_summary["validation_round"], dict)
        self.assertEqual(
            latest_summary["validation_round"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            latest_summary["validation_round"]["validation_round_index"],
            latest_summary["summary"]["validation_round_index"],
        )
        self.assertTrue(latest_summary["summary"]["validation_round_key"].startswith("vwap-vr-"))
        self.assertIsInstance(
            latest_summary["summary"]["validation_round_reused"],
            bool,
        )
        self.assertIn(
            latest_summary["summary"]["latest_decision_action"],
            {"trade", "wait", "no_trade"},
        )
        self.assertIn(
            latest_summary["summary"]["latest_governance_action"],
            {"keep", "downgrade", "freeze", "retire_candidate", "needs_review"},
        )
        self.assertTrue(latest_summary["blocker_progress"])
        self.assertEqual(
            latest_summary["blocker_progress"][0]["blocker_key"],
            "consistency_guard",
        )
        self.assertEqual(
            latest_summary["blocker_progress"][3]["acceptance_gate_type"],
            "a_share_proxy_guard_acceptance",
        )
        self.assertEqual(
            latest_summary["blocker_progress"][1]["acceptance_gate_type"],
            "sample_size_guard_acceptance",
        )
        self.assertTrue(latest_summary["a_share_proxy_guard"]["blocks_promotion"])
        self.assertIn("blocks_promotion", latest_summary["sample_size_thresholds"])
        self.assertTrue(latest_summary["recommended_next_actions"])
        self.assertTrue(
            all(
                item in rerun["next_validation_slice"]["normalized_follow_up_plan"]
                for item in latest_summary["recommended_next_actions"]
            )
        )
        self.assertTrue(latest_summary["source_refs"]["validation_report_id"])
        self.assertEqual(
            latest_summary["source_refs"]["candidate_validation_source_selection"]["selected_validation_report_id"],
            latest_summary["source_refs"]["validation_report_id"],
        )
        self.assertEqual(
            latest_summary["source_refs"]["candidate_validation_source_selection"]["latest_validation_report_id"],
            rerun["research_queue_skill_registry_entry"]["metadata"]["latest_validation_report_id"],
        )
        self.assertTrue(latest_summary["source_refs"]["decision_record_id"])
        self.assertTrue(latest_summary["source_refs"]["trade_journal_id"])
        self.assertEqual(
            latest_summary["source_refs"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertIn(
            latest_summary["source_refs"]["replay_variant_lineage"]["target_blocker_alignment_status"],
            {"aligned", "historical_mismatch"},
        )
        self.assertEqual(
            latest_summary["source_refs"]["replay_variant_lineage"]["current_target_blocker"],
            latest_summary["next_validation_slice"]["primary_blocker_key"],
        )
        self.assertEqual(
            latest_summary["source_refs"]["validation_round"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertTrue(latest_summary["source_refs"]["previous_variant_validation_report_id"])
        self.assertTrue(latest_summary["source_refs"]["latest_variant_timeline_validation_report_ids"])
        self.assertEqual(
            brain.status()["module_status"]["trading_research_queue_latest_validation_summary"],
            "Implemented",
        )
        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(sync_result["implementation_status"], "Implemented")
        self.assertIn("consistency_guard", sync_result["board_state"]["next_step"])
        self.assertIn(
            latest_summary["summary"]["validation_round_key"],
            sync_result["board_state"]["next_step"],
        )
        self.assertIn(
            str(latest_summary["summary"]["validation_round_index"]),
            sync_result["board_state"]["next_step"],
        )
        self.assertIn("sample_consistency=", sync_result["board_state"]["next_step"])
        self.assertIn("consistency_driver=", sync_result["board_state"]["next_step"])
        self.assertIn("Walk-forward 可见性：", sync_result["board_state"]["next_step"])
        self.assertIn("当前默认下一轮 replay", sync_result["board_state"]["next_step"])
        self.assertIn("先跑 收紧风险暴露", sync_result["board_state"]["next_step"])
        self.assertIn("上轮变体结果", sync_result["board_state"]["next_step"])
        self.assertNotIn("先跑 保留信号只查风险质量", sync_result["board_state"]["next_step"])
        self.assertIn("并行策略样本差距：", sync_result["board_state"]["next_step"])
        self.assertIn("候选对上一轮 replay 变体", sync_result["board_state"]["next_step"])
        self.assertIn("replay 变体时间线：", sync_result["board_state"]["next_step"])
        self.assertIn("replay 变体趋势统计：", sync_result["board_state"]["next_step"])
        self.assertIn("replay 治理提示：", sync_result["board_state"]["next_step"])
        self.assertIn("WorkBuddy 决策树约束快照：phase=", sync_result["board_state"]["next_step"])
        if sync_result["bulletin_state_record"]["metadata"]["sample_size_guard_blocked"]:
            self.assertIn("样本量守门仍阻塞升级", sync_result["board_state"]["next_step"])
            self.assertIn("成交对诊断：", sync_result["board_state"]["next_step"])
        self.assertIn("Experimental / ResearchQueue / no_trade", sync_result["board_state"]["next_step"])
        self.assertIn("A股代理守门仍阻塞升级", sync_result["board_state"]["next_step"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["primary_blocker"],
            "consistency_guard",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["sync_source"],
            "trading_research_queue_latest_validation_summary",
        )
        self.assertIn("sample_size_guard_blocked", sync_result["bulletin_state_record"]["metadata"])
        self.assertIn("sample_size_zero_trade_pairs_reason_key", sync_result["bulletin_state_record"]["metadata"])
        self.assertIn("sample_size_zero_trade_pairs_summary", sync_result["bulletin_state_record"]["metadata"])
        self.assertIn("strategy_parallel_sample_gap_summary", sync_result["bulletin_state_record"]["metadata"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["workbuddy_constraint_phase"],
            scaffold_result["triple_decision_trees_scaffold"]["current_phase"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["workbuddy_constraint_main_force_top_branch"],
            sync_result["latest_validation_summary"]["workbuddy_constraint_snapshot"]["main_force_top_branch"],
        )
        self.assertIn(
            sync_result["bulletin_state_record"]["metadata"]["consistency_primary_driver"],
            {"return_gap", "risk_score_gap", "none", "negative_oos_or_direction_flip"},
        )
        self.assertIn("consistency_secondary_driver", sync_result["bulletin_state_record"]["metadata"])
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["consistency_driver_detail_summary"])
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["consistency_focus_summary"])
        self.assertIn(
            "primary_driver=",
            sync_result["bulletin_state_record"]["metadata"]["consistency_snapshot_summary"],
        )
        self.assertIn("walk_forward_validation", sync_result["bulletin_state_record"]["metadata"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["walk_forward_validation"]["implementation_status"],
            "Experimental",
        )
        self.assertIn(
            sync_result["bulletin_state_record"]["metadata"]["walk_forward_stability_status"],
            {"stable_pass", "mixed", "unstable", "thin", "not_run"},
        )
        self.assertIn(
            sync_result["bulletin_state_record"]["metadata"]["walk_forward_coverage_status"],
            {"sufficient", "thin", "not_run"},
        )
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["walk_forward_summary"])
        self.assertIn("walk_forward=", sync_result["board_state"]["summary"])
        if sync_result["bulletin_state_record"]["metadata"]["consistency_focus_summary"].startswith("当前一致性主要由"):
            self.assertIn("关键差异", sync_result["bulletin_state_record"]["metadata"]["consistency_focus_summary"])
            self.assertIn("关键差异", sync_result["bulletin_state_record"]["next_step"])
        self.assertIn("一致性快照：", sync_result["bulletin_state_record"]["next_step"])
        self.assertIn("下一轮 replay 建议优先围绕", sync_result["bulletin_state_record"]["metadata"]["replay_adjustment_summary"])
        self.assertIn(
            "candidate_vs_previous_variant_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["candidate_vs_previous_variant_status"],
            latest_summary["summary"]["candidate_vs_previous_variant_status"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_timeline_count"],
            latest_summary["summary"]["replay_variant_timeline_count"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_timeline_status_counts"],
            latest_summary["summary"]["replay_variant_timeline_status_counts"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_timeline_status_summary"],
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_governance_hint"],
            latest_summary["summary"]["replay_variant_governance_hint"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["out_of_sample_guard_gate_status"],
            latest_summary["summary"]["out_of_sample_guard_gate_status"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["out_of_sample_guard_preferred_action"],
            latest_summary["summary"]["out_of_sample_guard_preferred_action"],
        )
        self.assertIn(
            "样本外守门",
            sync_result["board_state"]["next_step"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_governance_priority_action"],
            latest_summary["summary"]["replay_variant_governance_priority_action"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_governance_summary"],
            latest_summary["summary"]["replay_variant_governance_summary"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["execution_plan"]["default_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["execution_plan"]["default_variant_label"],
            "收紧风险暴露",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["execution_plan"]["plan_status"],
            "ready_for_replay",
        )
        self.assertIn(
            "trading-replay",
            sync_result["bulletin_state_record"]["metadata"]["execution_plan"]["command_hint"],
        )
        self.assertTrue(sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_blocked"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_bias_label"],
            "overnight_lock_pressure_bias",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_label"],
            "TDX realtime quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_sample_attached_count"],
            latest_summary["summary"]["a_share_proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_sample_available"],
            latest_summary["summary"]["a_share_proxy_guard_priority_sample_available"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["replay_variant_lineage"]["current_target_blocker"],
            sync_result["bulletin_state_record"]["metadata"]["primary_blocker"],
        )
        self.assertEqual(
            sync_result["validation_round"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["latest_validation_report_id"],
            rerun["research_queue_skill_registry_entry"]["metadata"]["latest_validation_report_id"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["id"],
            rerun["research_queue_skill_registry_entry"]["id"],
        )
        self.assertTrue(sync_result["candidate_skill_registry_entry"]["metadata"]["a_share_proxy_guard_blocked"])
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["a_share_proxy_guard_priority_source_label"],
            "TDX realtime quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            sync_result["candidate_skill_registry_entry"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["a_share_proxy_guard_sample_attached_count"],
            latest_summary["summary"]["a_share_proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["candidate_vs_previous_variant_status"],
            latest_summary["summary"]["candidate_vs_previous_variant_status"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_timeline_count"],
            latest_summary["summary"]["replay_variant_timeline_count"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_timeline_status_counts"],
            latest_summary["summary"]["replay_variant_timeline_status_counts"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_timeline_status_summary"],
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_governance_hint"],
            latest_summary["summary"]["replay_variant_governance_hint"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["out_of_sample_guard_gate_status"],
            latest_summary["summary"]["out_of_sample_guard_gate_status"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_governance_priority_action"],
            latest_summary["summary"]["replay_variant_governance_priority_action"],
        )
        self.assertEqual(
            sync_result["candidate_skill_registry_entry"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            sync_result["module_status_record"]["module_name"],
            "trading_domain_v0_1",
        )
        self.assertEqual(sync_result["module_status_record"]["status"], "Active")
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["status_scope"],
            "workflow_runtime",
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["selected_strategy_status"],
            latest_summary["summary"]["latest_trade_journal_status"],
        )
        self.assertIn(
            "latest selected strategy is governed separately",
            sync_result["module_status_record"]["summary"],
        )
        self.assertTrue(sync_result["module_status_record"]["metadata"]["a_share_proxy_guard_blocked"])
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["a_share_proxy_guard_priority_source_label"],
            "TDX realtime quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            sync_result["module_status_record"]["metadata"]["a_share_proxy_guard_plan_summary"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["a_share_proxy_guard_sample_attached_count"],
            latest_summary["summary"]["a_share_proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["candidate_vs_previous_variant_status"],
            latest_summary["summary"]["candidate_vs_previous_variant_status"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_timeline_count"],
            latest_summary["summary"]["replay_variant_timeline_count"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_timeline_status_counts"],
            latest_summary["summary"]["replay_variant_timeline_status_counts"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_timeline_status_summary"],
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_governance_hint"],
            latest_summary["summary"]["replay_variant_governance_hint"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["out_of_sample_guard_gate_status"],
            latest_summary["summary"]["out_of_sample_guard_gate_status"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_governance_priority_action"],
            latest_summary["summary"]["replay_variant_governance_priority_action"],
        )
        self.assertEqual(
            sync_result["module_status_record"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            sync_result["learning_entry"]["entry_type"],
            "trading_research_queue_validation_summary",
        )
        self.assertEqual(
            sync_result["learning_entry"]["target_type"],
            "trading_research_queue_candidate",
        )
        self.assertEqual(
            sync_result["learning_entry"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            sync_result["learning_entry"]["metadata"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            sync_result["learning_entry"]["metadata"]["sync_source"],
            "trading_research_queue_latest_validation_summary",
        )
        self.assertTrue(
            any(item.startswith("Train/OOS consistency:") for item in sync_result["learning_entry"]["lessons"])
        )
        self.assertTrue(sync_result["learning_entry"]["improvement_items"])
        if sync_result["learning_evolution_log"]:
            self.assertEqual(
                sync_result["learning_evolution_log"]["trigger"],
                "trading_research_queue_validation_summary_learning",
            )
        self.assertTrue(
            brain.store.get("learning_entries", sync_result["learning_entry"]["id"])
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertGreaterEqual(
            sync_result["bulletin_state_record"]["metadata"]["validation_round_index"],
            1,
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["recent_event"],
            "trading_research_queue_validation_summary_synced",
        )
        self.assertTrue(
            any(
                latest_summary["summary"]["validation_round_key"] in item["summary"]
                for item in brain.board_status()["recent_events"]
            )
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["trigger"],
            "trading_research_queue_validation_summary_synced",
        )
        self.assertTrue(sync_result["self_evolution_log"]["applied"])
        self.assertIn("sample_size_guard_blocked", sync_result["self_evolution_log"]["metrics"])
        self.assertIn(
            sync_result["self_evolution_log"]["metrics"]["consistency_primary_driver"],
            {"return_gap", "risk_score_gap", "none", "negative_oos_or_direction_flip"},
        )
        self.assertIn("consistency_secondary_driver", sync_result["self_evolution_log"]["metrics"])
        self.assertTrue(sync_result["self_evolution_log"]["metrics"]["consistency_driver_detail_summary"])
        self.assertIn(
            "primary_driver=",
            sync_result["self_evolution_log"]["metrics"]["consistency_snapshot_summary"],
        )
        self.assertIn("关键差异", sync_result["self_evolution_log"]["metrics"]["consistency_focus_summary"])
        self.assertIn("下一轮 replay 建议优先围绕", sync_result["self_evolution_log"]["metrics"]["replay_adjustment_summary"])
        self.assertTrue(sync_result["self_evolution_log"]["metrics"]["a_share_proxy_guard_blocked"])
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["a_share_proxy_guard_priority_source_key"],
            "tdx_realtime_quotes",
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["a_share_proxy_guard_priority_source_label"],
            "TDX realtime quotes",
        )
        self.assertIn(
            "先接 TDX realtime quotes",
            sync_result["self_evolution_log"]["metrics"]["a_share_proxy_guard_plan_summary"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["a_share_proxy_guard_sample_attached_count"],
            latest_summary["summary"]["a_share_proxy_guard_sample_attached_count"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["candidate_vs_previous_variant_status"],
            latest_summary["summary"]["candidate_vs_previous_variant_status"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_timeline_count"],
            latest_summary["summary"]["replay_variant_timeline_count"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_timeline_status_counts"],
            latest_summary["summary"]["replay_variant_timeline_status_counts"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_timeline_status_summary"],
            latest_summary["summary"]["replay_variant_timeline_status_summary"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_governance_hint"],
            latest_summary["summary"]["replay_variant_governance_hint"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["out_of_sample_guard_gate_status"],
            latest_summary["summary"]["out_of_sample_guard_gate_status"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_governance_priority_action"],
            latest_summary["summary"]["replay_variant_governance_priority_action"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_governance_summary"],
            latest_summary["summary"]["replay_variant_governance_summary"],
        )
        status_after_sync = brain.status()
        self.assertEqual(
            status_after_sync["trading_status"]["execution_plan_status"],
            "ready_for_replay",
        )
        self.assertEqual(
            status_after_sync["trading_status"]["next_validation_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            status_after_sync["trading_status"]["next_validation_variant_label"],
            "收紧风险暴露",
        )
        self.assertIn(
            "trading-replay",
            status_after_sync["trading_status"]["next_validation_command_hint"],
        )
        board_after_sync = brain.board_status()
        self.assertEqual(
            board_after_sync["latest_trading_bulletin_state"]["execution_plan_status"],
            "ready_for_replay",
        )
        self.assertEqual(
            board_after_sync["latest_trading_bulletin_state"]["next_validation_variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["next_validation_variant_label"],
            "收紧风险暴露",
        )
        self.assertIn(
            "next_variant=收紧风险暴露(risk_tighten_small_position)",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "plan=ready_for_replay",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_lineage"]["variant_key"],
            "risk_tighten_small_position",
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["replay_variant_lineage"]["current_target_blocker"],
            sync_result["bulletin_state_record"]["metadata"]["primary_blocker"],
        )
        self.assertEqual(
            sync_result["self_evolution_log"]["metrics"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        board_after_sync = brain.board_status()
        self.assertIn("consistency_guard", board_after_sync["next_step"])
        self.assertIn("当前默认下一轮 replay：", board_after_sync["next_step"])
        self.assertIn("收紧风险暴露", board_after_sync["next_step"])
        self.assertIn("先跑 收紧风险暴露", board_after_sync["next_step"])
        self.assertTrue(
            any(
                "根据最新验证摘要同步公告栏" in item["summary"]
                for item in board_after_sync["recent_events"]
            )
        )
        self.assertEqual(
            board_after_sync["latest_trading_research_queue_bulletin_state"]["validation_round"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round"]["validation_round_index"],
            latest_summary["summary"]["validation_round_index"],
        )
        self.assertIn(
            latest_summary["summary"]["validation_round_key"],
            board_after_sync["latest_trading_validation_round_summary"],
        )
        self.assertIn(
            "candidate=vwap",
            board_after_sync["latest_trading_validation_round_summary"],
        )
        self.assertIn(
            "primary_gate=scaffold",
            board_after_sync["latest_trading_validation_round_summary"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["candidate_slug"],
            "vwap",
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["validation_round_key"],
            latest_summary["summary"]["validation_round_key"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["primary_blocker"],
            "consistency_guard",
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["queue_recommendation"],
            board_after_sync["latest_trading_research_queue_bulletin_state"]["queue_recommendation"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["out_of_sample_result"],
            latest_summary["summary"]["latest_out_of_sample_result"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["out_of_sample_result_reason"],
            latest_summary["summary"]["latest_out_of_sample_reason"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["out_of_sample_coverage_status"],
            latest_summary["summary"]["latest_out_of_sample_coverage_status"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["oos_trade_pairs_count"],
            latest_summary["summary"]["latest_oos_trade_pairs_count"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["min_promotable_oos_trade_pairs"],
            latest_summary["summary"]["latest_min_promotable_oos_trade_pairs"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["oos_promotion_ready"],
            latest_summary["summary"]["latest_oos_promotion_ready"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["focus_status"],
            board_after_sync["latest_trading_validation_round_focus"]["queue_recommendation"],
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["focus_risk_level"],
            "high",
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["focus_action_hint"],
            (
                "freeze_watch"
                if board_after_sync["latest_trading_validation_round_focus"]["queue_recommendation"] == "freeze_candidate_watch"
                else "continue_research"
            ),
        )
        self.assertEqual(
            board_after_sync["latest_trading_validation_round_focus"]["focus_machine_state"],
            (
                "research_blocked"
                if board_after_sync["latest_trading_validation_round_focus"]["focus_action_hint"] == "freeze_watch"
                else "research_watch"
            ),
        )
        self.assertIn(
            "candidate=vwap",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "blocker=consistency_guard",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"recommendation={board_after_sync['latest_trading_validation_round_focus']['queue_recommendation']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "oos=pass",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"oos_reason={board_after_sync['latest_trading_validation_round_focus']['out_of_sample_result_reason']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"oos_coverage={board_after_sync['latest_trading_validation_round_focus']['out_of_sample_coverage_status']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "oos_pairs=",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"oos_promotion_ready={board_after_sync['latest_trading_validation_round_focus']['oos_promotion_ready']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "primary_gate=scaffold",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"status={board_after_sync['latest_trading_validation_round_focus']['focus_status']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "risk=high",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"action={board_after_sync['latest_trading_validation_round_focus']['focus_action_hint']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            f"machine_state={board_after_sync['latest_trading_validation_round_focus']['focus_machine_state']}",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "primary_driver=",
            board_after_sync["latest_trading_bulletin_state"]["consistency_snapshot_summary"],
        )
        self.assertIn(
            "consistency=",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertIn(
            "regime_train=",
            board_after_sync["latest_trading_validation_round_focus_summary"],
        )
        self.assertEqual(
            brain.status()["module_status"]["trading_research_queue_sync_bulletin_from_latest_validation"],
            "Implemented",
        )


    def test_research_queue_approval_summary_reflects_writeback_history_status(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        initial_summary = brain.trading_research_queue_approval_summary({"candidate_slug": "vwap", "limit": 5})
        self.assertEqual(initial_summary["summary"]["view_scope"], "summary_with_writeback_history")
        self.assertEqual(initial_summary["summary"]["human_reviewed_count"], 0)
        self.assertEqual(initial_summary["integration_note"]["workflow_status"], "Implemented")
        self.assertFalse(initial_summary["candidate_rows"][0]["human_reviewed"])
        self.assertEqual(initial_summary["candidate_rows"][0]["latest_reviewed_at"], "")

        brain.trading_confirm_research_queue_manual_approval({
            "candidate_slug": "vwap",
            "decision": "deferred",
            "reviewer": "summary-tester",
            "rationale": "鍏堜繚鎸?ResearchQueue锛岀户缁ˉ涓€鑷存€у拰浠ｇ悊瀹堥棬璇佹嵁銆?",
        })

        updated_summary = brain.trading_research_queue_approval_summary({"candidate_slug": "vwap", "limit": 5})
        self.assertEqual(updated_summary["summary"]["view_scope"], "summary_with_writeback_history")
        self.assertEqual(updated_summary["summary"]["approval_record_count"], 1)
        self.assertEqual(updated_summary["summary"]["human_reviewed_count"], 1)
        self.assertEqual(updated_summary["integration_note"]["workflow_status"], "Implemented")
        self.assertTrue(updated_summary["candidate_rows"][0]["human_reviewed"])
        self.assertTrue(updated_summary["candidate_rows"][0]["latest_reviewed_at"])

    def test_research_queue_compare_same_signal_variant_updates_latest_summary_lineage(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_confirm_research_queue_manual_approval({
            "candidate_slug": "vwap",
            "decision": "deferred",
            "reviewer": "test-reviewer",
            "rationale": "鍏堜繚鐣欑爺绌舵€侊紝缁х画鐪嬩竴鑷存€х己鍙ｃ€?",
            "follow_up_items": ["琛ラ綈 consistency_guard"],
            "evidence_notes": ["褰撳墠浠嶆槸 daily_proxy scaffold"],
        })
        brain.trading_workbuddy_probability_fusion_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_interface({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_probability_fusion_mock({
            "symbol": "300418",
            "timeframe": "1d",
        })
        brain.trading_workbuddy_triple_decision_trees_scaffold({
            "symbol": "300418",
            "timeframe": "1d",
        })
        rerun = brain.trading_research_queue_run_next_validation_slice({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
            "variant_key": "risk_compare_same_signal_quality",
        })
        self.assertEqual(
            rerun["candidate_validation_report"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertEqual(
            rerun["candidate_strategy_review"]["metadata"]["replay_variant_lineage"]["variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertEqual(
            rerun["validation_slice_execution"]["execution_outcome_assessment"]["variant_focus_assessment"]["variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertIn(
            rerun["validation_slice_execution"]["execution_outcome_assessment"]["variant_focus_assessment"]["focus_status"],
            {"quality_gap_persists", "coverage_gap_persists", "quality_metrics_stabilized"},
        )
        self.assertIn(
            "同信号风险质量检查：",
            rerun["validation_slice_execution"]["execution_outcome_assessment"]["summary"],
        )
        latest_summary = brain.trading_research_queue_latest_validation_summary({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(
            latest_summary["summary"]["latest_replay_variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertEqual(
            latest_summary["summary"]["latest_replay_variant_label"],
            "保留信号只查风险质量",
        )
        self.assertIn("walk_forward_validation", latest_summary["summary"])
        self.assertIsInstance(latest_summary["summary"]["walk_forward_validation"], dict)
        self.assertIn(
            latest_summary["summary"]["walk_forward_stability_status"],
            {"stable_pass", "mixed", "unstable", "thin", "not_run"},
        )
        self.assertIn(
            latest_summary["summary"]["walk_forward_coverage_status"],
            {"sufficient", "thin", "not_run"},
        )
        self.assertIsInstance(latest_summary["summary"]["walk_forward_summary"], str)
        self.assertEqual(
            latest_summary["source_refs"]["validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            latest_summary["candidate_vs_primary_comparison"]["candidate_validation_report_id"],
            rerun["candidate_validation_report"]["id"],
        )
        self.assertEqual(
            latest_summary["source_refs"]["replay_variant_lineage"]["variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertEqual(
            latest_summary["execution_outcome_assessment"]["variant_focus_assessment"]["variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertIn(
            latest_summary["execution_outcome_assessment"]["variant_focus_assessment"]["focus_status"],
            {"quality_gap_persists", "coverage_gap_persists", "quality_metrics_stabilized"},
        )
        self.assertIn(
            "同信号风险质量检查：",
            latest_summary["summary"]["execution_outcome_summary"],
        )
        self.assertEqual(
            latest_summary["summary"]["default_replay_variant_key"],
            "risk_compare_same_signal_quality",
        )
        self.assertEqual(
            latest_summary["summary"]["default_replay_variant_label"],
            "保留信号只查风险质量",
        )
        self.assertIn(
            "same_signal_quality",
            latest_summary["summary"]["default_replay_variant_reason"],
        )
        self.assertEqual(
            latest_summary["consistency_guard_plan"]["preferred_variant_key"],
            latest_summary["summary"]["default_replay_variant_key"],
        )
        self.assertEqual(
            latest_summary["consistency_guard_plan"]["preferred_variant_label"],
            latest_summary["summary"]["default_replay_variant_label"],
        )
        self.assertEqual(
            latest_summary["consistency_guard_plan"]["effective_variant_preference_origin"],
            "execution_plan_default_variant",
        )
        self.assertEqual(
            latest_summary["consistency_guard_plan"]["suggested_variant_preference_origin"],
            "consistency_guard_primary_driver",
        )
        self.assertEqual(
            latest_summary["execution_plan"]["consistency_guard_plan_summary"],
            latest_summary["summary"]["consistency_guard_plan_summary"],
        )
        self.assertIn(
            "当前执行口径先跑",
            latest_summary["summary"]["consistency_guard_plan_summary"],
        )
        self.assertTrue(
            latest_summary["candidate_vs_previous_variant_comparison"]["same_variant_key_as_candidate"]
        )
        self.assertEqual(
            latest_summary["candidate_vs_previous_variant_comparison"]["previous_variant_repeat_context"],
            "previous_run",
        )
        self.assertIn(
            "（上一次）",
            latest_summary["candidate_vs_previous_variant_comparison"]["previous_variant_label"],
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["variant_label_display"],
            "保留信号只查风险质量（本轮）",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][0]["variant_repeat_context"],
            "current_run",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][1]["variant_label_display"],
            "保留信号只查风险质量（上一次）",
        )
        self.assertEqual(
            latest_summary["replay_variant_timeline"]["rows"][1]["variant_repeat_context"],
            "previous_run",
        )
        self.assertIn(
            "当前候选",
            latest_summary["summary"]["replay_variant_timeline_summary"],
        )
        self.assertIn(
            "保留信号只查风险质量（上一次）",
            latest_summary["summary"]["candidate_vs_previous_variant_summary"],
        )
        self.assertEqual(
            rerun["bulletin_sync"]["implementation_status"],
            "Implemented",
        )
        board_state = brain.board.status()
        self.assertIn(
            "当前默认下一轮 replay",
            board_state["next_step"],
        )
        self.assertIn(
            "本轮 replay（保留信号只查风险质量）",
            board_state["next_step"],
        )
        self.assertNotIn(
            "琛ュ厖浜哄伐鍗囩骇瀹℃壒缁撴灉鍐欏叆鍏ュ彛鍗犱綅",
            board_state["next_step"],
        )
        self.assertIn(
            "primary_driver=",
            brain.status()["trading_status"]["consistency_snapshot_summary"],
        )
        self.assertIn(
            "regime_train=",
            brain.status()["trading_status"]["consistency_snapshot_summary"],
        )

    def test_research_queue_sync_bulletin_surfaces_proxy_sample_status_in_board_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_a_share_tdx_quote_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "ddx": 0.62,
            "ddy": 1.21,
            "change_pct": 2.84,
            "volume_ratio": 1.76,
            "price": 49.93,
            "volume": 950000,
            "amount": 47433500,
            "turnover_rate": 11.6,
            "quote_ts": "2026-07-11T14:39:00+08:00",
        })
        brain.trading_a_share_workbuddy_context_snapshot({
            "symbol": "300418",
            "timeframe": "1d",
            "sector_flow": {"sector": "AI搴旂敤", "strength": 0.64, "leader": "300418"},
            "macro_context": {"market_pressure": 0.03, "risk_mode": "neutral_to_risk_on"},
            "peer_snapshot": [{"symbol": "300418", "relative_rank": 1, "change_pct": 2.9}],
            "fund_flow_context": {"context_score": 0.44, "northbound_bias": "supportive"},
            "quote_ts": "2026-07-11T14:39:20+08:00",
        })

        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })

        self.assertEqual(sync_result["implementation_status"], "Implemented")
        self.assertIn("samples=", sync_result["board_state"]["next_step"])
        self.assertIn("priority_sample=", sync_result["board_state"]["next_step"])
        self.assertIn("priority_stage=payload_sample_only", sync_result["board_state"]["next_step"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_sample_attached_count"],
            2,
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_sample_status"],
            "sample_available",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_sample_connection_mode"],
            "payload_injected_sample",
        )
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_clearance_stage"],
            "payload_sample_only",
        )
        self.assertIn(
            "payload 注入样本",
            sync_result["bulletin_state_record"]["metadata"]["a_share_proxy_guard_priority_source_clearance_summary"],
        )
        degraded_skill = brain.store.get(
            "skill_registry_entries",
            sync_result["candidate_skill_registry_entry"]["id"],
        )
        degraded_skill["metadata"]["out_of_sample_guard_summary"] = {
            "gate_status": "",
            "preferred_action": "",
            "promotion_blocked": False,
            "reason_key": "",
            "severity": "",
            "summary": "",
        }
        brain.store.update_data(
            "skill_registry_entries",
            degraded_skill["id"],
            degraded_skill,
        )
        degraded_module = brain.store.get(
            "module_status_records",
            sync_result["module_status_record"]["id"],
        )
        degraded_module["metadata"]["out_of_sample_guard_summary"] = {
            "gate_status": "",
            "preferred_action": "",
            "promotion_blocked": False,
            "reason_key": "",
            "severity": "",
            "summary": "",
        }
        brain.store.update_data(
            "module_status_records",
            degraded_module["id"],
            degraded_module,
        )
        fallback_summary = brain.trading_research_queue_latest_validation_summary({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(
            fallback_summary["summary"]["out_of_sample_guard_gate_status"],
            "pass_but_consistency_gap",
        )
        self.assertEqual(
            fallback_summary["summary"]["out_of_sample_guard_preferred_action"],
            "continue_targeted_replay",
        )
        self.assertIn(
            "样本外结果为 pass",
            fallback_summary["summary"]["out_of_sample_guard_summary"],
        )
        fallback_sync = brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(
            fallback_sync["bulletin_state_record"]["metadata"]["out_of_sample_guard_gate_status"],
            "pass_but_consistency_gap",
        )
        self.assertIn(
            "样本外守门",
            fallback_sync["board_state"]["next_step"],
        )
        rerun_sync = brain.trading_research_queue_sync_bulletin_from_latest_validation({
            "candidate_slug": "vwap",
            "min_approvals": 1,
            "top_limit": 1,
        })
        self.assertEqual(
            rerun_sync["learning_entry"]["id"],
            sync_result["learning_entry"]["id"],
        )
        self.assertEqual(rerun_sync["learning_evolution_log"], {})

    def test_board_status_prefers_replay_bulletin_row_for_latest_replay_snapshot(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        replay_row = BulletinStateRecord(
            bulletin_path=str(brain.board.path),
            state_status="Experimental",
            summary="300418 replay selection=abstain. Train/OOS snapshot: oos=fail. Costs: total_cost_pct=0.00125.",
            metadata={
                "domain": "trading",
                "selected_strategy_name": "NO_TRADE",
                "selection_status": "abstain",
                "selection_governance_action": "retire_candidate",
                "portfolio_action": "no_trade",
                "selected_sample_summary": "train_return=-0.0574, test_return=-0.1999, oos=fail",
                "selected_sample_consistency": "train_stronger_than_test",
                "top_ranked_candidate_summary": "VWAP Proxy Research v0.1 (oos=pass)",
                "cost_assumption_summary": "commission_pct=0.00025, slippage_pct=0.00100, total_cost_pct=0.00125",
                "selection_state_summary": {
                    "queue_recommendation": "retire_candidate_review",
                    "primary_gate": "out_of_sample",
                    "upgrade_candidate_status": "blocked_by_out_of_sample",
                    "freeze_candidate_status": "freeze_candidate",
                    "summary": "recommendation=retire_candidate_review, primary_gate=out_of_sample",
                },
            },
            created_at="2026-07-15T11:42:25+00:00",
        )
        brain.store.save("bulletin_state_records", replay_row)

        newer_queue_row = BulletinStateRecord(
            bulletin_path=str(brain.board.path),
            state_status="Experimental",
            metadata={
                "domain": "trading",
                "queue_type": "ResearchQueue",
                "candidate_slug": "vwap",
                "selected_strategy_name": "NO_TRADE",
                "selection_status": "abstain",
                "selection_governance_action": "needs_review",
                "portfolio_action": "no_trade",
                "sample_comparison_summary": "train_return=0.4389, test_return=0.0395, oos=pass",
                "selection_state_summary": {
                    "queue_recommendation": "stay_experimental_watch_gap",
                    "primary_gate": "scaffold",
                    "upgrade_candidate_status": "blocked_by_scaffold",
                    "freeze_candidate_status": "watch_consistency_gap",
                    "summary": "recommendation=stay_experimental_watch_gap, primary_gate=scaffold, oos=pass",
                },
            },
            created_at="2026-07-15T11:42:26+00:00",
        )
        brain.store.save("bulletin_state_records", newer_queue_row)

        status = brain.status()
        replay_snapshot = status["latest_trading_replay_bulletin_state"]
        self.assertEqual(replay_snapshot["bulletin_id"], replay_row.id)
        self.assertIn("Train/OOS snapshot:", replay_snapshot["summary"])
        self.assertEqual(replay_snapshot["primary_gate"], "out_of_sample")
        self.assertEqual(replay_snapshot["out_of_sample_result"], "not_run")

    def test_research_queue_manual_approval_blocks_approval_without_ready_evidence(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        with self.assertRaisesRegex(ValueError, "can_submit_now=True"):
            brain.trading_confirm_research_queue_manual_approval({
                "candidate_slug": "vwap",
                "decision": "approved",
                "reviewer": "test-reviewer",
                "rationale": "鎯崇洿鎺ュ崌绾э紝浣嗚瘉鎹繕娌￠綈銆?",
            })

    def test_research_queue_approval_signals_empty_without_approvals(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })

        signals = brain.trading_research_queue_approval_signals({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(signals["summary"]["total_signal_candidates"], 0)
        self.assertEqual(signals["summary"]["signal_counts"], {})
        self.assertEqual(signals["signals"], [])
        watchlist = brain.trading_research_queue_watchlist({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(watchlist["summary"]["total_watch_candidates"], 0)
        self.assertEqual(watchlist["summary"]["bucket_counts"]["needs_review"], 0)
        self.assertEqual(watchlist["watchlist_rows"], [])
        agenda = brain.trading_research_queue_review_agenda({"candidate_slug": "vwap", "min_approvals": 1})
        self.assertEqual(agenda["summary"]["total_agenda_items"], 0)
        self.assertEqual(agenda["agenda_items"], [])
        self.assertEqual(agenda["top_candidates"], [])
        self.assertEqual(agenda["bucket_top_candidates"]["needs_review"], [])
        self.assertEqual(agenda["summary"]["top_priority_score"], 0.0)
        self.assertEqual(agenda["summary"]["top_candidate_slug"], "")

    def test_research_queue_review_agenda_global_ranking_with_second_candidate(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))
        for _ in range(4):
            brain.trading_replay({
                "data_path": str(REAL_REPLAY_JSON),
                "symbol": "300418",
            })
        brain.trading_confirm_research_queue_manual_approval({
            "candidate_slug": "vwap",
            "decision": "deferred",
            "reviewer": "test-reviewer",
            "rationale": "鏍锋湰澶栬櫧鏈け鏁堬紝浣嗚瘉鎹竻鍗曟湭婊¤冻锛屽厛鏆傜紦鍗囩骇銆?",
        })

        second_skill = SkillRegistryEntry(
            skill_name="trading.research_queue.delta_v0_1",
            domain="trading",
            version="v0.1",
            capability_type="research_queue",
            quality_score=0.31,
            evidence_level="interface",
            source_reliability=0.85,
            freshness=0.9,
            validation_status="needs_review",
            out_of_sample_result="fail",
            failure_count=2,
            status="Frozen",
            implementation_status="Interface",
            metadata={
                "domain": "trading",
                "queue_type": "ResearchQueue",
                "candidate_slug": "delta",
                "state_summary": {"queue_recommendation": "freeze_candidate_watch", "primary_gate": "out_of_sample"},
                "evidence_checklist": {"ready_count": 1, "total_count": 5, "missing_keys": ["replacement_candidate", "new_evidence_package", "freeze_rationale_review"]},
                "manual_approval_entrypoint": {
                    "approval_status": "rejected",
                    "can_submit_now": False,
                    "learning_entry_id": "learn_delta_seed",
                    "missing_keys": ["replacement_candidate", "new_evidence_package", "freeze_rationale_review"],
                },
                "manual_approval_writeback": {"entry_type": "trading_research_queue_manual_promotion_approval_result"},
                "manual_approval_confirmation_interface": {"entry_type": "trading_research_queue_manual_promotion_confirmation"},
            },
        )
        brain.store.save("skill_registry_entries", second_skill)
        second_learning = LearningEntry(
            entry_type="trading_research_queue_manual_promotion_approval_result",
            target_type="trading_research_queue_candidate",
            target_ids=[second_skill.id],
            summary="浜哄伐纭浜ゆ槗 ResearchQueue 鍊欓€夆€渄elta鈥濓紝褰撳墠澶勭悊缁撴灉锛氫汉宸ユ嫆缁濆崌绾у苟鍐荤粨璇ュ€欓€夌爺绌跺垏鐗囥€?",
            metadata={
                "candidate_slug": "delta",
                "decision": "rejected",
                "reviewer": "test-reviewer",
            },
        )
        brain.store.save("learning_entries", second_learning)

        agenda = brain.trading_research_queue_review_agenda({"min_approvals": 1, "top_limit": 2})
        self.assertEqual(agenda["summary"]["total_agenda_items"], 2)
        self.assertEqual(agenda["summary"]["top_candidate_limit"], 2)
        self.assertEqual(agenda["top_candidates"][0]["candidate_slug"], "vwap")
        self.assertEqual(agenda["top_candidates"][1]["candidate_slug"], "delta")
        self.assertEqual(agenda["bucket_top_candidates"]["needs_review"][0]["candidate_slug"], "vwap")
        self.assertEqual(agenda["bucket_top_candidates"]["freeze_watch"][0]["candidate_slug"], "delta")
        self.assertEqual(agenda["top_candidates"][0]["bucket"], "needs_review")
        self.assertEqual(agenda["top_candidates"][1]["bucket"], "freeze_watch")
        self.assertGreater(agenda["top_candidates"][0]["priority_score"], agenda["top_candidates"][1]["priority_score"])
        self.assertEqual(agenda["top_candidates"][0]["replay_variant_governance_priority_action"], "continue_targeted_replay")
        self.assertEqual(agenda["top_candidates"][0]["score_components"]["replay_governance_weight"], 4.0)
        self.assertEqual(agenda["top_candidates"][1]["score_components"]["replay_governance_weight"], 0.0)
        self.assertEqual(
            round(sum(agenda["top_candidates"][1]["score_components"].values()), 2),
            agenda["top_candidates"][1]["priority_score"],
        )
        self.assertIn("out-of-sample risk", agenda["top_candidates"][1]["score_explanation"])
        self.assertIn("oos=fail", agenda["top_candidates"][1]["score_explanation"])
        self.assertEqual(agenda["bucket_top_candidates"]["freeze_watch"][0]["out_of_sample_result"], "fail")
        self.assertIn("oos=fail", agenda["bucket_top_candidates"]["freeze_watch"][0]["ranking_reason"])
        self.assertEqual(agenda["summary"]["top_candidate_slug"], "vwap")

    def test_research_queue_next_validation_slice_template_waits_for_market_data(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        brain = SuperBrainV01(Path(tmp.name))

        next_slice = brain.trading_research_queue_next_validation_slice({"candidate_slug": "vwap"})
        self.assertEqual(next_slice["implementation_status"], "Implemented")
        self.assertEqual(next_slice["candidate_slug"], "vwap")
        self.assertFalse(next_slice["summary"]["ready_to_run"])
        self.assertEqual(next_slice["summary"]["focus_now"], "当前没有可生成的下一轮验证切片。")
        latest_summary = brain.trading_research_queue_latest_validation_summary({"candidate_slug": "vwap"})
        self.assertEqual(latest_summary["implementation_status"], "Implemented")
        self.assertEqual(latest_summary["summary"]["candidate_slug"], "vwap")
        self.assertEqual(latest_summary["summary"]["blocked_steps"], 0)
        self.assertEqual(latest_summary["blocker_progress"], [])
        self.assertEqual(latest_summary["strategy_parallel_scorecard"], [])
        self.assertEqual(latest_summary["summary"]["strategy_parallel_scorecard_count"], 0)
        self.assertEqual(latest_summary["summary"]["strategy_parallel_scorecard_summary"], "")
        self.assertEqual(latest_summary["summary"]["strategy_parallel_sample_gap_summary"], "")
        self.assertEqual(latest_summary["strategy_parallel_governance_rollup"], {})
        self.assertEqual(latest_summary["summary"]["strategy_parallel_governance_summary"], "")
        self.assertEqual(latest_summary["summary"]["candidate_vs_primary_status"], "not_available")
        self.assertEqual(latest_summary["summary"]["candidate_vs_primary_oos_shift"], "unknown")
        self.assertIn("暂时无法生成", latest_summary["summary"]["candidate_vs_primary_summary"])
        self.assertEqual(latest_summary["summary"]["candidate_vs_previous_variant_status"], "not_available")
        self.assertEqual(latest_summary["summary"]["candidate_vs_previous_variant_oos_shift"], "unknown")
        self.assertIn("暂时无法生成", latest_summary["summary"]["candidate_vs_previous_variant_summary"])
        self.assertEqual(latest_summary["replay_variant_timeline"]["count"], 0)
        self.assertEqual(latest_summary["summary"]["replay_variant_timeline_status_counts"], {})
        self.assertEqual(latest_summary["summary"]["replay_variant_timeline_status_summary"], "暂无可计数的 replay 变体趋势。")
        self.assertEqual(latest_summary["summary"]["replay_variant_governance_hint"], "insufficient_variant_history")
        self.assertEqual(latest_summary["summary"]["replay_variant_governance_priority_action"], "collect_more_variants")
        self.assertIn("变体历史不足", latest_summary["summary"]["replay_variant_governance_summary"])
        self.assertIn("没有可识别的 replay 变体时间线", latest_summary["summary"]["replay_variant_timeline_summary"])
        self.assertIn("consistency_guard_plan", latest_summary)
        self.assertIn("consistency_guard_plan_summary", latest_summary["summary"])
        self.assertTrue(latest_summary["summary"]["consistency_guard_plan_summary"])
        self.assertEqual(latest_summary["source_refs"]["primary_validation_report_id"], "")
        sync_result = brain.trading_research_queue_sync_bulletin_from_latest_validation({"candidate_slug": "vwap"})
        self.assertEqual(sync_result["implementation_status"], "Implemented")
        self.assertIn("验证证据", sync_result["board_state"]["next_step"])
        self.assertEqual(
            sync_result["bulletin_state_record"]["metadata"]["candidate_slug"],
            "vwap",
        )
        self.assertIn(
            "candidate_vs_primary_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "strategy_parallel_governance_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "strategy_parallel_governance_action_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "consistency_guard_plan_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "execution_plan_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "execution_plan",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "execution_outcome_summary",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertIn(
            "execution_outcome_assessment",
            sync_result["bulletin_state_record"]["metadata"],
        )
        self.assertEqual(sync_result["learning_entry"], {})
        self.assertEqual(sync_result["learning_evolution_log"], {})
        with self.assertRaisesRegex(ValueError, "not runnable yet"):
            brain.trading_research_queue_run_next_validation_slice({"candidate_slug": "vwap"})

    def test_market_regime_split_is_attached_to_train_test_validation(self):
        brain, sample = self.make_brain_with_data()
        result = brain.trading_replay({
            "data_path": str(sample),
            "symbol": "300418",
        })

        split_summary = result["backtest_result"]["metadata"]["train_test_split"]
        self.assertIn("market_regime_split", split_summary)
        regime_split = split_summary["market_regime_split"]
        self.assertEqual(set(regime_split.keys()), {"train", "test"})
        self.assertIn("dominant_regime", regime_split["train"])
        self.assertIn("dominant_regime", regime_split["test"])
        self.assertIn("counts", regime_split["train"])
        self.assertIn("counts", regime_split["test"])
        self.assertIn("summary", regime_split["train"])
        self.assertIn("summary", regime_split["test"])
        self.assertGreater(regime_split["train"]["bars_count"], 0)
        self.assertGreater(regime_split["test"]["bars_count"], 0)


if __name__ == "__main__":
    unittest.main()
