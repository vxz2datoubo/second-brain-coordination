"""
通达信 MCP HTTP 客户端
直接从 TDX 云平台 API 获取实时行情、K线、新闻等数据
OAuth token 已从 WorkBuddy credentials 提取
"""

import json
import time
import urllib.request
import urllib.error
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

# ============================================================
# TDX MCP 配置（从 WorkBuddy credentials 提取）
# ============================================================
ROOT = Path(__file__).resolve().parents[2]
TDX_MCP_URL = os.environ.get("TDX_MCP_URL", "https://txmcp.tdx.com.cn:3001/txmcp")
WORKBUDDY_CONNECTOR_ID = "a112e458-4c79-4b41-96b6-03e953dffd50"
ENV_TDX_TOKEN = "WORKBUDDY_TDX_TOKEN"
ENV_LOCAL_CREDENTIALS_PATH = "AIDANAO_LOCAL_CONFIG"


def _credential_paths() -> list[Path]:
    workbuddy_home = os.environ.get("WORKBUDDY_HOME", "").strip()
    paths = [
        Path(f"C:/Users/Administrator/.workbuddy/connectors/{WORKBUDDY_CONNECTOR_ID}/.credentials.json"),
    ]
    if workbuddy_home:
        paths.append(Path(workbuddy_home) / "connectors" / WORKBUDDY_CONNECTOR_ID / ".credentials.json")
    return paths


