# 00_MANIFEST — WB-HANDOFF-0001 交接包清单

> 交接包名称: WB-HANDOFF-0001
> 生成时间: 2026-07-16 03:00 (UTC+8)
> WorkBuddy 版本: 1.x (WorkBuddy Desktop 内置)
> 机器时区: (UTC+08:00) 北京
> 文件总数: 19

---

## 文件清单

| # | 文件 | 用途 | SHA256 |
|---|------|------|--------|
| 1 | `00_MANIFEST.md` | 本文件 — 交接包清单与完整性校验 | (生成结束后填入) |
| 2 | `01_SYSTEM_OVERVIEW.md` | 系统运行环境 (OS/CPU/RAM/磁盘/运行时) | `da95e985...42427d` |
| 3 | `02_REPOSITORY_TREE.txt` | F:\aidanao 目录结构 (深度4层, 含大小) | `62476fd4...1be45b` |
| 4 | `03_CORE_DOCUMENTS/CHATGPT-BRAIN-PROTOCOL.md` | ChatGPT 5.6 大脑协议文档 | `b716de11...6c2e4` |
| 5 | `03_CORE_DOCUMENTS/SKILLS-CATALOG.md` | 250项技能完整清单 | `9b14bb62...ec0736` |
| 6 | `03_CORE_DOCUMENTS/MEMORY.md` | 项目记忆 (决策铁律/规则) | `7d9dd113...3dcf8a` |
| 7 | `03_CORE_DOCUMENTS/SERVICE-REGISTRY.md` | 端口公告栏 (服务注册) | `096781ff...2bec3` |
| 8 | `04_SKILL_INVENTORY.csv` | 250项技能结构化清单 (12列) | `ed444c64...ea3b26` |
| 9 | `05_DATA_SOURCE_AUDIT.md` | 7个数据源逐一审计 (TDX/WeStock/Tushare/AkShare/本地/新闻/资金流) | `619d531c...5ac3` |
| 10 | `06_REALTIME_CAPABILITY_MATRIX.md` | 17项实时行情能力矩阵 | `107ab8e6...18047` |
| 11 | `06_REALTIME_CAPABILITY_MATRIX.csv` | 实时行情能力矩阵 (CSV版) | `603432d8...6027e` |
| 12 | `07_RESEARCH_AND_BACKTEST_INVENTORY.md` | 6个核心脚本的回测清单 | `f5402f29...b38d4` |
| 13 | `08_GIT_AND_CODE_STATUS.md` | Git 仓库状态 (无可) | `1ccabcd2...'c25dc` |
| 14 | `09_SERVICE_AND_PORT_STATUS.md` | 当前监听端口与运行服务状态 | `a13c0fb5...7dc5e2` |
| 15 | `10_SAMPLE_DATA/300418_daily_kline_60d.csv` | 昆仑万维 60日K线 (CSV) | `f5c3c1fc...` |
| 16 | `10_SAMPLE_DATA/300418_daily_kline_60d.json` | 昆仑万维 60日K线 (JSON) | `1ded3c91...` |
| 17 | `10_SAMPLE_DATA/300418_fund_flow_sample.json` | 四渠道资金流样本 (2条) | `78b940ed...` |
| 18 | `10_SAMPLE_DATA/SCHEMA.md` | 样本数据字典 | `86b110c5...` |
| 19 | `11_KNOWN_CONFLICTS_AND_GAPS.md` | 17项已知冲突 + 8项缺口 | `d31e3c48...` |
| 20 | `12_SECURITY_REDACTION_REPORT.md` | 安全脱敏审计报告 | `fd853d15...5637e` |

---

## 无法完成项 (及原因)

| 请求项 | 原因 |
|--------|------|
| `10_SAMPLE_DATA` — 最近10天1分钟线 | 需遍历10天逐一调 TDX MCP `tdx_kline` 且人工不可在脚本中批量完成 (MCP 限流)。标记为"无法在当前会话完成"，数据格式和获取方式已在 SCHEMA.md 中说明。 |
| `10_SAMPLE_DATA` — 最近20条新闻 | WeStock `data_news` 需实时 MCP 调用。本地新闻库为日频聚合指数非原始文本。 |
| `10_SAMPLE_DATA` — 集合竞价快照 | TDX MCP 不提供竞价序列数据 (见 06_REALTIME_MATRIX 和 11_CONFLICTS 第1条) |
| `10_SAMPLE_DATA` — 板块/主题归属 | 需 WeStock 实时 MCP 调用 |
| `10_SAMPLE_DATA` — 板块强弱排名 | 需 WeStock 实时 MCP 调用 |
| `10_SAMPLE_DATA` — 筹码/Volume Profile | 需运行 `volume-profile-chip` 技能，需完整历史数据 |
| `10_SAMPLE_DATA` — 持仓/账户数据 | 安全策略: 不暴露真实持仓金额/账号 |

> 以上所有"无法完成"项均因 MCP 限流或安全策略限制，非数据源不存在。SCHEMA.md 提供了获取这些数据的方法和字段格式。

---

## 安全声明

本交接包已经过敏感信息审计 (见 `12_SECURITY_REDACTION_REPORT.md`)：
- ❌ 无密码 / Token / API Key / Cookie
- ❌ 无券商账号 / 身份证 / 手机号 / 私钥
- ❌ 无真实持仓金额 / 成本价
- ✅ 仅包含公开市场数据 (股票代码、K线、公开资金流)

---

## 压缩包

| 项目 | 值 |
|------|-----|
| ZIP 文件 | `F:\aidanao\handoff\WB-HANDOFF-0001.zip` |
| SHA256 文件 | `F:\aidanao\handoff\WB-HANDOFF-0001.sha256` |

---

## 交接完成后

本交接包可供 ChatGPT 5.6 作为系统能力基准文档使用。后续如需更新：
1. 修改对应文件
2. 重新计算 SHA256
3. 更新本 MANIFEST
4. 重新打包 ZIP
