# 07_RESEARCH_AND_BACKTEST_INVENTORY — 研究与回测清单

> 生成时间: 2026-07-16 02:45 (UTC+8)

---

## 1. `core/backtest_news_nextday.py` — 消息面→次日涨跌回测

| 字段 | 值 |
|------|-----|
| **研究目标** | 验证新闻因子对次日/多日收益的预测能力 (IC, 五分位多空差, 持有期策略P&L) |
| **输入数据** | `data/news_index/exports/news_index_{code}_365.csv` (22维日频因子) + `data/news_db/staging/_raw/kline_{code}.json` (日K线) |
| **时间范围** | 2025-07-15 至 2026-07-15 (~365日; 活跃新闻日 60-74日) |
| **标签** | 消息面量化, 回测, IC分析, 衰减结构 |
| **模型** | Spearman秩相关IC + Pearson IC + 五分位分组 + 持有期多空策略净值 |
| **滚动样本外** | ❌ 全样本回测 |
| **交易成本** | ❌ 未计入 (纯理论研究) |
| **T+1** | ✅ 因子 t 日 → 收益 t+1 日 (无未来函数) |
| **涨跌停/停牌** | ⚠️ 未显式处理 (需验证) |
| **前视风险** | ✅ 已消除：因子只使用 t 日收盘可知新闻, 收益用 t+1 日收盘 |
| **最新结果** | 昆仑 fwd1 IC=0.27 (动量型), 蓝标 fwd3 IC=0.24 (滞后型但持有期P&L全负→不可交易) |
| **输出** | `data/news_index/backtest/{code}_ic.csv`, `_quintile.csv`, `_strategy.csv`, `REPORT.md`, `DECAY_VALIDATION.md` |

---

## 2. `core/chip_digestion_profile.py` — 筹码消化剖面

| 字段 | 值 |
|------|-----|
| **研究目标** | 一个月的筹码递推消化率：每日换手率 → 哪些成本区间的筹码被消化 |
| **输入数据** | `data/news_db/staging/_raw/kline_300418.json` (本地日K) |
| **时间范围** | ~30个交易日 |
| **标签** | 筹码分析, Volume Profile, 消化率 |
| **模型** | 递推残留 (层残留率判定) |
| **滚动样本外** | ❌ 固定窗口 |
| **交易成本** | ❌ |
| **T+1** | ⚠️ 间接 (换手率考虑了T+1) |
| **涨跌停/停牌** | ❌ 未处理 |
| **前视风险** | ❌ |
| **最新结果** | `data/chip_digestion/daily_turnover_log.csv` |
| **输出** | CSV 文件 (日期, 换手率, 层残留率, 未消化总量) |

---

## 3. `core/fund_pool_fifo.py` — FIFO 资金池引擎

| 字段 | 值 |
|------|-----|
| **研究目标** | 多批次资金按FIFO规则追踪：每批资金入场日期+渠道+持仓周期，当前持仓成本 |
| **输入数据** | 四渠道资金流数据 (WeStock `data_fund_flow` 或 Tushare `moneyflow`) |
| **时间范围** | 任意 (支持连续多日 deposit/withdraw) |
| **标签** | 资金管理, FIFO, 多批次, 成本核算 |
| **模型** | FIFO 队列 + MultiPoolManager + 持股周期统计 |
| **滚动样本外** | ✅ (设计为连续运行) |
| **交易成本** | ✅ 适配A股 (印花税0.1%卖出, 佣金0.03%, T+1, 涨跌停限制) |
| **T+1** | ✅ 硬编码适配 |
| **涨跌停/停牌** | ✅ 涨跌停无法买入/卖出, 冻结池 |
| **前视风险** | ❌ |
| **最新结果** | 24/24 单元测试通过 (634行) |
| **输出** | summary() / irr() / 逐批次持仓明细 |

---

## 4. `core/alert_engine.py` — 高价值消息预警引擎

| 字段 | 值 |
|------|-----|
| **研究目标** | 从 WeStock 全市场新闻中评分筛选高价值事件, 主动推送预警 |
| **输入数据** | WeStock MCP: `data_hot` (kind=news), `tool_event` (事件名称), `data_calendar` (未来事件日期) |
| **时间范围** | 持续 (每 2h 自动化扫描) |
| **标签** | 预警, 新闻筛选, 事件驱动 |
| **模型** | impact × urgency × relevance 加权评分 (阈值 55) + 关键词甄别 |
| **滚动样本外** | ✅ (实时运行) |
| **交易成本** | N/A |
| **T+1** | N/A |
| **涨跌停/停牌** | N/A |
| **前视风险** | ❌ |
| **最新结果** | `alerts/pending.json` (待推送), `alerts/history.json` (去重历史) |
| **输出** | JSON (pending/history) |

---

## 5. `core/synthesize_staging.py` — 新闻合成入库

| 字段 | 值 |
|------|-----|
| **研究目标** | 将 WeStock MCP 拉取的 `_raw/` 新闻 JSON 归一化合成 → `news_archive.db` (SQLite) |
| **输入数据** | `data/news_db/staging/_raw/*.json` |
| **时间范围** | 365 天 (两股各一年) |
| **标签** | 数据工程, ETL |
| **模型** | N/A (数据处理) |
| **输出** | SQLite DB (FTS5, 六表) |

---

## 6. `core/tushare_bridge.py` — Tushare 本地桥接

| 字段 | 值 |
|------|-----|
| **研究目标** | 通过本地 token 经 gyzcloud.top 代理调用 Tushare API, 获取历史资金流 |
| **输入数据** | Tushare REST API |
| **标签** | 数据工程, API桥接 |
| **最近验证** | 2026-07-15: 成功获取昆仑 moneyflow 历史 (7/14 主力净流出 2.82亿) |
| **输出** | pandas DataFrame |

---

## 综合评估

| 指标 | 状态 |
|------|------|
| 有滚动样本外验证 | ❌ 所有回测均为全样本 |
| 有真实交易成本建模 | ⚠️ 仅 fund_pool_fifo.py |
| 有T+1适配 | ⚠️ 回测脚本有, 其他不一定 |
| 有涨跌停/停牌处理 | ⚠️ 仅 fund_pool_fifo.py |
| 有前视风险检查 | ⚠️ backtest_news_nextday.py 有, 其他未审计 |
| 有单元测试 | ⚠️ 仅 fund_pool_fifo.py (24/24 通过) |
