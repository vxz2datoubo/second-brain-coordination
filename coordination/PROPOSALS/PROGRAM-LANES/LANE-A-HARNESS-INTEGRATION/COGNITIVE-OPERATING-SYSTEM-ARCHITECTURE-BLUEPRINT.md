# Cognitive Operating System × Harness Integration Blueprint

- status: `ARCHITECTURE_CANDIDATE / PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION`
- owner: `USER`
- architecture_owner: `GPT`
- parent_control_tower: `#310`
- required_cognitive_input: `#312`
- first_domain_consumer: `#308`
- second_brain_foundation: `#282 -> #335 CLOSED_WITH_BOUNDED_GAPS`
- canonical_base_at_design_start: `823d5b22c7b449626bc03cdf1f574c592e50b9fc`
- boundary: `NO_TRADE / NO_PRIVATE_ACTIVATION / NO_PRODUCTION_GATEWAY / NO_AGENT_ROUTE`

## 0. 北极星目标

目标不是“多 Agent 系统”，也不是“把所有功能塞进第二大脑”。目标是形成一个可以长期成长的 **AI Cognitive Operating System**：

`感知 / 输入`
→ `识别真正问题`
→ `按需召回历史知识、经验、失败、方法和约束`
→ `判断自己知道什么、不知道什么、该用什么方法`
→ `主动找证据与反证`
→ `独立生成主解与挑战解`
→ `验证、裁决、必要时退回重做或弃权`
→ `执行或给出决策支持`
→ `观察现实结果`
→ `归因失败/成功到具体 claim / method / tool / data / regime`
→ `二次学习`
→ `修正知识、方法健康度、失效条件、路由与技能候选`
→ `跨场景验证`
→ `升级、降级或退休技能`
→ `下一次遇到类似问题时自然召回并复用`。

最终用户体验必须是：**用户只面对一个 Signal Tower 入口；系统自己决定是否需要 0 / 1 / N 个任务、哪些可并行、哪些必须顺序、谁审核谁、失败退回谁。**

---

## 1. 绝对架构原则

### P1. 拆职责，不拆成多个“大脑”

- W3 / Second Brain 是唯一长期知识、记忆、冲突、未知、生命周期真源。
- Harness 是运行时与编排底盘，不是知识真源。
- Signal Tower 是唯一用户任务入口与 Mission 调度层，不是知识真源。
- Control Tower 是跨线路授权、WIP、Work Claim、冲突与漂移治理，不是任务路由器。
- #312 是 ProblemSignature / Method Discovery / Meta-Reasoning / Effective Challenge 方法层，不建立第二 W3。
- #308 是第一 A 股真实消费者，不建立第二 Method Router / Feedback Runtime / Evidence Truth。

### P2. 一个复杂任务只有一个 DecisionEpisode 主脊柱

所有重要任务使用统一 `DecisionEpisode` 贯穿，而不是 Agent 之间互相传自然语言导致语义漂移。

### P3. Evidence-first，而不是 Narrative-first

任何高影响结论固定遵循：

`OBSERVATION -> EVIDENCE -> COMPETING_HYPOTHESES -> MISSING_DATA -> TEST -> ATTRIBUTION -> CONFIDENCE / ABSTAIN`

禁止：

`现象 -> 编一个听起来合理的故事 -> 再找证据装饰故事`。

### P4. Independent-first, Reveal-later

高风险任务中，Producer 与 Challenger 必须先基于同一 canonical evidence 独立形成判断，再揭示彼此结论；避免顺序锚定和从众。

### P5. Raw once, reference everywhere

原始执行事件只保存一次。后续 Handoff、DecisionEpisode、Audit、Learning 通过稳定 ID/hash 引用，不复制大段原始 trace。

### P6. Foundation Closure

第二大脑基础层冻结后，新能力默认放在 adapter/service/plugin/skill/policy 层。只有 `BUG / SECURITY_GAP / CONTRACT_DEFECT / PROVEN_REGRESSION` 才允许重开基础接口。

