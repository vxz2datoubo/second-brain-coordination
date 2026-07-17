# LIVE-TIMELINE — TDX-L2-LIVE-AUCTION-AUDIT-0003

> 所有时间为北京时间。本地接收时间 ≠ 交易所时间(HQTime)。

| 本地接收 | HQTime(交易所) | 轮次 | 阶段 | 事件 |
|---|---|---|---|---|
| 09:21:53 | — | — | 盘前 | TdxW.exe 启动 (PID 1628) |
| 09:22:00 | — | — | 盘前 | tdxcef 子进程启动 |
| 09:24:15 | — | — | B(不可撤单) | 审计任务下发, 建目录, 探测环境 |
| 09:25:21 | 92500-92519 | R1 | C(撮合点) | 首轮采集, 覆盖撮合窗口; InOut/InOutHB 尚未出现 |
| 09:26:29 | 926xx | R2 | D(过渡) | InOut/InOutHB 首次出现; WeStock 价格对齐 |
| 09:32:18 | 93218-93221 | R3 | E(连续) | L2 聚合字段实时变动; BspInfo 仍5档; 落盘 raw |
| 09:35 | — | — | E | tqcenter.py 静态枚举 (v1.0.4, tq类23方法) |
| 09:35 | — | — | E | 文件监控: 无.l2d/.tick, 仅hq_cache压缩缓存 |
| 09:39:06 | 93903-93907 | R4 | E(中段) | L2 聚合跨轮变动确认; 十档definitive否定; 落盘 raw |
| 09:39:09 | — | — | E | 当前时刻; 10:00前可继续追加轮次 |

## 原始数据落盘
- `raw/tdx_mcp.jsonl` — 12行 (6标的 × R3/R4), 含 receive_time_local/local_sequence_no/raw_payload_hash
- `raw/westock.jsonl` — 10行 (5标的 × R3/R4, 999999指数WeStock无独立行)
- `raw/tdxquant.jsonl` — 1行 (静态枚举)
- `raw/formula_results.jsonl` — 1行 (L2聚合字段快照)
- `raw/file_changes.jsonl` — 1行 (本地文件监控)
- `raw/r3_full.json` / `raw/r4_full.json` — 整轮完整载荷
- `raw/_poll_anchor_r{1,2,3,4}.txt` — 各轮接收时间锚点
