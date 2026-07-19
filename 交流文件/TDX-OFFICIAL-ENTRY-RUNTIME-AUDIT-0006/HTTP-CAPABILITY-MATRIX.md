# HTTP-CAPABILITY-MATRIX — 基于官方 TQ-Local v1.0.12 SKILL.md 静态分析

> HTTP 17709 不可达 → 全为静态枚举(SKILL.md 文档字段), 非运行时实测。标 `STATIC_DOCUMENTED`。

## 能力总表（TQ-Local v1.0.12 SKILL.md 文档字段）

| # | 能力 | TQ-Local HTTP | 判定 |
|---|---|---|---|
| 1 | 五档盘口 | get_market_snapshot: BuyP[5]+BuyV[5]+SellP[5]+SellV[5] | **STATIC_DOCUMENTED (5档)** |
| 2 | 十档盘口 | 文档仅列5档, 未提十档 | NOT_EXPOSED_IN_DOCS |
| 3 | 逐笔成交(原始) | 无 tick/transaction 数组字段 | NOT_EXPOSED_IN_DOCS |
| 4 | 逐笔委托(原始) | 无 order/entrust 数组字段 | NOT_EXPOSED_IN_DOCS |
| 5 | 委托队列 | 无 queue 字段 | NOT_EXPOSED_IN_DOCS |
| 6 | 集合竞价虚拟参考价 | 未见专字段; get_more_info 有 OpenZTBuy(竞价涨停买入额)/OpenAmo(开盘额) | AGGREGATE_ONLY |
| 7 | 匹配量/未匹配量 | 未见 | NOT_EXPOSED_IN_DOCS |
| 8 | **L2逐笔成交数** | get_more_info: **L2TicNum** | STATIC_DOCUMENTED (计数聚合) |
| 9 | **L2逐笔委托数** | get_more_info: **L2OrderNum** | STATIC_DOCUMENTED (计数聚合) |
| 10 | 总委买量/总委卖量 | get_more_info: TotalBVol / TotalSVol | STATIC_DOCUMENTED (聚合) |
| 11 | 总撤买/总撤卖 | get_more_info: **BCancel / SCancel** | STATIC_DOCUMENTED (聚合) |
| 12 | 委比 | get_more_info: Wtb | STATIC_DOCUMENTED |
| 13 | 主力净流入 | get_more_info: Zjl(主买净额) / Zjl_HB(主力净流入) | STATIC_DOCUMENTED (聚合) |
| 14 | 竞价涨停买入 | get_more_info: OpenZTBuy | STATIC_DOCUMENTED |
| 15 | 价量分布 | **get_pricevol** (新增, v1.0.12独有) | STATIC_DOCUMENTED |
| 16 | 公式查询 | **未见 formula_get_all/formula_get_info** | NOT_EXPOSED_IN_DOCS |
| 17 | Tick数据 | get_market_data period列表无'tick' | NOT_EXPOSED_IN_DOCS |
| 18 | 十档盘口 | 未出现 | NOT_EXPOSED_IN_DOCS |

## 关键判定
- TQ-Local v1.0.12 比 tqcenter.py v1.0.4 **多出大量 L2 聚合字段**(L2TicNum/L2OrderNum/BCancel/SCancel/TotalBVol/TotalSVol/OpenZTBuy/Zjl/Zjl_HB/get_pricevol)
- **但仍无十档/原始逐笔成交/原始逐笔委托/委托队列/tick period/formula_get_all**
- get_market_snapshot 明确仅 **五档** (BuyP[5]/SellP[5])
