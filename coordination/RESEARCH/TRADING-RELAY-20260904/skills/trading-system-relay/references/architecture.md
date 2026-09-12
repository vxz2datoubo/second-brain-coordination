# 三方协作与可运行交付架构

agent_id: CODEX | 2026-09-04 | CANDIDATE / research_only / NO_TRADE

## 1. 结论与适用范围

采用现有“一个项目集、两个产品、一个受控联动层”。GPT 管方向，Codex 把方向编译成架构、接口和验收，WorkBuddy 实现和维护本地运行；LLM 是研发与解释参与者，确定性软件承担计算。Codex 不可用时，GPT 承担详细架构职责，WB 继续实现，验收标准不下降。

本文件是用户新请求的候选增补，不覆盖受保护蓝图，不领取其他活动任务，不新增权威调度器。GitHub 当前 CODEX 活动路由属于电影项目，不能用本交易研究任务篡改它。正式排入 WB 工作队列必须由现有 GPT 控制面发布匹配的任务/租约，而不是仅靠本文件赋权。

## 2. 已核实资产与连接点

以下路径以 `vxz2datoubo/second-brain-coordination` 为根。检查基线 `04124e233dc813cca4054851ef6a470b342d82fe`，不代表未来最新版本。

| 资产 | 当前证据边界 | 本次处理 | 下一验证 |
|---|---|---|---|
| `coordination/BLUEPRINTS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-PROGRAM-CHARTER-v1.4.md` | 已读章程，AMED 已定义 | REUSE 治理边界 | 后续任务带六层意图合同 |
| `coordination/ACTIVE-{CODEX,WORKBUDDY}-TASK.yaml` 及路由/租约 | 已有控制面，不是空项目 | REUSE，当前路由不改 | 新任务 exact head 与 lease 一致 |
| `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-1` | 已有基础合同 | REUSE | 在正式集成中运行合同测试 |
| 同项目 `PHASE-2-OFFLINE-VERTICAL-SLICE` | 已有真正 Python 研究引擎、合成样本、测试 | WRAP：此次证明运行的唯一引擎 | 两进程、跨环境结果一致 |
| 同项目 `PHASE-3-LOCAL-ADAPTER-IMPLEMENTATION` | 仓库代码/历史交付可见，非本机实时验证 | REUSE 接口，能力待新证据 | WB 许可明确后的只读适配测试 |
| 同项目 `PHASE-3-INTEGRATED-OFFLINE-MEMORY` | 既有 W3 候选知识入口 | REUSE，不另造知识库 | LearningPacket 幂等、来源、查询闭环 |
| `coordination/BLUEPRINTS/EPISTEMIC-KNOWLEDGE-STATE-FRONTIER-MAPPING-BLUEPRINT-v1.0.md` | 已有四层认知映射 | REUSE，仅新增交易场景 crosswalk | 用户纠正可覆盖推断，UNOBSERVED 保留 |
| 本地 `F:\aidanao\brain_core\market_observation_capture.py`、`mcp\tdx_live_bridge.py`、`mcp\westock_bridge.py` | 路径存在且部分未提交；本次未调用/审计能力 | ADAPT 候选，不复制到公开仓库 | WB 提供字段、许可、时效、失败回执 |
| 本地 `交易系统\SKILL-CATALOG.md` | 历史目录自报 78 技能，不能当运行器数量 | REFERENCE_ONLY | 每技能绑定 runner/测试/数据依赖 |
| 本地 `docs\workbuddy_trading_system_mapping.md` | 旧 WB 业务权威映射含代理限制 | 保留历史语义；用户本次更新职责分配 | GPT 发布治理增补，勿让职责变更改变指标定义 |

本次新建只限接力技能、固定数值合同、薄验证包装和公开合成 CI。没有另造行情、订单、风控、知识或任务权威。

## 3. 五个运行位置

