# AI-SYSTEM-PARALLEL-PROGRAM-CONTROL-TOWER-0001 Research Ledger

> `issue: #310`
>
> `captured_at: 2026-08-14`
>
> `status: CANDIDATE_EVIDENCE_LEDGER`
>
> 目的：保存总控台架构的外部研究依据、可迁移模式、适用边界和候选假设。外部资料不得覆盖本项目内部canonical事实。

## Evidence grading

- **T1 Official / Standard / Regulator**：官方产品文档、开源项目官方文档、监管指引；
- **T2 Peer-reviewed / top conference**：ACL/NAACL/NeurIPS等；
- **T3 Professional practitioner**：CFA、Kanban Guide等专业实践；
- **T4 Recent preprint / candidate**：新预印本，仅生成候选规则和Eval。

## T1 · GitHub Projects

### GitHub Projects best practices

Source: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/best-practices-for-projects

Key evidence:
- Projects支持table/board/roadmap、多视图、自定义字段、automation、charts/insights；
- sub-issues和issue dependencies支持层级与blocking关系；
- 官方明确建议保持single source of truth。

Transfer:
- GitHub Project适合作为总控台人类投影；
- 不应把Project字段变成第二任务权威。

### GitHub Board column limits

Source: https://docs.github.com/en/issues/planning-and-tracking-with-projects/customizing-views-in-your-project/customizing-the-board-layout

Key evidence:
- column limit只显示超限，不阻止用户或automation继续添加卡片。

Transfer:
- WIP必须由机器validator/route governance硬执行；Project只能报警。

### GitHub auto-add/workflows

Source: https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/adding-items-automatically

Transfer:
- 后续可把符合lane/label/issue条件的Issue/PR自动投影到Project；
- auto-add只负责projection，不负责claim/lease。

## T3 · Kanban / Flow

Source: https://kanbanguides.org/the-kanban-guide/2020.7/

Key evidence:
- minimum flow metrics: WIP, Throughput, Work Item Age, Cycle Time；
- SLE应基于历史cycle-time或早期best guess，并可视化；
- WIP超限应少见且显式。

Transfer:
- 总控台不能只显示状态灯，还要长期统计WIP、WorkItemAge、BlockedAge、Throughput、CycleTime；
- 研究/设计/实现/审计/修复按work class分开统计；
- 有足够历史后再引入SLE。

## T1 · Kubernetes Controller / Lease

### Controllers

Source: https://kubernetes.io/docs/concepts/architecture/controller/

Key evidence:
- controller持续比较desired state与current state并执行/请求收敛动作；
- 多个简单controller优于一个所有状态都揉在一起的单体循环。

Transfer:
- ProgramLaneSpec = desired；
- ACTIVE routes/Issues/PR/CI = observed；
- Reconciler = drift detector；
- 高影响drift不自动覆盖，进入GPT/User gate。

### Leases

Source: https://kubernetes.io/docs/concepts/architecture/leases/

Key evidence:
- Lease用于共享资源协调、heartbeat和leader election；
- coordinated leader election使用holder identity、renew time、duration等状态。

Transfer:
- 现有route_epoch/task lease应继续作为fencing evidence；
- 新总控不重复造lease，只消费它并做freshness校验。

## T1 · Apache Airflow

Source: https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/overview.html

Key evidence:
- DAG负责task dependencies和执行顺序，不需要理解task内部业务；
- Pools/concurrency用于限制共享资源并行度。

Transfer:
- Program Control Tower只管理依赖、Gate、WIP、资源与ownership；
- 不复制W2-W13或AI电影内部业务逻辑；
- dependency graph是一级对象。

## T1 · Temporal durable execution

Source: https://temporal.io/

Key evidence:
- durable workflow保存进度并在故障后恢复；
- workflow/event history支持replay；
- failure-prone external interactions被隔离为Activities。

Transfer:
- 未来Harness/长任务要保留可追溯运行历史；
- 业务副作用与控制状态分离；
- replay/恢复不能默默混入新的不兼容环境。

## T1/T3 · Institutional model governance / quantitative research

### Federal Reserve revised Model Risk Management guidance, SR 26-2

Sources:
- https://www.federalreserve.gov/supervisionreg/srletters/SR2602.htm
- https://www.federalreserve.gov/frrs/guidance/supervisory-guidance-on-model-risk-management.htm

Key evidence:
- model development/use、validation/monitoring、governance/controls是完整生命周期；
- 模型之间共享假设、数据、方法会产生aggregate model risk；
- 强调independent/effective challenge、limitations、outcomes analysis、ongoing monitoring；
- 模型退化时需要调整、重校准或重开发。

