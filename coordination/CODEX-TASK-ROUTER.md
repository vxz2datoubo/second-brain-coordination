# Codex任务路由协议

当用户在Codex中说“读取任务”“执行任务”“开始任务”或含义相近的短句时，Codex必须按以下顺序行动：

1. 固定目标仓库为 `vxz2datoubo/second-brain-coordination`，不得从聊天记录猜测其他仓库。
2. **先同步远端最新 `main`**：优先执行安全的 `git fetch origin main`，并从最新 `origin/main` 读取路由和活动索引。若本地工作区不适合快进或存在未提交改动，不得覆盖本地内容，应直接读取GitHub远端最新文件。
3. 禁止使用未验证的新旧本地缓存副本作为任务来源；必须确认读取到的 `coordination/ACTIVE-CODEX-TASK.yaml` 来自当前远端最新 `main`。
4. 打开最新：
   - `coordination/CODEX-TASK-ROUTER.md`；
   - `coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml`；
   - `coordination/GOVERNANCE/AGENT-IN-PROGRESS-REMOTE-VISIBILITY-AND-ROUTE-BRIDGE-PROTOCOL-v1.0.yaml`；
   - `coordination/GOVERNANCE/DUAL-LAYER-INITIATIVE-AND-GPT-ORCHESTRATION-CONSTITUTION-v1.0.yaml`；
   - `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`；
   - `coordination/AUTHORIZATION/CREDENTIAL-SECRETS-LOCAL-ONLY-v1.0.yaml`；
   - `coordination/GOVERNANCE/LOCAL-CREDENTIAL-DIRECT-USE-AND-NON-EXPORT-PROTOCOL-v1.0.yaml`；
   - `coordination/ACTIVE-CODEX-TASK.yaml`。
5. 读取其中的 `active_issue`、`mode`、`status`、`execution_allowed`、`route_epoch`、`route_issued_at`、`completion_signal`、`blocked_by`、`dependencies`、`task_impact_forecast`、`amed_policy`、`task_weight`、`research_trigger`、`exploration_budget`、`autonomy_grant`、顺序门和可见性要求。
6. 执行前必须提交任务租约声明，逐字回显仓库、远端main head、task_id、route_epoch、Issue、PR、分支、状态、completion_signal和reviewed/base head。只有与最新活动索引完全一致，且 `status: READY`、`execution_allowed: true`、依赖满足、任务影响预测存在、AMED字段完整时，才可继续。
7. 读取对应GitHub Issue正文与全部评论，以及AMED、PDER、双层主观能动性、本地凭据、进行中可见性协议、当前任务影响预测与任务简报。
8. 读取任务影响预测中的第一性原理目标、预期收益、预期负面影响、风险门禁、停止条件和执行观测要求。不得为了完成任务而忽略预测中的反证或风险信号。
9. 按Issue中明确标注的Codex模式执行，不得自行更换模式。
10. 执行必须同时覆盖：主任务交付、主动发现错误假设/缺口/重复/接口/风险/负面结果/机会，以及系统演进提案。
11. Codex不得采用被动工单模式。每个非轻量任务都必须主动扫描相邻模块、接口、测试、失败路径、复用机会和高价值后续目标，并在授权范围内完成高价值AMED A/B改良，而不是只在回执里建议。
12. Codex默认采用增强自主档：当活动任务授权时，可自主选择内部架构、模块布局、确定性算法、测试框架和实现顺序，可在路径与PR预算内创建受控分支/Draft PR，可在内部阶段门通过后继续推进，无需每个小步骤等待GPT。
13. 增强自主权不等于权威升级。Codex不得改变canonical、系统记录源、跨Agent所有权、许可证、隐私、真实数据准入、生产状态、账户、订单路由或交易权限。
14. 计划外改良必须按AMED分类：A可直接实施；B可实施但单独报告；C只提案；D停止并升级。不得突破探索预算。
15. 相邻工作只有同时满足以下条件才可直接完成：位于授权路径/分支；不改变外部合同或权威；能测试和回滚；不抢占其他Agent所有权；直接提升正确性、安全性、可复现性、集成性、可维护性或高杠杆未来能力。
16. 研究必须按L1/L2/L3触发执行。L2记录一手来源、反证、适用条件、来源冲突、可信度和A股适配；L3拆分新任务，不得静默扩张。
17. 若Issue存在旧的TIMEOUT、INVALID、UNKNOWN、较低route_epoch完成信号或已被supersedes替代的回执，只把它们当历史记录，不得当作本次任务完成证据。
18. 执行前确认仓库名、最新远端索引、Issue编号、任务租约、影响预测、AMED合同、PDER协议、双层主观能动性宪法、本地凭据协议、进行中可见性协议和当前活动任务完全一致。
19. 执行期间不得把主动发现推迟到最终交付：`S4_CRITICAL`立即停止并保全证据；`S3_MAJOR`证据足够即提交DiscoveryPacket；`S2_MATERIAL`在当前检查点报告；`S1_MINOR`按根因去重聚合。
20. 每个S3/S4发现必须同时提交机器可读证据和人类可读翻译，明确发现、含义、重要性、它不证明什么、是否停工和建议下一步。
21. Codex可以在授权范围内主动做只读核查、反证、验证、架构调整和高价值相邻修复，但不得自行切换顶层任务、接管其他Agent、建立平行canonical或突破硬边界。
22. 发现可能影响其他模块时，必须先报告受影响范围、证据、接口方案与推荐分流。若活动任务明确授权跨模块兼容层，可实现隔离适配，不得直接改写对方权威内容。
23. 执行期间在AMED回执和Agent执行反馈v2中报告实际正面效果、负面效果、意外事件、研究发现、计划外改良和风险信号；高严重度意外损害必须立即停止或上报。

