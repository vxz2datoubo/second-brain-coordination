# Codex ↔ WorkBuddy 协作与算力接力运行手册

`agent_id: CODEX`

这份手册把两名执行者变成协作流水线，但不替代 GitHub 上的 ACTIVE route、Issue、Claim、Lease、Snapshot 或单写者预约。

## 用户看到的最简单版本

正常施工时无需操作。Codex 在安全里程碑推送普通提交；WorkBuddy 只验证已推送的精确 SHA。

双方共同入口为 `EXECUTOR-COORDINATION-BATON.yaml`。任何一方开工前都应先运行：

```powershell
python tools/coordinate_creative_executors.py `
  --baton coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175/EXECUTOR-COORDINATION-BATON.yaml `
  --event AUTO
```

它会同时给出 `codex_action`、`workbuddy_action` 和唯一下一步。它只读取 GitHub 权威状态，
不能自己发布 route、领取任务、验收或合并。

当 Codex 额度不足、且 GitHub 上已经出现新的可执行 WorkBuddy route 后，用户只需对 WorkBuddy 说：

```text
继续实时互动电影游戏项目
```

WorkBuddy 必须自动读取 `PROJECT-BATON.yaml`、自己的 ACTIVE route 和本目录的 relay package。它不能要求用户重新讲历史。

接力包同时记录持续前进的实施分支和冻结的 checkpoint remote ref。WorkBuddy 验算必须使用 checkpoint ref；实施分支后来继续前进不会使已经排队的被测 SHA 失效。

如果 WorkBuddy ACTIVE route 仍为 `execution_allowed: false`，用户不要让它强行施工。此时唯一缺口是由 GitHub integrator 发布一次正式 WorkBuddy route。最短请求为：

```text
发布实时互动电影游戏项目的 WorkBuddy 接力任务，使用 GitHub 中最新的 Codex 安全检查点和接力包。
```

## Codex 安全检查点

Codex 在接近额度边界前必须：

1. 只保留可构建状态；
2. 运行与当前风险相称的一套本地回归；
3. 普通 commit 并 push，不 amend、不 force-push；
4. 为 exact head 创建一个新的、从不移动的 `codex/checkpoint-...` 远端分支；
5. 记录 baseline、40 位 exact head、checkpoint remote ref、测试、风险、回滚和唯一下一步；
6. 声明哪些写入面交出、哪些仍保留；
7. 若 WorkBuddy route 尚未发布，状态必须是 `BLOCKED_PENDING_TARGET_ROUTE`，不能假装已交棒。

## WorkBuddy 接棒后的连续工作

一个正式 route 可以把下列工作写成有序队列，使 WorkBuddy 完成验算后不用用户再次说“开始”：

1. `WB-V1`：独立干净克隆并锁定 Codex exact head；
2. `WB-V2`：运行固定全量回归和项目边界扫描；
3. `WB-V3`：运行 route 明确列出的攻击、并发、恢复和 Windows 环境矩阵；
4. `WB-S1...n`：只完成 route 已列明的简单、非重叠任务；
5. `WB-H1`：推送 WorkBuddy 分支，形成返回 Codex 的 exact-head 交接包。

只要仍在同一 route 的有序范围内，`automatic_resume_within_task` 可以为 `true`。发现架构变化、验收标准变化、与 Codex 写入面重叠、凭证/真实数据/外部付费服务或未列明的新模块时必须停止。

任务分配、成本优先级和验证种类的唯一候选策略见
`CODEX-WORKBUDDY-EXECUTION-POLICY.yaml`。正式 WorkBuddy route 应复制并绑定
`WORKBUDDY-ORDERED-BATCH-TEMPLATE.yaml`，再用下列命令逐项选择下一工作：

```powershell
python tools/evaluate_creative_executor_batch.py <BOUND-WORKBUDDY-BATCH.yaml>
```

输出 `READY` 时只领取 `ready_items` 中的唯一项目；输出 `RUNNING` 时只完成当前项目；
输出 `RETURN_TO_CODEX` 时停止新增工作并发布返回包；输出 `BLOCKED` 时禁止自行绕过。
这个工具不能发布 route，也不能授予执行、review 或 merge 权。

