# RUN-RECEIPT — REALTIME-DATA-AUDIT-0001 (FINAL)

【任务ID】REALTIME-DATA-AUDIT-0001
【状态】SUCCESS_WITH_FINDINGS
【测试标的】300418/000001/600519 ✅
【接口覆盖】TDX MCP / WeStock MCP / TDX 本地文件

【核心发现（更新）】
1. ✅ TDX MCP 5档盘口+涨停价+内外盘+PE/PB — 字段最全的快照主源
2. ✅ WeStock MCP 四渠道资金流 — 唯一实时资金细分源
3. ✅ TDX 客户端已重启 (`F:\tongdaxin\` PID 2416)，本地 `.day`/`.lc1` 文件格式已确认 (32B/record OHLCVA)
4. ⚠️ 内外盘跨源差异 2.5% — TDX vs WeStock 判定标准不同
5. ❌ L2 逐笔成交/逐笔委托/集合竞价流 — 两个 MCP 都不提供
6. ❌ TdxQuant 未安装 — PYPlugins 缺少 tqcenter 模块
7. ⚠️ 市场休市 — 实时延迟/推送/盘口连续性待开盘重测

【L2相关】`l2plugin.cfg` 存在（可能已开通L2权限），但 `.l2d` 逐笔文件未找到
【内外盘差异】TDX=459665 vs WeStock=471154 (内盘), TDX=455350 vs WeStock=443860 (外盘)

【建议转发ChatGPT】是 — 涉及架构决策(统一Adapter)、L2数据缺口和跨源数据质量问题
【产物路径】F:\aidanao\交流文件\REALTIME-DATA-AUDIT-0001\
【文件数】9 个（含补充发现）
【是否修改了任何现有文件】否
