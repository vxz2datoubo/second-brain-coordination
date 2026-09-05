# WorkBuddy任务路由协议

## 统一多项目执行总线

所有新 WorkBuddy / CodeBuddy CLI / Desktop 会话在读取活动任务前，先读取：

- `coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml`
- `coordination/EXECUTION/PROJECT-REGISTRY.yaml`
- `coordination/WORKBUDDY-UNIFIED-START-HERE.md`
- 当前任务指定的 `coordination/EXECUTION/PROJECT-ADAPTERS/*.yaml`

这套统一总线只定义全局工程端口：任务分级、执行载体、模型 profile、本地 bridge、single-writer/collision、return package、exact-head review 与 productivity telemetry。第二大脑、交易系统、实时互动电影游戏、AI导演分别通过 project adapter 加强自己的 SoR、测试、工具、权限与停止条件，不得再各自创造第二套全局 GPT→WorkBuddy factory。

**活动执行权保持不变：**唯一 WorkBuddy 活动任务真源仍是远端最新 `main` 上的 `coordination/ACTIVE-WORKBUDDY-TASK.yaml`。统一协议、README、Start Here、项目 Adapter 都不能单独 mint execution authority，也不能覆盖当前 R175 或未来合法 route/claim/lease。

执行载体可按 handoff 选择 `WORKBUDDY_CLI_HEADLESS`、`WORKBUDDY_CLI_WEBUI` 或 `WORKBUDDY_DESKTOP_INTERACTIVE`。同一 task branch/collision domain 禁止 CLI 与 Desktop 同时写；切换必须 checkpoint 并释放旧 writer lease。

Governed nontrivial task 必须显式记录 model profile / 当前模型 / 可观察到的积分倍率或免费状态 / fallback，不得静默依赖 Auto。价格与促销是动态事实，fresh 可用性优先于仓库历史快照。

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
4. 读取统一执行总线、项目注册表、当前 project adapter、本协议、RTCE、租约/新鲜度、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性、`LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`和`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
5. 读取活动Issue、全部评论、影响预测、任务简报、允许路径、权限与安全边界。
6. 根据实际OS、终端、shell、语言/runtime、格式/parser、编码、Unicode/path和网络传输面匹配适用问题模式，并声明`PERMANENT_FIX`、`CONTAIN_AND_MEASURE`或`NOT_APPLICABLE_WITH_REASON`。
7. 精确回显仓库、远端main head、project_id、task_id、route_epoch、Issue、PR、branch、status、completion_signal、base、carrier、model profile 与 resolved model，提交租约声明。
8. 只有字段一致、READY、execution_allowed为true且依赖满足时才执行。
9. 租约有效后立即开始第一个有意义的现场动作并给出证据；长任务在实质检查点回报。
10. 主动发现本地能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实偏差。
11. 授权现场路径内的A/B改良应实施并测试；C只提案；D/用户门停止升级。
12. 重复本地问题必须区分根因、workaround与永久修复；若只能规避，记录触发条件和验证，不能把重复重试当修复。
13. 检查点、阻塞、交接和完成必须按WPDCR报告过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
14. 完成后提交累计AMED/WPDCR、命令/测试、UNKNOWN、AI_HANDOFF、结果校准、`WORKBUDDY_RETURN_PACKAGE`、模型/载体/成本遥测，以及适用的本地问题模式证据与永久修复/containment结果，不自行合并或改变服务权威。

## 不可执行状态

PAUSED、execution_allowed false、依赖缺失、路径/权限不明、project adapter缺失、collision domain被占用或路由陈旧时：

- 禁止自动恢复、猜任务、执行Codex/QCLAW任务或进入Issue #7；
- 报告精确失败字段；
- 列出检查和尝试；
- 写明最小缺失能力/权限/决定；
- 区分受影响与可继续范围；
- 指定请求Owner、精确动作和恢复条件；
- 只写`BLOCKED`无效。

## 安全与所有权

主动发现和RTCE不授予跨模块接管、服务生命周期变更、凭证导出、账户、订单、交易或自动恢复权限。交易 adapter 可以单独授予 `READ_MARKET_DATA`，但它不等于 `PLACE_ORDER`。不得修改其他Agent分支，不得自行合并、直接写main、强推或改写历史。

普通 Owner 授权的私人/个人记忆内容允许进入公开 GitHub；密码、API/client secrets、private keys、认证/session/access/refresh tokens、认证 cookies、MFA/recovery credentials 等可复用认证秘密值禁止写入。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一WorkBuddy任务真源：远端最新`main`上的`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
