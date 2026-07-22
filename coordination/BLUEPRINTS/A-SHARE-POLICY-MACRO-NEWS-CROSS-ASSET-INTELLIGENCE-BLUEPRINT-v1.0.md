# A股政策-宏观-消息-跨资产情报系统蓝图 v1.0

> module_id: `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-0015`
>
> workstream: `W5`
>
> status: `REGISTERED_CANDIDATE / NOT_IMPLEMENTED`
>
> boundary: `research_only / NO_TRADE`
>
> decision_owner: `GPT`
>
> implementation_owner_candidate: `CODEX`
>
> local/source capability support: `WORKBUDDY`
>
> research/adversarial support: `QCLAW`

## 0. 结论

现有工程并非没有消息面能力。可复用基础包括：

1. PR #8的时序证据智能与注意力传播候选蓝图，已定义事件、来源、时间、证据、修订、反证和`available_at`；
2. W2市场数据与确定性回放，可承载点时价格、规则和A股约束；
3. W5事件、新闻、公告与注意力工作流；
4. W6多参与者博弈、W7验证风险、W9影子模式、W10 DecisionEpisode、W11概率资本配置、W12决策科学、W13参与者资金情报。

但当前没有形成可以持续运行并经过验证的“政策-宏观-消息-跨资产情报能力”。主要缺口为：

- 没有统一的国内政策与宏观事件日历；
- 没有区分“官方确认日程”“历史高先验窗口”“市场传闻窗口”；
- 没有冻结事件发生前的市场共识与预期分布；
- 没有把事件结果拆成标题惊喜、文本新颖度、政策路径、增长信息和风险溢价信息；
- 没有识别消息前抢跑、消息落地兑现、过度反应、反转和延迟漂移；
- 没有跨国债收益率曲线、资金利率、人民币、港股、商品、黄金、原油、指数期货、ETF和A股行业的统一反应地图；
- 没有将政策消息映射到直接、二阶、三阶受益/受损链与兑现时滞；
- 没有正式的传闻可信度、消息冲突和来源传播链；
- 没有跨制度、跨政策周期、跨市场状态的点时回测和增量价值验证。

因此，本模块不是第二套新闻库或行情系统，而是复用W2/W5基础对象的**政策预期、事件惊喜、跨资产解释和A股传导编译层**。

## 1. 第一原则

### 1.1 系统回答的问题

系统不只回答：

> 今天发生了什么新闻？

而要回答：

> 在当时可获得的信息下，市场原本预期什么？事件实际释放了哪些维度的信息？价格在事件前是否已经抢跑？事件后是继续吸收、兑现还是反转？不同资产的反应是否支持同一个解释？该解释通过什么机制影响A股哪些板块和公司，何时生效，又有哪些替代解释？

### 1.2 五项硬边界

1. **历史规律不是官方日程。** 例如七月底政治局经济会议可标记为高先验政策窗口，但在新华社或中国政府网正式发布前不能写成已确认日期。
2. **消息不是惊喜。** 市场反应主要取决于结果相对事前预期的差，而非结果绝对方向。
3. **单资产波动不是完整解释。** 需要同时观察收益率曲线、股票、汇率、商品、波动率、流动性和资金行为。
4. **价格先动不等于内幕泄漏。** 抢跑可由公开信息推理、仓位调整、传闻扩散、流动性和交易过程中的信息揭示引起。
5. **预测有效不等于因果正确。** 一个消息指标有预测力，不证明该消息是价格变化的唯一原因。

## 2. 用户知识四层映射

### 2.1 用户明确提出

- 消息面不能只看公司、板块和科技，也要覆盖国内政策、国际政治、战争、国际金融、油价、金价和跨资产变化；
- 重要政策窗口应提前提醒，例如七月底可能出现的政治局经济会议窗口；
- 单看国债收益率或其他价格变量可能得出错误结论；
- 要识别消息抢跑、提前反应和消息兑现；
- 必须结合多个技能、多个参数和不同历史时期回测。

### 2.2 用户知道但未显式展开

