# AI系统并行Program Control Tower蓝图 v1.0

> `control_tower_id: AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-0001`
>
> `issue: #310`
>
> `status: ACTIVE_CANDIDATE_GOVERNANCE`
>
> `owner: USER`
>
> `architecture_owner: GPT`
>
> `boundary: GOVERNANCE_AND_OBSERVABILITY / NO_TRADE`

## 0. 为什么现在需要这一层

当前系统已经拥有很强的**任务级控制**：per-agent ACTIVE route、task lease、route epoch、Issue/PR、AMED、WPDCR、完成新鲜度和资源预算。但程序级视图已出现真实漂移：旧的多Agent聚合表、PROGRAM-INDEX与历史执行序列可以落后于最新Agent route。

因此缺的不是第二套接任务系统，而是一个**跨Program Lane的Control Tower读模型**：

```text
用户战略方向 / Program Lane Desired State
                    ↓
最新per-agent ACTIVE routes + Issues/PRs + 项目canonical
                    ↓
          Observed State Scanner
                    ↓
             Reconciler
                    ↓
Fresh / Stale / Overlap / Blocked / WIP / Risk / Next Gate
                    ↓
Markdown公告板 + GitHub Project投影 + 后续Harness Runtime
```

总控台不拥有市场事实、知识、概率、风险、资本配置、AI电影剧情/资产或Agent执行任务的事实权威。

## 1. 两种“三条线”必须分开

### 1.1 Program Lanes

用户当前明确的三条长期并行线：

1. Harness Integration：DeepSeek Harness研究已完成第一轮，PoC未启动；
2. A-share Remediation：交易研究系统缺陷改进准备启动；
3. Second Brain × GPT Cognitive Closed Loop：当前正在实施。

它们是**长期战略工作流**，可以跨越很多Issue、PR、Agent与暂停期。

### 1.2 AMED Execution Chains

现有AMED规定每一个非trivial任务内部同时做：

- 主任务交付；
- 现场侦察；
- 系统演进。

这是**单任务内部的三条链**，不是Program Lanes。两个概念今后不得混名。

## 2. 设计原则

### 2.1 Single Source of Truth

GitHub Projects官方最佳实践强调单一事实源。总控台因此采用“canonical + projection”而非“多个手工状态表”。

- Agent执行真源：最新 `ACTIVE-*.yaml`；
- Program Lane关系：`ACTIVE-PROGRAM-LANES.yaml`；
- 领域事实：各W2-W13与项目canonical；
- Issue/PR：任务讨论、实现和审查；
- GitHub Project：人类可视化投影；
- DeepSeek Harness Session：未来运行轨迹，不是长期事实权威；
- W3/CLTM：知识、证据和长期记忆权威。

### 2.2 Desired vs Observed

借鉴Kubernetes Controller模式：

- Desired State：三条线应处于什么状态、谁负责、依赖是什么、可否执行；
- Observed State：远端main上最新route、Issue、PR、CI和canonical实际是什么；
- Reconciliation：比较两者并报告漂移。

控制器式设计的关键不是“永远没有变化”，而是变化后能发现并收敛。

### 2.3 Lease / Fencing

现有 `route_epoch` 与 task lease 应视为程序级防陈旧令牌。长期任务在开始时拥有权限，不代表提交时仍有权限。

未来持久写入前至少检查：

`task_id + route_epoch + issue + PR/branch + execution_allowed + authority witness + dependency state`

如果其中任何关键绑定已失效，必须重新规划或拒绝提交。

### 2.4 DAG而不是平铺清单

Airflow等成熟编排系统把依赖关系作为一等对象。Program Lane之间也应显式表示：

- upstream gate；
- downstream consumer；
- shared interface；
- blocking relationship；
- resource pool；
- completion/review gate。

“大家互相知道对方在做什么”不能代替机器可读DAG。

## 3. 当前三线路地图