Boundary:
- 2026 guidance明确generative/agentic AI不在其正式适用范围内；这里只迁移模型治理原则，不声称监管直接要求本系统。

Transfer to A-share lane:
- 总控台未来引用model/skill inventory、intended use、validation state、dependencies、limitations、OOS/shadow recency、revalidation state；
- 真正validation仍属于W7/W9/W12等canonical。

### CFA Institute quantitative diligence / model validation

Sources:
- https://www.cfainstitute.org/standards/professionals/code-ethics-standards/standards-of-practice-v-a
- https://rpc.cfainstitute.org/research/foundation/2024/investment-model-validation
- https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/backtesting-and-simulation

Key evidence:
- quantitative model使用者需要理解参数、假设、限制并合理测试；
- validation应在模型进入投资分析流程前开展并持续评估；
- backtesting需要与scenario/simulation/sensitivity等互补。

Transfer:
- “代码完成”与“交易研究能力成熟”必须是两种状态；
- Control Tower显示实现进度时同时显示validation/maturity reference。

## T1 · MLflow model registry analogy

Source: https://mlflow.org/docs/latest/ml/model-registry/

Key evidence:
- lifecycle registry保留version、lineage、metadata、alias以及从开发到部署的可追溯关系。

Transfer:
- 交易模型/Skill/AI系统模块可借鉴inventory/lineage思路；
- 不直接引入MLflow作为新的canonical，先复用现有W3/W4/W7/W9 registry。

## T2 · Multi-Agent coordination research

### MultiAgentBench, ACL 2025

Source: https://aclanthology.org/2025.acl-long.421/

Key evidence:
- benchmark比较star/chain/tree/graph等coordination protocols；
- 在论文的research scenario中graph表现最好；cognitive planning提高milestone achievement约3%。

Boundary:
- 不能外推成“graph永远最好”。

Transfer:
- 跨Lane关系默认用显式dependency graph，而不是全员广播或靠记忆互猜。

### LLM-Coordination, NAACL Findings 2025

Source: https://aclanthology.org/2025.findings-naacl.448/

Key evidence:
- LLM agents在主要依赖environment variables的协调场景表现更好；
- 需要主动考虑partner beliefs/intentions时挑战更大。

Transfer:
- Agent必须读取机器可见state，不要靠“猜其他Agent做到哪了”。

### Why Do Multi-Agent LLM Systems Fail?, NeurIPS 2025

Source: https://proceedings.neurips.cc/paper_files/paper/2025/hash/b1041e52d3be19f0a9bc491657488e4a-Abstract-Datasets_and_Benchmarks_Track.html

Key evidence:
- MAST-Data含1600+ annotated traces、7类MAS framework；
- 14 failure modes聚为system design、inter-agent misalignment、task verification三类。

Transfer:
- Control Tower把owner/authority/dependency/termination/verification作为显式字段；
- 多Agent数量本身不构成质量证明。

## T4 · Recent candidate research

### Semantic Isolation for Durable AI Workflows

Source: https://arxiv.org/abs/2608.05412

Candidate claims:
- durable AI workflow可能把保存的旧状态与更新后的prompt/model/index/policy/tool混合；
- 提出semantic read skew、compatibility skew、context escape、merge skew。

Transfer candidate:
- 长任务记录semantic environment版本；
- resume时检查兼容；
- 不兼容时REVALIDATE/REPLAN。

Maturity: `CANDIDATE / NEEDS_PROJECT_EVAL`

### Commit-Time Authorization for LLM Agents

Source: https://arxiv.org/abs/2607.10487

Candidate claim:
- 任务早期有效的authority witness不一定能授权后续durable effect；
- 提出在commit boundary重新验证freshness/binding/eligibility。

Transfer candidate:
- 强化现有FETCH→EDIT→COMMIT→FETCH VERIFY和route_epoch检查；
- commit前重新读取current route/authority/dependencies。

Maturity: `CANDIDATE / NEEDS_PROJECT_EVAL`

## Research synthesis

当前最适合本系统的组合不是复制某一个框架，而是：

```text
GitHub single-source/project views
+ Kanban flow observability
+ Kubernetes desired/observed reconciliation + lease semantics
+ Airflow dependency/resource orchestration
+ Temporal durable-history discipline
+ institutional model lifecycle governance
+ multi-agent failure/coordination evidence
+ 2026 semantic-isolation/commit-authorization candidate guards
```

这些共同支持一个结论：**建立Program Control Tower作为独立协调架构层，但坚持它是projection/reconciliation plane，而不是新的业务或任务authority。**
