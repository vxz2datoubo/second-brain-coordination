# 时序证据智能基础层实施任务清单

> 状态：Draft v0.1  
> 依赖蓝图：`TEMPORAL-EVIDENCE-INTELLIGENCE-FOUNDATION.md`  
> 集成映射：`TEMPORAL-EVIDENCE-INTEGRATION-MAP.md`  
> 默认交易状态：`NO_TRADE`  
> 最后更新：2026-07-18

---

## 1. 执行原则

1. 先契约，后数据库。
2. 先历史正确性，后实时性。
3. 先证据追溯，后复杂模型。
4. 先人工可验证闭环，后自动化。
5. 先世界模型与 Matrix 案例，后多主题扩展。
6. 未通过质量和回测门禁的输出不得进入策略白名单。
7. 所有任务必须附测试、工件、已知限制和交接记录。

---

## 2. 角色

| 角色 | 主责 |
|---|---|
| 用户 | 权限、付费数据、业务优先级、公司映射、真实交易和高风险批准 |
| ChatGPT | 研究、架构、来源审计、任务拆解、反证和独立验收 |
| Codex | 契约、代码、数据模型、测试、CI、迁移、性能和技术文档 |
| WorkBuddy | 真实环境、平台接入、工件、调度、监控、失败和能力登记 |

---

## 3. Epic 总览

| Epic | 名称 | 目标 |
|---|---|---|
| TEIF-E00 | 治理与架构对齐 | 固化边界、ADR、现状和未知项 |
| TEIF-E01 | 核心契约 | 统一 Event、Evidence、Claim、Assessment 和 Lineage |
| TEIF-E02 | 不可变事件账本 | 建立只追加历史和修订机制 |
| TEIF-E03 | 全局时间轴 | 建立多时间语义、as-of 和交易日历 |
| TEIF-E04 | 证据与工件 | 建立来源、工件、Claim 和反证追溯 |
| TEIF-E05 | 数据与运行谱系 | 建立 OpenLineage 兼容运行记录 |
| TEIF-E06 | 可信度与校准 | 分离概率、置信度、质量并进行历史校准 |
| TEIF-E07 | 时序知识图谱 | 建立实体、事件、主题和版本关系 |
| TEIF-E08 | 因果假设与归因 | 建立 C0-C5 因果等级和研究工作台 |
| TEIF-E09 | ASE / ASA 集成 | 用世界模型和 Matrix 案例形成闭环 |
| TEIF-E10 | 第二大脑与交易研究出口 | 建立只读视图和受控特征快照 |
| TEIF-E11 | 生产治理 | 安全、观测、备份、恢复和持续验收 |

---

## 4. TEIF-E00：治理与架构对齐

### TEIF-0001 创建基础层治理文件

- 优先级：P0
- 主责：Codex
- 协作：ChatGPT
- 输出：`docs/architecture/AGENTS.md`
- 内容：目录责任、写入边界、评审要求、NO_TRADE、禁止事项
- 验收：模型、采集器、第二大脑和交易系统的写权限明确

### TEIF-0002 创建 ADR 目录和索引

- 优先级：P0
- 主责：Codex
- 输出：`docs/architecture/adr/README.md`
- 首批 ADR：时间语义、只追加事件、概率与置信度分离、基础层边界、存储中立

### TEIF-0003 现有系统事实盘点

- 优先级：P0
- 主责：WorkBuddy
- 协作：Codex
- 输出：当前数据库、文件、调度、部署、账号、数据源、日志、备份和权限报告
- 验收：每项为 VERIFIED / UNKNOWN / BLOCKED，不允许根据想象填写

### TEIF-0004 总蓝图差异分析

- 优先级：P0
- 主责：ChatGPT
- 前置：总体系统蓝图已进入仓库
- 输出：REUSE / ADAPT / MIGRATE / DEPRECATE / UNKNOWN 映射表
- 验收：不覆盖原蓝图，所有冲突形成 ADR 候选

### TEIF-0005 建立风险与未知登记

- 优先级：P0
- 主责：ChatGPT + WorkBuddy
- 输出：`registries/unknowns/teif.yaml`
- 包含：技术、权限、数据、时间、合规、成本、模型和交易风险

