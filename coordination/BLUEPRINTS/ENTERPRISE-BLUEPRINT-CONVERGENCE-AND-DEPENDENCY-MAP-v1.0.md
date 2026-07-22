# 第二大脑＋A股交易研究企业蓝图收敛与依赖地图 v1.0

> governance_id: `ENTERPRISE-BLUEPRINT-CONVERGENCE-AND-DEPENDENCY-FREEZE-0019`
>
> implementation_issue: `#72`
>
> status: `ACTIVE_GOVERNANCE_BASELINE / CODEX_VERIFICATION_PENDING`
>
> boundary: `research_only / NO_TRADE`

## 0. 收敛结论

本工程不再通过不断增加平行工作流解决新需求。近期新增的0017和0018属于跨模块能力：

- 0017归属W4策略研究与W7验证；
- 0018归属W7风险、W9工程学习与W11资本配置的治理交叉层；
- 不创建W14；
- 不创建第二套市场数据、事件证据、概率、Kelly、风险、组合、回放、记忆、执行或订单运行时。

企业系统统一为四个相互连接但权威分离的平面：

1. 治理与控制面；
2. 事实与证据面；
3. 研究与模型面；
4. 决策、资本与生存面。

所有模块都必须沿共享时间、证据、规则、概率、验证和结果校准合同连接。

## 1. 四平面架构

### 1.1 治理与控制面

| 工作流 | 唯一职责 | 禁止 |
|---|---|---|
| W1 | 企业架构、AMED、任务路由、权限和蓝图收敛 | 建业务运行时 |
| W8 | 多Agent协作、部署、可观测和运维编排 | 自行改变业务权威 |
| W9 | 影子运行、结果校准、工程学习、成熟度回写 | 影子结果直接变订单 |

### 1.2 事实与证据面

| 工作流 | 唯一职责 | 禁止 |
|---|---|---|
| W2 | 市场数据、时间语义、A股规则快照、成本与确定性回放 | 编造字段语义或交易意图 |
| W3 | SourceRecord、EvidenceItem、KnowledgeAtom、冲突、检索与长期记忆 | 第二套市场或事件采集运行时 |
| W5 | 事件、公告、消息、政策、预期与跨资产证据 | 新闻直接变概率或因果 |
| W13 | 公开参与者资金活动证据、方向/金额/身份置信度分离 | 市场签名冒充真实身份 |

### 1.3 研究与模型面

| 工作流 | 唯一职责 | 禁止 |
|---|---|---|
| W4 | 指标、特征、理论、策略、实验族与参数版本 | 自行配置资本或绕过验证 |
| W6 | 竞争性参与者假设、反事实和多方博弈情景 | 假设冒充账户身份事实 |
| W12 | 问题框定、ProbabilityEstimate、信息价值、稳健选择、时机、研究真实性与归因方法 | 复制W11资本配置或W7风险门 |

### 1.4 决策、资本与生存面

| 工作流/能力 | 唯一职责 | 禁止 |
|---|---|---|
| W10 | 世界模型、个人模型、任务上下文、DecisionEpisode和认知校准 | 个人偏好篡改世界事实 |
| W11 | 扣除净期望后的Kelly、资本配置和零仓位/弃权权威 | 生成概率或绕过W7 |
| W7 | 统一验证、研究真实性、风险包络和最终硬否决 | 创建第二套策略平台 |
| 0017 | 参考区穿越、收复、失败、延续、稳定、T+1与样本外验证 | 主力意图、伪订单流、直接交易 |
| 0018 | 净优势质量、有效独立次数、风险破产、容量、游戏保护、对账和关桌 | 第二套Kelly、风险或订单引擎 |

## 2. 核心对象唯一写权威

