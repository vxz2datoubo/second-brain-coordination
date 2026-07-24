# A股市场主体圈内认知证据接入与可信度治理补充蓝图 v1.0

> `agent_id: GPT`
>
> 状态：`research_only / NO_TRADE`
>
> 关联模块：
> - `A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-0001`
> - `A-SHARE-MULTI-AGENT-STRATEGIC-GAME-ENGINE-BLUEPRINT-v1.0.md`
> - `A-SHARE-MULTI-AGENT-FAMILY-ADVANTAGE-WEAKNESS-MATRIX-v1.0.md`
> - `PROJECT-BLUEPRINT-INTEGRATION-INDEX-v1.0.md`
>
> 本文件是公开安全的专项补充蓝图，不替代本地受保护的交易系统、第二大脑与协作机制三份权威总蓝图。

## 一、目的

把长期活跃于A股市场、具有较大资金规模、真实交易经历或圈内接触面的参与者公开表达，作为“专家经验假设源”接入系统，同时防止以下错误：

1. 因为说话者有钱、知名或长期交易，就把其观点当成事实；
2. 因为说话者出现巨额亏损，就把其所有认知全部作废；
3. 把自我解释、市场结构观察、对其他主体的描述和行情预测混成同一可信度；
4. 把流畅叙事直接转成交易信号；
5. 把圈内术语、身份标签或个人印象误写成可证实的真实主体身份。

系统应吸收“观察优势”，而不是继承“立场偏差”。

## 二、本次来源样本

### 2.1 来源记录

- 公开身份：刘鑫，网络称呼“鑫多多”，公众号“亿万鑫”；
- 样本事件：2026年7月公开披露当月大额亏损后发布长文；
- 样本主题：个人亏损复盘、投资目的、A股九类市场主体、当前市场判断、投资经验；
- 九类主体：散户、公募、私募、量化、政策稳定资金、产业资本、外资、游资与牛散、其他核心股相关群体；
- 来源性质：公开个人陈述、媒体转述与圈内经验总结，不是审计报告、监管数据、学术研究或可直接复现的数据集。

### 2.2 系统定位

该样本只能进入：

- `ExpertElicitationCandidate`；
- `ParticipantArchetypeHypothesis`；
- `BehavioralMechanismHypothesis`；
- `ValidationTaskGenerator`；
- `NarrativeAndPositioningRisk`。

不得直接进入：

- 确定性身份识别；
- 无验证的参数常数；
- 自动买卖信号；
- 仓位调整指令；
- “圈内人说了所以成立”的权威覆盖。

## 三、核心可信度原则：分对象、分利益、分可验证性

### 3.1 非对称可信度假设

用户提出的重要观察是：

> 一个人谈自己时，可能受声誉、仓位、责任和自我辩护影响；谈其他市场群体时，若不存在直接利益冲突，可能更愿意陈述真实经验。

系统接受这一点作为“待检验的非对称可信度先验”，但不得把它写成普遍真理。

统一表示：

```text
CredibilityPrior(claim)
= BaseSourcePrior
× PerspectiveAdjustment
× ConflictOfInterestAdjustment
× AccessAdvantageAdjustment
× VerifiabilityAdjustment
× TrackRecordAdjustment
× CorroborationAdjustment
```

其中：

- `PerspectiveAdjustment`：区分谈自己、谈他人、谈制度、谈行情；
- `ConflictOfInterestAdjustment`：评估仓位、融资、减持、募集、声誉、粉丝维护和诉讼责任；
- `AccessAdvantageAdjustment`：评估是否确有资金规模、交易经验、调研和圈内接触优势；
- `VerifiabilityAdjustment`：是否可被公开数据、回放或官方资料验证；
- `TrackRecordAdjustment`：历史同类判断的校准记录，不使用单次盈亏替代；
- `CorroborationAdjustment`：是否得到独立来源和数据支持。

### 3.2 五类声明必须拆开

#### A. 自我行为与自我归因 `SELF_ATTRIBUTION`