- 已知日历事件和突发事件需要不同模型；
- 同一个“利好”在高预期和低预期下结果可能相反；
- 市场可能交易政策力度、政策节奏、政策可信度和后续条件，而不是只交易公告标题；
- 同一条政策对债券、人民币、成长股、周期股和商品的方向可能不同；
- 消息对公司影响有直接、供应链、需求、融资成本、估值和风险偏好等多条路径；
- 公告前价格变化会降低公告后的剩余信息差；
- 传闻被证实、被部分证实和被否认应分别处理。

### 2.3 用户暂不了解但容易理解

- `Expected / Surprise`：只有结果相对市场共识的差异才是可识别惊喜；
- `Policy Information Effect`：宽松政策可能同时传递“经济比市场想象更弱”的信息，导致股债反应并非简单相反；
- `Latent News Factor`：公告正文、措辞、新增条款和执行细节可能比标题数字更重要；
- `Pre-announcement Drift`：价格可能在预定会议前持续移动；
- `Post-announcement Drift`：信息可能被缓慢吸收，公告后继续延续；
- `Sell the News`：预期已交易充分时，利好落地可能反而回落；
- `Rational Inattention`：投资者注意力有限，复杂消息可能延迟定价；
- `Narrative Diffusion`：消息从官方、媒体、机构、自媒体到大众扩散的速度影响定价路径。

### 2.4 高级专业层

- 高频事件研究与局部投影；
- 异方差识别和符号限制；
- 多维政策惊喜与收益率曲线因子；
- 状态空间模型和潜在惊喜因子；
- 结构突变、时变系数和Markov状态切换；
- 文本新颖度、语义差分和政策立场分解；
- 事件知识图谱、因果图和机制传导图；
- Hawkes过程与传播强度；
- 合成控制、双重差分、安慰剂、负对照和异质性处理效应；
- 概率校准、选择性预测、PBO、Deflated Sharpe、White Reality Check、Hansen SPA和Romano-Wolf。

高级方法只有在时间戳、预期数据、样本量和可识别性满足时才允许启用。

## 3. 事件本体

### 3.1 事件类别

至少覆盖：

- `DOMESTIC_TOP_LEVEL_POLICY`：政治局、中央财经委员会、中央经济工作会议、国务院常务会议、全国两会等；
- `MONETARY_POLICY`：央行政策、MLF、LPR、OMO、降准降息、货币政策报告与沟通；
- `FISCAL_POLICY`：预算、专项债、特别国债、税费、财政支出与化债；
- `REGULATORY_POLICY`：证监会、交易所、金融监管总局、外汇局等规则；
- `INDUSTRIAL_POLICY`：发改委、工信部、国资委、能源局、卫健委、住建部、商务部等；
- `MACRO_DATA`：GDP、PMI、CPI/PPI、工业、社零、投资、地产、就业、社融、信贷、进出口；
- `COMPANY_EVENT`：公告、业绩、回购、增减持、并购、订单、产品和监管；
- `TECHNOLOGY_EVENT`：发布会、论文、模型、芯片、产业会议、技术验证；
- `GEOPOLITICAL_EVENT`：战争、制裁、外交、贸易限制、航运与供应链中断；
- `GLOBAL_MACRO_POLICY`：美联储、ECB、BOJ、全球财政与监管；
- `COMMODITY_ENERGY`：OPEC、EIA、IEA、原油、黄金、铜、铁矿石、煤炭、农产品；
- `FINANCIAL_STABILITY`：流动性、信用、房地产、银行、非银和市场稳定政策；
- `RUMOR_AND_LEAK`：未经证实消息、试探性放风、媒体引述和市场传闻。

### 3.2 日历状态

每个事件必须使用以下状态之一：

- `CONFIRMED_SCHEDULED`：官方已确认具体时间；
- `CONFIRMED_WINDOW`：官方确认期间但未给具体时点；
- `RECURRING_HIGH_PRIOR_WINDOW`：历史规律形成高先验窗口，未被官方确认；
- `MARKET_EXPECTED`：市场机构普遍预期；
- `RUMORED`：存在来源可追溯的传闻；
- `UNSCHEDULED_OCCURRED`：突发事件已经发生；
- `POSTPONED / CANCELLED / DENIED / SUPERSEDED`。

系统不得把`RECURRING_HIGH_PRIOR_WINDOW`显示成确定日期。

## 4. 来源权威和传播层级

### 4.1 来源等级

