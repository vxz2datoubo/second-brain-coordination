# 时序证据智能基础层集成映射

> 文档状态：Proposed v0.1  
> 父蓝图：`TEMPORAL-EVIDENCE-INTELLIGENCE-FOUNDATION.md`  
> 目标：把 TEIF 与现有注意力信号、异常归因、交易研究、第二大脑和多 AI 协作方式整合  
> 默认交易状态：`NO_TRADE`  
> 最后更新：2026-07-18

---

## 1. 仓库现状审查

截至 2026-07-18，本仓库主分支仍以协作中枢 README 为主；当前 Draft PR #8 中已形成：

- 注意力信号引擎蓝图和 Backlog
- 注意力异常归因与歧义消解蓝图和 Backlog
- `Matrix / Matrix 3.5` 关键词歧义配置

当前可访问仓库中尚未发现一份独立、完整的“整个交易系统与第二大脑总蓝图”文件。因此本集成映射采用两步策略：

1. 以当前文档已经声明的项目关系为受控基线。
2. 待总蓝图进入同一仓库后，通过 ADR 和模块接口表完成逐项对齐，而不是覆盖旧蓝图。

本文件不是宣称已审查一个不存在于当前仓库的总蓝图，而是先建立可执行的融合框架和差异检查表。

---

## 2. 项目集目标结构

```text
                         项目集治理层
      GitHub / ADR / Capability Registry / Unknown Registry / 审核
                                │
                                ▼
                 时序证据智能基础层 TEIF
  时间轴│证据│谱系│可信度│版本│时序图谱│归因│因果假设│统一输出
          │                     │                     │
          ▼                     ▼                     ▼
   A股交易研究系统        超级第二大脑          未来业务应用
          │                     │
          ▼                     ▼
   独立策略与风控         只读研究与知识视图
          │
          ▼
   人工授权的真实交易
```

### 2.1 一个项目集，多个独立产品

- **项目集**：共享治理、契约、时间、证据、谱系和协作规则。
- **交易研究产品**：专注数据、特征、回测、策略研究和风控。
- **第二大脑产品**：专注查询、解释、知识组织、任务协调和研究复盘。
- **真实交易执行产品**：保持最小依赖、确定性、低延迟和高安全。
- **其他业务产品**：未来可以复用 TEIF，但不能直接写入交易事实域。

---

## 3. 基础能力层与业务能力层

### 3.1 基础能力层

| 基础模块 | 统一职责 | 主要消费者 |
|---|---|---|
| Global Timeline | 多时间语义、历史截面、交易日历 | 全部模块 |
| Event Ledger | 只追加事件、修订、撤回和重放 | 全部模块 |
| Evidence & Provenance | 来源、工件、Claim、证据与反证 | ASE、ASA、第二大脑、研究报告 |
| Data & Run Lineage | 数据和作业谱系 | Codex、WorkBuddy、回测、审计 |
| Confidence & Calibration | 概率、分析置信度、数据质量和模型校准 | 所有分析模块 |
| Temporal Knowledge Graph | 实体、事件、主题及其历史关系 | 第二大脑、ASE、产业映射 |
| Causal Hypothesis Service | 因果等级、机制、混杂、反证 | ASA、事件研究、策略研究 |
| Version & Decision Ledger | 配置、判断、审核和决策版本 | 全部模块 |
| Governance & Policy | 权限、用途、质量门禁、NO_TRADE | 全部模块 |

### 3.2 业务能力层

| 业务模块 | 核心职责 | 禁止重复建设 |
|---|---|---|
| ASE 注意力信号引擎 | 主动搜索、内容扩散、专业确认和市场同步 | 自建独立证据评分和历史时间字段 |
| ASA 异常归因 | 关键词消歧、异常原因和候选事件归因 | 自建不可复用的因果和 Claim 模型 |
| 交易研究 | 市场数据、特征、事件研究、回测和策略候选 | 自建不带 `available_at` 的事件库 |
| 第二大脑 | 查询、解释、研究记忆、任务与工件导航 | 直接修改交易事实、评分和回测历史 |
| 真实交易 | 风控、订单、状态机和执行审计 | 直接调用 LLM 或等待图谱查询 |

