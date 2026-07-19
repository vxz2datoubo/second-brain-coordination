# 第二大脑交易系统 · 大奖章级设计 v4.0

## 1. 核心定位
目标：建立以**统计套利 + 信号堆叠 + 自适应执行**为核心的专业倒T交易系统，
对标文艺复兴大奖章基金方法论，适配中国A股T+1制度、每股票日最多3笔各5000、可跨日的约束条件。

## 2. 系统架构 === 6层金字塔

Layer 6: 自适应学习层 (Adaptive Learning)      ← 每周末自动调参
Layer 5: 统计信号层 (Statistical Signals)    ← 6因子打分融合
Layer 4: 执行优化层 (Execution Optimization)  ← 限价单调度 + 滑点控制
Layer 3: 仓位节奏层 (Slot Rhythm)            ← 3槽优先级 + 时间窗口
Layer 2: 市场状态层 (Regime Classification)  ← 5种市场状态
Layer 1: 数据基础层 (Data Foundation)        ← 继承 indicators.py

## 3. 项目文件布局

daytrade_system/
  medallion/
    __init__.py
    config.py          ← 所有可调参数集中管理
    regime_clf.py      ← 市场状态分类器
    signal_pipeline.py  ← 6因子信号管道
    slot_controller.py ← 3槽仓位节奏控制器
    execution_scheduler.py ← 分批执行调度器
    cross_day.py       ← 跨日仓位管理（升级版）
    statistics_book.py  ← 统计簿：跟踪每笔交易信号与结果
    adaptive_tuner.py  ← 自适应调参器
    portfolio_controller.py ← 双股联合控制
    live_runner.py      ← 生产运行入口
    backtest_medallion.py ← 回测引擎
    dashboard.py        ← 监控面板生成

## 4. 市场状态分类器 (RegimeClassifier)

将每日分为 5 种市场状态，决定系统整体参数：

| Regime | 特征 | T仓策略 |
|--------|------|---------|
| TREND_UP   | 5日均线多头 + 连续上涨 | 少做倒T，多持有 |
| TREND_DOWN | 5日均线空头 + 连续下跌 | 逆T为主（接更多） |
| HIGH_VOL_RANGE | 振幅>5% + 无明显趋势 | 倒T黄金窗口 |
| LOW_VOL_RANGE  | 振幅<2% + 盘整 | 降低频率，只做A级 |
| EXTREME    | 涨跌停/黑天鹅/异常波动 | 全停，保护底仓 |

判定特征向量：
  - 过去5日ATR与历史的比值 (vol_ratio)
  - 日内振幅 vs 预期振幅 (range_ratio)
  - 5日均线方向 (ma5_slope)
  - 涨跌家数比 (marketBreadth)
  - 过去10日系统胜率 (winRateTrend)

## 5. 六个独立信号因子

每个因子独立输出 score ∈ [0, 100]：

### F1: VWAP Extreme Deviation (权重 25%)
- 价格在VWAP 2σ上方 → 卖信号 = min(100, (price-VWAP)/σ × 30)
- 价格在VWAP 2σ下方 → 买信号 = min(100, (VWAP-price)/σ × 30)
- 附加：VWAP上升趋势中的卖信号 +10分（动量延续）
- 附加：VWAP下降趋势中的买信号 +10分（反弹概率大）

### F2: RSI Mean-Reversion (权重 20%)
- RSI(6) > 75 → 卖信号 = (RSI - 75) × 5 (最高100)
- RSI(6) < 25 → 买信号 = (25 - RSI) × 5 (最高100)
- 市场情绪锚定：用沪深300的RSI调整阈值
  （市场极热时，个股在RSI 85才触发；市场极冷时，RSI 65即触发）

### F3: Volume Profile Pressure (权重 20%)
- 计算当日量价分布，识别当前价格是否在"高量区域"（大量成交的价位）
- 在高量高价区卖出 + 在低量低价区买回 = 最优倒T
- 具体：统计最近5日每档价格区间的成交量分布
- 当前价格所在区间成交占全天 > 30% → 卖信号 + 压力确认
- 目标接回价位：当日成交量最集中的支撑带

### F4: Momentum Decay (权重 15%)
- 最近3根5分K逐根递减（close[i] < close[i-1] 连续3次）
  → 动量衰竭 → 卖信号 +50分
