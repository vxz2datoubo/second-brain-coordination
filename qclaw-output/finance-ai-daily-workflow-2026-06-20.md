# 炒股 AI 回测预测建议师 - 每日工作流

目标: 用第二大脑沉淀题材、规则、回测和复盘，形成可审计的交易辅助系统。系统只做概率、风控和纪律辅助，不承诺确定性预测或保证盈利。

## 1. 每日输入

每天收集以下文本，作为 `/api/finance/hot-themes` 的 `items` 输入:

- 盘前: 宏观政策、隔夜外围、产业新闻、公司公告。
- 盘中: 涨停原因、板块异动、成交量异常、资金流向。
- 盘后: 复盘文章、龙虎榜、连板高度、题材退潮/加强信号。

推荐 item 格式:

```json
{
  "title": "AI算力光模块继续走强",
  "text": "算力、服务器、光模块、数据中心方向成交量放大，板块内分化加剧。",
  "date": "2026-06-20",
  "source": "manual-daily-review"
}
```

## 2. 热门题材分析

调用:

```powershell
$payload = @{
  top_k = 10
  items = @(
    @{ title='AI算力光模块继续走强'; text='算力 服务器 光模块 数据中心 成交量放大'; date='2026-06-20'; source='daily' },
    @{ title='机器人板块午后拉升'; text='人形机器人 减速器 伺服 题材活跃'; date='2026-06-20'; source='daily' }
  )
} | ConvertTo-Json -Depth 6

Invoke-RestMethod -Uri http://localhost:8766/api/finance/hot-themes `
  -Method POST `
  -ContentType 'application/json; charset=utf-8' `
  -Body $payload
```

输出重点看:

- `themes[].rank`: 热度排名
- `themes[].score`: 文本热度分
- `themes[].keywords`: 命中的关键词
- `themes[].evidence`: 支撑证据
- `themes[].suggestion`: 观察/低吸/避免追高提示

## 推荐: 一键日更流水线

日常优先使用这个入口；后面的分步命令主要用于调试单个环节。

先做健康检查:

```powershell
python F:/ai/tools/finance_system_check.py
```

检查通过时会输出 `ok: true`，并确认行情样例、题材分析、观察池、回测、仓位计划、交易账本、复盘评分、风险节流和第二大脑 HTTP 服务是否可用。

```powershell
python F:/ai/tools/finance_daily_pipeline.py `
  --date 2026-06-20 `
  --market-dir F:/ai/qclaw-output/market-sample `
  --market-meta F:/ai/qclaw-output/market-sample-meta.json `
  --items F:/ai/qclaw-output/finance-daily-items-sample-2026-06-20.jsonl `
  --output-dir F:/ai/qclaw-output `
  --min-bars 30 `
  --account-equity 100000 `
  --risk-per-trade 0.005 `
  --max-position-pct 0.2 `
  --max-total-exposure 0.6 `
  --min-score 15 `
  --ingest
```

它会依次完成:

- 扫描本地行情 CSV，生成观察池。
- 分析每日题材热度和生命周期。
- 对观察池做多策略回测和候选评分。
- 生成组合仓位与 ATR 止损计划。
- 如果存在 `finance-risk-state.json`，自动按上一轮纪律分降低风险。
- 把日报和仓位计划摄入第二大脑。
- 输出流水线摘要: `qclaw-output/finance-daily-pipeline-日期.md`。

### 可选: 东方财富板块数据抓取

可以先尝试抓取东方财富概念/行业板块快照，输出 JSONL 后再交给日报脚本:

```powershell
python F:/ai/tools/finance_fetch_eastmoney.py `
  --kind concept `
  --page-size 50 `
  --date 2026-06-20
```

如果接口被远端断开或拦截，脚本会给出错误提示。这种情况下使用手动 JSONL 输入，不影响主流程。

生成日报:

```powershell
python F:/ai/tools/finance_daily_report.py `
  --input F:/ai/qclaw-output/finance-daily-items-sample-2026-06-20.jsonl `
  --watchlist F:/ai/qclaw-output/finance-watchlist-generated.csv `
  --date 2026-06-20