---

## 5. TEIF-E01：核心契约

### TEIF-0101 Event Envelope Schema

- 优先级：P0
- 主责：Codex
- 输出：`contracts/foundation/event-envelope.schema.json`
- 必含：事件标识、类型、来源、生产者、多时间字段、版本、工件、质量和 NO_TRADE
- 验收：正例、缺失时间反例、错误时区反例、修订事件样例

### TEIF-0102 Evidence Schema

- 优先级：P0
- 主责：Codex
- 输出：EvidenceItem、Source、Artifact 和 provenance 关系契约
- 验收：来源可靠性和证据质量分离

### TEIF-0103 Claim Schema

- 优先级：P0
- 主责：Codex
- 协作：ChatGPT
- 输出：事实、报道、派生指标、解释、预测、因果假设和建议类型
- 验收：支持证据、反证、替代解释和假设可登记

### TEIF-0104 Assessment Envelope Schema

- 优先级：P0
- 主责：Codex
- 输出：`contracts/foundation/assessment-envelope.schema.json`
- 验收：likelihood、analytic confidence、data quality、calibration 分离

### TEIF-0105 Lineage Event Schema

- 优先级：P1
- 主责：Codex
- 输出：OpenLineage Job/Run/Dataset 映射和扩展 facets
- 验收：可追踪词包、主题、模型、代码和数据版本

### TEIF-0106 版本与兼容策略

- 优先级：P0
- 主责：Codex
- 输出：Schema SemVer、向后兼容、迁移、废弃和验证规则
- 验收：旧事件不会因新字段加入而无法读取

### TEIF-0107 示例与夹具

- 优先级：P1
- 主责：Codex
- 输出：Matrix 指数事件、官方公告事件、修订事件、数据质量失败和归因判断样例

---

## 6. TEIF-E02：不可变事件账本

### TEIF-0201 存储 ADR

- 优先级：P0
- 主责：Codex
- 候选：PostgreSQL 只追加表、Parquet 分区、事件存储产品
- 验收：基于当前环境和规模选择，不为“企业级”三个字盲目上 Kafka

### TEIF-0202 事件写入器

- 优先级：P1
- 主责：Codex
- 输出：契约校验、幂等键、哈希、写入和错误分类
- 验收：重复运行不产生不可控重复

### TEIF-0203 修订与撤回

- 优先级：P1
- 主责：Codex
- 输出：`revises_event_id`、`retracts_event_id`、`supersedes_event_id`
- 验收：旧版本仍可查询，当前视图正确

### TEIF-0204 当前状态物化

- 优先级：P1
- 主责：Codex
- 输出：从事件账本生成 current state 的只读视图
- 验收：可删除重建，结果一致

### TEIF-0205 历史重放

- 优先级：P1
- 主责：Codex
- 输出：按 `as_of` / `knowledge_cutoff` 重建历史
- 验收：Matrix 案例能够重建 2026-06-24 当时知识截面

### TEIF-0206 事件完整性监控

- 优先级：P2
- 主责：WorkBuddy
- 输出：延迟、重复、断档、哈希冲突和 schema 失败告警

---

## 7. TEIF-E03：全局时间轴

### TEIF-0301 时间字段解析库

- 优先级：P0
- 主责：Codex
- 输出：原始字符串、时区、精度、UTC 和错误状态
- 验收：日期级信息不会被伪造成精确时刻

### TEIF-0302 交易日历服务

- 优先级：P1
- 主责：Codex
- 输出：A 股交易日、盘前、盘中、盘后、节假日和下一可交易时间
- 验收：跨午夜、周末、节假日和临时休市测试

### TEIF-0303 available_at 计算

- 优先级：P0
- 主责：Codex
- 输出：采集、处理、质量通过后合法可用时间
- 验收：回测只能读取 `available_at <= as_of`

### TEIF-0304 全局时间轴查询 API

- 优先级：P1
- 主责：Codex
- 输出：按主题、实体、事件类型、来源和时间轴查询
- 视图：现实发生、公开传播、系统认知、知识有效、市场作用

