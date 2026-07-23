# 注意力异常归因与歧义消解蓝图

> 文档状态：Proposed v0.1  
> 父模块：注意力信号引擎（ASE）  
> 子模块名称：注意力异常归因与歧义消解（Attention Signal Attribution，ASA）  
> 默认交易状态：`NO_TRADE`  
> 首个验证案例：`Matrix` / `Matrix 3.5` / `世界模型`  
> 最后更新：2026-07-18

## 1. 目标

注意力信号引擎回答“某个词是不是变热了”。本子模块继续追问：

1. 为什么变热？
2. 热度对应的是我们关心的主题，还是同名词造成的污染？
3. 哪些具体事件、内容、账号、公告或产品推动了异常？
4. 归因结论有多可信？
5. 如果证据不足，系统能否诚实输出“原因未确定”？

该模块不负责直接生成买卖指令。它输出结构化归因、证据链、候选解释、歧义风险和置信度，供研究人员、回测系统和第二大脑只读使用。

## 2. 问题定义

### 2.1 典型问题

假设微信指数中的 `Matrix` 在某日出现异常高值。该词可能同时指向：

- 昆仑万维或其他公司发布的 Matrix 系列 AI 模型
- `Matrix 3.5` 具体产品或版本
- 电影《The Matrix / 黑客帝国》
- 数学中的矩阵
- 软件、公司、机器人、加密项目或游戏名称
- 新闻标题中的普通英文词

单看指数无法证明热度来自目标技术主题。系统必须把“词的热度”与“主题的热度”分开。

### 2.2 三层对象

- **关键词 Keyword**：用户实际查询的字符串，例如 `Matrix`。
- **语义实体 Entity**：字符串可能指向的对象，例如电影、数学概念、AI 模型、公司。
- **研究主题 Topic**：交易研究关注的抽象方向，例如世界模型、具身智能或昆仑万维 AI 产品矩阵。

关键词可以映射多个实体；多个实体可以属于同一研究主题。归因必须在三层之间留下可审计映射。

## 3. 核心原则

### 3.1 先消歧，再计算主题热度

高歧义关键词不能直接进入主题综合分。必须先计算目标语义占比或降低权重。

### 3.2 事件归因不是强行讲故事

系统可以列出候选原因，但只有在时间、语义、来源和传播路径均有证据时，才输出高置信度归因。

### 3.3 多候选并存

一次异常可能由多个事件共同推动。系统允许输出：

```text
原因 A：55%
原因 B：25%
其他或无法识别：20%
```

这些百分比是归因权重或模型置信分布，不得伪装成真实用户构成比例，除非数据源确实提供此类统计。

### 3.4 时间因果边界

候选事件发生在异常之后，不能作为该异常的直接原因。转载和二次扩散需要区分首发时间与传播峰值。

### 3.5 证据优先级

优先使用官方公告、官方账号、发布会、公司公告、平台原始内容和可信媒体。搜索摘要、搬运内容和无来源截图只能作为弱证据。

### 3.6 默认不交易

所有归因结果均为研究工件：

```yaml
trade_action: NO_TRADE
research_only: true
```

## 4. 总体架构

```text
异常指数或热度序列
        ↓
异常检测器
        ↓
关键词歧义画像
        ↓
候选事件检索与采集
        ↓
实体识别、主题分类、内容聚类
        ↓
时间与传播路径对齐
        ↓
证据评分与反证检查
        ↓
候选原因排序
        ↓
归因报告、置信度、未知项
```

## 5. 输入

### 5.1 必需输入

- `topic_id`
- `keyword_id`
- 关键词原文
- 平台和指标名称
- 异常日期或异常窗口
- 原始指数或热度序列
- 关键词词包版本
- 数据质量状态

### 5.2 可选输入

- 相关词和联想词
- 平台内搜索结果标题、摘要和账号
- 当日新闻、公告、发布会、论文和视频
- 内容发布时间、互动量和传播链路
- 公司、产品、模型和人物实体字典
- 历史同类异常案例
- 资本市场同期事件

