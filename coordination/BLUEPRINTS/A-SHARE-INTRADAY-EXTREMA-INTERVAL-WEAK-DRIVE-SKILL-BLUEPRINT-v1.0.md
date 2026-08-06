# A股日内极值间隔与弱驱动状态识别技能蓝图 v1.0

> `agent_id: GPT`
>
> `module_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-0013`
>
> `skill_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-WEAK-DRIVE-SKILL-0013`
>
> `implementation_issue: #188`
>
> `status: CANDIDATE_BLUEPRINT_REGISTERED / EMPIRICAL_A_SHARE_VALIDATION_REQUIRED`
>
> `boundary: research_only / NO_TRADE`

## 一、原始观察与当前结论

用户观察：

> 在没有强烈买入或卖出时，日内某个阶段的最高点与最低点之间，常相差约20至30分钟。

本蓝图不把这句话直接升级为规律，而把它拆成一个可复现、可证伪、可分层的候选假设：

```text
H20_30:
在精确定义的弱方向驱动状态下，连续确认的日内局部极值之间，
以有效交易分钟计量的持续时间分布，是否在20至30分钟区间存在
跨股票、跨时期、跨市场状态、跨阈值仍稳定的条件性超额概率质量？
```

截至v1.0：

- 学术与市场微观结构研究明确支持日内成交、波动、价差和交易间隔具有显著时段季节性；
- 方向变化（Directional Change）与内在时间（Intrinsic Time）提供了比任意固定窗口更适合定义局部极值和持续时间的事件化框架；
- 现有公开高质量证据没有证明A股普遍存在固定的“20至30分钟高低点间隔规律”；
- 因此20至30分钟只能作为预注册待检验区间，不能成为硬编码交易参数、止盈止损时钟或买卖理由。

## 二、用户认知四层映射

### 2.1 用户知道且已经说出的部分

1. 日内价格不是随机散点，而有阶段性的高点、低点和转折节奏；
2. 当盘面没有明显单边买卖压力时，极值之间可能存在大约20至30分钟的常见间隔；
3. 单一指标不够，需要结合量、价、资金、市场环境和其他技能；
4. 结论必须经过多个时期和回测验证，不能凭肉眼案例升级。

### 2.2 用户已经隐含知道但没有完整说出的部分

1. “阶段”必须先定义，开盘、上午中段、午后重启、尾盘不能混在一起；
2. “没有强烈买入卖出”不能靠感觉，至少需要价格效率、成交量异常、VWAP斜率、波动、盘口失衡和板块残差等代理；
3. 趋势日、消息日、涨跌停附近、停复牌、开盘价格发现期会破坏20至30分钟节奏；
4. 极值必须在事后才能完全确认，实时系统只能知道“距上一个已确认极值多久”，不能提前知道当前点就是最终高低点；
5. 午休90分钟不是市场活动时间，不能把11:30至13:00直接算进极值间隔。

### 2.3 用户尚未系统掌握但容易理解的部分

1. **钟表时间与事件时间**：20分钟只是钟表长度；相同20分钟在清淡盘和剧烈盘里包含的市场事件量不同；
2. **方向变化事件**：价格从局部极值反向达到预设阈值，才确认一次方向变化；
3. **首次到达时间**：从一个状态到价格首次穿过某个阈值所花的时间；
4. **生存函数与风险率**：不是问“会不会20分钟反转”，而是问“已经持续t分钟仍未形成下一极值时，下一小段时间形成极值的条件概率如何变化”；
5. **时段季节性去偏**：开盘前一小时的价差和波动结构与中午不同，需要先标准化后再比较；
6. **条件分布而非单一均值**：均值20分钟可能来自大量5分钟与少量60分钟的混合，必须查看中位数、分位数、众数、尾部和置信区间。

### 2.4 用户尚未掌握且需要系统隐藏复杂度的部分

1. 停止时间、删失数据与竞争风险；
2. 点过程、Hawkes过程、事件强度与状态依赖风险率；
3. 微观结构噪声、买卖价反弹、离散价格和错误极值；
4. 内在时间与物理时间之间的尺度关系；
5. 多重检验、参数搜索偏差、PBO、Deflated Sharpe Ratio与选择者偏差；
6. 点时成分股、退市样本、公司行动、历史涨跌停规则和成交可执行性；
7. 这些复杂项由技能内部合同、验证器和报告承担，不向用户输出伪精确数学结论。

## 三、术语与对象映射

