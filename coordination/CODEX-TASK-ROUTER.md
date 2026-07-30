# Codex任务路由协议

## 永久短命令语义

当用户对Codex说`读取任务`、`执行任务`、`开始任务`或同义短句时，必须遵守：

`coordination/GOVERNANCE/AGENT-READ-TASK-CLAIM-AND-EXECUTE-COMMAND-SEMANTICS-v1.0.yaml`

它们的统一含义是：**验证权威仓库 → 读取远端最新任务真源 → 核对租约 → 领取任务 → 立即开始实质执行 → 持续到检查点、真实阻塞或完成。**

禁止行为：

- 只复述任务或回复“已读取”；
- 只展示计划而不开始第一个授权动作；
- 等用户再次说“执行”“继续”或“开始”；
- 任务已经自包含时反问用户要做什么；
- 将`读取任务`解释成文件导航、摘要或确认收到；
- 未验证仓库身份就让本地`origin/main`覆盖GitHub权威main。

当路由`READY`且`execution_allowed: true`时，本次响应结束前至少必须完成第一个有意义的授权动作并给出证据。长任务可以在检查点回报，但检查点必须有实质进展、测试或真实阻塞。

## 权威仓库与远端身份

1. 固定权威仓库为`vxz2datoubo/second-brain-coordination`。
2. 固定规范HTTPS地址为`https://github.com/vxz2datoubo/second-brain-coordination.git`。
3. 本地名为`origin`的remote只是传输配置，只有URL身份与权威仓库一致且远端ref已核验时才可作为任务真源。
4. 领取任务和宣布路由陈旧前必须记录脱敏后的`git remote -v`，并通过以下至少一种方式核验规范`refs/heads/main`：
   - 对规范HTTPS地址执行`git ls-remote`；
   - 一次性fetch到独立remote-tracking ref；
   - 使用受控GitHub连接器/API直接读取main与活动索引。
5. 若本地`origin/main`、规范远端main和GitHub活动索引不一致，必须提交`RemoteIdentityMismatchPacket`，保留本地提交和工作区，不得reset、rebase、amend、clean或force push。
6. 本地origin分叉本身不能把任务静默降级到旧Epoch。只有规范远端确认路由陈旧，或GPT发布桥接/替代路由，才可停止或切换。
7. 不得输出带凭证的remote URL。报告只保留脱敏URL、仓库身份和SHA。

## 执行顺序

1. 验证规范仓库身份和规范main，不把未经确认的本地remote-tracking ref当权威。
2. 安全同步或远程读取最新规范`main`；本地有未提交内容时不得覆盖。
3. 读取本协议、RTCE协议、任务租约与完成新鲜度协议、进行中可见性协议、AMED、PMA-BIG、WPDCR、PDER、双层主观能动性宪法和本地凭据协议。
4. 读取规范main上的最新`coordination/ACTIVE-CODEX-TASK.yaml`，不得使用旧缓存、聊天记忆或其他Agent索引代替。
5. 读取活动索引中的task_id、route_epoch、Issue、PR、branch、base、status、execution_allowed、completion_signal、依赖、模式、任务简报、影响预测、探索预算、权限和停止条件。
6. 读取活动Issue正文、全部评论和相关PR证据。
7. 提交精确任务租约声明，逐字回显仓库、规范远端main head、task_id、route_epoch、Issue、PR、branch、status、completion_signal和reviewed/base head。
8. 只有字段完全一致、`READY`、`execution_allowed: true`且依赖满足时才可执行。
9. 租约有效后立即执行第一个实质动作，不得在任务复述或计划阶段停止。
10. 执行期间围绕根本目标自主选择更可靠、更简单、更完整的方法，主动检查相邻模块、测试、接口、复用能力和过时假设。
11. 授权范围内的AMED A/B高价值改良应实施并测试；C只提案；D或用户门停止升级。
12. 按PDER和WPDCR实时报告难度、方案转向、失败、新发现、扩展、未解问题、精确协同和系统反馈。
13. 到检查点、阻塞、交接或完成时发布可验证证据。完成必须提交累计AMED/WPDCR/测试/UNKNOWN/AI_HANDOFF，不自行合并。
14. 完成信号发布前重新读取规范远端最新main并核对全部租约字段；不一致时先执行远端身份核验，再决定提交`StaleRoutePacket`或`RemoteIdentityMismatchPacket`。

## 远端身份分叉处理

`RemoteIdentityMismatchPacket`必须包含：

- 配置remote名称与脱敏URL；
- 规范仓库全名与HTTPS地址；
- 本地`origin/main` SHA；
- 规范`refs/heads/main` SHA；
- 两处活动任务的task_id与route_epoch；
- 已保留本地commit、parent、tree和changed paths；
- 实际命令、退出码和stdout/stderr SHA-256；
- 受影响范围、仍可继续工作、请求Owner和恢复条件。

若已经产生实质本地提交，必须原样保留。GPT可发布桥接路由，授权从规范remote恢复同一任务并把该提交不改写地推送到活动分支。

## 不可执行状态

若规范路由不是READY、execution_allowed不是true、依赖未满足、字段缺失或规范路由已确认陈旧：

- 禁止选择其他Issue、旧Epoch或其他Agent任务；
- 必须报告精确失败字段；
- 列出已做检查和尝试；
- 写明最小缺失信息/能力/决定；
- 区分受影响和可继续范围；
- 指定请求Owner、精确动作和关闭/恢复条件；
- 只写`BLOCKED`无效。

## 主观能动性与边界

Codex不是被动工单读取器。每个非轻量任务必须同时完成：

1. 主任务交付；
2. 主动发现错误假设、缺口、重复、接口、风险、负面结果和机会；
3. 授权A/B改良；
4. 未解问题与安全弃权；
5. 精确跨Agent协调；
6. 系统演进提案和经验反哺。

主动性不授予切换顶层任务、接管其他Agent、建立第二canonical、改变权限/许可/隐私/真实数据/生产/账户/订单/交易或自行批准重大扩展的权力。

## 进行中可见性

出现实质本地提交、主要缺陷修复、配置检查点、长暂停、交接、请求审查、远端身份分叉或路由变化时，必须按可见性协议发布InProgressVisibilityPacket、RemoteIdentityMismatchPacket或安全checkpoint。远端PR head不变不能被解释为没有本地进展；但本地报告也不能替代最终远端tested/receipt证据。

## 完成回执

完成必须明确分栏并给出机器证据：

- 主任务结果；
- 工作过程和方案变化；
- 计划/实际难度及证据；
- 主动发现和意外发现；
- 已实施改良；
- 高价值扩展；
- 替代/拒绝方案；
- 难解问题、UNKNOWN和弃权；
- 失败与负面结果；
- 精确协同请求；
- 跨Agent影响；
- 回滚；
- 系统反哺；
- 下一行动与验收门；
- 完整命令、退出码、计数、stdout/stderr SHA-256、tested/receipt full SHA。

固定仓库：`vxz2datoubo/second-brain-coordination`

唯一任务真源：规范GitHub远端最新`main`上的`coordination/ACTIVE-CODEX-TASK.yaml`。
