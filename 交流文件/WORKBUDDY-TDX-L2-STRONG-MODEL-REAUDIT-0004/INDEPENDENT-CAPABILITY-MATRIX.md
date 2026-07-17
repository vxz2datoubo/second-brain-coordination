# INDEPENDENT-CAPABILITY-MATRIX — 强模型独立复验

> 标签: RAW_EVIDENCE_VERIFIED / RUNTIME_VERIFIED / UI_ONLY / AGGREGATE_ONLY / PARTIALLY_VERIFIED / NOT_SUPPORTED_BY_CURRENT_ENDPOINT / NOT_TESTED / UNKNOWN
> 盲审阶段独立形成，未沿用旧推测。

| # | 能力 | UI | TDX MCP | TdxQuant | 本地文件 | 公式 |
|---|---|---|---|---|---|---|
| 1 | 五档盘口 | UI_ONLY | RAW_EVIDENCE_VERIFIED (BspInfo 5档, R3/R4/R5) | NOT_SUPPORTED_BY_EXTERNAL (InitConnect失败) | NOT_TESTED(专有格式) | N/A |
| 2 | 十档盘口 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT (bspNum=10仍5档, R3/R4/R5三轮确认) | NOT_TESTED (subscribe_hq未运行;InitConnect阻断) | UNKNOWN(.th2疑含,未解析) | N/A |
| 3 | 委托队列 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT | NOT_SUPPORTED (静态无 get_queue) | UNKNOWN | N/A |
| 4 | 逐笔成交 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT | PARTIALLY_VERIFIED: `_fast_format_tick_data`存在但`get_market_data(period='tick')`被valid_periods验证阻断(死代码) | NOT_TESTED | N/A |
| 5 | 逐笔委托 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT | NOT_SUPPORTED (静态无 get_order/entrust) | UNKNOWN | N/A |
| 6 | 单笔撤单 | UI_ONLY | NOT_SUPPORTED (仅聚合InOutHB,非单笔) | NOT_SUPPORTED | UNKNOWN | N/A |
| 7 | 集合竞价虚拟参考价 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT (竞价期仅OpenStatus/HQTime) | NOT_TESTED | UNKNOWN | N/A |
| 8 | 匹配量 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT | NOT_TESTED | UNKNOWN | N/A |
| 9 | 未匹配量与方向 | UI_ONLY | NOT_SUPPORTED_BY_CURRENT_ENDPOINT (指数有CasImbVol但语义UNKNOWN) | NOT_TESTED | UNKNOWN | N/A |
| 10 | L2资金分类(四渠道) | UI_ONLY | NOT_SUPPORTED (MCP无超大/大/中/小单) | NOT_TESTED | UNKNOWN | NOT_TESTED (WeStock wb_ratio/outer/inner为内外盘代理,非真实四渠道) |
| 11 | 总委买/总委卖 | UI_ONLY | AGGREGATE_ONLY (InOut/TotalBuyv/TotalSellv, 实时变动 RAW_EVIDENCE_VERIFIED) | NOT_TESTED | UNKNOWN | AGGREGATE_ONLY |
| 12 | 总撤买/总撤卖 | UI_ONLY | AGGREGATE_ONLY (InOutHB 实时变动, **语义UNKNOWN**) | NOT_TESTED | UNKNOWN | AGGREGATE_ONLY |
| 13 | L2成交笔数 | UI_ONLY | NOT_SUPPORTED (CJBS为总成交笔数,非L2逐笔计数) | NOT_SUPPORTED | UNKNOWN | N/A |
| 14 | L2委托笔数 | UI_ONLY | NOT_SUPPORTED | NOT_SUPPORTED | UNKNOWN | N/A |
| 15 | 交易所时间 | UI_ONLY | RAW_EVIDENCE_VERIFIED (HQTime, 秒级) | NOT_TESTED | UNKNOWN | N/A |
| 16 | 本地接收时间 | N/A | PARTIALLY_VERIFIED (receive_time_local有, 但粒度=轮级非逐标的; receive_time_ns=0占位) | N/A | N/A | N/A |
| 17 | 交易所/本地序号 | N/A | PARTIALLY_VERIFIED (local_sequence_no有; 无交易所序号) | N/A | N/A | N/A |
| 18 | 数据订阅/轮询方式 | UI_ONLY(推送) | 轮询快照(非推送), RUNTIME_VERIFIED | subscribe_hq推送接口存在但外部不可用(NOT_SUPPORTED_BY_EXTERNAL) | N/A | N/A |

## 独立确认的三项事实（强模型）
1. **TDX MCP 在本版本/本配置下不暴露十档盘口** — bspNum=10 请求，BspInfo 始终 5 档+5 空，R3/R4/R5 三轮（竞价后/连续中段/连续10:09）一致。NOT_SUPPORTED_BY_CURRENT_ENDPOINT。
2. **L2 聚合字段(InOut/InOutHB/Wtb/TotalBuyv/TotalSellv)经 MCP 实时可读且跨轮变动** — RAW_EVIDENCE_VERIFIED（300418 InOut: R3=47.5M→R4=44.5M→R5=199.9M；InOutHB: R3=-9.6M→R4=-29.4M→R5=+65M，含正负翻转）。AGGREGATE_ONLY，非原始逐笔。
3. **TdxQuant 无法从外部 python.exe 使用** — RUNTIME_VERIFIED：import tqcenter 成功(DLL加载)，但 `get_market_snapshot` 报 `RuntimeError: TQ数据接口初始化失败`(InitConnect失败)；TdxW PID 1628 探针前后均存活(未受损)。→ 必须在 TdxW 内嵌插件宿主(策略管理器)内运行。