### TEIF-0305 时间冲突处理

- 优先级：P1
- 主责：Codex
- 输出：多来源不同时间、估计时间、区间和不确定时间处理

### TEIF-0306 未来数据泄漏测试套件

- 优先级：P0
- 主责：Codex
- 验收：故意注入后续修订、盘后消息和下一日数据时测试必须失败

---

## 8. TEIF-E04：证据与工件

### TEIF-0401 Source Registry

- 优先级：P1
- 主责：WorkBuddy
- 输出：来源身份、类型、权限、历史可靠性、访问方式和许可

### TEIF-0402 Artifact Registry

- 优先级：P1
- 主责：Codex
- 协作：WorkBuddy
- 输出：文件哈希、MIME、大小、存储、来源、获取时间和权限

### TEIF-0403 Provenance Graph

- 优先级：P1
- 主责：Codex
- 输出：Entity / Activity / Agent 及 generated/used/derived/attributed 关系
- 验收：任意 Assessment 能回溯到原始工件和处理活动

### TEIF-0404 同源传播聚类

- 优先级：P2
- 主责：Codex
- 输出：origin cluster 和 independence group
- 验收：100 篇转载不会被计算为 100 份独立证据

### TEIF-0405 Claim 与证据关联

- 优先级：P1
- 主责：Codex
- 输出：supports / contradicts / contextualizes / supersedes 关系

### TEIF-0406 人工核验工作流

- 优先级：P1
- 主责：WorkBuddy
- 协作：用户 + ChatGPT
- 输出：未核验、来源核验、内容核验、交叉支持、冲突、撤回状态流

### TEIF-0407 版权与保留策略

- 优先级：P1
- 主责：用户 + WorkBuddy
- 输出：公开、内部、付费、受限和个人信息工件规则

---

## 9. TEIF-E05：数据与运行谱系

### TEIF-0501 OpenLineage 映射 ADR

- 优先级：P1
- 主责：Codex
- 输出：Job、Run、Dataset、Facet 与本项目对象映射

### TEIF-0502 采集作业埋点

- 优先级：P1
- 主责：WorkBuddy
- 输出：START / RUNNING / COMPLETE / FAIL 事件

### TEIF-0503 特征管线谱系

- 优先级：P1
- 主责：Codex
- 输出：原始观察到特征和报告的输入输出谱系

### TEIF-0504 代码和环境谱系

- 优先级：P1
- 主责：Codex
- 输出：Git commit、依赖锁、配置版本、模型版本和运行参数

### TEIF-0505 谱系查询

- 优先级：P2
- 主责：Codex
- 能力：上游、下游、影响分析、根因追踪、失败 Run 和重跑

### TEIF-0506 谱系完整性门禁

- 优先级：P1
- 主责：Codex
- 验收：缺少关键输入版本的 Feature 不得标记为 RELEASED

---

## 10. TEIF-E06：可信度与校准

### TEIF-0601 可信度策略配置

- 优先级：P1
- 主责：ChatGPT + Codex
- 输出：来源、直接性、独立性、完整性、时间、方法、反证和质量向量

### TEIF-0602 概率语言配置

- 优先级：P1
- 主责：ChatGPT
- 输出：数字区间、中文语言、展示规则和禁止混用规则

### TEIF-0603 Analytic Confidence 基线

- 优先级：P1
- 主责：Codex
- 输出：透明规则模型和分项解释
- 验收：总等级不掩盖分项

### TEIF-0604 预测结果库

- 优先级：P1
- 主责：Codex
- 输出：预测、截止时间、结果定义和最终结果，用于校准

### TEIF-0605 校准评估

- 优先级：P2
- 主责：Codex
- 输出：Brier、Log Loss、ECE、可靠性图和分组命中率

### TEIF-0606 校准方法

- 优先级：P2
- 主责：Codex
- 候选：温度缩放、等距回归、分箱、保序方法、conformal prediction
- 验收：使用时间切分，禁止训练集校准假象

### TEIF-0607 Abstention 门禁

- 优先级：P1
- 主责：Codex
- 输出：证据不足、冲突、分布外、质量阻断和方法未验证状态