def _local_credential_candidates() -> list[Path]:
    candidates: list[Path] = []
    env_path = os.environ.get(ENV_LOCAL_CREDENTIALS_PATH, "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(ROOT / "config" / "local_credentials.json")
    out: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        normalized = str(path).strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(path)
    return out


def _read_json_file(path: Path) -> dict:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return {}


def _load_tdx_token(explicit_token: Optional[str] = None) -> str:
    if explicit_token is not None:
        return str(explicit_token).strip()
    env_token = os.environ.get(ENV_TDX_TOKEN, "").strip()
    if env_token:
        return env_token
    for path in _credential_paths():
        data = _read_json_file(path)
        for value in (data.get("mcpOAuth", {}) or {}).values():
            if isinstance(value, dict):
                token = str(value.get("accessToken", "") or "").strip()
                if token:
                    return token
    for path in _local_credential_candidates():
        data = _read_json_file(path)
        for key in ("workbuddy_tdx_token", "WORKBUDDY_TDX_TOKEN", "tdx_token"):
            token = data.get(key)
            if isinstance(token, str) and token.strip():
                return token.strip()
    return ""

# ============================================================
# HTTP 客户端
# ============================================================
class TdxMcpClient:
    def __init__(self, base_url: str = TDX_MCP_URL, token: Optional[str] = None):
        self.base_url = base_url
        self.token = _load_tdx_token(token)
        self._request_id = 0
        self._last_request_time = 0
        self._min_interval = 0.1  # 最小请求间隔 100ms

    def _require_token(self) -> str:
        if not self.token:
            raise RuntimeError(
                "TDX MCP token missing. Set WORKBUDDY_TDX_TOKEN or provide config/local_credentials.json."
            )
        return self.token

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _throttle(self):
        """请求限流"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()

    def _do_request(self, method: str, params: Dict) -> Dict:
        """发送 JSON-RPC 请求"""
        self._throttle()
        token = self._require_token()
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params
        }).encode("utf-8")

        req = urllib.request.Request(
            self.base_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
                "Accept": "application/json, text/event-stream",
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                lines = raw.strip().split("\n")
                for line in lines:
                    if line.startswith("data:"):
                        line = line[5:].strip()
                    if line:
                        result = json.loads(line)
                        if "result" in result:
                            return result["result"]
                        if "error" in result:
                            raise Exception(f"MCP Error: {result['error']}")
                return {}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            raise Exception(f"HTTP {e.code}: {error_body[:500]}")
        except Exception as e:
            raise Exception(f"MCP 请求失败: {e}")

    def get_quotes(self, codes: List[str], fields: List[str] = None) -> List[Dict]:
        params = {"codes": codes}
        if fields:
            params["fields"] = fields
        result = self._do_request("tools/call", {
            "name": "tdx_quotes",
            "arguments": params
        })
        return result if isinstance(result, list) else [result]

    def get_kline(self, code: str, period: str = "5m", count: int = 100) -> List[Dict]:
        result = self._do_request("tools/call", {
            "name": "tdx_kline",
            "arguments": {"code": code, "period": period, "count": count}
        })
        return result if isinstance(result, list) else []

    def get_news(self, keyword: str, category: str = None,
                  date_range: str = "last_7_days", limit: int = 20) -> List[Dict]:
        args = {"keyword": keyword, "date_range": date_range, "limit": limit}
        if category:
            args["category"] = category
        result = self._do_request("tools/call", {
            "name": "wenda_news_query",
            "arguments": args
        })
        return result if isinstance(result, list) else []

    def get_notices(self, code: str, notice_type: str = None,
                     date_range: str = "last_7_days", limit: int = 10) -> List[Dict]:
        args = {"code": code, "date_range": date_range, "limit": limit}
        if notice_type:
            args["notice_type"] = notice_type
        result = self._do_request("tools/call", {
            "name": "wenda_notice_query",
            "arguments": args
        })
        return result if isinstance(result, list) else []

    def lookup_stock(self, keyword: str, market: str = None) -> List[Dict]:
        args = {"keyword": keyword}
        if market:
            args["market"] = market
        result = self._do_request("tools/call", {
            "name": "tdx_lookup_stock",
            "arguments": args
        })
        return result if isinstance(result, list) else []

    def get_macro(self, indicator: str, date_range: str = "last_30_days",
                   limit: int = 20) -> List[Dict]:
        result = self._do_request("tools/call", {
            "name": "wenda_macro_query",
            "arguments": {"indicator": indicator, "date_range": date_range, "limit": limit}
        })
        return result if isinstance(result, list) else []

    def screener(self, query: str, limit: int = 20) -> List[Dict]:
        result = self._do_request("tools/call", {
            "name": "tdx_screener",
            "arguments": {"query": query, "limit": limit}
        })
        return result if isinstance(result, list) else []

    def ping(self) -> bool:
        try:
            self._do_request("tools/list", {})
            return True
        except Exception:
            return False


# 全局单例
_client: Optional[TdxMcpClient] = None

def get_client() -> TdxMcpClient:
    global _client
    if _client is None:
        _client = TdxMcpClient()
    return _client


def get_realtime_quote(codes: List[str]) -> Dict[str, Dict]:
    client = get_client()
    quotes = client.get_quotes(codes)
    return {q.get("code") or q.get("sh_code") or q.get("sz_code"): q for q in quotes}


def get_min5_bars(code: str, count: int = 100) -> List[Dict]:
    return get_client().get_kline(code, "5m", count)


def get_daily_bars(code: str, count: int = 120) -> List[Dict]:
    return get_client().get_kline(code, "day", count)


def get_stock_news(codes: List[str], limit: int = 10) -> List[Dict]:
    client = get_client()
    all_news = []
    for code in codes:
        try:
            news = client.get_news(code, limit=limit)
            for n in news:
                n["_source_code"] = code
            all_news.extend(news)
        except Exception:
            pass
    return all_news


if __name__ == "__main__":
    c = get_client()
    print("=== 连接测试 ===")
    print("健康检查:", c.ping())
    print("\n=== 实时行情 ===")
    q = c.get_quotes(["300418", "300058"])
    for item in q:
        name = item.get("name", item.get("code", "?"))
        now = item.get("now", "N/A")
        pct = item.get("pct_chg", "?")
        print(f"  {name}: {now} ({pct}%)")
    print("\n=== 5分钟K线(昆仑) ===")
    bars = c.get_kline("300418", "5m", 5)
    print(f"  获取到 {len(bars)} 条, 最新: {bars[-1] if bars else 'N/A'}")
