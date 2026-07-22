# A股每日参与者资金情报系统蓝图 v1.0

> module_id: `A-SHARE-DAILY-PARTICIPANT-CAPITAL-FLOW-INTELLIGENCE-0014`
>
> workstream: `W13`
>
> status: `REGISTERED_CANDIDATE / NOT_IMPLEMENTED`
>
> boundary: `research_only / NO_TRADE`
>
> decision_owner: `GPT`
>
> implementation_owner_candidate: `CODEX + WORKBUDDY`
>
> research_and_adversarial_support: `QCLAW`

## 0. 结论

现有系统已经拥有三块可复用基础：

1. 多参与者博弈与优势/弱点矩阵，明确量化、短线活跃资金、大资金机构库存和散户的可观察轨迹与误分类风险；
2. `A-SHARE-CAPITAL-INTENT-MULTISCALE-EVIDENCE-BLUEPRINT-0001`，已经要求竞争性参与者假设、证据簇、能力门禁和多周期验证；
3. P2确定性离线回放，已经具备点时可用性、T+1、涨跌停、停牌、成本、滑点和`NO_TRADE`边界。

但当前没有形成可持续运行的“每日参与者资金情报能力”。缺失项包括：

- 机构、北向、短线活跃席位、被动/量化、国家队背景资金的每日官方证据采集；
- 2024年北向披露制度调整后的语义切换；
- 龙虎榜席位别名与席位网络；
- ETF申赎、份额、指数调整和收盘竞价等被动/量化代理；
- 国家队背景资金的证据分级与稳定市场行为假设；
- 每日统一资金地图、反证、未知项和日报；
- 身份识别校准与经济增量价值的分层回测；
- 跨制度、跨市场状态、跨周期和多技能交互验证。

因此，W13不是第二套行情、证据或回放系统，而是复用W2、W5、W6、W7、W9、W10、W11、W12的**参与者资金证据编译层与每日情报产品层**。

## 1. 第一原则

### 1.1 研究目标

系统回答的不是：

> “今天国家队、机构或某游资到底买了多少？”

而是：

> “在当前规则、数据权限和披露时点下，哪些参与者资金行为得到哪些等级的证据支持？有哪些竞争性解释？这种解释在对应持有期和市场状态中是否经过点时、样本外和经济增量验证？”

### 1.2 三项不可违反的边界

1. **可观察事实不等于参与者身份。** 成交、盘口、ETF份额或券商营业部席位只能支持候选解释，除非官方披露直接提供对应身份。
2. **成交活跃度不等于净买入。** 总成交额、额度余额、龙虎榜成交和ETF成交必须与买卖方向、持仓变化和库存压力分开。
3. **预测有效不等于因果正确。** 即使一个参与者代理能够预测收益，也不能自动证明该参与者造成了收益。

### 1.3 允许输出

- `OFFICIAL_DISCLOSED_FACT`
- `OFFICIAL_AGGREGATE_ACTIVITY`
- `PUBLIC_SEAT_EVIDENCE`
- `PERIODIC_OWNERSHIP_EVIDENCE`
- `CALIBRATED_MARKET_PROXY`
- `PARTICIPANT_FLOW_HYPOTHESIS`
- `COMPETING_EXPLANATIONS`
- `ABSTAIN`
- `INSUFFICIENT_OBSERVABILITY`

### 1.4 禁止输出

- 没有账户级证据却断言真实账户身份；
- 把北向总成交额写成北向净买入；
- 把龙虎榜营业部写成某位个人游资；
- 把ETF份额变化全部归因于国家队；
- 把供应商“主力净流入”字段当作交易所原始事实；
- 用事后持仓披露回填并假装当日已经知道；
- 在低能力数据上输出高能力订单流结论。

## 2. 用户知识四层映射

### 2.1 用户明确知道并提出

