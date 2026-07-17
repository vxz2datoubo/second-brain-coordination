# OLD-VS-NEW-CONCLUSION-DIFF — 新旧结论对账

> 旧=0003报告；新=0004独立复验。标签: CONFIRMED / CONFIRMED_WITH_NARROWER_SCOPE / OVERSTATED / UNDERSTATED / UNSUPPORTED / CONTRADICTED / REQUIRES_MORE_DATA

| # | 旧结论 | 新结论 | 标签 | 依据 |
|---|---|---|---|---|
| 1 | TDX MCP 只能提供五档 | 三轮(R3/R4/R5)bspNum=10仍5档+5空，一致 | **CONFIRMED** | raw证据 |
| 2 | TdxQuant 运行时未执行(DLL干扰风险) | 已执行:import OK,InitConnect失败,TdxW未受损;风险判断过虑 | **CONTRADICTED** | probe_result.json |
| 3 | 能否获得十档: MCP不能 / TdxQuant未测 | MCP确认不能;TdxQuant外部不可用(InitConnect),subscribe_hq待内嵌验证 | **CONFIRMED_WITH_NARROWER_SCOPE** | 探针 |
| 4 | 能否获得逐笔: TdxQuant静态未见get_tick | 修正: `_fast_format_tick_data`存在+`period=='tick'`死代码分支→基础设施存在但入口被阻断 | **UNDERSTATED**(旧漏报tick基础设施) | 源码896/938/1133 |
| 5 | 能否获得集合竞价数据: MCP无独立字段 | 确认MCP无;但R1/R2 raw未落盘,旧AUCTION-FINDINGS字段陈述无raw佐证 | **CONFIRMED + 缺证据** | 完整性复算 |
| 6 | 本地文件完全无法提供L2 | 修正:发现.th2(14MB)/.tcu/.tnf/PriCS.dat(802KB)/sz.tfz(实时)候选专有缓存,可能含L2,不可直接解析 | **OVERSTATED**(旧过窄) | 广谱审计 |
| 7 | InOut=总委买-总委卖; InOutHB=撤单聚合 | 无官方定义,均为推测;InOutHB正负翻转与"撤单"不符 | **UNSUPPORTED**(推翻语义断言) | 字段复验 |
| 8 | "MCP连续稳定无错误无限流" | 仅约12次调用/2轮完整raw,不能宣称无限流 | **OVERSTATED** | 样本规模 |
| 9 | UI能力与API能力被严格分离 | 旧报告此原则正确,新报告沿用 | **CONFIRMED** | — |
| 10 | 原始证据完整 | R1/R2 raw未落盘;receive_time_ns=0;receive_time_local粒度=轮级 | **UNSUPPORTED**(存在缺口) | 完整性复算 |

## 推翻/收窄的旧结论（摘要）
- **推翻**: #2(DLL干扰风险→实际可安全尝试,InitConnect失败才是真因)、#7(InOutHB撤单语义→unknown)、#8(无限流→未观察到错误)
- **收窄**: #3(十档,TdxQuant外部不可用)、#4(逐笔基础设施存在但阻断)
- **修正放大**: #6(本地有候选L2缓存文件)

## 强模型独立确认的三项事实
1. MCP 不暴露十档（三轮 RAW_EVIDENCE_VERIFIED）
2. L2 聚合字段经 MCP 实时可读且跨轮变动（AGGREGATE_ONLY）
3. TdxQuant 外部 python 不可用（InitConnect 失败，RUNTIME_VERIFIED，TdxW 未受损）