例：亏损原因、仓位动机、是否追高、是否长期主义、是否被迫交易。

处理：

- 默认存在自利性归因、事后合理化、选择性披露和声誉管理风险；
- 初始可信度低至中；
- 必须用持仓变化、融资数据、公告、成交轨迹和前期公开言论交叉验证；
- 不因“主动认错”自动提高为高可信。

#### B. 对其他主体的行为观察 `OTHER_ACTOR_OBSERVATION`

例：公募受排名和赎回约束、私募资金期限不同、量化偏好高交易活跃区域、游资具有注意力和退出需求。

处理：

- 若说话者确有长期市场接触，可给予“访问优势加分”；
- 若描述会服务于其当前仓位或舆论目标，仍需利益冲突折扣；
- 初始可信度中等，只能进入行为假设库；
- 通过基金持仓、赎回、成交、龙虎榜、ETF、融资融券和回放验证。

#### C. 市场结构与制度陈述 `MARKET_STRUCTURE`

例：公募机制、T+1约束、产业资本减持供给、政策稳定资金的市场功能。

处理：

- 优先使用法规、交易所、基金合同、定期报告和官方数据；
- 圈内陈述只负责发现问题和生成检索方向；
- 可验证事实不得由个人声望决定。

#### D. 行情方向与估值判断 `MARKET_OUTLOOK`

例：阶段性底部、某方向遍地黄金、未来一定重估。

处理：

- 与当前仓位和公开影响力高度相关；
- 默认低权重、高漂移、高反身性；
- 单独进入 `NarrativeForecastLedger`；
- 只能用于事后校准和舆情研究，不得直接进入中期爆发评分。

#### E. 规范性建议与人生经验 `NORMATIVE_ADVICE`

例：闲钱投资、不盲从、减少盯盘、逆人性。

处理：

- 拆成风险管理、行为金融和时间尺度假设；
- 分别与历史数据、用户约束和组合风险政策核验；
- 不把口号当成策略。

## 四、九类主体如何融入既有四家族模型

本次来源不替换既有四家族，而是提高家族内部粒度。

### 4.1 散户

映射到：`Retail Population Family`

新增候选子类型：

- 情绪摆动型；
- 热点一致性追逐型；
- 群聊与大V驱动型；
- 被套等待型；
- 低频长期型；
- 高认知独立决策型。

可验证指标：

- 小单占比及其方向变化；
- 新增开户和融资活跃度代理；
- 社媒注意力、搜索、评论情绪；
- 高换手、高波动和涨跌停追逐；
- 散户情绪极端与价格反转/延续概率。

### 4.2 公募

映射到：`Large Capital and Inventory Family / PublicFundSubtype`

新增约束：

- 相对排名；
- 申购赎回；
- 风格漂移约束；
- 组合集中度；
- 季末、半年末和年末窗口；
- 业绩比较基准和合规限制。

不得直接采用“公募比散户更情绪化”的结论。正确做法是检验：

- 在赎回、排名和拥挤条件下，公募是否表现出更强同向交易；
- 行为是否由主动观点、被动赎回、指数调整或风控触发。

### 4.3 私募

映射到：`Large Capital and Inventory Family / PrivateFundSubtype`

新增维度：

- 锁定期和赎回频率；
- 业绩报酬；
- 策略自由度；
- 净值预警/止损线；
- 客户集中度；
- 容量与流动性错配。

“私募更稳定”只能作为分层假设。不同私募策略、杠杆和止损合同可能产生完全相反行为。

### 4.4 量化

映射到：`Quant Strategy Family`

吸收的候选经验：

- 在交易活跃、风格集中和散户行为更稳定可预测的区域，部分量化策略容量和机会可能增加；
- 策略趋同可能放大同向交易、拥挤和流动性踩踏；
- 量化并非单一主体，不能笼统写成“主导市场”。

验证要求：

- 区分做市、执行、横截面、趋势、事件、ETF、统计套利和高频策略；
- 比较高交易活跃度与量化代理变量的关系；
- 检查是否存在反向因果：并非量化追逐热点，而是热点本身带来更多可交易流动性；
- 检查容量、冲击和拥挤失效。