Codex 和 WorkBuddy 不必完全串行。WorkBuddy 可以对一个冻结的 Codex checkpoint 做只读验证，
同时 Codex 在不重叠的核心表面继续前进。WorkBuddy 的阻断发现只冻结受影响表面；未受影响的
Codex 切片可以继续。只有 `IMPLEMENTATION_BATON` 交出的写入面必须保持单写者。

额度边界使用：

```powershell
python tools/coordinate_creative_executors.py `
  --baton coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175/EXECUTOR-COORDINATION-BATON.yaml `
  --event CODEX_QUOTA_LOW
```

WorkBuddy 完成整个有序批次后使用 `--event WORKBUDDY_BATCH_COMPLETE`；用户说“同步”或
“收尾”时使用 `--event USER_SYNC`，一次性汇总双方证据，不在日常循环中骚扰 GPT。

所谓“攻击测试”仅指对离线合成输入做鲁棒性验证，包括重复、乱序、截断、篡改、
并发、恢复和存储增长；不扫描外部系统、不碰账号、不尝试绕过权限，也不使用真实用户数据。

## 结果回传

WorkBuddy 的 PASS 叫：

```text
EXECUTOR_CLEAN_REPRODUCTION
```

它证明指定环境对指定 SHA 的命令通过，不等于最终独立验收。失败用 `WORKBUDDY-FINDING-TEMPLATE.yaml`，必须包含最小复现，不能一边改 Codex 分支一边宣布通过。

WorkBuddy 若实现了简单任务，必须使用新的 `workbuddy/...` 分支，推送 exact head 后将 Baton 指回 Codex。Codex 恢复时只依赖 GitHub，不依赖 WorkBuddy 聊天或未提交本地状态。

## GPT 终审边界

日常 Codex ↔ WorkBuddy 循环不自动联系 GPT。只有用户明确说“同步”或“收尾”时，才将整个阶段的 Codex 实现、WorkBuddy 环境/攻击证据、已知风险和精确提交一次性交给 GPT 做跨模块终审。

## 当前真实状态

- Codex R175：可执行且已形成推送检查点。
- WorkBuddy canonical ACTIVE route：仍为暂停、`execution_allowed: false`。
- 协作合同、队列、模板和校验器：已准备为候选实现。
- 因此当前是“链路已搭建、WorkBuddy 正式开工权尚未发布”，不是“WorkBuddy 已经可以写代码”。

验证当前接力包：

```powershell
python tools/validate_creative_executor_relay.py `
  coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175/EXECUTOR-RELAY-QUEUE.yaml
```

预期结果为 `PASS`，并包含 `target_authority_fail_closed`。发布完整 WorkBuddy route 后，更新 route 四个引用和状态，预期应变为 `target_authority_complete`。

生成额度检查点收据前，必须先把当前 HEAD 推送到新的冻结 checkpoint 分支并 fetch 为远端跟踪引用，然后运行：

```powershell
python tools/create_creative_quota_checkpoint.py `
  --source-agent CODEX `
  --target-agent WORKBUDDY `
  --baseline <IMPLEMENTATION_BASELINE> `
  --checkpoint-remote-ref refs/remotes/origin/codex/checkpoint-<TASK>-<SHORT_SHA> `
  --remaining-next-action "<ONE_NEXT_ACTION>" `
  --test creative_suite=PASS `
  --test public_safe=PASS `
  --completed "<COMPLETED_SCOPE>" `
  --output .creative-evidence/quota-checkpoint.json
```

工具只接受干净工作树、执行者前缀正确的当前分支以及和当前 HEAD 完全一致的冻结远端引用。收据只保存测试名称和结论，不嵌入原始日志；输出只能写入 Git 忽略的 `.creative-evidence/`。

任何 Agent 在让 WorkBuddy 开工前都应运行一次 canonical readiness audit：

```powershell
python tools/audit_creative_relay_readiness.py `
  --main-ref origin/main `
  --package coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R175/EXECUTOR-RELAY-QUEUE.yaml
```

只有输出 `status: READY` 才能领取 WorkBuddy 任务。`BLOCKED` 会列出 canonical ACTIVE route、package route 或 checkpoint SHA 的精确不一致，并给出唯一下一步；这个审计器只观察权限，永远不能自行授予执行、review 或 merge 权。
