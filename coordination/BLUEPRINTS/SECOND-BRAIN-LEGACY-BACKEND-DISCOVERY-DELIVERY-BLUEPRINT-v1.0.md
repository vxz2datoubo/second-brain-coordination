# 第二大脑旧后端识别与复用评估交付蓝图 v1.0

> 状态：read_only / research_only / NO_TRADE
>
> 父任务：Issue #22 `SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003`
>
> 交付方式：GPT先在GitHub建立蓝图与任务，用户再手动通知Codex或WorkBuddy读取指定Issue执行；执行者通过独立分支、PR和Issue评论回传，GPT最后验收。

## 一、背景与重构原因

Issue #22 原任务把静态配置扫描、端口与进程核验、健康检查、数据存储识别、接口能力判断和架构复用评估放在同一次执行中。第一次Codex调度在900秒后超时，未形成完整报告。

本蓝图不简单延长超时时间，而是把任务改造成可检查点、可恢复、可独立验收的三阶段交付链：

1. 静态线索发现；
2. 运行态与端口验证；
3. 证据合并与复用评估。

任何阶段失败或阻塞，都必须保留已完成证据，不能让整轮工作归零。

## 二、总目标

基于真实本地环境，识别用户既有第二大脑后端的：

- URL、IP、端口与协议；
- 对应项目、进程、启动脚本与配置；
- 数据目录、知识库类型与存储方式；
- API、MCP、Web、RAG或其他调用能力；
- 当前运行状态与可恢复方式；
- 与Issue #21 GitHub＋Supabase知识云架构的复用、封装、迁移或淘汰建议。

禁止凭用户记忆猜测地址。所有结论必须绑定证据来源和置信度。

## 三、GitHub交付链

```text
GPT建立蓝图与子Issue
        ↓
用户通知指定执行者读取GitHub Issue
        ↓
Codex或WorkBuddy创建独立分支执行
        ↓
执行者提交结果文件与Agent执行反馈v2
        ↓
执行者创建PR并在父/子Issue评论回传
        ↓
GPT进行证据验收
        ↓
通过后关闭子Issue并推进下一阶段
```

### 禁止事项

- 不在本蓝图或子Issue中放置自动调度块；
- 不因GitHub评论出现任务文字而自动执行；
- 不把本地其他工作区结果冒充当前任务分支结果；
- 不输出密钥、Token、Cookie、密码或完整敏感连接串；
- 不启动、停止、安装或修改服务，除非对应Issue明确授权；
- 不接触真实交易与券商权限。

## 四、阶段与责任边界

### 阶段A：静态线索发现

推荐执行者：Codex

模式：`【Codex模式：目标模式】`

原因：目标明确，是从真实目录和配置中提取候选地址与项目关系；具体路径未知，需要逐层只读排查。

只允许读取：

- README、文档、配置、`.env.example`；
- JSON、YAML、TOML、INI；
- BAT、CMD、PowerShell、Shell；
- Docker Compose、package.json、pyproject、requirements；
- 启动日志、历史报告、MCP和Agent配置；
- URL、端口、协议、框架和数据库关键词。

输出候选表：

| candidate_id | address_masked | protocol | evidence_path | evidence_type | associated_project | confidence | runtime_check_needed |
|---|---|---|---|---|---|---|---|

阶段A不得检查或改变当前进程，不得主动请求候选服务。

### 阶段B：运行态与端口验证

推荐执行者：WorkBuddy

模式：`【WorkBuddy模式：现场只读核验】`

原因：任务依赖Windows本机端口、进程、服务状态、文件权限与本地网络环境，WorkBuddy更适合做真实环境核验。

输入必须来自阶段A已验收的候选清单。允许：

- 检查监听端口；
- 建立端口到进程、可执行文件、工作目录的映射；
- 对本机候选地址执行安全、只读、低频健康检查；
- 检查公开API文档、`/health`、`/docs`、MCP握手或Web标题；
- 记录服务未运行时的启动入口，但不得自行启动；
- 识别数据目录是否存在及其类型，但不得读取敏感内容。

阶段B不得遍历无关端口，不得暴力探测，不得修改防火墙、服务和启动项。

### 阶段C：证据合并与复用评估

推荐执行者：Codex

模式：`【Codex模式：项目计划模式】`

原因：需要结合阶段A/B证据、Issue #21新架构、现有第二大脑与交易系统边界，形成可更新的迁移和复用计划，仍存在能力与依赖未知项。

