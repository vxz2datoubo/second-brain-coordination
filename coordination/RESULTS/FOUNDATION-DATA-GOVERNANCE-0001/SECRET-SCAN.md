# SECRET SCAN

## Scope

This scan was aimed at Git-baseline safety, not runtime remediation.

Search pattern families included:

- `api_key`
- `token`
- `secret`
- `authorization`
- `bearer`
- `password`
- `cookie`

## Confirmed Secret / Credential Risks

1. `F:/aidanao/core/tushare_bridge.py:16`
   - hardcoded Tushare token present in source
   - Git baseline status: **blocker unless sanitized or excluded**

2. `F:/aidanao/core/qclaw.py:26`
   - hardcoded fallback token present in source
   - Git baseline status: **blocker unless sanitized or excluded**

3. `F:/aidanao/daytrade_system/live/tdx_mcp_client.py:18`
   - hardcoded TDX OAuth token present in source
   - Git baseline status: **blocker unless sanitized or excluded**

4. `F:/aidanao/mcp/tdx_live_bridge.py:18`
   - environment lookup falls back to a hardcoded token string
   - Git baseline status: **blocker unless sanitized or excluded**

## Security-Relevant Documentation Mentions

These are not themselves plaintext credential payloads, but they indicate areas that should be reviewed before broad Git inclusion:

1. `F:/aidanao/daytrade_system/README_EVOLUTION.md:111`
2. `F:/aidanao/bulletin/deskpet-注意事项.md:63`
3. `F:/aidanao/handoff/WB-HANDOFF-0001/12_SECURITY_REDACTION_REPORT.md`

## Non-Issues Observed

- no repo-owned `.env` files were found
- the `.pem` files found were vendor certificate files under `.venv`
- many `token` hits were documentation or tokenizer code, not secrets

## Recommendation

Before `git init`, choose one of these:

1. sanitize the secret-bearing files and commit the sanitized versions
2. exclude those files from the first baseline commit
3. move credentials to environment-only loaders and provide `.env.example` or config templates separately
