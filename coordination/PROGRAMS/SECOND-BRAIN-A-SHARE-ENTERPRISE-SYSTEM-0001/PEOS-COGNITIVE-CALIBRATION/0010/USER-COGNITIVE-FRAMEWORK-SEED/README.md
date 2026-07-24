# 用户认知框架种子项目 v0.1

> status: `RESEARCH_INPUT / NON_CANONICAL / USER_REVIEW_REQUIRED`
>
> parent_module: `PERSONAL-EPISTEMIC-COGNITIVE-OPERATING-SYSTEM-0010`
>
> parent_issue: `#61`
>
> related_issues: `#38 / #59 / #60 / #63 / #72`
>
> boundary: `research_only / NO_TRADE`
>
> privacy: `PUBLIC_REPO_SAFE_ABSTRACTION_ONLY`
>
> evolution_status: `QUEUED_BLUEPRINT_INPUT / NON_BLOCKING / NO_WIP_EXPANSION`
>
> autonomous_capture: `ENABLED_WITH_PRIVACY_AND_REVOCATION_GATES`

## 1. 项目目的

本目录不是新建第二套个人模型，也不是新的平行记忆运行时。它是 PEOS W10 的**用户认知框架研究输入区**，用于把聊天中形成的认知观察、知识掌握、能力边界、未知区域、思维优势、潜在盲点和学习路线，整理成可版本化、可检索、可争议、可修正的结构化材料。

系统最终需要回答五类问题：

1. 用户目前在哪些领域知道什么；
2. 用户对这些知识掌握到什么层级；
3. 用户在哪些推理或决策环节表现较强；
4. 用户的知识、能力、证据或方法缺口在哪里；
5. 下一步怎样补足缺口，并把新认知回写到长期模型。

核心目标不是给用户贴固定人格标签，而是建立一个持续演化的认知地图。

## 2. 与现有第二大脑架构的关系

本目录服从现有权威边界：

- Issue #59：知识原子化、证据链、冲突与 UNKNOWN；
- Issue #60：长期混合检索、时间版本、记忆宫殿；
- Issue #38：知识网关与 canonical 运行时；
- Issue #61：PersonalCognitiveModel、DecisionEpisode 与元认知校准；
- Issue #63/#72：共享接口、决策生命周期和企业级权威冻结。

因此，本目录只提供：

- 研究输入；
- 候选认知观察；
- 候选知识掌握度；
- 学习与验证任务；
- 未来 canonical 合同的样例数据；
- 不抢占现有排期的蓝图回写候选。

本目录不提供：

- 第二套事实源；
- 自动人格判决；
- 真实交易行动；
- 对外部世界事实的无证据修改；
- 未经用户确认的永久特质结论；
- 对当前 Codex/WorkBuddy active route 的插队或资源抢占。

## 3. 认知框架的基本对象

### 3.1 CognitiveObservation

一次具体对话、行为或任务中观察到的现象。单次出现只能形成 Observation，不得直接升级为稳定特质。

### 3.2 CognitiveClaimCandidate

由一个或多个 Observation 提炼出的候选判断，例如：

- 用户能够自然识别“局部最优不等于整体最优”；
- 用户对系统论已有较强直觉，但缺少正式术语和数学工具；
- 用户倾向用真实运行结果而非舆论声量评价治理机制。

候选判断必须附支持证据、反向证据、适用领域、置信度和失效条件。

### 3.3 KnowledgeMastery

使用分阶段掌握度：

`UNKNOWN → HEARD_OF → RECOGNIZES → CAN_EXPLAIN → CAN_APPLY_WITH_SUPPORT → CAN_APPLY_INDEPENDENTLY → CAN_TRANSFER → CAN_CRITIQUE → CAN_TEACH → CALIBRATED_MASTERY`

### 3.4 CognitiveGap

缺口不只等于“不知道”，至少包括：

- 术语缺口：已有直觉，但不知道学科名称；
- 形式化缺口：能讲道理，但不能建模或量化；
- 证据缺口：观点合理，但缺少数据或研究支持；
- 迁移缺口：在一个例子中会用，换情境后不稳定；
- 反例缺口：不能识别理论何时失效；
- 校准缺口：自信程度和真实能力不匹配；
- 执行缺口：知道正确方法，但不能稳定执行。

### 3.5 UnknownRegistryEntry

记录：

- 已知未知；
- 未知但被对话暴露出的未知；
- 目前无法验证的假设；
- 需要外部领域专家、数据或实验才能解决的问题。

## 4. 四象限认知地图

认知框架至少要区分：

| 区域 | 含义 | 系统动作 |
|---|---|---|
| 知道且知道自己知道 | 已掌握且能说明边界 | 迁移、教学、挑战性验证 |
| 知道但不知道自己知道 | 直觉或能力已出现，但缺少术语和自觉 | 点拨、命名、结构化 |
| 不知道且知道自己不知道 | 已明确的学习缺口 | 建立学习任务和验证路径 |
| 不知道且不知道自己不知道 | 对话、失败或反例暴露的新盲区 | 元认知提示、UNKNOWN 登记 |

用户明确希望系统重点帮助发现后两类，尤其是“说出来后仍未必能意识到”的隐藏前提、盲点、相邻理论和潜在后果。

## 5. 未来聊天的更新闭环

```text
原始对话或任务
→ 识别情境、观点、证据、假设和情绪状态
→ 生成 CognitiveObservation
→ 检索历史支持与反向证据
→ 形成 Candidate Claim / Gap / Mastery Update
→ 用户查看、纠正或否决
→ 版本化写入长期模型
→ 到期复审、衰减、冲突或撤销
```