## 进行中成果远端可见性

24. 当出现下列任一情况，必须发布`InProgressVisibilityPacket`，不能等最终完成：
   - 形成了超出远端PR head的实质本地提交或恢复点；
   - 到达活动任务配置的检查点；
   - 一个主要缺陷已有可运行修复或测试里程碑；
   - 状态被报告为`PARTIAL`、`CHECKPOINT`或`RECOVERY_POINT`；
   - 准备长时间暂停、交接、切换Gate、请求审查或发布完成；
   - 发现远端main已经切换到更高route_epoch，但本地仍有工作。
25. 对PUBLIC_SAFE且不含秘密、私人数据、许可受限内容、真实行情或本地敏感路径的checkpoint，Codex应推送一个专用的快进式checkpoint分支，并在活动PR和Issue发布完整可见性包。建议分支：`codex/checkpoint/<task_id>/<gate>`。
26. 每个活动Gate最多一个checkpoint分支。该分支不计入最终实现PR数量，不是tested head、receipt head或canonical，禁止合并；它只用于恢复、远端审查和路线桥接。
27. 若checkpoint含密钥、私人数据、许可受限内容或不能安全上传的本地材料，不得为了可见性而推送。应发布脱敏的`LOCAL_UNVERIFIABLE`包，保留本地提交、patch和日志，并明确哪些内容无法独立审查。
28. `InProgressVisibilityPacket`至少包含：task_id、route_epoch、Gate、远端main head、远端PR head、本地或checkpoint完整SHA、parent、tree、分支、changed paths或脱敏摘要、工作树状态、精确测试命令、退出码、计数、失败/SKIP/UNKNOWN、已完成范围、剩余范围、是否含秘密、远端是否可验证和下一步。
29. 远端PR head未变化不表示没有本地进展。若当前没有实质未推送工作，应发布`IDLE_OR_NO_LOCAL_PROGRESS`包，明确远端PR已经代表当前实现状态。
30. 当远端路由变为更高route_epoch时，不得删除、reset、覆盖、强推或静默放弃本地工作。必须发布`StaleRoutePacket`和可见性包，保存checkpoint或本地备份，再读取新路由的桥接决定。
31. 若新路由保留同一底层目标，可在核对parent、授权路径和新Gate后继续利用本地成果；若发生冲突，保存证据并停止等待GPT决定。

