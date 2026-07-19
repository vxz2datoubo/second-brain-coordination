# 05_DATA_SOURCE_AUDIT — 数据源审计

> 生成时间: 2026-07-16 02:45 (UTC+8)
> 审计方式: 查询各 MCP 工具的实际 schema + 历史使用经验

---

## 1. TDX MCP (tdx-connector + tdx-live)

### 实际可调用函数
| 函数 | 说明 | 经测试可用 |
|------|------|:--:|
| `tdx_quotes` | 实时行情快照 (含 10档盘口+PE/PB/市值) | ✅ |
| `tdx_kline` | 历史K线 (日/分钟) | ✅ |
| `tdx_lookup_stock` | 代码/名称模糊查询 | ✅ |
| `tdx_screener` | 条件选股 | ✅ |
| `tdx_indicator_select` | 多股指标对比 | ✅ |
| `tdx_security_deep_info` | 深度资料 (F10) | ✅ |
| `tdx_ai_listening` | AI 资讯聚合 | ✅ |
| `tdx_futures_quotes` | 期货实时行情 | ⚠️ |
| `tdx_futures_deep_info` | 期货深度资料 | ⚠️ |
| `tdx_option_t_quote` | 期权行情 | ⚠️ |

### 数据覆盖
| 维度 | 详情 |
|------|------|
| 支持字段 | 最新价/今开/最高/最低/涨跌幅/成交量/成交额/换手率/量比/振幅/委比/内外盘 + 盘口10档 + PE(TTM)/PB/ROE/总市值/流通市值 |
| 数据粒度 | 快照 (实时) / K线: 1min/5min/15min/30min/60min/day/week/month |
| 历史起始 | 取决于 TDX 客户端本地数据 (通常 5-10年) |
| 更新时间 | 实时 (3-6秒快照刷新) |
| 延迟 | **亚秒级** (<500ms 端到端) |
| 证券覆盖 | A股(沪深京全市场) + 港股 + 指数 + 板块 |
| 退市股 | ⚠️ 取决于客户端本地数据库 |
| Point-in-Time | ❌ 快照 + K线，无 PIT 标记 |
| 本地持久化 | ❌ (仅客户端缓存，不通过 MCP 提供) |
| DDX/四渠道资金 | ❌ TDX MCP 不直接提供 DDX 字段或四渠道分类 |

### 已知字段缺失
- 无 DDX/DDY/DDZ 指标字段 (需从盘口数据间接计算)
- 无四渠道资金流向 (WeStock 独有)
- 无 L2 逐笔成交 / 逐笔委托

### 失败重试
- 单次查询超时约 10s
- 无内置重试，调用方需自行处理

---

## 2. WeStock MCP (westock-mcp)

### 实际可调用函数 (核心)
| 函数 | 说明 | 经测试可用 |
|------|------|:--:|
| `data_quote` | 实时行情快照 | ✅ |
| `data_kline` | K线数据 (日/周/月/分钟) | ✅ |
| `data_minute` | 分钟线 (分时) | ✅ |
| `data_fund_flow` | **四渠道资金流向** (特大/大/中/小) | ✅ |
| `data_sector` | 板块排行/行情 | ✅ |
| `data_news` | 个股新闻 | ✅ |
| `data_hot` | 全市场热新闻 | ✅ |
| `data_events` | 事件日历 (42类) | ✅ |
| `data_calendar` | 投资日历 (日期列表) | ✅ |
| `data_finance` | 财务报表 | ✅ |
| `data_profile` | 公司概况 | ✅ |
| `data_consensus` | 一致预期 | ✅ |
| `data_rating` | 机构评级 | ✅ |
| `data_report` | 研报 | ✅ |
| `data_chip` | 筹码分布 | ✅ |
| `data_shareholder` | 股东数据 | ✅ |
| `data_fund_margin` | 融资融券 | ✅ |
| `data_lhb` | 龙虎榜 | ✅ |
| `data_technical` | 技术指标 (含 DDX) | ✅ |
| `tool_ranking` | 板块/策略排行 | ✅ |
| `tool_filter` | 条件选股 | ✅ |
| `tool_event` | 事件名称获取 | ✅ |
| `portfolio_watchlist` | 自选股管理 | ✅ |

### 数据覆盖
| 维度 | 详情 |
|------|------|
| 支持字段 | 行情/K线/资金流/财务/新闻/事件/筹码/股东/融资/龙虎榜/技术指标/板块 |
| 数据粒度 | 快照 + K线(日/周/月/分钟) + 资金流(日频) |
| 历史起始 | 各维度不同 (K线: 上市至今, 资金流: ~3-5年) |
| 更新时间 | 实时 (行情/资金流当日) / T+1 (龙虎榜/两融) |
| 延迟 | **~1秒** (行情), ~秒级 (资金流), T+1 (龙虎榜/两融) |
| 证券覆盖 | A股(全市场) + 港股 + 美股 + 指数 + 板块 + ETF |
| 退市股 | ⚠️ 不确定 |
| Point-in-Time | ❌ 无 PIT 标记 |
| 本地持久化 | ❌ (仅通过 MCP 返回，不自动落盘) |