- 机构、量化、北向、游资和国家队背景资金的每日动向越来越重要；
- A股中机构和具有稳定市场职责或国家队背景的资金需要单独跟踪；
- 不能只看单一指标，需要多个技能、参数与关联关系叠加；
- 必须跨不同时期回测并判断可信度。

### 2.2 用户知道但未显式说出的隐含要求

- 同一笔交易可能同时符合“机构执行”“指数被动”“量化拆单”等多种解释；
- 资金影响依赖市值、流动性、市场阶段、持有期和拥挤度；
- 资金流强度、持仓变化、库存持续性和价格冲击是不同对象；
- 日内观察、收盘后披露、季度持仓与事后公告有不同的`available_at`；
- T+1、涨跌停、停牌和集合竞价会改变资金行为能否兑现。

### 2.3 用户暂不了解但容易理解

- 2024年8月19日起，北向公开披露不再提供实时买卖金额和每日个股持仓，公开数据主要变为收盘后总成交、成交笔数、ETF成交、十大活跃股以及季度个股持仓；
- 龙虎榜只覆盖触发异常交易披露条件的股票，存在选择偏差；
- 券商营业部是交易通道或席位，不等同于唯一真实资金主体；
- 国家队背景资金的日度精确交易通常不可公开观测，只能结合官方公告、定期持仓、ETF份额和市场稳定行为做分级假设；
- 量化交易报告制度为监管提供更丰富信息，但不等于这些账户标签向公众开放。

### 2.4 高级专业层

- 隐状态/状态空间模型与贝叶斯后验；
- 订单流不平衡、Kyle lambda、`lambda × OIB`信息含量；
- 机构羊群效应、短期延续与中长期反转；
- LSV herding、需求系统与持仓因子；
- Hawkes过程、事件聚类与席位共现网络；
- 参与者需求冲击与跨股票价格冲击；
- 监管制度断点、结构突变和时变系数；
- 点时事件研究、合成控制、安慰剂与负对照；
- 概率校准、选择性预测和弃权；
- PBO、Deflated Sharpe、White Reality Check、Hansen SPA、Romano-Wolf多重检验。

这些高级方法只能在数据能力、可识别性和样本量满足时启用，不能作为复杂包装。

## 3. 参与者分类本体

系统不得只保留“机构/游资/散户”三个大桶。至少登记以下候选家族：

| actor_family | 含义 | 主要可观察证据 | 核心误分类风险 |
|---|---|---|---|
| `NORTHBOUND_CONNECT` | 沪深股通渠道资金 | 官方总成交、活跃股、季度持仓、历史旧制度净流数据 | 把成交额当净流；把渠道当单一外国机构 |
| `DOMESTIC_INSTITUTION` | 公募、保险、社保、私募、资管等国内机构 | 机构专用席位、定期持仓、基金份额、公告、大宗交易 | 季度数据滞后；机构之间方向相反 |
| `ETF_AP_PASSIVE` | ETF申赎、做市、指数复制和被动再平衡 | ETF份额、PCF、指数调整、成分权重、收盘竞价 | 把被动流误认主动研究型机构或国家队 |
| `PROGRAM_QUANT` | 程序化、统计套利、因子、执行算法和跨市场量化 | 批量同向交易、周期再平衡、竞价集中、跨标的结构 | 无账户标签时不可证明量化身份 |
| `ACTIVE_SHORT_TERM_SEAT` | 龙虎榜和活跃席位簇代表的短线资金 | 席位净买卖、重复席位、共现网络、次日行为 | 营业部不是个人；触发样本选择偏差 |
| `STATE_LINKED_STABILIZATION` | 中央汇金等国家队背景或稳定市场职责资金假设 | 官方公告、定期持仓、宽基ETF份额与大盘稳定模式 | 不能从ETF流量直接断言国家队金额 |
| `BROKER_PROPRIETARY` | 券商自营与做市 | 公开持仓、做市资格、席位/大宗、券商报告 | 与客户通道交易混淆 |
| `CORPORATE_INSIDER` | 回购、增减持、产业资本和重要股东 | 公司公告、交易所增减持、回购进度 | 公告时点与实际执行时点不同 |
| `MARGIN_LEVERAGED` | 融资融券和杠杆资金 | 融资余额、买入额、偿还额、融券余量 | 融资变化不等于当日方向性净买 |
| `RETAIL_RESIDUAL` | 无法归属及零售群体残差 | 账户分层数据或残差代理 | 残差不是纯散户，也可能含未识别机构 |