## 完成与回执

32. 任务完成后必须提交 `AMEDAgentExecutionReceipt`、`AMEDResearchLedger`、`UnplannedImprovementLedger`、`SystemDiscoveryAndOpportunityReport`、DiscoveryPacket或`NO_S2_PLUS_DISCOVERY`声明、真实命令/退出码/测试回执、`UNKNOWN-REGISTRY`和`AI_HANDOFF`。
33. 完成交付必须明确分栏：主任务结果、主动发现、已实施主动改良、高价值新目标、考虑过的替代方案、删除/拒绝的方案、相邻影响、负面结果、UNKNOWN、回滚与下一步建议。
34. Codex不能自行宣布主动扩展已成为accepted或canonical。最终由GPT执行第二遍创造性治理，决定直接接受、整合、改良、删除不和谐部分、退回修订、拆分、延期或拒绝。
35. **发布完成信号前必须再次同步或远程读取最新main。** 重新比较task_id、route_epoch、Issue、PR、分支、completion_signal和execution_allowed。任一不一致时，禁止发布旧完成信号，必须提交`StaleRoutePacket`和`InProgressVisibilityPacket`。
36. 当前完成回执必须包含领取与交付前的远端main head、task_id、route_epoch、完整40位delivered/tested/receipt head、精确命令、退出码、计数、stdout/stderr哈希和保留的失败/SKIP/UNKNOWN。
37. 在活动Issue和父Issue中留下证据，创建独立PR，不得自行合并。
38. 若远端入口文件缺失、任务租约字段缺失、影响预测缺失、AMED字段缺失、PDER协议缺失、双层主观能动性宪法缺失、本地凭据协议缺失、进行中可见性协议缺失、状态不是READY、execution_allowed不是true、依赖未满足、Issue不存在、索引版本冲突或无法确认远端最新状态，停止执行并报告，不得猜测任务。
39. 不得因为用户只说“读取任务”就扫描、选择或执行其他Issue。
40. 不得重新执行 `supersedes` 中记录的旧活动任务。
41. 主动发现与实现权限必须服从当前活动路由中的路径、分支、PR、探索预算和停止条件。

## 工作过程、难度、发现与协同强制回报

42. 任务租约、重要检查点、阻塞、暂停、跨Agent交接、路线变化和完成回执必须使用或完整映射：
   - `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`；
   - `coordination/TEMPLATES/AGENT-WORK-PROCESS-AND-COORDINATION-REPORT-TEMPLATE-v1.0.yaml`。
43. Codex每次必须报告：可观察工作阶段、计划与实际难度D0-D4、最难的架构/实现/测试/接口部分及证据、方案改变、失败尝试和所得经验、新发现或意外发现、可拓展架构/Skill/复用机会、难以解决的问题和UNKNOWN、发现的Bug/技术债/负面结果、需要GPT/QCLAW/WorkBuddy/用户完成的精确协调动作、跨模块影响、交接制品、下一步和验收门。
44. `BLOCKED`报告必须说明已尝试方法、失败证据、真正缺少的最小信息/接口/权限/决策、阻塞范围、仍可继续的工作、请求对象、精确动作和关闭条件；只写`BLOCKED`或“等待GPT”无效。
45. 新机会必须先查`REUSE / ADAPT / MIGRATE / REFERENCE_ONLY / DEPRECATE / NEW_CANDIDATE`，并写价值、成本、复杂度、风险、AMED级别、Owner、前置条件、激活触发和验证门；不得用“以后可以扩展”替代可执行提案。
46. 没有发现、没有难题或无需协调时必须明确写`NONE_OBSERVED`、`NONE`或`NONE_REQUIRED`并列出检查面；空白栏目无效。
47. 未关闭的D2以上难点、S2以上发现、开放协调请求、负面结果和UNKNOWN必须在后续检查点持续携带，直到验证关闭、拒绝或延期并绑定Owner与触发条件。
48. 本规则记录可审计过程、决策依据、失败和证据，不要求也不得输出私有思维链或逐token推理。

