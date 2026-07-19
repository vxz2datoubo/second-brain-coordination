# RUN-RECEIPT — TDX-PREUPDATE-CAPABILITY-CORRECTION-0007

> 2026-07-16 11:00 | 状态: COMPLETED | 原文件未修改

## 1. v1.0.4 是否存在 get_more_info
**是。** 源码3019行, hasattr=True, RUNTIME_VERIFIED: 4标的全部成功返回86字段, 含全部13个L2聚合字段。0006 的"v1.0.4没有get_more_info"错误。

## 2. v1.0.4 实际返回哪些 L2 聚合字段
**全部13个**: L2TicNum, L2OrderNum, TotalBVol, TotalSVol, BCancel, SCancel, Zjl, Zjl_HB, OpenAmo, OpenZTBuy, Wtb, FzAmo, VOpenZAF。4标的均存在,值随行情不同。**但均为 AGGREGATE(计数/总量), 非原始逐笔。**

## 3. WorkBuddy 和 Codex 初始化差异来自什么
**根因: 未调 `tq.initialize(__file__)`。** `_auto_initialize` 检查 `cls._connection_path` → 为空抛 RuntimeError。WorkBuddy probe_v1 跳过了 initialize → 失败; probe_v2 先调 initialize → 成功。与 Codex 无本质差异——都通过外部 python.exe 成功。

## 4. 哪些 0006 结论需要撤回
**10 条撤回**(详 CORRECTION-OF-0006.md)。核心: v1.0.4 有 get_more_info/get_gb_info/ipo_info/download/send_message/get_trackzs_etf_info; 外部初始化可成功; v1.0.4 get_more_info 已有 L2 聚合字段。

## 5. 当前是否仍有必要升级
**是。** v1.0.4 仍缺 get_pricevol/get_match_stkinfo/get_relation + tick period + 可能的 formula + 端口17709。升级后 get_more_info 字段可能更多(>86)。升级 v1.0.4→v1.0.12 有价值, 但非紧急(核心L2聚合在v1.0.4已可用)。

## 6. 升级后必须重测哪些接口
P0: get_more_info 字段差异 + tick period 可用性。P1: get_pricevol/formula/get_match_stkinfo 存在性+运行。P2: HTTP 17709 + subscribe_hq 推送增强。(详 UPGRADE-AB-TEST-PLAN.md)

## 输出目录
`F:\aidanao\交流文件\TDX-PREUPDATE-CAPABILITY-CORRECTION-0007\` (11文件 + probes/)