| Lane | 当前状态 | 主要系统面 | 最大重叠风险 | 下一Gate |
|---|---|---|---|---|
| Harness Integration | RESEARCHED / NOT_IMPLEMENTED | W1/W8/W9，辅助W3/W7/W10/W12 | 与认知闭环共享Context/Skill/Agent Runtime | 隔离PoC，等待相关接口冻结或走adapter |
| A-share Remediation | PREPARING / NOT_STARTED | W2/W4/W5/W7/W9/W12/W13 | 与Harness共享Guard/Observability；与认知线共享W3/W10/W12 | 形成缺陷总账与首个有界修复切片 |
| Cognitive Closed Loop | ACTIVE | W3/W10，辅助W8/W9/W12 | 正在修改ContextBundle语义，暂不适合被Harness直接耦合 | 完成P2.2 remediation并GPT验收 |

当前最重要的并行策略不是“三个都同时写代码”，而是**正交并行**：

```text
Lane C：重实施 / Codex current route
Lane A：研究、PoC合同与隔离设计
Lane B：缺陷归并、证据研究、首切片设计
```

等Lane C相关共享接口冻结后，再决定A/B中哪一个获得下一条重执行route。

## 4. Overlap Taxonomy

### O0 NONE

无实质共享。正常并行。

### O1 READ/READ

只读取同一source。允许并行，但必须检查freshness。

### O2 SHARED CONTRACT

共享稳定接口或一个消费另一个。接口冻结、单写权威成立时可并行。

### O3 MUTABLE SURFACE

共享正在变化的接口、文件、Schema、branch或本机重资源。必须：

`sequence / isolate / adapter / explicit lock`

四选一或组合。

### O4 AUTHORITY COLLISION

两条线都声称同一canonical写权威，或两个desired state互斥。Fail closed，进入GPT/用户架构决策。

## 5. Control Tower对象

### 5.1 ProgramLaneSpec

最小字段：

- lane_id
- mission
- owner
- architecture_owner
- execution_owner/candidate
- desired_state
- system_positions
- dependencies
- shared_interfaces
- next_gate
- maturity
- stop_conditions

### 5.2 ProgramLaneObservation

- observed_at
- remote_main_head
- current task route
- route_epoch
- issue / PR / branch
- execution_allowed
- CI/evidence state
- observed phase
- active blockers
- resource lease

### 5.3 DriftFinding

- finding_id
- class
- severity
- desired evidence
- observed evidence
- affected lanes
- affected authorities/interfaces
- allowed automatic action
- owner decision if needed
- closure condition

### 5.4 ProgramGate

- gate_id
- upstream evidence
- pass/fail/unknown
- blocking scope
- unlocks
- owner
- recheck trigger

## 6. GitHub人类界面

GitHub Projects适合成为“公告栏UI”，因为官方支持Table、Board、Roadmap、自定义字段、自动化、charts/insights、Issue dependencies和sub-issues。

建议一个Project，多视图，不建三套Project：

### Executive Overview

只显示：Lane、Status、Owner、Agent、Current Phase、Next Gate、Risk、Age。

### Active Now

显示当前实际可执行任务，并从ACTIVE routes同步。

### By Program Lane

按三条Program Lane分组。

### By Agent

按Codex/QCLAW/WorkBuddy/GPT分组，用于发现double booking。

### Dependencies & Blocked

展示blocked-by、blocking、blocked age。

### Risk & Gates

展示O2/O3/O4 overlap、风险等级与人门。

### Roadmap

仅显示真实Start/Target/Iteration，不为了漂亮图表伪造日期。

### Recently Completed

用于吞吐与Cycle Time统计。

### Learning / Candidate Queue

AMED系统演进提案、Harness候选、新Skill、UNKNOWN，不自动变成active work。

注意：GitHub Board的column limit只是视觉提醒，官方明确说明不会阻止人或automation继续添加卡片。因此真实WIP上限必须由validator执行。

## 7. Flow与周期问题

看板最大的失败之一是“任务都在动，但没有东西完成”。Kanban最小流指标给我们一个适合AI工程的监测组：

