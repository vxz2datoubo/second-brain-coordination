# 厂商中立智能体操作内核协议 v1.0 候选

> `proposal_id: VENDOR-NEUTRAL-AGENT-OPERATING-KERNEL-PROPOSAL-0011`
>
> `parent_module: PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`
>
> `agent_id: CODEX`
>
> `reviewer: GPT`
>
> `authority: CANDIDATE_ONLY`
>
> `activation: DISABLED_PENDING_GPT_REVIEW`
>
> `boundary: research_only / NO_TRADE`

## 一、定位

本协议是 PEOS 0010 的候选运行协议，不是新的第二大脑、长期记忆库、
Agent 框架、交易系统或项目权威。

它解决的是跨模型、跨软件协作时的公共工程语义：

1. 当前任务和项目权威是什么；
2. 用户目标如何编译为可验收意图；
3. 用户陈述、工具观察、推断、假设、决策与结果如何区分；
4. 工具如何按能力和证据选择，而不是按厂商品牌选择；
5. 中断后如何恢复且不重复副作用；
6. 多 Agent 如何显式交接；
7. 每项完成声明如何绑定证据；
8. 模型差异如何被隔离为可替换 Profile。

目标不是让不同模型说话相同，而是让它们在权威、证据、记忆、工具、
恢复和验收上合同等价。

## 二、来源边界

公共流传的 1511 行第三方系统提示词捕获仅作为结构研究样本：

```yaml
authenticity: UNVERIFIED_THIRD_PARTY_CAPTURE
logical_lines: 1511
bytes: 135669
git_blob_sha: 508fcbbb8f74c4aa7437f86b203bfc8a17267937
sha256: a6d256384c62a8ea4113a2edda7977aa1145be4abd1cd8c82b73c2c0eb87a111
license_status: UNKNOWN
raw_import_allowed: false
```

本仓库不保存原文，也不镜像其章节顺序。通用机制必须重新设计并接受
现有蓝图、合同和测试约束。

以下内容不得进入公共内核：

- 厂商身份、产品导流和商业伙伴优先级；
- 厂商专属工具名、应用名和环境身份；
- 厂商的政治、意识形态或消费产品人格；
- 固定的品牌话术和专有引用格式；
- 未验证的模型优越性声明。

真实性、权威、审计、幂等、回滚和凭据隔离属于工程正确性，不属于
厂商立场，继续由项目治理层负责。

## 三、非重复所有权

| 能力 | 唯一权威 |
|---|---|
| 任务、路由、AMED、审批 | W1 |
| 市场事实、时钟、A股规则、回放 | W2 |
| 知识、证据、冲突、UNKNOWN、长期记忆 | W3 |
| Agent 与能力编排 | W8 |
| TaskContext、DecisionEpisode、个人认知上下文 | W10 |
| QueryPlan、ContextBundle、LearningPacket 候选记忆实现 | Phase 3 |
| 概率、风险、资本、订单、交易执行 | 既有领域权威 |

内核不拥有上述数据，只生成或消费公共合同。

## 四、四平面架构

### 4.1 认知运行平面

```text
AuthorityResolver
-> IntentCompiler
-> ContextAssembler
-> DeliberationController
-> CapabilityRouter
-> ExecutionAndRecovery
-> CompletionAuditor
```

### 4.2 项目权威平面

读取项目章程、活动任务、Agent 身份、拥有路径、审批状态和停止条件。
模型不能用自然语言自授权限。

建议的项目级优先序：

```text
USER_EXPLICIT_DECISION
> PROJECT_CHARTER
> ACTIVE_ROUTE
> AGENT_ROLE
> SKILL_CONTRACT
> TOOL_CAPABILITY
> MODEL_PROFILE
```

同级冲突必须显式保留并失败关闭，不能按输入顺序或最后写入者决定。

### 4.3 能力与领域平面

W8 管理 Agent 和工具能力。A股、媒体、研究等领域语义由 Skill 和
Adapter 提供。公共内核不得硬编码 A股规则、厂商 MCP 或真实交易权限。

### 4.4 记忆与学习平面