- `A1 OFFICIAL_PRIMARY`：中国政府网、新华社原始通稿、中央及国务院部门、央行、统计局、财政部、证监会、交易所和国际官方机构；
- `A2 OFFICIAL_AUTHORIZED_MEDIA`：官方授权发布和国家级权威媒体；
- `B1 INSTITUTIONAL_PRIMARY`：上市公司公告、指数公司、交易所数据、国际组织、评级与行业组织；
- `B2 PROFESSIONAL_MARKET_SOURCE`：许可明确的专业数据和机构研究；
- `C1 MAJOR_MEDIA`：具备采编和更正机制的主要媒体；
- `C2 EXPERT_INTERPRETATION`：可识别作者和方法的专家解释；
- `D SOCIAL_OR_RUMOR`：自媒体、匿名消息、群聊和未验证转载。

来源等级不等于结论正确。每条Claim还要记录独立证据、反证、历史准确率和利益冲突。

### 4.2 传播链

```text
事件或政策准备
→ 官方草案/征求意见/会议窗口
→ 专业机构预期与市场定价
→ 传闻、媒体报道和搜索需求
→ 官方发布
→ 权威解读与执行细则
→ 产业、公司和资金行为
→ 事后修订、否认或效果评估
```

系统必须保存首次出现、首次被主流确认、首次被官方确认和首次可交易使用的时间。

## 5. 核心对象

### 5.1 `PolicyMacroEvent`

```yaml
PolicyMacroEvent:
  event_id: string
  event_family_id: string
  event_type: enum
  jurisdiction: string
  authority_entities: list
  calendar_status: enum
  expected_window_start: datetime | null
  expected_window_end: datetime | null
  scheduled_at: datetime | null
  event_time: datetime | null
  first_public_at: datetime | null
  published_at: datetime | null
  available_at: datetime
  market_effective_at: datetime
  source_refs: list
  source_grade: enum
  rule_or_policy_version: string | null
  topic_entities: list
  affected_asset_classes: list
  status: CANDIDATE | CONFIRMED | DENIED | SUPERSEDED | INVALIDATED
```

### 5.2 `ExpectationSnapshot`

事件前必须冻结：

- 共识方向；
- 点预测、区间和分布；
- 预测来源和样本数；
- 机构分歧；
- 市场隐含预期；
- 文本预期和政策关键词概率；
- 当前价格已经计入的程度；
- UNKNOWN质量。

### 5.3 `PolicySurpriseVector`

惊喜不得只有一个正负分数，至少拆成：

- `headline_numeric_surprise`；
- `policy_stance_surprise`；
- `policy_path_surprise`；
- `implementation_strength_surprise`；
- `timing_surprise`；
- `growth_information_surprise`；
- `inflation_information_surprise`；
- `financial_stability_surprise`；
- `risk_premium_surprise`；
- `text_novelty`；
- `latent_detail_factor`；
- `credibility_and_follow_through`。

### 5.4 `CrossAssetReactionMap`

至少记录：

- A股指数、行业、风格和个股；
- 港股、A/H价差和中概；
- 国债1Y/2Y/5Y/10Y/30Y收益率和期限利差；
- 资金利率、回购、IRS和信用利差；
- CNY/CNH、美元指数和主要外汇；
- 股指期货、国债期货、期权波动率与偏度；
- 原油、黄金、铜、铁矿、煤炭、农产品和航运；
- ETF份额、北向活动和W13参与者资金证据；
- 市场广度、成交、流动性和相关结构。

“异常”既包括单个资产跳动，也包括常见关系失效，例如股跌债不涨、宽松预期下人民币不弱、油涨但能源股不涨。

### 5.5 `EventPricingState`

状态机：

```text
UNPRICED
→ EXPECTATION_BUILDING
→ PRE_EVENT_RUNUP_OR_HEDGE
→ PARTIALLY_PRICED
→ FULLY_OR_OVER_PRICED
→ ANNOUNCEMENT_SURPRISE
→ CONTINUATION / SELL_THE_NEWS / REVERSAL / POST_EVENT_DRIFT
→ DIGESTED / INVALIDATED
```

核心字段：

- `pre_runup_score`；
- `hedging_pressure_score`；
- `priced_in_ratio_band`；
- `announcement_gap`；
- `reaction_consistency`；
- `post_event_drift`；
- `reversal_probability`；
- `leakage_hypothesis_probability`；
- `public_inference_probability`；
- `liquidity_explanation_probability`。

