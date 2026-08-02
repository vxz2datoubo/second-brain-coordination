# 时序证据智能基础层蓝图

> 文档状态：Proposed v0.1  
> 英文名称：Temporal Evidence Intelligence Foundation（TEIF）  
> 架构层级：项目集基础能力层（Foundation Layer）  
> 服务对象：A 股 AI 量化交易研究系统、超级第二大脑、注意力信号引擎、异常归因模块及未来业务系统  
> 默认交易状态：`NO_TRADE`  
> 单一真相源：本 GitHub 仓库中的受控版本  
> 最后更新：2026-07-18

---

## 1. 执行摘要

现有注意力信号引擎已经提出了主动搜索、内容供给、传播消费、专业确认、机构确认和资本市场同步的分层方法，并要求原始事实可追溯、词包可版本化和研究输出默认 `NO_TRADE`。下一步不能只为注意力模块继续增加局部字段，而应建立一套被所有业务模块共同复用的基础方法论：

> **任何事实、信号、判断、模型输出和决策，都必须回答：什么时候发生、什么时候被系统知道、证据来自哪里、证据质量如何、结论有多大把握、有哪些替代解释、什么新证据会改变判断。**

TEIF 将以下能力建设为项目集级基础服务：

1. **全局时间轴**：统一新闻、论文、模型、公告、搜索指数、内容传播、研报、招聘、资金、价格、任务运行和人工决策的时间语义。
2. **证据与来源追溯**：每个判断可以回到原始来源、采集活动、处理作业、模型版本和人工审核记录。
3. **可信度与不确定性**：区分事件发生概率、分析置信度、数据质量、来源可靠性和模型校准状态。
4. **主题演化与时序知识图谱**：记录实体、事件、主题和关系随时间的出现、变化、失效与修订。
5. **归因与因果假设**：严格区分时间先后、相关、预测领先、机制支持和因果识别。
6. **知识与决策版本**：支持任意历史时点的“当时已知信息”重放，防止未来信息污染回测。
7. **统一输出契约**：交易研究、第二大脑、Codex、WorkBuddy 和 ChatGPT 使用同一套时间、证据和概率语言。

TEIF 不直接替代交易策略、风控、知识图谱或注意力信号模块。它是这些系统下方的公共地基。

---

## 2. 研究依据与企业级参考

本设计吸收以下公开标准、学术研究和企业实践，但不复制任何单一产品：

### 2.1 数据来源与证据追溯

- **W3C PROV-O** 用 `Entity`、`Activity`、`Agent` 及生成、使用、派生、归属关系描述跨系统来源追溯，适合作为 TEIF 证据图的概念映射基准。
- **OpenLineage** 使用事件化的 Job、Run、Dataset 模型记录数据作业状态、输入和输出，并允许通过 facets 扩展元数据。
- **Databricks Unity Catalog** 的企业实践表明，访问控制、审计、质量、数据发现和端到端 lineage 应位于统一治理层，而不是散落在各业务脚本里。

### 2.2 时间与事件建模

- **CloudEvents** 证明跨服务事件需要统一 envelope，至少表达事件类型、来源、标识、时间和数据内容。
- **Event Sourcing** 强调以不可变、只追加事件作为系统记录，并从事件物化当前视图；它适合需要历史重建和审计的部分，但不应无差别用于全部 CRUD 数据。
- 时序知识图谱研究指出，很多事实只在特定时间区间成立，静态知识图谱无法表达实体与关系的动态演化。
- 事件知识图谱研究强调事件中心表示在搜索、问答、推荐、金融量化等下游任务中的价值。

### 2.3 分析可信度和不确定性

- **ODNI ICD 203 Analytic Standards** 要求描述来源质量与可信度、解释重大判断中的不确定性、区分底层信息与分析假设，并考虑替代观点和反证。
- **NIST AI RMF 1.0** 提出 Govern、Map、Measure、Manage 的持续治理循环，要求有效性、可靠性、透明性、可解释性以及独立验证和持续监控。
- 机器学习校准研究表明，模型输出的概率不天然等于真实正确率；置信度必须通过历史结果校准，而不能直接使用模型自报分数。

### 2.4 关联、领先与因果

- PCMCI+ 等时序因果发现方法提醒我们：自相关、多变量混杂和同期关系会造成虚假的领先或因果判断。
- TEIF 因此把“时间先后”“统计关联”“预测领先”“机制证据”“准实验支持”和“因果结论”分为不同等级。

