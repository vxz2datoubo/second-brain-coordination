# 波仔量化交易系统 · 全貌文档 v1.0

> **用途**: 供 Codex/智能体 理解整个交易系统的全貌，便于整合、升级为完整量化系统。
> **对标**: 文艺复兴大奖章基金方法论 × A股T+1制度适配
> **股票**: 昆仑万维(300418) + 蓝色光标(300058)
> **最后更新**: 2026-07-03 (22:30)

---

## 一、系统全景

```
                    ┌─────────────────────────────────┐
                    │     runner.py (统一入口 v3)       │
                    │  premarket / intraday / after     │
                    └──────────────┬──────────────────┘
           ┌──────────────────────┼──────────────────────┐
    ┌──────▼──────┐  ┌───────────▼───────┐  ┌───────────▼───────┐
    │ strategies/ │  │    engine/        │  │     risk/         │
    │ 28个策略模块 │  │ 数据+指标+回测+可视化│  │  仓位管理+熔断     │
    └──────┬──────┘  └───────────┬───────┘  └───────────┬───────┘
           │                     │                       │
    ┌──────▼─────────────────────▼───────────────────────▼──────┐
    │                    数据层                                 │
    │  neodata(WB金融skill) + tdx-connector(MCP) + 通达信本地文件 │
    └───────────────────────────────────────────────────────────┘
```

### 当前状态
- **v3 已实现**: runner.py 统一入口 + Engine A 趋势分类 + 量价效率 + 主力筹码 + 动能PK + 情绪追踪 + 新闻监控 + 换手率分析
- **v4 已设计**: 6因子信号管道 + 市场状态5分类 + 3槽节奏控制器 + 双股联合组合 + 自适应学习 (见 `daytrade_system/TRADING_SYSTEM_V4.md`)
- **v4 待实现**: `medallion/` 目录下的12个新模块（详见路线图）
- **99天回测**: 已跑通300418和300058的全量数据回测 + 可视化

---

## 二、文件地图（关键入口）

```
F:/aidanao/
├── daytrade_system/              ← 核心交易系统
│   ├── runner.py                 ← 【入口】盘前/盘中统一入口
│   ├── config.py                 ← 所有可调参数
│   ├── TRADING_RULES.md          ← 做T操作手册
│   ├── TRADING_SYSTEM.md         ← 系统架构总纲 v1
│   ├── TRADING_SYSTEM_V4.md      ← 大奖章级设计 v4（待实现）
│   ├── strategies/               ← 28个策略模块
│   ├── engine/                   ← 引擎(数据/指标/信号/回测/可视化)
│   ├── risk/                     ← 风控(仓位管理+熔断)
│   ├── scripts/                  ← 回测/验证脚本
│   │   ├── run_backtest.py
│   │   ├── run_full_backtest.py  ← 99天全量回测
│   │   ├── run_verify.py         ← 300418全程验证
│   │   └── run_verify_300058.py  ← 300058全程验证
│   └── output/                   ← 报告+JSON快照+HTML图表
│
├── .workbuddy/memory/MEMORY.md   ← 交易规则(闭环学习)
├── data/                         ← 知识图谱+持仓数据
├── reports/                      ← 分析报告HTML
└── scripts/                      ← 辅助脚本(解析/回测)
```

---

## 三、核心策略模块速查

### 3.1 趋势与市场状态

| 模块 | 文件 | 功能 |
|------|------|------|
| 趋势判定器 | `strategies/trend_classifier.py` | Engine A: 4状态(强涨/强跌/震荡/低波)，决定策略开关+T仓允许/禁止+仓位系数 |
| 日线分析 | `strategies/daily_analyzer.py` | 连阳/均线/量比/影线信号 |
| 情绪追踪 | `strategies/sentiment_tracker/` | 5层模型(L1-L5)综合输出-100~+100情绪分 |

### 3.2 量价与筹码

