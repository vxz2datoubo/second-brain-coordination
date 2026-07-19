# Changed Files

- `modified` `F:/aidanao/core/tushare_bridge.py`: Remove hardcoded Tushare token fallback; add env/local config resolution and safe failure path.
- `modified` `F:/aidanao/core/qclaw.py`: Remove hardcoded QClaw fallback token; keep local config and env lookup; surface auth-safe failure.
- `modified` `F:/aidanao/daytrade_system/live/tdx_mcp_client.py`: Remove hardcoded TDX OAuth token; add env/local config resolution and safe failure path.
- `modified` `F:/aidanao/mcp/tdx_live_bridge.py`: Remove hardcoded TDX bridge token fallback; add env/local config resolution and import-safe main() wrapper.
- `added` `F:/aidanao/.env.example`: Safe environment template with placeholder values only.
- `added` `F:/aidanao/config/local_credentials.example.json`: Safe local credential template for non-committed machine-local use.
- `added` `F:/aidanao/tests/test_git_credential_sanitization.py`: Focused tests for missing-token failure paths and placeholder token request construction.
