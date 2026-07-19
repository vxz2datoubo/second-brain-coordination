# Redaction Plan

## Scope

本轮不直接修改业务代码，只给出候选脱敏方案。

## Candidate Changes

### 1. `core/tushare_bridge.py`

Current issue:

- class constant carries a real Tushare token

Candidate fix:

1. keep `BASE_URL`, but allow `TUSHARE_PROXY_BASE_URL` override
2. replace hardcoded token with `os.environ.get("TUSHARE_TOKEN", "")`
3. if no token is available, fail with a safe runtime error
4. never print token in request error logs

### 2. `core/qclaw.py`

Current issue:

- `FALLBACK_TOKEN` is a real token

Candidate fix:

1. remove real fallback
2. prefer existing config resolution order
3. only use `QCLAW_GATEWAY_TOKEN` as a last env fallback
4. if still missing, raise a safe error instead of silently keeping a baked-in secret

### 3. `daytrade_system/live/tdx_mcp_client.py`

Current issue:

- module-level `OAUTH_TOKEN` contains a real token

Candidate fix:

1. replace with env read: `WORKBUDDY_TDX_TOKEN`
2. allow explicit constructor parameter to override env
3. fail fast if token is still empty

### 4. `mcp/tdx_live_bridge.py`

Current issue:

- `_load_token()` contains a real fallback value

Candidate fix:

1. keep local credential discovery logic
2. keep env variable support
3. remove the real fallback string entirely
4. if token remains absent, abort startup with a safe error

## Files To Exclude Instead Of Patching

这些不是“改一下再提交”，而是应该直接不进 Git：

1. `data/wallet.json`
2. `chatgpt_bridge/playwright_state.json`
3. `chatgpt_bridge/playwright_user_data/**`
4. `data/**`
5. `logs/**`

## Historical Audit File Handling

`coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md` 目前含明文值。

建议：

1. 首次基线中排除它
2. 以后若要长期保留，只保留新的脱敏版摘要
