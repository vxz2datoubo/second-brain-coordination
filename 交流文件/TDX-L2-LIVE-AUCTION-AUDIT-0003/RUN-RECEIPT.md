# RUN-RECEIPT — TDX-L2-LIVE-AUCTION-AUDIT-0003

> 收据生成: 2026-07-16 09:39 (北京时间) | 任务状态: **采集中, 无阻塞**

## 启动收据 (按任务第十一节要求)

| 项 | 值 |
|---|---|
| **是否已开始采集** | ✅ 是。已采集 R1(09:25撮合点)/R2(09:26过渡)/R3(09:32连续)/R4(09:39连续) 共4轮, 6标的+指数 |
| **当前北京时间** | 2026-07-16 09:39:09 |
| **已启动数据源** | TDX MCP(tdx_quotes, bspNum=10+hasProInfo=1) + WeStock MCP(data_quote) + 本地文件只读监控 + TdxQuant静态枚举 |
| **客户端是否显示十档** | ✅ 是 (UI_VERIFIED_BY_USER, 用户陈述; 未截图以免干扰) |
| **客户端是否显示竞价虚拟价/匹配量/未匹配量** | ✅ 是 (UI_VERIFIED_BY_USER, 用户陈述) |
| **TdxQuant当前是否可用** | ⚠️ 静态可用 (tqcenter.py v1.0.4 存在, tq类含get_market_snapshot/subscribe_hq); **运行时未执行** (避免DLL干扰运行客户端, 留非交易时段) |
| **原始数据目录** | `F:\aidanao\交流文件\TDX-L2-LIVE-AUCTION-AUDIT-0003\` (raw/*.jsonl + r3/r4_full.json + 锚点) |
| **是否遇到阻塞** | ❌ 无阻塞。MCP 连续稳定无错误无限流。唯一限制: MCP 不暴露十档/逐笔(见CAPABILITY-MATRIX) |

## 核心结论速览

### ✅ MCP 能拿到 (实时变动, 连续竞价已验证)
- 五档盘口 + 内外盘 + 量价笔数 + OpenStatus + 均价/量比/换手
- **L2 聚合统计**: InOut(总委买−卖净额) / InOutHB(撤单聚合,语义待确认) / Wtb(委比) / NowVol / 指数 TotalBuyv/TotalSellv/CasImbVol

### ❌ MCP 拿不到 (即便 bspNum=10)
- **十档盘口** (definitive: bspNum=10 仍只返5档, 后5档空)
- 原始逐笔成交/逐笔委托/委托队列
- 集合竞价虚拟参考价/匹配量/未匹配量
- 四渠道真实资金流(超大/大/中/小单)
- L2_AMO 等公式显式求值

### ⚠️ 关键差距
- **UI 能显示十档/逐笔/虚拟价, 但 MCP 全部读不到** → 严禁据 UI 推断 API。
- **本地无 .l2d/.tick 文件** → 本地文件解析无法重建 L2 逐笔。
- **TdxQuant subscribe_hq 推送内容未知** → 非交易时段验证后才能定论能否拿十档/逐笔。

## 交付文件清单
- ENVIRONMENT.md — 客户端环境 + 现场保护确认
- CAPABILITY-MATRIX.md — 18项能力 × 5接口 矩阵 (核心)
- AUCTION-FINDINGS.md — A/B/C 竞价阶段发现
- CONTINUOUS-AUCTION-FINDINGS.md — D/E 过渡+连续发现
- LIVE-TIMELINE.md — 时间线
- RISKS-AND-UNKNOWN.md — 6风险 + 6未知 + 下一步
- RUN-RECEIPT.md — 本收据
- raw/ — 原始数据 (tdx_mcp 12行 / westock 10行 / tdxquant / formula / file_changes + r3/r4_full.json)

## 下一步
1. 10:00 前可继续追加轮次到 raw jsonl (框架已就绪)
2. 收盘后执行 TdxQuant 运行时验证 (subscribe_hq 推送抓取)
3. 若仍无逐笔 → 评估 eltdx / TdxQuant 量化版客户端
