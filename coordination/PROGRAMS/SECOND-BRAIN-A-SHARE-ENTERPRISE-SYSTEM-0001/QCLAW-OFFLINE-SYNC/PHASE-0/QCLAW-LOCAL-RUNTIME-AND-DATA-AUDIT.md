# QCLAW 本地运行时与数据审计报告

> `agent_id: WORKBUDDY` | `task: QCLAW-OFFLINE-FIRST-KNOWLEDGE-SYNC-0001-PHASE0`
> `boundary: local-read-only` | `verified: 2026-07-20T14:43:00Z`

## 审计摘要

| 维度 | 发现 |
|------|------|
| QCLAW 运行态 | ✅ 5进程活跃, ~1.12GB内存, 端口8618 |
| QCLAW 版本 | v0.2.33 (appVersion), 探测为0.2.33 |
| 主桥接层 | `core/qclaw.py` (407行), QClawBridge类 |
| MCP桥接 | `mcp/qclaw_bridge.py` (89行), 2工具 |
| 健康检查 | `/v1/models` with Bearer Token |
| 配置源 | `~/.qclaw/qclaw.json` + `openclaw.json` |
| Token解析 | env→qclaw.json→openclaw.json 三级优先链 |
| 输出目录 | `F:/aidanao/qclaw-output/` (2MB, 207文件) |
| 状态目录 | `~/.qclaw/` (8-9GB估计) |

## QCLAW 运行环境

```
PID      内存      角色
30900    363MB    QClaw主进程
33520     95MB    QClaw子进程
27436    165MB    QClaw子进程
22852    105MB    QClaw子进程
29100    396MB    QClaw子进程(最大)
─────────────────────────
总计:   ~1.12GB
```

QCLAW 桌面应用持续运行，5个进程占用约1.1GB内存。配置文件指向PID 14100但实际PID可能是30900（主进程）。通过 `/v1/models` 端点健康检查可达。

## 桥接架构

```
WorkBuddy/Codex → core/qclaw.py → QClawBridge.ask()
                                   ├── 读 ~/.qclaw/qclaw.json → port:8618
                                   ├── 读 ~/.qclaw/openclaw.json → gateway.auth.token
                                   ├── health check: GET /v1/models (Bearer)
                                   └── POST /v1/chat/completions → QCLAW LLM
                                        ↓
                                   F:/aidanao/qclaw-output/*.md
```

## 输出现状

- **207个文件**, 2MB总量, 完全扁平结构
- 主要格式: Markdown (142) > JSON (40) > CSV (17) > JSONL (4)
- **无清单**: 没有任何文件记录产出物的身份、来源、处理器版本或内容哈希
- **无隐私分级**: 不区分公开/私有/敏感内容
- **无候选包结构**: 没有 LearningPacket schema 的任何字段
- **无状态机**: 没有处理中/候选/已审核/已同步等状态标记

## 磁盘规模

| 目录 | 大小 | 风险 |
|------|------|------|
| `~/.qclaw/workspace/` | **7.1 GB** | 🔴 最大消费，40+ agent workspace子目录 |
| `~/.qclaw/skills/` | 46 MB | 🟡 技能缓存 |
| `~/.qclaw/state/` | 25 MB | 🟡 会话状态 |
| `~/.qclaw/logs/` | 348 KB | 🟢 小 |
| `F:/aidanao/data/raw/` | 153 MB | 🟡 tushare历史数据 |
| `F:/aidanao/qclaw-output/` | 2 MB | 🟢 小，但会增长 |

总计QCLAW相关磁盘占用约 **8-10 GB**，主要来源于 workspace/ 目录。

## 配置稳定性

⚠️ `~/.qclaw/` 根目录存在 **150+ 个 `openclaw.json.invalid.*.bak` 文件**，表明 QCLAW 配置写入曾反复失败/损坏。当前 `openclaw.json` 可读但存在配置腐败历史模式。

## 权限边界

- QClawBridge: 通过 HTTP 调用 localhost:8618, 无需文件系统权限
- QCLAW桌面应用: 完整用户级文件系统权限
- 输出目录: WorkBuddy/Codex 均可读写
- 状态目录: QCLAW 独有, 其他Agent只读
- Token: 通过 `QCLAW_GATEWAY_TOKEN` 环境变量或配置文件读取

## 关键回答

**QCLAW现在是否已经能稳定输出候选知识包？**
❌ 不能。输出是扁平Markdown/JSON文件，不含结构化LearningPacket所需字段。

**真实输出在哪里、格式是什么、是否混有日志或敏感数据？**
`F:/aidanao/qclaw-output/`，混合Markdown+JSON+CSV+JSONL，未与系统日志分离，未做隐私分级。

**能否在完全离线状态持续运行和保存？**
✅ 可以。QCLAW桥接只依赖localhost HTTP调用和本地文件系统，无需外部网络。

**本地应使用文件、SQLite、JSONL还是组合式候选仓？**
推荐组合：文件系统目录结构 + JSONL候选包 + SQLite状态索引。文件系统承载不可变原始工件和候选包，JSONL便于追加和流式处理，SQLite管理幂等键、游标和同步状态。

**哪些内容永不上传？**
RESTRICTED_NEVER_SYNC: 凭证、Token、浏览器会话、个人账户数据、真实交易记录。
SENSITIVE_LOCAL_ONLY: 个人笔记、私密对话总结、涉及第三方隐私的内容。