### 5.6 `PolicyTransmissionGraph`

每个政策事件映射：

```text
政策工具
→ 直接目标
→ 融资/需求/成本/监管/供给/风险偏好渠道
→ 行业与产业链
→ 公司业务与财务变量
→ 估值、现金流和风险溢价
→ 生效时滞
→ 支持证据、反证和失效条件
```

必须区分：

- 直接受益；
- 二阶供应链受益；
- 替代和挤出效应；
- 短期题材与长期基本面；
- 政策意图与真实执行；
- 全国政策与地区执行差异。

## 6. 十二个子模块

| id | 子模块 | 责任 | 初始优先级 |
|---|---|---|---|
| `PMN-01` | Official Source & Calendar Registry | 官方来源、日程、历史窗口、许可和修订 | P0 |
| `PMN-02` | Event/Claim/Evidence Normalizer | 事件、Claim、来源、时间和证据合同 | P0 |
| `PMN-03` | Expectation & Consensus Freezer | 事前共识、分歧、市场隐含预期和UNKNOWN | P0 |
| `PMN-04` | Policy Surprise Compiler | 数字、措辞、路径、力度、时点和隐含信息惊喜 | P1 |
| `PMN-05` | Rumor/Leak/Trial-Balloon Intelligence | 传闻聚类、来源链、证实/否认和抢跑假设 | P1 |
| `PMN-06` | Cross-Asset Anomaly Interpreter | 股票、债券、汇率、商品、波动率和关系异常 | P0 |
| `PMN-07` | Pre-Runup & Sell-the-News State Machine | 抢跑、计价、兑现、反转和漂移 | P1 |
| `PMN-08` | China Policy Transmission Graph | 政策到行业、公司和财务变量的传导图 | P1 |
| `PMN-09` | Geopolitical/Commodity Shock Mapper | 战争、制裁、能源、航运和供应链映射 | P1 |
| `PMN-10` | Daily/Weekly Intelligence Bulletin | 未来窗口、当日事件、跨资产解释和待观察 | P0 |
| `PMN-11` | Point-in-Time Replay & Validation | 事件回放、预期冻结、因果/预测和增量验证 | P0 |
| `PMN-12` | Drift, Calibration & Retirement | 来源准确率、模型漂移、降权、冻结和退役 | P1 |

## 7. 每日运行链

### 7.1 盘前

- 未来30/90日官方确认日历；
- 历史高先验但未确认的政策窗口；
- 国际宏观、战争、制裁、商品和科技事件；
- 事前共识、分歧和市场已计价程度；
- 潜在A股传导链和最需要补的信息。

### 7.2 盘中

- 只处理当时已经合法可用的官方消息与授权数据；
- 检测跨资产和资产关系异常；
- 比较当前反应与历史条件分布；
- 更新竞争性解释，不把价格先动直接写成泄漏。

### 7.3 收盘后与夜间

- 收集官方发布、全文、修订和权威解读；
- 计算惊喜向量和文本差分；
- 判断抢跑、兑现、漂移和反转；
- 映射行业、公司、W13资金证据和W6参与者反应；
- 生成点时日报并进入回放。

### 7.4 周度/月度

- 未来政策窗口和数据日历；
- 来源历史准确率；
- 传闻证实率和平均领先时间；
- 事件模型校准、漂移和退役；
- 政策执行进度和效果追踪。

## 8. 日报输出

```yaml
PolicyMacroNewsBulletin:
  bulletin_time: datetime
  knowledge_cutoff: datetime
  confirmed_calendar: list
  high_prior_unconfirmed_windows: list
  current_events: list
  expectation_snapshots: list
  policy_surprise_vectors: list
  cross_asset_anomalies: list
  pricing_states: list
  rumor_and_leak_hypotheses: list
  policy_transmission_maps: list
  a_share_sector_company_impacts: list
  w13_participant_flow_context: list
  supporting_evidence: list
  counterevidence: list
  competing_explanations: list
  next_most_valuable_information: list
  abstentions: list
  validation_status: string
  no_trade_gate: true
```

## 9. 多技能联动

