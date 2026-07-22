# 企业级自适应任务执行与双环演进协议 v1.0

> protocol_id: `ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-0001`
>
> short_name: `AMED`
>
> authority_scope: `enterprise_program_default_execution_governance`
>
> applies_to: `GPT / CODEX / WORKBUDDY / QCLAW / future agents`
>
> boundary: `research_only / NO_TRADE unless separately authorized`
>
> status: `ACTIVE_ENTERPRISE_STANDARD`

## 1. 根本目标

每个AI任务不能只是逐字完成清单，也不能以“主动改良”为名无限扩张。AMED要求执行者同时运行三条链：

```text
主任务交付链
→ 完成明确目标、成功标准与验证

现场侦察链
→ 发现错误假设、缺失需求、重复建设、接口缺口、过时规则、负面影响与新机会

系统演进链
→ 将可复用发现形成证据化提案，经GPT二次审核后反哺蓝图、合同、Skill、测试、路由和长期工程经验
```

核心原则：

> 有纪律的主动性。围绕任务意图自主改进方法，但不得绕过权威边界、WIP、风险门、许可、隐私或GPT验收。

## 2. 双环学习

### 第一环：任务内改进

回答：

- 怎样更可靠地完成本次任务？
- 哪个实现、数据、测试或接口更合适？
- 哪些错误可以在当前范围内修正？

### 第二环：系统级演进

回答：

- 为什么原系统没有提前发现这个问题？
- 哪条任务模板、蓝图、接口、测试、权威边界或决策链需要永久改变？
- 该发现能否泛化到其他工作流？
- 哪些旧能力应降级、废弃或重新验证？

单次成功只形成观察或假设，不能自动升级为企业标准。系统级回写必须经过GPT二次审核、证据复核和必要的独立验证。

## 3. 所有任务必须包含的六层意图

### 3.1 Mission Intent

任务必须说明：

- 根本目标；
- 用户最终要获得的能力；
- 当前状态为什么不足；
- 因果机制；
- 真正成功标准；
- 失败和停止条件。

### 3.2 System Position

必须标明：

- 所属工作流和有界上下文；
- 上游、下游；
- 系统记录源；
- 只读依赖；
- 不得复制的canonical运行时；
- 对其他任务、分支和接口的影响。

### 3.3 Hard Boundaries

至少覆盖：

- 权限、安全、隐私和许可；
- 文件和分支所有权；
- WIP和活动路由；
- 实盘、凭证、账户和订单边界；
- 不可访问证据必须标记UNKNOWN；
- 不得将推断写成事实；
- 不得自行改变模式、任务或优先级。

### 3.4 Active Discovery Duty

所有非trivial任务必须主动检查：

- 原任务是否有错误或过时假设；
- 是否缺少必要需求、数据、测试、接口或规则；
- 是否存在重复Skill、Schema、存储或运行时；
- 是否可以复用、适配、迁移或废弃现有能力；
- 是否存在更简单、更可靠或更低成本的方案；
- 是否有跨模块联动机会；
- 是否产生隐藏成本、风险、技术债或维护负担；
- 是否有负面或反直觉结果需要保留。

### 3.5 Improvement Authority

每项计划外改良必须分类：

#### A级 `SAFE_LOCAL_AUTONOMOUS`

可直接实施，必须满足全部条件：

- 仅限当前分支和当前模块；
- 不改变外部合同和权威关系；
- 不扩大数据权限或依赖；
- 不影响其他活动任务；
- 有测试且易回滚。

典型事项：补测试、错误处理、字段校验、局部重构、可观测性、文档与代码一致性。

#### B级 `BOUNDED_IMPLEMENT_AND_REPORT`

可实现但必须单独报告：

- 向后兼容的内部对象或字段；
- 局部性能、维护性或验证增强；
- 不改变外部权威的适配层优化。

必须说明原因、证据、影响、测试和回滚。

#### C级 `PROPOSAL_ONLY`

只允许形成RFC、ADR、Schema提案或新任务候选，禁止自行实现：