### 2.5 企业语义层

- 企业 Ontology 实践通常将对象、属性、关系和动作放在共享语义层，使数据、逻辑、行动和权限能够围绕真实业务对象协同。
- TEIF 借鉴这种对象化思想，但在本项目中坚持开源标准优先、存储中立和渐进建设，避免一开始引入昂贵、封闭或超出当前规模的基础设施。

---

## 3. 设计目标

### 3.1 必须实现

1. 所有重要对象均具有稳定 ID 和版本。
2. 所有重要事实至少具有“事件发生时间”和“系统可用时间”。
3. 所有分析结论可追溯到来源、采集、转换、特征和模型版本。
4. 来源质量、数据质量、分析置信度和事件概率彼此分离。
5. 系统可以在任意历史时点重建当时可知的世界状态。
6. 支持证据、反证、替代解释、假设和知识缺口并存。
7. 所有跨模块输出使用统一 envelope。
8. 研究与真实交易执行保持物理和权限隔离。
9. 支持人工审核、撤回、修订和失效，不删除历史。
10. 允许输出“不知道”“证据不足”“多个解释并存”。

### 3.2 暂不追求

- 不在第一阶段建设大规模通用知识图谱平台。
- 不在第一阶段采用全量流式基础设施。
- 不把所有内容都存成 RDF 或全部放入图数据库。
- 不让大语言模型直接修改事实层或真实交易状态。
- 不把一个综合可信度分数当作全部真相。
- 不承诺仅凭观察性数据自动识别真实因果。

---

## 4. 总体架构

```text
外部平台 / 官方来源 / 市场数据 / 论文 / GitHub / 人工输入
                         │
                         ▼
                采集适配与来源登记层
                         │
                         ▼
            统一事件信封 + 幂等去重 + 原始工件
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  不可变事件账本    证据与工件库      数据运行谱系
        │                │                │
        └────────────────┼────────────────┘
                         ▼
              时间语义与质量门禁层
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
  全局时间轴服务   时序知识图谱     特征与数据产品层
        │                │                │
        └────────────────┼────────────────┘
                         ▼
        可信度 / 校准 / 归因 / 因果研究服务
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 注意力信号与归因    交易研究系统      第二大脑只读视图
                         │
                         ▼
             独立策略、风控与人工授权
                         │
                         ▼
                    真实交易系统
```

### 4.1 分层说明

| 层 | 责任 | 禁止事项 |
|---|---|---|
| 采集层 | 获取原始事实和工件，登记来源与权限 | 在采集时偷偷改写事实 |
| 事件与证据层 | 只追加保存事件、工件、来源和谱系 | 覆盖历史、删除不利证据 |
| 时间与质量层 | 统一时间语义、去重、校验、质量门禁 | 将缺失当零、将发布时间当发生时间 |
| 语义与特征层 | 生成实体、主题、关系、特征和物化视图 | 把推断写回原始事实 |
| 分析层 | 生成判断、归因、概率、反证和因果假设 | 强行给出唯一结论 |
| 业务层 | 交易研究、第二大脑和专题系统 | 绕过基础层自建不可审计口径 |
| 执行层 | 策略、组合、风控、订单和人工批准 | 直接消费未经验证的 LLM 文本 |

---

## 5. 核心时间模型

### 5.1 为什么不能只有一个时间字段

同一条消息可能在 10:00 发生、10:08 发布、10:12 被采集、10:15 被解析、10:30 才进入特征，第二天又被官方修订。交易回测若只使用 `date` 字段，就会产生严重未来函数。

### 5.2 标准时间字段

| 字段 | 含义 | 必需性 |
|---|---|---|
| `event_time` | 事件在现实世界中发生的时间 | 尽可能必需 |
| `published_at` | 来源首次公开发布时间 | 有公开内容时必需 |
| `observed_at` | 采集主体实际观察到内容的时间 | 必需 |
| `ingested_at` | 数据进入 TEIF 的时间 | 必需 |
| `available_at` | 数据完成必要处理、可被下游合法使用的时间 | 回测必需 |
| `valid_from` | 事实开始成立的时间 | 区间事实必需 |
| `valid_to` | 事实不再成立的时间 | 可选，未知时为空 |
| `corrected_at` | 来源或系统确认修订的时间 | 修订时必需 |
| `superseded_at` | 该版本被新版本取代的时间 | 版本替换时必需 |
| `market_effective_at` | 对特定交易市场可交易地生效的时间 | 交易研究必需 |