### 已知字段缺失 vs TDX
- 无10档深度盘口 (WeStock 盘口档数较少)
- 无专业信息 (内盘/外盘/委比/委差)

### 失败重试
- 超时约 15-30s
- 某些工具可能返回空结果 (非报错)

---

## 3. Tushare MCP (tushare)

### 实际可调用函数 (核心可用)
| 函数 | 说明 | 经测试可用 |
|------|------|:--:|
| `daily` | 日线行情 | ✅ |
| `daily_basic` | 每日指标 | ✅ |
| `moneyflow` | **个股资金流向 (T+1)** | ✅ (7/14 = 2.82亿净流出) |
| `stock_basic` | 股票列表 | ✅ |
| `trade_cal` | 交易日历 | ✅ |
| `stk_limit` | 涨跌停价格 | ✅ |
| `margin` | 融资融券 | ✅ |
| `top_list` | 龙虎榜 | ✅ |
| `income` / `balancesheet` / `cashflow` | 三大报表 | ✅ |
| `fina_indicator` | 财务指标 | ✅ |
| `forecast` | 业绩预告 | ✅ |
| `stk_holdernumber` | 股东人数 | ✅ |
| `stk_mins` | 分钟K线 | ✅ (历史, 需指定起止时间) |
| `ft_tick` | Tick数据 | ❌ **仅期货/期权，不包含A股股票** |
| `moneyflow_ths` | 同花顺资金流向 | ⚠️ |
| `cyq_chips` | 筹码分布 | ⚠️ |

### 关键限制
- **没有 A 股逐笔成交 (tick)** — `ft_tick` 只支持期货和期权
- 资金流数据: T+1 更新，**不支持当日实时**
- 历史 tick 仅期货/期权

### 数据覆盖
| 维度 | 详情 |
|------|------|
| 支持字段 | 日K/分钟K/财务/资金流(T+1)/融资/龙虎榜/股东/筹码 |
| 数据粒度 | 日频(主力), 分钟(可查历史), tick(仅期货/期权) |
| 历史起始 | ~1990年至今 (上市数据完备) |
| 更新时间 | T+1 (盘后), 分钟线支持历史指定 |
| 证券覆盖 | A股(全市场) + 期货 + 期权 + 指数 |
| 本地持久化 | ❌ |
| 权限 | 本地 bridge 有 moneyflow 历史权限; MCP 通道部分接口需积分 |

---

## 4. AkShare (本地库)

### 实际可调用
- 通过 `akshare-stock` 技能调用
- `pip list` 确认版本: **akshare 1.18.64**

### 数据覆盖
| 维度 | 详情 |
|------|------|
| 支持字段 | 行情/财务/板块 (Web 抓取, 接口稳定性取决于上游网站) |
| 数据粒度 | 日频为主 |
| 本地持久化 | ❌ |
| 优势 | 免费, 无需账号, 覆盖广 |
| 限制 | 实时性差, 依赖上游网站稳定, 非官方接口 |

---

## 5. 本地历史数据

### 已存储的数据
| 数据集 | 位置 | 说明 |
|--------|------|------|
| 新闻数据库 | `data/news_db/` | SQLite (news_archive.db): 769篇新闻, 22维日频指数 |
| 新闻指数 CSV | `data/news_index/exports/` | 300418 & 300058 各一年 (2025-07-15 → 2026-07-15) |
| 回测数据 | `data/news_index/backtest/` | IC/分位/策略 CSV + REPORT.md + DECAY_VALIDATION.md |
| K线 JSON | `data/news_db/staging/_raw/` | kline_300418.json, kline_300058.json |
| 筹码消化 | `data/chip_digestion/` | daily_turnover_log.csv |
| 预警数据 | `alerts/` | pending.json + history.json |
| 统一数据 | `data/unified/snapshots/` | hot_news, sector_ranking |

---

## 6. 新闻数据库 (news_db)

| 维度 | 详情 |
|------|------|
| 存储引擎 | SQLite (FTS5 全文搜索) |
| 已入库 | 769 篇 (从原始117篇扩展) |
| 覆盖标的 | 300418 (昆仑万维) + 300058 (蓝色光标) |
| 时间范围 | 2025-07-15 至 2026-07-15 (365天) |
| 输出格式 | 22维日频指数 (composite_index, mean_sentiment, article_impact 等) |
| 更新方式 | AI 拉取 (WeStock MCP) → 落盘 staging/_raw/ → synthesize_staging.py 入库 |
| 已知限制 | 新闻来源 ≠ 官方数据库, sentiment 为 NLP 模型输出 (非标), 日频聚合可能丢失日内事件时序 |

---

## 7. 资金流数据库

| 维度 | 详情 |
|------|------|
| 实时来源 | WeStock `data_fund_flow` (当日, 四渠道) |
| 历史来源 | Tushare `moneyflow` (T+1, 日频) |
| 本地引擎 | `core/fund_pool_fifo.py` — FIFO 资金池多头寸追踪 |
| 已知口径差异 | WeStock 与 Tushare 在"大单"定义上可能存在差异 (WeStock: 10-50万 vs Tushare: 可能不同阈值) |
| 中单/小单 | 包含机构拆单 + 量化拆分, 非100%散户纯净 |
