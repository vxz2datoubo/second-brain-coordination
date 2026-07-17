# GET-MORE-INFO-FIELD-MATRIX — v1.0.4 实测 L2 聚合字段

> 探针: probe_v2.py, 方法: tq.get_more_info(code), 时间: 2026-07-16 ~10:57

## 13 个 L2 字段 (全部在 v1.0.4 中存在)
| 字段 | 300418 昆仑 | 300058 蓝标 | 600519 茅台 | 510300 ETF | 类型 | 粒度 |
|---|---|---|---|---|---|---|
| **L2TicNum** | 121,610 | 207,262 | 20,011 | 51,183 | str/int | AGGREGATE (L2逐笔成交计数) |
| **L2OrderNum** | 215,498 | 362,490 | 50,758 | 217,612 | str/int | AGGREGATE (L2逐笔委托计数) |
| TotalBVol | 38,442 | 132,027 | 4,496 | 728,067 | str/float | AGGREGATE (总买量,单位待确认) |
| TotalSVol | 100,071 | 495,192 | 10,418 | 365,755 | str/float | AGGREGATE (总卖量) |
| **BCancel** | 274,688 | 624,139 | 13,462 | 78,460,192 | str/float | AGGREGATE (总撤买单量) |
| **SCancel** | 228,272 | 788,340 | 11,215 | 50,009,788 | str/float | AGGREGATE (总撤卖单量) |
| **Zjl** | 59,025.19 | 53,002.92 | -2,755.06 | 29,338.53 | str/float | AGGREGATE (主买净额,万元) |
| **Zjl_HB** | 29,223.02 | 19,388.62 | -5,292.43 | -58,507.74 | str/float | AGGREGATE (主力净流入,万元) |
| OpenAmo | 26,299,000 | 20,911,102 | 58,593,600 | 0 | str/float | AGGREGATE (开盘额) |
| OpenZTBuy | 200 | 300 | 1,100 | 0 | str/float | AGGREGATE (竞价涨停买入,万元) |
| Wtb | 16.50 | 28.30 | 78.57 | -36.70 | str/float | AGGREGATE (委比%) |
| FzAmo | 1,376.51 | 1,354.91 | 1,276.16 | 759.96 | str/float | AGGREGATE (分钟额?) |
| VOpenZAF | 0 | 0 | 0.07 | 0 | str/float | AGGREGATE (竞价涨幅?) |

## 全部 86 字段分类
- L2 聚合: 13个 (如上)
- 基本面/财务: CJJEPre1/3, FDEPre1/2, DynaPE, CashZJ, KfEarnMoney, IPO_Price 等 ~15个
- 行情派生: ConZAFDateNum, LastStartZT, EverZTCount, DTPrice, DTDate_Recent 等 ~10个
- 股本/标识: FreeLtgb, IsKzz, IsT0Fund, IsZCZGP, Kzz_HSCode 等 ~8个
- 其他: BetaValue, HisHigh/Low, HqDate, DYRatio, FCb, FCAmo, Fzhsl, LLPrice 等 ~40个

## 与 MCP ProInfo 对比
- MCP ProInfo.InOut ≈ Zjl? No — InOut(300418=592M) vs Zjl(59,025万元=590M) → 量级吻合但方向不完全一致
- MCP ProInfo.InOutHB 无直接对比项
- MCP Wtb vs get_more_info Wtb: 300418 46.10 vs 16.50 → **完全不同！** 可能 Wtb 定义在两条路径不一致
- get_more_info 提供了 MCP 未暴露的 13个 L2 聚合 → **这是 v1.0.4 的新发现能力**

## 结论
v1.0.4 的 get_more_info 提供丰富的 L2 聚合字段(RUNTIME_VERIFIED)。**但全部为 AGGREGATE——L2TicNum 是计数，不是逐笔数据**。要原始逐笔仍需 tick period 或 subscribe_hq 推送。
