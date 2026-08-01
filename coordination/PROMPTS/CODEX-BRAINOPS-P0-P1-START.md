# Codex guarded start prompt: BrainOps P0-P1

【Codex模式：项目计划模式】

请读取仓库 `vxz2datoubo/second-brain-coordination` 的以下内容：

1. Draft PR #109；
2. `coordination/BLUEPRINTS/BRAINOPS-LOCAL-AGENT-SERVICE-AND-PORT-CONTROL-PLANE-v1.0.md`；
3. `coordination/BLUEPRINTS/BRAINOPS-CODEX-APP-FIRST-ACTIVATION-ADDENDUM-v1.1.md`；
4. `coordination/TASK-BRIEFS/CODEX-BRAINOPS-LOCAL-CONTROL-PLANE-P0-P1-0001-AMED.yaml`；
5. `.agents/skills/brainops-control-plane/SKILL.md`；
6. canonical main 上当前 `coordination/ACTIVE-CODEX-TASK.yaml`。

先执行路由真实性检查，不得凭本提示词自行扩大权限：

- 如果 canonical active route 尚未显式激活 `CODEX-BRAINOPS-LOCAL-CONTROL-PLANE-P0-P1-0001`，或任务仍为 `execution_allowed: false`，只回报：当前活动任务、route epoch、阻塞原因、PR #109 head，以及“BrainOps任务已排队但未获执行权”。不得创建实现分支、不得修改本地服务、不得安装软件、不得启动后台程序。
- 只有在 GPT 已发布新的明确活动路由，且 task ID、reviewed base、branch、route epoch、completion signal、allowed paths 与安全边界全部一致时，才领取租约并立即执行，不需要第二次“开始”口令。

激活后，本轮只实施 P0 + 最小 P1：

- 真实盘点 Windows、ChatGPT桌面应用、Codex视图、Codex App Automations、Codex CLI、.NET、Docker、GitHub 和相关本地进程/端口能力；
- 核验 2026-07-16 后的 ChatGPT/Codex 桌面一体化外壳在本机的真实可用状态，不得仅凭文档推定；
- 优先评估 Codex App 作为正常执行和人工监督界面，CLI 只作为机器执行备用方案；
- 核验 App Automations 是否可用、是否支持每30分钟、是否可回到同一线程、是否进入review queue、是否要求电脑唤醒且App运行；
- 搜索并验证是否存在官方公开的App本地触发API、深链、URI scheme、命令或App Intent；不存在则明确记录，不得采用鼠标键盘模拟、界面抓取或未公开进程注入；
- 输出 SUPPORTED / UNSUPPORTED / UNKNOWN / BLOCKED 证据表；
- 完成 App优先、CLI备用的分层架构 ADR 与威胁模型；
- 建立服务、端口、健康、审计、租约、激活清单、Codex App automation/thread 与 CLI session 的严格 schema；
- 建立 loopback-only 的 ASP.NET Core/Blazor 只读控制台原型；
- 建立 SQLite 元数据/审计骨架，不存储秘密；
- 建立只读 ChatGPT/Codex App host、native process、Windows Service、port 与 Docker availability 发现适配器；
- 建立 SignalR 实时状态和轮询恢复；
- 建立 mock/shadow route reconciler，只输出 WOULD_DISPATCH / WOULD_BLOCK，绝不调用 Codex App 或 CLI；
- 建立必要的单元、集成与敌对测试；
- 交付 App Automation、CLI fallback、Windows启动方式比较报告，但不得安装 Windows Service、计划任务、启动项或 Docker。

架构硬边界：

- 集成后的 ChatGPT 桌面应用中的 Codex 视图是首选人机界面，Codex CLI 不是默认用户界面；
- App 与 ChatGPT 处于同一桌面外壳不等于工作流、线程历史或外部控制API已经完全合并；
- Codex OAuth、Codex App、CLI备用执行器与未来桌面音频进程属于用户会话 Agent，不能默认塞入 LocalSystem/LocalService；
- BrainOps不得通过UI自动化操纵Codex App；
- BrainOps默认不得为了停止一个任务而终止整个ChatGPT桌面应用；
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
