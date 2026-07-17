# RUN-RECEIPT — WORKBUDDY-TDX-L2-STRONG-MODEL-REAUDIT-0004

> 生成: 2026-07-16 ~10:10 | 模型: Hy3 最强推理配置 | 状态: **COMPLETED**

## 1. 实际使用的模型/质量配置
Hy3 推理模型（本会话最强配置）。方法: 盲审优先（先读 raw+重跑探针，后读旧报告对账）。

## 2. 任务状态
COMPLETED。旧任务目录 `TDX-L2-LIVE-AUCTION-AUDIT-0003\` 未改/未删/未移。TdxW PID 1628 全程存活。

## 3. 原始文件是否完整
**不完整**。
- tdx_mcp.jsonl 仅 rounds[3,4]（12行），**R1/R2(竞价撮合/过渡)原始载荷未落盘**，仅锚点存在。
- receive_time_ns=0（占位），receive_time_local 粒度=轮级非逐标的。
- WeStock 缺 999999 指数行。
- 无空文件/截断/重复/时间倒退。

## 4. 强模型独立确认的三个事实
1. **TDX MCP 本版本/本配置不暴露十档盘口** — bspNum=10 仍 5 档+5 空，R3/R4/R5 三轮一致（RAW_EVIDENCE_VERIFIED）。
2. **L2 聚合字段(InOut/InOutHB/Wtb/TotalBuyv/TotalSellv)经 MCP 实时可读且跨轮变动** — AGGREGATE_ONLY，非原始逐笔。
3. **TdxQuant 无法从外部 python.exe 使用** — import OK 但 InitConnect 失败(`TQ数据接口初始化失败`)，TdxW 未受损（RUNTIME_VERIFIED）。

## 5. 推翻/收窄的旧结论
- **推翻**: "DLL加载即干扰风险"→实际可安全尝试，InitConnect 失败才是真因；"InOutHB=撤单聚合"→无官方定义(unknown_vendor_semantics)；"无限流"→仅"未观察到错误"(样本不足)。
- **收窄**: "本地无L2文件"→发现 .th2(14MB)/.tcu/.tnf/PriCS.dat(802KB)/sz.tfz(实时)候选专有缓存(可能含L2,不可直接解析)；"逐笔无基础设施"→`_fast_format_tick_data` 存在但 `get_market_data(period='tick')` 被 valid_periods 验证阻断(死代码)。

## 6. 尚未验证的关键问题
- **subscribe_hq 推送是否含十档/逐笔** — 须在 TdxW 内嵌插件宿主抓回调（外部 InitConnect 失败）。
- InOut/InOutHB/NowVol/Wtb/TotalBuyv/HQMaskFlag 官方定义（unknown_vendor_semantics）。
- .th2/.tcu/.tnf/PriCS.dat/sz.tfz 内部结构（须逆向）。

## 7. 是否建议运行 TdxQuant 最小探针
**已运行（外部）→ 失败(InitConnect)**。建议: **收盘后在 TdxW 策略管理器内嵌环境**运行 subscribe_hq 探针抓回调原始参数，定论十档/逐笔可达性。此为唯一未闭合关键验证。

## 8. 是否发现值得 Codex 继续调查的本地文件
**是**。优先: `T0002/hq_cache/sz.tfz`(131KB,实时更新,最小最易逆向) → `sh.th2`/`sz.th2`(疑十档缓存) → `T0002/PriCS.dat`(802KB) → `hq_cache/shsz.tdf`。

## 9. 输出目录
`F:\aidanao\交流文件\WORKBUDDY-TDX-L2-STRONG-MODEL-REAUDIT-0004\`（13文件 + probe/ + raw/RAW-EVIDENCE-INDEX.csv）

## 10. 下一交易日是否必须补采
**是**。须 09:14:50 前启动，补 09:15-09:24 竞价逐秒轨迹 + 撮合瞬间 + subscribe_hq 内嵌验证。方案见 NEXT-TRADING-DAY-CAPTURE-PLAN.md。
