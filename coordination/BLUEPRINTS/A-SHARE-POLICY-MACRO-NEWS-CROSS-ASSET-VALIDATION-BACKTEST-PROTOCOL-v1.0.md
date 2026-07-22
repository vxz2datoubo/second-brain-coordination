# A股政策-宏观-消息-跨资产情报验证与回测协议 v1.0

> protocol_id: `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-VALIDATION-0015V`
>
> parent_skill: `A-SHARE-POLICY-MACRO-NEWS-CROSS-ASSET-INTELLIGENCE-SKILL-0015`
>
> status: `REGISTERED / NOT_RUN`
>
> boundary: `research_only / NO_TRADE`

## 0. 为什么不能只回测新闻后的涨跌

消息研究至少包含五个不同问题：

1. 日历或事件是否被正确识别；
2. 市场事前预期是否被真实冻结；
3. 事件的多维惊喜是否被正确提取；
4. 抢跑、兑现、漂移和反转状态是否被正确分类；
5. 加入该技能后是否在完整母系统之外产生稳定经济增量或风险改善。

只看公告后涨跌会把已计价、市场状态、风险溢价、资金冲击和同期其他事件混在一起。

## 1. 验证对象

### 1.1 事件和日历

- 官方确认的宏观数据发布时间；
- 政治局、国务院、央行、财政、监管和产业政策事件；
- 历史高先验但未确认窗口；
- 国际央行、战争、制裁和商品事件；
- 公司、行业、科技发布和重要会议；
- 延期、取消、否认、修订和执行细则。

### 1.2 预期和惊喜

- 数值共识；
- 政策方向与力度概率；
- 路径、时点和条件；
- 机构预测分歧；
- 市场隐含预期；
- 文本新颖度；
- 标题之外的潜在细节因子；
- 政策信息效应与风险溢价效应。

### 1.3 定价状态

- 事件前异常收益、成交、波动和跨资产对冲；
- 已计价比例；
- 公告瞬间反应；
- 利好兑现、利空出尽、延续、反转和后续漂移；
- 信息泄漏假设、公开推理假设和流动性假设。

### 1.4 A股传导

- 指数、行业、风格和公司；
- 直接、二阶和三阶传导；
- 基本面、估值、融资成本、风险偏好、供应链和监管渠道；
- 题材热度与真实执行进度；
- W13参与者资金和W6博弈交互。

## 2. 点时数据要求

每个事件、预期、Claim、来源和价格特征至少保留：

- `event_time`；
- `scheduled_at`；
- `expected_window_start/end`；
- `first_public_at`；
- `published_at`；
- `observed_at`；
- `ingested_at`；
- `available_at`；
- `market_effective_at`；
- `corrected_at`；
- `source_version`；
- `event_family_id`；
- `calendar_status`；
- `knowledge_cutoff`；
- `rule_snapshot_id`。

严格禁止：

- 使用事后媒体总结回填事前预期；
- 使用最终修订数据冒充首次发布值；
- 把历史规律窗口冒充确定日程；
- 把盘后发布的信息用于当日盘中策略；
- 把后来证实的传闻在历史回放中提前标为真。

任何未来泄漏使整个实验族无效。

## 3. 事件家族和时期切分

### 3.1 事件家族

至少分开报告：

- 顶层经济政策会议；
- 货币政策与央行沟通；
- 财政、债券供给和化债；
- 房地产；
- 资本市场监管；
- 科技、产业和国资政策；
- 宏观数据；
- 国际央行；
- 战争、制裁和贸易限制；
- 原油、黄金和其他商品供给冲击；
- 公司公告、财报、回购、减持和并购；
- 重大科技发布与产业会议。

不同事件族不得共用一个无条件参数。

### 3.2 中国市场时期

至少覆盖并单独报告：

- 2005股权分置改革后至2008全球危机；
- 2009刺激与后续收紧；
- 2014至2015杠杆牛市和市场稳定阶段；
- 2016熔断及监管重构；
- 2018中美摩擦和去杠杆；
- 2020疫情和全球宽松；
- 2021至2022地产、平台监管和地缘冲突；
- 2023至2024稳增长、资本市场和国家队政策阶段；
- 2025程序化规则阶段；
- 2026现行规则与当前政策环境。

具体断点必须由官方规则和事件时间复核，不得仅按年份粗切后声称制度识别。

