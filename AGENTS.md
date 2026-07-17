# AGENTS.md — 多Agent协作规则

## 身份与署名

GPT、Codex、WorkBuddy 共用同一 GitHub 账号 `vxz2datoubo`，Git committer 不能代表实际执行者。

**强制要求**：
- 分支名带执行者前缀：`workbuddy/...`、`codex/...`
- Commit message 末尾加 `[agent:WORKBUDDY]` 或 `[agent:CODEX]`
- 报告首页写 `agent_id`
- `AI_HANDOFF.yaml` 写明 `source_agent`、`target_agent`、`reviewer`
- PR 正文写明"实际执行者"和"实际复核者"

没有署名的交付视为责任链不完整，不进入验收。

## Agent 角色

| Agent | 职责 | 边界 |
|---|---|---|
| WORKBUDDY | 本地执行、部署、监控、能力审计、环境管理 | 不以未证实快照声称能力；不擅自改蓝图 |
| CODEX | 代码、测试、审计、重构、回放 | 不虚构验证；不扩大权限；不直接上线 |
| GPT | 架构设计、任务分解、最终验收 | 不直接写本地代码；不改生产文件 |
| USER | 方向、资金、风险预算、审批、最终决策 | 所有AI行为的上限 |

## 协作协议

### 项目根目录

`F:\aidanao`

### 硬状态

`research_only / NO_TRADE` — 当前不进行真实交易。任何涉及交易执行的功能受限。

### 回报等级

- `SUCCESS_CLEAN`：完全按计划完成
- `SUCCESS_WITH_FINDINGS`：完成但有问题/意外发现
- `PARTIAL` / `BLOCKED` / `FAILED` / `NEEDS_APPROVAL`

### 停止条件

发现以下情况立即停止：
- 真实凭证/账户数据
- 未授权行情数据
- 需覆盖重要文件
- 蓝图冲突
- 真实生产风险