### TEIF-0608 人类覆盖记录

- 优先级：P2
- 主责：WorkBuddy
- 输出：人类接受、拒绝、修改 AI 判断及原因，供后续评估

---

## 11. TEIF-E07：时序知识图谱

### TEIF-0701 图谱概念模型

- 优先级：P1
- 主责：ChatGPT + Codex
- 输出：Entity、Event、Topic、Claim、Evidence、Dataset、Feature、Model、Decision

### TEIF-0702 关系时间化

- 优先级：P1
- 主责：Codex
- 验收：所有核心关系有 valid/observed/available/version/evidence

### TEIF-0703 实体解析和稳定 ID

- 优先级：P1
- 主责：Codex
- 首批：昆仑万维、Matrix 3.5、世界模型、相关论文、证券和平台

### TEIF-0704 Topic Version

- 优先级：P1
- 主责：ChatGPT + 用户
- 输出：主题定义、词包、子主题、公司映射、有效期和审核状态

### TEIF-0705 图存储 ADR

- 优先级：P2
- 主责：Codex
- 决策：关系数据库图视图、图数据库或 RDF
- 原则：先真实查询需求，后选技术

### TEIF-0706 历史图查询

- 优先级：P2
- 主责：Codex
- 验收：能查询某历史时点的实体与关系状态

### TEIF-0707 主题演化报告

- 优先级：P2
- 主责：ChatGPT
- 输出：概念、实体、产业映射、传播阶段和市场叙事的版本变化

---

## 12. TEIF-E08：因果假设与归因

### TEIF-0801 C0-C5 因果等级契约

- 优先级：P1
- 主责：Codex + ChatGPT

### TEIF-0802 Confounder Registry

- 优先级：P1
- 主责：ChatGPT
- 首批：市场整体、行业行情、公司公告、平台算法、营销、影视事件、同名词和价格反向带动

### TEIF-0803 事件研究基线

- 优先级：P2
- 主责：Codex
- 输出：窗口、基准、行业调整、显著性和多重检验

### TEIF-0804 领先关系研究

- 优先级：P2
- 主责：Codex
- 输出：交叉相关、滚动领先和 Granger 预测关系
- 文案门禁：不得直接称因果

### TEIF-0805 PCMCI+ 实验

- 优先级：P3
- 主责：Codex
- 前置：足够长、频率一致、质量合格的多变量序列
- 验收：与透明基线比较并记录失败案例

### TEIF-0806 反证与负对照

- 优先级：P1
- 主责：ChatGPT + Codex
- 输出：时间反转、随机日期、无关词、无关公司和窗口敏感性

### TEIF-0807 Causal Hypothesis Workspace

- 优先级：P2
- 主责：Codex
- 输出：机制、混杂、替代原因、证据、反证、方法和等级

---

## 13. TEIF-E09：ASE / ASA 集成

### TEIF-0901 RawObservation 适配

- 优先级：P1
- 主责：Codex
- 输出：旧 ASE 数据到 Event Envelope 的映射

### TEIF-0902 Matrix 原始工件

- 优先级：P1
- 主责：WorkBuddy + 用户
- 输出：微信指数截图、查询词、日期窗口、设备时间和人工观察记录

### TEIF-0903 Matrix 时间轴

- 优先级：P1
- 主责：Codex
- 输出：指标、相关新闻、官方事件、同名事件和市场事件同轴视图

### TEIF-0904 Matrix 证据图

- 优先级：P1
- 主责：ChatGPT + Codex
- 输出：支持世界模型、电影、数学、机器人、软件和未知解释的证据

### TEIF-0905 Matrix 归因报告 v1

- 优先级：P1
- 主责：ChatGPT
- 验收：允许结论仍为 `INSUFFICIENT_EVIDENCE`

### TEIF-0906 ASE 阶段判断升级

- 优先级：P2
- 主责：Codex
- 输出：统一 Assessment、证据、反证和置信度向量

### TEIF-0907 注意力特征谱系

- 优先级：P1
- 主责：Codex
- 验收：任意分数可回到平台观察和词包版本