## 4. 市场状态分层

分别验证：

- 牛、熊、震荡；
- 高低波动；
- 高低流动性；
- 通胀、通缩和再通胀预期；
- 宽松、紧缩和政策观望；
- 高低政策不确定性；
- 风险偏好、避险和流动性冲击；
- 大盘成长、小盘题材、周期和防御；
- 人民币升贬值压力；
- 商品供给冲击与需求冲击；
- 市场压力和国家队稳定假设；
- 高低拥挤与高低注意力。

状态定义必须事前冻结。

## 5. 事件窗口

### 5.1 预定事件

统一报告：

- `[-60,-21]`背景期；
- `[-20,-6]`预期形成；
- `[-5,-1]`临近抢跑；
- `[0]`公告日；
- `[+1,+3]`短期消化；
- `[+4,+10]`漂移/反转；
- `[+11,+20]`执行预期；
- `[+21,+60]`中期基本面兑现。

### 5.2 高频窗口

有准确时点时，使用：

- 公告前60/30/10分钟；
- 公告后1/5/15/30/60分钟；
- 当日收盘；
- 下一交易日开盘和收盘。

### 5.3 突发事件

使用首个可验证发布时间和首个市场可交易时点，并设置相邻无事件日、同类事件和安慰剂时点。

禁止只挑表现最好的窗口。

## 6. 事前预期验证

### 6.1 预期来源

优先级：

- 官方已公布目标或指引；
- 合法的专业机构共识；
- 期货、掉期、收益率曲线、期权和汇率中的市场隐含预期；
- 权威媒体和机构文本预测；
- 搜索、新闻和社交传播作为低等级注意力代理。

### 6.2 预期质量指标

- 覆盖率；
- 来源独立性；
- 预测分歧；
- 历史偏差；
- 校准；
- 发布时间；
- 事后修订风险；
- 市场隐含与调查预期差异。

没有可靠预期时必须输出`EXPECTATION_UNKNOWN`，不能用事件后价格倒推共识。

## 7. 惊喜分解验证

每个事件至少比较以下模型：

- `M0`：只有标题/数值惊喜；
- `M1`：标题 + 文本情绪；
- `M2`：标题 + 立场 + 路径 + 力度 + 时点；
- `M3`：M2 + 增长/通胀/金融稳定信息效应；
- `M4`：M3 + 文本新颖度和潜在细节因子；
- `M5`：M4 + 跨资产联合反应。

通过消融检验每个维度是否提供稳定增量。复杂模型若不能稳定优于简单模型，应降级。

## 8. 抢跑、泄漏和公开推理

### 8.1 抢跑检测

检测：

- 异常收益和成交；
- 收益率曲线形变；
- 期权隐含波动和偏度；
- ETF、期货、现货和行业同步性；
- 新闻/搜索/传闻传播加速；
- W13参与者活动后验；
- 相对历史政策窗口的异常程度。

### 8.2 竞争性解释

至少同时估计：

- `INFORMATION_LEAKAGE_HYPOTHESIS`；
- `PUBLIC_INFERENCE_AND_POSITIONING`；
- `RISK_HEDGING`；
- `PASSIVE_OR_REBALANCE_FLOW`；
- `LIQUIDITY_AND_SUPPLY`；
- `OTHER_CONCURRENT_EVENT`；
- `RANDOM_MARKET_MOVE`。

价格先动本身不足以认定泄漏。只有在来源时间链、跨资产一致性、事件特异性、安慰剂和后续确认共同支持时，泄漏后验才可上升。

## 9. 兑现、延续和反转

### 9.1 定义

- `SELL_THE_NEWS`：事前高度计价，事件不弱但公告后风险收益比恶化并出现反转；
- `UNDERREACTION_DRIFT`：事件惊喜未被即时吸收，后续同向漂移；
- `OVERREACTION_REVERSAL`：初始反应超过后续基本面或跨资产确认；
- `POLICY_INFORMATION_REVERSAL`：政策工具利好被经济弱势信息抵消；
- `IMPLEMENTATION_DOUBT`：政策方向积极但执行可信度不足；
- `SECOND_ORDER_REPRICING`：直接受益先动，供应链和二阶影响后定价。

### 9.2 验证

比较事前计价程度、事件惊喜、初始反应、后续漂移和真实执行结果。不得仅因“利好后跌”就标记兑现。

