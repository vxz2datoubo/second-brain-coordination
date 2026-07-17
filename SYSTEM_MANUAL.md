# 波仔量化交易系统 — 完整系统手册
版本: 2026-07-04 | v1.0

> **用途**: 供任何AI工具无缝接管整个交易系统
> **维护**: 所有AI共享，每次交接必须读取

---

## 一、系统架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                    波仔量化交易系统 v4                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │   AGENTS.md │ ──> │  second-brain │ ──> │ daytrade_system │  │
│  │  (架构入口)  │     │   (知识库)    │     │   (交易引擎)    │  │
│  └─────────────┘     └──────────────┘     └─────────────────┘  │
│         │                   │                      │            │
│         └───────────────────┼──────────────────────┘            │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    MCP 桥接层 (mcp/)                        ││
│  │  tdx_live_bridge.py  │  tdx_bridge.py  │  brain_bridge.py  ││
│  └─────────────────────────────────────────────────────────────┘│
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    数据源 (三层)                             ││
│  │  1. 通达信官方MCP (txmcp.tdx.com.cn:3001)                   ││
│  │  2. 通达信本地二进制 (F:/tongdaxin/vipdoc/)                 ││
│  │  3. WorkBuddy neodata skill (HTTP API)                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、AI交接协议

任何AI工具接管时，**必须按顺序**读取以下文件：

### 必读文件清单

| 顺序 | 文件 | 说明 |
|------|------|------|
| 1 | `AGENTS.md` | 本文件，了解系统架构 |
| 2 | `second-brain/rules.md` | 获取最新交易规则 |
| 3 | `second-brain/lessons.md` | 获取历史教训 |
| 4 | `second-brain/daily_log.md` | 查看近期交易日志 |
| 5 | `daytrade_system/TRADING_SYSTEM_BLUEPRINT.md` | 完整设计蓝图 |
| 6 | `daytrade_system/medallion/config.py` | 当前参数配置 |

### 快速了解（5分钟）

若时间紧迫，只需读取：
1. `AGENTS.md` 第2节"核心参数"
2. `second-brain/rules.md` 第1-3节
3. `second-brain/lessons.md` 最新3条教训

---

## 三、核心概念

### 3.1 T仓交易
- **定义**: 日内买卖同一只股票，当日回笼资金
- **倒T**: 先卖出持仓，等跌再买回（利用冲高卖出）
- **正T**: 先买入，等涨再卖出（利用回调买入）
- **本系统**: 倒T优先，正T谨慎

### 3.2 目标股票
| 代码 | 名称 | 概念 | 风格 | 权重 |
|------|------|------|------|------|
| 300418 | 昆仑万维 | AI+游戏 | 趋势跟随 | 60% |
| 300058 | 蓝色光标 | 营销+AI | 逆势抄底 | 40% |

### 3.3 6因子信号系统

| 因子 | 名称 | 说明 |
|------|------|------|
| F1 | VWAP偏离 | 价格在VWAP 2σ外的偏离度 |
| F2 | RSI极值 | RSI超买/超卖 + 市场情绪锚定 |
| F3 | 量价剖面 | 5日量价分布的压力/支撑确认 |
| F4 | 动量衰竭 | 3根5分K连续递减判动量衰竭 |
| F5 | Delta转向 | 累积主动买卖，极值反转 |
| F6 | 隔夜缺口 | 开盘跳空判断 |

### 3.4 市场状态（5种）

| 状态 | 说明 | 操作策略 |
|------|------|----------|
| TREND_UP | 上升趋势 | 减少做T，持有底仓 |
| TREND_DOWN | 下跌趋势 | 倒T为主，控仓 |
| HIGH_VOL_RANGE | 高波动震荡 | 做T黄金期，积极操作 |
| LOW_VOL_RANGE | 低波动震荡 | 减少操作，仅强信号执行 |
| EXTREME | 极端行情 | 全天停止，所有仓位平掉 |

---

## 四、交易规则摘要

### 4.1 仓位约束
```
单笔金额: 5000元 (±1000)
单日上限: 3笔T仓
总持仓: ≤90%，保持≥10%现金
熔断线: 日亏>2% 全天停止
```

### 4.2 时间窗口
```
09:30-09:50  开盘处理（优先接回跨日仓位）
09:50-10:30  ★ 黄金窗口1（倒T首选）
10:30-11:00  上午延续
11:00-11:30  谨慎期
13:00-13:30  下午重启
13:30-14:00  ★ 黄金窗口2（倒T首选）
14:00-14:30  尾盘决策
14:30-15:00  强制收尾（未接回T仓强平）
```

### 4.3 置信度等级
```
A++ (≥90分): 立即执行，限1笔/天
A   (≥75分): 正常执行，等回调0.3%再挂
B   (≥60分): 可执行，限额1笔/天
C   (≥45分): 仅备选，谨慎执行
D   (<45分): 不执行
```

---

## 五、文件地图

### 5.1 核心目录结构