- 新跨模块接口；
- 新独立Skill；
- 新canonical对象、存储或运行时；
- 新数据源、付费许可或大规模历史数据；
- 改变其他模块权威；
- 明显扩大任务规模。

#### D级 `PROHIBITED_OR_USER_GATE`

必须停止并升级：

- 真实资金、账户、凭证、订单和实盘；
- 自动合并或直接写main；
- 高风险风控、资本、组合和执行变更；
- 删除或替代权威系统；
- 绕过许可、验证码、付费墙或隐私边界；
- 不可逆或系统级高严重度变化。

### 3.6 Exploration Budget

主动探索不得吞没主交付。默认预算：

```yaml
primary_delivery_share: "70-80%"
active_discovery_share: "10-20%"
system_opportunity_share: "5-10%"
max_new_architecture_proposals: 3
max_new_skill_candidates: 2
max_unplanned_files: 5
scope_expansion_without_gate: false
```

任务发布者可按轻量、标准、战略档位裁剪，但不能删除主动发现和证据回执。

## 4. 三级研究触发器

### L1 `REUSE_AND_QUICK_CHECK`

所有任务默认执行：

- 查仓库、蓝图、Issue、PR、Skill、规则和工程经验；
- 检查重复、过时引用和明显更优方案；
- 不要求重新开展全面互联网研究。

### L2 `TARGETED_PROFESSIONAL_RESEARCH`

出现以下任一条件时触发：

- 新专业领域或现有蓝图缺口；
- 来源、模块或测试结论冲突；
- 规则、政策、数据、软件可能变化；
- 重要资金、风险、架构或A股适配决策；
- 方法缺少一手依据；
- 理论与回测明显相反；
- 跨模块接口冲突；
- 执行者对方案可靠性没有足够把握。

研究必须优先一手官方来源、原始论文、标准、大学课程、可复现工程和真实机构案例，并记录适用条件、反证、冲突、可信度和A股适配。

### L3 `INDEPENDENT_RESEARCH_TASK`

以下情况不得在原任务中顺手扩展，应提交新任务候选：

- 改变canonical运行时或系统记录源；
- 建立系统级Schema或跨模块权威迁移；
- 形成新独立Skill；
- 新付费数据、许可证或重大接口；
- 大规模历史数据和正式回测；
- 预计规模明显超过探索预算；
- 需要独立对抗验证或用户决策。

## 5. 研究与证据纪律

AI自我反思不是验证。重大改良必须经过：

```text
执行者提案
→ 仓库与外部一手事实
→ 自动测试、历史数据或可复现实验
→ 反方/独立审计
→ GPT总架构审核
→ 高风险事项由用户决定
```

研究账本必须包含：

- 精确研究问题和触发级别；
- 查询时间和知识截止时间；
- 来源、作者、发布日期和版本；
- 来源类型、权威等级和许可；
- 支持什么、不支持什么；
- 关键假设、适用条件和反例；
- 与其他来源的冲突；
- A股适用性；
- 可信度和UNKNOWN；
- 最终是否影响实现或只作为参考。

禁止用论文标题数量、名气、复杂术语或多数AI意见代替验证。

## 6. 强制交付包

所有标准和战略任务必须交付：

1. `AgentExecutionReceipt`；
2. `ResearchLedger`，未触发L2时也要说明仅执行L1；
3. `UnplannedImprovementLedger`；
4. `SystemDiscoveryAndOpportunityReport`；
5. 真实命令、退出码、测试、数据范围和未运行项；
6. `UNKNOWN-REGISTRY`；
7. `AI_HANDOFF`；
8. 任务影响预测与实际结果对照。

每条关键事实必须标记：

- `VERIFIED_REPOSITORY`；
- `VERIFIED_LOCAL`；
- `VERIFIED_OFFICIAL_SOURCE`；
- `VERIFIED_TEST`；
- `INFERENCE`；
- `INHERITED_REPORT`；
- `ACCESS_NOT_AVAILABLE`；
- `UNKNOWN`。

## 7. GPT二次审核七道门

GPT不得仅凭“报告看起来完整”验收。

