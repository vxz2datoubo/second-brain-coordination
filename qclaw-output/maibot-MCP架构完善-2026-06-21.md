# MaiBot MCP 架构完善 — 2026-06-21

## 执行摘要

MaiBot MCP 架构已存在（`src/mcp_module/`），模式是：bridge 脚本 → stdio JSON-RPC 2.0 → 注册到 bot_config.toml。

本次完成了三件事：
1. 把已写好的 codex_bridge.py 注册进配置（之前缺少这一步）
2. 新写 workbuddy_bridge.py（文件/脚本/Shell 执行层）
3. 新写 tdx_bridge.py（通达信本地行情数据）

## 当前 MCP 服务器全景

| # | name | bridge | 工具数 | 定位 |
|---|------|--------|--------|------|
| 1 | second-brain | brain_bridge.py | 4 (search/consult/digest/read) | 知识库 |
| 2 | qclaw-bridge | qclaw_bridge.py | 2 (ask/analyze_douyin) | 分析算力 |
| 3 | codex-bridge | codex_bridge.py | 4 (run/resume/review/doctor) | 架构审查 |
| 4 | workbuddy-bridge | workbuddy_bridge.py | 6 (read/write/list/py/sh/status) | 执行层 |
| 5 | tdx-bridge | tdx_bridge.py | 4 (realtime/kday/kmin/search) | 行情数据 |

**合计 20 个 MCP 工具，覆盖知识→分析→审查→执行→数据五层。**

## 新增文件

- `F:\ai\mcp\workbuddy_bridge.py` — 10.1KB，6工具
- `F:\ai\mcp\tdx_bridge.py` — 13.1KB，4工具，通达信二进制解析
- `F:\ai\MaiBot\config\bot_config.toml` — 修改，新增3个 server 注册

## 待办

- 通达信路径当前未自动探测到（不在标准路径），需确认实际安装位置后设置 TDX_HOME 环境变量或改代码中的候选路径
- MaiBot 需重启使新 MCP 服务器生效
- tdx_bridge 的实时行情目前是日K最新一根（不是盘中的分笔tick），盘中实时需另接腾讯API（qt.gtimg.cn）

## 设计文档产出（同批次）

- `F:/ai/qclaw-output/maibot-InnerBrainStore-数据模型设计草案-2026-06-21.md`
- `F:/ai/qclaw-output/maibot-brain_consult-决策咨询规则草案-2026-06-21.md`