## 6. 输出

### 6.1 `AttributionAssessment`

```json
{
  "assessment_id": "asa_matrix_20260624_wechat",
  "topic_id": "tech.world_model",
  "keyword_id": "kw.matrix",
  "source_id": "wechat_index",
  "metric_id": "keyword_index",
  "anomaly_window": {
    "start": "2026-06-24",
    "end": "2026-06-24"
  },
  "ambiguity_level": "HIGH",
  "target_relevance_score": 0.34,
  "status": "INSUFFICIENT_EVIDENCE",
  "candidate_causes": [],
  "counter_evidence": [],
  "unexplained_share": null,
  "confidence": 0.22,
  "trade_action": "NO_TRADE",
  "notes": "示例结构，不代表已完成真实归因"
}
```

### 6.2 状态枚举

| 状态 | 含义 |
|---|---|
| `CONFIRMED_SINGLE_CAUSE` | 单一原因证据充分 |
| `CONFIRMED_MULTI_CAUSE` | 多个原因共同推动，证据充分 |
| `LIKELY` | 有较强候选原因，但仍有明显不确定性 |
| `AMBIGUOUS` | 多个解释接近，无法可靠区分 |
| `INSUFFICIENT_EVIDENCE` | 缺少数据或证据链 |
| `UNRELATED_SPIKE` | 异常主要来自目标主题之外 |
| `DATA_ARTIFACT` | 平台口径、数据修订、采集错误或算法变化导致 |

## 7. 关键词歧义模型

### 7.1 歧义等级

| 等级 | 定义 | 示例 |
|---|---|---|
| `LOW` | 基本唯一，目标实体明确 | `Matrix 3.5 昆仑万维` |
| `MEDIUM` | 存在少量同名实体，可通过上下文消歧 | `Matrix 3.5` |
| `HIGH` | 多领域高频同名词 | `Matrix` |
| `EXTREME` | 通用词、字母缩写或人名，几乎无法单独使用 | `AI`、`Agent`、`Apple` |

### 7.2 关键词角色

- `ANCHOR`：高唯一性锚点词，直接指向目标实体。
- `CORE`：主题核心词，但可能存在少量歧义。
- `BROAD`：覆盖面广，用于发现扩散，但不能独立归因。
- `EXCLUSION`：排除词，用于去除电影、数学或其他同名领域。
- `CONTEXT`：公司名、创始人、产品线、发布日期等辅助词。

### 7.3 Matrix 试点词包

```yaml
topic_id: tech.world_model
keyword_groups:
  anchor:
    - Matrix 3.5 昆仑万维
    - 昆仑万维 Matrix 3.5
    - Matrix 世界模型 昆仑万维
  core:
    - Matrix 3.5
    - 世界模型
    - World Model
  broad:
    - Matrix
    - 矩阵
  context:
    - 昆仑万维
    - SkyReels
    - Riemann
    - 黎曼模型
  exclusions:
    - 黑客帝国
    - The Matrix 电影
    - 线性代数
    - 矩阵乘法
    - Matrix Robotics
```

排除词只能作为辅助过滤，不能简单删除全部匹配内容。例如一篇文章可能同时讨论数学矩阵与 AI 世界模型。

## 8. 异常检测

### 8.1 异常类型

- 单日尖峰
- 多日持续抬升
- 阶梯式上升
- 周期性峰值
- 平台单点异常
- 跨平台同步异常
- 搜索先行、内容滞后
- 内容先行、搜索滞后
- 指数突变但无外部事件

### 8.2 基线方法

首版采用透明方法：

- 滚动中位数和 MAD
- 7 日、30 日分位数
- 同比和环比
- 变化率与加速度
- 平台间一致性
- 节假日和星期效应

后续可加入贝叶斯变点、孤立森林或时序模型，但不能取代可解释基线。

### 8.3 异常门槛

异常门槛按平台和指标独立配置。一个平台的指数 70 万，不能与另一个平台的 70 万直接比较。

## 9. 候选事件发现

