# A股 CORE长期底仓 × 小仓做T 职业级查询决策系统蓝图 v1.0

> blueprint_id: `A-SHARE-CORE-T-PROFESSIONAL-QUERY-DECISION-SYSTEM-0001`
>
> status: `REGISTERED_CANDIDATE / IMPLEMENTATION_QUEUED`
>
> boundary: `RESEARCH_AND_DECISION_SUPPORT / NO_AUTONOMOUS_TRADE`
>
> ux_registry: `Issue #217 v2.1`
>
> program_parent: `Issue #218`
>
> blueprint_authoring_issue: `Issue #219`
>
> initial_targets: `300418.SZ 昆仑万维`, `300058.SZ 蓝色光标`
>
> dependencies: `#199 #211 #212 #213 #214 #215`

## 0. Mission

把机构级研究、估值、事件研究、风险管理、日内执行与绩效归因，压缩成用户可直接按编号调用的简单查询按钮；按钮标题可以通俗，但底层执行必须保持职业级深度、证据纪律、点时一致性、可回测与可审计。

用户真实操作模式是第一性约束：
- 大部分仓位属于 `CORE_BOOK`，长期持有昆仑万维/蓝色光标，服务6~18个月及更长主逻辑；
- 小部分仓位属于 `T_BOOK`，用于日内/短周期做T，只负责增厚收益，不得改变长期方向；
- `CASH_BUFFER` 独立管理现金与事件风险缓冲；
- `NO_T / NO_ACTION` 是正式最优候选；
- 日内执行不得静默降低CORE底仓，底仓变化只能经过Core Position Gate；
- 所有研究输出必须区分事实、证据、推断、概率、价格区间与失效条件。

## 1. Canonical architecture

### 1.1 Query UX / Intent Router

用户可只输入单个编号或组合，例如 `4 5`、`2+15`、`0+8`。Router只解释意图与选择必要模块，不把全部模块全文加载进上下文。

每次输出同时保留：
- `human_readable_card`
- `machine_readable_payload`
- `as_of`
- `source_cutoff`
- `market_effective_at`
- `horizon`
- `confidence`
- `missing_data`
- `data_grade`

### 1.2 Three books

- `CORE_BOOK`：长期股数、长期thesis版本、FFW、估值分布、风险预算、minimum_core_floor。
- `T_BOOK`：日初可卖老库存、T额度、成交、执行基准、期末库存归一。
- `CASH_BUFFER`：可用现金、冻结资金、事件缓冲和回补资金。

### 1.3 Three ledgers

- `THESIS_LEDGER`：商业模式、FFW、估值、竞争、管理层兑现、资本配置、长期失效条件。
- `MARKET_EVENT_LEDGER`：MTW、题材/因子、事件、跨市场传导、价格隐含预期、拥挤度、Regime。
- `EXECUTION_LEDGER`：T+1可卖库存、T额度、VWAP/AVWAP、Volume Profile、成交、滑点、冲击、机会成本、净T Alpha。

硬隔离：日内信号不能直接写长期thesis；长期thesis变化不能伪装成日内执行信号。

### 1.4 Time scales

- Intraday：日内T与执行；
- 1~5D：事件、MTW、残差主导；
- 20~60D：FFW/MTW融合；
- 6~18M+：FFW、估值、商业兑现主导。

## 2. 正式查询按钮 0~17

| 编号 | 用户标题 | 专业内核 |
|---:|---|---|
| 0 | 全套体检 | 自动路由长期、中期、短期、估值、风险、事件、相对配置与T许可；只加载必要模块。 |
| 1 | 今天为什么涨跌？ | Dynamic Factor Exposure & Return Attribution；拆 market / industry / orthogonal theme / company event / residual。 |
| 2 | 财报到底值多少钱？ | EIVR：Earnings Surprise × Price-Implied Expectations × Earnings Quality × Valuation Repricing。 |
| 3 | 长期逻辑坏没坏？ | Thesis Health / Bayesian Fundamental State Update。 |
| 4 | 今天适不适合做T？ | T-Day Gate；趋势/反转/事件首次定价、T+1库存、成本、卖飞风险。 |
| 5 | T在哪卖、哪买？ | Intraday Execution Map；分价成交、Volume Profile、VWAP/AVWAP、波动、相对强弱、订单流可选层。 |
| 6 | 这次T到底赚没赚？ | Counterfactual T-Alpha / Implementation Shortfall。 |
| 7 | 底仓该不该动？ | Core Position Gate。 |
| 8 | 昆仑还是蓝标更值得多拿？ | Relative Value / Pair Allocation / Opportunity Cost。 |
| 9 | 市场现在是什么状态？ | Market Regime。 |
| 10 | 这条消息值不值得追？ | Event Intelligence / point-in-time event study。 |
| 11 | 资金到底在干什么？ | Participant / Flow Evidence；禁止伪“主力意图”。 |
| 12 | 现在贵不贵？ | Reverse DCF + SOTP + Residual Income + Price-Implied Expectations + Scenario Valuation。 |
| 13 | 风险什么时候要减？ | Risk Budget / Stress Test。 |
| 14 | 我们到底有没有Alpha？ | Performance Attribution / Appraisal 与反事实对账。 |
| 15 | 同行先考得怎样？ | Peer / Leading Indicator Earnings Radar。 |
| 16 | 管理层说话靠不靠谱？ | Management Credibility Ledger。 |
| 17 | 行业天花板还在不在？ | Industry/TAM/Competitive Dynamics。 |