1. `TASK_COMPLETENESS_GATE`：主任务和成功标准是否真正完成；
2. `FACT_EVIDENCE_GATE`：关键事实、时间、版本、本地访问和来源能否复核；
3. `RESEARCH_QUALITY_GATE`：一手资料、反证、适用条件、A股差异和过时性；
4. `ENGINEERING_CORRECTNESS_GATE`：测试、Schema、接口、重复运行时和回滚；
5. `IMPROVEMENT_VALUE_GATE`：计划外改良是否净价值为正且权限合规；
6. `SYSTEM_EVOLUTION_GATE`：是否应回写蓝图、模板、Skill、测试、路由或废弃项；
7. `NEXT_ACTION_GATE`：接受、限定整改、独立验证、拆分新任务、架构决策或用户决策。

允许的最终判定：

- `ACCEPTED`；
- `ACCEPTED_WITH_BOUNDED_AMENDMENT`；
- `REMEDIATION_REQUIRED`；
- `INDEPENDENT_VALIDATION_REQUIRED`；
- `SPLIT_INTO_NEW_TASK`；
- `ARCHITECTURE_DECISION_REQUIRED`；
- `USER_DECISION_REQUIRED`；
- `REJECTED`。

## 8. 系统反哺

经GPT接受的可复用发现必须分类回写：

- 企业总章程和专项蓝图；
- 机器可读合同与Skill Registry；
- TaskImpactForecast和任务模板；
- Agent路由、AGENTS和禁止清单；
- 自动测试、回归测试和影子门；
- Engineering Learning Registry；
- 退役、冲突和UNKNOWN登记；
- 新任务队列。

建议处置枚举：

- `ACCEPT_IN_CURRENT_TASK`；
- `PROPOSE_FOLLOW_UP`；
- `PROPOSE_ARCHITECTURE_DECISION`；
- `PROPOSE_NEW_SKILL`；
- `PROPOSE_DEPRECATION`；
- `NEEDS_INDEPENDENT_RESEARCH`；
- `NEEDS_USER_DECISION`；
- `REJECTED_AFTER_RESEARCH`；
- `UNKNOWN`。

## 9. 三档任务重量

### 轻量 `LIGHT`

适用于文档小修、局部Bug和字段校正。保留目标、边界、测试、主动发现和简短回执。默认L1研究。

### 标准 `STANDARD`

适用于适配器、Schema、报告和中等功能。要求定向研究触发判断、方案比较、影响分析、完整回执和GPT七门审核。

### 战略 `STRATEGIC`

适用于新工作流、量化Skill、风险、资金、政策消息和系统级架构。要求项目计划模式、全仓库/可访问本地实况审计、TaskImpactForecast、研究矩阵、独立反方验证、多时期回测、影子运行和用户高风险门。

## 10. 反失控硬规则

1. 主任务优先，主动研究不能成为未完成主交付的理由；
2. 发现不等于实现，C级默认只提案；
3. 所有新能力先查重：`REUSE / ADAPT / MIGRATE / REFERENCE_ONLY / DEPRECATE / NEW_CANDIDATE`；
4. 改良必须说明净价值、复杂度、维护和验证成本；
5. 失败、无增量和复杂模型不如简单基线必须保留；
6. 执行AI不能批准自己的重大扩展；
7. 建议必须有Owner、验证门、关闭条件和状态；
8. 任何系统级变化必须可回滚或明确不可逆风险；
9. AMED不授予实盘、账户、凭证或自动合并权限；
10. 所有能力成熟度必须以证据升级，不以自报升级。

## 11. 成功标准

- 每个非trivial任务都有任务意图、系统位置、研究触发、探索预算和改良权限；
- 执行者能主动发现真实问题，而不是机械1:1完成；
- 主动性没有造成WIP膨胀、重复运行时或权威混乱；
- GPT可从回执中独立复核研究、实现和系统级建议；
- 可复用经验进入蓝图、模板、测试和后续任务；
- 负面结果、失败和UNKNOWN被保留；
- 系统持续演进但保持可审计、可回滚和NO_TRADE边界。