### 5.3 双时间与多时间语义

TEIF 至少实现两个核心维度：

- **有效时间 Valid Time**：事实在现实世界何时成立。
- **系统时间 System/Transaction Time**：系统何时知道并保存该事实。

为交易研究增加第三个关键维度：

- **可用时间 Available Time**：信息何时通过质量门禁，允许进入当时的研究或策略特征。

### 5.4 时间统一规则

- 内部存储统一使用 UTC，展示时保留原始时区和 `Asia/Shanghai` 视图。
- 保存原始时间字符串、解析结果和解析置信度。
- 仅有日期时不得伪造具体时分秒，使用时间精度字段。
- 区分“首发”“转载”“编辑”“采集”和“首次被本系统知道”。
- 交易相关事件必须映射交易所日历、盘前、盘中、盘后、休市和下一可交易时点。
- 每次回测必须指定 `as_of` 和 `knowledge_cutoff`。

### 5.5 全局时间轴视图

系统支持至少五种视图：

1. **现实发生轴**：按 `event_time`。
2. **公开传播轴**：按 `published_at`。
3. **系统认知轴**：按 `observed_at` / `available_at`。
4. **知识有效轴**：按 `valid_from` / `valid_to`。
5. **市场作用轴**：按 `market_effective_at`。

---

## 6. 不可变事件账本

### 6.1 原则

- 原始事件只追加，不原地更新。
- 修订通过新事件表达，并链接 `revises_event_id`。
- 删除通过失效或撤回事件表达。
- 当前状态由事件物化，不是唯一真相。
- 事件 envelope 兼容 CloudEvents 的核心思想，但增加交易研究所需时间和证据字段。

### 6.2 事件分类

| 类别 | 示例 |
|---|---|
| `SOURCE_PUBLICATION` | 新闻、公告、论文、研报、视频首次发布 |
| `PLATFORM_METRIC` | 百度指数、微信指数、内容播放量观察值 |
| `PRODUCT_RELEASE` | 模型、API、软件版本发布 |
| `CORPORATE_ACTION` | 公司公告、合作、订单、招聘、调研 |
| `MARKET_OBSERVATION` | 价格、成交、资金、波动、板块联动 |
| `DATA_PIPELINE` | 采集、解析、特征和模型作业运行 |
| `ANALYTIC_ASSESSMENT` | 人工或模型分析判断 |
| `KNOWLEDGE_REVISION` | 实体、主题、关系或词包修订 |
| `DECISION` | 研究批准、拒绝、冻结、策略候选 |
| `CONTROL_EVENT` | 权限变化、质量门禁失败、数据源停用 |

### 6.3 幂等与去重

每条事件包含：

- `event_id`
- `source_native_id`
- `source_uri`
- `content_hash`
- `dedup_fingerprint`
- `schema_version`
- `producer`
- `collection_run_id`

去重不能只看标题。转载、翻译、摘要和内容更新需要分别保存，并通过关系表达。

---

## 7. 证据与来源追溯体系

### 7.1 核心对象

- **EvidenceItem**：一条原始或加工证据。
- **Source**：发布者、平台、数据产品或文件。
- **Agent**：采集人、分析人、组织、脚本或模型。
- **Activity**：采集、解析、转换、聚类、计算、审核等过程。
- **Claim**：可被支持或反驳的陈述。
- **Artifact**：截图、PDF、网页快照、导出表、代码、日志或模型工件。

这些对象可映射到 W3C PROV 的 Entity、Agent、Activity，但工程存储不强制采用 RDF。

### 7.2 来源可靠性维度

来源可靠性不只看“官方或非官方”，至少分解为：

- 身份真实性
- 是否为一手来源
- 对事件的直接接触程度
- 历史准确率
- 专业能力
- 利益冲突与动机
- 可被操纵或欺骗风险
- 可获得性和持续性
- 发布与修订机制
- 法律、版权与使用权限

### 7.3 证据质量维度

- 与目标 claim 的相关性
- 完整性
- 时间接近性与新鲜度
- 内容真实性与完整性验证
- 方法透明度
- 样本代表性
- 独立性
- 可重复性
- 与其他来源的一致或冲突
- 数据质量状态

### 7.4 来源与证据必须分离

