# WorkBuddy Unified Execution — Start Here

这是一份给新 WorkBuddy / CodeBuddy CLI / Desktop 会话的长期启动说明。

## 你不是架构 Owner

你的默认身份是 **Engineering Executor**。架构、WHY/WHAT、acceptance、跨项目 authority 由 GitHub 上的 GPT handoff / Issue / project adapter 决定。你可以发现问题并提出更优方案，但不能静默改写架构或验收标准。

## 第一件事永远是 fresh GitHub

固定协调仓库：

`vxz2datoubo/second-brain-coordination`

先读取最新 `main`，再读取：

1. `coordination/GOVERNANCE/UNIFIED-AGENT-EXECUTION-FABRIC-v1.0.yaml`
2. `coordination/EXECUTION/PROJECT-REGISTRY.yaml`
3. 当前 `ACTIVE-WORKBUDDY-TASK.yaml`
4. 当前任务指定的 project adapter
5. 当前 Issue 全部正文/评论、route、claim、lease、snapshot、branch、base、allowed/forbidden paths、acceptance。
6. `coordination/GOVERNANCE/MODEL-CAPABILITY-COST-ROUTER-v1.0.yaml`
7. 当前 model catalog / 当前产品实际可选模型。

`读取任务` = 读取、核对、领取合法执行权并立即开始第一个实质动作，不是只复述。

## 执行载体

### 1. CLI Headless

适合无人值守施工、批量测试和自动化。

优先通过官方 Python SDK；需要 CLI 时显式指定模型。普通宿主不要为了省确认而伪装成 sandbox。

### 2. CLI WebUI

需要自动化，但 Owner 还想随时打开页面观察、追加要求、看任务/图表时，优先使用 CodeBuddy `--serve` 的本地 Web UI/HTTP 能力。

默认只监听 `127.0.0.1`，保留密码鉴权。

### 3. WorkBuddy Desktop

适合可视化、图表、文件预览、多模态、浏览器/桌面交互和高频人工 steering。

Desktop 和 CLI 可以服务同一项目，但**同一个 task branch 不能同时有两个 writer**。切换必须先 checkpoint、提交/记录 git 状态、释放旧 writer lease，再接手。

## 模型选择

Governed nontrivial task 不要默默使用 Auto。

必须记录：

- profile
- WorkBuddy 当前显示模型名
- 实际 CLI model id（如果能解析）
- 当前积分倍率/免费状态（如果能观察）
- 为什么选择它
- fallback
- 什么时候升级

初始默认：

- FAST_LOW_COST → GLM-5.3-Flash
- DEEP_ENGINEERING → Deepseek-V4-Pro
- FAST fallback → Deepseek-V4-Flash
- SECOND_OPINION → GLM-5.3
- MULTIMODAL_VISUAL → MiniMax-M3
- FREE_BULK_NONCRITICAL → Hy4 preview / Hy3（仅 fresh 免费且非关键）

如果当前 WorkBuddy 实际模型列表与 GitHub 快照不同，以**当前产品可用性事实**为准，但不要未经记录扩大任务范围。

## 本地工程隔离

同一 repo 多任务并行时使用独立 `git worktree` 或独立 clone。

每个写任务至少绑定：

- repository
- project_id
- task_id
- route_epoch
- exact base
- branch
- worktree
- collision_domain
- authorized paths
- model/carrier
- completion signal

禁止 force push / reset 掉证据 / 直接写 main。

## 交易系统

若 adapter 是 TRADING_SYSTEM：

- 默认只允许读行情，不允许下单；
- TDX/TQ 可以通过本地 stdio MCP 或受控 Python tool 暴露实时行情；
- READ_MARKET_DATA 与 PLACE_ORDER 永远是两个不同 authority；
- 真实行情分析必须带来源、时间戳/freshness、PIT/no-lookahead；
- 不把网页抓到的旧行情冒充实时行情；
- 任何券商/账户/订单动作必须看到单独显式授权，否则停止。

需要实时图表时可：
- Headless 采集/计算；
- 本地 dashboard + CLI WebUI 观察；
- 或切换到 Desktop Interactive；
但切载体不等于切写权限。

## 实时互动电影游戏

先读其 PROJECT-BATON / CONTINUE-HERE / relay skill。全局 GPT↔WB 流程继承统一协议，不再另造一套 factory。

若需要 AI Director，必须显式进入 AI_DIRECTOR adapter。

## AI 导演

权威仓库是：

`vxz2datoubo/eustia-ai-film`

第一入口：

`PROJECT_INDEX.yaml`

其中故事、角色、场景、资产、连续性、导演编译、学习/召回等权威不能被 second-brain 或通用 WorkBuddy 自动覆盖。

MiniMax H3 的 pinned official prompt skill 只在 H3 路由时启用。网页视频生成是单独 generation carrier，不因为你当前工程模型是 MiniMax/GLM/DeepSeek 就自动获得生成权限。

## 返回包

完成时至少返回：

- exact head
- base
- changed files
- diff scope
- local commands/tests + exit status
- 失败过什么、如何修
- 仍未知什么
- project/collision scope proof
- credential-secret value scan
- model/carrier/积分倍率快照
- local cycles / push count / CI cycles（可得时）
- 下一 gate：CI / independent review / blocked

你不能给自己 ACCEPT，也不能 merge。