**删除项**：不存在“L2值不值得买”用户按钮；数据采购属于后台 `DATA_PURCHASE_GATE`。

## 3. Domain engines

底层按共享引擎实现，禁止每个按钮复制一套代码：

1. `ForwardExposureAttributionEngine`
2. `EIVREngine`
3. `ThesisStateEngine`
4. `TDayGateEngine`
5. `IntradayExecutionMapEngine`
6. `TAlphaAccountingEngine`
7. `CorePositionGateEngine`
8. `RelativeValuePairEngine`
9. `MarketRegimeEngine`
10. `EventIntelligenceEngine`
11. `ParticipantFlowEvidenceEngine`
12. `ValuationEnsembleEngine`
13. `RiskBudgetStressEngine`
14. `PerformanceAttributionAppraisalEngine`
15. `PeerLeadingIndicatorEngine`
16. `ManagementCredibilityLedgerEngine`
17. `IndustryTAMCompetitiveDynamicsEngine`

0号只做router/orchestration，不拥有独立事实或风险权威。

## 4. Evidence quality standard

每个引擎必须生成 `EvidencePack`。来源优先级：

1. 一级官方：交易所、公司公告/IR、监管、会计准则、官方API/文档；
2. 学术：顶级/高质量同行评审论文；working paper必须显式标注未同行评审；
3. 专业机构：CFA、MSCI/Barra、AQR、BlackRock/Aladdin、公开卖方方法论文；区分方法文档与营销材料；
4. 真实案例/项目：可复现事件研究、公开组合/执行案例、失败案例；
5. 用户知识库/既有Skills；
6. 新闻/二手主要用于发现，关键结论回溯一级源。

每项方法必须记录：
`method_id / source_refs / assumptions / valid_horizon / failure_modes / required_data / evidence_maturity`。

复杂度不是专业度；复杂模型无OOS增量时必须退回透明baseline。

## 5. Market Data Fabric / Market Data Bridge

### 5.1 本机数据优先级

目标统一现有通道：
`TQ > TDX MCP > WeStock > vipdoc`

不是盲信第一源。每字段输出：
- `value`
- `source`
- `observed_at`
- `market_timestamp`
- `freshness`
- `quality_flag`
- `conflict_set`

源间冲突超过字段阈值时输出 `SOURCE_CONFLICT`，不得静默选择有利于当前叙事的数据。

### 5.2 MarketDecisionSnapshot

本地先聚合，不把海量逐笔直接塞给GPT。至少支持：
- symbol/session/latest/open/high/low/prev_close；
- 1m/5m OHLCV与relative volume；
- VWAP；
- open-anchored / event-anchored AVWAP；
- realized volatility；
- Volume Profile bins；
- POC/VAH/VAL；
- HVN/LVN节点及计算窗；
- sector/index/proxy relative strength；
- day-start saleable inventory（若安全可得，否则UNKNOWN）；
- explicit fee model；
- event/regime tags；
- optional真实订单流字段及算法/来源。

快照必须可保存并点时回放，防止盘后结果污染盘中判断。

### 5.3 Data Grades

**A — 完整执行研究**：分钟+分价+VWAP/AVWAP+Volume Profile+板块/事件/Regime+库存/成本完整；如引用CVD/Delta/盘口则对应数据真实可用。

**B — 条件式执行**：无完整订单簿/订单流，但分钟、分价、VWAP、Volume Profile、板块、事件完整。允许区间执行研究。

**C / 5-Lite — 降级**：缺分价或可靠实时字段，只能输出条件地图；不得声称POC、吸收、订单流确认。