异常窗口确定后，系统围绕以下来源生成候选事件：

1. 公司官方公告和官方账号
2. 产品发布会、版本发布和开发者活动
3. 监管公告和交易所互动
4. 主流媒体报道
5. 微信公众号、微博、抖音、小红书、B站和知乎内容
6. 论文、代码仓库、模型平台和技术社区
7. 影视、游戏、数学、机器人等同名领域事件
8. 平台算法、榜单规则或指数口径变化

候选事件窗口默认覆盖异常前若干日到异常后若干日，具体窗口按平台传播速度配置。

## 10. 内容聚类与实体识别

### 10.1 处理流程

- 标题、摘要和正文清洗
- 实体识别
- 主题分类
- 近重复内容去重
- 转载链识别
- 内容聚类
- 首发源识别
- 传播规模估计

### 10.2 目标语义分类

对于 `Matrix`，首版至少分为：

- `TARGET_WORLD_MODEL`
- `AI_OTHER`
- `MOVIE_THE_MATRIX`
- `MATHEMATICS_MATRIX`
- `ROBOTICS_OR_COMPANY`
- `SOFTWARE_OR_PRODUCT`
- `CRYPTO_OR_GAME`
- `UNKNOWN`

系统必须保留 `UNKNOWN`，不能把无法判断的内容硬塞进某一类。

## 11. 候选原因评分

每个候选原因由以下分项组成：

```text
AttributionScore = f(
  TemporalFit,
  SemanticFit,
  SourceAuthority,
  PlatformMatch,
  VolumeContribution,
  CrossPlatformSupport,
  PropagationFit,
  CounterEvidencePenalty,
  DataQualityPenalty
)
```

### 11.1 分项解释

- `TemporalFit`：事件与异常在时间上是否匹配。
- `SemanticFit`：内容是否真正指向目标实体或主题。
- `SourceAuthority`：来源是否官方、可信、可核验。
- `PlatformMatch`：事件是否可能影响对应平台用户。
- `VolumeContribution`：相关内容规模是否足以解释异常。
- `CrossPlatformSupport`：其他平台是否出现相似变化。
- `PropagationFit`：传播路径是否符合先发、转载和峰值顺序。
- `CounterEvidencePenalty`：是否存在更强的无关事件。
- `DataQualityPenalty`：指数和采集数据是否可靠。

首版以规则评分为主。任何机器学习模型都必须保留分项解释。

## 12. 反证机制

归因报告必须主动寻找反证：

- 同日是否有更大的电影、游戏、数学或其他同名事件？
- 目标公司的官方渠道是否完全没有动作？
- 目标主题在其他平台是否没有同步变化？
- 指数是否在每周同一天周期性冲高？
- 是否发生平台数据口径或产品升级？
- 搜索结果是否被少数营销账号垄断？
- 异常是否来自错误拼写、自动补全或热榜推荐？

没有反证检查的归因，只能标为研究假设。

## 13. 归因报告模板

```markdown
# 注意力异常归因报告

## 异常概况
- 关键词：Matrix
- 平台：微信指数
- 日期：2026-06-24
- 异常类型：单日尖峰
- 数据质量：待核验

## 歧义画像
- 歧义等级：HIGH
- 目标主题：世界模型 / 昆仑万维 Matrix 3.5
- 主要竞争语义：电影、数学、机器人、软件

## 候选原因
1. 候选事件 A
   - 时间匹配：
   - 语义匹配：
   - 来源：
   - 支持证据：
   - 反证：
   - 置信度：

## 结论
- 状态：INSUFFICIENT_EVIDENCE
- 目标相关性：未知
- 未解释部分：未知
- 交易状态：NO_TRADE
```

## 14. 数据模型

### 14.1 新增实体

- `KeywordDefinition`
- `KeywordSense`
- `AnomalyEvent`
- `CandidateCause`
- `EvidenceItem`
- `CounterEvidenceItem`
- `ContentCluster`
- `PropagationEdge`
- `AttributionAssessment`