### P7. No one-shot skill promotion

一次成功不能把方法升级为正式技能。技能必须经过 synthetic、real-case、cross-context、regime、失败条件、回滚与回归验证。

### P8. Abstention is a feature

`NO_METHOD / NO_SUITABLE_METHOD / EVIDENCE_INSUFFICIENT / CONFLICT_UNRESOLVED / REGIME_UNKNOWN / ABSTAIN` 都是合法结果。

---

## 2. 九层总体架构

### L0. User / External World

输入来源：用户对话、文件、网页、GitHub、市场数据、公告、工具结果、现实反馈、Agent 回执。

### L1. Signal Tower — Mission Intake & Dispatch

职责：
- 唯一用户入口；
- 识别真实目标、约束、风险、需要的决策；
- 创建 `Mission`；
- 请求 ProblemSignature；
- 生成 `MissionGraph`；
- 决定 0 / 1 / N 个 Work Items；
- 向 Control Tower 请求可执行性裁决；
- 汇总最终结果与 unresolved items；
- 绝不直接绕过领域权威写知识、下单或授权执行。

### L2. Cognitive Planning — #312

核心组件：
- `ProblemSignature`
- `CognitiveCapabilityMap`
- `MethodMemory`
- `SkillManifest`
- `MethodDiscovery`
- `MetaReasoningRouter`
- `DynamicMethodComposition`
- `ChallengePolicy`
- `EvidenceAcquisitionPlan`

核心问题：**“这件事应该怎么想、需要什么方法、还缺什么证据？”**

### L3. Governance — Control Tower #310

核心问题：**“这个计划现在能不能这样执行？”**

检查：
- latest per-agent ACTIVE route；
- Work Claim；
- O0-O4 overlap；
- authority collision；
- path/interface collision；
- same-agent double booking；
- heavy-resource collision；
- privacy / permission / NO_TRADE / production gates；
- stale view / stale route。

### L4. Runtime / Orchestration — Harness

只负责执行机制：
- session；
- workflow；
- subagent；
- job；
- tool；
- retry/cancel/timeout；
- background child task；
- lifecycle event；
- provider adapter；
- runtime observability。

Harness **不能成为** W3、Risk、Trading、Method、Evidence 或 Control Tower authority。

### L5. Knowledge / Memory — W3 Second Brain

职责：
- SourceEpisode；
- memory / knowledge / plan / stance / event atoms；
- provenance；
- bitemporal validity；
- conflict / unknown；
- retrieval-before-write；
- retrieval-before-answer；
- candidate lifecycle；
- feedback/lifecycle update；
- current/historical separation。

### L6. Domain Authorities — W2-W13

典型：
- W2 market data / A-share rules / replay；
- W4 indicator/strategy/experiment；
- W5 event/news/policy/cross-asset；
- W6 participant hypothesis/game；
- W7 validation/risk/final veto；
- W9 outcome calibration/system learning；
- W10 Personal Epistemic OS / DecisionEpisode；
- W11 capital allocation；
- W12 decision science / method gap compiler；
- W13 participant capital-flow evidence。

### L7. Effective Challenge & Evidence Audit

角色模板，而非永久 Agent：
- Producer；
- Challenger；
- Evidence Verifier；
- Method Validator；
- Adjudicator；
- Risk Veto；
- Outcome Auditor。

### L8. Learning / Evolution

- W9 outcome audit；
- MethodCredit / SkillHealth；
- failure localization；
- RegressionCase；
- W3 candidate update；
- method/skill promotion/degradation/retirement；
- routing-policy learning；
- architecture debt / incident learning。

---

## 3. 统一认知闭环状态机

