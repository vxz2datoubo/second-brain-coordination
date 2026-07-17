import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

TDX_URL = os.environ.get("TDX_MCP_URL", "https://txmcp.tdx.com.cn:3001/txmcp")
WORKBUDDY_CONNECTOR_ID = "a112e458-4c79-4b41-96b6-03e953dffd50"
ROOT = Path(__file__).resolve().parents[1]
ENV_LOCAL_CREDENTIALS_PATH = "AIDANAO_LOCAL_CONFIG"
ENV_TDX_TOKEN = "WORKBUDDY_TDX_TOKEN"
TOKEN_MISSING_MESSAGE = (
    "TDX MCP token missing. Set WORKBUDDY_TDX_TOKEN or provide config/local_credentials.json."
)


def _credential_paths():
    paths = [
        Path(f"C:/Users/Administrator/.workbuddy/connectors/{WORKBUDDY_CONNECTOR_ID}/.credentials.json"),
    ]
    workbuddy_home = os.environ.get("WORKBUDDY_HOME", "").strip()
    if workbuddy_home:
        paths.append(Path(workbuddy_home) / "connectors" / WORKBUDDY_CONNECTOR_ID / ".credentials.json")
    return paths


def _local_credential_candidates():
    candidates = []
    env_path = os.environ.get(ENV_LOCAL_CREDENTIALS_PATH, "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(ROOT / "config" / "local_credentials.json")
    out = []
    seen = set()
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
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        pass
    return {}


def _load_token():
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


TOKEN = _load_token()


def _require_token():
    if not TOKEN:
        raise RuntimeError(TOKEN_MISSING_MESSAGE)
    return TOKEN


class MCPSession:
    def __init__(self, url, token):
        self.url = url
        self.token = token
        self.sid = None
        self._init()

    def _init(self):
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "tdx-live", "version": "1.0.2"},
                },
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer " + self.token,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                self.sid = resp.headers.get("mcp-session-id")
        except Exception as exc:
            print("init error:", exc, file=sys.stderr)

    def call(self, name, args, rid):
        if not self.sid:
            return {"error": "no session"}
        body = json.dumps(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            self.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": "Bearer " + self.token,
                "mcp-session-id": self.sid,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                for line in raw.split("\n"):
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        if "result" in data:
                            return data["result"]
                        if "error" in data:
                            return {"error": data["error"]}
                return {"error": "no result"}
        except urllib.error.HTTPError as exc:
            return {"error": "HTTP " + str(exc.code)}
        except Exception as exc:
            return {"error": str(exc)}


_sess = None


def _get_sess():
    global _sess
    token = _require_token()
    if _sess is None:
        _sess = MCPSession(TDX_URL, token)
    return _sess


def _setcode(code):
    return "1" if code.startswith(("60", "68")) else "0"


TOOLS = [
    {
        "name": "tdx_realtime",
        "description": "Realtime quote: code",
        "inputSchema": {"type": "object", "properties": {"code": {"type": "string"}}, "required": ["code"]},
    },
    {
        "name": "tdx_kline",
        "description": "Kline: code,period,count",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "period": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["code", "period"],
        },
    },
    {
        "name": "tdx_lookup",
        "description": "Search: query",
        "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "tdx_news",
        "description": "News: keyword,date_range,limit",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "date_range": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["keyword"],
        },
    },
    {
        "name": "tdx_notice",
        "description": "Notice: code,date_range,limit",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "date_range": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "tdx_screener",
        "description": "Screen: query,limit",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"],
        },
    },
]


def _exec(name, args):
    session = _get_sess()
    rid = (id(args) + 100) % 9999
    if name == "tdx_realtime":
        code = args.get("code", "")
        return session.call("tdx_quotes", {"code": code, "setcode": _setcode(code)}, rid)
    if name == "tdx_kline":
        code = args.get("code", "")
        return session.call(
            "tdx_kline",
            {
                "code": code,
                "period": args.get("period", "5m"),
                "count": args.get("count", 100),
                "setcode": _setcode(code),
            },
            rid,
        )
    if name == "tdx_lookup":
        return session.call("tdx_lookup_stock", {"query": args.get("query", "")}, rid)
    if name == "tdx_news":
        return session.call(
            "wenda_news_query",
            {
                "keyword": args.get("keyword", ""),
                "date_range": args.get("date_range", "last_7_days"),
                "limit": args.get("limit", 10),
            },
            rid,
        )
    if name == "tdx_notice":
        code = args.get("code", "")
        return session.call(
            "wenda_notice_query",
            {
                "code": code,
                "setcode": _setcode(code),
                "date_range": args.get("date_range", "last_7_days"),
                "limit": args.get("limit", 10),
            },
            rid,
        )
    if name == "tdx_screener":
        return session.call(
            "tdx_screener",
            {"query": args.get("query", ""), "limit": args.get("limit", 20)},
            rid,
        )
    return {"error": "unknown: " + name}


def _resp(rid, result):
    line = json.dumps({"jsonrpc": "2.0", "id": rid, "result": result}, ensure_ascii=True)
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def _err(rid, msg):
    line = json.dumps(
        {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": msg}},
        ensure_ascii=True,
    )
    sys.stdout.buffer.write(line.encode("utf-8") + b"\n")
    sys.stdout.buffer.flush()


def main():
    for line_b in sys.stdin.buffer:
        line = line_b.decode("utf-8").strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method", "")
        rid = req.get("id")
        if method == "initialize":
            _resp(
                rid,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "tdx-live", "version": "1.0.2"},
                },
            )
        elif method == "tools/list":
            _resp(rid, {"tools": TOOLS})
        elif method == "tools/call":
            name = req["params"].get("name", "")
            args = req["params"].get("arguments", {})
            try:
                result = _exec(name, args)
                txt = []
                if isinstance(result, dict) and "content" in result:
                    for item in result["content"]:
                        txt.append(item["text"] if isinstance(item, dict) else str(item))
                else:
                    txt.append(json.dumps(result, ensure_ascii=True))
                _resp(rid, {"content": [{"type": "text", "text": "\n".join(txt)}]})
            except Exception as exc:
                _resp(rid, {"content": [{"type": "text", "text": "Error: " + str(exc)}]})
        elif rid is None:
            pass
        else:
            _err(rid, "Method not found: " + method)


if __name__ == "__main__":
    main()