| 日常说法 | 研究术语 | 机器对象 | 关键风险 |
|---|---|---|---|
| 阶段高点/低点 | Local extrema / swing extrema | `ConfirmedExtremum` | 事后确认与前视泄漏 |
| 高低点相隔多久 | Duration / waiting time | `ExtremumIntervalObservation` | 午休、停牌、集合竞价计时错误 |
| 没有强买强卖 | Weak directional drive | `WeakDriveProxyState` | bar代理冒充真实订单流 |
| 20至30分钟 | Preregistered duration band | `DurationBand(20,30)` | 事后调参和图形错觉 |
| 容易转折的时间 | Conditional hazard | `ExtremumHazardEstimate` | 把概率误解成必然 |
| 市场节奏 | Intraday seasonality | `SessionSeasonalityProfile` | 开盘尾盘混合偏差 |
| 按波动而非钟表分段 | Directional-change intrinsic time | `DirectionalChangeEvent` | 阈值敏感与市场迁移 |
| 冲高回落/探底回升 | Drawup/drawdown and overshoot | `DrawEvent` / `OvershootEvent` | 用收盘bar掩盖路径 |
| 横盘震荡 | Mean-reverting or low-efficiency regime | `RegimePosterior` | 震荡与低流动性混淆 |

## 四、核心定义

### 4.1 有效交易分钟

`active_trading_minute`只累计当前证券允许连续竞价且存在有效行情的分钟：

- 上午连续竞价与下午连续竞价分别计时；
- 午休不累计；
- 停牌、无有效行情、数据断层不累计；
- 开盘集合竞价、收盘集合竞价单独建模，不与连续竞价持续时间混算；
- 交易阶段由按生效日版本化的A股规则包提供，禁止永久硬编码。

### 4.2 四种极值定义必须分开验证

#### A. 固定窗口极值

在长度为W的窗口内取最高/最低。仅用于描述和基线，因W本身会制造接近W的间隔结构。

#### B. 对称局部极值标签

若某点高于前后各k根bar，则事后标为局部高点，低点同理。只能用于训练标签或研究，不能成为实时输入。

#### C. 方向变化极值

从当前局部极值反向移动达到阈值δ时，确认先前极值。δ必须使用预注册网格，并可按时段波动标准化。该方法是本技能的主要研究定义。

#### D. 首次到达/返回间隔

测量价格、波动或VWAP偏离首次达到某阈值所需的有效交易分钟，用于检验20至30分钟是否只是某种波动尺度的结果。

四种定义不得混成一个结果。若只有固定窗口支持20至30分钟，而方向变化和首次到达不支持，应判定为窗口构造伪影。

### 4.3 弱驱动只能输出代理状态

在没有验证逐笔委托、逐笔成交、订单ID、撤单和队列重建前，系统不得输出“没有强烈真实买入/卖出”。第一阶段只能输出：

```text
WEAK_DRIVE_PROXY
STRONG_UP_DRIVE_PROXY
STRONG_DOWN_DRIVE_PROXY
MIXED_OR_CONFLICTED
INSUFFICIENT_DATA
```

`WEAK_DRIVE_PROXY`候选条件由多项共同构成：

1. 过去5/15/30分钟绝对异常收益不高；
2. 路径效率比低，净位移相对于总路径长度较小；
3. 波动和真实波幅没有进入异常爆发区；
4. 成交量/成交额相对于同股同时段季节基线没有显著冲击；
5. VWAP或AVWAP斜率、价格偏离和回收速度较温和；
6. 盘口数据新鲜时，五档失衡、价差与深度冲击不极端；
7. 相对指数、行业和同题材残差不极端；
8. 不处于涨跌停邻近、开盘快速价格发现、午后刚复市、临停复牌、重大公告或极端市场状态；
9. 多项证据冲突时输出`MIXED_OR_CONFLICTED`，不得强行归类。

### 4.4 持续时间与风险率

对相邻两个已确认方向变化极值：

```text
T_i = active_trading_minutes(extremum_i, extremum_{i+1})
BandMass_20_30 = P(20 <= T_i <= 30 | state, phase, liquidity, regime, threshold)
```

实时输出不预测“第25分钟一定反转”，而输出：

```text
elapsed_since_last_confirmed_extremum
survival_probability
next_5m_extremum_hazard
next_10m_extremum_hazard
conditional_duration_quantiles
20_30_band_support_score
```

## 五、机制假设图

### 5.1 支持20至30分钟候选的可能机制