```
F:/aidanao/
├── AGENTS.md                          # 系统入口（必读）
├── SYSTEM_MANUAL.md                   # 本文件（AI完整手册）
├── server.py                          # 第二大脑HTTP服务
│
├── second-brain/                      # ★ 第二大脑知识库
│   ├── rules.md                       # 交易规则库（每日更新）
│   ├── lessons.md                     # 历史教训库
│   └── daily_log.md                   # 每日交易日志
│
├── core/                              # 核心算法
│   ├── graph.py                       # 知识图谱引擎
│   ├── fast_index.py                  # BM25F融合索引
│   ├── decision_consult.py            # 决策前自检
│   ├── evolve.py                      # 进化引擎
│   ├── self_verify.py                 # 自验证引擎
│   ├── digest.py                      # 知识消化
│   ├── memory.py                      # 记忆引擎
│   └── ...
│
├── daytrade_system/                   # 日内交易系统
│   ├── runner.py                      # 统一入口
│   ├── config.py                      # 参数配置
│   ├── engine/                        # 引擎层
│   │   ├── data_loader.py             # 数据加载
│   │   ├── indicators.py              # 指标计算
│   │   ├── signals.py                 # 信号生成
│   │   └── backtest.py                # 回测引擎
│   ├── strategies/                    # 28个策略模块
│   │   ├── reverse_t_engine.py        # 倒T引擎
│   │   ├── trend_classifier.py        # 趋势分类
│   │   ├── volume_efficiency.py       # 量价效率
│   │   └── ...
│   ├── medallion/                     # ★ v4核心模块
│   │   ├── config.py                  # 股票配置
│   │   ├── signal_pipeline.py         # 6因子信号管道
│   │   ├── regime_clf.py              # 市场状态分类
│   │   ├── slot_controller.py         # 槽位控制器
│   │   └── ...
│   ├── live/                          # 实盘引擎
│   │   ├── live_engine.py             # 实盘运行
│   │   ├── tdx_mcp_client.py          # TDX MCP客户端
│   │   └── trade_logger.py            # 交易日志
│   ├── risk/                          # 风控
│   │   └── position_manager.py        # 仓位管理
│   └── output/                        # 回测输出
│
├── mcp/                               # MCP桥接层
│   ├── tdx_live_bridge.py             # 通达信官方MCP桥
│   ├── tdx_bridge.py                  # 通达信本地桥
│   └── brain_bridge.py                # 第二大脑桥
│
└── data/                              # 数据目录
    ├── knowledge-graph.json           # 知识图谱
    └── ...
```

### 5.2 关键入口

| 入口 | 命令 | 说明 |
|------|------|------|
| 第二大脑服务 | `python F:/aidanao/server.py` | 启动HTTP服务，端口8766 |
| 日内回测 | `python F:/aidanao/daytrade_system/runner.py --stock 300418 --days 99` | 99天回测 |
| MCP桥接 | `python -u F:/aidanao/mcp/tdx_live_bridge.py` | 启动MCP stdio桥 |

---

## 六、MCP工具速查

### 6.1 通达信MCP (tdx_live_bridge.py)

```json
tdx_realtime  {"code": "300418"}     // 实时行情
tdx_kline     {"code":"300418","period":"5m","count":100}  // K线
tdx_lookup    {"query": "昆仑"}       // 搜索股票
tdx_news      {"keyword": "AI","limit":5}  // 新闻资讯
tdx_notice    {"code":"300418","limit":3}  // 公告
tdx_screener  {"query":"AI概念","limit":10}  // 条件选股
```

### 6.2 第二大脑API

```json
POST /api/retrieve/search   // 搜索知识库
POST /api/digest/text       // 添加文本知识
GET  /api/stats             // 系统统计
GET  /api/knowledge-graph   // 获取完整图谱
POST /api/evolve/evaluate   // 执行进化评估
GET  /api/evolve/report     // 获取进化报告
```

---

## 七、自进化机制

### 7.1 进化层次

| 层级 | 周期 | 动作 |
|------|------|------|
| 日级 | 每日收盘 | 记录日志、分析当日教训 |
| 周级 | 每周五 | 进化引擎分析教训，更新规则 |
| 月级 | 每月末 | 自检验验证胜率，更新参数 |

### 7.2 进化触发条件

| 条件 | 动作 |
|------|------|
| 连续3日盈利 | 考虑加仓10% |
| 连续2日亏损 | 触发减仓至1槽 |
| 连亏3笔 | 全天停止交易 |
| 某因子胜率<40% | 自动降低该因子权重 |
| 某因子胜率>70% | 自动提高该因子权重 |

### 7.3 进化日志

进化记录保存在：
- `second-brain/rules.md` — 规则更新
- `second-brain/lessons.md` — 新增教训
- `data/evolution-log.json` — 进化评估记录

---

## 八、快速命令参考

### 8.1 启动服务
```bash
# 第二大脑HTTP服务
python F:/aidanao/server.py

# 通达信MCP桥（独立窗口）
python -u F:/aidanao/mcp/tdx_live_bridge.py
```

### 8.2 回测命令
```bash
# 单股回测
python F:/aidanao/daytrade_system/runner.py --stock 300418

# 99天全量回测
python F:/aidanao/daytrade_system/runner.py --stock 300418 --days 99

# 300058回测
python F:/aidanao/daytrade_system/runner.py --stock 300058 --days 99
```

### 8.3 查看状态
```bash
# 查看第二大脑状态
curl http://localhost:8766/api/stats

# 查看进化报告
curl http://localhost:8766/api/evolve/report
```

---

## 九、故障排除

### 9.1 第二大脑无法启动
- 检查端口8766是否被占用：`netstat -ano | findstr 8766`
- 查看server.py错误日志

### 9.2 通达信MCP无法连接
- 确认通达信软件已登录
- 检查网络连接：ping txmcp.tdx.com.cn
- 尝试重启MCP桥接

### 9.3 回测数据缺失
- 检查 `F:/tongdaxin/vipdoc/` 目录
- 确认股票代码存在对应.day文件

---

## 十、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v1.0 | 2026-07-04 | 初始版本，完整系统文档 |