| 模块 | 文件 | 功能 |
|------|------|------|
| 量价效率 | `strategies/volume_efficiency.py` | 效率 = Delta成交量% / Delta价格%，>3.0=硬阻力，<1.0=软阻力 |
| 量价剖面 | `strategies/volume_profile.py` | 5日5分钟K统计成交量密集区，合并为支撑/压力带 |
| 穿越修正 | `strategies/crossover_tracker.py` | 评估上次穿越成本，修正系数0.7~1.3，过滤虚假阻力 |
| 入市评分卡 | `strategies/entry_scorer.py` | 4维共振(量价30%+资金30%+情绪20%+板块20%)，绿灯>5/黄灯3-4/红灯<3 |
| 筹码分析 | `strategies/chip_analyzer.py` | 18个月4阶段主力行为(建仓→洗盘→拉升→出货)，成本区定位 |
| 动能分析 | `strategies/momentum_analyzer.py` | 5维评分(日内强度+涨速+VWAP+量价+买卖压力) |
| 阻力PK | `strategies/resistance_pk.py` | 动能分 vs 修正阻力，穿越胜率预估(>60%=绿/35-60%=黄/<35%=红) |

### 3.3 信号与执行

| 模块 | 文件 | 功能 |
|------|------|------|
| 倒T引擎 | `strategies/reverse_t_engine.py` | 3槽状态机(EMPTY/SHORT/LONG/DONE)，五重过滤入场 |
| 换手分析 | `strategies/turnover_analyzer.py` | 5维联动(阶段+量质+突破+周期+次日预测) |
| 竞价裁判 | `strategies/auction_judge.py` | 6维评分(匹配量+价格趋势+关联股+昨日资金+量价位置+板块情绪) |
| 跨日追踪 | `strategies/cross_day_tracker.py` | JSON持久化未平仓位，次日开盘加载+低开高开判断 |
| 新闻监控 | `strategies/news_monitor.py` | 价格>3%/10min触发，利好分3级，卖点上移30-50% |

### 3.4 板块与多股

| 模块 | 文件 | 功能 |
|------|------|------|
| 板块扫描 | `strategies/sector_scanner.py` | 关联小票池(昆仑5只/蓝标8只)，涨停检测 |
| 板块热度 | `strategies/sector_heat.py` | 通达信API查询AI/传媒题材热度 |
| 板块联动 | `strategies/sector_watch.py` | 关联股同步性判断 |

### 3.5 引擎层

| 模块 | 文件 | 功能 |
|------|------|------|
| 数据加载 | `engine/data_loader.py` | MCP JSON → KBar/QuoteSnapshot |
| TDX解析 | `engine/tdx_parser.py` | 直接读.day/.lc5/.lc1二进制，免API |
| 指标计算 | `engine/indicators.py` | SMA/EMA/布林/ATR/MACD/RSI/VWAP+σ/Keltner/支撑压力/CDV/背离 |
| 信号生成 | `engine/signals.py` | 正T/倒T多维度检测，0-100适宜度评分 |
| 回测引擎 | `engine/backtest.py` | 逐日回测+趋势过滤+3出场条件+尾盘强平 |
| 可视化 | `engine/visualize.py` | ECharts HTML: K线+VWAP+σ带+RSI+CDV+信号标注 |

---

## 四、数据基础设施

### 4.1 数据源层次

| 优先级 | 来源 | 协议 | 覆盖 |
|--------|------|------|------|
| 1 | neodata-financial-search | HTTP API (WB Skill) | A/港/美股实时+历史行情、资金流向、板块、宏观 |
| 2 | tdx-connector MCP | MCP stdio | 通达信本地K线(日/5分/1分)、实时行情、选股、资讯 |
| 3 | 通达信本地文件 | 二进制直接读 | .day(日K) / .lc1(1分钟) / .lc5(5分钟)，免API |

### 4.2 关键API端口

```
neodata:    https://copilot.tencent.com/agenttool/v1/neodata (鉴权: Bearer)
tdx MCP:    mcp__tdx-connector__tdx_kline / tdx_quotes / tdx_screener 等
第二大脑:   localhost:8766/api/retrieve/search / api/digest/text
```

### 4.3 关联股票池

```
昆仑万维(300418) ← 科大讯飞(002230) 三六零(601360) 恺英网络(002517) 三七互娱(002555) 世纪华通(002602)
蓝色光标(300058) ← 分众传媒(002027) 省广集团(002400) 天娱数科(002354) 福石控股(300071) 奥飞娱乐(002292)
```

