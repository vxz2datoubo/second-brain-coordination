# RISKS-AND-UNKNOWN — TDX-L2-LIVE-AUCTION-AUDIT-0003

## 风险

### R1. UI能力误当API能力 (最高风险)
- **事实**: 用户客户端 UI 显示十档/逐笔/委托队列/虚拟价/匹配量/未匹配量/总撤买卖 (UI_VERIFIED_BY_USER), 但 **TDX MCP 全部拿不到**。
- **风险**: 若据 UI 能力推断 MCP 可读, 将导致策略基于不存在的数据。
- **处置**: CAPABILITY-MATRIX 已逐项分离 UI/MCP/TdxQuant/本地文件/公式, 严禁跨接口推断。

### R2. InOutHB 字段语义未确认
- **事实**: `ProInfo.InOutHB` 实时大幅变动 (510300 R3=-108M→R4=-377M), 疑为"撤买/撤卖聚合"或"沪市委托净额", 但**字段名未在官方文档确认**。
- **风险**: 误读 InOutHB 语义导致资金流判断反向。
- **处置**: 标记 `FORMULA_AGGREGATE_ONLY`, 待官方文档/公式编辑器确认语义后再用于决策。不得仅凭字段名推断。

### R3. HQMaskFlag 差异
- **事实**: 不同标的 HQMaskFlag 不同 (300418=11, 300058=10, 600519=7, 510300=6, 000609=1048576/0x100000)。
- **风险**: 掩码位含义未知, 0x100000(*ST)可能标记特殊状态。
- **处置**: 记录为 UNKNOWN, 不据其做判断。

### R4. TdxQuant 运行时未验证
- **事实**: tqcenter.py 静态存在, 但 get_market_snapshot/subscribe_hq **未运行时执行** (避免 DLL 干扰运行客户端)。
- **风险**: subscribe_hq 推送**可能**含十档/逐笔 (TdxQuant 官方宣称支持L2), 但未证实; 也可能仅五档快照。
- **处置**: 标记 `NOT_TESTED_RUNTIME`, 留作**非交易时段**(收盘后/周末)执行验证。验证前不得宣称 TdxQuant 能拿十档/逐笔。

### R5. WeStock 竞价期不可信
- **事实**: 集合竞价阶段 WeStock 价格/成交量滞后 (R1 深市 volume=0, 价差>0.4%)。
- **风险**: 用 WeStock 做竞价期信号会失真。
- **处置**: WeStock 仅用于连续竞价交叉验证, 竞价期不采信。

### R6. 本地文件半条记录风险
- **事实**: 未发现 .l2d/.tick, 仅 hq_cache 压缩缓存; 压缩格式为 TDX 专有, 解码需官方库。
- **风险**: 若误读压缩缓存, 存在半条记录/格式错位风险。
- **处置**: 不解析压缩缓存, 标记 `LOCAL_FILE_VERIFIED`(仅监控不解析)。

## 未知 (UNKNOWN)

1. **tqcenter subscribe_hq 推送内容**: 是否含十档? 是否含逐笔? → 非交易时段验证。
2. **InOutHB 精确语义**: 撤买? 沪比? 委托净额? → 查官方/公式编辑器。
3. **HQMaskFlag 各位含义**: → 查官方。
4. **CasUpperPx / CasImbVol**(指数, 极小浮点): 集合竞价失衡量? → 待确认。
5. **TdxQuant 是否有未公开 L2 函数**: 静态枚举仅公开方法, 可能有内部/未文档化接口 → 非交易时段深挖。
6. **09:15–09:24 段**: 本会话未覆盖 (任务下发时已过), 不补造。

## 下一步建议
1. **收盘后(非交易时段)**: 执行 tqcenter 运行时验证 (get_market_snapshot + subscribe_hq 推送内容抓取), 确认十档/逐笔可达性。
2. **若 TdxQuant 仍无逐笔**: 评估 eltdx (pip install, TCP直连) 或 TdxQuant 量化版客户端。
3. **语义确认**: 用 TDX 公式编辑器查 L2_AMO / 总撤买 / 总撤卖 公式定义, 对齐 InOutHB 语义。
4. **连续追加轮次**: 10:00 前可继续 append R5/R6 到 jsonl, 框架已就绪。