```text
USER ──方向/资金/风险最终决定── GPT
                                │ 版本化设计、研究假设
                                ▼
GitHub：任务 / 蓝图 / 源代码 / 审核 / 发布清单 / 公开安全回执
   │             ▲                        │
   │精确版本     │测试、结果摘要           │批准的发布版本
   ▼             │                        ▼
隔离研究 runner（本地或云）       WB 本地部署管理
   │既有 P2/P3 程序                        │
   └──ContextBundle / LearningPacket──► 第二大脑 W3 候选入口
                                          │
授权行情端 ─► WB采集服务 ─► 本地不可变数据 ─► 确定性研究运行器
                                          │
                                 校验/规则/回放/风控
                                          │
                                    NO_TRADE 闭锁
```

GitHub 是版本与协作中心；GitHub Actions runner 才是云端计算机。普通文件读取、网页看到结果、语言模型描述策略、真实运行程序是四种不同证据。

## 4. 本地目录与安装合同

开发 worktree 只在 `F:\aidanao-worktrees\<任务名>`。不在母系统脏分支直接更新。

WB 后续受控安装目标为母系统内 `F:\aidanao\交易系统\runtime\`，这是部署输出，不是新的 Git worktree。该目标为提案，本次不安装守护服务：

```text
交易系统/
  SKILL-CATALOG.md                 既有文件，保留
  runtime/
    releases/<commit-sha>/         只读发布包，校验依赖和清单
    current.json                   唯一部署指针，原子更新
    config/                        非敏感本机配置；凭证外置
    data/raw/<source>/<date>/       授权原始修订，只追加
    data/normalized/               标准化数据及血缘
    runs/<run-id>/                  固定输入、参数、输出、回执
    state/                         检查点、进程锁、投递队列
