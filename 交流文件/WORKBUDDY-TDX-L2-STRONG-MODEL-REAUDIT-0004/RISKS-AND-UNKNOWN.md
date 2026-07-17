# RISKS-AND-UNKNOWN — 0004 复验

## 风险
- **R1 字段语义误用**: InOut/InOutHB/Wtb/TotalBuyv 等均无官方定义，旧报告语义断言已推翻。误用可致资金流方向判断反向。→ 红线: 取得官方定义前不得用于方向决策。
- **R2 样本不足**: 仅2轮完整raw+1轮单标的，不能证稳定/不限流/无偶发字段。
- **R3 R1/R2无raw**: 旧竞价期结论无原始证据复核依据。
- **R4 CasImbVol/CasUpperPx 脏数据**: 指数量级 1e-42，疑未初始化，禁用。
- **R5 本地专有格式逆向风险**: .th2/.tcu/PriCS.dat 直接解析有半条记录风险，须先做结构分析。
- **R6 TdxQuant 内嵌运行风险**: subscribe_hq 在 TdxW 内嵌运行会注册回调线程，须确保 unsubscribe + atexit，否则回调泄漏。

## 未知
1. subscribe_hq 推送字段集（是否含十档/逐笔）— 须内嵌验证
2. InOut/InOutHB/NowVol/Wtb/TotalBuyv/TotalSellv/HQMaskFlag 官方定义 — unknown_vendor_semantics
3. .th2/.tcu/.tnf/PriCS.dat/sz.tfz 内部结构 — 须逆向
4. get_market_data period='tick' 死代码是否在更高版本/内嵌环境可达
5. 09:15-09:24 竞价逐秒轨迹 — 已不可补
6. TdxQuant 内嵌 get_market_snapshot 是否返回 L2 聚合字段（外部InitConnect失败，内嵌未测）

## 表述规范
- 当前未观察到错误 → 表述"在已测试频率和样本规模内未观察到错误或限流"，**不得表述"无限流"**。