一个长期可靠的媒体也可能发布一条低质量转述；一个普通用户也可能提供关键的一手截图。因此：

```text
Source Reliability ≠ Evidence Quality ≠ Claim Confidence
```

### 7.5 独立性与重复传播

一百篇转载同一篇稿件不是一百个独立证据。系统必须建立 `origin_cluster_id` 和 `independence_group_id`，识别：

- 同源转载
- 同一公关稿
- 交叉引用
- 同一数据集衍生
- 账号矩阵协同发布
- 真正独立的一手观察

### 7.6 证据状态

| 状态 | 含义 |
|---|---|
| `UNVERIFIED` | 尚未核验 |
| `VERIFIED_SOURCE` | 来源身份和原始工件已核验 |
| `VERIFIED_CONTENT` | 内容完整性或哈希已核验 |
| `CORROBORATED` | 被独立来源支持 |
| `CONTRADICTED` | 存在强反证 |
| `RETRACTED` | 来源撤回 |
| `SUPERSEDED` | 被新版本取代 |
| `UNAVAILABLE` | 来源暂不可访问但历史工件保留 |

---

## 8. Claim、判断与反证模型

### 8.1 不把事实、推断和假设混在一起

| Claim 类型 | 示例 |
|---|---|
| `OBSERVED_FACT` | 某官方页面在某时刻显示某指数 |
| `REPORTED_FACT` | 某媒体报道称公司发布产品 |
| `DERIVED_METRIC` | 7 日搜索加速度为正 |
| `INTERPRETATION` | 搜索增长可能代表主动兴趣扩大 |
| `FORECAST` | 未来一周内容供给可能增加 |
| `CAUSAL_HYPOTHESIS` | 发布会推动了搜索峰值 |
| `DECISION_RECOMMENDATION` | 建议进入研究候选池 |

### 8.2 每个重大判断必须包含

- 判断正文
- 作用范围与时间范围
- 支持证据
- 反证
- 替代解释
- 关键假设
- 知识缺口
- 事件概率或方向概率
- 分析置信度
- 什么新信息会改变判断
- 负责人和审核状态
- 数据、代码、模型和词包版本

### 8.3 假设登记

关键假设不能藏在自然语言里。必须登记：

- `assumption_id`
- 假设内容
- 必要性
- 可检验性
- 当前证据
- 失效条件
- 影响的判断和模型

---

## 9. 可信度与不确定性框架

### 9.1 四类不同概念

1. **Likelihood**：事件或判断成立的概率。
2. **Analytic Confidence**：分析者对判断依据是否充分稳健的信心。
3. **Data Quality**：数据完整性、准确性、及时性、一致性和可用性。
4. **Model Calibration**：模型声称的概率与历史真实正确率是否一致。

这些值不得用一个字段代替。

### 9.2 概率语言

建议采用七段概率区间，并在界面中同时显示数字范围和自然语言：

| 概率区间 | 建议语言 |
|---|---|
| 1%-5% | 极少可能 |
| 5%-20% | 很不可能 |
| 20%-45% | 不太可能 |
| 45%-55% | 大致均等 |
| 55%-80% | 可能 |
| 80%-95% | 很可能 |
| 95%-99% | 几乎确定 |

不得把“高置信度”和“很可能”混成同一句话。前者描述依据质量，后者描述事件概率。

### 9.3 分析置信度

分析置信度由以下向量共同决定，不应只保留总分：

```yaml
confidence_vector:
  source_quality: 0.0-1.0
  evidence_directness: 0.0-1.0
  evidence_independence: 0.0-1.0
  evidence_completeness: 0.0-1.0
  temporal_alignment: 0.0-1.0
  method_validity: 0.0-1.0
  alternative_explanation_risk: 0.0-1.0
  data_quality: 0.0-1.0
  model_calibration: 0.0-1.0
```

系统可以提供可解释的综合等级 `LOW / MEDIUM / HIGH`，但必须保留分项和计算版本。

### 9.4 模型概率校准

对于可历史验证的分类或预测任务，至少使用：

- Brier Score
- Log Loss
- Expected Calibration Error
- Reliability Diagram
- 分箱命中率
- 区间覆盖率与区间宽度
- 不同主题、平台和市场状态的分组校准

模型未通过校准时，输出只能标记为实验性；大语言模型的自然语言自信程度不作为概率。

### 9.5 Abstention

分析系统必须具有拒答或保留判断能力：