`INTAKE`
→ `PROBLEM_SIGNATURED`
→ `CONTEXT_RETRIEVED`
→ `CAPABILITY_GAP_MAPPED`
→ `METHODS_DISCOVERED`
→ `METHODS_SELECTED_OR_ABSTAINED`
→ `EVIDENCE_PLAN_READY`
→ `CONTROL_TOWER_AUTHORIZED`
→ `EXECUTING`
→ `PRIMARY_RESULT_READY`
→ `CHALLENGE_PENDING_OR_SKIPPED`
→ `VERIFIED`
→ `ADJUDICATED`
→ `DOMAIN_VALIDATED`
→ `RISK_VETO_CHECKED`
→ `OUTPUT_OR_ACTION_PROPOSED`
→ `OUTCOME_OBSERVED`
→ `ATTRIBUTED`
→ `REFLECTED`
→ `LEARNING_CANDIDATES_CREATED`
→ `CROSS_CONTEXT_VALIDATED`
→ `UPDATED / DEGRADED / RETIRED`
→ `CLOSED`。

任何状态都允许：
- `RETURN_FOR_EVIDENCE`
- `RETURN_FOR_REWORK`
- `ESCALATE`
- `CANCEL`
- `ABSTAIN`
- `FAIL_CLOSED`。

---

## 4. DecisionEpisode 主对象

`DecisionEpisode` 是认知编排主脊柱，不是数据库替代品。

必须至少包含：

- `decision_episode_id`
- `mission_id`
- `problem_signature_id`
- `user_goal`
- `task_class`
- `materiality`
- `risk_class`
- `regime_context`
- `context_bundle_ref`
- `method_selection_ref`
- `evidence_plan_ref`
- `mission_graph_ref`
- `challenge_level`
- `claim_ids[]`
- `trace_root_id`
- `handoff_refs[]`
- `unresolved_ids[]`
- `veto_status`
- `decision_status`
- `outcome_ref`
- `learning_ref`
- `reproducibility_fingerprint`

只保存关键状态和引用。原始模型输出、工具日志、Agent 细节放 Raw Trace。

---

## 5. ProblemSignature 与 CognitiveCapabilityMap

### 5.1 ProblemSignature

描述问题结构，而不只描述主题：
- domain；
- task type；
- objective；
- decision horizon；
- materiality；
- reversibility；
- evidence requirements；
- causal vs descriptive；
- temporal/PIT requirements；
- uncertainty type；
- adversarial exposure；
- data/tool prerequisites；
- relevant regimes；
- failure cost。

### 5.2 两轴认知地图

用户认知轴继续复用现有四状态：
- `KNOWN_SAID`
- `KNOWN_UNSAID_INFERRED`
- `UNKNOWN_BUT_ACCESSIBLE`
- `UNKNOWN_REQUIRES_SCAFFOLDING`

系统能力轴新增：
- `EXISTING`
- `CONTRACTED`
- `CANDIDATE_SKILL`
- `REFERENCE_ONLY`
- `REJECTED`
- `UNKNOWN`

推荐字段：
- concept_id
- user_cognitive_state
- user_state_confidence
- system_capability_state
- system_skill_ref
- task_relevance
- bridge_concepts
- prerequisites
- next_action

推断状态永远不能伪装成用户明确说法。

---

## 6. Method Discovery / Meta-Reasoning Router

输入：
- ProblemSignature；
- W3 ContextBundle；
- MethodMemory；
- SkillManifest projection；
- Failure/Regression cases；
- current regime；
- available tools/data/permissions；
- budget/time/resource limits。

评估维度：
- structural fit；
- prerequisites；
- evidence/data availability；
- materiality；
- regime/freshness；
- expected value / cost；
- conflicts；
- historical success/failure；
- permission/safety；
- tool availability。

输出允许：
- 0 个方法；
- 1 个方法；
- N 个方法组合；
- `NO_METHOD`；
- `NO_SUITABLE_METHOD`；
- `ABSTAIN`。

`DynamicMethodComposition` 必须 bounded：只能组合已声明输入/输出/前置条件/权限/失败条件的方法片段，组合后进入额外验证，不得把临时组合直接晋升正式 Skill。

---

## 7. Effective Challenge Mesh

### 7.1 风险自适应 Challenge Level