## 10. 跨资产验证

至少构建：

- 国债曲线水平、斜率和曲率；
- 股票指数、行业和风格；
- CNY/CNH和美元；
- 股指、国债和商品期货；
- 信用利差、资金利率和流动性；
- 黄金、原油、铜、铁矿、煤炭和航运；
- 波动率、偏度和相关性；
- W13参与者资金证据。

验证对象包括：

- 单资产异常；
- 股票与债券共同方向；
- 股债跷跷板失效；
- 曲线不同期限反应；
- 现货与期货背离；
- 中国资产与海外映射；
- 商品价格与相关A股行业反应不一致。

每次解释必须给出支持和反对资产。

## 11. A股传导和公司映射验证

### 11.1 基准组

- B0：市场和行业平均；
- B1：市场、行业、市值、流动性、波动、估值、质量和动量；
- B2：公司公告、注意力和传统事件因子；
- B3：完整母系统，包括W13资金与W6博弈；
- B4：`B3 + PMN`。

只有B4在样本外稳定优于B3，或显著改善尾部风险、弃权和解释校准，才算有增量。

### 11.2 匹配和中性化

控制：

- 行业、规模、流动性、beta和风格；
- 事件前收益和拥挤；
- 公司政策暴露；
- 国企/央企属性；
- 海外收入和商品敏感度；
- 同期公司事件；
- 指数调整和被动流。

### 11.3 传导时滞

分别测试分钟、当日、1/3/5/10/20/60日。短期题材反应和长期基本面效果不得混为一个标签。

## 12. 统计和因果框架

按数据能力选择：

- 高频事件研究；
- 市场模型和因子调整事件研究；
- local projections；
- 异方差识别；
- 状态空间/潜在因子；
- 符号限制的跨资产冲击分解；
- difference-in-differences；
- synthetic control；
- matching和doubly robust估计；
- placebo dates/assets/events；
- negative controls；
- time-varying parameter和regime switching。

不得以复杂方法名称替代识别条件。

## 13. 时间切分和反过拟合

必须使用：

- expanding walk-forward；
- rolling walk-forward；
- purged cross-validation；
- embargo；
- nested model/parameter selection；
- final lockbox；
- 完全未使用的影子运行期。

所有事件、关键词、窗口、行业映射和模型属于同一`ExperimentFamily`，记录搜索次数。

多重检验至少报告：

- White Reality Check；
- Hansen SPA；
- PBO；
- Deflated Sharpe Ratio；
- Romano-Wolf stepdown。

## 14. 指标

### 14.1 事件与来源

- calendar precision/recall；
- confirmed-window coverage；
- rumor precision、recall和Brier；
- source calibration和更正率；
- duplicate/contradiction rate；
- time-to-detection和time-to-confirmation。

### 14.2 预期与惊喜

- expectation MAE/RMSE；
- interval coverage；
- disagreement calibration；
- surprise reproducibility；
- latent-factor incremental explanatory power。

### 14.3 定价状态

- pre-runup classification F1；
- sell-the-news/reversal/drift confusion matrix；
- priced-in ratio calibration；
- high-confidence error rate；
- abstention coverage和selective risk。

### 14.4 经济增量

- IC/rank IC；
- abnormal return和分位数组合；
- hit rate、odds和conditional distribution；
- volatility、max drawdown和Expected Shortfall；
- liquidity、impact、turnover和capacity；
- T+1、涨跌停、停牌和公告延迟后的可执行性；
- B3 versus B4增量。

## 15. 失败和晋级规则

候选不得晋级，如果：

- 需要事后数据才能重建预期；
- 历史日程无法点时还原；
- 复杂惊喜模型不能优于简单基准；
- 抢跑模型大量误报泄漏；
- 跨资产解释只挑支持资产；
- A股增量只存在于单一时期、事件或窗口；
- 成本后和样本外失效；
- 多重检验后消失；
- 影子日报出现严重漏报、时点错误或来源越级。

晋级顺序：

```text
EVENT_AND_SOURCE_VALIDATED
→ EXPECTATION_AND_SURPRISE_VALIDATED
→ PRICING_STATE_VALIDATED
→ CROSS_ASSET_VALIDATED
→ A_SHARE_INCREMENT_VALIDATED
→ SHADOW_BULLETIN_VALIDATED
```

当前协议状态：`NOT_RUN`。