- `INSUFFICIENT_EVIDENCE`
- `AMBIGUOUS`
- `CONFLICTING_EVIDENCE`
- `OUT_OF_DISTRIBUTION`
- `DATA_QUALITY_BLOCKED`
- `METHOD_NOT_VALIDATED`

---

## 10. 时序知识图谱与主题演化

### 10.1 图谱对象

- Entity：公司、产品、模型、论文、人物、机构、证券、平台、政策。
- Event：发布、融资、合作、公告、搜索峰值、研报、价格异动。
- Topic：世界模型、具身智能、AI Agent 等研究主题。
- Claim：事实或分析陈述。
- Evidence：支持或反驳 claim 的证据。
- Dataset / Feature / Model：数据与计算工件。
- Decision：人工和系统决策。

### 10.2 关系必须带时间和来源

```text
Company --released--> Product
Product --belongs_to--> Topic
Event --increased_attention_of--> Topic
Claim --supported_by--> Evidence
Assessment --used_dataset--> DatasetVersion
Feature --derived_from--> Observation
Decision --based_on--> Assessment
```

每条关系至少包含：

- `valid_from / valid_to`
- `observed_at / available_at`
- `evidence_ids`
- `confidence`
- `status`
- `version`

### 10.3 主题演化

主题不是静态词包。系统记录：

- 首次出现
- 概念定义变化
- 关联实体增加或移除
- 子主题分裂与合并
- 专业圈与大众语义差异
- 产业链映射变化
- 市场叙事与实际收入相关性的变化
- 主题失效或过期

### 10.4 历史查询

支持以下查询：

- 2026-06-24 当天系统知道哪些关于 Matrix 的信息？
- 当时哪些公司被映射到世界模型，映射依据是什么？
- 当前结论相较当时修改了什么，为什么？
- 某次回测实际使用了哪个词包和图谱版本？

---

## 11. 归因与因果框架

### 11.1 因果证据梯度

| 等级 | 状态 | 含义 |
|---|---|---|
| C0 | `TEMPORAL_ORDER_ONLY` | 只有先后关系 |
| C1 | `ASSOCIATED` | 存在统计相关 |
| C2 | `PREDICTIVE_LEAD` | 对未来变化有稳定预测领先 |
| C3 | `MECHANISM_SUPPORTED` | 有可信机制与传播路径证据 |
| C4 | `QUASI_EXPERIMENTAL` | 通过事件研究、对照、自然实验等支持 |
| C5 | `CAUSAL_SUPPORTED` | 多方法、多证据和稳健性检验支持 |

在观察性市场研究中，大多数结论应停留在 C1-C4。C5 必须非常克制。

### 11.2 统一因果假设对象

```yaml
causal_hypothesis:
  cause_event_id: ...
  effect_event_or_metric_id: ...
  expected_lag: ...
  mechanism: ...
  confounders: []
  alternative_causes: []
  falsifiers: []
  method: ...
  evidence_ids: []
  counter_evidence_ids: []
  causal_level: C0-C5
  confidence: LOW|MEDIUM|HIGH
```

### 11.3 研究方法

- 时间顺序与传播路径检查
- 交叉相关和滚动领先
- Granger 预测检验，仅称预测领先，不直接称真实因果
- PCMCI+ 等多变量时序因果候选发现
- 事件研究
- 差分中的差分
- 合成控制
- 安慰剂与负对照
- 机制证据核验
- 跨平台重复验证

### 11.4 强制反证

每个高影响归因至少回答：

1. 是否存在共同原因同时推动两者？
2. 是否是平台算法或口径变化？
3. 是否由营销投放、刷量或同名词污染造成？
4. 是否是价格先涨后引发搜索，而非搜索推动价格？
5. 换窗口、换词包、换基准后结论是否稳定？

---

## 12. 数据谱系与运行谱系

### 12.1 两种谱系

- **数据谱系**：原始来源 → 观察值 → 归一化数据 → 特征 → 模型输入 → 报告。
- **运行谱系**：哪个 Job、Run、代码版本、参数和执行环境产生了结果。

### 12.2 OpenLineage 兼容映射

TEIF 最小对象映射：

- Job：采集器、归一化任务、特征构建、报告生成。
- Run：一次具体执行。
- Dataset：原始表、规范表、特征集、研究报告。
- Facet：词包版本、主题版本、数据质量、证据状态、模型版本、人工审核。

