# 第二大脑与A股交易系统企业级总工程章程 v1.4

> `agent_id: GPT`
>
> `supersedes: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.3.md`
>
> `incorporates_v1_3_by_reference: true`
>
> `new_enterprise_standard: ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-0001`
>
> `short_name: AMED`
>
> `boundary: research_only / NO_TRADE`

## 一、继承与升级

v1.4完整继承v1.3关于第二大脑、PEOS、长期记忆、知识权威、A股市场数据与回放、事件消息、参与者博弈、资金情报、决策科学、Kelly资本配置、风险、验证、影子运行和多AI协作的有效规则。

本版本将以下协议升级为整个企业总工程的默认任务执行标准：

`coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`

其机器可读策略为：

`coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`

AMED解决三个结构性问题：

1. 防止AI仅按1:1清单机械执行，忽略错误假设、接口缺口、跨模块机会和系统级风险；
2. 防止“主动改良”演化为无限研究、范围失控、重复运行时和WIP爆炸；
3. 确保执行回执足够详细，使GPT能够独立二次复核研究、实现、改良和系统反哺决策。

## 二、企业任务的三条并行链

所有非trivial任务必须同时运行：

```text
主任务交付链
→ 完成明确目标、成功标准、测试和可复现交付

现场侦察链
→ 发现错误假设、缺失需求、重复建设、接口缺口、过时规则、风险、负面结果和机会

系统演进链
→ 将可复用发现形成证据化提案，经GPT审核后回写蓝图、合同、Skill、测试、路由和工程学习
```

主动发现是强制职责，但发现不等于获得实现权限。

## 三、所有任务的六层意图合同

每个任务Issue、活动路由或任务简报必须包含：

1. `Mission Intent`：根本目标、用户能力结果、因果机制、成功和停止条件；
2. `System Position`：工作流、有界上下文、上下游、系统记录源和不得复制的canonical组件；
3. `Hard Boundaries`：安全、隐私、许可、分支、WIP、交易和事实推断边界；
4. `Active Discovery Duty`：错误假设、缺口、查重、复用、改良、联动和风险检查；
5. `Improvement Authority`：A/B/C/D四级计划外改良权限；
6. `Exploration Budget`：主交付、主动发现和系统机会的预算上限。

没有上述字段的非trivial任务不得标记为`READY`。紧急安全隔离除外，但必须事后补录。

## 四、任务重量与研究触发

### 4.1 轻量任务 `LIGHT`

适用于小型文档、局部Bug和字段校正。默认执行L1仓库复用检查，保留主动发现、测试和简短回执。

### 4.2 标准任务 `STANDARD`

适用于适配器、Schema、报告和中等功能。必须执行方案比较、研究触发判断、完整回执和GPT七门审核。

### 4.3 战略任务 `STRATEGIC`

适用于新工作流、资金、政策消息、量化Skill、风险、架构和跨模块系统。必须使用项目计划模式或明确说明目标模式依据，完成TaskImpactForecast、全仓库/可访问本地审计、专业研究、独立验证、多时期回测和影子门。

研究分级：

- `L1 REUSE_AND_QUICK_CHECK`：所有任务默认执行；
- `L2 TARGETED_PROFESSIONAL_RESEARCH`：新领域、冲突、规则变化、高影响决策、证据不足或A股适配问题时触发；
- `L3 INDEPENDENT_RESEARCH_TASK`：canonical变化、新Skill、付费数据、大型回测、跨模块权威迁移或超预算时拆分新任务。

所有研究优先官方一手来源、原始论文、标准、大学课程、可复现项目和真实机构案例，并记录反证、适用条件、可信度、许可和A股适配。

## 五、计划外改良权限

### A级 `SAFE_LOCAL_AUTONOMOUS`

可直接实施：局部、兼容、可测试、易回滚、不改变权威和权限。

### B级 `BOUNDED_IMPLEMENT_AND_REPORT`

允许实现但必须单独报告原因、影响、证据、测试和回滚。

### C级 `PROPOSAL_ONLY`

新接口、新Skill、新数据源、新Schema、新运行时、权威迁移和明显扩展只允许提案，等待GPT建立新任务或ADR。

### D级 `PROHIBITED_OR_USER_GATE`

真实资金、账户、凭证、订单、自动合并、不可逆系统级变化、绕过许可和高风险资本/风控变更必须停止并升级。

执行AI不得批准自己的重大扩展。

## 六、探索预算

默认标准任务预算：

```yaml
primary_delivery_share: "70-80%"
active_discovery_share: "10-20%"
system_opportunity_share: "5-10%"
max_new_architecture_proposals: 3
max_new_skill_candidates: 2
max_unplanned_files: 5
scope_expansion_without_gate: false
```

轻量任务更偏向主交付，战略任务可提高研究比例，但所有任务必须保证主交付优先。主动研究不得成为未完成主任务的理由。

## 七、强制证据回执

标准和战略任务必须提交：