- **W2**：行情、收益率曲线、交易日历、规则、点时数据和回放权威；
- **W4**：将消息和政策形成可注册、可消融的因子/策略候选；
- **W5**：本技能的事件、新闻、公告和注意力权威边界；
- **W6**：消费政策环境和信息差，模拟不同参与者响应，不能反写事实；
- **W7**：验证、风险、尾部、流动性和因果边界否决；
- **W9**：影子日报、误报漏报、时点错误和工程学习；
- **W10**：在DecisionEpisode冻结当时消息、预期和判断；
- **W11**：只读消费概率、收益分布和不确定性，W5不得直接定仓；
- **W12**：DS-02概率融合、DS-03信息价值、DS-04模糊性、DS-10多重检验、DS-11漂移、DS-12归因；
- **W13**：提供机构、北向、被动、活跃席位和国家队背景资金证据，帮助区分政策交易与普通资金波动。

## 10. 回测与验证总原则

必须同时通过：

1. `EVENT_AND_CLAIM_VALIDATION`：事件、来源、传闻、确认和否认分类是否正确；
2. `EXPECTATION_AND_SURPRISE_VALIDATION`：事前预期是否真实冻结，惊喜是否可复现；
3. `CROSS_ASSET_EXPLANATION_VALIDATION`：解释能否覆盖多资产反应并保留替代解释；
4. `A_SHARE_ECONOMIC_INCREMENT_VALIDATION`：在完整母系统基准上是否有稳定样本外增量；
5. `SHADOW_OPERATION_VALIDATION`：每日预警、日历和报告的时效、校准和弃权是否合格。

不得用单次政治局会议、单次降准或单次战争事件证明技能有效。

完整协议见：

`coordination/BLUEPRINTS/A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-VALIDATION-BACKTEST-PROTOCOL-v1.0.md`

## 11. 首个纵向切片

### `W5-PMN-VS1 Policy Calendar + Event Packet + Cross-Asset Shadow Bulletin`

首版只做：

- 中国官方政策与宏观数据来源注册；
- 已确认日历与高先验未确认窗口分离；
- 事件、Claim、证据和修订的点时包；
- 事前预期和UNKNOWN快照；
- 国债收益率曲线、人民币、主要指数、商品和市场广度的跨资产反应；
- 抢跑/计价/兑现的规则基线；
- 事实优先、反证齐全的影子日报；
- P2/P3回放适配和基础事件验证。

首版不做：

- 未授权付费数据抓取；
- 匿名传闻自动升级为事实；
- “内幕资金”账户识别；
- 大规模LLM自主交易；
- 实盘订单；
- 未校准的综合消息分数。

## 12. 成熟度状态机

```text
DISCOVERED
→ CANDIDATE_SKILL_REGISTERED
→ SOURCE_CALENDAR_AND_SCHEMA_CONTRACTED
→ POINT_IN_TIME_DATA_READY
→ EVENT_AND_SURPRISE_VALIDATED
→ CROSS_ASSET_AND_A_SHARE_INCREMENT_VALIDATED
→ SHADOW_BULLETIN_VALIDATED
→ VALIDATED_RESEARCH_CAPABILITY
```

当前状态：

- 蓝图：`COMPLETE`
- 机器Skill合同：`REGISTERED_CANDIDATE`
- 研究验证协议：`COMPLETE`
- 数据适配器：`NOT_IMPLEMENTED`
- 政策日历：`NOT_ASSEMBLED`
- 事前预期数据集：`NOT_ASSEMBLED`
- 抢跑/兑现模型：`NOT_IMPLEMENTED`
- 回测：`NOT_RUN`
- 影子日报：`NOT_STARTED`
- 实盘：`PROHIBITED`

## 13. 成功标准

- 官方确认日程、高先验窗口和传闻严格分离；
- 所有事件有`published_at / available_at / market_effective_at`；
- 事前预期和分歧在事件发生前冻结；
- 消息惊喜至少拆成数字、政策立场、路径、执行力度、增长信息和风险溢价；
- 抢跑不被自动解释为泄漏；
- 跨资产异常包含关系异常和替代解释；
- A股传导图区分直接、二阶、题材和基本面；
- 不同时期、政策类型、市场状态和持有期均报告；
- `B3 + PMN`在样本外、成本后稳定优于`B3`或能显著改善风险/弃权；
- 影子日报通过时效、来源、校准、漂移和安全门；
- 所有输出保持`NO_TRADE`。