---

## 4. 与注意力信号引擎 ASE 的关系

### 4.1 当前 ASE 能力

ASE 已定义：

- 主动需求、内容供给、传播消费、专业确认、机构确认和资本市场同步
- 原始观察、主题、数据源、特征、阶段和 A 股映射
- `NO_TRADE` 侧车定位
- 词包版本和原始事实不可覆盖

### 4.2 迁移到 TEIF 的公共能力

| ASE 当前概念 | TEIF 归属 | 处理方式 |
|---|---|---|
| `RawObservation` | Event Ledger + Evidence | ASE 保留业务字段，复用基础 envelope |
| 采集时间 | Global Timeline | 扩展为 observed/ingested/available 等时间 |
| 来源截图 | Artifact Registry | 不再只存路径，增加哈希、权限和谱系 |
| 数据质量 | Confidence & Quality | 使用统一质量契约 |
| 主题词包版本 | Version Ledger | 统一版本和有效期 |
| 扩散阶段判断 | Assessment Envelope | 加支持证据、反证和改变指标 |
| 特征来源 | OpenLineage Mapping | 记录 Job/Run/Dataset/Commit |
| 领先滞后 | Causal Hypothesis Service | 明确最多代表预测领先，不自动等于因果 |

### 4.3 ASE 保留的业务专属能力

- 平台指数适配器
- 注意力特征工厂
- 搜索到内容的扩散阶段
- 主题热度组合与平台顺序
- A 股主题映射和市场同步

---

## 5. 与异常归因模块 ASA 的关系

### 5.1 当前 ASA 能力

ASA 已定义关键词、实体、主题三层对象，高歧义词先消歧，异常归因允许多候选和证据不足状态。

### 5.2 TEIF 提供的公共组件

| ASA 需求 | TEIF 能力 |
|---|---|
| 异常前后时间对齐 | Global Timeline |
| 候选事件 | Event Ledger + Temporal KG |
| 来源优先级 | Evidence Framework |
| 支持与反证 | Claim/Evidence Model |
| 置信度 | Confidence Vector |
| 原因 A/B/未知 | Assessment Envelope |
| 因果边界 | Causal Evidence Level C0-C5 |
| 报告可追溯 | Data/Run Lineage |

### 5.3 Matrix 案例的改造

`Matrix` 微信指数案例接入后，应形成：

```text
PlatformMetricEvent
  ├─ event_time: 2026-06-24
  ├─ observed_at: 用户实际查询时间
  ├─ available_at: 截图和口径通过校验时间
  ├─ evidence: 微信指数截图工件
  └─ keyword_version: tech.world_model.matrix v1

AttributionAssessment
  ├─ target_topic: tech.world_model
  ├─ alternatives: 电影 / 数学 / 机器人 / 软件 / 未知
  ├─ supporting evidence
  ├─ counter evidence
  ├─ causal level
  ├─ analytic confidence
  └─ status: INSUFFICIENT_EVIDENCE / AMBIGUOUS / LIKELY ...
```

在截图和完整窗口数据进入前，继续保持 `INSUFFICIENT_EVIDENCE`。

---

## 6. 与 A 股交易研究系统的关系

### 6.1 可进入研究层的数据

TEIF 可以向交易研究输出：

- 冻结版本的事件数据集
- 经过质量门禁的注意力特征
- 主题与公司映射版本
- 事件发生、公开和可用时间
- 来源、证据和置信度向量
- 因果假设等级
- 数据和运行谱系

### 6.2 禁止直接进入订单层的内容