1. 弱方向驱动时，短期库存、被动流动性供给和均值回归形成有限寿命；
2. 执行算法以时间片分批交易，造成短周期冲击、恢复和再平衡；
3. 市场参与者在5/15/30分钟等常用观察窗形成同步反馈；
4. 价格偏离VWAP后，在低趋势效率状态中逐渐回归；
5. 局部流动性扫掠后，价差、深度和订单流韧性需要一定恢复时间；
6. T+1、库存锁定和当日可卖量结构可能改变买卖反馈的不对称性。

这些均为候选机制，不是已确认因果。

### 5.2 最强反方

1. 20至30分钟来自人眼选择“看起来像阶段”的窗口；
2. 方向变化持续时间理论上随阈值、波动和流动性变化，不应固定；
3. 开盘前一小时的A股价差、波动和成交结构快速松弛，混合后容易制造20至30分钟峰值；
4. 5分钟bar会把真实持续时间量化成5的倍数，导致20/25/30分钟机械聚集；
5. 午休、停牌或缺失bar被错误计时；
6. 只看活跃股票、成功案例或近期行情形成选择偏差；
7. 趋势日和重大事件日的极值可能相隔数小时或仅几分钟；
8. 同一日的最高点和最低点与“连续局部极值”不是同一对象。

## 六、系统架构

```text
W2点时市场数据与规则快照
→ SessionClock / DataQualityGate
→ IntradaySeasonalityNormalizer
→ WeakDriveProxyClassifier
→ ExtremumLabeller（研究后验）
→ OnlineConfirmedExtremumState（实时仅已确认）
→ DurationAndHazardEstimator
→ Regime/Liquidity/Board Conditional Model
→ ProbabilityFusion
→ TimingAdvisory / Abstain / Monitor
→ W7验证与风险门
→ W9影子模式
→ DecisionEpisode与知识回写
```

## 七、输入合同

### 7.1 第一阶段最低输入

- 1分钟OHLCV与成交额；
- 交易所、板块、证券状态和历史规则快照；
- 复权与公司行动边界信息；
- 点时指数、行业和同题材基准；
- VWAP及相对成交量；
- 数据新鲜度、缺失、停牌、涨跌停和异常标记。

### 7.2 增强输入

- 五档盘口、价差、深度和失衡；
- 可验证的TdxQuant/TDX增量聚合字段；
- 真实逐笔成交、逐笔委托、撤单和队列，仅在字段语义和许可验证后启用；
- 公告、新闻和事件可用时点；
- 指数期货、ETF和跨标的共同冲击代理。

禁止把供应商资金流分类、内外盘或五档快照冒充真实主动买卖方向。

## 八、输出合同

```yaml
IntradayExtremaTimingAssessment:
  instrument_id: string
  rule_snapshot_id: string
  data_snapshot_id: string
  event_definition: FIXED_WINDOW|SYMMETRIC_LABEL|DIRECTIONAL_CHANGE|FIRST_PASSAGE
  threshold_version: string
  session_phase: string
  drive_state: WEAK_DRIVE_PROXY|STRONG_UP_DRIVE_PROXY|STRONG_DOWN_DRIVE_PROXY|MIXED_OR_CONFLICTED|INSUFFICIENT_DATA
  drive_evidence: []
  last_confirmed_extremum: {type: HIGH|LOW, timestamp: timestamp, price: number}|null
  elapsed_active_minutes: number|null
  duration_quantiles: {p10: number, p25: number, p50: number, p75: number, p90: number}
  band_20_30_probability: number|null
  band_20_30_baseline_probability: number|null
  incremental_support: number|null
  next_5m_hazard: number|null
  next_10m_hazard: number|null
  calibration_status: string
  confidence: HIGH|MEDIUM|LOW
  invalidation_conditions: []
  action_class: MONITOR|WAIT|DEFER|ABSTAIN|RESEARCH_ONLY
  no_trade: true
```

本技能不直接输出`BUY`或`SELL`。

## 九、与现有技能联动

| 现有技能/模块 | 联动职责 | 禁止替代 |
|---|---|---|
| `market-context` / 状态衰减 | 判断趋势、震荡、恐慌、事件和流动性状态 | 极值时间特征替代市场状态 |
| `opening-range` | 识别开盘价格发现和开盘区间 | 把开盘节奏推广全天 |
| `vwap-analyzer` | 偏离、斜率、回收和执行基准 | 单独用VWAP断言反转 |
| `volume-battle-analyzer` | 成交努力、异常量与价格结果 | 供应商资金分类冒充订单流 |
| `liquidity-sweep` | 预先流动性区、穿越、收复、持续/失败 | 见到刺穿就叫扫单 |
| `order-flow-microstructure` | OFI、Delta、CVD、价差和韧性，需真实数据 | bar代理冒充逐笔证据 |
| `sector-flow-radar` / `market-context` | 指数、板块和主题共同冲击 | 个股波动误判为自身驱动 |
| `event-radar` | 排除公告、政策和消息驱动状态 | 把事件日放入弱驱动样本 |
| `t1-lockup-tracking` | 可卖库存、隔夜风险和反馈延迟 | 生成当日买入后可卖假设 |
| `probability-fusion` | 将时长风险率作为一个条件证据 | 把20至30分钟变成主导总分 |
| `backtest-integrity-audit` | 前视、样本外、多重检验和成本审计 | 用一次漂亮回测晋级 |