- 最近3根5分K逐根递增后出现第一根下跌
  → 顶部结构 → 卖信号 +40分
- 附加：当日价格已从日内高点回撤 > 50% 的止损位
  → 卖信号 +30分（防止卖在最低点）

### F5: Intraday Cumulative Delta (权重 10%)
- 累积Delta = Σ((close-low)/(high-low) - 0.5) × volume
  （正值 = 主动买入主导，负值 = 主动卖出主导）
- Delta从正转负且绝对值放大 → 卖信号
- Delta触及极值（超过历史95分位）→ 反转概率极高 → 卖信号

### F6: Cross-Day Gap (权重 10%)
- 开盘跳空判断：
  高开 > 1%：若成交量放大 → 假突破概率高 → 卖信号
  低开 > 1%：若成交量缩量 → 恐慌见底概率高 → 买信号
- 缺口是否当天回补？
  未补缺口 = 趋势延续方向
  已补缺口 = 反转概率高（适合倒T）

## 6. 信号融合

加权平均：score = Σ wi × Fi
初始权重：w = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]

动态权重调整（每周）：
  用最近20笔交易的 (信号分, 盈亏) 做Pearson相关
  相关性 > 0.3 的因子权重 ×1.05（+5%）
  相关性 < 0.1 的因子权重 ×0.90（-5%）
  归一化后总权重 = 1.0

## 7. 置信度分级与执行策略

| 置信度 | 分数区间 | 执行策略 |
|--------|---------|---------|
| A++ | 90-100 | 立即执行，立即挂限价单 |
| A   | 75-89  | 正常执行，等回调0.3%再挂 |
| B   | 60-74  | 可执行，降低预期，限额1笔/天 |
| C   | 45-59  | 仅当无其他机会时备选 |
| D   | < 45   | 不执行 |

## 8. 时间切片执行窗口

| 窗口 | 时间 | 策略重点 |
|------|------|---------|
| T1   | 9:30-9:50 | 开盘处理：优先接回跨日仓位。高开/低开判断后决定是否立刻行动 |
| T2   | 9:50-10:30 | 黄金窗口：方向确认后执行首笔倒T。追买/追卖都要等 |
| T3   | 10:30-11:00 | 上午延续：继续看倒T机会，特别是10:30附近的方向选择 |
| T4   | 11:00-11:30 | 谨慎期：除非强信号，否则等待 |
| T5   | 13:00-13:30 | 下午重启：观察下午是否有新方向 |
| T6   | 13:30-14:00 | 下午黄金窗口：最易出倒T机会 |
| T7   | 14:00-14:30 | 尾盘决策：判断当天是否还有T仓机会 |
| T8   | 14:30-15:00 | 强制收尾：所有未接回的T仓全部强平 |

槽位优先级（在T2/T6黄金窗口优先开启新槽）：
  槽1 > 槽2 > 槽3（按顺序开启，但允许选择性跳过差的信号）

## 9. 仓位节奏控制器 (SlotController)

### 槽位状态机
状态：EMPTY / SHORT_PENDING / SHORT_FILLED / LONG_PENDING / LONG_FILLED / DONE

### 卖出决策树
对于每个空槽：
1. 当前Regime是否允许开仓？
   EXTREME → 否 | LOW_VOL → 仅A++ | 其他 → B级以上

2. 冷却期检查：卖出后30分钟冷却（已有position_manager）

3. 信号过滤：
   if signal_confidence >= B_THRESHOLD:
       执行卖出
   else:
       等待更好的信号

### 接回决策树（倒T）
对于每个SHORT_FILLED槽：
1. 价格回到卖出价 → 立即接回
2. 价格回撤超过0.3%但未到卖出价 → 视情况接回
3. 价格继续上涨超过卖出价1% → 若为跨日仓位 → 止损接回
4. 14:50前未接回 → 强制接回

### 槽位优先级（3个槽如何分配）
- 跨日槽优先接回（已持有过夜）
- 当日槽：信号最强时开启第1槽，最强+5分才开启第2槽

## 10. 执行调度器 (ExecutionScheduler)