### 4.5 政策稳定资金

映射到：`Large Capital and Inventory Family / StabilizationCapitalSubtype`

候选假设：

- 大额增持可能与市场压力、估值、流动性和政策目标相关；
- 退出或降低持有可能与市场稳定目标、资产配置和阶段性环境相关。

强制限制：

- 不得把“买入等于底部、卖出等于顶部”写成确定规则；
- 区分公告时间、成交时间、ETF申赎、汇金等公开主体、政策预期和市场自发反弹；
- 做事件研究、基准调整和样本外检验。

### 4.6 产业资本

映射到：`Large Capital and Inventory Family / IndustrialCapitalSubtype`

高价值候选假设：

- 单家公司减持可能是个体原因；
- 同行业、同产业链或同估值区域出现批量增减持，可能反映产业资本对估值、融资、经营和供给的共同约束；
- 产业资本行为对中期供需和信号质量可能比单个大V言论更重要。

新增特征：

- 行业减持广度、金额、频率和占流通市值比例；
- 回购、增持、定增、解禁、股权质押和员工持股；
- 减持公告到实际执行的时间差；
- 产业资本方向与机构持仓、盈利预期、估值的交叉。

### 4.7 外资

映射到：`Large Capital and Inventory Family / ForeignCapitalSubtype`

来源中的情绪化评价不得进入模型。仅保留可检验维度：

- 全球风险预算；
- 汇率与利差；
- 指数纳入和被动配置；
- 地缘、合规和可投资性约束；
- 中国资产估值与全球替代资产比较；
- 不同外资类型的期限和目标差异。

### 4.8 游资与牛散

映射到：`Active Speculative Capital Family`

吸收的候选经验：

- 不神化为统一精英群体；
- 可能具有更高注意力敏感度、更短决策链、更强独立性和局部题材经验；
- 仍可能受到情绪、杠杆、容量、退出通道和路径依赖约束；
- 大资金规模不自动等于高认知，也不自动等于稳定收益。

新增识别风险：

- 牛散持仓披露存在季度时滞；
- 公开言论可能与真实仓位不一致；
- 融资账户和关联账户可能放大或隐藏风险；
- 个人品牌可能制造跟随盘和反身性。

### 4.9 其他核心股相关群体

不得直接创建含糊的“神秘核心群体Agent”。拆成：

- 上市公司与管理层；
- 供应链与产业关联方；
- 员工持股与股权激励；
- ETF、指数与被动资金；
- 做市和流动性提供者；
- 券商两融、衍生品和风险管理；
- 媒体、大V、研究员和注意力中介；
- 监管、交易所与政策事件。

无法归类时进入 `UNKNOWN_ACTOR_CLUSTER`，不得编故事补齐身份。

## 五、新增机器可读对象

### 5.1 `ExpertSourceProfile`

至少包含：

```yaml
source_id:
public_identity:
source_type:
market_experience_proxy:
capital_scale_proxy:
access_advantages: []
known_positions_or_exposures: []
reputational_incentives: []
commercial_incentives: []
legal_or_disclosure_constraints: []
track_record_scope:
source_prior:
source_prior_rationale:
last_reviewed_at:
```

### 5.2 `InsiderClaimRecord`

```yaml
claim_id:
source_id:
claim_time:
claim_text_summary:
claim_perspective: SELF_ATTRIBUTION | OTHER_ACTOR_OBSERVATION | MARKET_STRUCTURE | MARKET_OUTLOOK | NORMATIVE_ADVICE
subject_family:
subject_subtype:
time_horizon:
position_relevance:
conflict_of_interest_score:
access_advantage_score:
verifiability_score:
initial_credibility:
evidence_for: []
evidence_against: []
independent_corroboration: []
invalidation_conditions: []
calibration_status: UNTESTED | PARTIAL | SUPPORTED | WEAKENED | REJECTED | STALE
allowed_uses: []
prohibited_uses: []
```