必须将每个候选归类为：

- `REUSE_AS_IS`：可直接复用；
- `WRAP`：保留原服务，通过适配层接入；
- `MIGRATE`：数据或能力迁移到新架构；
- `ARCHIVE`：只保留历史数据或文档；
- `DEPRECATE`：停止使用；
- `UNKNOWN`：证据不足。

必须说明：

- 与GitHub、Supabase、MCP、RAG、向量库、第二大脑长期记忆和交易系统只读接口的关系；
- 数据迁移风险、权限风险、版本风险与回滚方案；
- 下一阶段可执行任务清单；
- 未确认项和需要用户批准的事项。

## 五、统一结果目录

所有交付进入：

```text
coordination/RESULTS/SECOND-BRAIN-LEGACY-BACKEND-DISCOVERY-0003/
├── A-STATIC-DISCOVERY/
│   ├── LEGACY-BACKEND-STATIC-DISCOVERY.md
│   ├── CANDIDATE-ENDPOINTS.yaml
│   └── CODEX-FEEDBACK.yaml
├── B-RUNTIME-VERIFICATION/
│   ├── LEGACY-BACKEND-RUNTIME-VERIFICATION.md
│   ├── ENDPOINT-RUNTIME-STATUS.yaml
│   └── WORKBUDDY-FEEDBACK.yaml
└── C-SYNTHESIS/
    ├── LEGACY-BACKEND-DISCOVERY-REPORT.md
    ├── LEGACY-BACKEND-REUSE-DECISION.yaml
    ├── MIGRATION-AND-ADAPTER-PLAN.md
    └── CODEX-FEEDBACK.yaml
```

执行者不得覆盖前一阶段原始结果。发现修订时，采用新版本并保留变更说明。

## 六、证据等级

每条结论必须标记：

- `VERIFIED_FACT`：已由文件、命令或实际响应直接证明；
- `PARTIAL_EVIDENCE`：有支持但覆盖不完整；
- `INFERENCE`：基于多个证据推断；
- `UNVERIFIED`：尚未验证；
- `CONTRADICTED`：已有反证。

候选地址展示时必须脱敏查询参数、用户名、密钥和敏感路径。安全的本机地址和端口可以保留，但不得连带输出凭证。

## 七、提交与PR规则

每个阶段必须：

1. 从最新可用基线创建独立分支；
2. 仅修改本阶段结果与反馈文件；
3. 提交命令、证据边界、失败尝试和未确认项；
4. 提交Agent执行反馈v2；
5. 创建独立PR并关联父Issue和当前子Issue；
6. 不自行合并；
7. 等待GPT验收。

推荐分支：

```text
codex/legacy-backend-static-discovery-0003a
workbuddy/legacy-backend-runtime-verification-0003b
codex/legacy-backend-synthesis-0003c
```

## 八、统一回传格式

```yaml
DeliveryReport:
  task_id:
  parent_issue: 22
  child_issue:
  agent_id:
  mode:
  branch:
  pr_number:
  base_head:
  final_head:
  status: COMPLETED | PARTIAL | BLOCKED | FAILED
  completion_ratio:
  verified_facts:
  changed_files:
  commands_and_tests:
  evidence_boundary:
  failed_attempts:
  unexpected_findings:
  risks:
  rollback:
  next_best_action:
  user_approval_needed:
```

## 九、验收门禁

### 阶段A通过条件

- 有候选地址清单或明确的“未找到”证据；
- 每个候选绑定文件路径和证据类型；
- 没有输出敏感凭证；
- 没有运行态修改；
- Agent反馈v2完整。

### 阶段B通过条件

- 只核验阶段A候选；
- 端口、进程、工作目录、响应状态形成证据链；
- 未运行服务没有被擅自启动；
- 健康检查安全且低频；
- Agent反馈v2完整。

### 阶段C通过条件

- A/B证据可追溯；
- 候选均有复用分类和依据；
- 与Issue #21及现有系统边界清晰；
- 有迁移、适配、回滚和下一步计划；
- 未知项未被伪装成事实。

## 十、与Issue #23的关系

Issue #23 多智能体博弈引擎继续保持排队状态。阶段A和B完成后即可判断旧第二大脑服务是否能承担知识检索、证据账本、Agent记忆或仿真结果存储接口；阶段C通过后，再由GPT决定Issue #23的正式启动顺序和接入方式。
