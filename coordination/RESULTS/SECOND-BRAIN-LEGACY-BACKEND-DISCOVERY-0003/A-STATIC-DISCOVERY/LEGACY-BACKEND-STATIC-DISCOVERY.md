# 第二大脑旧后端静态线索发现

- `agent_id`: `CODEX`
- `task_id`: `SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003A`
- `parent_issue`: `#22`
- `child_issue`: `#24`
- `mode`: `goal`
- `execution_profile`: `read-only / research_only / NO_TRADE`
- `evidence_cutoff`: `2026-07-20`

## 结论摘要

静态证据最高置信度地指向一个旧第二大脑 HTTP 服务：`http://localhost:8766`，实现文件为 `F:/aidanao/server.py`。该服务源码使用 Python 标准库 `HTTPServer`，启动时声明端口 `8766`，源码绑定为 `0.0.0.0`，并以 `data/` 为主要数据根目录。多个 MCP 和客户端桥接文件将其配置为 `localhost:8766`。

还发现两个不同的 8767 服务声明：`deep_server.py` 的深度第二大脑 HTTP 服务，以及 `mcp/brain_server.py` 的旧 HTTP 知识桥。两者共享端口号但具有不同绑定和职责，属于**静态冲突线索**，不能据此判断任何一个当前可运行。另有一个 stdio MCP 桥和一个 8799 ChatGPT 本地桥，二者均是适配层而不是已证实的母系统后端。

本阶段没有检查端口、进程、运行状态、HTTP 响应、服务健康度或数据内容。所有候选均需要阶段 B 的 WorkBuddy 现场只读核验。

## 扫描边界

### 已读取范围

- `F:/aidanao/server.py`、`deep_server.py`；
- `F:/aidanao/mcp/`、`chatgpt_bridge/`、`core/`、`brain_core/` 中与服务、MCP、URL、数据存储直接相关的源码；
- `F:/aidanao/docs/`、`bulletin/`、`SYSTEM_MANUAL.md`、`README.md` 的相关静态说明；
- `.py`、`.md`、`.bat`、`.cmd`、`.ps1`、`.json`、`.yaml`、`.yml`、`.toml`、`.ini`、`.cfg` 中的地址、协议、框架和端口声明。

### 明确未做

- 未读取 `.env`、浏览器会话、凭证库或任何真实秘密值；
- 未检查 `netstat`、监听端口、进程、计划任务或服务状态；
- 未请求 `/health`、`/docs`、`/openapi.json` 或任意候选地址；
- 未启动、停止、重启、安装或修改任何服务；
- 未读取或修改交易、券商、账户或运行态数据库数据。

## 静态证据链

| Candidate | 地址或传输 | 直接证据 | 静态判断 | 证据等级 |
|---|---|---|---|---|
| `SB-HTTP-8766` | `http://localhost:8766` | `server.py:2, 52-75, 1736-1739`; `bulletin/SERVICE-REGISTRY.md:18,29-41`; `mcp/brain_bridge.py:36` | 主旧第二大脑 HTTP 后端候选 | `VERIFIED_FACT` |
| `SB-DEEP-HTTP-8767` | `http://localhost:8767` | `deep_server.py:2-11,405-408` | 独立深度服务候选 | `VERIFIED_FACT` |
| `SB-LEGACY-HTTP-MCP-8767` | `http://127.0.0.1:8767` | `mcp/brain_server.py:1-10,147-149` | 旧 HTTP 知识桥候选；与前项端口冲突 | `VERIFIED_FACT` |
| `SB-MCP-STDIO` | JSON-RPC over stdio | `mcp/brain_bridge.py:1-36,1127-1172` | 面向母系统的 MCP 适配层；下游配置为 8766 | `VERIFIED_FACT` |
| `SB-CHATGPT-BRIDGE-8799` | `http://127.0.0.1:8799` | `chatgpt_bridge/bridge.py:1-25,139-141`; `docs/chatgpt_bidirectional_integration_plan.md:18-25,80-88` | ChatGPT 本地桥，依赖 8766，不是系统记录后端 | `VERIFIED_FACT` |

