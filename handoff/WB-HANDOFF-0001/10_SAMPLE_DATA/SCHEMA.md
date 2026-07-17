# 10_SAMPLE_DATA — 300418 昆仑万维样本数据 SCHEMA

> 数据来源: 本地 JSON K线 + WeStock MCP (资金流)
> 复权方式: 不复权 (原始价格)
> 时区: UTC+8 (北京时间)
> 单位: 价格=元, 成交量=手, 成交额=元

## 文件清单

### 300418_daily_kline_60d.csv / .json
**K线日频数据 — 最近60个交易日**

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| date | string | YYYY-MM-DD | 交易日 |
| open | float | 元 | 开盘价 |
| high | float | 元 | 最高价 |
| low | float | 元 | 最低价 |
| close | float | 元 | 收盘价 |
| volume | float | 手 | 成交量 |
| amount | float | 元 | 成交额 |

时间范围: 2026-04-16 至 2026-07-14 (60个交易日)
复权: 不复权
来源: `data/news_db/staging/_raw/kline_300418.json`

### 300418_fund_flow_sample.json
**四渠道资金流样本**

| 字段 | 类型 | 单位 | 说明 |
|------|------|------|------|
| date | string | YYYY-MM-DD | 交易日 |
| code | string | — | 股票代码 |
| name | string | — | 股票名称 |
| super_large_net | int | 元 | 特大单净流入 (≥50万/笔) |
| large_net | int | 元 | 大单净流入 (10-50万/笔) |
| medium_net | int | 元 | 中单净流入 |
| small_net | int | 元 | 小单净流入 |
| total_net | int | 元 | 当日净流入合计 |

数据包含:
- 1 条完整日数据 (2026-07-10, WeStock `data_fund_flow` 真实数据)
- 1 条盘中快照示例 (14:30 切片)

## 缺失项说明

以下数据当前无法生成，标记为"无法完成"：

| 请求项 | 状态 | 原因 |
|--------|:--:|------|
| 最近10天1分钟线 | ❌ | TDX MCP 分钟线需指定日期范围且需遍历10天；暂未调用 (时间限制) |
| 最近20条新闻 | ❌ | WeStock `data_news` 需要实时MCP调用；本地新闻库为日频聚合，非原始新闻文本 |
| 集合竞价快照 | ❌ | TDX MCP 不提供竞价序列数据 (见 06_REALTIME_MATRIX) |
| 板块和主题归属 | ❌ | WeStock 板块归属需实时MCP调用 |
| 最近板块强弱排名 | ❌ | WeStock `data_sector` 需实时MCP调用 |
| 筹码/Volume Profile | ❌ | 需 `volume-profile-chip` 技能运行，需完整历史数据 |
| 持仓/账户数据 | ❌ | 不包含真实持仓金额/账号 (安全策略) |

这些项标记为"无法完成"并列出原因，符合交接协议。