- WIP：已开始未完成数量；
- Throughput：单位时间真正完成的工作项；
- Work Item Age：未完成任务已经活了多久；
- Cycle Time：从开始到完成多久；
- Blocked Age：本项目增加的实用指标，判断“卡住”是否正在变成僵尸任务；
- SLE：历史足够后再估计例如“85%同类任务在N天内完成”，不能拍脑袋设置。

周期问题还应按工作类型分层：研究、设计、实现、审计、修复的Cycle Time不能混为一个均值。

## 8. 多Agent为什么必须显式状态而不能靠“互相猜”

2025年的LLM-Coordination研究发现，LLM在主要依赖环境变量的协调任务上更可靠，而需要主动推断伙伴信念/意图时更困难。这与本系统的经验高度吻合：Agent不应该猜“Codex可能已经做到哪里”，而应读取机器状态。

NeurIPS 2025的MAST基于1600+条多Agent轨迹，把常见失败归为系统设计、Agent间失配、任务验证三类。对我们最直接的工程含义：

- owner和authority必须显式；
- dependency必须显式；
- termination/acceptance必须显式；
- 当前状态必须来自环境证据；
- 不以“多Agent数量”本身当作质量提升。

ACL 2025 MultiAgentBench比较star/chain/tree/graph等拓扑，在其研究场景中graph表现最佳。这不能直接推广为“图一定最好”，但支持我们用**依赖图**而不是扁平广播作为跨Program Lane的默认表达。

## 9. 与机构量化/模型治理联动

交易线的Control Tower不能只看工程进度，还应看模型生命周期状态。

2026年美国联储更新的Model Risk Management guidance强调：

- 模型开发与使用；
- validation与ongoing monitoring；
- governance and controls；
- model interactions/dependencies会形成aggregate model risk；
- objective effective challenge；
- 现实结果分析和模型退化后的调整/重开发。

CFA Institute对量化研究也强调在把模型结果纳入投资流程前理解参数、假设、限制并验证输出；投资模型验证应贯穿生命周期。

因此交易Lane未来投影字段应逐步增加：

`Model/Skill ID → intended use → maturity → validation state → last OOS/shadow check → dependencies → limitations → degradation/revalidation state`

但这些状态由W4/W7/W9/W12等canonical产生，总控台只引用。

## 10. DeepSeek Harness联动

Harness最适合成为未来Control Tower下方的执行层：

```text
Control Tower Desired/Gates
          ↓
Harness Runtime
Agent / Skill / Tool / Subagent / Session / Approval / Guard
          ↓
Domain Systems
          ↓
Observed Events / Outcome
          ↓
W9 + Control Tower Reconciliation
```

不能倒过来让Harness Session成为Program/Knowledge/Market truth。

第一批未来Harness候选插件：

- `program-lane-context-provider`
- `source-authority-router`
- `cross-lane-write-guard`
- `route-epoch-commit-guard`
- `program-event-observer`

都应先PoC再晋级。

## 11. Durable AI的新风险：Semantic Isolation

2026年新论文提出一个非常贴合当前系统的问题：长任务可能保存了旧状态，但在恢复时碰到已经变化的prompt、model alias、index、policy或tool，形成“语义版本混搭”。论文称其为semantic isolation问题，并提出semantic read skew、compatibility skew、context escape、merge skew等异常。

对我们先作为`candidate`规则：

- 长任务/多日任务记录关键semantic environment版本；
- resume前比较当前环境；
- 不兼容变化进入REVALIDATE/REPLAN，而不是静默继续；
- 特别关注Harness升级、ContextBundle Schema、模型版本、Skill版本、W3 index/policy变化。

## 12. Durable effect的新风险：Commit-Time Authorization

另一个2026候选研究指出，Agent可能在任务开始时拥有有效授权，但到真正产生永久副作用时，这个授权已经失效。

这与现有 `FETCH → EDIT → COMMIT → FETCH VERIFY`、route epoch和completion freshness高度一致。因此总控台正式加入候选检查：