显式触发词包括但不限于：

- “记忆采集”
- “知识框架采集”
- “双重采集”
- “把这个录入记忆系统”
- “把这个放进知识框架”

显式触发不代表可以跳过证据、隐私分类和用户撤销权，只代表该内容应进入对应的候选写入流程。

## 6. 检索目标

未来应支持以下检索：

- 按主题：系统论、控制论、传播治理、交易决策；
- 按掌握度：哪些概念只听过，哪些能独立应用；
- 按缺口：术语、形式化、证据、迁移、反例、执行；
- 按时间：某项认知如何形成和变化；
- 按证据：哪些判断来自用户确认，哪些只是模型推断；
- 按任务：当前问题需要调用用户哪些强项、规避哪些薄弱环节；
- 按关系图：某个观点连接了哪些理论、案例和决策经验。

## 7. 隐私与公开边界

当前仓库为公开仓库，因此本目录只保存**经过抽象化、适合公开的认知材料**：

- 不保存原始亲密对话；
- 不保存私人身份、联系方式、账号、凭据或精确生活轨迹；
- 不保存未经用户同意的敏感经历；
- 不把角色扮演内容混入真实用户画像；
- 需要保留的私人原始证据应进入本地、加密或权限受控的正式记忆层。

## 8. 蓝图融合与未来实施节奏

本方向已登记为 PEOS/W10 的蓝图回写候选，但**不立即启动实现，也不改变现有 Agent 节奏**。

未来实施原则：

```text
先完成原有 active route
→ 在自然排期点做非重复建设审计
→ 复用 W3/W10/W9 现有合同和运行时
→ 从只读、可纠正的最小切片开始
→ 验证后再逐步扩充
```

角色边界：

- **Codex**：未来负责 canonical schema、服务边界、版本迁移、接口和有界实施计划；
- **WorkBuddy**：未来负责本地数据接入、隐私隔离、真实检索、运行验证、UI 流程和负向测试；
- **QCLAW**：只负责知识学习、研究消化、术语、证据、反例和学习材料支持，不承担本系统工程实施或运行时所有权；
- **GPT + 用户**：负责认知点拨、候选提炼、用户复审、方向控制和最终验收。

详细内容见：`BLUEPRINT-INTEGRATION-AND-CONTINUOUS-EVOLUTION-PLAN.md`。

## 9. 当前交付文件

- `CURRENT-COGNITIVE-SNAPSHOT-v0.1.md`：当前认知强项、缺口和未知；
- `DISCUSSION-2026-07-25-SYSTEMS-FEEDBACK-GOVERNANCE.md`：本次系统论与治理讨论的详细认知记录；
- `COGNITIVE-FRAMEWORK-MODEL-v0.1.yaml`：结构化候选数据；
- `COGNITIVE-UPDATE-AND-RETRIEVAL-PROTOCOL.md`：未来聊天如何持续补充和检索；
- `COGNITIVE-GROWTH-BACKLOG.md`：学习与验证路线；
- `BLUEPRINT-INTEGRATION-AND-CONTINUOUS-EVOLUTION-PLAN.md`：蓝图回写、Codex/WB 实施、QCLAW 限定角色和非抢占式演化路线；
- `SYSTEMS-CYBERNETICS-MECHANISM-GAME-COMPLEXITY-MULTI-AGENT-INTEGRATION-BLUEPRINT.md`：七理论跨系统融合蓝图；
- `THEORY-TO-ENTERPRISE-ARCHITECTURE-INTEGRATION-MAP.yaml`：理论到企业架构的机器映射；
- `DUAL-TRACK-MEMORY-AND-COGNITIVE-FRAMEWORK-PROTOCOL.md`：记忆轨与知识框架轨的边界、口令和自主采集规则；
- `MEMORY-AND-COGNITIVE-CAPTURE-COMMAND-REGISTRY-v0.1.yaml`：机器可读口令和授权注册表；
- `AI_HANDOFF.yaml`：后续 Agent 接力与边界。

## 10. 验收标准

本种子项目满足以下条件才算有效：

1. 能明确区分事实、用户观点、模型解释和待验证假设；
2. 能显示用户认知强项、知识缺口和 UNKNOWN；
3. 能追溯每项候选判断的来源和时间；
4. 能记录反证、冲突和用户纠正；
5. 不因一次聊天形成永久人格标签；
6. 能为后续学习生成可执行任务；
7. 能被 Issue #61 的正式 PersonalCognitiveModel 合同吸收，而不形成平行运行时；
8. 能由 Codex 与 WorkBuddy 在原有节奏下逐步实现，不抢占当前 WIP；
9. QCLAW 保持知识支持角色，不承担工程实现；
10. 每次扩展都通过现有治理、依赖、验收和回滚机制；
11. 记忆系统与知识框架系统使用分离权威、共享来源链接且不复制原始证据；
12. 用户能够用简短口令采集、查看、纠正、撤销和暂停自动采集。

## 11. 双轨采集速查

```text
记忆采集
→ 保存发生过什么、重要约定、共同语境和以后从哪里继续

知识框架采集
→ 分解理解、掌握度、强项候选、缺口、反例和未知未知

双重采集
→ 两条轨道分别生成记录，并使用同一 source_episode_id 连接
```

用户已授权 GPT 在有明显长期价值时自主生成候选并告知，不必每次事前询问。敏感内容、第三方信息、原始亲密对话和公开上传仍需确认或进入私有受控存储。详细规则见双轨协议与命令注册表。
