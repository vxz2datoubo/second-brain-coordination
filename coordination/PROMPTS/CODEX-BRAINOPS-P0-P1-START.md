# Codex guarded start prompt: BrainOps P0-P1

【Codex模式：项目计划模式】

请读取仓库 `vxz2datoubo/second-brain-coordination` 的以下内容：

1. Draft PR #109；
2. `coordination/BLUEPRINTS/BRAINOPS-LOCAL-AGENT-SERVICE-AND-PORT-CONTROL-PLANE-v1.0.md`；
3. `coordination/TASK-BRIEFS/CODEX-BRAINOPS-LOCAL-CONTROL-PLANE-P0-P1-0001-AMED.yaml`；
4. `.agents/skills/brainops-control-plane/SKILL.md`；
5. canonical main 上当前 `coordination/ACTIVE-CODEX-TASK.yaml`。

先执行路由真实性检查，不得凭本提示词自行扩大权限：

- 如果 canonical active route 尚未显式激活 `CODEX-BRAINOPS-LOCAL-CONTROL-PLANE-P0-P1-0001`，或任务仍为 `execution_allowed: false`，只回报：当前活动任务、route epoch、阻塞原因、PR #109 head，以及“BrainOps任务已排队但未获执行权”。不得创建实现分支、不得修改本地服务、不得安装软件、不得启动后台程序。
- 只有在 GPT 已发布新的明确活动路由，且 task ID、reviewed base、branch、route epoch、completion signal、allowed paths 与安全边界全部一致时，才领取租约并立即执行，不需要第二次“开始”口令。

激活后，本轮只实施 P0 + 最小 P1：

- 真实盘点 Windows、.NET、Codex CLI、Docker、GitHub 和相关本地进程/端口能力；
- 输出 SUPPORTED / UNSUPPORTED / UNKNOWN / BLOCKED 证据表；
- 完成分层架构 ADR 与威胁模型；
- 建立服务、端口、健康、审计、租约、激活清单和 Codex session 的严格 schema；
- 建立 loopback-only 的 ASP.NET Core/Blazor 只读控制台原型；
- 建立 SQLite 元数据/审计骨架，不存储秘密；
- 建立只读 native process、Windows Service、port 与 Docker availability 发现适配器；
- 建立 SignalR 实时状态和轮询恢复；
- 建立 mock/shadow route reconciler，只输出 WOULD_DISPATCH / WOULD_BLOCK，绝不调用 Codex；
- 建立必要的单元、集成与敌对测试；
- 交付安装/启动方式比较报告，但不得安装 Windows Service、计划任务、启动项或 Docker。

架构硬边界：

- Codex OAuth 与未来桌面音频进程属于用户会话 Agent，不能默认塞入 LocalSystem/LocalService；
- 管理界面仅绑定 `127.0.0.1`；
- UI 不得提供任意 shell、任意可执行路径或自由参数；
- 所有可执行路径、工作目录和参数模板必须来自白名单 manifest；
- QQ/QCLAW 在 canonical route 为暂停、阻塞、禁用或 `execution_allowed: false` 时绝不可执行；
- 不得启动、停止或杀死现有本地项目进程；
- 不得读取或输出 OAuth token、API key、浏览器配置或凭据库；
- 不得触碰真实交易、账户、订单、券商接口或生产市场数据。

最终提交形状：一个 tested substantive commit，随后一个非空 evidence-only receipt commit；完成后停止并以

`CODEX_BRAINOPS_P0_P1_DISCOVERY_ARCHITECTURE_AND_READ_ONLY_CONTROL_PLANE_READY_FOR_GPT_REVIEW`

请求 GPT 独立二次审查。不要自行进入 P2，不要开启任何自动执行。