### 12.3 工件登记

所有重要截图、PDF、导出文件、网页快照、日志和报告必须保存：

- 内容哈希
- MIME 类型
- 大小
- 存储位置
- 来源 URI
- 获取时间
- 权限和保留策略
- 关联 Evidence / Event / Run

Git 仓库存放契约、配置、代码和小型测试夹具；大规模真实数据和版权工件进入受控对象存储。

---

## 13. 统一分析输出 Envelope

所有分析模块至少输出：

```yaml
assessment_id: ...
assessment_type: ...
subject_ids: []
as_of: ...
knowledge_cutoff: ...
valid_time_range: ...
claim: ...
claim_type: ...
likelihood:
  value: null
  band: null
analytic_confidence:
  level: LOW|MEDIUM|HIGH
  vector: {}
evidence_ids: []
counter_evidence_ids: []
alternative_explanations: []
assumption_ids: []
knowledge_gaps: []
change_indicators: []
method:
  name: ...
  version: ...
lineage:
  dataset_versions: []
  feature_versions: []
  model_version: null
  code_commit: null
review:
  status: DRAFT|REVIEWED|APPROVED|REJECTED
trade_action: NO_TRADE
research_only: true
```

---

## 14. 安全、权限与治理

### 14.1 写入边界

- 采集器只能写原始事实域。
- 解析器只能写派生事实域。
- 模型只能写候选判断域。
- 人工审核才能将候选判断升级为受控判断。
- 第二大脑默认只读事实和判断视图。
- 真实交易系统只读取经过显式批准的版本化特征。

### 14.2 数据分类

- Public
- Internal
- Confidential
- Restricted
- Personal / Sensitive
- Licensed Content

权限不仅按角色，还应按用途、项目和数据授权限制。

### 14.3 审计

记录：

- 谁查看、创建、修改、批准或撤回了什么
- 使用了哪些工具和权限
- 哪些模型和代码参与
- 哪些来源被拒绝或降权
- 哪些判断被人类覆盖及原因

### 14.4 交易安全

TEIF 输出默认：

```yaml
trade_action: NO_TRADE
research_only: true
```

只有通过数据质量、研究验证、回测、独立验收、策略风控和用户授权的版本化特征，才能由独立交易系统消费。

---

## 15. 技术实现建议

### 15.1 接口优先、存储中立

先固定契约、ID、时间语义和测试，再选数据库。避免把业务绑定到单一厂商。

### 15.2 最小可行技术栈

| 能力 | MVP 建议 |
|---|---|
| 契约 | JSON Schema / YAML 配置 / Pydantic 模型 |
| 事件账本 | PostgreSQL 只追加表或受控 Parquet 分区 |
| 时间查询 | PostgreSQL + 明确索引和 `as_of` 查询 |
| 工件 | 对象存储或受控文件系统 + 哈希登记 |
| 分析数据 | Parquet + DuckDB，后续评估 Iceberg/Delta |
| 图谱 | 初期关系表与图视图，规模扩大后评估图数据库或 RDF 存储 |
| 谱系 | OpenLineage 兼容事件，后续可接 Marquez 等后端 |
| 任务 | 复用现有调度与 WorkBuddy 运行环境 |
| 观测 | 结构化日志、运行 ID、指标和告警 |

### 15.3 规模化选项

达到以下条件后再评估 Kafka/Redpanda、Iceberg/Delta、图数据库和专用特征平台：

- 多源分钟级持续采集
- 每日百万级事件
- 多团队并行消费
- 复杂跨域图查询
- 严格 SLA 和灾备需求

---

## 16. 非功能性要求

### 16.1 正确性

- 时间字段不可静默降级。
- 缺失、零值、未收录、不可访问和采集失败严格区分。
- 任意分析结果可追溯至原始工件。
- 任意历史回测可重建知识截面。

### 16.2 可用性

- 关键数据源失败不得静默。
- 允许降级到人工流程。
- 报告明确显示数据缺口。

### 16.3 可扩展性

- 新业务模块只需接入统一 event、evidence 和 assessment 契约。
- 自定义字段通过 namespaced extensions，不污染核心模型。

### 16.4 可解释性

- 综合分必须可拆解。
- 任何高影响判断必须显示主要支持证据、反证和方法限制。

### 16.5 性能

- 研究查询与真实交易关键路径隔离。
- 全局图谱和证据查询不能阻塞订单系统。