### 14.2 `EvidenceItem` 建议字段

```yaml
evidence_id: string
evidence_type: OFFICIAL_RELEASE | ANNOUNCEMENT | NEWS | SOCIAL_POST | VIDEO | PAPER | PLATFORM_CHANGE
source_name: string
source_url_or_artifact: string
published_at: datetime
first_seen_at: datetime
author_or_account: string
entities: []
topic_labels: []
content_hash: string
credibility_grade: A | B | C | D
supports_candidate_id: string
notes: string
```

## 15. 目录建议

```text
contracts/attention_attribution/
  keyword.schema.json
  anomaly.schema.json
  evidence.schema.json
  attribution.schema.json

configs/attention/keywords/
  tech.world_model.matrix.yaml

pipelines/attention/attribution/
  anomaly_detection/
  candidate_discovery/
  entity_resolution/
  content_clustering/
  propagation_analysis/
  evidence_scoring/
  report_generation/

services/attention/attribution/
  ambiguity_registry/
  attribution_engine/

reports/attention/attribution/
  daily/
  cases/

tests/attention/attribution/
```

## 16. Matrix 首个案例研究

### 16.1 研究问题

微信指数中的 `Matrix` 在 2026-06-24 出现高值时，目标世界模型主题贡献了多少，是否存在更强的同名事件？

### 16.2 必需数据

- 微信指数截图或人工记录
- 前后至少 30 日序列
- 当日微信内相关内容样本
- 百度、抖音、微博、B站、小红书等同期变化
- `Matrix 3.5`、`昆仑万维`、`世界模型` 等锚点词序列
- 当日及前后新闻、公告、发布会和影视事件

### 16.3 验证逻辑

1. 确认指数值、日期和数据口径。
2. 检查是否为周期性异常或数据错误。
3. 比较高歧义词 `Matrix` 与低歧义锚点词。
4. 抽样分类微信内相关内容。
5. 聚类同日候选事件。
6. 对齐其他平台变化。
7. 输出候选原因、反证和置信度。
8. 证据不足时保持 `INSUFFICIENT_EVIDENCE`。

## 17. 验收标准

第一版必须满足：

1. 能区分关键词、语义实体和研究主题。
2. 能登记高歧义词和低歧义锚点词。
3. 任意归因结论可以回溯到证据项。
4. 能输出多个候选原因，而不是只给单一故事。
5. 能输出反证、未知项和未解释部分。
6. 候选事件在时间上必须早于或覆盖异常传播。
7. 平台口径变化可以被识别为数据伪异常。
8. `Matrix` 不得直接等同于 `Matrix 3.5`。
9. 归因置信度不足时不得进入正式主题分数。
10. 所有报告默认 `NO_TRADE`。

## 18. 关键风险

- 微信等封闭生态内容样本不足。
- 平台指数算法不透明，无法精确分解贡献。
- 搜索结果受个性化推荐影响。
- 转载时间晚于首发时间，导致因果顺序判断错误。
- 同一内容跨平台搬运，造成虚假证据数量。
- 大模型分类产生幻觉或过度归类。
- 为解释股价事后挑选新闻，形成叙事偏差。
- 高歧义词的目标相关性无法稳定估计。

## 19. 决策记录

### ADR-ASA-001：高歧义词不得直接计入主题热度

决定：`Matrix`、`Agent`、`AI` 等高歧义词必须经过消歧或显著降权。

### ADR-ASA-002：异常必须附归因状态

决定：所有异常输出至少标记 `LIKELY`、`AMBIGUOUS`、`INSUFFICIENT_EVIDENCE`、`UNRELATED_SPIKE` 或 `DATA_ARTIFACT`。

### ADR-ASA-003：允许原因未确定

决定：证据不足时，系统必须输出“原因未确定”，不得用语言模型补齐一个听起来合理的故事。

### ADR-ASA-004：归因结果不直接驱动交易

决定：归因是研究解释层，不进入订单关键路径。只有经历史验证的结构化特征，才可能在未来进入策略研究层。