### 5.3 `ClaimCredibilityVector`

禁止只给一个笼统总分。至少输出：

- `source_access`；
- `self_interest_risk`；
- `public_positioning_risk`；
- `direct_observability`；
- `independent_verifiability`；
- `historical_calibration`；
- `cross_source_agreement`；
- `regime_dependence`；
- `final_research_weight`。

## 六、新增主体共振与错位模型

### 6.1 主体一致性评分 `ParticipantAlignmentScore`

用途：衡量多个可观察主体行为是否在同一方向形成中期共振。

候选维度：

- 产业资本方向；
- 公募/私募/外资持仓与资金流代理；
- 游资与短线活跃资金是否愿意点火和承接；
- 量化流动性与趋势是否支持；
- 散户注意力是否处于可扩散但未极端拥挤状态；
- 公告、基本面和产业事件是否验证；
- 盘口与成交是否出现承接、吸收和有效突破；
- 板块和核心标的是否同步。

输出不是“主体都在买”，而是：

```yaml
alignment_score:
aligned_dimensions: []
conflicting_dimensions: []
unknown_dimensions: []
dominant_hypotheses: []
confidence:
invalidation_conditions: []
```

### 6.2 主体错位风险 `ParticipantMismatchRisk`

重点识别：

- 消息强、舆情热，但大额资金持续流出；
- 大V喊多，但产业资本批量减持；
- 短线资金点火，但中线资金不跟；
- 机构持仓集中，但价格对利好钝化；
- 散户极度拥挤，量化和大资金利用流动性退出；
- ETF或指数被动流被误判为主动建仓；
- 自媒体叙事与真实公告、持仓、融资或减持行为冲突；
- 同一来源“说别人”和“说自己”的可信度显著不对称。

## 七、数据与验证映射

### 7.1 官方与结构数据优先

- 交易所公告、监管规则和上市公司公告；
- 基金定期报告、基金份额和公开持仓；
- ETF申赎、指数调整和成分变化；
- 龙虎榜、大宗交易、融资融券；
- 十大股东、十大流通股东和持仓时滞；
- 增减持、回购、解禁、质押和定增；
- 市场成交、订单流、盘口和历史回放；
- 行业和板块横截面。

### 7.2 舆情与公开表达只作辅助

- 公众号、社交媒体、访谈、论坛和直播；
- 媒体转述必须保留原始来源和转述层级；
- 同一内容被大量转载不得视为多个独立证据；
- 文章发布后价格变化不得自动证明文章正确；
- 公开表达可能改变市场本身，需标记反身性。

### 7.3 最低验证方法

- 事件研究；
- 横截面比较；
- 时间序列与市场状态分层；
- 样本外与walk-forward；
- 消融与反事实；
- 基准率比较；
- Brier Score、log loss和coverage；
- 预测方向、时间窗、幅度与失效条件分别计分；
- 对自我陈述与他人观察分别校准。

## 八、第二大脑接入规则

第二大脑保存时必须分开：

1. 原始来源与发布时间；
2. 媒体转述层；
3. 事实陈述；
4. 个人解释；
5. 对其他主体的经验判断；
6. 行情预测；
7. 规范性建议；
8. 支持证据与反证；
9. 当前可信度与变化历史；
10. 是否已进入正式Agent本体。

禁止将“圈内人说法”压缩成无来源的永久知识。任何升级都要保留来源、时间、利益冲突和验证记录。

## 九、对本地权威总蓝图的回写建议

### 9.1 交易系统总蓝图

建议新增：

- `Expert Elicitation Ingestion`；
- `Source Conflict-of-Interest Model`；
- `Participant Alignment Score`；
- `Participant Mismatch Risk`；
- `Narrative Forecast Ledger`；
- 圈内经验到可验证特征的转换门禁。

### 9.2 第二大脑总蓝图

建议新增：

- 声明视角分类；
- 自我陈述与他人观察的非对称可信度；
- 立场、仓位、融资、声誉和商业利益字段；
- 来源历史校准和版本演化；
- 公开言论与后续真实行为冲突检测。