- `C0`: deterministic/schema checks only
- `C1`: Producer + deterministic verification
- `C2`: independent Challenger
- `C3`: Challenger + Evidence Verifier + Adjudicator
- `C4`: two independent research lanes + Method Validator + W7 + Human Gate

升级因素：
- 资金影响；
- 不可逆性；
- 新颖度；
- 证据质量；
- Agent disagreement；
- regime 异常；
- downstream dependency；
- 历史失败率；
- trace completeness；
- confidence 与 materiality 不匹配。

### 7.2 独立性规则

高风险情形：
1. Producer 与 Challenger 读取同一 canonical evidence；
2. 不读取对方结论；
3. 独立生成 claim set；
4. 之后按 ClaimID 交叉质询；
5. Evidence Verifier 调工具/一手资料验证；
6. Adjudicator 按证据契约裁决，可 ABSTAIN；
7. W7 保留最终 veto。

Judge 永远不是 truth authority。

---

## 8. Evidence Contract 与 Claim Graph

每个 material claim 必须有：
- `claim_id`
- `claim_type`: OBSERVED_FACT / SOURCE_CLAIM / MODEL_INFERENCE / CAUSAL_HYPOTHESIS / UNKNOWN
- `statement`
- `scope`
- `valid_time`
- `source_refs[]`
- `support_refs[]`
- `counterevidence_refs[]`
- `assumptions[]`
- `falsifiers[]`
- `regime_applicability`
- `confidence_class`
- `status`

对于市场因果归因必须保留竞争假设，不能强迫选唯一故事。

---

## 9. Signal Tower Mission Graph

Signal Tower 不把自然语言直接扔给 Agent，而先生成 `MissionGraph`。

节点：
- research
- retrieval
- data acquisition
- evidence verification
- implementation
- test
- challenge
- review
- adjudication
- approval
- writeback

边类型：
- `DEPENDS_ON`
- `CAN_PARALLEL_WITH`
- `BLOCKS`
- `REQUIRES_APPROVAL_FROM`
- `RETURNS_TO`
- `ESCALATES_TO`

Signal Tower 只提出执行计划；Control Tower 才裁决是否允许实际运行。

---

## 10. Department Contract Graph

每一个部门/组件必须声明：
- department_id
- authority_domain
- consumes[]
- produces[]
- may_review[]
- may_challenge[]
- may_verify[]
- may_veto[]
- return_to[]
- escalation_target[]
- timeout_policy
- retry_policy
- privacy_class
- required_trace_level
- rollback_owner

关系类型标准化：
- `PRODUCES_FOR`
- `READS_FROM`
- `REQUESTS_FROM`
- `HANDOFF_TO`
- `REVIEWS`
- `CHALLENGES`
- `VERIFIES`
- `VETOES`
- `RETURNS_TO`
- `REWORKS`
- `ESCALATES_TO`
- `FEEDBACK_TO`
- `LEARNS_FROM`
- `DEPENDS_ON`
- `BLOCKS`

禁止只画“箭头”，却没有输入输出契约和失败路径。

---

## 11. Organization Graph Validator

架构完成不能靠人工看图验收。验证器必须检测：

- orphan department；
- sink/dead-end department；
- circular dependency without termination；
- duplicate authority；
- missing reviewer/challenger for material path；
- return path missing；
- infinite rework loop；
- schema incompatibility；
- stale interface version；
- trace break；
- feedback break；
- resource collision；
- shadow authority/runtime；
- unauthorized cross-domain write；
- unbounded retry；
- missing ABSTAIN/fail-closed path。

关键状态机后续候选用 TLA+/TLC 或同等级 model-based state exploration 验证 deadlock / safety / liveness，而不是只写 unit test。

---

## 12. Trace / Handoff / Replay

### 12.1 三层 Trace

**Native Raw Trace**
- Harness SessionEvents
- provider-native events
- Codex App Server Thread/Turn/Item
- tool raw result
- workflow lifecycle

**Cross-Agent Trace Ledger**
- 谁把什么交给谁；
- upstream/downstream refs；
- acceptance/rejection；
- retry/rework；
- route/claim/witness。

