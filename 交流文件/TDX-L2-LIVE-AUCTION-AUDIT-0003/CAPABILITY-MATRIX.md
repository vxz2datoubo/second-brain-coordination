# CAPABILITY-MATRIX — TDX-L2-LIVE-AUCTION-AUDIT-0003

> 核心原则: **UI 能显示 ≠ API 能读取。** 每项能力按接口分别标记, 不得跨接口推断。

## 能力总表

| # | 能力 | UI (客户端) | TDX MCP | TdxQuant (tqcenter) | 本地文件 | 公式 |
|---|---|---|---|---|---|---|
| 1 | 十档盘口 | UI_VERIFIED_BY_USER | ❌ **MCP_NOT_EXPOSED** (bspNum=10仍只返5档) | NOT_TESTED_RUNTIME (subscribe_hq可能含,未执行) | NOT_AVAILABLE | N/A |
| 2 | 五档盘口 | UI_VERIFIED | ✅ MCP_VERIFIED (BspInfo 5档) | STATIC_API_PRESENT | NOT_AVAILABLE | N/A |
| 3 | 逐笔成交(原始tick) | UI_VERIFIED_BY_USER | ❌ NOT_AVAILABLE | ❌ 静态枚举未见 get_tick/transaction | ❌ 无.l2d/.tick | N/A |
| 4 | 逐笔委托(原始order/entrust) | UI_VERIFIED_BY_USER | ❌ NOT_AVAILABLE | ❌ 静态枚举未见 get_order/entrust | ❌ 无 | N/A |
| 5 | 委托队列(queue) | UI_VERIFIED_BY_USER | ❌ NOT_AVAILABLE | ❌ 静态枚举未见 get_queue | ❌ 无 | N/A |
| 6 | 集合竞价虚拟参考价 | UI_VERIFIED_BY_USER | ❌ MCP无独立字段(竞价期仅OpenStatus/HQTime) | NOT_TESTED | ❌ 无 | N/A |
| 7 | 虚拟匹配量/未匹配量 | UI_VERIFIED_BY_USER | ❌ MCP无独立字段 | NOT_TESTED | ❌ 无 | N/A |
| 8 | 总委买量/总委卖量(聚合) | UI_VERIFIED | ⚠️ **FORMULA_AGGREGATE_ONLY** (ProInfo.InOut/TotalBuyv/TotalSellv, 实时变动) | STATIC_API_PRESENT(get_market_snapshot) | ❌ 无压缩 | FORMULA_AGGREGATE_ONLY |
| 9 | 总撤买/总撤卖(聚合) | UI_VERIFIED | ⚠️ FORMULA_AGGREGATE_ONLY (ProInfo.InOutHB, 实时变动) | NOT_TESTED | ❌ 无 | FORMULA_AGGREGATE_ONLY |
| 10 | 委比 Wtb | UI_VERIFIED | ✅ MCP_VERIFIED (ProInfo.Wtb, 实时) | NOT_TESTED | ❌ | AGGREGATE |
| 11 | L2逐笔成交数(计数) | UI_VERIFIED | ❌ NOT_AVAILABLE | ❌ 未见 | ❌ 无 | N/A |
| 12 | L2逐笔委托数(计数) | UI_VERIFIED | ❌ NOT_AVAILABLE | ❌ 未见 | ❌ 无 | N/A |
| 13 | 内盘/外盘 | UI_VERIFIED | ✅ MCP_VERIFIED (Inside/Outside) | NOT_TESTED | ❌ | N/A |
| 14 | 成交量/成交额/笔数 | UI_VERIFIED | ✅ MCP_VERIFIED (Volume/Amount/CJBS) | NOT_TESTED | ❌ 压缩 | N/A |
| 15 | 开盘状态 OpenStatus | UI_VERIFIED | ✅ MCP_VERIFIED (0=盘前/3=连续) | NOT_TESTED | ❌ | N/A |
| 16 | 指数L2聚合(TotalBuyv/Sellv/CasImbVol) | UI_VERIFIED | ✅ MCP_VERIFIED (指数999999独有) | NOT_TESTED | ❌ | AGGREGATE |
| 17 | 四渠道资金流(超大/大/中/小单) | UI_VERIFIED | ❌ NOT_AVAILABLE(MCP) | ❌ 未见 | ❌ | NOT_TESTED (WeStock有wb_ratio/outer/inner代理) |
| 18 | 行情订阅推送流 | UI_VERIFIED | ❌ MCP为轮询快照(非推送) | STATIC_API_PRESENT(subscribe_hq/subscribe_quote) | ❌ | N/A |