`提交前重新读取当前authority/route/dependency → 验证witness仍有效 → 再提交`

不是只在开工时检查一次。

## 13. 四状态知识映射

本Skill继承认知闭环现有四状态：

### KNOWN_SAID

用户已经明确说过。例如本轮三条线及其大体状态。

### KNOWN_UNSAID_INFERRED

用户没有明确说，但从系统结构可高置信推断。例如“三线并行”需要跨线冲突检测，而不仅是三个任务列表。必须标记Inference。

### UNKNOWN_BUT_ACCESSIBLE

用户没学过术语但一解释就能对应现有经验。例如：

- Control Tower
- Desired/Observed Reconciliation
- WIP
- DAG
- Lease/Fencing
- Materialized View

### UNKNOWN_REQUIRES_SCAFFOLDING

需要先搭概念台阶：

- semantic isolation levels
- commit-time authorization
- distributed leases/fencing semantics
- probabilistic SLE
- model aggregate risk / dependency risk

这些不能只丢术语，要从用户已经熟悉的“任务真源、route epoch、GitHub canonical、并行Agent”往上搭。

## 14. 第一阶段不做什么

- 不创建第二任务分发器；
- 不替换ACTIVE routes；
- 不改当前Issue #305 / PR #307；
- 不自动激活Harness；
- 不同时启动三个重任务；
- 不把交易研究接入真实下单；
- 不因Project看板字段变化自动提升canonical maturity；
- 不把旧聚合表删掉，先明确标记历史/STALE后再由后续迁移任务处理。

## 15. Eval

### Targeted cases

1. 最新Codex route与旧聚合表冲突，必须选择最新route并报STALE_VIEW；
2. 同一Agent被两个Lane要求执行，必须报DOUBLE_BOOKED；
3. 三个Lane存在但只有一个重任务，必须允许，不误报WIP；
4. 两个Lane只读W3，必须O1，不应过度阻断；
5. Harness准备修改正在变化的ContextBundle接口，必须O3；
6. 两个Lane都要成为ProbabilityEstimate writer，必须O4 fail closed；
7. 交易Lane不得借Harness绕过W7/NO_TRADE；
8. route epoch在commit前变化，持久写必须停止重验；
9. 长任务恢复时模型/Skill/Policy版本变化，必须显式semantic skew；
10. Project UI字段与route不一致时，UI不得成为执行真源。

### Success metrics

- stale-view detection recall/precision；
- authority collision false negative = 0 in regression set；
- unnecessary block rate；
- duplicate work incidents；
- stale-route commits；
- user correction count；
- WIP / Work Item Age / Blocked Age；
- program-level cycle time；
- regression pass rate。

## 16. 成熟度

当前：`CANDIDATE_GOVERNANCE`。

至少经历一次真实三Lane协调周期，并产生真实冲突/无冲突样本、targeted regression、错误报警复盘后，才允许升级。

## 17. 外部证据等级

### Stable / 官方或成熟来源

- GitHub Projects官方文档：single source of truth、views、roadmap、dependencies、automation、insights；
- The Kanban Guide：WIP、Throughput、Work Item Age、Cycle Time、SLE；
- Kubernetes官方：Controller desired/current reconciliation、Lease coordination；
- Apache Airflow官方：DAG、task dependencies、pools/concurrency；
- Temporal官方：durable execution、history/replay；
- Federal Reserve 2026 Model Risk Management guidance；
- CFA Institute investment/quantitative model validation材料；
- ACL 2025 MultiAgentBench；
- NAACL 2025 LLM-Coordination；
- NeurIPS 2025 MAST。

### Candidate / 新近预印本

- `BEGIN AI TRANSACTION: Semantic Isolation for Durable AI Workflows`, arXiv:2608.05412；
- `Temporary Authority, Permanent Effects: Commit-Time Authorization for LLM Agents`, arXiv:2607.10487。

新预印本只作为设计候选与测试假设，不直接晋升企业永久标准。