**Formal Handoff**
- `*.handoff.json`
- `*.analysis.md`

JSON 是机器契约；Markdown 解释原因、最强反方、未知、失效条件和建议。自然语言不得偷偷升级 JSON 的 epistemic status。

### 12.2 OTel 对齐

概念映射：
- DecisionEpisode ≈ Trace
- Agent/Tool/Method/Stage ≈ Span
- critical transition ≈ Span Event
- cross-workflow relation ≈ Span Link

只借用通用 trace/span/context 语义；不把 OpenTelemetry 变成业务真源。

### 12.3 Cognitive Reproducibility Fingerprint

至少绑定：
- SourceSnapshotHash
- ContextBundleHash
- UpstreamHandoffHashes
- PromptTemplateHash
- Method/SkillVersion
- ModelProvider
- ModelID
- ToolSchemaHash
- CodeCommit
- DomainRuleSnapshot
- SchemaVersion

用于回答：同一问题为什么这次和上次得出不同结果？是数据、模型、Prompt、Skill、工具、规则还是代码变了？

---

## 13. Harness Integration Boundary

### 13.1 Harness 可以拥有

- workflow lifecycle；
- agent/subagent process/session；
- background jobs；
- provider adapter；
- tool invocation；
- runtime retry/cancel/timeout；
- runtime trace emission；
- bounded workflow state。

### 13.2 Harness 不可以拥有

- W3 canonical knowledge truth；
- formal Skill truth；
- MethodMemory truth；
- market data truth；
- probability/risk truth；
- trading truth；
- Control Tower authorization truth；
- W7 veto authority。

### 13.3 Adapter-first

固定结构：

`Signal Tower / #312 / W3 / W2-W13 / Control Tower`
→ `Our Harness Adapter`
→ `Harness stable public service boundary`
→ `provider / subagent / tool`。

不得让 domain code 直接 import Harness 内部 provider implementation。

### 13.4 Version policy

- production/runtime pin exact tested version；
- latest upstream 只跑 compatibility radar；
- breaking change 只报警；
- 禁止自动升级；
- adapter contract tests 必须覆盖 pinned + candidate latest；
- Harness source/repository identity 在实际实现前必须重新独立验证，当前架构阶段不依赖未重新核实的 source identity。

---

## 14. Codex / External Agent Adapter

若使用 Codex，优先通过其公开 App Server 协议构建 richer adapter：
- thread start/resume/fork；
- turn/item lifecycle；
- shell/file-edit/reasoning/agent output items；
- approvals；
- auth；
- native progress events。

Codex native trace 必须作为 Raw Trace 引用进入系统，不能只保留“最终一句 SUCCESS”。

任何 Agent 自报 SUCCESS 都必须经 artifact/test/CI/worktree/authority 独立验收。

---

## 15. Learning & Evolution — 真正的“二次学习”

系统学习不等于模型权重训练。当前第一阶段采用可审计的 external cognitive learning。

### Loop A — Immediate Correction

用户纠正 / 工具验证失败 / 审核发现错误：
- 修正 Claim；
- 更新 evidence/counterevidence；
- 标记 superseded/revoked；
- 创建 FailureCase。

### Loop B — Episode Reflection

任务结束后：
- 哪一步错；
- 为什么错；
- 哪个前提错；
- 哪个数据缺失；
- 哪个方法不适用；
- 哪个 Agent/Tool 失败；
- 哪个 regime 改变。

输出 `ReflectionCandidate`，不是自动真理。

### Loop C — Method Credit

把成功/失败 credit 分配到：
- method；
- skill；
- tool；
- evidence source；
- challenge strategy；
- routing choice；
- regime。

避免把“最终成功”全归功于最后一个 Agent。

### Loop D — Regression Mining

将高价值成功、失败、边界案例形成 `RegressionCase`：
- positive；
- negative；
- adversarial；
- regime shift；
- counterfactual。

### Loop E — Skill Evolution