| 核心对象 | 唯一写权威 | 主要消费者 |
|---|---|---|
| `MarketTimeAndAvailabilityEnvelope` | W2 | 全系统 |
| `AShareRuleSnapshot` | W2 | W4/W7/W11/0017/0018 |
| `SourceRecord/EvidenceItem/KnowledgeAtom` | W3 | W5/W10/W12/W13 |
| `EventEvidencePacket` | W5 | W4/W6/W10/W12/0017/0018 |
| `ParticipantFlowEvidencePacket` | W13 | W4/W6/W10/W12/0017/0018 |
| `StrategyExperimentFamily` | W4 | W7/W9/W11/W12/0018 |
| `ParticipantHypothesis` | W6 | W10/W12，不作为身份事实 |
| `ProbabilityEstimate` | W12/DS-02 | W10/W11/W7/0018 |
| `DecisionEpisode` | W10 | W9/W11/W12 |
| `W11CandidateAllocation` | W11 | W7/W9/0018 |
| `W7RiskEnvelope` | W7 | W11/0018/影子报告 |
| `ValidationReport` | W7 | W4/W9/W11/W12/0017/0018 |
| `OutcomeCalibrationRecord` | W9 | W10/W11/W12/0018 |
| `ReferenceZoneBreachEvent/ReclaimAssessment` | 0017 within W4/W7 | W7/W9/W12 |
| `HouseEdgeInspiredNetEdgeEstimate` | 0018 within W7/W9/W11 | W7/W11/W9 |

任何核心对象不得出现第二写入者。其他模块只能读取、引用、附加自己的领域视图或提出候选变更。

## 3. 共享合同最小集合

### C1 时间与可得性

所有事实、特征、模型输入和结果必须保留：

- `event_time`
- `source_time`
- `published_at`
- `observed_at`
- `ingested_at`
- `available_at`
- `as_of`
- 修订版本和bar完成状态

### C2 A股规则

统一`AShareRuleSnapshot`按市场、板块、证券类型和生效日版本化，覆盖：

- T+1与lot-level可卖库存；
- 涨跌幅、停牌、复牌和无涨跌幅阶段；
- 集合竞价、连续竞价和盘后；
- 申报单位、价格步长和整数股；
- 成本、滑点、冲击、容量和成交概率；
- ST、退市、新股和历史制度。

### C3 证据与来源

所有推断必须链接不可覆盖的来源和证据，区分：

- 官方事实；
- 供应商定义字段；
- 模型推断；
- 竞争性解释；
- 反证；
- UNKNOWN；
- 不可访问证据。

### C4 概率与收益分布

`ProbabilityEstimate`由W12/DS-02生产，必须记录校准、预测期、条件状态、支持和反证。W11和0018不得自行生产平行概率。

### C5 验证与结果

所有策略和技能必须通过W7的统一点时、成本、T+1、样本外、多重检验、压力与影子验证，并由W9保存结果校准和成熟度变化。

## 4. 模块成熟度基线

| 模块 | 蓝图/合同 | 实现 | A股回测 | 影子 | 当前结论 |
|---|---|---|---|---|---|
| W2 | 部分完成 | 最小离线闭环存在 | 局部 | 未完整 | `PARTIAL_FOUNDATION_EXISTS` |
| W3 | 完成度较高 | Phase 3 canonical存在 | 不适用 | 部分待验 | `IMPLEMENTED_WITH_OPEN_GATES` |
| W4 | 多份蓝图 | 局部候选 | 不完整 | 未完成 | `PARTIAL_CANDIDATES` |
| W5/0015 | 已注册 | 未实现 | 未运行 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |
| W6 | 蓝图级 | 未实现 | 未运行 | 未开始 | `BLUEPRINT_ONLY` |
| W7 | 部分合同和测试 | 部分存在 | 局部 | 未完整 | `PARTIAL_FOUNDATION_EXISTS` |
| W9 | 治理与模板存在 | 部分 | 不适用 | 部分 | `ACTIVE_GOVERNANCE_PARTIAL_RUNTIME` |
| W10/0010 | 已注册 | 未实现 | 不适用 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |
| W11/0011 | 已注册 | 未实现 | 未运行 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |
| W12/0012 | D0完成于PR #66 | 子运行时未实现 | 未运行 | 未开始 | `D0_COMPLETE_PENDING_MERGE` |
| W13/0014 | 已注册 | 未实现 | 未运行 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |
| 0017 | 已注册 | 未实现 | 未运行 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |
| 0018 | 已注册 | 未实现 | 未运行 | 未开始 | `CONTRACTED_NOT_IMPLEMENTED` |

