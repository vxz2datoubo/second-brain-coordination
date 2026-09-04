# Unified Execution Fabric — Research Notes

Issue: #596

本文件只记录采用架构背后的公开技术依据，不是新的执行权威。

## 1. Ports & Adapters

统一总线只定义稳定“端口”，第二大脑、交易、互动电影、AI 导演各自实现 adapter。这样 CLI、Desktop、Codex、未来模型都能替换，而领域 SoR 不需要跟着重写。

## 2. GitOps-style reconciliation

GitHub 保存版本化 desired engineering state；本地 bridge 主动 pull 并比对实际本机状态。采用 pull/reconcile 而不是 public repo 任意 workflow 直接执行宿主命令。

## 3. WorkBuddy/CodeBuddy 官方本地能力

当前官方 CLI/SDK 已提供：

- `--model` / fallback model；
- Headless；
- Python Agent SDK；
- MCP；
- `--serve` 本地 Web UI / HTTP API；
- 后台会话；
- session cost / stats；
- tool allow/deny 和 permission mode。

因此本地 bridge 不需要做 GUI 键鼠脚本。

## 4. 为什么不用 public-repo unrestricted self-hosted runner

GitHub 官方安全文档明确警告 public repository 的 fork/PR 可导致 self-hosted runner 执行危险代码并危及宿主环境。因此本项目默认采用窄权限、pull-based local reconciler。

## 5. 多项目并行

Git 官方 `git worktree` 支持同一 repository 同时检出多个工作树。我们用 task-scoped worktree 物理隔离本地任务，再用 collision domain 保证同一 canonical object 仍只有一个 writer。

## 6. MCP

MCP 标准支持 stdio 与 Streamable HTTP。对交易系统，本地实时数据优先采用 stdio MCP 或受控本地 Python tool，避免把行情/账户能力暴露成宽泛网络服务。

## 7. 模型路由

供应商基准只能作为方向信号，因为 harness、reasoning effort、tool scaffold 可能不同。最终模型路由依据我们自己的任务级 telemetry 学习，不把某天 UI 的积分倍率写成永久真理。