生命周期：

`DISCOVERED_INSIGHT`
→ `KNOWLEDGE_CANDIDATE`
→ `METHOD_CANDIDATE`
→ `SKILL_CANDIDATE`
→ `SYNTHETIC_TESTED`
→ `REAL_CASE_TESTED`
→ `CROSS_CONTEXT_VALIDATED`
→ `FORMAL_SKILL`
→ `DEGRADED / RETIRED`。

每次升级都需要 evidence package + test receipt + rollback。

### Loop F — Architecture Learning

如果错误来自流程/接口/组织关系，而不是知识本身：
- 写入 Engineering Learning；
- 更新 Department Contract / Router Policy / Challenge Policy 候选；
- 通过回归与治理门后再改变系统。

---

## 16. Failure Taxonomy

统一候选分类：
- SOURCE_ERROR
- DATA_ERROR
- RETRIEVAL_ERROR
- EPISTEMIC_ERROR
- CAUSAL_ERROR
- MODEL_ERROR
- METHOD_ERROR
- TOOL_ERROR
- COORDINATION_ERROR
- JUDGE_ERROR
- RISK_ERROR
- AUTHORITY_ERROR
- PERMISSION_ERROR
- TRACE_ERROR
- RESOURCE_ERROR
- ENVIRONMENT_CHANGE
- CONCEPT_DRIFT
- REGIME_SHIFT
- RANDOMNESS
- UNKNOWN_UNKNOWN

W9 必须尽量把失败定位到 claim/span/method/tool，而不是只记录“任务失败”。

---

## 17. Resource Governance

针对本机资源约束，固定：
- same agent active executable route max = 1；
- local heavy stage max = 1；
- nested process pools forbidden；
- task-owned descendants must be tracked and cleaned；
- 禁止全局 `kill python.exe`；
- 大矩阵优先远程 CI；
- Agent parallelism 与 CPU/process/memory budget 分离控制；
- 超资源预算可 `DEFER / QUEUE / ABSTAIN`，不能为了并行把电脑拖死。

---

## 18. A 股首个真实消费者 #308

第一真实 consumer 必须保持 `research_only / NO_TRADE`。

流程：

`Market Observation`
→ `EventCoverageReport`
→ `PIT Event Backfill`
→ `Competing Hypotheses H1..H5`
→ `Evidence Acquisition`
→ `Independent Challenge`
→ `Cross-sectional / negative control`
→ `Domain W2/W5/W6/W13`
→ `W12 decision science`
→ `W7 veto`
→ `UNRESOLVED_MIXED / EVENT_CAUSE_UNKNOWN / bounded attribution`
→ `Outcome audit W9`
→ `MethodCredit / W3 learning candidate`。

利好消息不能直接等于股价必涨；主力/洗盘/吸筹等人格化语言没有证据不得升级成事实。

---

## 19. Evaluation Architecture

必须同时评估：

### Memory
- extraction
- multi-session reasoning
- temporal reasoning
- knowledge update
- abstention
- stale/current separation
- cross-scope privacy isolation

### Method Selection
- method recall
- structural fit
- prerequisite checking
- NO_METHOD correctness
- composition validity

### Challenge
- error catch rate
- false challenge rate
- agreement-collapse rate
- judge order/position robustness
- evidence usage

### Learning
- next-episode improvement
- wrong lesson rate
- catastrophic over-generalization
- skill promotion precision
- degradation detection

### System
- trace completeness
- replayability
- authority collision
- deadlock/livelock
- rework termination
- stale route detection
- resource ceiling compliance

### A-share
- PIT integrity
- event coverage
- false attribution
- unresolved honesty
- T+1 / limit / suspension / liquidity / cost semantics where applicable

---

## 20. 研究映射与采用原则

以下研究只作为设计证据，不直接成为产品规则：