---

## 五、交易规则完整清单

### 5.1 仓位铁律
- 底仓97%长线不动，T仓3%每日最多2-3笔
- 单笔上限 5000元 (100股整数倍)
- 单日亏损熔断 >2% 全天停止
- 连续亏损2笔 降为1槽
- 卖出后30分钟冷却期

### 5.2 每日操作窗口

| 窗口 | 时间 | 策略 |
|------|------|------|
| T1 开盘处理 | 09:30-09:50 | 竞价分析，优先接回跨日仓位 |
| T2 黄金窗口 | 09:50-10:30 | 方向确认后首笔倒T |
| T3 上午延续 | 10:30-11:00 | 方向选择 |
| T4 谨慎期 | 11:00-11:30 | 仅强信号才执行 |
| T5 下午重启 | 13:00-13:30 | 第二反转窗口 |
| T6 下午黄金 | 13:30-14:00 | 倒T黄金窗口 |
| T7 尾盘决策 | 14:00-14:30 | 判断是否还有机会 |
| T8 强制收尾 | 14:30-15:00 | 未接回T仓全部强平 |

### 5.3 倒T卖飞处理
- 涨超卖出价3% → 等回落1%形成支撑 → 追回
- 追回后冷却20分钟不新卖
- 若有利好消息 → 先查新闻再决定追回价

### 5.4 🔴 硬规则 (闭环学习)

**规则1: 新闻突袭处理 (7/2)**
- 盘中涨幅>5%或振幅>8% → 自动查新闻
- 消息分级(里程碑/重要/一般) → 卖点调整(上移50%/30%/10%)
- 底仓不动，不受T仓操作影响

**规则2: 追涨次日判定 (7/3)**
- 昨日涨>8%+放量>2倍 → 今日标记"需验证日"
- 竞价低开>1.5% → 降T仓50%
- 30分钟不翻红 → T仓全清，全天禁买
- 评判: 利好一次性定价 + 接力失败

**规则3: 卖出后等待规则**
- 卖出后至少30分钟不接回
- 让股价走完路径再判断
- 禁止1分钟内接回 (7/3教训: 46.45卖→45.81接亏掉全天利润)

**规则4: 追涨次日反T禁止**
- 重大消息日次日只卖不买
- 禁止抄底，禁止正T
- 只保留底仓，T仓当日不操作

---

## 六、历史回测核心结论

### 6.1 低开急拉深跌模式 (7/3回测)
- 一年内12个相似日
- 日内反弹概率: 92% (平均+3.6%)
- 次日上涨概率: 42% (均值-0.7%)
- 反转时间窗口: 10:15-10:45(第一) / 13:00-13:30(第二) / 14:00-14:30(尾盘)

### 6.2 斐波那契反弹
- 38.2%反弹 → 历史达成率58%
- 50.0%反弹 → 达成率42%
- 61.8%反弹 → 达成率33%

### 6.3 量价效率有效性
- 效率>3.0x的硬阻力 → 做倒T胜率85%+
- 效率<1.0x的软阻力 → 做倒T胜率<40%
- 结论: 只在硬阻力位做倒T

---

## 七、v4 大奖章级升级路径

### 7.1 待实现的 medallion/ 模块

| 模块 | 功能 | 优先级 |
|------|------|--------|
| `regime_clf.py` | 5种市场状态分类器 (TREND_UP/DOWN/HIGH_VOL/LOW_VOL/EXTREME) | P0 |
| `signal_pipeline.py` | 6因子信号管道 (VWAP/RSI/VolProfile/Momentum/Delta/Gap) | P0 |
| `slot_controller.py` | 3槽节奏控制器 (状态机+决策树+优先级) | P0 |
| `execution_scheduler.py` | 限价单调度 + 滑点控制 + 5分钟超时重挂 | P1 |
| `cross_day.py` | 跨日仓位管理升级版 | P1 |
| `statistics_book.py` | 每笔交易信号分+盈亏记录，用于因子权重优化 | P1 |
| `adaptive_tuner.py` | 每周自动调参 (因子权重+阈值+时间窗口) | P2 |
| `portfolio_controller.py` | 双股联合控制 (60/40配比+动态再平衡+相关性决策) | P2 |
| `live_runner.py` | 生产环境运行入口 | P1 |
| `backtest_medallion.py` | 基于新架构的全量回测引擎 | P0 |

