# OFFICIAL-SKILL-FILES — 官方 Skill 包文件清单

## 下载来源
- TQ-Python: `https://www.tdx.com.cn/products/autoup/skills/tdx-quant.zip`
- TQ-Local: `https://www.tdx.com.cn/products/autoup/skills/tdx-tq-local.zip`
- 来源页面: `https://help.tdx.com.cn/quant/docs/markdown/mindoc-1he2c52nvvdkg.html`

## 文件结构

### TQ-Python v1.0.12 (tdx-quant.zip, 27,315 bytes)
```
SKILL.md  (~5KB frontmatter + 全文)
```
单文件 Skill，内容为 tqcenter.py 接口文档 + Python 代码编写指引。

### TQ-Local v1.0.12 (tdx-tq-local.zip, 27,900 bytes)
```
SKILL.md  (2,000+ lines, 完整接口文档)
```
单文件 Skill，内容为 HTTP 17709 JSON-RPC 接口文档（改写自 tqcenter.py）。

## 底层调用路径
- **TQ-Local**: Skill → HTTP 127.0.0.1:17709 (JSON-RPC) → TDX 客户端内嵌 HTTP 服务 → tqcenter APIs
- **TQ-Python**: Skill → 生成 Python 代码文件 → 运行 tqcenter.py → TPythClient.dll → TDX

## 禁止清单（交易类工具）
- order_stock, cancel_order_stock, query_stock_positions, query_stock_asset, stock_account
- 任何含 "order"/"trade"/"position"/"account" 的交易接口
- 本轮均未调用

## 工具枚举 (TQ-Local 行情/只读类)
get_market_data, get_market_snapshot, get_stock_info, get_match_stkinfo, get_stock_list, get_sector_list, get_user_sector, get_stock_list_in_sector, get_trading_calendar, get_trading_dates, get_relation, **get_pricevol**, get_divid_factors, **get_more_info**, get_gb_info, get_gb_info_by_date, get_kzz_info, get_ipo_info, get_trackzs_etf_info, get_financial_data, get_financial_data_by_date, get_gpjy_value, get_gpjy_value_by_date, get_bkjy_value, get_bkjy_value_by_date, get_scjy_value, get_scjy_value_by_date, refresh_cache, refresh_kline, download_file, send_message, send_file, send_warn, send_bt_data, send_user_block, exec_to_tdx, create_sector, delete_sector, rename_sector, clear_sector
