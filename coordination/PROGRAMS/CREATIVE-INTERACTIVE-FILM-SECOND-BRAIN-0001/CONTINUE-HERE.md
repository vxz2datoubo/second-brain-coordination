# 实时互动电影游戏：从这里继续

如果你是 **GPT、Codex 或 WorkBuddy**，用户只说了：

> **继续实时互动电影游戏项目**

不要让用户重新解释历史，也不要先写一大段计划。

## 固定读取顺序

1. 读 [`PROJECT-BATON.yaml`](./PROJECT-BATON.yaml) ＝ **现在轮到谁、正在做什么、下一步是什么**。
2. 读 [`CREATIVE-INTERACTIVE-FILM-MULTI-AGENT-RELAY-SKILL-v1.0.yaml`](../../SKILLS/CREATIVE-INTERACTIVE-FILM-MULTI-AGENT-RELAY-SKILL-v1.0.yaml) ＝ **怎么继续、怎么交接、冲突时怎么办**。
3. 读 [`GPT-WORKBUDDY-ENGINEERING-FACTORY-PROTOCOL-v1.0.yaml`](../../GOVERNANCE/GPT-WORKBUDDY-ENGINEERING-FACTORY-PROTOCOL-v1.0.yaml) ＝ **GPT 与 WorkBuddy 的长期工程分工、模型选择、CLI 对接和回传规则**。
4. 读 Baton 指向的 **当前 Issue / PR / exact head / ACTIVE route**。
5. Fresh reconcile GitHub 现实；如果 Baton 过期，先纠正 Baton，再继续。
6. 如果当前 Agent 正是合法执行者，**同一轮直接开始第一个有意义的授权动作**，不要等用户再说“开始”。

## GPT→WorkBuddy长期工程模式

本项目默认采用：

`用户目标 → GPT研究/架构/合同/验收 → GitHub任务真源 → WorkBuddy实际编程/本地实测 → GPT对账/集成 → 独立验算/受治理canonicalization`

GPT向WorkBuddy发布任何非trivial工程任务时，必须明确告诉用户以及任务文件本身：

- 使用 `DEEPSEEK_V4_PRO`、`DEEPSEEK_V4_FLASH` 还是 `HYBRID_PRO_WITH_FLASH_LITE`；
- 精确 `primary_model_id / reasoning_model_id / lite_model_id`；
- 为什么选这个模型；
- execution carrier 是 WorkBuddy App 还是 CLI；
- 模型缺失或不可用时是 fail closed 还是经过GPT显式批准的fallback。

没有明确模型分配的WorkBuddy治理任务不得执行。

## 用户说“做交接”时

当前 AI 必须：

1. 到达安全检查点，不能把只存在本机/当前聊天里的未记录修改直接甩给下一位；
2. fresh 对账 main / Issue / PR / exact head / CI / review / route；
3. 向 [`PROJECT-HANDOFF-LOG.md`](./PROJECT-HANDOFF-LOG.md) **只追加**一条交接记录；
4. 更新 `PROJECT-BATON.yaml` 的当前 holder、下一位、状态、证据和 exact next action；
5. 下一位如果需要新任务/route，先创建或更新真正的 Issue/ACTIVE route，Baton 只能指向它，不能自己授权；
6. 如果某 exact head 已送独立验算，停止修改它；
7. 告诉用户“已交给谁 + 入口在哪里”即可，不要求用户复制长提示词。

## 一句话理解五个核心东西

- **Baton**：工地门口的“现在谁接班、下一步干什么”白板。
- **Handoff Log**：每次换班的流水账，只追加，不覆盖历史。
- **Issue / PR / ACTIVE route**：真正决定任务、代码和权限的事实源。
- **Skill**：多 Agent 都遵守的接班规则。
- **Engineering Factory Protocol**：决定 GPT 与 WorkBuddy 怎么分工、什么时候用 Pro/Flash、CLI 怎么接 GitHub 的长期工作法。

## 绝对不要做

- 不要把 `ACCEPT` 自动理解成已经进入 `main`；
- 不要把 Baton 当成代码/世界/session/merge 权威；
- 不要两个 AI 同时写同一个 single-writer surface；
- 不要从聊天记忆猜当前 head；
- 不要为了交接复制私密本地资料到公开 GitHub；
- 不要 self-review / self-merge；
- 不要让WorkBuddy在未声明模型的情况下执行治理任务；
- 不要把GitHub上的READY字段误认为能够无桥接地启动用户本机CLI进程。

当前项目机器入口始终是：

`coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/PROJECT-BATON.yaml`
