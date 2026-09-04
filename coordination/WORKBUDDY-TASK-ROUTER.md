# WorkBuddy任务路由协议

## 永久短命令语义

用户对WorkBuddy说`读取任务`、`执行任务`、`开始任务`或同义短句时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

统一含义：读取远端最新WorkBuddy多槽任务真源，核对可执行slot并领取与本执行实例**明确匹配**的有效租约，然后立即开始实质现场执行。不得只复述任务、只写计划、等待用户第二次说开始，或跳到Issue #7的CodexDispatch。

R579后，WorkBuddy canonical任务真源为：

`coordination/ACTIVE-WORKBUDDY-TASKS.yaml`

`coordination/ACTIVE-WORKBUDDY-TASK.yaml`仅保留为迁移期**primary-slot兼容投影**。它不得覆盖、删除、暂停或释放复数registry中的其他slot，也不得单独创造新的执行权限。两者身份不一致时必须fail closed。

例外：目标slot为`PAUSED`、非READY、`execution_allowed: false`、租约无效、claim/reservation不一致、slot选择不唯一或碰撞检查失败时，必须硬停止该slot，不得因主动性规则自动恢复。其他互不冲突且已被独立明确绑定的合法slot可以继续。

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
9. route/claim/lease/reservation/snapshot/batch identity或active-state drift；
10. non-primary授权文档缺少`worker_slot_id`或完整`slot_collision_surface`绑定；
11. registry声明的write surface小于实际Route/Claim/Lease/Reservation授权面；
12. active slot数量超过registry上限。

纯read/read、冻结合同共享或明确的只读资源共享可以并行，不得因为WorkBuddy已有另一个任务就机械全局阻塞。

## 多实例领取与slot选择规则

### 选择权威

多槽环境下，WorkBuddy**不得凭registry顺序猜测自己属于哪个slot**。slot选择按以下优先级机械解析：

1. 当前受治理的启动/交接包已经显式绑定`worker_slot_id`时，只能选择该slot；
2. 用户命令显式给出task或`worker_slot_id`时，只能尝试该目标；
3. 若且仅若当前canonical registry中恰好存在一个通过全部结构/授权/碰撞检查的可执行slot，裸`读取任务`可以自动选择它；
4. 若存在两个或更多可执行slot而当前执行上下文没有唯一slot绑定，必须返回`AMBIGUOUS_WORKBUDDY_SLOT_SELECTION`并停止该实例，不得“按第一个”“按最新”“按Issue最小/最大”等猜测。

这不是要求用户发第二次“开始”命令。正常并行发布时，协调者应在每个WorkBuddy任务启动包中预先绑定对应`worker_slot_id`，因此该实例收到一次`读取任务`即可继续执行。

### 不能伪造运行时独占

- `claim_state: ACTIVE`或`lease_state: ACTIVE`本身只证明治理授权处于活动状态，**不能单独证明某一个WorkBuddy窗口/进程已经取得运行时独占**；
- 在仓库尚无executor-instance级原子锁/唯一claim-id协议前，不得从“ACTIVE Claim/Lease”推断具体本地实例身份；
- 两个执行实例不得同时针对同一`worker_slot_id`工作；如果启动上下文、远端in-progress evidence或本地现场证据显示同slot已有另一真实执行实例，后到实例必须fail closed并报告`DUPLICATE_WORKBUDDY_SLOT_EXECUTOR`；
- 不得通过另建第二套Lease/Claim真源来解决该问题；若未来需要机器级原子claim，应扩展现有Task Lease/RTCE协议并独立验收。

### slot级完成规则

- 一个slot完成/阻塞只允许更新或释放自身绑定证据；
- 不得因为一个slot完成而清空整个`ACTIVE-WORKBUDDY-TASKS.yaml`；
- primary兼容投影只跟随registry指定的primary slot，不代表其他slot的生命周期；
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
6. 按“多实例领取与slot选择规则”解析本执行实例唯一目标slot；无法唯一解析时停止该实例并报告精确歧义，不得猜测。
7. 读取目标slot的活动Issue、全部评论、影响预测、任务简报、允许路径、权限与安全边界。
8. 根据实际OS、终端、shell、语言/runtime、格式/parser、编码、Unicode/path和网络传输面匹配适用问题模式，并声明`PERMANENT_FIX`、`CONTAIN_AND_MEASURE`或`NOT_APPLICABLE_WITH_REASON`。
9. 精确回显仓库、远端main head、worker_slot_id、task_id、route_epoch、Issue、PR、branch、status、completion_signal和base，提交slot级租约声明。
10. 只有registry、slot、claim、lease、reservation、snapshot、batch字段一致，READY、execution_allowed为true且依赖满足时才执行。
11. 租约有效后立即开始第一个有意义的现场动作并给出证据；长任务在实质检查点回报。
12. 主动发现本地能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实偏差。
13. 授权现场路径内的A/B改良应实施并测试；C只提案；D/用户门停止升级。
14. 重复本地问题必须区分根因、workaround与永久修复；若只能规避，记录触发条件和验证，不能把重复重试当修复。
15. 检查点、阻塞、交接和完成必须按WPDCR报告过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
16. 完成后仅释放自身slot的claim/lease/reservation并提交累计AMED/WPDCR、命令/测试、UNKNOWN、AI_HANDOFF、结果校准；不得释放、覆盖或修改其他WorkBuddy slot，不自行合并或改变服务权威。

## 不可执行状态

目标slot为PAUSED、execution_allowed false、依赖缺失、路径/权限不明、路由陈旧、registry不一致、slot选择歧义或collision未知/高风险时：

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