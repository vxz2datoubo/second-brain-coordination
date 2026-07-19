# CAPABILITY-EVIDENCE-MATRIX — 综合能力证据矩阵

> 汇总三条路线(Python v1.0.4 / HTTP v1.0.12文档 / TQ-Local v1.0.12)的 L2 能力判定。

| # | 能力 | Python tqcenter v1.0.4 | HTTP 17709 (v1.0.12文档) | TQ-Local v1.0.12 | TDX MCP | WeStock |
|---|---|---|---|---|---|---|
| 1 | 十档 | NOT_SUPPORTED | NOT_EXPOSED | NOT_EXPOSED | NOT_SUPPORTED | N/A |
| 2 | 五档 | RUNTIME_VERIFIED | STATIC_DOCUMENTED | 同HTTP | RAW_EVIDENCE_VERIFIED | N/A |
| 3 | 逐笔成交(原始) | NOT_SUPPORTED(死代码) | NOT_EXPOSED | NOT_EXPOSED | NOT_SUPPORTED | N/A |
| 4 | 逐笔委托(原始) | NOT_SUPPORTED | NOT_EXPOSED | NOT_EXPOSED | NOT_SUPPORTED | N/A |
| 5 | 委托队列 | NOT_SUPPORTED | NOT_EXPOSED | NOT_EXPOSED | NOT_SUPPORTED | N/A |
| 6 | 集合竞价(虚拟价/匹配量) | NOT_SUPPORTED | NOT_EXPOSED | NOT_EXPOSED | NOT_SUPPORTED | N/A |
| 7 | L2逐笔成交数 | NOT_SUPPORTED(v1.0.4) | STATIC_DOCUMENTED(L2TicNum) | 同HTTP | NOT_SUPPORTED | N/A |
| 8 | L2逐笔委托数 | NOT_SUPPORTED(v1.0.4) | STATIC_DOCUMENTED(L2OrderNum) | 同HTTP | NOT_SUPPORTED | N/A |
| 9 | 总委买/委卖 | NOT_SUPPORTED(v1.0.4) | STATIC_DOCUMENTED(TotalBVol/SVol) | 同HTTP | AGGREGATE_ONLY(InOut) | N/A |
| 10 | 总撤买/撤卖 | NOT_SUPPORTED(v1.0.4) | STATIC_DOCUMENTED(BCancel/SCancel) | 同HTTP | AGGREGATE_ONLY(InOutHB) | N/A |
| 11 | 主力净流入 | NOT_SUPPORTED(v1.0.4) | STATIC_DOCUMENTED(Zjl/Zjl_HB) | 同HTTP | NOT_SUPPORTED | wb_ratio代理 |

## 证据等级
- RUNTIME_VERIFIED: 运行时实测(Python external, TDX MCP)
- RAW_EVIDENCE_VERIFIED: 多轮实测(TDX MCP R3/R4/R5)
- STATIC_DOCUMENTED: 官方文档枚举(HTTP不可达, 未实测)
- NOT_SUPPORTED: 代码/文档确认不支持
- NOT_EXPOSED: 当前版本未见
- N/A: 该数据源不提供此类别
