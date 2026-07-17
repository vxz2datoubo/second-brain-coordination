# 自进化交易系统 · 使用指南

## 系统架构

```
daytrade_system/
  engine/               # 技术指标计算、信号生成
    indicators.py       # 指标库（VWAP/RSI/MACD/布林带/ATR等）
    signals.py          # 交易信号生成
    data_loader.py      # 数据加载
  live/                 # 实时交易引擎（核心）
    tdx_mcp_client.py   # 通达信MCP HTTP客户端
    live_engine.py       # 主引擎：信号生成+槽位管理
    slot_manager.py      # 3槽位管理器
    risk_controller.py   # 实时风控
    trade_logger.py      # 交易记录器
    regime_clf.py        # 市场状态分类器
  sentiment/            # 情绪分析
    news_monitor.py       # 新闻情绪监测
  evolution/            # 自进化层
    auto_tuner.py         # 自适应参数调优
    backtest_optimizer.py # 回测优化器
    self_test.py         # 自我检验
  data/                 # 数据存储
    trade_log.json       # 所有交易记录
    slots.json           # 当前槽位状态
    risk_state.json      # 风控状态
    param_evolution.json # 参数进化历史
```

## 快速开始

### 1. 环境要求
- Python 3.10+
- 通达信客户端（已登录并连接）
- TDX MCP 服务（已授权 WorkBuddy）
- 昆仑万维(300418) + 蓝色光标(300058) 持仓

### 2. 单次信号分析
```bash
cd F:\aidanao\daytrade_system
python live\live_engine.py --mode single
```

### 3. 实时监控模式
```bash
python live\live_engine.py --mode monitor --interval 60
```
每分钟自动扫描两只股票的信号。

### 4. 情绪监测
```bash
python sentiment\news_monitor.py
```

### 5. 自进化调参（建议每周运行）
```bash
python evolution\auto_tuner.py
```

### 6. 回测优化
```bash
python evolution\backtest_optimizer.py
```

### 7. 系统自我检验（建议每天运行）
```bash
python evolution\self_test.py
```

## 核心功能

### 信号生成（6因子模型）
| 因子 | 权重 | 说明 |
|------|------|------|
| F1_VWAP | 25% | 价格相对VWAP极端偏离 |
| F2_RSI | 20% | RSI均值回归 |
| F3_VOL_PROFILE | 20% | 量价分布压力位 |
| F4_MOMENTUM | 15% | 动量衰竭检测 |
| F5_DELTA | 10% | 累积成交量Delta |
| F6_GAP | 10% | 跳空缺口分析 |

### 置信度评级
- **A++ (90+)**: 强烈建议执行，立即挂限价单
- **A (75-89)**: 建议执行，等回调0.3%
- **B (60-74)**: 可执行，限额1笔/天
- **C (45-59)**: 仅备选
- **D (<45)**: 不执行

### 槽位管理规则
- 每股票日最多3笔卖出未回笼
- 回笼后可继续开新槽
- 跨日仓位优先接回
- 14:50 强制平所有未完成槽

### 风控规则
- 硬止损：单笔亏损>2%立即平仓
- 熔断：日累计亏损>2%全天停止
- 连亏2笔：降为1个槽
- 黑天鹅：跌破20日线8%停所有T仓

## TDX MCP 工具使用

系统通过通达信 MCP HTTP API 获取数据：
- `tdx_quotes`: 实时行情
- `tdx_kline`: K线数据（1m/5m/day/week）
- `wenda_news_query`: 新闻查询
- `wenda_notice_query`: 公告查询
- `tdx_lookup_stock`: 代码搜索

OAuth token 已内置，无需额外配置。

## 进化机制

1. **每周自动调参**：分析最近20笔交易，调整因子权重
2. **参数历史追踪**：记录每一代参数及性能
3. **回测验证**：测试不同持有天数和阈值的收益
4. **自我检验**：每日验证数据源、槽位一致性、风控逻辑

## 输出文件

- `data/trade_log.json` - 所有交易记录
- `data/param_evolution.json` - 参数进化历史
- `data/test_reports/` - 每日自我检验报告
- `data/backtest_report_*.md` - 回测报告
