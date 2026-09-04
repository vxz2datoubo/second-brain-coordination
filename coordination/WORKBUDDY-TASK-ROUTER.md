# WorkBuddy任务路由协议

## 永久短命令语义

用户对WorkBuddy说`读取任务`、`执行任务`、`开始任务`或同义短句时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

统一含义：读取远端最新WorkBuddy多槽任务真源，核对可执行slot并领取与本执行实例匹配的有效租约，然后立即开始实质现场执行。不得只复述任务、只写计划、等待用户第二次说开始，或跳到Issue #7的CodexDispatch。

R579后，WorkBuddy canonical任务真源为：

`coordination/ACTIVE-WORKBUDDY-TASKS.yaml`

`coordination/ACTIVE-WORKBUDDY-TASK.yaml`仅保留为迁移期**primary-slot兼容投影**。它不得覆盖、删除、暂停或释放复数registry中的其他slot，也不得单独创造新的执行权限。两者身份不一致时必须fail closed。

例外：目标slot为`PAUSED`、非READY、`execution_allowed: false`、租约无效、claim/reservation不一致或碰撞检查失败时，必须硬停止该slot，不得因主动性规则自动恢复。其他互不冲突的合法slot可以继续。

## 多槽并行语义

WorkBuddy可以同时存在多个有界执行slot，但“同一个agent名字”不等于“共享一个可写表面”。每个slot必须拥有独立：

- `worker_slot_id`
- task / route epoch / Issue / branch
- Work Claim
- Task Lease
- Executor Reservation
- Authorization / prewrite evidence
- write/read paths
- interface/domain authority
- local resource/service/runtime claims
- completion signal

并行只在`coordination/CONTROL-TOWER/workbuddy_slots.py`验证通过时成立。

必须fail closed的碰撞至少包括：

1. 可写路径相交；
2. 一方写、另一方读同一可变文件表面；
3. 同一mutable interface；
4. authority claim相交；
5. exclusive local resource相交；
6. mutable runtime/service/config与另一slot共享；
7. credential surface相交；
8. real-data surface未显式声明可安全共享；
9. route/claim/lease/reservation identity drift；
10. active slot数量超过registry上限。

纯read/read、冻结合同共享或明确的只读资源共享可以并行，不得因为WorkBuddy已有另一个任务就机械全局阻塞。

### 多实例领取规则

- 已经有ACTIVE Claim/Lease的slot继续由原执行实例持有，其他实例不得重复领取同一task/slot。
- 新WorkBuddy实例读取任务时，只能领取尚未被其他实例有效持有、且registry/collision/capacity全部通过的slot。
- 若用户命令明确给出task/slot，必须只尝试该目标。
- 若用户只说通用`读取任务`，按canonical registry中可领取slot的稳定顺序选择第一个合法slot；已被有效持有的slot跳过，不得抢占。
- 一个slot阻塞不得自动暂停其他O0/O1安全slot。

## 本地问题预防门

跨Agent本地执行问题登记表：

`coordination/ENGINEERING-LEARNING/LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`

WorkBuddy是本地环境事实验证者，因此除匹配当前任务的已知问题模式外，还应优先调查反复出现问题是否来自终端编码、系统locale/code page、路径、shell、Python/Node运行时、Git配置或网络环境等可永久修复的现场共因。安全且授权范围内能永久修复时，实施并回归验证；涉及全局系统配置、权限、网络或可能影响其他程序时，只给证据和最小变更提案，不擅自改动。

## 执行顺序

1. 固定仓库为`vxz2datoubo/second-brain-coordination`。
2. 明确身份为WorkBuddy执行者；Issue #7只用于Codex调度基础设施，永远不是WorkBuddy收件箱。
3. 安全同步或远程读取最新`main`，不得覆盖本地未提交内容。
4. 读取本协议、RTCE、租约/新鲜度、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性、`LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`、`coordination/ACTIVE-WORKBUDDY-TASKS.yaml`和兼容投影`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
5. 对registry执行WorkBuddy slot结构、capacity、compatibility projection和pairwise collision验证；任何UNKNOWN按fail closed处理。
6. 选择一个未被其他有效执行实例持有且合法的目标slot；读取其活动Issue、全部评论、影响预测、任务简报、允许路径、权限与安全边界。
7. 根据实际OS、终端、shell、语言/runtime、格式/parser、编码、Unicode/path和网络传输面匹配适用问题模式，并声明`PERMANENT_FIX`、`CONTAIN_AND_MEASURE`或`NOT_APPLICABLE_WITH_REASON`。
8. 精确回显仓库、远端main head、worker_slot_id、task_id、route_epoch、Issue、PR、branch、status、completion_signal和base，提交slot级租约声明。
9. 只有registry、slot、claim、lease、reservation字段一致，READY、execution_allowed为true且依赖满足时才执行。
10. 租约有效后立即开始第一个有意义的现场动作并给出证据；长任务在实质检查点回报。
11. 主动发现本地能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实偏差。
12. 授权现场路径内的A/B改良应实施并测试；C只提案；D/用户门停止升级。
13. 重复本地问题必须区分根因、workaround与永久修复；若只能规避，记录触发条件和验证，不能把重复重试当修复。
14. 检查点、阻塞、交接和完成必须按WPDCR报告过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
15. 完成后仅释放自身slot的claim/lease/reservation并提交累计AMED/WPDCR、命令/测试、UNKNOWN、AI_HANDOFF、结果校准；不得释放、覆盖或修改其他WorkBuddy slot，不自行合并或改变服务权威。

## 不可执行状态

目标slot为PAUSED、execution_allowed false、依赖缺失、路径/权限不明、路由陈旧、registry不一致或collision未知/高风险时：

- 禁止自动恢复、猜任务、执行Codex/QCLAW任务或进入Issue #7；
- 报告精确失败字段；
- 列出检查和尝试；
- 写明最小缺失能力/权限/决定；
- 区分受影响slot与可继续slot；
- 指定请求Owner、精确动作和恢复条件；
- 只写`BLOCKED`无效。

## 安全与所有权

主动发现和RTCE不授予跨模块接管、服务生命周期变更、凭证导出、真实数据准入、账户、订单、交易或自动恢复权限。多槽能力只扩展**调度并发**，不扩展任何业务权限。不得修改其他Agent/其他slot分支，不得自行合并、直接写main、强推或改写历史。

固定仓库：`vxz2datoubo/second-brain-coordination`

canonical WorkBuddy任务真源：远端最新`main`上的`coordination/ACTIVE-WORKBUDDY-TASKS.yaml`。

迁移期兼容投影：`coordination/ACTIVE-WORKBUDDY-TASK.yaml`，仅代表registry指定的primary slot。
