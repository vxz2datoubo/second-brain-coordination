# AGENTS.md — 可进化A股倒T交易系统 | 2026-07-05

## 核心目标
自我进化的A股T仓交易系统，以第二大脑知识库为核心，让任意AI工具都能无缝接管。

## A股权威准则优先级

- 交易系统当前最高准则文件：`D:/LiblibAI-workspace/comfyui-deploy-win/ComfyUI/output/SYSTEM_REPLICATION_FOR_CODEX.md`
- 本地可追踪镜像：`F:/aidanao/docs/SYSTEM_REPLICATION_FOR_CODEX.md`
- 适用范围：A股交易分析、T+1 语义、Seasoned/Fresh 区分、DDX/DDY 真资金约束、25 技能架构、概率融合、禁止事项
- 冲突处理：如果旧技能、通用交易知识、非A股默认假设、历史提示词与该文档冲突或重叠，默认以该文档为准
- 持续有效条件：除非用户后续明确指定新的最终版权威文档，否则继续以该文档为最高优先级
- 工程约束：
  - 不得把 OHLCV 资金流代理冒充为真 DDX/DDY
  - 不得忽视 A股 T+1 与交易时段差异，直接套用美股逻辑
  - 不得把单技能信号直接变成交易结论，必须保持概率化、证据化、可复盘
  - 交易子系统必须继续挂接第二大脑母系统协议、公告栏、SelfEvolutionLog、SkillRegistry 与治理链

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    波仔量化交易系统 v4                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐     ┌──────────────┐     ┌─────────────────┐  │
│  │   AGENTS.md │ ──> │  second-brain │ ──> │ daytrade_system │  │
│  │  (架构入口)  │     │   (知识库)    │     │   (交易引擎)    │  │
│  └─────────────┘     └──────────────┘     └─────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    MCP 桥接层 (mcp/)                        ││
│  │  tdx_live_bridge.py  │  tdx_bridge.py  │  brain_bridge.py  ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
F:/aidanao/
├── AGENTS.md                          # 系统入口（必读）
├── SYSTEM_MANUAL.md                   # 完整AI手册
├── AUTO_EVOLUTION.md                  # 自动进化机制
├── MCP_TOOLS.md                       # MCP工具速查
├── server.py                          # 第二大脑HTTP服务
│
├── second-brain/                      # ★ 第二大脑知识库
│   ├── rules.md                       # 交易规则库
│   ├── lessons.md                     # 历史教训库
│   └── daily_log.md                   # 每日交易日志
│
├── core/                              # 核心算法
│   ├── graph.py                       # 知识图谱引擎
│   ├── fast_index.py                  # BM25F融合索引
│   ├── decision_consult.py            # 决策前自检
│   ├── evolve.py                      # 进化引擎
│   ├── self_verify.py                 # 自验证引擎
│   └── ...
│
├── daytrade_system/                   # 日内交易系统
│   ├── runner.py                      # 统一入口
│   ├── engine/                        # 引擎层
│   ├── strategies/                    # 28个策略模块
│   ├── medallion/                     # v4核心模块
│   ├── live/                          # 实盘引擎
│   └── risk/                          # 风控
│
├── mcp/                               # MCP桥接层
│   ├── tdx_live_bridge.py             # 通达信官方MCP桥
│   ├── tdx_bridge.py                  # 通达信本地桥
│   └── brain_bridge.py                # 第二大脑桥
│
└── data/                              # 数据目录
```

---

## 核心参数

| 参数 | 值 | 说明 |
|------|-----|------|
| 单笔金额 | 5000元 (±1000) | 约3-5%仓 |
| 单日T仓上限 | 3笔 | 未回笼计数 |
| 总持仓上限 | 90% | 保持10%+现金 |
| 日亏熔断线 | 2% | 超限全天停止 |
| 昆仑优先级 | 60% | 300418 |
| 蓝标优先级 | 40% | 300058 |
| 倒T优先 | 是 | 先卖后买 |

---

## 交易规则摘要

### 买入红线（违反必亏）
- [x] 大盘下跌趋势禁止追高买入
- [x] 开盘30分钟内禁止买入（除非已有持仓做T）
- [x] 持仓当日跌幅超5%禁止补仓
- [x] 跌幅超7%必须检查是否止损
- [x] 涨停板次日不追高
- [x] 追涨次日只卖不买

### 卖出红线
- [x] 大盘大跌禁止恐慌性卖出
- [x] 盈利未达2%禁止卖出
- [x] 卖出后30分钟内禁止接回
- [x] 连续3日下跌才考虑止损

### 做T原则
- 倒T优先：先卖后买，利用冲高卖出
- 正T谨慎：仅buy_score>40时考虑
- 卖飞处理：等回落1%再追回

---

## 时间窗口

| 窗口 | 时间 | 策略 | 优先级 |
|------|------|------|--------|
| T1 开盘处理 | 09:30-09:50 | 竞价分析，优先接回跨日仓位 | 2 |
| T2 黄金窗口 | 09:50-10:30 | 方向确认后首笔倒T | 1 |
| T3 上午延续 | 10:30-11:00 | 继续看倒T机会 | 3 |
| T4 谨慎期 | 11:00-11:30 | 除非强信号，否则等待 | 5 |
| T5 下午重启 | 13:00-13观察下午是否有新方向 | 3 |
| T6 下午黄金 | 13:30-14:00 | 倒T黄金窗口 | 1 |
| T7 尾盘决策 | 14:00-14:30 | 判断当天是否还有T仓机会 | 2 |
| T8 强制收尾 | 14:30-15:00 | 所有未接回T仓全部强平 | 4 |

---

## MCP工具速查

### 通达信MCP (tdx_live_bridge.py)

```json
tdx_realtime  {"code": "300418"}              // 实时行情
tdx_kline     {"code":"300418","period":"5m","count":100}  // K线
tdx_lookup    {"query": "昆仑"}               // 搜索股票
tdx_news      {"keyword": "AI","limit":5}     // 新闻资讯
tdx_notice    {"code":"300418","limit":3}     // 公告
tdx_screener  {"query":"AI概念","limit":10}   // 条件选股
```

### 第二大脑API

```bash
# 启动服务
python F:/aidanao/server.py  ->  http://localhost:8766

