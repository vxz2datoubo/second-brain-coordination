# TDXQUANT-STATIC-SURFACE

- generated_at: `2026-07-16T10:22:00.576+08:00`
- python: `C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe`
- tqcenter.py: `F:\tongdaxin\PYPlugins\user\tqcenter.py`
- tqcenter_sha256: `6d685e0ed802b63341d2ca07183ce84b121d950bb47c09048cb585dc74219eb4`
- TPythClient.dll: `F:\tongdaxin\PYPlugins\TPythClient.dll`
- TPythClient_sha256: `5772ef0c5d48c33b1bd14c9f6734135441c6ad767d86773031274d229faf2170`

## Public callable surface

- `clear_sector(block_code: str = '')`
- `close()`
- `create_sector(block_code: str = '', block_name: str = '')`
- `data_transfer(signature_unavailable)`
- `delete_sector(block_code: str = '')`
- `download_file(stock_code: str = '', down_time: str = '', down_type: int = 1)`
- `filter_dict_by_fields(data: Dict = {}, field_list: List = []) -> Dict`
- `formula_exp(formula_name: str = '', formula_arg: str = '')`
- `formula_format_data(data_dict: Dict = {})`
- `formula_get_data()`
- `formula_process_mul(formula_name: str = '', formula_arg: str = '', formula_type: int = 0, return_count: int = 1, return_date: bool = False, xsflag: int = -1, stock_list: List[str] = [], stock_period: str = '1d', start_time: str = '', end_time: str = '', count: int = 0, dividend_type: int = 0)`
- `formula_process_mul_xg(formula_name: str = '', formula_arg: str = '', return_count: int = 1, return_date: bool = False, stock_list: List[str] = [], stock_period: str = '1d', start_time: str = '', end_time: str = '', count: int = 0, dividend_type: int = 0)`
- `formula_process_mul_zb(formula_name: str = '', formula_arg: str = '', return_count: int = 1, return_date: bool = False, xsflag: int = -1, stock_list: List[str] = [], stock_period: str = '1d', start_time: str = '', end_time: str = '', count: int = 0, dividend_type: int = 0)`
- `formula_set_data(stock_code: str = '', stock_period: str = '1d', stock_data: List = [], count: int = 1, dividend_type: int = 0)`
- `formula_set_data_info(stock_code: str = '', stock_period: str = '1d', start_time: str = '', end_time: str = '', count: int = 0, dividend_type: int = 0)`
- `formula_xg(formula_name: str = '', formula_arg: str = '')`
- `formula_zb(formula_name: str = '', formula_arg: str = '', xsflag: int = -1)`
- `get_bkjy_value(stock_list: List[str] = [], field_list: List[str] = [], start_time: str = '', end_time: str = '') -> Dict`
- `get_bkjy_value_by_date(stock_list: List[str] = [], field_list: List[str] = [], year: int = 0, mmdd: int = 0) -> Dict`
- `get_cb_info(stock_code: str = '', field_list: List[str] = [])`
- `get_divid_factors(stock_code: str, start_time: str, end_time: str) -> pandas.DataFrame`
- `get_financial_data(stock_list: List[str] = [], field_list: List[str] = [], start_time: str = '', end_time: str = '', report_type: str = 'report_time') -> Dict`
- `get_financial_data_by_date(stock_list: List[str] = [], field_list: List[str] = [], year: int = 0, mmdd: int = 0) -> Dict`
- `get_gb_info(stock_code: str = '', date_list: List[str] = [], count: int = 1)`
- `get_gp_one_data(stock_list: List[str] = [], field_list: List[str] = []) -> Dict`
- `get_gpjy_value(stock_list: List[str] = [], field_list: List[str] = [], start_time: str = '', end_time: str = '') -> Dict`
- `get_gpjy_value_by_date(stock_list: List[str] = [], field_list: List[str] = [], year: int = 0, mmdd: int = 0) -> Dict`
- `get_ipo_info(ipo_type: int = 0, ipo_date: int = 0)`
- `get_market_data(field_list: List[str] = [], stock_list: List[str] = [], period: str = '', start_time: str = '', end_time: str = '', count: int = -1, dividend_type: Optional[str] = None, fill_data: bool = True) -> Dict`
- `get_market_snapshot(stock_code: str, field_list: List = []) -> Dict`
- `get_more_info(stock_code: str = '', field_list: List = [])`
- `get_scjy_value(field_list: List[str] = [], start_time: str = '', end_time: str = '') -> Dict`
- `get_scjy_value_by_date(field_list: List[str] = [], year: int = 0, mmdd: int = 0) -> Dict`
- `get_sector_list(list_type: int = 0) -> List`
- `get_stock_info(stock_code: str, field_list: List = []) -> Dict`
- `get_stock_list(market=None, list_type: int = 0) -> List`
- `get_stock_list_in_sector(block_code: str, block_type: int = 0, list_type: int = 0) -> List`
- `get_subscribe_hq_stock_list()`
- `get_trackzs_etf_info(zs_code: str = '')`
- `get_trading_calendar(market: str, start_time: str, end_time: str) -> List`
- `get_trading_dates(market: str, start_time: str, end_time: str, count: int = -1) -> List`
- `get_user_sector() -> List`
- `initialize(path: str, dll_path: str = '')`
- `order_stock(account: str, stock_code: str, order_type: int, order_volume: int, price_type: int, price: float, strategy_name: str, order_remark: str = '')` FORBIDDEN_BY_RUN_POLICY
- `price_df(df, price_col, column_names=None)`
- `print_to_tdx(df_list, sp_name='', xml_filename='', jsn_filenames=None, vertical=None, horizontal=None, height=None, table_names=None)`
- `refresh_cache(market: str = 'AG', force: bool = False)`
- `refresh_kline(stock_list: List[str] = [], period: str = '')`
- `rename_sector(block_code: str = '', block_name: str = '')`
- `send_bt_data(stock_code: str = '', time_list: List[str] = [], data_list: List[List[str]] = [], count: int = 1) -> Dict`
- `send_file(file_path: str) -> Dict`
- `send_message(msg_str: str) -> Dict`
- `send_user_block(block_code: str = '', stocks: List[str] = [], show: bool = False) -> Dict`
- `send_warn(stock_list: List[str] = [], time_list: List[str] = [], price_list: List[str] = [], close_list: List[str] = [], volum_list: List[str] = [], bs_flag_list: List[str] = [], warn_type_list: List[str] = [], reason_list: List[str] = [], count: int = 1) -> Dict`
- `subscribe_hq(stock_list: List[str] = [], callback=None)`
- `subscribe_quote(stock_code: str, period: str = '1d', start_time: str = '', end_time: str = '', count: int = 0, dividend_type: Optional[str] = None, callback=None)`
- `tdx_formula(formula_type: int = 0, formula_name: str = '', formula_arg: str = '', xsflag: int = -1)`
- `unsubscribe_hq(stock_list: List[str] = [])`

## Legacy alias check

- `get_full_tick`: `False`
- `get_report_data`: `False`