每个家族必须维护：优势、约束、典型持有期、观测签名、反例、误分类矩阵、证据等级、后验概率和校准状态。

## 4. 证据与可观察性分级

### 4.1 `observation_class`

1. `EXACT_DISCLOSED`：官方明确披露主体、方向、数量或持仓；
2. `OFFICIAL_AGGREGATE`：官方聚合成交、活跃度或持仓；
3. `PUBLIC_SEAT`：交易所披露席位/营业部层数据；
4. `OWNERSHIP_SNAPSHOT`：季度、半年或其他定期持仓快照；
5. `VENDOR_DERIVED`：供应商派生字段，必须冻结语义和版本；
6. `MARKET_PROXY`：由价格、成交、ETF份额、竞价等构造的代理；
7. `MODEL_INFERENCE`：由融合模型产生的参与者后验。

### 4.2 证据等级

- `A1`：官方点时、主体和字段语义明确；
- `A2`：官方聚合或触发式披露，覆盖有限但语义可靠；
- `B1`：官方定期持仓、ETF份额或公告锚点；
- `B2`：许可明确、语义冻结并经交叉核验的供应商数据；
- `C`：经过历史校准的市场代理或模型推断；
- `D`：叙事、传闻和未验证经验，只能进入研究队列，不得计入正式评分。

### 4.3 三种置信度必须分离

- `identity_confidence`：参与者身份可信度；
- `direction_confidence`：买卖或支持/抑制方向可信度；
- `amount_confidence`：金额或仓位变化精度。

例如，北向十大活跃股可能具有较高“渠道活跃度”可信度，但在新披露制度下，日度净买卖方向和个股持仓变化可信度可能很低。

## 5. 现行公开数据与制度映射

### 5.1 北向资金

必须按披露制度版本分段：

- 历史旧制度：可使用当时公开的日度净流和更高频数据，但必须记录来源、可用时点和停止日期；
- 自2024-08-19起：公开日度能力主要为收盘后市场总成交额、成交笔数、ETF成交和十大活跃证券；个股持仓改为季度披露；
- 北向每日额度与额度余额属于交易通道约束，不等于资金净买入；
- 自2026-01-12起北向程序化交易报告制度生效，监管可获得程序化交易报告，但公众系统不得假设可取得账户级标签。

北向模块必须分别输出：

- `NorthboundActivity`；
- `NorthboundTopActiveMap`；
- `NorthboundQuarterlyHoldingAnchor`；
- `NorthboundDailyHoldingNowcast`，仅为模型估计；
- `DisclosureRegimeBreakWarning`。

禁止统一输出跨全历史的“北向净流入”字段而不标制度版本。

### 5.2 国内机构

优先证据：

- 龙虎榜机构专用席位；
- 大宗交易买卖营业部；
- 公募/保险/社保/重要机构定期持仓；
- ETF和基金份额、申赎代理；
- 上市公司回购、增减持与重要股东公告；
- 融资融券和证券借贷相关公开数据；
- 机构调研、公告、业绩和指数调整作为事件上下文，不直接当交易事实。

必须区分：

- 主动机构研究流；
- 被动指数流；
- ETF做市与申赎流；
- 组合风险调整；
- 大宗交易与二级市场交易。

### 5.3 短线活跃资金与龙虎榜

