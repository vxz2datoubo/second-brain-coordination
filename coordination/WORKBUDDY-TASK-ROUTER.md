# WorkBuddy任务路由协议

## 永久短命令语义

用户对WorkBuddy说`读取任务`、`执行任务`、`开始任务`或同义短句时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

统一含义：读取远端最新WorkBuddy任务真源，核对并领取有效租约，然后立即开始实质现场执行。不得只复述任务、只写计划、等待用户第二次说开始，或跳到Issue #7的CodexDispatch。

例外：当活动索引为`PAUSED`、非READY或`execution_allowed: false`时，必须硬停止，不得因主动性规则自动恢复。此时提交精确状态报告，而不是执行。

## GPT→WorkBuddy工程工厂协议

所有非trivial WorkBuddy工程任务还必须读取：

`coordination/GOVERNANCE/GPT-WORKBUDDY-ENGINEERING-FACTORY-PROTOCOL-v1.0.yaml`

硬规则：

1. 每个任务必须显式给出`model_profile`、`primary_model_id`、`reasoning_model_id`、`lite_model_id`、模型选择理由、fallback policy和execution carrier；缺任一项不得执行。
2. 治理任务禁止未声明的Auto模型选择。允许的标准profile为`DEEPSEEK_V4_PRO`、`DEEPSEEK_V4_FLASH`、`HYBRID_PRO_WITH_FLASH_LITE`。
3. V4 Pro用于架构敏感核心实现、复杂debug、多模块/长回合施工、迁移与高正确性风险任务；V4 Flash用于低架构风险且机械边界清晰的批量测试、fixture、boilerplate、schema/data转换、lint/type/docs、简单adapter和重复验证；Hybrid由Pro负责核心/推理，Flash负责lite/background工作。
4. WorkBuddy不得因为实现方便而静默改变GPT发布的架构、合同、acceptance oracle或single-writer边界。发现架构问题必须STOP或RFC回GPT。
5. 完成/阻塞return package必须回报实际使用的model profile和精确model id，不得只写“WorkBuddy”。
6. GitHub上的任务发布不等于本地CLI进程执行权。CLI只能由用户手工启动，或由另行安装且fail-closed的本地canonical-task watcher / 受治理runner启动。
7. 本地桥不得从候选PR启动；必须fresh读取canonical main上的READY + execution_allowed任务，并核对route/claim/lease/snapshot/batch/model/base/branch/single-writer身份后才允许launch。
8. GitHub任务文件不得包含API Key、token、cookie或本地认证材料。

CLI与模型选择参考：

`coordination/GUIDES/WORKBUDDY-CLI-BRIDGE-AND-MODEL-SELECTION-v1.0.md`

标准dispatch模板：

`coordination/TEMPLATES/WORKBUDDY-ENGINEERING-DISPATCH-v1.yaml`

## 本地问题预防门

跨Agent本地执行问题登记表：

`coordination/ENGINEERING-LEARNING/LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`

WorkBuddy是本地环境事实验证者，因此除匹配当前任务的已知问题模式外，还应优先调查反复出现问题是否来自终端编码、系统locale/code page、路径、shell、Python/Node运行时、Git配置或网络环境等可永久修复的现场共因。安全且授权范围内能永久修复时，实施并回归验证；涉及全局系统配置、权限、网络或可能影响其他程序时，只给证据和最小变更提案，不擅自改动。

## 执行顺序

1. 固定仓库为`vxz2datoubo/second-brain-coordination`。
2. 明确身份为WorkBuddy执行者；Issue #7只用于Codex调度基础设施，永远不是WorkBuddy收件箱。
3. 安全同步或远程读取最新`main`，不得覆盖本地未提交内容。
4. 读取本协议、GPT→WorkBuddy工程工厂协议、RTCE、租约/新鲜度、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性、`LOCAL-EXECUTION-ISSUE-PATTERNS.yaml`和`coordination/ACTIVE-WORKBUDDY-TASK.yaml`。
5. 读取活动Issue、全部评论、影响预测、任务简报、允许路径、权限、安全边界以及模型分配字段。
6. 根据实际OS、终端、shell、语言/runtime、格式/parser、编码、Unicode/path和网络传输面匹配适用问题模式，并声明`PERMANENT_FIX`、`CONTAIN_AND_MEASURE`或`NOT_APPLICABLE_WITH_REASON`。
7. 精确回显仓库、远端main head、task_id、route_epoch、Issue、PR、branch、status、completion_signal、base、model_profile、primary_model_id、reasoning_model_id、lite_model_id和execution carrier，提交租约声明。
8. 只有字段一致、READY、execution_allowed为true、model assignment完整且依赖满足时才执行。
9. 租约有效后立即开始第一个有意义的现场动作并给出证据；长任务在实质检查点回报。
10. 主动发现本地能力、接口、权限、许可、路径、服务、数据质量、性能、部署、可观测性和云端设计与本地现实偏差。
11. 授权现场路径内的A/B改良应实施并测试；C只提案；D/用户门停止升级。
12. 重复本地问题必须区分根因、workaround与永久修复；若只能规避，记录触发条件和验证，不能把重复重试当修复。
13. 检查点、阻塞、交接和完成必须按WPDCR报告过程、难度、失败、发现、扩展、未解问题、精确协同和系统反馈。
14. 完成后提交累计AMED/WPDCR、命令/测试、UNKNOWN、AI_HANDOFF、结果校准、实际模型profile/model ids，以及适用的本地问题模式证据与永久修复/containment结果，不自行合并或改变服务权威。

## 不可执行状态

PAUSED、execution_allowed false、依赖缺失、模型分配缺失、路径/权限不明或路由陈旧时：

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