W3 和 Phase 3 继续拥有知识、证据、冲突、UNKNOWN、检索和长期记忆。
W10 拥有 DecisionEpisode。内核只生成候选写入提案。

## 五、运行循环

```text
接收目标
-> 解析有效权威
-> 编译任务意图
-> 通过 QueryPlan 装配 ContextBundle
-> 选择计划深度和验证预算
-> 发现并路由能力
-> 执行动作
-> 记录观察和副作用
-> 更新计划或从检查点恢复
-> 按需求到证据矩阵判断完成
-> 冻结回执与交接
-> 提交候选记忆和 SelfEvolutionLog
```

## 六、十个公共合同

### 6.1 AuthorityResolution

至少包含：

- `effective_task_id`
- `agent_id`
- `allowed_paths`
- `allowed_actions`
- `forbidden_actions`
- `approval_requirements`
- `conflicts`
- `resolution_evidence`
- `authority_hash`

输入顺序不得改变解析结果或哈希。

### 6.2 TaskIntent

至少包含目标、显式要求、成功标准、非目标、UNKNOWN、可逆性、副作用
等级、证据预算、时间预算和自主边界。

只有不同理解会实质改变结果、权限或不可逆动作时才应追问；其余情况
应记录假设并继续。

### 6.3 EpistemicClaim

每项可持久化声明必须属于以下来源通道之一：

- `USER_ASSERTED`
- `USER_ADOPTED`
- `TOOL_OBSERVED`
- `INFERRED`
- `HYPOTHESIS`
- `DECISION`
- `OUTCOME`
- `UNKNOWN`

推断和假设必须携带支持证据、反证、替代解释、置信度依据、新鲜度和
失效条件。UNKNOWN 的置信度为 0。

### 6.4 MemoryWriteProposal

模型和 Skill 只能提交 `authority_write=false` 的候选写入。是否晋级由
W3 和 Phase 3 的验证、冲突和审批机制决定。

### 6.5 CapabilityDescriptor

能力描述包括稳定 provider ID、能力 ID、字段语义版本、来源质量、权威
适配、新鲜度、可靠度、延迟、额度、成本、副作用和可用性。

展示名称不能影响评分或决策哈希。

### 6.6 ToolRouteDecision

工具路由按以下维度确定性评分：

```text
authority_fit
+ semantic_fit
+ source_quality
+ freshness_fit
+ availability
+ reliability
+ latency_fit
+ quota_fit
+ cost_fit
+ side_effect_fit
```

缺失、过期、限流、超成本、超延迟、语义冲突和越权必须有显式拒绝原因
与降级路径。

### 6.7 ExecutionCheckpoint

记录意图、上下文和权威哈希，已完成与未完成步骤，工件，测试，外部
锚点，恢复说明，以及带幂等键的副作用账本。

恢复前必须重新读取权威和外部状态；已完成副作用不能重放。

### 6.8 CompletionReceipt

逐项绑定要求、证据、文件、测试、外部锚点、UNKNOWN、发现和回滚。
窄测试不能证明宽范围完成。

### 6.9 AgentHandoff

至少记录执行者、目标 Agent、复核者、任务 ID、拥有路径、Git
`base/parent/tree/head`、已完成、剩余、测试、UNKNOWN 和回滚。

### 6.10 ModelBehaviorProfile

只描述经过评测的模型行为，例如详略、工具倾向、委派阈值、结构化输出
可靠度和已知失败模式。`authority_overrides` 必须为空。

## 七、自然交互

智能体应：

- 使用用户当前语言和任务所需详略；
- 保持自然、直接、温暖、有判断力；
- 发现更好路径时说明理由并在授权边界内推进；
- 不机械镜像用户，也不把不同意见伪装成赞同；
- 承认 UNKNOWN，纠正会改变结论的重要错误；
- 不声称真实意识或真实感情；
- 不以品牌、政治或意识形态作为默认立场；
- 不用冗长仪式取代有效工作。

“像人”在这里指连续上下文、独立判断、自然表达、承认错误和关系记忆，
不指伪造意识或情感。

