# 炒股 AI 每日配置化运行卡

目标: 每天只维护行情 CSV、题材 JSONL 和一个配置文件，然后一行命令生成观察池、题材日报、回测结果、仓位计划和流水线摘要。

## 每天准备

1. 把日线 CSV 放进 `market_dir` 指定目录。
2. 把当天题材、新闻、复盘文本写进 `items` 指定的 JSONL。
3. 更新配置里的 `date`、`market_dir`、`items`，真实交易前确认 `account_equity` 和风控参数。
4. 如果昨天有纪律扣分，先运行 `finance_risk_state.py` 更新 `risk_state`，流水线会自动降风险。
5. 保持 `quality_check` 为 `true`，让流水线先检查行情 CSV，再做回测和仓位计划。
6. 如果有指数和市场宽度数据，填入 `market_index_csv` 和 `market_breadth`，让仓位计划按市场环境自动降风险。

## 一行运行

```powershell
python F:/ai/tools/finance_daily_pipeline.py --config F:/ai/qclaw-output/finance-pipeline-sample-config.json
```

如需覆盖配置中的日期:

```powershell
python F:/ai/tools/finance_daily_pipeline.py `
  --config F:/ai/qclaw-output/finance-pipeline-sample-config.json `
  --date 2026-06-21
```

如需摄入第二大脑:

```powershell
python F:/ai/tools/finance_daily_pipeline.py `
  --config F:/ai/qclaw-output/finance-pipeline-sample-config.json `
  --ingest
```

如需只本地生成、不摄入:

```powershell
python F:/ai/tools/finance_daily_pipeline.py `
  --config F:/ai/qclaw-output/finance-pipeline-sample-config.json `
  --no-ingest
```

## 看结果顺序

1. `finance-daily-pipeline-日期.md`: 先看流水线是否完整、风控是否被节流。
2. `finance-data-quality-日期.md`: 先确认行情质量，失败标的不参与交易候选。
3. `finance-daily-report-日期.md`: 看题材生命周期，避开高潮和退潮。
4. `finance-portfolio-plan-日期.md`: 只按计划里的数量、入场、止损和风险执行。
5. 下单前调用 `/api/finance/consult`，盘后写交易日志并运行计划复盘。
7. 隔几天运行前向表现评估，检查候选和题材是否真的有效。
8. 用前向评估结果生成信号评分卡，再让下一次日流水线读取它。
9. 对重点标的或策略定期跑 walk-forward，检查是否过拟合。

## 质量门

配置中的质量参数:

```json
{
  "quality_check": true,
  "quality_min_score": 70,
  "quality_max_gap_business_days": 10,
  "quality_max_abs_return": 0.35
}
```

质量检查会识别重复日期、日期乱序、OHLC 异常、成交量异常、过大价格跳变和过大交易日缺口。低于 `quality_min_score` 或检查失败的标的会从观察池剔除。

A 股实盘建议在 CSV 中增加 `adjustment`、`limit_up`、`limit_down`、`paused` 列。缺少这些字段时质量报告会给警告但不一定剔除；真实下单前要先确认复权方式、涨跌停可成交性和停牌状态。

仓位计划会直接拦截 `paused=1`、最新价接近涨停、最新价接近跌停的候选。被拦截的标的可以继续观察，但当天不作为新开仓计划。

## 下单前检查

任何真实下单前先跑:

```powershell
python F:/ai/tools/finance_pretrade_check.py `
  --plan F:/ai/qclaw-output/finance-portfolio-plan-2026-06-29.md `
  --symbol SAMPLE `
  --action buy `
  --qty 96 `
  --price 13.3 `
  --thesis "按仓位计划小仓试错" `
  --horizon "短线" `
  --max-loss "账户0.1%" `
  --consult