---

## 17. 测试与验收

### 17.1 时间正确性

- 同一事件不同时间字段的解析测试
- 盘前、盘中、盘后和休市映射测试
- `as_of` 历史重放测试
- 修订和撤回测试
- 防未来数据泄漏测试

### 17.2 证据与谱系

- 每个 Feature 可追溯到 RawObservation
- 每个 Assessment 可追溯到 Evidence
- 每个 Dataset 可追溯到 Job / Run / Code Commit
- 同源转载独立性识别测试

### 17.3 可信度

- 概率与置信度字段分离测试
- 校准指标测试
- 证据不足时 abstention 测试
- 反证影响测试

### 17.4 因果研究

- 事件发生在结果之后时禁止直接归因
- 共同原因和反向因果检查
- 安慰剂和负对照
- 方法切换稳健性

### 17.5 安全

- 第二大脑无法写入交易事实域
- 模型无法批准自身判断
- 未审核特征无法进入策略白名单
- 工件权限和许可证约束测试

---

## 18. 关键架构决策

### ADR-TEIF-001：所有重大对象接入全局时间语义

决定：任何新增模块必须明确事件时间、观察时间、系统可用时间和有效区间的适用情况。

### ADR-TEIF-002：原始事实只追加

决定：原始事实和判断历史不覆盖，修订通过版本和关系表达。

### ADR-TEIF-003：概率与分析置信度分离

决定：事件概率、分析置信度、数据质量和模型校准分别建模。

### ADR-TEIF-004：证据向量优先于单一总分

决定：保留来源、直接性、独立性、完整性、时间匹配和反证等分项。

### ADR-TEIF-005：因果分级

决定：时间先后、关联、预测领先、机制和因果支持使用明确等级，不用“导致”一词掩盖证据差异。

### ADR-TEIF-006：基础层与业务层分离

决定：TEIF 提供统一服务，交易系统、注意力模块和第二大脑保持独立产品边界。

### ADR-TEIF-007：接口优先，避免过早平台化

决定：先实现契约、账本、时间轴和证据链，再根据规模选择流平台、湖仓和图数据库。

---

## 19. 参考资料

### 标准与企业文档

1. W3C, PROV-O: The PROV Ontology: https://www.w3.org/TR/prov-o/
2. CloudEvents Specification: https://cloudevents.io/
3. OpenLineage Documentation and Specification: https://openlineage.io/docs/
4. Microsoft Azure Architecture Center, Event Sourcing Pattern: https://learn.microsoft.com/azure/architecture/patterns/event-sourcing
5. NIST AI Risk Management Framework 1.0: https://doi.org/10.6028/NIST.AI.100-1
6. ODNI, ICD 203 Analytic Standards: https://www.dni.gov/files/documents/ICD/ICD-203.pdf
7. Databricks Unity Catalog Data Lineage: https://docs.databricks.com/aws/en/data-governance/unity-catalog/data-lineage
8. Palantir Foundry Ontology Overview: https://www.palantir.com/docs/foundry/ontologies/ontologies-overview

### 学术研究

1. Guan et al., “What is Event Knowledge Graph: A Survey,” arXiv:2112.15280.
2. Cai et al., “A Survey on Temporal Knowledge Graph: Representation Learning and Applications,” arXiv:2403.04782.
3. Runge, “Discovering contemporaneous and lagged causal relations in autocorrelated nonlinear time series datasets,” arXiv:2003.03685.
4. Guo et al., “On Calibration of Modern Neural Networks,” ICML 2017, PMLR 70:1321-1330.
5. Zhou et al., “Conformal Prediction: A Data Perspective,” arXiv:2410.06494.

---

## 20. 当前状态

| 能力 | 状态 |
|---|---|
| 基础层总体蓝图 | Proposed v0.1 |
| 统一事件契约 | 本 PR 提供初版 |
| 统一判断契约 | 本 PR 提供初版 |
| 全局时间轴服务 | 未实现 |
| 证据与工件库 | 未实现 |
| OpenLineage 兼容运行谱系 | 未实现 |
| 时序知识图谱 | 未实现 |
| 可信度与校准服务 | 未实现 |
| 因果假设工作台 | 未实现 |
| 注意力模块接入 | 设计映射阶段 |
| 第二大脑接入 | 设计映射阶段 |
| 真实交易接入 | 禁止，保持 `NO_TRADE` |