# 搜索知识库
curl -X POST http://localhost:8766/api/retrieve/search \
  -d '{"query": "昆仑万维 交易", "top_k": 5}'

# 执行进化评估
curl -X POST http://localhost:8766/api/evolve/evaluate
```

---

## 启动命令

```bash
# 第二大脑HTTP服务
python F:/aidanao/server.py

# 通达信MCP桥（MCP stdio模式）
C:/Users/Administrator/.workbuddy/binaries/python/versions/3.13.12/python.exe -u F:/aidanao/mcp/tdx_live_bridge.py

# 日内回测
python F:/aidanao/daytrade_system/runner.py --stock 300418 --days 99
```

---

## 数据源

| 优先级 | 来源 | 覆盖 |
|--------|------|------|
| 1 | 通达信官方MCP (txmcp.tdx.com.cn:3001) | 实时行情 |
| 2 | 通达信本地二进制 (F:/tongdaxin/vipdoc/) | 历史K线 |
| 3 | WorkBuddy neodata skill | 财务/宏观 |

---

@@REGION@@

## 认知决策系统

### 新增能力
- 独立思考：像精英大脑一样进行深思熟虑
- 跨领域联想：发现不同领域知识点之间的隐藏关联
- 闭环学习：决策→执行→复盘→更新规则
- 元认知监控：自动识别思维盲区和推理漏洞

### 核心模块
- `core/cognitive_engine.py` — 核心认知引擎
- `core/reason_engine.py` — 跨领域推理引擎
- `core/maibot_bridge.py` — Maibot集成桥接

### API端点
```
POST /api/cognitive/think      # 独立思考
POST /api/cognitive/decision   # 做出决策
POST /api/cognitive/outcome    # 记录结果
GET  /api/cognitive/stats      # 获取统计

