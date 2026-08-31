# Codex ↔ WorkBuddy 协作与算力接力运行手册

`agent_id: CODEX`

这份手册把两名执行者变成协作流水线，但不替代 GitHub 上的 ACTIVE route、Issue、Claim、Lease、Snapshot 或单写者预约。

## 用户看到的最简单版本

正常施工时无需操作。Codex 在安全里程碑推送普通提交；WorkBuddy 只验证已推送的精确 SHA。

当 Codex 额度不足、且 GitHub 上已经出现新的可执行 WorkBuddy route 后，用户只需对 WorkBuddy 说：

```text
继续实时互动电影游戏项目
```

WorkBuddy 必须自动读取 `PROJECT-BATON.yaml`、自己的 ACTIVE route 和本目录的 relay package。它不能要求用户重新讲历史。

如果 WorkBuddy ACTIVE route 仍为 `execution_allowed: false`，用户不要让它强行施工。此时唯一缺口是由 GitHub integrator 发布一次正式 WorkBuddy route。最短请求为：

```text
发布实时互动电影游戏项目的 WorkBuddy 接力任务，使用 GitHub 中最新的 Codex 安全检查点和接力包。
```

## Codex 安全检查点

Codex 在接近额度边界前必须：

1. 只保留可构建状态；
2. 运行与当前风险相称的一套本地回归；
3. 普通 commit 并 push，不 amend、不 force-push；
4. 记录 baseline、40 位 exact head、测试、风险、回滚和唯一下一步；
5. 声明哪些写入面交出、哪些仍保留；
6. 若 WorkBuddy route 尚未发布，状态必须是 `BLOCKED_PENDING_TARGET_ROUTE`，不能假装已交棒。

## WorkBuddy 接棒后的连续工作

一个正式 route 可以把下列工作写成有序队列，使 WorkBuddy 完成验算后不用用户再次说“开始”：

1. `WB-V1`：独立干净克隆并锁定 Codex exact head；
2. `WB-V2`：运行固定全量回归和项目边界扫描；
3. `WB-V3`：运行 route 明确列出的攻击、并发、恢复和 Windows 环境矩阵；
4. `WB-S1...n`：只完成 route 已列明的简单、非重叠任务；
5. `WB-H1`：推送 WorkBuddy 分支，形成返回 Codex 的 exact-head 交接包。

只要仍在同一 route 的有序范围内，`automatic_resume_within_task` 可以为 `true`。发现架构变化、验收标准变化、与 Codex 写入面重叠、凭证/真实数据/外部付费服务或未列明的新模块时必须停止。

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