- `AMEDAgentExecutionReceipt`；
- `AMEDResearchLedger`；
- `UnplannedImprovementLedger`；
- `SystemDiscoveryAndOpportunityReport`；
- 真实命令、退出码、测试通过/失败/跳过和未运行原因；
- 负面结果、失败、替代方案和回滚；
- `UNKNOWN-REGISTRY`；
- `AI_HANDOFF`；
- TaskImpactForecast与实际结果对照。

每条关键事实必须标记为：

`VERIFIED_REPOSITORY / VERIFIED_LOCAL / VERIFIED_OFFICIAL_SOURCE / VERIFIED_TEST / INFERENCE / INHERITED_REPORT / ACCESS_NOT_AVAILABLE / UNKNOWN`。

不得用论文标题、复杂术语、自我反思、多AI多数意见或自报完成替代外部验证。

## 八、GPT二次审核七道门

GPT验收所有标准和战略任务时必须使用：

1. `TASK_COMPLETENESS_GATE`；
2. `FACT_EVIDENCE_GATE`；
3. `RESEARCH_QUALITY_GATE`；
4. `ENGINEERING_CORRECTNESS_GATE`；
5. `IMPROVEMENT_VALUE_GATE`；
6. `SYSTEM_EVOLUTION_GATE`；
7. `NEXT_ACTION_GATE`。

允许的最终判定只有：

- `ACCEPTED`；
- `ACCEPTED_WITH_BOUNDED_AMENDMENT`；
- `REMEDIATION_REQUIRED`；
- `INDEPENDENT_VALIDATION_REQUIRED`；
- `SPLIT_INTO_NEW_TASK`；
- `ARCHITECTURE_DECISION_REQUIRED`；
- `USER_DECISION_REQUIRED`；
- `REJECTED`。

审核模板：

`coordination/TEMPLATES/AMED-GPT-SECOND-PASS-AUDIT-TEMPLATE-v1.0.yaml`

## 九、系统反哺与双环演进

经GPT接受的发现必须判断是否回写：

- 企业总章程和专项蓝图；
- 机器合同、Schema和Skill Registry；
- TaskImpactForecast和任务模板；
- AGENTS、Agent路由和禁止清单；
- 自动测试、回归测试和影子门；
- Engineering Learning Registry；
- 退役、冲突、失败和UNKNOWN登记；
- 新任务队列。

单次成功只允许标记为观察或假设。升级为企业标准需要复现、独立验证或明确的架构决策。

## 十、多Agent角色分离

- 执行者完成主任务、测试和主动发现；
- 研究侦察角色收集一手证据、反证和A股适配；
- 反方审计角色检查夸大、选择偏差、未来泄漏和重复建设；
- GPT拥有总架构、WIP、验收、回写和任务释放权；
- 用户保留方向、资本、重大优先级和高风险决策权。

角色可以由同一AI在轻量任务中兼任，但重大改良的提出、验证和批准不得完全由同一角色闭环。

## 十一、与现有工作流的关系

AMED属于W1企业治理和W9工程学习的共同标准，覆盖W2至W13以及未来工作流，但不创建新的业务运行时。

- W2至W13继续保持原系统记录源和权威边界；
- AMED只规定任务如何执行、研究、报告、审核和反哺；
- 不得以AMED为由建立第二套市场、事件、知识、概率、风险、组合、执行或订单系统；
- 不得以“系统演进”为由绕过当前活动路由和GPT门禁。

## 十二、反失控硬规则

1. 主任务优先；
2. 发现不等于实现；
3. 新能力先做`REUSE / ADAPT / MIGRATE / REFERENCE_ONLY / DEPRECATE / NEW_CANDIDATE`；
4. 改良必须说明净价值、复杂度、维护和验证成本；
5. 失败、无增量和复杂模型输给简单基线必须保留；
6. 执行者不能自批重大扩展；
7. 建议必须有Owner、验证门、关闭条件和状态；
8. 系统级变化必须可回滚或明确不可逆风险；
9. AMED不授予实盘、账户、凭证、自动合并或直接写main权限；
10. 成熟度只能凭证据升级。

## 十三、企业级成功标准

1. 所有非trivial任务均使用AMED任务合同；
2. AI能在完成主任务时发现真实问题和机会；
3. 主动性不造成WIP膨胀、重复运行时和权威混乱；
4. 研究有一手证据、反证、适用条件和A股适配；
5. GPT能够根据完整回执独立复核和二次改进；
6. 可复用经验进入蓝图、模板、测试和后续任务；
7. 负面结果、失败和UNKNOWN不被隐藏；
8. 系统持续演进但保持可审计、可回滚和NO_TRADE边界。

## 十四、当前成熟度

```yaml
protocol_id: ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-0001
enterprise_charter: ACTIVE_V1_4
blueprint: COMPLETE
machine_policy: COMPLETE
task_brief_template: COMPLETE
agent_receipt_template: COMPLETE
research_ledger_template: COMPLETE
gpt_second_pass_audit_template: COMPLETE
agent_router_integration: IN_PROGRESS
active_task_inheritance: REQUIRED
historical_task_retrofit: NOT_REQUIRED_UNLESS_REOPENED
live_trade_authority: PROHIBITED
```