POST /api/reason/cross-domain  # 跨领域推理

POST /api/maibot/think        # 与Maibot协作
POST /api/maibot/sync         # 同步知识
```

### 认知思考流程
```
1. 检索相关知识节点
2. 跨领域联想扩展
3. 构建推理链
4. 元认知检查（识别盲点）
5. 生成决策和置信度
6. 输出风险警告和备选方案
```

## 自进化机制

### 日级（每日收盘）
1. 记录交易日志到 second-brain/daily_log.md
2. 亏损日写入lessons.md
3. 更新知识图谱

### 周级（每周五）
1. 进化引擎分析教训
2. 更新rules.md相关参数
3. 优化因子权重

### 月级（每月末）
1. 自检验验证胜率
2. 更新参数配置
3. 输出进化报告

### 进化触发条件
| 条件 | 动作 |
|------|------|
| 日亏>2% | 立即熔断，全天停止 |
| 连亏3笔 | 全天停止交易 |
| 连续2日亏损 | 降仓至1槽 |
| 连续3日盈利 | 考虑加仓10% |
| 某因子胜率<40% | 自动降低该因子权重 |

---

## AI交接协议

任何AI接管时**必须按顺序**读取：

1. **AGENTS.md**（本文件）— 了解架构
2. **second-brain/rules.md** — 获取最新规则
3. **second-brain/lessons.md** — 获取历史教训
4. **second-brain/daily_log.md** — 查看近期日志
5. **SYSTEM_MANUAL.md** — 完整系统手册
6. **daytrade_system/medallion/config.py** — 当前参数配置

---

## 快速参考

### 股票代码
- 昆仑万维: 300418
- 蓝色光标: 300058

### 关联股票池
```
昆仑 → 科大讯飞(002230), 三六零(601360), 恺英网络(002517), 三七互娱(002555)
蓝标 → 分众传媒(002027), 省广集团(002400), 天娱数科(002354), 福石控股(300071)
```

### 置信度等级
| 等级 | 分数 | 动作 |
|------|------|------|
| A++ | ≥90 | 立即执行，限1笔/天 |
| A | ≥75 | 正常执行，等回调0.3% |
| B | ≥60 | 可执行，限额1笔/天 |
| C | ≥45 | 仅备选，谨慎执行 |
| D | <45 | 不执行 |

### 市场状态
- TREND_UP: 上升趋势（减少做T）
- TREND_DOWN: 下跌趋势（倒T为主）
- HIGH_VOL_RANGE: 高波动震荡（做T黄金期）
- LOW_VOL_RANGE: 低波动震荡（减少操作）
- EXTREME: 极端行情（全天停止）

---

版本: 2026-07-05 | 维护: 所有AI共享 | 包含超级博弈大脑


---

## 超级博弈大脑 — Codex自动调用指南 | 2026-07-05

### 核心原则

**任何AI（包括Codex）在处理以下问题时，必须自动查询超级大脑：**

1. **交易决策前** — 买入/卖出/持仓调整
2. **遇到突发新闻** — 需要验证消息真伪
3. **股价异动** — 突然拉升或下跌
4. **不确定性高** — 需要多路径推演
5. **情绪波动** — 恐惧/贪婪时做决策

### Codex自动调用流程

```
当遇到上述场景时，按以下流程操作：

1. 【识别场景】
   判断属于哪种情况（见上）

2. 【调用超级大脑】
   通过 shell_command 调用：
   
   curl -X POST http://localhost:8766/api/super/think \
     -H "Content-Type: application/json" \
     -d '{
       "situation": "<当前情境描述>",
       "stock": "<股票代码>",
       "current_price": <当前价格>,
       "change_pct": <涨跌幅>,
       "volume": <成交量>,
       "avg_volume": <均量>,
       "market_trend": "<市场趋势>",
       "recent_news": [<相关新闻>]
     }'