建立版本化`SeatAliasRegistry`和`SeatStockTemporalGraph`：

- 营业部名称历史别名与迁移；
- 席位出现频率、净买卖、持有期和次日行为；
- 席位与股票、题材、其他席位的时序共现；
- 机构专用、深股通/沪股通专用和普通营业部分类；
- 席位簇而非个人姓名作为最小可信主体。

输出统一使用：

`ACTIVE_SHORT_TERM_SEAT_CLUSTER`

不得输出“某著名游资本人今天买入”，除非存在独立、合法且可验证的账户身份证据。

### 5.4 国家队背景与稳定市场资金

国家队模块必须以竞争性假设运行：

`STATE_LINKED_STABILIZATION_HYPOTHESIS`

证据包括：

- 中央汇金或其他官方主体公告；
- 定期持仓披露；
- 宽基ETF份额、成交与申赎异常；
- 大盘蓝筹、金融、核心指数成分的同步需求冲击；
- 市场压力、流动性收缩和政策事件；
- 与普通ETF套利、养老金、公募申赎、保险配置等替代解释的比较。

该模块可以输出“稳定市场资金假设后验上升”，不能输出未经披露的日度精确买入额。

### 5.5 程序化与量化

公开系统通常无法直接识别账户是否为程序化交易。因此模块只允许构造：

- 指数和ETF已知再平衡需求；
- 收盘竞价集中度；
- 横截面同步订单流/成交冲击；
- 周期性再平衡与因子拥挤；
- 跨ETF、期货、现货和成分股联动；
- 批量拆单、参与率和执行算法候选签名；
- 程序化交易制度与监管事件状态。

输出：

`PROGRAM_QUANT_ACTIVITY_HYPOTHESIS`

不得把固定节奏或大量小单直接写成量化账户事实。

## 6. 统一数据对象

### 6.1 `ParticipantFlowEvidence`

```yaml
ParticipantFlowEvidence:
  evidence_id: string
  market_date: date
  event_time: datetime
  source_time: datetime | null
  published_at: datetime
  available_at: datetime
  as_of: datetime
  instrument_id: string | null
  sector_id: string | null
  index_id: string | null
  actor_family_candidate: enum
  actor_subtype_candidate: string | null
  observation_class: enum
  evidence_grade: A1 | A2 | B1 | B2 | C | D
  measure_type: enum
  gross_buy: number | null
  gross_sell: number | null
  net_value: number | null
  turnover_value: number | null
  holding_value: number | null
  holding_delta: number | null
  creation_redemption_proxy: number | null
  activity_score: number | null
  pressure_score: number | null
  value_unit: string
  coverage_universe: object
  disclosure_trigger: object | null
  source_id: string
  source_hash: string
  source_license: string
  field_semantics_version: string
  rule_snapshot_id: string
  identity_confidence: number
  direction_confidence: number
  amount_confidence: number
  coverage_score: number
  latency_score: number
  source_reliability: number
  evidence_cluster_id: string
  supporting_evidence: list
  counterevidence: list
  alternative_explanations: list
  invalidation_conditions: list
  status: OBSERVED | NORMALIZED | CANDIDATE | FROZEN | SUPERSEDED | INVALIDATED
```

### 6.2 其他对象

- `ParticipantIdentityCandidate`
- `SeatAliasRegistry`
- `SeatStockTemporalGraph`
- `NorthboundDisclosureRegime`
- `OwnershipAnchor`
- `ETFShareAndCreationRecord`
- `ParticipantFlowPosterior`
- `ActorPressureMap`
- `InventoryPressureEstimate`
- `CrowdingAndUnwindRisk`
- `DailyParticipantFlowMap`
- `DailyParticipantFlowBulletin`
- `ParticipantFlowValidationReport`

所有对象复用母系统时间、来源、证据、规则、UNKNOWN、版本和权限合同，不建立第二套事件账本。

## 7. W13十个子模块

