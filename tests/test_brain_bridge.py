from __future__ import annotations

import unittest
from unittest.mock import patch

from mcp import brain_bridge


class BrainBridgeTests(unittest.TestCase):
    @patch("mcp.brain_bridge._post_json")
    def test_tool_brain_trading_replay_formats_compact_summary(self, mock_post_json):
        mock_post_json.return_value = {
            "top_level_strategy_name": "SMA Trend v0.1",
            "candidate_count": 3,
            "selection_reason": "No candidate satisfied keep + out_of_sample pass gate.",
            "selected_candidate_summary": {
                "selection_status": "abstain",
                "portfolio_action": "no_trade",
                "selection_governance_action": "retire_candidate",
                "out_of_sample_result": "fail",
                "validation_verdict": "needs_review",
                "sample_consistency": "train_stronger_than_test",
                "governance_primary_reason": "oos_fail_plus_gap",
                "primary_gate": "out_of_sample",
                "queue_recommendation": "freeze_candidate_watch",
                "freeze_candidate_status": "freeze_candidate",
                "upgrade_candidate_status": "blocked_by_out_of_sample",
                "governance_rule_summary": "selected_action=retire_candidate; triggered_actions=retire_candidate,freeze",
                "sample_comparison_summary": "train_return=0.12, test_return=-0.03, oos=fail",
            },
            "candidate_summaries": [
                {
                    "strategy_name": "SMA Trend v0.1",
                    "out_of_sample_result": "fail",
                    "sample_consistency": "train_stronger_than_test",
                    "governance_action": "retire_candidate",
                    "primary_gate": "out_of_sample",
                    "total_return": 0.0215,
                }
            ],
            "validation_warnings": ["Research-only proxy chain."],
        }

        text = brain_bridge.tool_brain_trading_replay({"symbol": "300418"})

        self.assertIn("300418 replay 摘要", text)
        self.assertIn("当前动作: no_trade", text)
        self.assertIn("治理动作: retire_candidate", text)
        self.assertIn("样本外结果: fail", text)
        self.assertIn("样本一致性: train_stronger_than_test", text)
        self.assertIn("治理主因: oos_fail_plus_gap", text)
        self.assertIn("当前主门: out_of_sample", text)
        self.assertIn("队列建议: freeze_candidate_watch", text)
        self.assertIn("冻结态: freeze_candidate", text)
        self.assertIn("升级态: blocked_by_out_of_sample", text)
        self.assertIn("规则摘要: selected_action=retire_candidate; triggered_actions=retire_candidate,freeze", text)
        self.assertIn("候选比较:", text)
        self.assertIn("SMA Trend v0.1: oos=fail", text)
        self.assertIn("gate=out_of_sample", text)

    @patch("mcp.brain_bridge._post_json")
    def test_tool_brain_a_share_realtime_crosscheck_formats_lane_summary(self, mock_post_json):
        mock_post_json.return_value = {
            "implementation_status": "Implemented",
            "crosscheck_summary": {
                "symbol": "300418",
                "timeframe": "1d",
                "tdx_signal": "supportive",
                "tencent_signal": "mixed",
                "workbuddy_signal": "supportive",
                "alignment": "aligned_supportive",
                "recommended_action": "watch",
                "primary_risk": "experimental_connector_gap",
                "implementation_status": "Experimental",
                "summary": "Three-lane summary.",
                "warnings": ["All lanes are experimental."],
            },
        }

        text = brain_bridge.tool_brain_a_share_realtime_crosscheck({"symbol": "300418"})

        self.assertIn("A股实时交叉校验摘要", text)
        self.assertIn("TDX 信号: supportive", text)
        self.assertIn("研究态建议: watch", text)
        self.assertIn("实现状态: Experimental", text)


if __name__ == "__main__":
    unittest.main()