每次4/5必须先显示Data Grade。

## 6. Button 4 — T-Day Gate

目标不是找点位，而是判断“今天是否应该让均值回归型T仓参与”。候选输入至少包括：
- scheduled/unscheduled company event；
- 财报/重大公告首次定价；
- #1 company residual / leader state；
- #9 regime；
- gap / relative volume / breadth / realized vol / trend strength；
- VWAP state / price-limit proximity / liquidity；
- T+1 saleable inventory；
- expected edge vs implementation shortfall；
- missed-breakout tail cost。

输出：`ALLOW / SMALL_ONLY / WAIT / NO_T` + reason codes + invalidation。

研究必须比较：
- mean-reversion baseline；
- momentum/trend baseline；
- event-conditioned momentum；
- T+1/turnover-conditioned reversal hypothesis；
- no-trade baseline。

阈值只能由训练窗和walk-forward获得，禁止先拍经验阈值再回测美化。

## 7. Button 5 — Intraday Execution Map

只有4号许可后运行。

核心特征：
- 分价成交量；
- Volume Profile POC/VAH/VAL/HVN/LVN；
- VWAP + 明确锚点AVWAP；
- realized volatility / excursion；
- relative volume；
- target vs sector/proxy relative strength；
- event and regime context。

订单流层仅数据真实可靠时启用：Delta/CVD、trade imbalance、footprint、absorption candidate、order-book imbalance/queue/impact。

任何buy/sell classification必须标记 `estimated_trade_direction`，不得等同“主力”。

输出不是单点，而是：
- `sell_candidate_zone_1/2`
- `buyback_candidate_zone_1/2`
- `why_here`
- `cancel/invalidation`
- `max_T_budget_suggestion`
- `chase_prohibition`
- `data_grade`
- `evidence/conflict_flags`

所有“可信度xx%”必须有已校准概率模型、样本量和验证证据；否则只允许High/Medium/Low evidence quality。

## 8. Button 6 — T-Alpha accounting

首要反事实：`NO_T_STATIC_HOLD`。

期末库存归一后计算：
`net_T_alpha = captured_spread + inventory_effect - fees - taxes - slippage - market_impact - opportunity_cost - missed_breakout_cost - execution_error`

至少报告20/60/120有效T样本的mean/median、hit rate、MAE/MFE、tail loss，并分event/non-event、regime、昆仑/蓝标。

若长期成本后增量≤0或OOS不稳定，系统必须建议降低T频率/额度或停用对应状态，而不是继续过拟合。

## 9. Long-term CORE engines

### 9.1 Button 2 — EIVR

不能只看同比或EPS×PE。至少包括：
- T-1 reverse expectations；
- analyst/market expectation distribution（可得时）；
- Surprise Vector：收入、标准化经营利润、毛利率、销售效率、OCF、KPI、guidance；
- earnings quality：投资收益、公允价值、一次性、应计、营运资本；
- 2027~2028路径后验更新；
- pre-report run-up / crowding / peer / event reaction overlay；
- Grade 0~5 + 1~5D/20~60D价格带；
- 财报前发生重大重估后旧绝对价格带自动失效。

### 9.2 Button 3 — Thesis

Prior + evidence慢更新；公司长期逻辑只能被经济证据改变，不被单日分时改变。

### 9.3 Button 7 — Core Position Gate

只消费3/12/13/8及公司级重大事件，不接受5号单独改变CORE。

### 9.4 Button 12 — Valuation

Reverse DCF + SOTP + residual income + scenario/Monte Carlo（有充分依据时）+ price-implied expectations；R&D经济资本化仅作辅助视图，不改法定报表。

### 9.5 Button 13 — Risk

组合集中、共同AI/传媒因子、downside correlation、valuation compression、liquidity、regulatory/geopolitical、financing/dilution、gap/event stress。

## 10. Company adapters

### 10.1 KunlunAdapter

复用前视暴露三层图谱，经营Application与Technology Option严格分离：
- Opera ads/search/browser；
- DramaWave/FreeReels短剧；
- Agent/productivity；
- AI music；
- AI social；
- AI game/legacy game；
- SkyReels/Mureka/R1V/UniPic/Matrix等技术期权不可与应用价值重复计权。

EIVR/CORE重点：
normalized core operating result、sales expense ratio、ROAS/CAC/LTV、AI ARR/retention、OCF、Opera、R&D/compute efficiency、profitability timeline。

### 10.2 BlueFocusAdapter

