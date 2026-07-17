# TDXQUANT-REAUDIT — TdxQuant 强制复验

## 一、静态枚举（tqcenter.py v1.0.4, 关键词扫描）
检查关键词: tick/transaction/trade/order/entrust/queue/detail/auction/l2/full/report/init/subscribe/snapshot/market/hq

### 公开方法（tq 类）
- initialize (410) / _auto_initialize (472)
- get_market_data (872) / get_market_snapshot (1310) / get_stock_info (1278)
- get_divid_factors / get_sector_list / get_user_sector / get_stock_list_in_sector
- get_financial_data* / get_gpjy_value* / get_bkjy_value* / get_scjy_value* / get_gp_one_data
- get_trading_calendar / get_trading_dates / get_stock_list
- **order_stock (2252) ← 下单，严禁**
- subscribe_quote (2302) / **subscribe_hq (2390)** / unsubscribe_hq (2450) / get_subscribe_hq_stock_list (2503)
- get_cb_info / get_ipo_info / get_more_info / get_gb_info / get_trackzs_etf_info

### 关键发现
1. **`_fast_format_tick_data` (1133) 存在** — 内部逐笔数据格式化（Date/Time 时间戳+数值字段，numpy 结构化数组）。→ 逐笔基础设施**存在**。
2. **`get_market_data` 第896行 `valid_periods` 不含 'tick'**，但第938行 `if period == 'tick': cls._fast_format_tick_data(...)` 分支存在 → **验证先拒绝 'tick'，该分支为死代码**。即公开 get_market_data(period='tick') 会返回 error -5，不可达 tick 格式化。
3. **`get_market_snapshot` 实为报表接口** — 调用 `dll.GetREPORTInStr`，docstring "获取报表数据"，返回行情表字段（非盘口快照）。旧报告把它当"实时盘口快照API"不准确。
4. **未发现** get_full_tick / get_report_data（任务点名）/ get_transaction / get_order / get_entrust / get_queue / get_auction / get_l2_* 公开方法。
5. subscribe_hq 走 `dll.SubscribeHQDUpdate` + `Register_DataTransferFunc` 回调，推送内容由 DLL 决定（是否含十档/逐笔须抓回调参数）。

## 二、运行时探针（旧轮未执行，本轮新增）— RUNTIME_VERIFIED
- 探针: `_probe_snapshot.py`，仅 get_market_snapshot(300418.SZ/600519.SH)，禁 order/subscribe
- 环境: managed venv 3.13 + numpy 2.5.1 + pandas 3.0.3
- 结果（probe/probe_result.json）:
  - `import tqcenter`: ✅ ok (0.73s)，TPythClient.dll 加载成功
  - `get_market_snapshot("300418.SZ")`: ❌ **`RuntimeError: TQ数据接口初始化失败`**
  - `get_market_snapshot("600519.SH")`: ❌ 同上
  - `close`: ✅ ok
  - **TdxW PID 1628 探针前=true / 后=true（未受损）**

## 三、具体技术依据（回应任务"不得笼统判断危险"）
- **实证**: tqcenter 从外部 python.exe 可 import + DLL 可加载，但 `InitConnect`(经 `_auto_initialize`→`initialize`→`dll.InitConnect`) **返回失败**。
- **原因推断（有据）**: TPythClient.dll 的 InitConnect 极可能校验调用方是否为 TdxW 内嵌插件宿主（共享内存/父进程上下文），外部独立 python.exe 不满足 → 初始化失败。无 TDX 独立 python.exe 可调用佐证"须在 TdxW 内运行"。
- **安全实证**: 探针后 TdxW 仍存活 → 外部尝试不会崩溃客户端。**旧轮"加载DLL即干扰风险"判断 = OVERSTATED（过虑）**。
- subscribe_hq 同样走 `_auto_initialize`，外部调用亦会 InitConnect 失败，故本轮未单独测（无意义）。

## 四、结论
- **TdxQuant 无法从外部脚本使用**（InitConnect 失败）。要使用须在 **TdxW 策略管理器/Python 插件宿主内**加载运行。
- 即便在内嵌运行: get_market_data 拿不到 tick（valid_periods 阻断）；get_market_snapshot 拿报表字段；十档/逐笔**仅可能**经 subscribe_hq 推送获得（须内嵌环境抓回调验证）。
- **建议**: 收盘后在 TdxW 内嵌插件环境运行 subscribe_hq 探针，抓回调原始参数，定论推送是否含十档/逐笔。此为唯一未闭合的关键验证。

## 五、任务要求对照
- `initialize`: 存在(410)，外部调用失败
- `subscribe_hq`: 存在(2390)，外部不可用(InitConnect阻断)，待内嵌验证
- `get_market_snapshot`: 存在(1310)，实为报表接口(GetREPORTInStr)，外部InitConnect失败
- `get_full_tick`: **不存在**
- `get_report_data`: **不存在**（get_market_snapshot 即报表接口，命名误导）
