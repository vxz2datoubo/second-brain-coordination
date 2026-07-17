# Runtime And Generated Files

## Runtime-State Areas Found

| Scope | Files | Size | Recommended treatment |
|---|---:|---:|---|
| `data/` | `332` | `209,855,220` bytes | exclude |
| `logs/` | `4` | `9,966` bytes | exclude |
| `backups/` | `19` | `13,061,314` bytes | exclude |
| `handoff/` | `48` | `516,981` bytes | exclude |
| `qclaw-output/` | `207` | `894,345` bytes | exclude |
| `chatgpt_bridge/playwright_user_data/` | `63` | `9,193,509` bytes | exclude |
| `coordination/RESULTS/FOUNDATION-DATA-GOVERNANCE-0001/` | `16` | `41,810` bytes | keep out of first baseline unless separately curated |

## Database / Audit / Session Counts

- 数据库文件：`7`
- 日志类文件（不含 `.venv`）：`35`
- `__pycache__` 目录：`590`
- Node `node_modules` 目录：`0`
- 常见模型权重文件（`.safetensors/.ckpt/.pt/.bin/.onnx/.gguf`）：`0`

## Runtime Files That Must Stay Out

1. `data/super_brain_v01.sqlite`
2. `data/audit/events.jsonl`
3. `data/wallet.json`
4. `chatgpt_bridge/playwright_state.json`
5. `chatgpt_bridge/playwright_user_data/**`
6. `second-brain/daily_log.md`
7. `server.pid`
8. 根目录运行日志和输出转储

## Generated / Cache Areas

- `__pycache__/`
- `_tmp_status_debug/`
- `codex_siliconflow_proxy/.venv/`

## Coordination Results Differentiation

`coordination/RESULTS/` 不能一刀切：

### 可以考虑长期保留并入库的内容

- 正式、脱敏、人工可审计的摘要报告
- 不含密钥、不含运行态路径、不含回滚指令的治理结论

### 不建议进入首次基线的内容

- `ROLLBACK-PACK/`
- 本地回滚脚本
- 依赖当前绝对路径和当前 SQLite 主键的回滚说明
- 任何含明文秘密的旧审计文件

## Practical Recommendation

首次 Git 基线只纳入：

- 源码
- 测试
- 正式文档
- 配置模板
- 已脱敏审计摘要

把一切运行态状态、缓存、会话、数据库、日志与回滚包留在 Git 之外。