### 9.3 协作机制总蓝图

建议新增：

- GPT负责来源拆解、理论映射和验收；
- Codex负责Schema、评分、验证计划和回测实现；
- WorkBuddy负责本地公开数据接线、事件回放和运行态证据；
- QCLAW负责同类圈内访谈、学术和机构材料的离线知识包；
- 未通过验证不得提升为生产规则。

## 十、Issue #23新增强制交付

Codex项目计划阶段新增：

- `EXPERT-SOURCE-PROFILE-SCHEMA.yaml`；
- `INSIDER-CLAIM-RECORD-SCHEMA.yaml`；
- `CLAIM-CREDIBILITY-MODEL.md`；
- `PERSPECTIVE-ASYMMETRY-CALIBRATION-PLAN.md`；
- `NINE-GROUP-TO-FOUR-FAMILY-MAPPING.yaml`；
- `PARTICIPANT-ALIGNMENT-SCORE-SPEC.md`；
- `PARTICIPANT-MISMATCH-RISK-SPEC.md`；
- `NARRATIVE-FORECAST-LEDGER-SCHEMA.yaml`；
- `EXPERT-ELICITATION-VALIDATION-BACKLOG.md`；
- `PROTECTED-BLUEPRINT-BACKWRITE-PACKAGE.md`对应增量。

## 十一、验收门禁

只有同时满足以下条件，圈内认知才可升级：

1. 来源身份和原始发布时间可追踪；
2. 声明已按五类视角拆分；
3. 利益冲突和仓位相关性已评估；
4. 至少一个独立数据源或独立来源支持；
5. 存在明确反证和失效条件；
6. 完成样本外或跨事件验证；
7. 结果按市场状态分层；
8. 未把主体行为当身份铁证；
9. 未直接接入真实交易；
10. GPT验收并记录升级理由。

状态机：

```text
RAW_PUBLIC_STATEMENT
→ PARSED_CLAIMS
→ EXPERT_HYPOTHESIS
→ VALIDATION_QUEUED
→ PARTIALLY_VALIDATED
→ RESEARCH_FEATURE_CANDIDATE
→ SHADOW_MODE
→ CALIBRATED_RESEARCH_SIGNAL
```

任何阶段均可进入：

```text
WEAKENED / REJECTED / STALE / CONFLICTED / UNKNOWN
```

## 十二、本次样本的初始结论

### 可直接吸收为结构目录

- 九类主体清单可用于扩展既有四家族内部子类型；
- 公募、私募、政策稳定资金、产业资本、外资必须从“大资金”中进一步拆开；
- 游资与牛散不应被神化，应保留散户式情绪、容量和退出约束；
- 产业资本批量行为值得建立行业级供给与信号模块；
- 大V和圈内公开表达本身应建成立场与反身性风险模块。

### 只能作为待验证经验

- 散户是A股风格的核心驱动力；
- 公募在特定机制下可能比想象中更趋同和被动；
- 私募在某些资金合同下可能更稳定；
- 量化更集中于散户活跃和赚钱效应高的区域；
- 政策稳定资金的大额行为与阶段极值相关；
- 独立、理性和专注是游资牛散长期存活的重要特征。

### 不得直接吸收

- 任何“现在就是底部”或“未来一定上涨”的判断；
- 对外资、散户、公募等群体的情绪化贬义评价；
- 将个人巨亏后的自我解释视为完整因果；
- 将大额资金规模视为高可信度证明；
- 将公开文章视为买卖依据。

## 十三、最终定位

这类来源的最佳用途不是“听他买什么”，而是：

- 发现市场主体分类是否缺项；
- 发现不同资金的真实约束候选；
- 生成可被盘口、公告、持仓和回放验证的行为假设；
- 识别说话者对自己与对他人的可信度差异；
- 把公开叙事、真实行为和市场结果放在同一证据账本中长期校准。

系统既不迷信圈内人，也不浪费圈内人的现场经验。