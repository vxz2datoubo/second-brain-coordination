# TQ-LOCAL-TOOL-CATALOG — 官方 TQ-Local v1.0.12 工具目录

## 行情与基础数据
| 工具 | 用途 | L2相关字段 | 状态 |
|---|---|---|---|
| get_market_data | K线/分钟线/历史行情 | 无L2 | STATIC_DOCUMENTED |
| get_market_snapshot | 实时行情快照 | BuyP[5]+SellP[5] (五档), NowVol, Inside/Outside | **SNAPSHOT_ONLY (5档)** |
| get_more_info | 更多证券信息(含L2) | **L2TicNum, L2OrderNum, BCancel, SCancel, TotalBVol, TotalSVol, Wtb, Zjl, Zjl_HB, OpenZTBuy, OpenAmo** | STATIC_DOCUMENTED **(L2聚合)** |
| get_stock_info | 基础信息+财务 | 无L2 | STATIC_DOCUMENTED |
| get_pricevol | 价量分布 | LastClose, Now, Volume | STATIC_DOCUMENTED |

## L2 特定字段映射 (get_more_info)
| 字段 | 类型 | 说明 | 粒度 |
|---|---|---|---|
| L2TicNum | str | L2逐笔成交数 | AGGREGATE_ONLY (计数) |
| L2OrderNum | str | L2逐笔委托数 | AGGREGATE_ONLY (计数) |
| TotalBVol | str | 总买量 | AGGREGATE_ONLY |
| TotalSVol | str | 总卖量 | AGGREGATE_ONLY |
| BCancel | str | 总撤买量 | AGGREGATE_ONLY |
| SCancel | str | 总撤卖量 | AGGREGATE_ONLY |
| Wtb | str | 委比 | AGGREGATE_ONLY |
| Zjl | str | 主买净额(万元) | AGGREGATE_ONLY |
| Zjl_HB | str | 主力净流入(万元) | AGGREGATE_ONLY |
| OpenZTBuy | str | 竞价涨停买入金额(万元) | AGGREGATE_ONLY |

## 缺失的工具
- formula_get_all: **未见**
- formula_get_info: **未见**
- get_full_tick: **不存在**
- get_report_data: **不存在** (get_market_snapshot即报表)
- subscribe_hq / subscribe_quote: **在 v1.0.12 SKILL.md 中未见**(可能被 HTTP 层移除)
- Tick / 逐笔: **未见** (get_market_data period列表无'tick')
- 十档接口: **未见** (get_market_snapshot仅五档)

## 能力标签定义
- RUNTIME_VERIFIED: 运行时实测
- SNAPSHOT_ONLY: 仅快照(五档)
- AGGREGATE_ONLY: 聚合统计(非原始逐笔)
- STATIC_DOCUMENTED: 仅文档枚举(HTTP不可达)
- NOT_EXPOSED_IN_DOCS: 文档未见
- NOT_TESTED: 未测