| id | 子模块 | 责任 | 首版状态 |
|---|---|---|---|
| `DPF-01` | Source & Rule Registry | 来源、许可、字段语义、披露制度和规则快照 | P0 |
| `DPF-02` | Official Evidence Collector | 龙虎榜、大宗、ETF、北向、融资融券、公告等官方证据适配 | P0 |
| `DPF-03` | Northbound Activity & Nowcast | 新旧披露制度切换、活跃度与季度锚定估计 | P1 |
| `DPF-04` | Domestic Institution Inventory & Flow | 机构席位、持仓、基金和大宗证据 | P1 |
| `DPF-05` | Active Seat Graph | 龙虎榜席位别名、共现、风格和复现行为 | P1 |
| `DPF-06` | State-Linked Stabilization Hypothesis | 官方锚点、ETF和稳定市场竞争性假设 | P1 |
| `DPF-07` | Program/Quant Signature Detector | 被动流、再平衡、收盘竞价和拥挤代理 | P1 |
| `DPF-08` | Actor Evidence Fusion | 证据去重、依赖聚类、后验、反证和弃权 | P1 |
| `DPF-09` | Daily Participant Flow Bulletin | 每日资金地图、变化、异常、可信度与待观察项 | P1 |
| `DPF-10` | Replay, Validation & Calibration | 身份与经济价值双重验证、漂移和退役 | P0 |

## 8. 每日运行链

```text
官方/许可来源
→ 原始工件只追加保存
→ 时间与披露制度标准化
→ 来源、许可、能力和字段语义门禁
→ 参与者证据生成
→ 同源与高相关证据聚类
→ 竞争性参与者假设
→ 多周期和市场状态融合
→ 反证、替代解释和弃权门
→ DailyParticipantFlowBulletin
→ 结果发生后的校准、降权、冻结或退役
```

### 8.1 每日最少批次

- 盘前：规则、公告、ETF PCF、指数调整和隔夜事件；
- 盘中：仅使用已授权实时行情和已验证字段，输出活动/压力代理；
- 收盘后：龙虎榜、大宗、北向官方汇总、ETF份额、融资融券和公告；
- 夜间：日报、证据冲突、回放入库和后验更新；
- 周/季：持仓锚点、席位图更新、模型重校准和制度漂移审计。

### 8.2 日报结构

```yaml
DailyParticipantFlowBulletin:
  bulletin_date: date
  rule_and_disclosure_regime: object
  market_regime: object
  source_coverage: object
  actor_summaries:
    - actor_family
      observed_facts
      inferred_direction
      posterior_band
      amount_range
      horizons
      affected_indices_sectors_instruments
      supporting_evidence
      counterevidence
      alternative_explanations
      confidence_components
      invalidation_conditions
  interaction_map: list
  crowding_and_unwind_risks: list
  next_most_valuable_information: list
  abstentions: list
  validation_status: string
  no_trade_gate: true
```

## 9. 多技能联动

### W2 市场数据与回放

- 提供原始行情、规则快照、点时数据和确定性回放；
- W13只新增适配器和参与者证据，不复制行情与回放引擎。

### W5 事件、公告与注意力

- 提供政策、公司、行业、指数调整、官方干预和消息传播上下文；
- 事件不能直接变成资金流，必须匹配可观察交易证据。

### W6 多参与者博弈

- W13提供每日参与者后验、优势激活条件和库存压力；
- W6用于对手策略与反制模拟，不能把模拟结果反写成事实。

### W7 风险与验证

- 负责多重检验、成本、流动性、尾部、容量、制度断点和最终验证门；
- 资金情报不得绕过独立风险否决。

### W9 影子模式与工程学习

- 日报先影子运行，记录漏报、误报、可用时点错误和置信度漂移；
- 未通过影子验证不得升级为稳定研究能力。

### W10 PEOS