```

结果含义:

- `block`: 不下单，通常是计划外、超数量、追高超过容忍、计划不允许。
- `caution`: 先补齐理由、周期、最大亏损或反方证据。
- `allow`: 本地计划检查通过，仍按 consult 红线和实际盘口执行。

## 题材集中度

`max_theme_exposure_pct` 控制同一题材的最大累计暴露。比如设为 `0.35`，账户 100000 时，同一题材合计持仓名义金额最多约 35000。超过上限的同题材候选会在仓位计划中标记为不允许，原因写明“超过单题材暴露上限”。

## 市场环境温度计

可选输入:

```json
{
  "market_index_csv": "F:/ai/qclaw-output/finance-market-index-sample.csv",
  "market_breadth": "F:/ai/qclaw-output/finance-market-breadth-sample.json"
}
```

宽度 JSON 示例:

```json
{
  "date": "2026-06-20",
  "advancers": 1800,
  "decliners": 3200,
  "limit_up": 28,
  "limit_down": 18,
  "up_amount": 4200,
  "down_amount": 6100
}
```

单独生成市场温度计:

```powershell
python F:/ai/tools/finance_market_regime.py `
  --index-csv F:/ai/qclaw-output/finance-market-index-sample.csv `
  --breadth F:/ai/qclaw-output/finance-market-breadth-sample.json `
  --date 2026-06-20
```

日流水线会把市场温度计的 `risk_multiplier` 叠加到单笔风险、单标的仓位上限和组合总暴露上限。弱市只降风险，不会单独否定所有候选；强市也不会绕过质量门、可成交性和交易前 consult。

## 前向表现评估

候选生成后，等 1/3/5/10 个交易日，再评估当初的观察池有没有命中:

```powershell
python F:/ai/tools/finance_forward_eval.py `
  --watchlist F:/ai/qclaw-output/finance-watchlist-2026-06-25.csv `
  --signal-date 2026-06-02 `
  --horizons 1,3,5,10 `
  --output-dir F:/ai/qclaw-output
```

重点看:

- `命中率`: 该周期收盘收益是否大于 0。
- `平均收益`: 候选整体有没有正期望。
- `最大不利`: 信号后先回撤多少，决定仓位和止损是否过松或过紧。
- `题材归因`: 哪些题材连续有效，哪些题材只是热但不赚钱。

## 信号评分卡

把多个前向评估报告聚合成评分卡:

```powershell
python F:/ai/tools/finance_signal_scorecard.py `
  --input-dir F:/ai/qclaw-output `
  --output-dir F:/ai/qclaw-output `
  --horizon 3 `
  --min-samples 5
```

配置文件中的 `signal_scorecard` 会让每日流水线读取评分卡:

```json
{
  "signal_scorecard": "F:/ai/qclaw-output/finance-signal-scorecard.json"
}
```

日报会显示 `原始候选分`、`历史调整`、`候选分`。历史调整只用于排序加减权，不会绕过质量门、涨跌停/停牌拦截、仓位计划和交易前 consult。

## 每周反馈刷新

每周更新完行情 CSV 后，运行批量反馈刷新:

```powershell
python F:/ai/tools/finance_feedback_refresh.py `
  --watchlist-dir F:/ai/qclaw-output `
  --output-dir F:/ai/qclaw-output `
  --horizons 1,3,5,10 `
  --scorecard-horizon 3 `
  --min-samples 5
```

它会扫描历史 `finance-watchlist-日期.csv`，只评估后续 K 线足够的观察池，并自动重建 `finance-signal-scorecard.json`。如果需要手动回补某个观察池:

```powershell
python F:/ai/tools/finance_feedback_refresh.py `
  --extra-watchlist F:/ai/qclaw-output/finance-watchlist-2026-06-25.csv=2026-06-02
```

## Walk-forward 防过拟合

对重点标的做滚动验证:

```powershell
python F:/ai/tools/finance_walk_forward.py `
  --csv F:/ai/qclaw-output/market-sample/SEMI-半导体样例.csv `
  --date 2026-06-20 `
  --train-bars 18 `
  --test-bars 12 `
  --output-dir F:/ai/qclaw-output
```

重点看:

- `训练分` 高但 `测试收益` 低，说明参数可能过拟合。
- `有效窗口` 太少时，不要放大仓位。
- `稳定性分` 低时，即使普通回测好看，也应降低候选权重。

原则: 这个系统只提供概率、纪律和风控辅助，不做确定性预测，也不保证盈利。

## 持仓监控与止损检查

每天盘中或盘后，先检查已有持仓，再决定是否开新仓：

```powershell
python F:/ai/tools/finance_position_monitor.py `
  --plan F:/ai/qclaw-output/finance-portfolio-plan-2026-06-20.md `
  --journal F:/ai/qclaw-output/finance-trade-journal.jsonl `
  --watchlist F:/ai/qclaw-output/finance-watchlist-2026-06-20.csv `
  --market-dir F:/ai/qclaw-output/market-sample `
  --date 2026-06-20
```