### 7.2 6因子的信号管道

```
F1: VWAP Extreme Deviation (权重25%) - 价格在VWAP 2σ外的偏离度
F2: RSI Mean-Reversion (权重20%)     - RSI(6)超买/超卖 + 市场情绪锚定
F3: Volume Profile Pressure (权重20%) - 5日量价分布的压力/支撑确认
F4: Momentum Decay (权重15%)          - 3根5分K连续递减判动量衰竭
F5: Intraday Cumulative Delta (10%)  - 主动买卖累积Delta，极值反转
F6: Cross-Day Gap (权重10%)          - 开盘跳空判断(高开假突破/低开恐慌底)
```

### 7.3 复用现有模块
- `engine/indicators.py` → 全部基础指标
- `risk/position_manager.py` → 仓位约束+冷却期
- `strategies/cross_day_tracker.py` → 跨日持久化
- `strategies/reverse_t_engine.py` → 槽位状态机基础

### 7.4 实施路线
```
Phase 1: base framework + 6-factor signal pipeline + backtest (P0)
Phase 2: execution scheduler + slot controller (P1)
Phase 3: regime classifier + adaptive tuner (P2)
Phase 4: dual-stock portfolio controller (P2)
Phase 5: live production + daily dashboard (P1)
```

---

## 八、心理纪律与行为规则

### 8.1 你的交易性格
- 优势: 耐心、不冲动追高、敢于急跌抄底
- 弱点: 卖点贪心、止损犹豫、卖飞后情绪化操作
- 应对: 系统强制规则 > 自由裁量；别把T仓盈亏当总资产盈亏

### 8.2 T仓心理锚定
```
T仓占总资产仅3%
T仓亏2% → 总资产影响仅0.06%
不值得为T仓亏损焦虑或频繁操作
```

### 8.3 禁止行为
- ❌ 卖了立刻接回（至少等30分钟）
- ❌ 盘中追涨买入
- ❌ 同一天三进三出
- ❌ 在重大消息日次日做正T抄底

---

## 九、第二大脑集成

### 9.1 当前集成
- 第二大脑 (localhost:8766) 存储决策教训、知识图谱
- MEMORY.md 存储硬规则（每次闭环学习后更新）
- 每日工作日志 (.workbuddy/memory/YYYY-MM-DD.md) 记录交易

### 9.2 待集成
- 实时持仓同步到第二大脑知识图谱
- 交易信号与第二大脑的 decision-lessons 节点联动
- 自动化每日盘后总结摄入

---

## 十、对 Codex 的说明

### 你的任务
读取本文件，理解整个系统的全貌，然后用你的能力**整合、升级、补全** v4 大奖章级交易系统。

### 关键约束
1. **复用现有模块**，不重复造轮子。`engine/indicators.py` 和 `risk/position_manager.py` 已经写得很好。
2. **保持与 runner.py 的兼容**。新增功能通过 runner.py 的新模式暴露。
3. **数据源走 neodata 或 tdx-connector MCP**，不要另起炉灶。
4. **每完成一个 Phase，输出一个可运行的 `.py` 文件** + 对应的测试。
5. **遵循 TRADING_SYSTEM_V4.md 的设计规范**。
6. **A股语境**: 红涨绿跌、T+1制度、100股单位。

### 建议的优先顺序
```
1. medallion/config.py       ← 所有参数集中管理（已有 config.py 可参考）
2. medallion/regime_clf.py   ← 市场状态分类（最关键的上游模块）
3. medallion/signal_pipeline.py ← 6因子信号管道（核心引擎）
4. medallion/backtest_medallion.py ← 回测验证（边写边测）
5. medallion/slot_controller.py ← 接着补齐执行层
```

---

_由 迪迪 编译于 2026-07-03 22:30_
_供 Codex 参考，作为构建大奖章级量化交易系统的蓝图_
