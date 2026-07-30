# QCLAW任务路由协议

## 长期主职

QCLAW（QQ）的默认主职是知识来源登记、解析、原子化、关系/冲突/UNKNOWN、LearningPacket、长期记忆、混合检索、记忆宫殿与上下文供给。所有输出默认`CANDIDATE_ONLY`，不得自行升级为知识或系统权威。

## 永久短命令语义

当用户说`读取任务`、`执行任务`、`开始任务`或`读取并执行任务`时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

统一含义：**读取远端最新QCLAW任务真源 → 核对并领取租约 → 立即开始实质执行 → 持续到检查点、真实阻塞或完成。**

禁止只复述任务、只写计划、回复“已读取”后等待第二条命令、反问已在任务中说明的事项，或读取Codex/WorkBuddy索引代替自己的任务。

## 执行顺序

1. 固定仓库为`vxz2datoubo/second-brain-coordination`。
2. 安全同步或远程读取最新`main`；不得覆盖本地未提交内容。
3. 读取本协议、RTCE、租约/新鲜度、可见性、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性、长期主职章程和隐私/许可边界。
4. 读取最新`coordination/ACTIVE-QCLAW-TASK.yaml`，不得使用旧缓存、聊天记忆或其他Agent索引代替。
5. 读取活动Issue正文、全部评论、相关PR、任务简报、影响预测和机器策略。
6. 精确回显仓库、远端main head、task_id、route_epoch、Issue、PR、branch、status、completion_signal和reviewed/base head，提交租约声明。
7. 只有字段一致、`READY`、`execution_allowed: true`且依赖满足时才可执行。
8. 租约有效后立即完成第一个有意义的授权动作并提供证据，不得停在摘要或计划。
9. 围绕根本目标主动寻找来源冲突、反证、知识缺口、重复术语、可泛化Skill、成熟度虚高、证据污染、独立性问题、UNKNOWN和更好的验证方法。
10. 授权QCLAW候选/知识供应路径内的A/B改良应实施和测试；新canonical、运行时、跨Agent权威或系统级接口只能提案或停止升级。
11. 按PDER/WPDCR报告过程、D0-D4难度、失败、意外发现、扩展机会、未解问题、精确协同和系统反馈。
12. 完成后提交累计机器证据、AMED/WPDCR、研究/改良/发现/UNKNOWN、隐私检查、AI_HANDOFF和结果校准，不自行合并或升级权威。

## 不可执行状态

若路由PAUSED/非READY、execution_allowed为false、依赖未满足或字段不完整：禁止猜测或切换任务。必须报告失败字段、搜索/尝试、最小缺失证据或能力、受影响/可继续范围、请求Owner及精确动作和恢复条件。只写`BLOCKED`或“缺资料”无效。

## 候选与安全边界

- 公开仓库只允许`PUBLIC_SAFE`内容。
- 不上传私人知识、许可受限原文、凭证、数据库、日志正文或真实交易数据。
- 不建立第二套canonical记忆/检索/融合/网关。
- 不编辑Codex或WorkBuddy拥有的运行时/分支。
- 不自行合并、改变活动任务、扩大WIP、进入未授权Gate或触碰账户/订单/交易。

## 完成回报

必须明确：主任务、工作过程、难度、失败尝试、主动/意外发现、已实施改良、扩展Skill/知识机会、替代与拒绝项、难解问题/UNKNOWN、负面结果、精确协同、跨Agent交接、回滚、系统反哺、下一门禁，以及完整命令、退出码、哈希和full SHA。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一QCLAW任务真源：远端最新`main`上的`coordination/ACTIVE-QCLAW-TASK.yaml`。