```

生成并摄入第二大脑:

```powershell
python F:/ai/tools/finance_daily_report.py `
  --input F:/ai/qclaw-output/finance-daily-items-sample-2026-06-20.jsonl `
  --watchlist F:/ai/qclaw-output/finance-watchlist-generated.csv `
  --date 2026-06-20 `
  --ingest
```

## 3. 个股或策略回测

准备 CSV:

```csv
date,open,high,low,close,volume
2026-06-01,10.0,10.5,9.8,10.3,100000
```

### 从本地行情目录自动生成观察池

把真实 A股日线 CSV 放进一个目录，例如:

```text
F:/ai/data/market/a-share/
  300750-宁德时代.csv
  688981-中芯国际.csv
```

文件名建议用 `代码-名称.csv`。CSV 至少包含 `date,open,high,low,close,volume`，也支持中文列名，如 `日期,开盘,最高,最低,收盘,成交量`。

可选元数据文件:

```json
{
  "300750": {"name": "宁德时代", "theme": "新能源", "strategy": "optimize"},
  "688981": {"name": "中芯国际", "theme": "半导体", "strategy": "optimize"}
}
```

生成观察池:

```powershell
python F:/ai/tools/finance_build_watchlist.py `
  --market-dir F:/ai/data/market/a-share `
  --meta F:/ai/data/market/a-share-meta.json `
  --output F:/ai/qclaw-output/finance-watchlist-generated.csv `
  --min-bars 120
```

样例验证命令:

```powershell
python F:/ai/tools/finance_build_watchlist.py `
  --market-dir F:/ai/qclaw-output/market-sample `
  --meta F:/ai/qclaw-output/market-sample-meta.json `
  --output F:/ai/qclaw-output/finance-watchlist-generated.csv `
  --min-bars 30
