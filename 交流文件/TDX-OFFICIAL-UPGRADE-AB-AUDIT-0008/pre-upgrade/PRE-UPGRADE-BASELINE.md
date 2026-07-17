# PRE-UPGRADE-BASELINE — v1.0.4 升级前基线

> 快照时间: 2026-07-16 11:07 | TdxW PID 1628 存活 | 不中断交易

## 组件信息
| 组件 | 版本 | 大小 | SHA256 | mtime |
|---|---|---|---|---|
| tqcenter.py | v1.0.4 | 130,371 | 6D685E0ED8... | 2026-03-06 |
| TPythClient.dll | N/A | 2,411,416 | 5772EF0C5D... | 2026-03-23 |
| 客户端主程序 | 1,0,0,1 | — | — | — |
| Python解释器 | 3.13.14 (managed venv) | — | — | — |

## 端口状态
- 127.0.0.1:17709: **NOT_LISTENING**

## v1.0.4 方法清单 (30个公开方法)
initialize, _auto_initialize, close, get_market_data, get_market_snapshot, get_stock_info,
get_sector_list, get_user_sector, get_stock_list_in_sector, get_financial_data, get_financial_data_by_date,
get_divid_factors, get_gpjy_value, get_gpjy_value_by_date, get_bkjy_value, get_bkjy_value_by_date,
get_scjy_value, get_scjy_value_by_date, get_gp_one_data, get_trading_calendar, get_trading_dates,
get_stock_list, order_stock (禁止), subscribe_quote, subscribe_hq, unsubscribe_hq, get_subscribe_hq_stock_list,
send_message, send_warn, send_file, get_more_info, get_gb_info, get_ipo_info,
get_cb_info, get_trackzs_etf_info, download_file

## 缺失方法 (预期升级后新增)
get_pricevol, get_match_stkinfo, get_relation, formula_get_all, formula_get_info

## v1.0.4 运行时结果 (见 0007 probe_v2, GET-MORE-INFO-FIELD-MATRIX)
- get_more_info: 4标的 86字段，13个L2聚合全部存在 ✅
- get_market_data(tick): ❌ error -5 (valid_periods 不含 tick)
- formula 方法: ❌ hasattr=False
- 外部初始化: ✅ 成功 (tq.initialize(__file__), run_id=3)
- get_market_snapshot: ✅ 五档
- subscribe_hq: 未运行 (外部环境风险, 待内嵌测试)

## Level-2 权限
用户已开通沪深 Level-2, 升级后需确认仍有效。