```

发布包必须包含 CLI、引擎、合同、合成样例、依赖锁、哈希清单、安装/停止/回滚说明，不能只下载 Markdown。WB 从批准 SHA 导出到新的 release 目录，验证后切换指针。工作中不 `git pull` 改写运行代码。失败回滚到上一已验证版本，未完成运行继续绑定原版本。

同一 GitHub repo 足以完成当前验证，无需马上拆仓；真实行情与本机状态不纳入公开 repo。私有存储/对象存储可扩展，但先评估已有能力和许可，不自动采购。

## 5. 接力状态机与部门交付

`PROPOSED → SPECIFIED → CLAIMED → IMPLEMENTED → EXECUTOR_VERIFIED → INDEPENDENTLY_REVIEWED → RELEASED → LOCALLY_VERIFIED`。

失败进入明确的 `BLOCKED/FAILED/REVALIDATION_REQUIRED`，不能跳门。状态由现有 route/claim/review 对象承载，本技能仅解释并校验。

| 部门/责任 | 输入 | 输出 | 接收者/验收 |
|---|---|---|---|
| GPT 架构治理 | 用户目标、现有权威、研究反证 | 有版本设计、验收、预算、允许路径 | Codex/WB 检查可实现性 |
| Codex 工程架构 | 设计及依赖 | 合同、薄原型、错误处理、可复现测试 | WB 按精确 SHA 实现，GPT 审核 |
| WB 数据与运维 | 授权来源、已批准代码 | capability receipt、采集 manifest、本机运行回执 | 数据校验器先验语义，GPT 看摘要 |
| 研究与策略 | PIT 数据、事前假设、规则包 | 候选信号、试验族、样本外结果/反证 | 验证门，不直接写正式策略 |
| 独立验证与风控 | 同一输入与候选版本 | 通过/拒绝/弃权及理由 | 发布治理；不得自验自批 |
| 第二大脑 W3 | 脱敏候选结果、来源、未知 | 可追溯知识、检索上下文 | GPT 学习，不能覆盖行情事实 |
| USER | 审计结果、风险解释 | 高影响决定 | 所有 Agent 的授权上限 |

每交接必须关联 `task_id, source_agent, target_agent, reviewer, review_status, source_commit, spec_hash, input_manifest_hash, parameter_hash, allowed_paths, commands, evidence_refs, unknowns, next_action`。长任务写安全检查点；模型额度耗尽时保存失败和已完成步骤，下一执行者先重验输入与租约，不重新解释一切也不继承未经验证的完成声明。

角色可替换，证据合同不变。GPT 做设计时也不能把自己的设计称为独立验收。共享 GitHub 账号只说明账号相同；agent_id 是声明，不是密码学证明。更强身份需独立工作负载身份或审计见证，列为后续改进。

## 6. 同步、故障和成本

- 代码：按批准版本更新；任务/回执：事件触发，失败进入本地 outbox；行情：由本地授权连接按所需周期采集。禁止每个 tick 都 commit。
- 接力消息幂等键：任务 ID + 输入内容哈希 + 目标步骤。重复交付可读回旧结果；新内容必须新运行。实际锁/租约继续复用现有治理内核。
- Webhook 可重复、乱序；使用版本比较与幂等，不假设 exactly-once。断网期间本地写盘，恢复后按序补安全摘要；GitHub 不可用时不影响已批准离线运行。
- 采集器断线：记录缺口、停止依赖新鲜行情的信号、重连后去重并重核时间。不能用缓存冒充实时。
- LLM 全不可用：确定性回放仍运行；解释、研究提案暂停。额度恢复后从回执接力。没有授权 runner 的 GPT 降为只读评审。
- 每个任务记录产品/实际模型 ID、输入输出用量（可得时）、耗时、失败重试、实际账单或 UNKNOWN、验收结果。以“每个通过验收任务总成本”比较模型，不依据单价传言绑定供应商。
- 首期只要求单机可恢复，不声称企业 HA。候选服务目标：任务摘要同步 P95 ≤60 秒、研究 RTO ≤15 分钟、元数据 RPO ≤60 秒；这些不是已达到的承诺，需 WB 测试校准。实时行情延迟预算依策略频率单独批准，不能沿用这三个数。

## 7. 分阶段验收与下一任务

| 门 | 要证明什么 | 本次/后续 |
|---|---|---|
| G0 | 仓库、基线、职责、已有模块已定位 | 本次现场核对 |
| G1 | 既有程序在本地真实执行，固定合成输入重放一致，防护有效 | 本次执行 |
| G2 | 同一 SHA 在 GitHub runner 执行并可下载回执，跨系统比较 | 本次 CI 验证；结果另见执行报告 |
| G3 | 用户实际 GPT 会话读取精确版本并通过可用工具触发/关联真实运行 | 本次提供挑战协议，不能用 Codex 代测冒充 |
| G4 | WB 在指定目录按发布清单安装、停止、重启、回滚；无 LLM 仍可回放 | 后续 WB 任务，尚未部署 |
| G5 | 一条有明确许可的行情路径 → PIT → 既有引擎 → W3 候选包 | 后续受控数据准入，不以合成结果代替 |
| G6 | 历史回测/前瞻影子、成本和周期稳健性验证 | 仍属研究；收益不预设 |
| G7 | 任何实盘接入 | 当前禁止，独立用户审批和规则/券商核查 |

WB 最小任务：先 G4（纯合成，无采集，无账户），回传精确版本、发布包清单、Python/编码、两次执行哈希、重启/回滚、断网与 LLM 不可用测试；随后才为 G5 提交字段级能力及许可证据。GPT 应将此候选任务与当前 WB 活动队列协调后发布；本次不抢占。

## 8. 本轮失败、发现与限制

裸 `python` 在 Windows 默认 GBK 下运行既有 P2 测试：163 项中 19 项发生 UTF-8 文件解码错误。处理是为验证入口显式添加 `-X utf8`，不修改原引擎。具体复测结果见执行报告。

首要缺口是运行交付一致性，不是更多策略。既有引擎内部 `code_version` 是文本标签，外层增加真实 commit + 源码哈希绑定。哈希不能证明金融字段正确，不能证明真实身份，也不能代替独立 review。

未经核实项：用户实际 GPT 产品面与可用工具；WB 实际模型/版本/费用；实时端权限与许可；全量安装依赖；当前真实数据质量与策略效益。对应 owner 分别为 GPT 会话、WB、WB 数据审计、WB 发布管理、研究验证部门。
