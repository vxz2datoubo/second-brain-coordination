# Secret Classification

## Classification Rules Used

- `confirmed_hardcoded_secret`: 当前仓库中存在真实秘密值或真实会话值
- `environment_variable_reference`: 代码只引用环境变量，不含真实值
- `local_config_reference`: 文档或代码引用本地配置位置，但不含真实值
- `placeholder_or_example`: 示例字段或占位符，不含真实值
- `test_fixture`: 仅测试样例
- `historical_or_deprecated`: 历史文档或报告中的陈旧路径 / 旧做法
- `false_positive`: 只命中了“token / secret / config”等词，但不是秘密
- `unknown_requires_user_review`: 当前无法确认归属或用途

## Classified Hits

| Path | Line / region | Credential class | Category | Risk | Suggested handling | Fingerprint |
|---|---:|---|---|---|---|---|
| `F:/aidanao/core/tushare_bridge.py` | `16` | Tushare API token | `confirmed_hardcoded_secret` | Critical | 改为 `TUSHARE_TOKEN` + 缺失检查；原文件在基线前不得直接纳入 | `sha256:8086a8ab765a` |
| `F:/aidanao/core/qclaw.py` | `26` | QClaw gateway fallback token | `confirmed_hardcoded_secret` | Critical | 去掉硬编码 fallback，改为 config / env 读取 | `sha256:f76dac51d493` |
| `F:/aidanao/daytrade_system/live/tdx_mcp_client.py` | `18` | TDX OAuth token | `confirmed_hardcoded_secret` | Critical | 改为 `WORKBUDDY_TDX_TOKEN` 或本地不入库配置 | `sha256:7bd70dd00912` |
| `F:/aidanao/mcp/tdx_live_bridge.py` | `18` | TDX token fallback | `confirmed_hardcoded_secret` | Critical | 去掉真实默认值；只允许 env / 本地配置提供 | `sha256:7bd70dd00912` |
| `F:/aidanao/data/wallet.json` | `6-19` | WorkBuddy API key | `confirmed_hardcoded_secret` | Critical | 运行态钱包文件，永久排除；迁移到外部私有凭据仓 | `sha256:94d066d90791` |
| `F:/aidanao/data/wallet.json` | `16-19` | Tushare token duplicate | `confirmed_hardcoded_secret` | Critical | 运行态钱包文件，永久排除；不要进入 Git | `sha256:8086a8ab765a` |
| `F:/aidanao/chatgpt_bridge/playwright_state.json` | `1` | Browser cookies and session material | `confirmed_hardcoded_secret` | Critical | 永久排除；禁止入库；如需保留，仅保留空模板 | `multiple fingerprints` |
| `F:/aidanao/chatgpt_bridge/playwright_user_data/Default/Network/Cookies` | whole file | Browser cookie store DB | `confirmed_hardcoded_secret` | Critical | 永久排除整个 `playwright_user_data/` 目录 | `binary store` |
| `F:/aidanao/codex_siliconflow_proxy/proxy_server.py` | `14` | `SILICONFLOW_API_KEY` env lookup | `environment_variable_reference` | Medium | 可保留；确保 `.env` / 本地配置永不入库 | `n/a` |
| `F:/aidanao/codex_siliconflow_proxy/proxy_server.py` | `16` | `CODEX_SILICONFLOW_PROXY_KEY` env lookup | `environment_variable_reference` | Medium | 可保留；确保密钥只从 env 注入 | `n/a` |
| `F:/aidanao/daytrade_system/README_EVOLUTION.md` | `111` | “token 已内置”说明 | `historical_or_deprecated` | Medium | 不视为当前秘密值，但应在后续文档治理中改写 | `n/a` |
| `F:/aidanao/bulletin/deskpet-注意事项.md` | `63` | FISH audio key path reference | `local_config_reference` | Low | 文档不含真实值；如入库可保留，但需注明是本地敏感配置位置 | `n/a` |
| `F:/aidanao/coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md` | `13-14` | Historical report leaking real token | `confirmed_hardcoded_secret` | High | 不得直接进入首次提交；如要保留，只能先生成脱敏版替代 | `sha256:8086a8ab765a` |
| `F:/aidanao/coordination/RESULTS/GIT-BASELINE-AND-FOUNDATION-AUDIT-0002/SECRET-SCAN.md` | `21-22` | Missing `codex_accounts/*` paths from old audit | `historical_or_deprecated` | Low | 当前路径已不存在；按旧审计上下文保留，但不应作为当前存在风险计入 | `n/a` |
| `F:/aidanao/mcp/qclaw_bridge.py` | current file | QClaw token mention without hardcoded value | `false_positive` | Low | 当前文件已经改为动态探测，不构成当前秘密泄露 | `n/a` |
| `F:/aidanao/core/wallet.py` | module docstring | “存储 API tokens” 文本说明 | `false_positive` | Low | 只是功能描述，不是秘密值 | `n/a` |

## Current Confirmed Secret Count

- 代码中的确认硬编码秘密：`4`
- 运行态 / 会话 / 钱包类真实秘密文件：`3`
- 历史报告中的当前可见秘密泄露源：`1`

## Important Duplicate Finding

以下两处引用的是同一个 Tushare token：

- `core/tushare_bridge.py`
- `data/wallet.json`

以及以下两处引用的是同一个 TDX token：

- `daytrade_system/live/tdx_mcp_client.py`
- `mcp/tdx_live_bridge.py`