重点看：

- `action_required`: 先处理止损、超计划、计划外持仓，再考虑新机会。
- `watch_count`: 多半是行情缺失或行情过期，不要把过期行情当成信号。
- `unrealized_pnl` / `unrealized_return`: 只用于复盘和仓位管理，不用于冲动加仓。
- 触发止损时先执行纪律，再写复盘；不能用补仓掩盖亏损。

## 每日决策面板

现在 `finance_daily_pipeline.py` 会自动生成一份每日决策面板：

```text
F:/ai/qclaw-output/finance-decision-dashboard-日期.md
F:/ai/qclaw-output/finance-decision-dashboard-日期.json
```

它把以下信息合并成一页：

- 今日风控模式、市场温度、仓位上限和计划总暴露。
- 热门题材排名、生命周期阶段、风险等级和题材建议。
- 计划内候选标的、入场价、止损价、数量和单笔风险。
- 持仓监控里需要先处理的止损、超计划、计划外持仓或行情过期问题。
- 当天硬闸门：未进计划不交易、下单前必须 consult、触发止损先执行。

也可以单独重建面板：

```powershell
python F:/ai/tools/finance_decision_dashboard.py `
  --pipeline F:/ai/qclaw-output/finance-daily-pipeline-2026-06-29.json `
  --date 2026-06-29 `
  --output-dir F:/ai/qclaw-output
```

日常使用顺序：

1. 先看 `finance-decision-dashboard-日期.md` 的“先做什么”和“风控闸门”。
2. 如果有 `action_required` 持仓，先处理持仓，不开新仓。
3. 只从“计划内候选”里等待入场条件。
4. 真要下单前，再跑 `finance_pretrade_check.py` 或 `/api/finance/consult`。

## 题材事件摄入

如果当天题材、新闻、研报摘要、盘后复盘还不是 JSONL，先用摄入器标准化：

```powershell
python F:/ai/tools/finance_theme_ingest.py `
  --input F:/ai/qclaw-output/today-review.md `
  --date 2026-06-30 `
  --source manual-after-market `
  --output F:/ai/qclaw-output/finance-daily-items-2026-06-30.jsonl
```

也可以直接粘贴一段文本：

```powershell
python F:/ai/tools/finance_theme_ingest.py `
  --date 2026-06-30 `
  --source manual-note `
  --output F:/ai/qclaw-output/finance-daily-items-2026-06-30.jsonl `
  --text "AI算力放量分歧。半导体确认走强。消费继续退潮。"
```

它会把长复盘按句子拆成独立事件，避免“消费退潮”这类词污染同一段里的 AI、半导体判断。输出的 `finance-daily-items-日期.jsonl` 填到流水线配置的 `items` 字段即可。

## 最近题材趋势

每日流水线现在会自动生成多日题材趋势：

```text
F:/ai/qclaw-output/finance-theme-trends-日期.md
F:/ai/qclaw-output/finance-theme-trends-日期.json
```

也可以单独运行：

```powershell
python F:/ai/tools/finance_theme_trends.py `
  --input-dir F:/ai/qclaw-output `
  --days 10 `
  --date 2026-06-30 `
  --output-dir F:/ai/qclaw-output
```

重点看：

- `升温`: 进入重点观察，但仍要等价格、量能、仓位计划确认。
- `持续热门`: 不追一致高潮，只考虑计划内核心标的的分歧低吸或回踩确认。
- `降温/退潮`: 降低权重；如果已有持仓，优先看止损和减仓纪律。
- `单日脉冲`: 第二天不延续就不放大仓位。

每日决策面板会自动显示“最近题材趋势”，用来和“今日热门题材”互相校验。

## 纸面交易验证

生成仓位计划后，等后续 K 线补齐，可以用纸面交易验证计划本身有没有赚钱能力：

```powershell
python F:/ai/tools/finance_paper_trade.py `
  --plan F:/ai/qclaw-output/finance-portfolio-plan-2026-06-20.md `
  --watchlist F:/ai/qclaw-output/finance-watchlist-2026-06-20.csv `
  --signal-date 2026-06-20 `
  --horizon-days 5 `
  --output-dir F:/ai/qclaw-output
```