### 限价单策略
- 基准价 = 当前价
- 卖出挂单：基准价 - 1 tick（买入倾向）
- 买回挂单：基准价 + 1 tick（买入挂高一点）
- 若5分钟未成交：检查信号是否仍有效
  - 有效 → 撤单重挂（调整1个tick）
  - 无效 → 取消该笔

### 5000元/笔的处理
`python
shares = floor(5000 / current_price / 100) * 100
# 确保100股整数倍，A股最小交易单位100股
`

### 跨日仓位特殊处理
- 跨日槽接回优先级：> 当日新开槽
- 跨日槽若开盘大跌（> 1%）→ 立即接回（锁定利润）
- 跨日槽若开盘大涨（> 1%）→ 等待回落到开仓价附近再接

## 11. 自适应学习层 (Adaptive Learning)

### StatisticsBook 统计簿
每笔交易记录：
`json
{
  "date": "2026-07-03",
  "stock": "300418",
  "entry_time": "10:15",
  "exit_time": "13:42",
  "direction": "short",
  "entry_price": 44.50,
  "exit_price": 44.00,
  "profit_pct": 1.12,
  "signal_scores": {"F1": 85, "F2": 70, "F3": 60, "F4": 45, "F5": 80, "F6": 0},
  "total_signal": 73,
  "regime": "high_vol_range",
  "time_window": "T2",
  "was_carried": false,
  "cooldown_observed": true
}
`

### Adaptive Tuner（每周运行）
1. 对过去20笔交易的因子分和盈亏做相关性分析
2. 调整因子权重
3. 调整置信度阈值
4. 调整时间窗口权重（T2/T6可能更有效）
5. 生成调参报告

## 12. 双股联合 PortfolioController

### 资金分配
- 昆仑60% / 蓝色40%（基于波动率倒数调整）
- 动态再平衡：每周将盈利的50%转入表现更好的股票
- 底仓比例不低于初始的70%（保护长期配置）

### 相关性决策
- 昆仑与蓝色联动分析：
  同涨 → 优先在涨幅更大的那只做倒T
  分化 → 弱的那只做正T，强的那只做倒T
  同跌 → 评估系统性风险，必要时停止T仓

### 总卖出笔数约束
- 两股每日合计最多3笔卖出
- 优先级：信号更强的股票优先使用卖出额度
- 若两股信号相同：优先昆仑（流动性更好）

## 13. 风控体系（扩展已有）

| 风控 | 规则 | 触发后果 |
|------|------|---------|
| 硬止损 | 单笔亏损 > 2% | 无条件平仓 |
| 熔断 | 每日累计 > 2% | 全天停止 |
| 冷却期 | 卖出后30分钟 | 不能卖出 |
| 连亏降仓 | 连亏2笔 | 降为1个槽 |
| 极端行情 | Regime=EXTREME | 所有T仓平掉 |
| 黑天鹅 | 跌破20日线8% | 立即平所有T仓 |
| 信号消失 | 卖出后信号由A降至D | 取消未成交单 |

## 14. 与现有系统关系

复用部分：
- indicators.py：所有基础指标计算
- position_manager.py：仓位约束 + 冷却期
- cross_day_tracker.py：跨日仓位持久化
- reverse_t_engine.py：槽位状态机的基础设计

新写部分：
- medallion/config.py
- medallion/regime_clf.py
- medallion/signal_pipeline.py
- medallion/slot_controller.py
- medallion/execution_scheduler.py
- medallion/cross_day.py
- medallion/statistics_book.py
- medallion/adaptive_tuner.py
- medallion/portfolio_controller.py
- medallion/live_runner.py
- medallion/backtest_medallion.py
- medallion/dashboard.py

## 15. 实施路线图

Phase 1: 基础框架 + 6因子信号管道 + 回测
Phase 2: 执行调度器 + 槽位控制器
Phase 3: 市场状态分类 + 自适应调参
Phase 4: 双股联合控制器
Phase 5: 生产运行 + 每日仪表盘

## 16. 关键假设

1. 通达信数据延迟 ≤ 5秒（足够5分K决策）
2. A股T+1下倒T卖后资金当日可用于买回（5000/笔 < 当日卖出底仓市值）
3. 每日最多3笔卖出（硬约束）
4. 每笔5000元
5. 昆仑日均振幅 > 3% 时系统最有效
6. 蓝色日均振幅 > 2% 时系统最有效