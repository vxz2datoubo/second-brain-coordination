# RUN-RECEIPT — STOCKAPI-L2-RUNTIME-PREP-AND-LIVE-POC-0016

任务: STOCKAPI-L2-RUNTIME-PREP-AND-LIVE-POC-0016
生成: 2026-07-17 02:55 UTC+8
模型: DeepSeek-V4-Pro (reasoning)
状态: ✅ PHASE1 离线准备完成

## 执行摘要

| 指标 | 值 |
|------|-----|
| task_id | STOCKAPI-L2-RUNTIME-PREP-AND-LIVE-POC-0016 |
| status | PHASE1_OFFLINE_PREP_COMPLETE |
| 是否取得账号 | ❌ 用户尚未提供 |
| 是否接触/泄露凭据 | ❌ 否 — 无凭据可接触 |
| 是否安装未知程序 | ❌ 否 |
| 服务器 | dy1.l2api.cn / gzqt1.l2api.cn (待服务器发现确定) |
| 四端口 | 18100(Market)/18103(Order)/18104(Queue)/18105(Tran) |
| Queue端口已加入 | ✅ Demo缺失，已标注P0风险 |
| 登录确认后订阅 | ✅ 要求：等`<DL,...>`成功后再`<DY2,..>` |
| 环境基线 | Python 3.13.14, F盘 4.65TB可用, 端口全空闲 |
| 周一PoC时间 | 2026-07-20 09:00-15:35 |
| PoC标的 | 300418.SZ/300058.SZ/600519.SH/510300.SH/000001.SZ (最多5只) |

## Demo审查结论

- test_demo.py: 参考骨架。解析逻辑正确(curly-brace buffer + `#` 多记录), 十档+66字段覆盖完整。需P0修正4项(密码/登录确认/Queue端口/重连策略)。
- test_demo (2)(1).py: 反例。嵌套正则`finditer`逻辑错误, gzip解压被注释, 仅print不落盘。不进入任何运行。
- 两Demo均缺失Queue端口18104 — 这是PoC核心验证目标。

## 排队风险

| 级别 | 数量 | 详情 |
|------|:---:|------|
| P0 (阻塞运行) | 4 | 密码环境变量/登录确认/Queue端口/反例解析 |
| P1 (严重) | 4 | 重连策略/KICK/队列/原始落盘 |
| P2 (生产就绪) | 4 | HTTP回补/monotonic/local_seq/connection_id |

## 周一前必须完成 (用户侧)

1. 取得 StockAPI 账号并配置环境变量
2. 确认北京/广州接入点网络可达性
3. P0修正项的采集器脚本改造

## 禁止确认

| 禁止项 | 状态 |
|------|:---:|
| 未联系商家 | ✅ |
| 未代付款 | ✅ |
| 未登录支付账户 | ✅ |
| 未把凭据写入聊天/报告/源码 | ✅ |
| 未发送凭据给ChatGPT/Codex | ✅ |
| 未安装未知程序 | ✅ |
| 未开放入站公网端口 | ✅ |

## 交付物

目录: `F:\aidanao\交流文件\STOCKAPI-L2-RUNTIME-PREP-AND-LIVE-POC-0016\`

| 文件 | 状态 |
|------|:---:|
| ENVIRONMENT-BASELINE.md | ✅ |
| DEMO-RUNTIME-RISK-REVIEW.md | ✅ |
| SECRET-HANDLING-RECEIPT.md | ✅ |
| STATUS.yaml | ✅ |
| RUN-RECEIPT.md | ✅ |
| SERVER-DISCOVERY.json | ⏳ 需要账号 |
| RAW-FRAMES/ | ⏳ 周一运行时 |
| NORMALIZED-SAMPLES/ | ⏳ 周一运行时 |
| CODEX-SANITIZED-SAMPLE-PACK/ | ⏳ 周一运行时 |
| MARKET/ORDER/TRAN/QUEUE-RUNTIME-RESULT.md | ⏳ 周一 |
| SEQUENCE-AND-GAP-ANALYSIS.md | ⏳ 周一 |
| HTTP-BACKFILL-RESULT.md | ⏳ 周一 |
| DATA-QUALITY-METRICS.json | ⏳ 周一 |
| CAPABILITY-EVIDENCE-MATRIX.md | ⏳ 周一 |
| SECURITY-RECEIPT.md | ⏳ 周一 |