- 原始自然语言新闻
- 未核验社交媒体内容
- LLM 自报概率
- 未通过历史校准的综合分
- `AMBIGUOUS` 或 `INSUFFICIENT_EVIDENCE` 判断
- 未冻结的词包和公司映射
- 使用未来修订数据生成的特征

### 6.3 策略特征出口门禁

只有满足以下条件的 FeatureVersion 才能进入策略研究白名单：

1. 契约验证通过。
2. 原始数据可追溯。
3. `available_at` 完整。
4. 缺失和异常规则明确。
5. 历史重放一致。
6. 无未来数据泄漏。
7. 回测和稳定性报告存在。
8. 特征版本冻结。
9. 独立验收通过。
10. 仍然仅是研究特征，不代表获准真实交易。

### 6.4 真实交易边界

```text
TEIF → 研究特征快照 → 策略研究 → 组合与风控 → 人工授权 → 订单系统
```

TEIF 不调用券商下单接口，不持有交易凭证，不控制订单状态机。

---

## 7. 与超级第二大脑的关系

### 7.1 第二大脑可读取

- 全局时间轴
- 主题演化图
- 证据和反证摘要
- 分析判断和版本差异
- 数据源可用性和未知项
- Codex / WorkBuddy 运行工件
- 研究报告和历史复盘

### 7.2 第二大脑可写入的独立域

- 用户笔记
- 人工标签
- 阅读状态
- 待办和研究问题
- 候选假设
- 审核意见

这些写入必须保存为 UserAnnotation、ReviewComment 或 ResearchQuestion，不能覆盖 RawObservation、MarketData 或已冻结 Assessment。

### 7.3 防污染原则

第二大脑生成的总结属于派生工件。它可以链接事实，但不能成为事实本身，除非通过独立证据和人工审核升级。

---

## 8. 与 Codex、WorkBuddy、ChatGPT 的协同

### 8.1 Codex

负责：

- 契约和类型模型
- Event Ledger 和 as-of 查询
- 证据、谱系和版本服务
- 数据质量门禁
- 特征与校准代码
- 测试、CI、迁移和性能
- ADR 和代码级文档

不得：

- 假设未验证平台权限
- 在没有数据的情况下伪造适配器成功
- 绕过审核直接连接真实交易

### 8.2 WorkBuddy

负责：

- 本地环境和账号能力审计
- 平台页面、官方导出和授权 API 接入
- 截图、导出文件和运行日志工件化
- 调度、失败重试、告警和运行报告
- Capability Registry 与 Unknown Registry 更新

不得：

- 绕过验证码或反自动化机制
- 把登录失败当零值
- 把人工观察伪装成官方 API

### 8.3 ChatGPT

负责：

- 深度研究和来源审计
- 主题、事件和证据模型设计
- 任务拆解和验收标准
- 分析报告与反证检查
- 跨模块一致性审查
- 对 Codex 和 WorkBuddy 工件做独立验收

不得：

- 将语言流畅度当证据
- 在证据不足时补全原因
- 自行批准高风险上线

### 8.4 用户

负责：

- 账号、付费数据和授权
- 业务优先级
- 公司映射和高影响判断审核
- 资金、风控阈值和真实交易批准
- 对项目边界和成本做最终决策

---

## 9. 统一协作工件

| 工件 | GitHub 路径建议 | 维护者 |
|---|---|---|
| 总体蓝图 | `docs/architecture/` | ChatGPT + Codex |
| ADR | `docs/architecture/adr/` | Codex |
| 契约 | `contracts/foundation/` | Codex |
| 能力登记 | `registries/capabilities/` | WorkBuddy |
| 未知项 | `registries/unknowns/` | ChatGPT + WorkBuddy |
| 主题配置 | `configs/topics/` | ChatGPT + 用户 |
| 数据源配置 | `configs/sources/` | WorkBuddy + Codex |
| 质量策略 | `configs/quality/` | Codex |
| 置信度策略 | `configs/confidence/` | ChatGPT + Codex |
| 小型测试夹具 | `tests/fixtures/` | Codex |
| 运行报告引用 | `artifacts/index/` | WorkBuddy |
| 验收报告 | `reports/acceptance/` | ChatGPT |