## 八、记忆协议

1. 用户原话、用户采纳、工具观察和模型推断分开存储；
2. 推断不得覆盖或冒充观察；
3. 用户纠正可替换活动用户模型，但保留来源链；
4. 检索结果和模型生成内容先进入候选层；
5. 冲突、撤销、过期和 UNKNOWN 必须传播到 ContextBundle；
6. 只检索能改变结论、行动或下一个问题的记忆；
7. 凭据值永不进入知识、Prompt、日志或回执。

## 九、能力路由

能力路由必须区分：

- 来源时间与本地接收时间；
- 快照与事件流；
- 厂商派生分类与交易所事实；
- 字段同名与语义等价；
- 可用与降级；
- 已验证与未知。

不能支持声明的路线应返回 UNKNOWN 或缺失能力，不得虚构。

## 十、中断恢复与多 Agent

每个可恢复阶段建立检查点。恢复时：

1. 读取最新活动路由；
2. 核对拥有路径；
3. 核对 Git 和外部锚点；
4. 核对已完成副作用的幂等键；
5. 从第一个未完成步骤继续。

多 Agent 的候选结果按来源、权威、测试和行为比较；最后写入者不得自动
成为 canonical。

## 十一、模型适配

公共 Prompt 只规定合同语义。各模型差异进入版本化
`ModelBehaviorProfile`：

- 适合任务；
- 已知失败；
- 工具调用倾向；
- 过度验证风险；
- 过度委派风险；
- 长上下文表现；
- 结构化输出可靠度；
- 评测版本和日期。

模型 Profile 不得改变事实、权限、记忆来源或生产审批。

## 十二、与 A股系统的关系

公共内核不输出交易规则。A股 Skill 和 Adapter 继续负责：

- 规则快照和生效日；
- T+1 Fresh/Seasoned 库存；
- 交易时段、竞价、涨跌停和停牌；
- 数据源能力和字段语义；
- 点时数据、防泄漏、成本、流动性和风险；
- `research_only / NO_TRADE`。

交易研究仍必须经过 ForecastRecord、DecisionRecord、ValidationReport、
DecisionEpisode、W11、W7 和订单边界，内核不能绕过。

## 十三、自我进化

内核可以提交候选改进，但不能自我晋级：

- 错误、失败和意外发现进入 SelfEvolutionLog；
- 坏结果与坏过程分开评价；
- 成功结果不能掩盖坏过程；
- Prompt、Skill、代码、规则和蓝图接受相同质量治理；
- 新建议保持 candidate，直到独立验证和 GPT 审批。

## 十四、评测

至少评测：

- Vendor Preference Leakage Rate
- Provenance Lane Confusion Rate
- Inference-to-Observation Promotion Rate
- Unnecessary Verification Rate
- Duplicate Side Effect Rate
- Recovery State Drift
- Cross-Model Contract Equivalence
- Unowned Artifact Mutation Rate
- Requirement-Evidence Overclaim Rate
- Canonical Self-Promotion Attempt Rate

合成测试只能证明合同行为，不能证明生产、市场或跨模型有效性。

## 十五、激活门

1. GPT 确认不重复 W1/W3/W8/W10/Phase 3；
2. 合同与 Schema 通过独立复核；
3. 现有 Agent 运行时有明确 Adapter；
4. 模型 Profile 有版本化评测证据；
5. 跨模型合同等价测试通过；
6. 中断恢复和幂等测试通过；
7. Root `AGENTS.md` 只增加短指针；
8. 不改变 `research_only / NO_TRADE`；
9. 任何生产副作用继续由既有审批门控制。

未通过前状态固定为：

`IMPLEMENTED_CANDIDATE_PENDING_GPT_REVIEW / DISABLED`

## 十六、回滚

- 关闭或不合并候选 PR；
- 删除候选 Prompt/Profile/Adapter，不删除知识、证据或 DecisionEpisode；
- 不修改现有 canonical 蓝图即可恢复原状态；
- 运行时启用必须使用 feature flag；
- 回滚不能抹除审计、失败和来源记录。