## 关键判定(可直接引用)

### ✅ MCP 能拿到 (连续竞价已验证, 实时变动)
- 五档盘口 (买1-5/卖1-5 价量)
- 内盘/外盘、成交量/成交额/成交笔数(CJBS)、量比(LB)、换手(HSL)、均价(Average)
- OpenStatus (盘前/连续状态机)
- **L2 聚合统计**: `InOut`(总委买−总委卖量净值), `InOutHB`(撤买/撤卖聚合, 字段名待官方确认), `Wtb`(委比%), `NowVol`(最新量), `OpenAmo`(开盘额)
- 指数额外: `TotalBuyv`, `TotalSellv`, `CasImbVol`(集合竞价失衡量, 极小值浮点), `CasUpperPx`
- HQMaskFlag (L2掩码标志, 不同标的不同: 300418=11, 300058=10, 600519=7, 510300=6, 000609=1048576/0x100000)

### ❌ MCP 拿不到 (即便 bspNum=10 + hasProInfo=1)
- **十档盘口**: bspNum=10 请求, `aHasBspNum` 返回 10, 但 `BspInfo` 数组**始终只有前5档有数据, 后5档为空对象**。竞价期、撮合后、连续竞价全程如此。
- **原始逐笔成交/逐笔委托/委托队列**: MCP 无任何 tick/transaction/order/entrust/queue 字段
- **集合竞价虚拟参考价/匹配量/未匹配量**: MCP 无独立字段, 竞价期只能看到 OpenStatus 切换 + HQTime
- **四渠道资金流**(超大/大/中/小单买卖额): MCP 不提供
- **L2_AMO 等公式显式求值**: MCP 未暴露公式求值接口

### ⚠️ TdxQuant (tqcenter.py v1.0.4)
- **静态枚举确认存在**: `get_market_snapshot`, `get_market_data`, `subscribe_quote`, `subscribe_hq`, `get_subscribe_hq_stock_list`, `get_stock_info`, 板块/财务/日历等
- **静态枚举未见**: `get_tick`, `get_transaction`, `get_order`, `get_entrust`, `get_queue`, `get_auction` 等原始逐笔/委托/队列/竞价专用函数
- **下单接口存在且严禁调用**: `order_stock`, DLL `SetNewOrder`
- **运行时未执行**: 模块加载即 `ctypes.CDLL(TPythClient.dll)`+InitConnect, 实时竞价为进行的客户端上加载桥接DLL存在干扰风险 → 留作非交易时段执行
- **结论**: TdxQuant 提供**快照+订阅推送**官方只读接口, 可能通过 subscribe_hq 推送拿到比 MCP 更高频/更全的 L2 数据, 但**原始逐笔提取能力未在静态枚举中证实**, 须非交易时段运行时验证

### ❌ 本地文件 (LOCAL_FILE_VERIFIED)
- 全盘(限时)未发现 `.l2d` / `.tick` 文件 → 本配置下 TDX **不将 L2 原始逐笔/委托落地为可读取磁盘文件**
- 新增文件仅 `T0002/hq_cache/*.{tcu,tfz,th2,tnf,tdf}`(压缩行情缓存) + `datacache.json` + `CacheData2.db` + `PYPlugins/py_strategy.cfg`
- 结论: **本地文件解析在此配置下无法重建 L2 逐笔/委托/队列/竞价**

## 能力标签图例
- `UI_VERIFIED` / `UI_VERIFIED_BY_USER`: 客户端可见 (用户陈述或截图)
- `MCP_VERIFIED`: TDX MCP 接口实测可读
- `TDXQUANT_VERIFIED` / `STATIC_API_PRESENT` / `NOT_TESTED_RUNTIME`: TdxQuant
- `LOCAL_FILE_VERIFIED` / `NOT_AVAILABLE`: 本地文件
- `FORMULA_AGGREGATE_ONLY`: 仅聚合统计, 非原始逐笔
- `NOT_AVAILABLE` / `NOT_TESTED` / `UNKNOWN`
