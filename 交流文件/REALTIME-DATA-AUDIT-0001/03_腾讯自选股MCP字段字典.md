# 03 — WeStock(腾讯自选股) MCP 字段字典

> Source: `mcp__westock-mcp__data_quote` + `data_fund_flow` | Test: 300418 | 2026-07-16

## data_quote — 实时快照

| 字段 | 示例值 | 类型 | 含义 | vs TDX |
|------|--------|------|------|--------|
| price | 46.11 | float | 现价 | ✅ 一致 |
| prev_close | 45.93 | float | 昨收 | ✅ 一致 |
| open | 46.18 | float | 今开 | ✅ 一致 |
| high | 48.48 | float | 最高 | ✅ 一致 |
| low | 45.49 | float | 最低 | ✅ 一致 |
| volume | 915015 | int | 成交量(手) | ⚠️ TDX=915014 (差1手) |
| amount | 4286184690 | int | 成交额 | ✅ 一致 |
| change | 0.18 | float | 涨跌额 | |
| change_percent | 0.39 | float | 涨跌幅(%) | |
| turnover_rate | 7.79 | float | 换手率(%) | ⚠️ TDX=7.785 |
| volume_ratio | 0.67 | float | 量比 | |
| range_pct | 6.51 | float | 振幅(%) | |
| avg_price | 46.84 | float | 均价 | |
| outer_volume | 443860 | int | 外盘(手) | ⚠️ TDX=455350 (差2.5%) |
| inner_volume | 471154 | int | 内盘(手) | ⚠️ TDX=459665 (差2.5%) |
| wb_ratio | -66.93 | float | 委比(%) | |
| pe_ratio | -34.64 | float | PE(TTM) | |
| pe_fwd | -16.7 | float | 前瞻PE | TDX无此字段 |
| pe_lyr | -37.2 | float | 静态PE | |
| pb_ratio | 4.62 | float | PB | TDX无此字段 |
| price_ceiling | 55.12 | float | 涨停价 | ✅ 一致 |
| price_floor | 36.74 | float | 跌停价 | ✅ 一致 |
| chg_5d/10d/20d/60d/ytd | float | float | 阶段涨幅 | TDX有Zaf20/ThisYear |
| total_market_cap | 59253000000 | int | 总市值 | |
| circulating_market_cap | 54194000000 | int | 流通市值 | |
| high_52week | 72.09 | float | 52周高 | |
| low_52week | 33.43 | float | 52周低 | |

## data_fund_flow — 四渠道资金流（独家）

| 字段 | 示例值 | 含义 | TDX有此吗 |
|------|--------|------|:--:|
| JumboNetFlow | 45707302 | 特大单净流入(≥50万/笔) | ❌ |
| MainNetFlow | 28198445 | 大单净流入(10-50万/笔) | ❌ |
| MidNetFlow | 14236293 | 中单净流入 | ❌ |
| SmallNetFlow | -42434738 | 小单净流入 | ❌ |
| MainInFlow | 2101016199 | 主力买入额 | ❌ |
| MainOutFlow | 2072817754 | 主力卖出额 | ❌ |
| MainNetFlow5D | 165838468 | 5日主力净流入 | ❌ |
| MainNetFlow10D | 1715027028 | 10日主力净流入 | ❌ |
| MainNetFlow20D | 1568968107 | 20日主力净流入 | ❌ |

⚠️ **WeStock独有四渠道资金流细分**，TDX MCP完全不提供。这是当前实时资金维度的唯一来源。

## 不支持字段

| 字段 | 状态 |
|------|:--:|
| 盘口(bid/ask depth) | ❌ 快照不返回盘口 |
| 逐笔成交 | ❌ |
| 逐笔委托 | ❌ |
| exchange_time | ❌ |
| 日内分钟线 | ⚠️ data_minute (未测) |
