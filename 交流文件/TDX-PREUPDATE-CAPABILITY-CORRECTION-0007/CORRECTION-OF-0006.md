# CORRECTION-OF-0006 — 0006 结论校正清单

> 生成: 2026-07-16 10:57 | 校正来源: tqcenter.py v1.0.4 静态 grep + 运行时探针(probe_v2)

## 需要撤回/修正的 0006 结论

| # | 0006 旧结论 | 实测结果 | 校正 |
|---|---|---|---|
| 1 | "v1.0.4 没有 get_more_info" | **有** — tqcenter.py 3019行, DLL GetMoreInfoInStr, 4标的全返回86字段含全部13个L2聚合字段 | **撤回** |
| 2 | "v1.0.4 没有 get_gb_info" | **有** — 3051行 | **撤回** |
| 3 | "v1.0.4 没有 get_ipo_info" | **有** — 2748行 | **撤回** |
| 4 | "v1.0.4 没有 download_file" | **有** — 2568行 | **撤回** |
| 5 | "v1.0.4 没有 get_trackzs_etf_info" | **有** — 3207行 | **撤回** |
| 6 | "v1.0.4 没有 send_message" | **有** — 1342行 | **撤回** |
| 7 | "v1.0.4 没有 send_warn" | **有** — 1396行 | **撤回** |
| 8 | "TdxQuant 外部 InitConnect 失败" | **初始化成功** — `tq.initialize(__file__)` → "TQ数据接口初始化成功" run_id=3 | **撤回。根因: 未调 initialize(path)** |
| 9 | "Codex 仅在内嵌环境初始化成功" | 外部 python.exe(3.13, managed venv) 同样成功;只需 path 参数 | **撤回** |
| 10 | "v1.0.4 缺失 v1.0.12 Skill 文档中的 L2TicNum 等字段" | v1.0.4 get_more_info 已有全部13个L2聚合字段 | **撤回** |

## 0006 中仍然正确的结论
| # | 结论 | 依据 |
|---|---|---|
| 1 | v1.0.4 没有 get_pricevol | hasattr(tq, 'get_pricevol') = False |
| 2 | v1.0.4 没有 formula_get_all | hasattr = False |
| 3 | v1.0.4 没有 formula_get_info | hasattr = False |
| 4 | v1.0.4 没有 get_match_stkinfo | hasattr = False |
| 5 | v1.0.4 没有 get_relation | hasattr = False |
| 6 | get_market_data(period='tick') 被拒绝 | error -5, valid_periods 不含 tick |
| 7 | 端口 17709 NOT_LISTENING | Test-NetConnection 失败 |
| 8 | v1.0.4 vs v1.0.12 版本错位 | 确认 8 minor 版本差距 |
| 9 | 十档/原始逐笔/委托队列未突破 | 各路确认 |

## 根因分析
0006 关于 v1.0.4 方法缺失的漏报:
- **方法枚举不完整**: 只 grep 了 `def get_*` 模式，但 `get_more_info` 等带有多参数的 def 行被 grep 捕获，我在 0006 时未做更全面的静态检查
- **初始化路径错误**: probe_v1 未调 `tq.initialize(__file__)` → 空 path → RuntimeError。probe_v2 修正后成功

## 推荐更新后的 AB 测试计划
v1.0.12 预期新增: get_pricevol / get_match_stkinfo / get_relation + tick period 支持 + formula_get_all/formula_get_info(待确认)。需升级后运行以下比对:
1. v1.0.4 vs v1.0.12 get_more_info 字段差异
2. v1.0.12 get_market_data(period='tick') 是否可用
3. v1.0.12 formula_get_all 是否存在
