from __future__ import annotations

import unittest
from unittest.mock import patch

from server import SecondBrainHandler


class DummyHandler:
    def __init__(self):
        self.sent = None
        self.status = None

    def send_json(self, data, status=200):
        self.sent = data
        self.status = status

    _coerce_bool_flag = staticmethod(SecondBrainHandler._coerce_bool_flag)


class ServerV0ApiTests(unittest.TestCase):
    def test_coerce_bool_flag_handles_querystring_list_and_text(self):
        self.assertTrue(SecondBrainHandler._coerce_bool_flag("true"))
        self.assertTrue(SecondBrainHandler._coerce_bool_flag(["1"]))
        self.assertTrue(SecondBrainHandler._coerce_bool_flag(["yes"]))
        self.assertFalse(SecondBrainHandler._coerce_bool_flag(""))
        self.assertFalse(SecondBrainHandler._coerce_bool_flag(["false"]))

    @patch("server._v01")
    def test_v0_trading_replay_summary_only_returns_replay_summary(self, mock_v01):
        handler = DummyHandler()
        mock_v01.trading_replay.return_value = {
            "replay_summary": {
                "symbol": "300418",
                "implementation_status": "Implemented",
                "sample_comparison": {"consistency": "fail"},
            },
            "strategy_definition": {"name": "SMA Trend v0.1"},
        }

        SecondBrainHandler.v0_trading_replay(handler, {"summary_only": "true", "symbol": "300418"})

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.sent["symbol"], "300418")
        self.assertEqual(handler.sent["implementation_status"], "Implemented")
        self.assertIn("sample_comparison", handler.sent)

    @patch("server._v01")
    def test_v0_trading_replay_default_returns_full_payload(self, mock_v01):
        handler = DummyHandler()
        mock_v01.trading_replay.return_value = {
            "replay_summary": {"symbol": "300418"},
            "strategy_definition": {"name": "SMA Trend v0.1"},
        }

        SecondBrainHandler.v0_trading_replay(handler, {"symbol": "300418"})

        self.assertEqual(handler.status, 200)
        self.assertIn("strategy_definition", handler.sent)
        self.assertIn("replay_summary", handler.sent)

    @patch("server._v01")
    def test_v0_trading_a_share_realtime_crosscheck_summary_returns_service_payload(self, mock_v01):
        handler = DummyHandler()
        mock_v01.trading_a_share_realtime_crosscheck_summary.return_value = {
            "symbol": "300418",
            "alignment": "mixed",
            "recommended_action": "wait",
        }

        SecondBrainHandler.v0_trading_a_share_realtime_crosscheck_summary(
            handler,
            {"symbol": "300418", "timeframe": "1d"},
        )

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.sent["symbol"], "300418")
        self.assertEqual(handler.sent["recommended_action"], "wait")

    @patch("server._v01")
    def test_v0_trading_a_share_tencent_snapshot_returns_service_payload(self, mock_v01):
        handler = DummyHandler()
        mock_v01.trading_a_share_tencent_qt_realtime_snapshot.return_value = {
            "symbol": "300418",
            "implementation_status": "Implemented",
        }

        SecondBrainHandler.v0_trading_a_share_tencent_qt_realtime_snapshot(
            handler,
            {"symbol": "300418"},
        )

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.sent["implementation_status"], "Implemented")


if __name__ == "__main__":
    unittest.main()
