# V104-METHOD-SURFACE — tqcenter.py v1.0.4 方法存在性

## 关键方法 (0006 点名的)
| 方法 | v1.0.4 存在 | 源码行 | hasattr | 备注 |
|---|---|---|---|---|
| get_more_info | ✅ | 3019 | True | DLL GetMoreInfoInStr, 86字段含13个L2聚合 |
| get_gb_info | ✅ | 3051 | True | 股本信息 |
| get_ipo_info | ✅ | 2748 | True | IPO 信息 |
| download_file | ✅ | 2568 | True | 下载(股东/舆情/龙虎榜等) |
| get_trackzs_etf_info | ✅ | 3207 | True | 追踪指数ETF |
| send_message | ✅ | 1342 | True | 策略管理输出 |
| send_warn | ✅ | 1396 | True | 策略警告输出 |
| get_pricevol | ❌ | — | False | **v1.0.12 新增** |
| formula_get_all | ❌ | — | False | **v1.0.12? 官方 changelog 声称有** |
| formula_get_info | ❌ | — | False | **v1.0.12?** |
| get_match_stkinfo | ❌ | — | False | **v1.0.12 新增** |
| get_relation | ❌ | — | False | **v1.0.12 新增** |

## 完整公开方法列表 (tq 类, v1.0.4, 共 ~30 个)
initialize, _auto_initialize, close, get_market_data, get_market_snapshot, get_stock_info,
get_sector_list, get_user_sector, get_stock_list_in_sector, get_financial_data, get_financial_data_by_date,
get_divid_factors, get_gpjy_value, get_gpjy_value_by_date, get_bkjy_value, get_bkjy_value_by_date,
get_scjy_value, get_scjy_value_by_date, get_gp_one_data, get_trading_calendar, get_trading_dates,
get_stock_list, order_stock, subscribe_quote, subscribe_hq, unsubscribe_hq, get_subscribe_hq_stock_list,
send_message, send_warn, send_file, **get_more_info**, **get_gb_info**, get_gb_info_by_date, **get_ipo_info**,
get_cb_info, get_kzz_info(?), get_trackzs_etf_info, **download_file**, get_match_stkinfo(?), exec_to_tdx(?),
refresh_cache, refresh_kline, create_sector, delete_sector, rename_sector, clear_sector,
send_bt_data, send_user_block, send_res

> ? = 部分方法可能在 v1.0.4 存在但首次被 v1.0.12 文档化列举
