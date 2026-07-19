from __future__ import annotations

import unittest

from brain_core.trading_domain import TradingDomainV01
from core.finance_advisor import Bar, backtest_sma_cross


class TradeBreakdownSummaryTests(unittest.TestCase):
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

    def test_sma_backtest_exposes_recent_trade_pairs_for_summary_consumers(self):
        bars = [
            Bar(date="2026-05-01", open=10.0, high=10.2, low=9.9, close=10.0, volume=100000),
            Bar(date="2026-05-02", open=10.0, high=10.1, low=9.8, close=9.9, volume=105000),
            Bar(date="2026-05-05", open=9.9, high=10.0, low=9.7, close=9.8, volume=110000),
            Bar(date="2026-05-06", open=9.8, high=10.3, low=9.8, close=10.2, volume=160000),
            Bar(date="2026-05-07", open=10.2, high=10.6, low=10.1, close=10.5, volume=170000),
            Bar(date="2026-05-08", open=10.5, high=10.8, low=10.4, close=10.7, volume=180000),
            Bar(date="2026-05-09", open=10.7, high=10.9, low=10.2, close=10.3, volume=175000),
            Bar(date="2026-05-12", open=10.3, high=10.4, low=9.9, close=10.0, volume=165000),
        ]

        result = backtest_sma_cross(
            bars=bars,
            short_window=2,
            long_window=3,
            initial_cash=100000.0,
            fee_rate=0.0003,
        )

        self.assertIn("recent_trade_pairs", result)
        self.assertTrue(result["recent_trade_pairs"])
        pair = result["recent_trade_pairs"][0]
        self.assertIn("entry", pair)
        self.assertIn("exit", pair)
        self.assertTrue(pair["entry"]["date"])
        self.assertTrue(pair["exit"]["date"])


if __name__ == "__main__":
    unittest.main()