### 关键证据文件哈希

| 文件 | SHA256 |
|---|---|
| `F:/aidanao/server.py` | `003e39808f51d89e3093f2901b69b4d12001d194a4926d53a0ace564a321aee7` |
| `F:/aidanao/deep_server.py` | `4c4683dff4e57dcfebdca6f9994284ce3878771ca852e701573c69975539e880` |
| `F:/aidanao/mcp/brain_server.py` | `6c293fa66a5c1d06b3e0002578cb3530a87f4c9164283dcf7c37047bd67a04e0` |
| `F:/aidanao/mcp/brain_bridge.py` | `08cc7345216ea1f4bd868b722ec0753efe7a9e7700926284ad2986c58a1610a1` |
| `F:/aidanao/chatgpt_bridge/bridge.py` | `b30bed05a32703b21810939b2fe481f22417e22efc1a25217176a28fe0457bc2` |
| `F:/aidanao/brain_core/storage.py` | `a1cfda776c592a99c99db21c814f8a316e60f8107047a9a7e1b0e73d3c628383` |

## 存储线索

| 候选 | 静态数据位置线索 | 结论边界 |
|---|---|---|
| `SB-HTTP-8766` | `server.py:67-81` 指向 `ROOT/data`；`brain_core/storage.py:118-120` 声明 `data/super_brain_v01.sqlite` 与 `data/audit/events.jsonl` | 文件/路径声明已证实；未读取实际记录、完整性或权威性 |
| `SB-LEGACY-HTTP-MCP-8767` | `mcp/brain_server.py:8-10` 指向 `F:/aidanao/second-brain` 与 `core/logs` | 旧文档知识桥线索；未读取内容或运行日志 |
| `SB-MCP-STDIO` | `mcp/brain_bridge.py:198` 有本地 `SuperBrainV01(PROJECT_ROOT)` 回退线索 | 回退路径存在；未执行握手或工具调用 |

## 历史路径与端口线索处理

- `bulletin/maibot-v2-improvement-board.md:46` 与 `core/qclaw.py` 中存在 `F:/ai` 加 `localhost:8766` 的历史描述；它与当前 `F:/aidanao/server.py` 线索不一致，记录为**历史路径漂移**，不得视为当前部署事实。
- 8000/8001 在 `bulletin/SERVICE-REGISTRY.md:15-16,44` 被标为 MaiBot 相关服务，不纳入第二大脑后端候选。
- 用户记忆端口 `180` 和 `749` 未在本次受限静态服务声明扫描中发现可归因于第二大脑后端的地址或启动入口。普通数值出现不构成端口证据。
- `mcp/core/__init__.py:3,18` 声明 `localhost:6220/v1` 为 QClaw OpenAI 兼容网关；它是外部分析依赖线索，不是旧第二大脑后端，故未纳入候选端点表。

## 给阶段 B 的最小核验清单

1. 仅检查本报告 `CANDIDATE-ENDPOINTS.yaml` 中的候选；不要广泛扫描其他端口。
2. 优先区分 8766 主服务与两个 8767 冲突声明的实际监听者、进程、工作目录和安全健康响应。
3. 对 `SB-MCP-STDIO` 只做协议握手和工具清单验证；不得调用写入或交易相关工具。
4. 对历史 `F:/ai` 路径先做存在性与所有权核验，再决定是否形成独立候选。

## 可复现的只读命令类别

```text
rg -n -i '<address and protocol patterns>' server.py deep_server.py mcp chatgpt_bridge core brain_core docs bulletin SYSTEM_MANUAL.md README.md
rg -n -i '<framework and service patterns>' server.py deep_server.py mcp chatgpt_bridge core brain_core docs bulletin SYSTEM_MANUAL.md README.md
Get-Content <selected source and documentation files>
Get-FileHash -Algorithm SHA256 <selected evidence files>
```

上述命令均为静态文件读取；本阶段未执行网络、端口或进程命令。