## 十、A股专属适配

1. 上午与下午分别建时段季节基线；
2. 09:30后价格发现与价差松弛单独建模；
3. 13:00复市的第一批bar单独建模；
4. 14:57后收盘集合竞价不进入普通连续竞价极值间隔；
5. T+1使新开仓无法当日卖出，本技能即使发现潜在转折也不能据此虚构可执行止损；
6. 涨跌停、临停、停牌、除权、上市初期与风险警示状态分别处理；
7. 主板、创业板、科创板、北交所、ETF、低流动性股票不能共享一个未分层参数；
8. 历史回测按当时有效交易规则和费用回放。

## 十一、成熟度和晋级门

```text
CANDIDATE_BLUEPRINT
→ RESEARCH_DATA_READY
→ DESCRIPTIVE_VALIDATED
→ PREDICTIVE_OOS_VALIDATED
→ COMBINATION_OOS_VALIDATED
→ SHADOW
→ RETIRED或进一步审批
```

不得跳级。晋级最低条件：

1. 20至30分钟区间在预注册定义下有稳定样本外增量，而不是事后选出的最佳区间；
2. 至少四种市场阶段、多个流动性层、多个板块和多个历史时期方向一致；
3. 更换方向变化阈值和bar频率后结论不崩塌；
4. 控制时段季节性、波动、成交量、指数/板块和事件后仍有增量；
5. 概率预测有校准增益，优于仅使用时段和波动的简单基线；
6. 与其他技能组合时通过消融，证明不是其他信号的重复包装；
7. 通过purged walk-forward、embargo、lockbox、PBO/DSR与成本压力测试；
8. 影子运行保留所有失败、漂移和失效条件；
9. 用户审批前始终`NO_TRADE`。

## 十二、当前状态

```yaml
module_id: A-SHARE-INTRADAY-EXTREMA-INTERVAL-0013
blueprint: COMPLETE
research_validation_design: COMPLETE
machine_skill_contract: COMPLETE
implementation_issue: 188
empirical_a_share_backtest: NOT_RUN_DATA_UNAVAILABLE_IN_CURRENT_GPT_SESSION
hypothesis_20_30: UNVERIFIED
standalone_signal: PROHIBITED
shadow_mode: NOT_STARTED
live_trading: PROHIBITED
codex_dispatch: PENDING_AFTER_ACTIVE_E56_AND_DATA_GATE
qclaw_relation: E44_PARALLEL_NO_CROSS_BRANCH_WRITE
```

## 十三、证据与参考地图

### 高可信基础

- 上海证券交易所、深圳证券交易所交易时段与竞价规则；
- Cont、Kukanov、Stoikov：订单流失衡、市场深度与短期价格冲击；Journal of Financial Econometrics, DOI `10.1093/jjfinec/nbt003`；
- Bailey、Borwein、López de Prado、Zhu：Probability of Backtest Overfitting与CSCV；Journal of Computational Finance, DOI `10.21314/JCF.2016.322`。

### 中高可信方法

- Aloud、Tsang、Olsen、Dupuis：Directional-Change Events与内在时间；
- Petrov、Golub、Olsen：方向变化阈值与局部极值事件；Quantitative Finance, DOI `10.1080/14697688.2019.1669809`；
- Ni、Zhou：1364只中国A股价差的日内L形与开盘后幂律松弛；DOI `10.3938/jkps.54.786`；
- Nishimura、Sun：中国股票指数与股指期货的5分钟成交量、波动和日内周期；DOI `10.1111/ajfs.12117`。

### A股相关但需继续验证

- 中国股票市场方向变化波动测量研究，可作为方法候选，不能直接证明20至30分钟；
- 2026年关于T+1延迟反馈与日内反转的SSRN预印本，可作为机制线索，未升级为正式因果定论；
- AKShare分钟接口可作研究期辅助适配器，但上游网页口径、历史范围、复权和稳定性必须单独审计，不能替代交易所或已验证本地数据源。