## 本地凭据与MCP直接使用规则

49. 当活动任务明确授权连接用户本机的WorkBuddy MCP、通达信/TDX、TQ、WeStock或其他用户自有本地适配器时，本地Codex被明确授权直接搜索、读取和使用本机已有密钥、令牌、会话凭据和认证配置，不需要每次再次向用户确认。
50. `LOCAL_ONLY`表示密钥只能留在用户本机，不表示本地Codex不可读取。Codex不得以“凭据属于秘密”“跨Agent配置”“安全策略不允许读取”为由跳过已授权的本地认证步骤。
51. 本地凭据发现顺序为：已认证会话 → 进程/用户环境变量 → 项目批准的本地配置引用 → WorkBuddy或适配器本地配置 → 已配置的操作系统凭据存储。只有全部尝试后仍不可用，才可报告真实阻塞。
52. Codex可读取WorkBuddy本地MCP配置和凭据以完成互操作，但这不转移WorkBuddy的分支、任务、历史或canonical所有权；除非活动路由另行授权，不得改写WorkBuddy仓库内容。
53. 密钥值只允许存在于本机进程内存、环境注入、stdin或本地认证客户端对象中。优先避免会进入shell历史或进程列表的命令行参数。
54. 密钥值禁止进入Git、GitHub、PR、Issue、评论、回执、AI_HANDOFF、日志、stdout/stderr持久记录、测试夹具、数据集、知识图谱、聊天上下文或无关外部服务。报告只允许写引用ID、来源类别、认证是否成功和不可逆验证摘要。
55. 读取本地凭据只解决认证和连接权限，不自动授权真实数据准入、回放、回测、模型拟合、账户访问、订单路由或交易；这些能力仍必须由独立活动路由显式放行。
56. 若发现密钥可能被打印、提交或外泄，立即停止相关输出，执行脱敏并保留不含密钥的证据；未推送的Git污染应先清除，已推送则停止并请求用户主导轮换和历史处置。
57. 本地Codex的默认执行目标是最高效率：已有本地凭据和会话可直接复用，不要求用户手工复制密钥，不重复制造认证步骤，不把可自动解决的本地配置问题包装成人工阻塞。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一任务真源：远端最新 `main` 上的 `coordination/ACTIVE-CODEX-TASK.yaml`。

任务租约、完成新鲜度与进行中可见性权威：

- `coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-IN-PROGRESS-REMOTE-VISIBILITY-AND-ROUTE-BRIDGE-PROTOCOL-v1.0.yaml`

工程学习蓝图：

- `coordination/BLUEPRINTS/ENGINEERING-LEARNING-AND-OUTCOME-CALIBRATION-SYSTEM-v1.0.md`

AMED、主动发现、双层主观能动性、工作过程协同回报与本地凭据权威：

- `coordination/BLUEPRINTS/ADAPTIVE-MISSION-EXECUTION-AND-DOUBLE-LOOP-EVOLUTION-PROTOCOL-v1.0.md`
- `coordination/GOVERNANCE/AMED-ENTERPRISE-POLICY-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-PROACTIVE-DISCOVERY-AND-REALTIME-ESCALATION-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/DUAL-LAYER-INITIATIVE-AND-GPT-ORCHESTRATION-CONSTITUTION-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-WORK-PROCESS-DIFFICULTY-DISCOVERY-AND-COORDINATION-REPORTING-PROTOCOL-v1.0.yaml`
- `coordination/AUTHORIZATION/CREDENTIAL-SECRETS-LOCAL-ONLY-v1.0.yaml`
- `coordination/GOVERNANCE/LOCAL-CREDENTIAL-DIRECT-USE-AND-NON-EXPORT-PROTOCOL-v1.0.yaml`