该表是治理基线，不得被解释为最终验收。Codex必须用仓库与可访问本地证据重新核验。

## 5. 依赖DAG

```text
W1/W8 governance
      ↓
W2 market-time-rules-replay ───────────────┐
W3 knowledge-evidence ────────┐             │
W5 event-policy evidence ─────┼→ W4/W6/W12 │
W13 participant evidence ─────┘             │
                                            ↓
W4 strategies/experiments → W7 validation ← 0017
             ↓                 ↑
W12 ProbabilityEstimate → W11 allocation
             ↓                 ↑
W10 DecisionEpisode            │
             ↓                 │
W9 outcome calibration ← 0018 net-edge/survival/control
```

0018必须消费W12概率、W11候选配置、W7风险和W9结果，不能成为概率或配置上游。

## 6. 当前关键路径

1. PR #66完成有界GPT验收，保留不自动合并；
2. Issue #72完成蓝图收敛、权威和共享接口冻结；
3. 再分别执行W13、PMN、0017和0018的D0实况审计；
4. 依据数据准备度、增量价值、验证成本和风险，只激活一个首批纵向切片；
5. 首批切片通过点时、成本、A股规则、样本外和影子门后，才能进入联合经济验证；
6. W11资本成熟度升级必须等待概率、风险、0018净优势和破产风险接口完成。

## 7. 首批候选排序框架

每个候选按以下维度评分，但不得在Issue #72前锁死结果：

- 数据是否真实可得和许可清楚；
- 是否已有可复用运行时；
- 点时重建难度；
- A股规则和成本可模拟程度；
- 单独经济增量是否可识别；
- 失败风险和负面外部性；
- 与其他模块的阻塞关系；
- 首个切片是否可以BAR_ONLY或官方来源优先；
- 验证和回滚成本。

候选包括：

- W13官方参与者证据简报；
- PMN官方政策日历与跨资产影子简报；
- 0017 BAR_ONLY参考区穿越/收复与T+1验证；
- W12 DS-01/DS-02/DS-10首批切片；
- W11单机会NetEV与稳健Kelly；
- 0018净优势/有效次数/破产风险影子报告。

## 8. WIP和并行原则

- Codex同时只能有一个活动任务；
- 治理审计可与QCLAW独立证据任务并行，但不能改同一文件；
- 同一共享接口冻结前，不并行实现其多个消费者；
- W13、PMN、0017、0018首批运行时最多激活一个；
- 新发现默认进入C类提案，不因发现而扩大WIP；
- 不自动合并，不直接进入实盘。

## 9. 停止条件

Issue #72遇到以下情况必须停止并升级：

- 两个模块都声称同一核心对象写权威；
- 可访问仓库和本地权威相互冲突；
- 需要改变真实市场数据、账户、凭证、服务或订单运行时；
- 需要新建canonical运行时；
- 无法在不丢失已验证资产的情况下完成收敛；
- 新任务将超过WIP上限。

## 10. 完成定义

只有以下全部完成，蓝图才视为收敛：

1. 权威矩阵无重复写入者；
2. 共享接口有producer、consumer、版本和UNKNOWN；
3. PROGRAM-INDEX、集成索引、执行序列和ACTIVE路由一致；
4. 0017、0018被嵌入既有工作流而不是平行平台；
5. 所有模块成熟度有证据；
6. 下一纵向切片排序有可复核依据；
7. YAML、UTF-8、引用和秘密扫描通过；
8. GPT完成AMED七门验收；
9. 全系统保持`research_only / NO_TRADE`。
