# 06_REALTIME_CAPABILITY_MATRIX — 实时行情能力矩阵

> 生成时间: 2026-07-16 02:45 (UTC+8)
> 时区: UTC+8

## 核心能力覆盖

| capability | TDX MCP | WeStock MCP | Tushare MCP | Local (scripts) | currently_available | data_level | latency | limitations |
|---|---|---|---|---|---|---|---|---|
| 实时行情 (最新价/涨跌/成交量) | ✅ tdx_quotes | ✅ data_quote | ❌ T+1 only | ❌ | ✅ YES | L1 | <500ms TDX; ~1s WeStock | TDX 需客户端运行 |
| 买卖五档/十档盘口 | ✅ tdx_quotes(bspNum=10) | ⚠️ 有限 | ❌ | ❌ | ✅ 10档 (TDX) | L2-Snapshot | <500ms | 不是逐笔更新，是快照 |
| 十档以上深度 | ❌ | ❌ | ❌ | ❌ | ❌ NO | L3 | N/A | 需要交易所直连 |
| 集合竞价虚拟匹配价 | ⚠️ 开盘后可查 | ❌ | ❌ | ❌ | ⚠️ 部分 | L1-equiv | 实时(客户端) | 需通过通达信客户端"超级盘口"查看；API暂不支持实时推送竞价序列 |
| 集合竞价匹配量 | ⚠️ 同上 | ❌ | ❌ | ❌ | ⚠️ 部分 | L1-equiv | 实时(客户端) | 同上 |
| 集合竞价未匹配量 | ⚠️ 同上 | ❌ | ❌ | ❌ | ⚠️ 部分 | L1-equiv | 实时(客户端) | 同上 |
| 集合竞价完整委托流(9:15-9:25每笔增删改) | ❌ | ❌ | ❌ | ❌ | ❌ NO | L2 | N/A | 仅机构级(交易所VDE接口)才有；个人投资者不可达 |
| **逐笔成交 (Tick-by-Tick Trade)** | ❌ | ❌ | ❌(仅期货/期权) | ❌ | ❌ NO | L2 | N/A | **当前最大缺口**。TdxQuant官方API(period='tick')可提供历史tick；eltdx协议库(trades.today())可提供当日tick |
| **逐笔委托 (Tick-by-Tick Order)** | ❌ | ❌ | ❌ | ❌ | ❌ NO | L2 | N/A | 同上。TdxQuant支持。 |
| 订单ID (Order ID) | ❌ | ❌ | ❌ | ❌ | ❌ NO | L3 | N/A | 交易所层面才有，个人不可达 |
| 撤单事件 | ❌ | ❌ | ❌ | ❌ | ❌ NO | L2 | N/A | 需L2逐笔委托；TdxQuant可能提供 |
| DDX (大单动向) | ❌ TDX MCP直接字段 | ⚠️ data_technical可能提供 | ✅ moneyflow历史 | ❌ | ⚠️ 间接 | L1+ | TDX快照可间接计算; WeStock technical指标有DDX | TDX MCP的tdx_quotes不直接返回DDX字段 |
| 四渠道资金 (特大/大/中/小单) | ❌ | ✅ data_fund_flow | ✅ moneyflow(T+1) | ✅ fund_pool_fifo.py | ✅ YES (WeStock实时+Tushare历史) | L1+ | WeStock当日实时 | 主力资金数据中，中单/小单渠道包含拆单行为，非100%纯净 |
| 分钟K线 (1min/5min/...) | ✅ tdx_kline | ✅ data_minute | ✅ stk_mins | ✅ 本地JSON缓存 | ✅ YES | L1 | <1s (TDX实时) | 数据源间字段和对齐方式有差异 |
| 板块实时行情 | ❌ | ✅ data_sector | ❌(历史板块) | ❌ | ✅ YES (WeStock) | L1 | ~1s | 仅WeStock支持板块实时排行 |
| 龙虎榜实时 | ❌ | ✅ data_lhb(T+1) | ✅ top_list | ❌ | ✅ YES (T+1) | L1 | T+1日公布 | 盘中不可用 |
| 融资融券实时 | ❌ | ✅ data_fund_margin | ✅ margin(T+1) | ❌ | ✅ YES (T+1) | L1 | T+1日 | 盘中不可用 |
| 北向资金实时 | ❌ | ✅ data_north_holding | ✅ moneyflow_hsgt | ❌ | ✅ YES (日频) | L1 | 日频 | 盘中实时净流向不可达 |
| ETF实时IOPV | ❌ | ❌ | ✅ rt_etf_sz_iopv | ❌ | ✅ YES(Tushare) | L1 | 实时 | 仅深交所ETF |

## 数据层级说明

| Level | 说明 | 代表性数据 |
|-------|------|-----------|
| L0 | 原始交易所数据 | 逐笔成交/委托、订单ID |
| L1 | 标准行情 | K线、实时快照、成交汇总 |
| L2 | 增强行情 | 逐笔成交、十档盘口、逐笔委托 |
| L3 | 全深度/全委托 | 全档深度、完整订单簿快照 |

## 关键结论

1. **当前最大缺口**：L2 逐笔成交和逐笔委托均不可达。这是 TdxQuant Python API (`period='tick'`) 和 eltdx 协议库的重点攻关方向。
2. **竞价委托流**：仅能做时点快照差分（TDX客户端"超级盘口"功能手动查看），无法自动化获取完整增删改事件流。
3. **四渠道资金**：WeStock 提供当日实时资金流向（特大单/大单/中单/小单），是当前最强的实时资金数据维度。
4. **板块实时**：WeStock 独有，TDX 不支持。
5. **DDX**：没有直接字段，需要从TDX快照的买盘/卖盘数据间接计算，或使用WeStock的technical指标。
