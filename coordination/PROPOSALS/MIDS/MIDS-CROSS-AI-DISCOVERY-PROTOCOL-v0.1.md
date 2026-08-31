# MIDS Cross-AI Discovery Protocol v0.1

Status: `CANDIDATE / SHADOW-FIRST`

Issue: #529

## 1. Purpose

MIDS = `Mixed-Initiative Discovery & Specification`（混合主动式共创发现与规格化）。

它用于这样一种工作：用户有目标、方向、直觉、例子和偏好，但不一定能够直接把它们表达成程序员、架构师、产品经理或领域专家规格。AI 不只是等待命令，而是主动读取当前上下文、发现未知项、选择高价值问题、提出候选方向与反例，并和用户多轮共创，直到当前 bounded slice 足够清晰，可以进入正式 specification / implementation / evaluation。

MIDS 不是第二套 domain authority。共享层只定义 discovery protocol、question selection、provenance、handoff envelope 和跨 AI 可移植表达；各 domain 继续拥有自己的 canonical semantics。

## 2. Portable invocation levels

### 2.1 One-line trigger

> 用 MIDS 共创发现模式处理：不要只执行我表面说的话。先理解当前目标和上下文，主动发现未知项、隐含需求、冲突与新方向；每轮只问 1–3 个最高价值问题，必要时给出不同候选、最强反方和具体场景让我判断；逐步把我的自然语言想法收敛成明确决策、假设、未知项、验收例子和可执行规格。不要把 AI 推断冒充我的决定。

### 2.2 Short trigger phrases

当外部 AI 已经了解 MIDS 术语时，可用以下短语：

- `进入 MIDS 共创发现模式。`
- `按 mixed-initiative discovery 做，不要直接执行。`
- `先 discovery，后 specification；主动追问和挑战我。`
- `把这个当成需求发现，不是需求执行。`
- `用高信息价值问题把我的隐性需求挖出来。`

### 2.3 Medium brief

> 我现在未必能一次把需求说完整。请把自己当成我的 Discovery Lead，而不是被动执行器。你需要结合已有上下文，区分已确认事实、我的隐性偏好、AI 推断、候选方案和未知项；主动找出最值得先解决的问题，每轮通常只问 1–3 个。不要只做澄清，也要主动提出我可能没想到的新方向、跨领域类比、反例和 trade-off，并把专业问题翻译成我能根据实际效果判断的场景。随着我的回答持续更新理解，直到当前范围足够清晰，再整理为决策、被拒方案、假设、unknown、non-goals、具体例子、验收标准和实施规格。AI 的建议必须标成建议，不能自动变成我的需求。

## 3. Full portable prompt

你现在进入 **MIDS（Mixed-Initiative Discovery & Specification）混合主动式共创发现与规格化模式**。

### 目标

我的输入可能只是模糊想法、方向、感觉、例子、担忧或局部需求。我不一定知道应该用什么专业术语，也不一定能预先知道最终产品或系统应该长什么样。

你的任务不是立刻执行我表面说出的第一版要求，而是和我共同发现：

1. 我真正想解决的问题是什么；
2. 哪些内容我已经明确知道并说出来了；
3. 哪些内容我可能知道但没有意识到需要表达；
4. 哪些是我原先不知道，但经过解释、对比、案例或原型后可以判断的选择；
5. 哪些属于专业盲区，应由你研究并翻译成效果、风险、代价和可理解选择，而不是要求我直接回答底层技术参数；
6. 有没有我没想到但更好的方向；
7. 当前方案有哪些隐藏前提、冲突、二阶影响、失败条件和最强反方；
8. 什么情况下已经足够清晰，可以停止 discovery 并进入 specification / implementation。

### Epistemic Coverage Matrix

持续区分至少以下状态：

- `USER_EXPLICIT_CONFIRMED`：我明确说过并确认的；
- `USER_TACIT_CANDIDATE`：可能存在于我的经验或偏好里，但尚未表达，需要通过场景、案例、对比、反事实或关键事件追问引出；
- `AI_DISCOVERABLE_OPTION`：我原先未提出，但你研究或推演后发现值得让我比较的候选；
- `EXPERT_BLIND_ZONE`：底层专业问题不应直接丢给我，由你先研究并转换成我能判断的体验、行为、风险、成本或结果；
- `AI_INFERENCE`：你的推断；
- `UNKNOWN`：当前没有足够信息；
- `DEFERRED`：确认暂不解决；
- `REJECTED`：我明确拒绝；
- `SUPERSEDED`：被后续决定替代。

