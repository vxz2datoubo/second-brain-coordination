from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.qclaw import QClawBridge, QClawError
from core.tushare_bridge import TushareBridge
from daytrade_system.live.tdx_mcp_client import TdxMcpClient
import mcp.tdx_live_bridge as tdx_live_bridge


class _FakeHttpResponse:
    def __init__(self, body: str, headers: dict | None = None):
        self._body = body.encode("utf-8")
        self.headers = headers or {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class GitCredentialSanitizationTests(unittest.TestCase):
    def test_tushare_bridge_fails_safely_without_token(self):
        bridge = TushareBridge(token="")
        with patch("core.tushare_bridge.requests.post") as mock_post:
            with self.assertRaisesRegex(RuntimeError, "Tushare token missing"):
                bridge.daily("300418.SZ", "20260101", "20260131")
        mock_post.assert_not_called()

    def test_tushare_bridge_reads_token_from_env(self):
        bridge = TushareBridge(token="test-tushare-token")
        captured = {}

        def fake_post(url, json=None, timeout=None):
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout

            class _Resp:
                @staticmethod
                def json():
                    return {"code": 0, "data": {"items": [{"trade_date": "20260105"}]}}

            return _Resp()

        with patch("core.tushare_bridge.requests.post", side_effect=fake_post):
            rows = bridge.daily("300418.SZ", "20260101", "20260131")
        self.assertEqual(rows, [{"trade_date": "20260105"}])
        self.assertEqual(captured["json"]["token"], "test-tushare-token")

    def test_qclaw_bridge_fails_safely_without_token(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        missing_qclaw = str(Path(tmp.name) / "missing-qclaw.json")
        missing_openclaw = str(Path(tmp.name) / "missing-openclaw.json")
        with patch("core.qclaw.QCLAW_CONFIG_PATH", missing_qclaw), patch(
            "core.qclaw.OPENCLAW_CONFIG_PATH", missing_openclaw
        ), patch.dict("os.environ", {"QCLAW_GATEWAY_TOKEN": ""}, clear=False):
            bridge = QClawBridge(api_url="http://127.0.0.1:9/v1/chat/completions")
            health = bridge.health_check()
            self.assertFalse(health["token_available"])
            with self.assertRaises(QClawError) as ctx:
                bridge.ask("hello")
        self.assertEqual(ctx.exception.category, "auth")

    def test_tdx_client_fails_safely_without_token(self):
        client = TdxMcpClient(token="")
        with patch("daytrade_system.live.tdx_mcp_client.urllib.request.urlopen") as mock_urlopen:
            with self.assertRaisesRegex(RuntimeError, "TDX MCP token missing"):
                client.get_quotes(["300418"])
        mock_urlopen.assert_not_called()

    def test_tdx_client_uses_test_token_without_secret_fallback(self):
        client = TdxMcpClient(token="test-tdx-token")
        captured = {}

        def fake_urlopen(req, timeout=0):
            captured["authorization"] = req.headers.get("Authorization")
            body = 'data: {"result": [{"code": "300418", "last_price": 48.5}]}\n'
            return _FakeHttpResponse(body)

        with patch("daytrade_system.live.tdx_mcp_client.urllib.request.urlopen", side_effect=fake_urlopen):
            rows = client.get_quotes(["300418"])
        self.assertEqual(rows[0]["code"], "300418")
        self.assertEqual(captured["authorization"], "Bearer test-tdx-token")

    def test_tdx_live_bridge_reports_missing_token_when_sources_absent(self):
        with patch.object(tdx_live_bridge, "TOKEN", ""), patch.object(tdx_live_bridge, "_sess", None):
            with self.assertRaisesRegex(RuntimeError, "TDX MCP token missing"):
                tdx_live_bridge._get_sess()

    def test_local_credentials_example_is_safe_json(self):
        payload = json.loads(Path("F:/aidanao/config/local_credentials.example.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["tushare_token"], "replace-with-local-token")
        self.assertEqual(payload["workbuddy_tdx_token"], "replace-with-local-token")

    def test_env_example_contains_only_placeholder_values(self):
        lines = Path("F:/aidanao/.env.example").read_text(encoding="utf-8").splitlines()
        content = "\n".join(line for line in lines if line and not line.startswith("#"))
        self.assertIn("replace-with-local-token", content)
        self.assertNotIn("TDX-", content)
        self.assertNotIn("ts-", content.lower())


if __name__ == "__main__":
    unittest.main()