```

调用:

```powershell
$payload = @{
  csv_path = 'F:/ai/qclaw-output/finance-sample-bars.csv'
  short_window = 3
  long_window = 8
  initial_cash = 100000
  fee_rate = 0.0003
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8766/api/finance/backtest `
  -Method POST `
  -ContentType 'application/json; charset=utf-8' `
  -Body $payload
```

输出重点看:

- `total_return`: 区间收益
- `annualized_return`: 年化收益
- `max_drawdown`: 最大回撤
- `trades_count`: 交易次数
- `win_rate`: 胜率
- `latest.rsi14`: 最新 RSI
- `suggestion.flags`: 风险提示

### 多策略比较

`/api/finance/backtest` 支持 `strategy=optimize`，会在小参数网格里比较:

- `sma_cross`: 均线交叉趋势策略
- `breakout`: 价格突破策略
- `rsi_reversion`: RSI 均值回归策略

调用:

```powershell
$payload = @{
  csv_path = 'F:/ai/qclaw-output/finance-sample-bars.csv'
  strategy = 'optimize'
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8766/api/finance/backtest `
  -Method POST `
  -ContentType 'application/json; charset=utf-8' `
  -Body $payload
```

选择规则不是只看最高收益，而是看 `risk_adjusted_score`:

- 收益越高越好。
- 最大回撤越低越好。
- 胜率越高越好。
- 有效交易次数过少会扣分。
- 最大回撤超过 20% 会重罚。

注意: 参数扫描容易过拟合。真实交易前必须用更长时间窗口、不同市场环境、交易前 consult 风控检查和小仓试错验证。

### 组合仓位与风险计划

观察池和多策略回测之后，必须生成仓位计划，不能直接凭候选分下单:

```powershell
python F:/ai/tools/finance_portfolio_plan.py `
  --watchlist F:/ai/qclaw-output/finance-watchlist-generated.csv `
  --date 2026-06-20 `
  --account-equity 100000 `
  --risk-per-trade 0.005 `
  --max-position-pct 0.2 `
  --max-total-exposure 0.6 `
  --atr-multiple 2 `
  --min-score 15 `
  --ingest
```

默认纪律:

- 单笔亏损风险控制在账户权益的 0.5%。
- 单标的仓位不超过 20%。
- 组合总暴露不超过 60%。
- 止损用 `入场价 - 2 * ATR` 估算。
- 策略分低于阈值、历史最大回撤过大、无法计算止损距离时，不允许交易。
- 即使计划允许，下单前仍要调用 `/api/finance/consult` 做红线检查。

## 4. 交易前检查

任何买入前调用 `/api/finance/consult`:

```powershell
$payload = @{
  target='某A股AI算力概念股'
  action='想买入'
  thesis='题材热度提升，个股回踩支撑'
  horizon='短线'
  position='一成仓试错'
  stop_loss='跌破昨日低点'
  max_loss='账户0.5%'
  record=$true
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8766/api/finance/consult `
  -Method POST `
  -ContentType 'application/json; charset=utf-8' `
  -Body $payload
```

硬规则:

- 没有止损条件，不交易。
- 没有最大可承受亏损，不交易。
- 只因害怕错过而买入，默认情绪交易。
- 补仓必须基于新证据，不能只为摊低成本。
- 重仓前必须通过极端情景检查。

## 5. 盘后复盘

把实际交易结果写成节点摄入第二大脑，标题建议:

- `复盘: 2026-06-20 AI算力交易`
- `教训: 追高某题材导致亏损`
- `交易规则: 某题材退潮后的卖出条件`

复盘必须包含:

- 原始假设
- 买入/卖出理由
- 反方证据
- 实际结果
- 偏差原因
- 下次规则修正

### 交易账本与绩效归因

记录买入:

```powershell
python F:/ai/tools/finance_trade_journal.py add `
  --date 2026-06-20 `
  --symbol SAMPLE `
  --name 样例趋势股 `
  --theme AI算力 `
  --side buy `
  --qty 1000 `
  --price 12.80 `
  --fee 5 `
  --reason 分歧低吸 `
  --notes "按计划试错"
```

记录卖出:

```powershell
python F:/ai/tools/finance_trade_journal.py add `
  --date 2026-06-20 `
  --symbol SAMPLE `
  --name 样例趋势股 `
  --theme AI算力 `
  --side sell `
  --qty 1000 `
  --price 13.30 `
  --fee 5 `
  --reason 分歧低吸 `
  --notes "按计划卖出"
```

生成绩效归因报告:

```powershell
python F:/ai/tools/finance_trade_journal.py report `
  --date 2026-06-20 `
  --ingest
```

对照仓位计划做执行复盘评分:

```powershell
python F:/ai/tools/finance_plan_review.py `
  --plan F:/ai/qclaw-output/finance-portfolio-plan-2026-06-20.md `
  --journal F:/ai/qclaw-output/finance-trade-journal-sample.jsonl `
  --date 2026-06-20 `
  --ingest
```

根据复盘评分更新下一轮风控状态:

```powershell
python F:/ai/tools/finance_risk_state.py `
  --review F:/ai/qclaw-output/finance-plan-review-2026-06-20.md `
  --state F:/ai/qclaw-output/finance-risk-state.json `
  --base-risk-per-trade 0.005 `
  --base-max-position-pct 0.2 `
  --base-max-total-exposure 0.6
```

下一次运行 `finance_daily_pipeline.py` 时会自动读取这个状态。如果纪律分低、计划外交易、超计划买入或止损滞后，系统会降低单笔风险、仓位上限或组合总暴露。

重点检查:

- 哪个题材真正赚钱，哪个题材只是热闹。
- 哪个交易理由胜率低，应删除或降低仓位。
- 是否违反追高、补仓、单一消息源等红线。
- 是否存在赚小亏大、胜率高但盈亏比差的问题。
- 是否计划外交易、买入数量超计划、买入价明显高于计划、止损执行滞后。

## 下一步增强

- 接入真实 A股日线/分钟线数据源。
- 接入每日题材新闻抓取或手动导入文件夹。
- 增加多策略回测: 突破、回踩、RSI反转、ATR止损。
- 增加题材生命周期: 发酵、高潮、分歧、退潮。
- 增加交易账本和按月绩效归因。