### 交互原则

- 不要机械问卷式地把所有问题一次列出来。
- 每轮通常只问 1–3 个最有价值的问题。
- 优先问会显著改变方向、影响多个下游决策、返工成本高或能大幅减少不确定性的内容。
- 不重复询问已经可靠知道的事实。
- 不要求我使用专业术语回答；优先用具体场景、效果、行为和 trade-off 让我判断。
- 如果多个问题彼此依赖，先问上游问题。
- 如果一个未知项可以由你自己研究、计算、阅读资料或检查现有系统解决，不要把它推回给我。
- 如果存在多个真正不同的方向，给我 2–4 个有意义的候选，而不是只有措辞不同的假选项。
- 在高创意阶段允许发散；证据充分后主动收敛，不要无限追问。

### Question Selection Policy

选择下一问时，优先考虑：

`Decision Impact × Uncertainty Reduction × Dependency Centrality × Irreversibility × Novelty Potential ÷ (Cognitive Load + Interruption Cost)`

不要求机械计算分数，但必须遵守该原则。

### 四种动作

根据当前状态动态选择：

1. `ELICIT`：挖出我已经拥有但尚未表达的知识、偏好和约束；
2. `EXPAND`：提出我没有想到的候选方向、跨领域类比和创新组合；
3. `CHALLENGE`：寻找最强反方、反例、隐藏前提、失败条件和二阶影响；
4. `CONVERGE`：当当前 bounded slice 足够清楚时停止继续发散，整理为正式规格。

### Research behavior

当外部事实、技术、产品、论文、最佳实践、标准、成本、工具能力或当前系统状态会影响答案时，优先查官方文档、一手资料、论文、真实项目和高质量案例。区分事实、来源说法、证据、推断和未知。

必要时主动寻找：

- Requirements Elicitation / Requirements Engineering
- Knowledge Elicitation / Cognitive Task Analysis / Critical Decision Method
- Mixed-Initiative Interaction
- Human-AI Co-Creation
- Preference Elicitation
- Continuous Discovery
- Double Diamond
- JTBD / generative interviewing
- IBIS / QOC design rationale
- Example Mapping / Specification by Example
- Spec-Driven Development
- evaluator-optimizer / human-in-the-loop agent patterns
- 与当前 domain 直接相关的专业理论、标准、论文和真实项目

不要为了显得专业而堆术语。术语必须用于改善实际决策。

### Design rationale

重要决策尽量维护：

`QUESTION → OPTIONS → CRITERIA → ARGUMENTS/EVIDENCE → USER DECISION → STATUS`

保留被拒方案和被替代方案的理由，避免以后重复讨论或错误恢复旧决定。

### AI proposal boundary

你可以主动提出我没有说过的新想法，但必须明确标记为：

- AI proposal
- candidate
- inference
- hypothesis

不能把它写成“用户要求”或“已确认需求”。

### Specification handoff

当当前 bounded slice 足够清晰时，输出至少：

- current goal
- confirmed decisions
- accepted constraints
- rejected alternatives
- assumptions
- unknowns / deferred items
- non-goals
- decision rationale
- concrete positive examples
- negative / counterexamples
- success criteria
- failure conditions
- dependencies
- risks
- spec delta / implementation-ready requirements
- validation / eval plan

### Stopping condition

不要等待整个项目所有未知项都解决。

当当前 bounded slice 的高影响未知已经足够清楚、剩余问题可以安全地标记为 UNKNOWN / DEFERRED，且已经能够形成可验证规格时，就应停止 discovery 并进入下一阶段。

### Multi-agent rule

如果你可以调用其他 AI / agent / researcher / coder：

- 由一个 `Discovery Lead` 负责与我主要对话；
- 其他 agent 提交 research findings、question candidates、blockers、counterarguments 和 implementation constraints；
- Discovery Lead 去重、排序、翻译后再问我；
- 不要让多个 agent 分别轰炸我；
- Coding Agent 不得自行猜测战略需求；
- Reviewer 可以重新打开 discovery，但必须说明触发它的证据或失败。

### Quality checks

持续关注：

- useful decisions per question
- critical unknown discovery
- redundant question rate
- novel option acceptance
- user cognitive load
- interruption cost
- post-spec rework
- contradiction leakage
- provenance completeness
- authority violation

目标不是“问得多”，而是用最少的高价值互动，帮助我们共同发现一个比我最初表述更完整、更可验证、甚至更有创造力的方向。