- ReAct：reasoning 与 action 交替，支持“思考-取证-再思考”结构；
- Reflexion：把现实反馈转成 episodic reflection，支持不改权重的二次学习；
- Self-Refine：反馈-修正迭代说明 first-pass 不是 final-pass；
- CRITIC：外部工具反馈对纠错的重要性，支持独立 Evidence Verifier；
- Voyager：skill library、环境反馈、自验证与可组合技能；
- MemGPT：分层/虚拟上下文与长期记忆调度；
- LongMemEval / LoCoMo：长期记忆需单测 extraction、跨会话、时间、更新、abstention；
- A-MEM：动态链接和 memory evolution，但任何自动演化在本系统必须保留 W3 provenance/lifecycle authority；
- Multi-agent debate failure research：反对无约束“大家讨论到一致”；
- LLM-as-a-Judge bias research：Judge 必须盲化/随机顺序/证据 rubrics，并接受不确定；
- OpenTelemetry：Trace/Span/Context 语义可复用；
- Temporal：长流程 durable history/replay/retry 思路可参考，但不直接引入第二 workflow truth；
- TLA+/TLC：用于关键组织状态机的 deadlock/safety/liveness 验证候选；
- NIST AI RMF / TEVV：风险自适应评估、验证与持续监控参考。

---

## 21. 分阶段落地

### H0 — Architecture Freeze

交付：
- Authority Map
- Department Contract Graph
- Interface Map
- DecisionEpisode Contract
- Trace/Handoff Contract
- Effective Challenge Policy
- Signal Tower Contract
- Harness Adapter Boundary
- Failure/Learning lifecycle
- Dependency DAG

### H1 — Contract-only Synthetic Skeleton

只实现 schema/state-machine/validator，不连接 private data，不调用真实交易，不创建生产 daemon。

### H2 — Harness Adapter PoC

在隔离 fixture 中验证：
- Mission -> workflow
- child agent
- tool call
- retry/rework
- trace linkage
- cancellation
- resource cap
- provider failure

### H3 — Cognitive Synthetic Vertical Slice

`ProblemSignature -> W3 synthetic recall -> Method Discovery -> Primary/Challenge -> Adjudication -> Reflection -> LearningCandidate`

### H4 — Cross-Agent Trace & External Agent Adapter

验证 Codex/native provider trace、Handoff、artifact audit、failure injection。

### H5 — #308 A-share Shadow Consumer

仅历史/PIT/shadow replay；NO_TRADE。

### H6 — Outcome Learning / Skill Health

MethodCredit、RegressionCase、degrade/retire、cross-context promotion。

### H7 — Signal Tower User Entry

用户只对一个入口发任务；Mission Router + Control Tower + Harness 串联。

### H8 — Production-readiness Gate

只有在独立安全/权限/隐私/恢复/资源/回滚/TEVV 审核后，才讨论 private/live/production；真实交易仍需独立高风险批准。

---

## 22. 当前必须保留的未决项

- Harness canonical source/repository/version identity：`REVERIFY_BEFORE_IMPLEMENTATION`。
- R120-W01 context-only endpoint：`BOUNDED_GAP / ADAPTER_CONCERN`。
- R122 unknown binding：`BOUNDED_GAP / SUCCESSOR_INTERFACE`。
- production/private bridge：`LOCKED`。
- formal skill promotion runtime：未来独立 gate。
- real A-share execution：`NO_TRADE`。

---

## 23. H0 完成标准

只有同时满足以下条件才能进入 H1：

1. 每个 authority 唯一；
2. 每个 material path 有 review/challenge/veto/return path；
3. 所有跨部门接口版本化；
4. Signal Tower 不复制 Control Tower；
5. Harness 不复制 W3/#312/W7；
6. DecisionEpisode 与 Trace/Handoff 可一一追踪；
7. learning 不允许一次成功直接升级 Skill；
8. Organization Graph Validator 无 unresolved O3/O4 architecture collision；
9. 有完整 rollback/reopen rule；
10. Harness source/version identity 已重新验证；
11. synthetic evaluation plan 已冻结；
12. 用户高影响审批边界保持不变。

**H0 未通过前，不发布 Harness runtime implementation route。**
