# Initial Commit Summary

## Recommended First Commit Strategy

采用**严格清洁基线**：

- 先只纳入明确安全的源码、测试、正式文档和配置模板
- 把四个待脱敏源文件单独处理后再加入
- 暂不纳入运行态数据、浏览器状态、钱包文件、第三方虚拟环境、归档和大二进制

## Strict Safe Include Set

- 文件数：`60`
- 总体积：`2,628,194` bytes
- 最大文件：`brain_core/trading_domain.py` (`1,224,073` bytes)

组成：

1. 根级控制文件
2. `brain_core/` 源码
3. `apps/` 源码
4. `tests/`
5. `docs/`
6. `config/trading/*.candidate.yaml`

## Add-After-Redaction Set

- 文件数：`4`
- 总体积：`37,898` bytes

包括：

1. `core/tushare_bridge.py`
2. `core/qclaw.py`
3. `daytrade_system/live/tdx_mcp_client.py`
4. `mcp/tdx_live_bridge.py`

## Explicit Exclusion Pressure

- 当前明确排除层：`16,113` 个文件，约 `721.21 MB`

其中最重的拖累来自：

1. `data/`
2. `codex_siliconflow_proxy/.venv/`
3. `chatgpt_bridge/playwright_user_data/`
4. `backups/`
5. `qclaw-output/`

## Suspicious Or Operational Extensions In The Workspace

- 数据库：`7`
- 日志类：`35`
- `__pycache__` 目录：`590`
- 常见模型权重：`0`
- 二进制 / 压缩类文件总数：`1,098`

## Foundation Placement Recommendation

Foundation 相关的**代码、测试、文档**建议作为初始状态进入基线。  
Foundation 相关的**公告栏、SQLite、JSONL、回滚包**不应进入首次提交。

## Final Recommendation

第一次 Git 提交不要追求“把一切都收进去”。  
先把可审计、可复现、无秘密的源码基线钉住，再处理用户决定项。