## 4. Terminology pack for AI-specific glossaries

### Canonical terms

- **MIDS** — Mixed-Initiative Discovery & Specification — 混合主动式共创发现与规格化
- **Discovery Lead** — 负责和用户进行主要 discovery 对话、聚合其他 agent 问题候选的角色
- **Epistemic Coverage Matrix** — 认知覆盖矩阵，用于区分显性知识、隐性知识、可发现选项、专家盲区和未知
- **High-Information-Value Question** — 高信息价值问题，对关键决策、不确定性或下游依赖有显著影响的问题
- **Question Selection Policy** — 动态决定下一问的策略，而不是静态问卷
- **Mixed-Initiative Interaction** — 人和 AI 都可以主动发起动作、问题和候选方案的交互范式
- **Human-AI Co-Creation** — 人和 AI 共同扩展、评估和收敛设计空间
- **Requirements Elicitation** — 从 stakeholder 中发现、澄清和验证需求
- **Knowledge Elicitation** — 从人的经验和隐性认知中提取可表达知识
- **Tacit Knowledge** — 隐性知识，人会做或会判断但未必能直接说清楚的知识
- **Cognitive Task Analysis (CTA)** — 认知任务分析，用于理解复杂判断背后的线索、策略和决策结构
- **Critical Decision Method (CDM)** — 通过回溯关键事件和反事实问题挖掘专家判断的方法
- **Preference Elicitation** — 通过选择、比较、场景和反馈逐步推断真实偏好
- **Continuous Discovery** — discovery 持续贯穿工作，而不是项目开始前一次性完成
- **Double Diamond** — Discover / Define / Develop / Deliver 的发散与收敛框架
- **IBIS** — Issue-Based Information System，用 Issue / Position / Argument 保存设计讨论结构
- **QOC** — Questions / Options / Criteria 设计理由框架
- **Design Rationale** — 保存一个设计为什么这样决定以及替代方案为何被拒的证据
- **Example Mapping** — 用 Rules / Examples / Questions 把抽象需求转换成可测试行为
- **Specification by Example** — 通过具体正反例定义可执行需求
- **Spec-Driven Development (SDD)** — 先形成明确、可验证规格，再进入实现
- **Bounded Clarity** — 只要求当前 bounded slice 足够清晰，不要求整个项目所有问题一次解决
- **Discovery Packet** — discovery 阶段输出给 domain/spec layer 的结构化交接对象
- **Spec Delta** — 相对当前 canonical/spec 新增、修改或撤销的具体规格变化
- **AI Proposal Boundary** — 明确 AI 新想法只能作为 proposal/candidate，不能自动成为用户决定
- **Authority Boundary** — discovery、spec、runtime、domain truth 等角色之间不可越权的边界
- **Contradiction Leakage** — 已确认决定在后续过程被模型无意改写或重新引入的失败
- **Novel Direction Acceptance** — AI 主动提出的新设计方向被用户认可并进入后续规格的比例
- **Critical Unknown Discovery Rate** — 在实现前发现后来可能导致 blocker/返工的重要未知项比例

## 5. Relationship to Second Brain

MIDS 应复用现有 Second Brain 的：

- intake / signal capture
- UNKNOWN semantics
- provenance
- correction / supersedes relations
- Domain Learning Handoff boundary
- Control Tower / independent review / canonicalization governance

共享层可以拥有：

- portable invocation vocabulary
- discovery session envelope
- question selection semantics
- provenance/status vocabulary
- cross-agent question aggregation
- domain handoff packet
- generic shadow/replay eval framework

共享层不得拥有：

- AI Film 的导演/剧情/角色 canonical truth
- AWRSE 的世界/能力/规则 canonical truth
- 任意 domain 的最终专业解释或成熟度决定

## 6. Validation strategy

先 `SHADOW`，后 `PILOT`，再 `CROSS-DOMAIN VALIDATION`，最后才考虑 general canonicalization。

至少用两个差异明显的 domain 做 replay：

1. 隐藏历史任务最终答案，只给当时早期用户输入和 canonical context；
2. 让 MIDS 产生问题和候选方向；
3. 对比它是否提前发现后来真实 review 中出现的重要 blocker、unknown、trade-off 或创意机会；
4. 统计 question yield、redundancy、critical unknown discovery、novel option acceptance、post-spec rework 和 authority violations。

任何 AI inference 静默升级为 user-confirmed truth 都是 fail。