3. 【解读结果】
   - confidence: 置信度（>70%才可信）
   - warnings: 风险警告（必须看）
   - recommended_action: 推荐行动
   - alternatives: 备选方案

4. 【执行前检查】
   - 是否有"风险优先"警告？
   - 置信度是否足够？
   - 备选方案是什么？

5. 【记录结果】
   决策后调用 /api/super/record-outcome 记录
```

### 常用API速查

| 场景 | API | 用途 |
|------|-----|------|
| 综合思考 | `/api/super/think` | 遇到复杂问题时用 |
| 资金分析 | `/api/detective/investigate` | 分析主力行为 |
| 消息验证 | `/api/news/verify` | 突发新闻时用 |
| 情景推演 | `/api/scenario/plan` | 不确定性高时用 |
| 反坐庄检测 | `/api/anti-gaming/detect` | 怀疑被操纵时用 |
| 博弈分析 | `/api/game/analyze` | 分析市场博弈 |

### 调用示例

**场景1：昆仑万维突然拉升5%**

```bash
curl -X POST http://localhost:8766/api/super/think -d '{
  "situation": "昆仑万维突然拉升5%，有AI芯片利好",
  "stock": "300418",
  "current_price": 48.5,
  "change_pct": 5.2,
  "volume": 15000000,
  "avg_volume": 8000000,
  "market_trend": "up"
}'
```

**场景2：接到"昆仑万维业绩大增"的消息**

```bash
# 先验证消息
curl -X POST http://localhost:8766/api/news/verify -d '{
  "news": {
    "title": "昆仑万维业绩大增50%",
    "source": "市场传言",
    "time": "2026-07-05T10:00:00"
  },
  "stock": "300418",
  "price_data": {"change_pct": 3.5, "volume_ratio": 2.0}
}'
```

**场景3：判断当前是否适合追高**

```bash
curl -X POST http://localhost:8766/api/anti-gaming/detect -d '{
  "stock": "300418",
  "price_history": [...],
  "volume_history": [...]
}'
```

### 快速判断规则

**Codex遇到以下情况时，必须先查大脑：**

| 情况 | 至少调用 |
|------|----------|
| 计划买入 | `/api/anti-gaming/detect` |
| 计划卖出 | `/api/game/analyze` |
| 有突发消息 | `/api/news/verify` |
| 股价异动 | `/api/detective/investigate` |
| 拿不定主意 | `/api/super/think` |
| 连续亏损 | `/api/scenario/plan` |

### 服务器状态检查

```bash
# 检查大脑是否在线
curl http://localhost:8766/api/stats

# 如果返回error，检查服务器是否启动：
# python F:/aidanao/server.py
```

### 思维链模板

Codex遇到交易决策时，必须按以下格式输出：

```
## 决策分析

### 1. 情况识别
- 当前情境：...
- 相关代码：...
- 关键数据：...

### 2. 大脑查询（如需要）
调用：<API名称>
结果：<置信度>，<关键警告>，<推荐行动>

### 3. 综合判断
- 风险点：...
- 机会点：...
- 最终决策：...

### 4. 备选方案
如果上述方案失败/变化，备用：...

### 5. 触发条件
什么情况下改变决策：...
```

---

## 快速启动

```bash
# 1. 启动第二大脑（必须先启动）
python F:/aidanao/server.py

# 2. 验证服务
curl http://localhost:8766/api/stats

# 3. 测试综合思考
curl -X POST http://localhost:8766/api/super/think -d '{
  "situation": "测试：昆仑万维当前是否可以买入",
  "stock": "300418",
  "current_price": 45.0,
  "change_pct": 1.5,
  "market_trend": "neutral"
}'
```

---

版本: 2026-07-05 | 包含超级博弈大脑调用指南

