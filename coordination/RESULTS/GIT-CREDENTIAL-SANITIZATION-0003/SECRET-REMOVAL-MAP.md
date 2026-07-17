# Secret Removal Map

| File | Removed secret type | Replacement source | Safe failure mode |
|---|---|---|---|
| `core/tushare_bridge.py` | Tushare API token | `TUSHARE_TOKEN` or `config/local_credentials.json` | Raises `RuntimeError` before API request |
| `core/qclaw.py` | QClaw gateway fallback token | `QCLAW_GATEWAY_TOKEN`, `~/.qclaw/qclaw.json`, or `~/.qclaw/openclaw.json` | Raises `QClawError(category="auth")` before request |
| `daytrade_system/live/tdx_mcp_client.py` | TDX MCP OAuth token | `WORKBUDDY_TDX_TOKEN`, WorkBuddy local credentials, or `config/local_credentials.json` | Raises `RuntimeError` before request |
| `mcp/tdx_live_bridge.py` | TDX bridge fallback token | `WORKBUDDY_TDX_TOKEN`, WorkBuddy local credentials, or `config/local_credentials.json` | Raises `RuntimeError` before MCP session init |
