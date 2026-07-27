# 本地PARTIAL不可见事件与纠正措施

- 日期：2026-07-27
- 父项目：Issue #31
- 关联任务：Codex Epoch 14 → Epoch 15
- 关联PR：#101
- 状态：CORRECTIVE_ACTION_ACTIVE

## 事件

GPT根据远端main、PR #101远端head和最近远端提交，判断“没有新的Agent交付”，并将Epoch 14优化为Epoch 15。
随后用户提供Codex完整状态报告，表明Codex已经在本地形成PARTIAL恢复提交：

`4bce7eca2da7aa37168b10f8415cf8bff7138e98`

该SHA在GitHub上无法解析，PR #101远端head仍为`9e694d1cca3fd867fe5b1d2deb6a7c3868546ae6`。因此本地工作真实存在的可能性与远端不可审查状态同时成立。

## 准确结论

错误不在于把本地提交判为未验收，因为不可远程获取的提交本来就不能正式验收。
错误在于把：

`NO_REMOTE_VERIFIABLE_DELIVERY`

扩大解释成：

`NO_NEW_PROGRESS`

远端没有新head只能证明没有新的远端可验证交付，不能证明Agent本地没有实质进展。

## 根本原因

1. 现有租约协议只设置了开工前和完成前的新鲜度检查，没有进行中成果可见性门。
2. 大型Codex任务允许长时间本地开发，最终又要求严格tested＋receipt提交形状，客观上降低了中途推送频率。
3. Agent报告PARTIAL或创建本地恢复提交时，没有强制发布标准化`InProgressVisibilityPacket`。
4. GPT审查流程没有把“本地状态未知”作为独立状态，也没有在切换route_epoch前检查checkpoint ref。
5. 用户提供完整Agent报告的时间晚于远端审查与新路由发布，形成异步竞态。

## 发生概率判断

分类：`STRUCTURAL_MEDIUM_HIGH_RECURRENCE_RISK`

这不是一次性的GitHub延迟。只要同时满足以下条件，就可能重现：

- 任务较大；
- Agent在本地形成实质提交；
- 最终交付尚未推送；
- 用户或GPT在此期间发起审查或切换路由。

因此需要制度调整。若只是一条短命令失败或偶发API延迟，则不值得新增治理，但本事件不属于该类。

## 纠正措施

### Agent侧

- 达到实质检查点、形成本地PARTIAL提交、准备暂停/交接/审查或发现route_epoch变化时，必须发布`InProgressVisibilityPacket`。
- PUBLIC_SAFE内容推到每个Gate唯一的快进checkpoint分支。
- 含秘密、私人数据、许可受限内容或真实行情的本地工作不得推送，只发布脱敏的`LOCAL_UNVERIFIABLE`包。
- checkpoint不是tested head、receipt head、最终交付或canonical，不得合并。
- 路由变更时必须保存本地工作并执行桥接，不得reset、覆盖、强推或静默丢弃。

### GPT侧

- “审查任务”必须检查PR/Issue中的PARTIAL、CHECKPOINT、RECOVERY_POINT、StaleRoutePacket和InProgressVisibilityPacket。
- PR head未变化时，只能输出`NO_REMOTE_VERIFIABLE_DELIVERY`。
- 只有存在当前`IDLE_OR_NO_LOCAL_PROGRESS`包或等价独立证据，才能断言没有本地实质进展。
- 发布更高route_epoch前，必须为已报告或未知的本地工作定义保留、桥接、隔离或有理由丢弃的策略。
- 用户提供本地SHA时，应标为`LOCAL_PROGRESS_REPORTED_NOT_VERIFIED`，不能直接接受，也不能忽略。

## 比例控制

本措施采用事件触发，不采用高频定时上报：

- 小改字、草稿和失败实验不需要远端checkpoint；
- 一个活动Gate最多一个checkpoint分支；
- checkpoint分支不计入最终PR和提交形状；
- 只有实质提交、主要测试里程碑、PARTIAL状态、暂停/交接或路由变化才触发。

这样避免治理噪声，同时消除长任务的本地盲区。

## 新增与更新的权威文件

- `coordination/GOVERNANCE/AGENT-IN-PROGRESS-REMOTE-VISIBILITY-AND-ROUTE-BRIDGE-PROTOCOL-v1.0.yaml`
- `coordination/GOVERNANCE/AGENT-TASK-LEASE-AND-COMPLETION-FRESHNESS-PROTOCOL-v1.0.yaml` schema 1.2.0
- `coordination/GOVERNANCE/GPT-TASK-REVIEW-AND-PUBLISH-COMMAND-SEMANTICS-v1.0.yaml` schema 1.1
- `coordination/CODEX-TASK-ROUTER.md`

## 回归案例

当PR head未变化，但Agent拥有未推送的PARTIAL本地提交，且GPT准备发布更高route_epoch时：

1. GPT不得宣称“没有进展”；
2. GPT必须标记远端无可验证交付、本地状态未知或已报告；
3. 新路由必须桥接本地工作；
4. Agent保存本地提交并发布checkpoint或脱敏包；
5. 只有远端可获取后才能内容验收。

## 不变边界

- 不自动接受本地自报提交；
- 不允许秘密或私人材料为了checkpoint被上传；
- 不直接写main、不自动合并、不强推、不重写历史；
- 不释放Issue #92、真实数据、回放、回测、拟合、账户、订单或交易权限。
