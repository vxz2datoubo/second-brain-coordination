# CODEX TASK PACKET — FOUNDATION-DATA-GOVERNANCE-0001 v2

## 元数据

- task_id: FOUNDATION-DATA-GOVERNANCE-0001
- owner: Codex
- reviewer: ChatGPT via User
- runtime_executor: WorkBuddy
- priority: P0
- risk_level: low
- mode: architecture + isolated implementation
- live_trading: forbidden
- predecessor: CODEX-TASK-ARCH-MARKET-DATA-0001（停止使用，以本任务为准）

---

## 一、任务目标

建设A股量化母系统的第一块正式地基：

> **统一对象模型 + 数据分层边界 + 市场数据适配 + 能力协商 + 数据质量治理**

这不是单一接口任务，而是后续回测、集合竞价、逐笔成交、逐笔委托、消息面、风控和自动交易共同依赖的母系统契约。

必须优先对接当前真实仓库结构：

- `brain_core`
- `bulletin`
- `data`
- 现有交易和技能目录

不得未经批准直接把现有治理链迁移到新的 `memory/` 目录。

---

## 二、建设顺序

后续总顺序确定为：

1. 统一对象模型、数据分层、Adapter、能力协商和质量治理；
2. A股专属规则引擎、微观结构与时段语义；
3. Replay + Validation闭环和策略生命周期；
4. 在以上地基上接入更多策略。

本任务只完成第1项，同时为第2、3项预留稳定接口。

---

## 三、必须先做的仓库审计

在修改前：

1. 检查Git状态、分支、未提交文件和其他AI产出；
2. 阅读现有 `brain_core` 对象、数据契约和存储代码；
3. 检查 `bulletin` 的治理和状态文件；
4. 检查 `data` 的实际目录和写入规则；
5. 识别可复用对象，禁止平行复制一套同名系统；
6. 输出“复用、扩展、废弃候选”清单。

建议使用独立branch或worktree：

```text
codex/FOUNDATION-DATA-GOVERNANCE-0001
```

不得直接覆盖其他Agent未提交的工作。

---

## 四、统一母系统对象模型

Codex需根据现有代码决定复用或新增，至少覆盖以下概念：

### 证据与来源

- `SourceRecord`
- `EvidenceItem`
- `DataLineageRecord`
- `DataQualityRecord`

### 市场数据

- `MarketDataRecord`
- `TradeEvent`
- `OrderEvent`
- `BookSnapshot`
- `AuctionSnapshot`
- `PriceBar`
- `SecurityStatusEvent`
- `CorporateActionEvent`

### 研究和特征

- `FeatureSet`
- `FeatureDefinition`
- `DatasetSnapshot`
- `ResearchHypothesis`
- `ExperimentRecord`

### 验证和决策

- `BacktestResult`
- `ValidationReport`
- `DecisionRecord`
- `ForecastRecord`
- `ModelRecord`
- `StrategyLifecycleRecord`

### 交易和复盘

- `OrderIntent`
- `ExecutionRecord`
- `PositionLot`
- `TradeJournal`
- `RiskEvent`
- `SelfEvolutionLog`

要求：

1. 不强制为每个概念都创建独立类，允许合理聚合；
2. 必须有清晰关系图和版本策略；
3. 区分事实、派生统计、模型推断和人工解释；
4. 所有关键对象具备：
   - object_id
   - schema_version
   - created_at
   - effective_at
   - available_at
   - source_id
   - lineage
   - quality_flags
5. 不把供应商字段名直接暴露给上层策略。

---

## 五、数据分层和文件/数据库边界

必须明确并文档化：

```text
raw
normalized
features
signals
reports
runtime_logs
```

每层至少说明：

- 保存什么；
- 不保存什么；
- 推荐目录或数据库；
- 主要写入者；
- 主要读取者；
- 是否不可变；
- 保留周期；
- 是否允许重算；
- 是否进入Git；
- 是否可能包含敏感信息。

基础原则：

### raw

- 供应商原始响应或事件；
- 追加写、不可覆盖；
- 不进入Git；
- 可以重建normalized。

### normalized

- 统一对象模型；
- 必须保留raw lineage；
- 供应商无关；
- 可由raw重新生成。

### features

- 必须记录feature_time与available_time；
- 可重算；
- 保存feature_version和输入数据快照。

### signals

- 保存模型、版本、概率、置信区间、适用状态和证据；
- `+1/0/-1`只作展示。

### reports

- 人可读输出；
- 不能作为唯一事实源。

### runtime_logs

- 运行、错误、延迟、恢复和审计；
- 与研究数据分离。

请优先映射到当前 `brain_core + bulletin + data`，不要先造新的平行目录树。

---

## 六、市场数据Adapter体系

必须设计：

- `MarketDataAdapter`
- `CapabilityDescriptor`
- `AdapterHealthStatus`
- `SourceReliabilityProfile`

### 本任务实现或适配

- `TdxMcpSnapshotAdapter`
- `HistoricalTradeReplayAdapter`
- `MockMboAdapter`
- `MockAuctionAdapter`

### 只建立接口和映射模板

- `TdxQuantAdapter`
- `WeStockAdapter`
- `TushareAdapter`

不得虚构TdxQuant字段。

---

## 七、能力协商正式契约

每个数据源声明：

- realtime_snapshot
- depth_levels
- trade_by_trade
- market_by_order
- order_id
- cancel_event
- modify_event
- sequence_no
- channel_no
- auction_snapshot
- auction_order_event
- historical_replay
- point_in_time
- local_persistence
- source_latency_metadata
- correction_stream
- recovery_support