它会模拟：

- 计划内且允许交易的标的。
- 后续行情触及计划入场价才买入。
- 买入后若触及计划止损则止损退出。
- 未触及止损则在验证周期末按收盘价退出。
- 输出总净盈亏、胜率、平均收益率和按题材归因。

使用原则：

- 纸面交易连续为负时，先降低对应题材/策略权重，不要扩大实盘仓位。
- 入场触发很少，说明计划价过严或行情未确认，不应该追价补触发。
- 止损触发很多，优先检查题材生命周期、市场温度、止损距离和入场条件。
- 纸面交易只是执行验证，不等同于真实成交，也不保证未来盈利。

## 纸面反馈评分卡

跑完一批纸面交易后，生成纸面反馈评分卡：

```powershell
python F:/ai/tools/finance_paper_scorecard.py `
  --input-dir F:/ai/qclaw-output `
  --output-dir F:/ai/qclaw-output `
  --min-samples 5
```

输出：

```text
F:/ai/qclaw-output/finance-paper-scorecard.json
F:/ai/qclaw-output/finance-paper-scorecard.md
```

每日流水线会自动读取 `finance-paper-scorecard.json`，并在日报的观察池回测表里显示 `纸面调整`：

- 纸面交易持续亏损的题材会降低候选分。
- 纸面交易表现好的题材会小幅提高候选分。
- 样本少时调整会被压低，避免一两次结果过拟合。
- 它只影响排序，不会绕过行情质量、市场温度、仓位计划、pretrade check 和 consult。

## 盈利边际审计

每日流水线会自动生成盈利边际审计：

```text
F:/ai/qclaw-output/finance-edge-audit-日期.md
F:/ai/qclaw-output/finance-edge-audit-日期.json
```

也可以单独运行：

```powershell
python F:/ai/tools/finance_edge_audit.py `
  --journal F:/ai/qclaw-output/finance-trade-journal.jsonl `
  --input-dir F:/ai/qclaw-output `
  --horizon 3 `
  --date 2026-06-30 `
  --output-dir F:/ai/qclaw-output
```

它会合并三类证据：

- 真实交易账本：真实闭合交易的胜率、平均收益和净盈亏。
- 纸面交易：仓位计划在后续行情里的模拟执行表现。
- 前向评估：观察池信号在未来 N 天是否有效。

重点看：

- `positive`: 证据允许按既定风控继续，但仍不能重仓。
- `caution`: 只做小样本、低风险验证。
- `negative`: 暂停或极小仓，直到纸面交易、真实交易、前向评估改善。

如果出现“前向评估为正，但纸面交易为负”，优先调试入场、止损、仓位执行规则，而不是简单换题材。

## 执行规则敏感性分析

当盈利边际审计提示“前向评估为正，但纸面交易为负”时，运行执行规则敏感性分析：

```powershell
python F:/ai/tools/finance_execution_tuner.py `
  --plan F:/ai/qclaw-output/finance-portfolio-plan-2026-06-20.md `
  --watchlist F:/ai/qclaw-output/finance-watchlist-2026-06-20.csv `
  --signal-date 2026-06-02 `
  --horizons 3,5,10 `
  --entry-tolerances 0,0.01,0.02 `
  --stop-buffers 0,0.01,0.02,0.03 `
  --output-dir F:/ai/qclaw-output
```

它会扫描：

- 不同持有/验证天数。
- 不同入场容忍度。
- 不同止损缓冲比例。

重点看：

- 如果所有组合仍为负，说明不是简单调参能解决，优先暂停或极小仓。
- 如果只有大幅放宽止损才改善，必须重新计算单笔风险和仓位，不能直接套用。
- 如果最佳组合不需要追价容忍，继续坚持不追高。
- 如果多期敏感性分析都指向同一规则改进，才考虑修改默认执行规则。