- 将每日资金判断冻结到DecisionEpisode；
- 区分当时信息、事后结果、用户理解和模型修正。

### W11 Kelly-Thorp

- W13只能提供概率、分布、流动性和参与者压力输入；
- W13不得直接给出资金仓位，W11也不得把低可信参与者后验当确定概率。

### W12 决策科学

- DS-02融合参与者概率；
- DS-03计算是否值得继续购买/等待更高质量数据；
- DS-04处理身份与分布模糊性；
- DS-10审计参数和组合搜索；
- DS-11监控制度和模型漂移；
- DS-12归因预测、时机、仓位与执行误差。

## 10. 回测与验证总原则

W13必须同时通过两类验证：

1. **身份/方向识别验证**：参与者后验是否与后续公开锚点、席位复现、持仓变化和ETF份额变化相符；
2. **经济增量验证**：加入参与者信息后，是否在既有市场、行业、因子、事件和注意力模型之上产生稳定、成本后和样本外增量。

只通过收益预测，不能证明身份正确；只通过身份锚点，也不能证明具有交易研究价值。

完整协议见：

`coordination/BLUEPRINTS/A-SHARE-DAILY-PARTICIPANT-FLOW-VALIDATION-BACKTEST-PROTOCOL-v1.0.md`

## 11. 首个纵向切片

首版不得同时实现十个模块。推荐：

### `W13-VS1 Official Daily Evidence + Bulletin`

数据范围：

- 沪深交易所龙虎榜；
- 大宗交易；
- ETF份额/PCF和指数调整；
- 北向官方收盘后汇总、十大活跃和季度持仓；
- 现有历史旧制度北向数据，仅在来源与许可确认后；
- 官方公告中的国家队/重要机构/回购增减持事件。

输出：

- 每日官方证据账本；
- 不做人物身份断言的席位簇；
- 北向活动地图而非伪造净流；
- 国家队背景稳定市场假设与替代解释；
- 日报和`ABSTAIN`；
- 点时回放数据集与基础验证报告。

首版不做：

- 账户级真实身份识别；
- 未授权爬虫绕过登录或验证码；
- 真实下单；
- 大规模MARL；
- 未经校准的“主力净流入”总分。

## 12. 成熟度状态机

```text
DISCOVERED
→ CANDIDATE_SKILL_REGISTERED
→ SOURCE_AND_RULE_CONTRACTED
→ DATA_READY
→ IDENTIFICATION_VALIDATED
→ ECONOMIC_INCREMENT_VALIDATED
→ SHADOW_DAILY_VALIDATED
→ VALIDATED_RESEARCH_CAPABILITY
```

不得跳级。

当前状态：

- 蓝图：`COMPLETE`
- 机器Skill合同：`REGISTERED_CANDIDATE`
- 研究与验证协议：`COMPLETE`
- 数据适配器：`NOT_IMPLEMENTED`
- 每日调度：`NOT_IMPLEMENTED`
- 历史参与者数据集：`NOT_ASSEMBLED`
- 身份验证：`NOT_RUN`
- 经济增量回测：`NOT_RUN`
- 影子日报：`NOT_STARTED`
- 实盘交易：`PROHIBITED`

## 13. 成功标准

W13只有在以下条件同时满足时才能升级：

- 每个来源有官方/许可证据、时间语义、覆盖范围和字段语义版本；
- 北向新旧披露制度被正确分段；
- 席位、机构、量化和国家队代理不越级为真实身份；
- 点时回放无未来泄漏；
- 至少跨五个制度/市场时期和多个市场状态验证；
- 单技能、组合技能、交互项、消融和基准模型均有报告；
- 多重检验与实验族登记完成；
- 经济结果在成本、容量、T+1和样本外后仍有增量；
- 概率经过校准，模型能够在证据不足时弃权；
- 连续影子日报通过稳定性、漂移和误报门；
- 始终保持`research_only / NO_TRADE`。