---

## 10. 总蓝图未来对齐清单

当现有总体系统蓝图进入本仓库后，必须逐项检查：

### 10.1 架构

- 是否已有事件总线或统一数据层？
- 是否已有知识图谱，时间语义是什么？
- 是否已有谱系、工件和版本管理？
- 是否已有策略特征库和数据门禁？
- 是否已有第二大脑写入隔离？

### 10.2 数据模型

- 现有事件是否区分 event/publish/observe/available？
- 现有数据是否可做 as-of 重放？
- 现有“可信度”是否混合概率、质量和来源？
- 现有知识是否可修订而不覆盖历史？

### 10.3 技术与运维

- 当前数据库、对象存储、调度器和日志系统是什么？
- 是否已有消息队列，是否真的需要？
- 是否已有 OpenTelemetry/OpenLineage 或类似观测？
- 当前部署环境和备份恢复能力是什么？

### 10.4 治理

- 当前谁能写事实、特征、判断和订单？
- 当前是否存在统一审批和审计？
- 真实交易凭证和研究系统是否隔离？
- 版权、个人信息和商业数据源如何治理？

对齐结果分为：

- `REUSE`：直接复用现有能力。
- `ADAPT`：增加适配层。
- `MIGRATE`：逐步迁移。
- `DEPRECATE`：停止重复能力。
- `UNKNOWN`：待真实环境确认。

---

## 11. 目标数据流

### 11.1 注意力数据

```text
微信/百度/抖音/小红书等观察
→ Event Envelope
→ 原始工件和 Evidence
→ 时间与质量门禁
→ ASE Feature
→ 扩散阶段 Assessment
→ 第二大脑只读卡片 / 策略研究快照
```

### 11.2 异常归因

```text
异常指标
→ 异常事件
→ 候选事件检索
→ Entity/Topic 消歧
→ Evidence + CounterEvidence
→ CausalHypothesis C0-C5
→ AttributionAssessment
```

### 11.3 交易研究

```text
市场数据 + 事件 + 主题 + 注意力
→ available_at 截面
→ 特征版本
→ 回测 Run
→ 谱系与校准报告
→ 独立验收
→ 研究白名单
```

### 11.4 第二大脑查询

```text
用户问题
→ 时间/主题/实体解析
→ 只读查询 TEIF
→ 返回 Claim + Evidence + Confidence + Version
→ 用户注释写入独立 Annotation 域
```

---

## 12. 建议实施顺序

1. **统一契约和 ADR**：先确定语言。
2. **不可变事件账本和时间字段**：先能重放历史。
3. **证据工件与谱系**：先能证明结果从哪里来。
4. **全局时间轴查询**：让不同模块在同一时间轴说话。
5. **可信度与校准**：让概率不再是装饰数字。
6. **ASE/ASA 接入**：用世界模型和 Matrix 案例验证。
7. **时序知识图谱**：在真实对象和事件积累后建设。
8. **因果研究工作台**：在数据量和质量足够后上线。
9. **第二大脑只读接入**。
10. **交易研究特征出口**，继续保持 `NO_TRADE`。

---

## 13. 完成定义

集成不是“文档互相加链接”。第一阶段完成必须满足：

- ASE 和 ASA 使用统一 Event / Evidence / Assessment 契约。
- 任意注意力特征可以回到原始平台工件。
- Matrix 案例可以按历史时点重放。
- 概率和分析置信度分开显示。
- 同源转载不会虚增证据数量。
- 第二大脑只读权限经过测试。
- 回测使用 `available_at`，无未来信息。
- Codex、WorkBuddy、ChatGPT 的交接工件有统一 ID 和状态。
- 任何证据不足的判断能够稳定输出 abstention。
- 真实交易执行仍然完全独立。