每项能力至少包含：

```text
status: available / partial / unavailable / unverified
field_coverage
time_coverage
history_start
latency_profile
quality_grade
license_scope
fallback
```

上层模块必须根据能力自动降级：

- 无MBO，不计算真实撤单率；
- 无原始成交方向，标记`inferred`；
- 无竞价序列，只分析9:25最终结果；
- 数据质量不足时，输出`no_signal`或阻断。

---

## 八、质量标记和可靠性

至少支持：

- missing_sequence
- duplicate
- out_of_order
- timestamp_regression
- clock_drift
- unknown_unit
- cumulative_semantics_unknown
- field_semantics_unverified
- source_disagreement
- stale_data
- partial_recovery
- session_mismatch
- corporate_action_mismatch
- point_in_time_violation
- inferred_not_original

严重问题支持：

```text
blocking = true
```

不得静默继续产生可交易信号。

---

## 九、三时间戳和可见性

所有市场与事件数据尽可能支持：

- `exchange_timestamp`
- `vendor_timestamp`
- `receive_timestamp`
- `effective_at`
- `available_at`
- `sequence_no`

必须区分：

- 事实属于哪个时间；
- 市场何时可以看到；
- 系统何时收到；
- 回测何时允许使用。

---

## 十、验证生命周期骨架

本任务不制定未经验证的固定阈值，但必须建立生命周期对象和状态机：

```text
candidate
→ research
→ validated
→ simulation
→ shadow
→ limited_live
→ production
```

以及：

```text
keep
downgrade
freeze
retire
```

要求：

- 状态变化必须产生`DecisionRecord`；
- 保存原因、证据、批准者和回滚点；
- 定量阈值由后续Validation任务配置；
- 本任务禁止把“30笔、12个月、5%退化”等写成全局铁律。

---

## 十一、永久记忆权威边界

必须形成一份短文档，明确：

- `QUANT-SYSTEM-MASTER-MEMORY.md`是总索引和外部记忆；
- 它不是运行配置；
- 它不能覆盖正式Schema、代码、市场规则或已批准配置；
- 当前活跃治理仍在 `brain_core + bulletin + data`；
- 未来通过“Memory Patch”桥接，不直接迁移；
- 冲突时：
  1. 用户当前明确指令；
  2. 正式AGENTS/子目录规则；
  3. 已批准Schema与配置；
  4. 代码和测试；
  5. 永久记忆总纲作为导航和冲突提示。

建议输出：

```text
docs/governance/MEMORY-AUTHORITY-BOUNDARY.md
```

若仓库已有同类文件，应扩展而非重复创建。

---

## 十二、A股规则预留

本任务不实现完整规则引擎，但对象模型必须表达：

- exchange
- board
- security_type
- risk_warning_type
- listing_stage
- special_status
- effective_date
- upper_limit_price
- lower_limit_price
- suspension_status
- sellable_quantity
- available_cash_for_trading
- withdrawable_cash

当前ST知识基线按用户确认的最新上下10%处理，但正式运行仍以当日正规行情源和版本化规则为准。

---

## 十三、测试要求

至少包括：

1. 对象Schema版本测试；
2. 事实/派生/推断类型隔离测试；
3. Adapter能力声明测试；
4. 不支持能力自动降级测试；
5. 原始方向与推断方向不可混淆；
6. 去重、乱序、序列缺口测试；
7. 三时间戳与available_at测试；
8. raw到normalized血缘测试；
9. 历史回放确定性测试；
10. point-in-time违规阻断测试；
11. 候选配置不可被运行时加载测试；
12. 永久记忆不得覆盖正式配置测试；
13. source disagreement阻断或降级测试；
14. 旧对象兼容或迁移测试。

---

## 十四、输出要求

至少交付：

1. 仓库现状与复用审计；
2. 对象模型关系图；
3. 数据分层与路径边界；
4. Schema和核心接口；
5. Adapter框架与Mock；
6. 能力协商Schema；
7. 数据质量模块；
8. 生命周期状态机骨架；
9. 永久记忆权威边界文档；
10. 测试；
11. WorkBuddy真实字段接入指南；
12. 迁移方案；
13. 回滚方案；
14. 后续两个任务建议：
    - A股规则与微观结构；
    - Replay + Validation。

---

## 十五、需要WorkBuddy后续提供

Codex完成后，列出精确的数据包需求，至少包括：

- TDX MCP真实函数和原始字段；
- TdxQuant真实函数、权限和样本；
- 历史逐笔文件Schema与样本；
- WeStock/Tushare字段和Point-in-Time说明；
- 当前数据目录结构；
- 延迟、缺失、乱序和重连报告；
- 证券主数据和历史规则来源。

---

## 十六、禁止

- 不连接真实交易；
- 不访问密钥；
- 不下单；
- 不激活候选策略参数；
- 不覆盖生产数据；
- 不迁移整个memory目录；
- 不虚构vendor字段；
- 不重构无关模块；
- 不删除旧对象或文件；
- 不把未经验证阈值写成硬规则。

---

## 十七、完成报告

返回：

- task_id
- branch_or_worktree
- changed_files
- reused_existing_components
- new_components
- architecture_decisions
- commands_run
- tests_run
- test_results
- unresolved_conflicts
- required_workbuddy_packages
- migration_plan
- rollback_plan
- next_two_tasks
- confirmation_no_live_trading_changes