---

## 14. TEIF-E10：第二大脑与交易研究出口

### TEIF-1001 第二大脑只读 API

- 优先级：P2
- 主责：Codex
- 输出：时间轴、Claim、Evidence、Topic 和 Assessment 查询

### TEIF-1002 Annotation 独立域

- 优先级：P2
- 主责：Codex
- 验收：用户笔记不能覆盖事实

### TEIF-1003 研究特征快照

- 优先级：P2
- 主责：Codex
- 输出：冻结 DatasetVersion、FeatureVersion、knowledge cutoff 和 lineage

### TEIF-1004 策略研究白名单

- 优先级：P2
- 主责：用户 + ChatGPT + Codex
- 输出：批准状态、适用范围、已知限制和撤回机制

### TEIF-1005 真实交易隔离测试

- 优先级：P0
- 主责：Codex
- 验收：TEIF 和第二大脑无券商凭证、无下单权限、无订单状态修改能力

---

## 15. TEIF-E11：生产治理

### TEIF-1101 结构化日志与运行 ID

- 优先级：P1
- 主责：WorkBuddy + Codex

### TEIF-1102 数据新鲜度和缺失告警

- 优先级：P1
- 主责：WorkBuddy

### TEIF-1103 备份与恢复演练

- 优先级：P2
- 主责：WorkBuddy
- 验收：事件账本、工件索引和配置可恢复

### TEIF-1104 权限最小化

- 优先级：P1
- 主责：用户 + WorkBuddy

### TEIF-1105 成本观测

- 优先级：P2
- 主责：WorkBuddy
- 输出：存储、采集、模型、查询和第三方数据成本

### TEIF-1106 持续验收

- 优先级：P1
- 主责：ChatGPT
- 输出：月度架构、来源、质量、校准和风险审查

---

## 16. 推荐第一个 Sprint

### 目标

不引入复杂基础设施，先建立可验证的“时间 + 证据 + 概率”最小闭环，并让 Matrix 案例跑通。

### 范围

1. TEIF-0001 至 TEIF-0005
2. TEIF-0101、0102、0103、0104、0106、0107
3. TEIF-0301、0303、0306
4. TEIF-0401、0402、0405
5. TEIF-0902、0903、0905

### 完成定义

- Event 和 Assessment 契约有正反例测试。
- Matrix 截图被登记为有哈希和权限的工件。
- 指数观察包含 observed、ingested、available 时间。
- 至少一个 Claim 同时有支持证据和替代解释。
- 结论概率与分析置信度分开。
- 能按历史时点查询当时已知数据。
- 证据不足时稳定输出 abstention。
- 没有真实交易动作。

---

## 17. 第二个 Sprint 候选

- PostgreSQL 事件账本和物化视图
- OpenLineage 兼容运行事件
- ASE RawObservation 适配
- 第一版 Source Registry
- 第一版全局时间轴 API
- 世界模型周报升级为统一 Assessment

---

## 18. 任务模板

```markdown
## Task ID
TEIF-XXXX

## 目的

## 前置条件

## 输入契约

## 时间语义

## 来源与证据

## 权限和合规

## 实现

## 测试

## 工件与谱系

## 已知限制

## 回滚方式

## NO_TRADE
本任务不进入真实订单关键路径。
```

---

## 19. 当前状态

| 项目 | 状态 |
|---|---|
| 基础层蓝图 | 已完成 Proposed v0.1 |
| 集成映射 | 已完成 Proposed v0.1 |
| 实施 Backlog | 已完成 Draft v0.1 |
| Event 契约 | 本 PR 提供种子 |
| Assessment 契约 | 本 PR 提供种子 |
| 真实系统盘点 | 未开始 |
| 事件账本 | 未开始 |
| 全局时间轴 | 未开始 |
| 证据工件库 | 未开始 |
| 谱系 | 未开始 |
| 校准 | 未开始 |
| 时序知识图谱 | 未开始 |
| 因果工作台 | 未开始 |
| ASE / ASA 集成 | 未开始 |
| 第二大脑接入 | 未开始 |
| 真实交易接入 | 禁止 |
