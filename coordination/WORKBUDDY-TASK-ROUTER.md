# WorkBuddy任务路由协议

## 永久短命令语义

用户对WorkBuddy说`读取任务`、`执行任务`、`开始任务`或同义短句时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

统一含义：读取远端最新WorkBuddy任务真源，核对并领取有效租约，然后立即开始实质现场执行。不得只复述任务、只写计划、等待用户第二次说开始，或跳到Issue #7的CodexDispatch。

例外：当活动索引为`PAUSED`、非READY或`execution_allowed: false`时，必须硬停止，不得因主动性规则自动恢复。此时提交精确状态报告，而不是执行。

## 本地问题预防门

跨Agent本地执行问题登记表：

`coordination/ENGINEERING-LEARNING/LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`

WorkBuddy是本地环境事实验证者，因此除匹配当前任务的已知问题模式外，还应优先调查反复出现问题是否来自终端编码、系统locale/code page、路径、shell、Python/Node运行时、Git配置或网络环境等可永久修复的现场共因。安全且授权范围内能永久修复时，实施并回归验证；涉及全局系统配置、权限、网络或可能影响其他程序时，只给证据和最小变更提案，不擅自改动。

## 执行顺序

1. 固定仓库为`vxz2datoubo/second-brain-coordination`。
2. 明确身份为WorkBuddy执行者；Issue #7只用于Codex调度基础设施，永远不是WorkBuddy收件箱。
3. 安全同步或远程读取最新`main`，不得覆盖本地未提交内容。
4. 读取本协议、RTCE、租约/新鲜度、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性、`LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`和`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
5. 读取活动Issue、全部评论、影响预测、任务简报、允许路径、权限与安全边界。
6. 根据实际OS、终端、shell、语言/runtime、格式/parser、编码、Unicode/path和网络传输面匹配适用问题模式，并声明`PERMANENT_FIX`、`CONTAIN_AND_MEASURE`或`NOT_APPLICABLE_WITH_REASON`。
7. 精确回显仓库、远端main head、task_id、route_epoch、Issue、PR、branch、status、completion_signal和base，提交租约声明。
8. 只有字段一致、READY、execution_allowed为true且依赖满足时才执行。
9. 租约有效后立即开始第一个有意义的现场动作并给出证据；长任务在实质检查点回报。
10. 主动发现本地能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实偏差。
11. 授权现场路径内的A/B改良应实施并测试；C只提案；D/用户门停止升级。
12. 重复本地问题必须区分根因、workaround与永久修复；若只能规避，记录触发条件和验证，不能把重复重试当修复。
13. 检查点、阻塞、交接和完成必须按WPDCR报告过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
14. 完成后提交累计AMED/WPDCR、命令/测试、UNKNOWN、AI_HANDOFF、结果校准，以及适用的本地问题模式证据与永久修复/containment结果，不自行合并或改变服务权威。

## 不可执行状态

PAUSED、execution_allowed false、依赖缺失、路径/权限不明或路由陈旧时：

- 禁止自动恢复、猜任务、执行Codex/QCLAW任务或进入Issue #7；
- 报告精确失败字段；
- 列出检查和尝试；
- 写明最小缺失能力/权限/决定；
- 区分受影响与可继续范围；
- 指定请求Owner、精确动作和恢复条件；
- 只写`BLOCKED`无效。

## 安全与所有权

主动发现和RTCE不授予跨模块接管、服务生命周期变更、凭证导出、真实数据准入、账户、订单、交易或自动恢复权限。不得修改其他Agent分支，不得自行合并、直接写main、强推或改写历史。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新`main`上的`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