重点：
- global performance media procurement；
- AI Agentic marketing；
- AI creative/video；
- Globalization 2.0；
- Blue X/Turbo/adtech；
- gross profit/margin；
- AI high-margin revenue；
- OCF/working capital；
- media concentration/532；
- agency vs media-platform vs adtech peers分层。

## 11. Peer / management / industry layers

### Button 15

每个可比标的分别输出：
- `business_overlap_score`
- `factor_reference_value`

禁止混成一个“同行相关度”。

### Button 16

`ManagementPromiseRecord`至少包括：
`speaker/date/source/metric/target/horizon/original_wording/paraphrase/result/deviation/changed_definition/credibility_update`。

### Button 17

行业分析不得只用TAM/CAGR。至少包含：
penetration、monetizable TAM、price/cost curve、competition、platform bargaining、regulation/copyright、substitution、cycle、company capture rate。

## 12. Statistical and research validation

必须满足：
- point-in-time：first_public_at / available_at / market_effective_at / knowledge_cutoff；
- A股T+1、集合竞价、停牌、涨跌停、不可成交；
- train / validation / purged walk-forward OOS；
- event/non-event、bull/bear、AI hot/cold、高低成交、高低波动；
- negative controls / placebo / label permutation；
- multiple testing / false discovery；
- parameter stability；
- 保留simple baseline；
- 概率输出存在时做calibration/Brier；
- 无样本量、CI或校准证据，不得输出伪精确概率。

## 13. Performance appraisal

14号至少对照四个反事实：
A. 完全静态持有；
B. 昆仑/蓝标固定权重静态持有；
C. 只调整CORE、不做T；
D. 实际策略。

总收益至少拆：
`market/industry/theme beta + selection alpha + pair allocation + event alpha + CORE carry + net_T_alpha - implementation_shortfall - explicit_cost - opportunity_cost + unexplained`。

## 14. Implementation sequence for Codex

必须分阶段，不一次实现全部：

### P0 — Blueprint / contracts / schemas
- 固化本蓝图及机器合同；
- 更新集成索引与权威关系；
- 定义MarketDecisionSnapshot、DataGrade、三账本、EvidencePack、按钮输出schema；
- 不实现业务预测。

### P1 — Market Data Bridge
- 统一 TQ / TDX MCP / WeStock / vipdoc；
- 字段级来源、新鲜度、冲突与点时快照；
- 本地先聚合，避免把海量逐笔塞给上层；
- 不引入未经授权的真实交易连接。

### P2 — first vertical slice: 4 → 5 → 6
- T-Day Gate；
- Intraday Execution Map；
- NO_T反事实与净T Alpha；
- 先透明baseline，再walk-forward。

### P3 — CORE vertical slice
- 2 / 3 / 7 / 8 / 12 / 13。

### P4 — evidence/market layers
- 1 / 9 / 10 / 11 / 15 / 16 / 17。

### P5 — orchestration/appraisal
- 0号总路由；
- 14号统一绩效归因与模型退役门。

## 15. Acceptance gates

- CORE_BOOK与T_BOOK可追溯且物理隔离；
- T+1库存模拟正确；
- no-T counterfactual正确；
- 4/5每次显示Data Grade；
- Data Grade C不得伪装完整Volume Profile/订单流；
- 多源数据冲突显式暴露；
- 分价成交、VWAP/AVWAP等真正进入5号，而不是人工画线；
- event日与普通日分层；
- 昆仑/蓝标参数允许不同；
- 未经OOS不得输出伪胜率/伪概率；
- 复杂模型无OOS增量时可降级；
- 5号不得单独修改CORE；
- 不自动真实下单。

## 16. Local resource guardrail

继承项目资源协议：
- Windows / i7-6700 / 32GiB / RTX2070；
- 禁止nested parallelism；
- CPU-bound worker保守限制；
- 全部任务必须回收子进程；
- 不允许遗留大量Python后台；
- Codex与其他Agent并行时继续收紧worker预算；
- 回测优先批处理/缓存/增量计算，不牺牲用户正常电脑使用。

## 17. Governance

- 本蓝图是职业查询系统的正式候选蓝图；
- UX按钮只拥有用户意图与展示格式，不拥有事实、概率、风险或订单权威；
- 复用现有W2/W3/W4/W5/W7/W9/W10/W11/W12/W13能力与权威，不重复造平行系统；
- 当前Codex ACTIVE route未释放前，本蓝图不得抢占Codex活动任务；
- 后续由Codex按P0→P5分阶段实现，每阶段由GPT独立验收后才允许升级；
- `NO_AUTONOMOUS_TRADE` 持续生效。
