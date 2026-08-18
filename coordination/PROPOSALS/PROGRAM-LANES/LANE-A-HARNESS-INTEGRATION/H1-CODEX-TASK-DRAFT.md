# 【Codex模式：目标模式】H1 Cognitive OS Contract-Only Synthetic Skeleton

> **STATUS: `DRAFT_ONLY / NOT_ACTIVE / DO_NOT_EXECUTE`**
>
> This file is a future task contract candidate. It is **not** `ACTIVE-CODEX-TASK`, not a Work Claim, not execution authorization, and not merge authorization.

## 为什么是目标模式

H1 的成功目标和硬边界已经非常明确：把 H0 的 machine-oriented contracts 变成真正可执行的 schema/validator/state-machine synthetic skeleton，并用 deterministic tests 证明这些合同不是“像机器合同的文档”。

实现路径仍允许 Codex在不越界的前提下选择合理代码组织，因此使用：

`【Codex模式：目标模式】`

而不是继续扩大项目计划范围。

---

## 0. 启动前硬门

任何一项未满足：**DO NOT START**。

1. GPT 对 H0 给出 final `ACCEPT` 或 `ACCEPT_WITH_BOUNDED_DEBT`；
2. canonical Control Tower stale state 已清理；
3. `ACTIVE-CODEX-TASK.yaml` 不再把已完成 R132 暴露为 executable READY；
4. Lane C Work Claim 不再绑定 R120 heavy implementation；
5. Lane A 在 current governance 中至少是 `ACTIVE_PROPOSAL_ONLY`，且 H1 有全新的独立 implementation Work Claim；
6. fresh O0-O4 / WIP / same-agent / heavy-resource scan PASS；
7. fresh durable authorization witness；
8. GPT 明确发布 H1 executable route；
9. 当时没有其他 Codex executable route 占用单 Agent lease。

当前在 Draft PR #336 阶段，这些门尚未全部满足，所以**禁止执行**。

---

## 1. H1 唯一目标

实现一个 **public-safe / synthetic / contract-only** 的 Cognitive OS 骨架，用于证明以下 H0 合同可以被机器严格验证：

- DecisionEpisode lifecycle；
- ProblemSignature；
- Mission / MissionGraph；
- Claim / ChallengeCase / VerificationResult / Adjudication；
- FormalHandoff；
- OutcomeLearning；
- ReworkRequest；
- Department Contract Graph；
- dynamic return aliases；
- Trace/Handoff completeness；
- Cognitive Reproducibility Fingerprint。

H1 **不实现真实智能召回、不运行 Harness、不接真实 Agent、不读 private W3、不碰 A 股真实数据**。

---

## 2. H1 输入权威

启动时只读取 GPT 最终接受的 H0 architecture package，至少：

- `COGNITIVE-OS-CONTRACT-SCHEMAS.yaml`
- `DEPARTMENT-CONTRACT-GRAPH.yaml`
- `ORGANIZATION-GRAPH-VALIDATOR-SPEC.yaml`
- `TRACE-LEDGER-PRIVACY-CONTRACT.yaml`
- `METHOD-MEMORY-SKILL-MANIFEST-CONTRACT.yaml`
- `SIGNAL-TOWER-MISSION-ROUTER-CONTRACT.yaml`
- `IMPLEMENTATION-CLAIM-CANDIDATE.yaml`
- `H0-STATIC-CROSS-FILE-AUDIT.yaml`
- final H0 verdict/receipt

H0 proposal files are design inputs. Codex不得自行重定义 authority topology。

---

## 3. 必须实现的模块

### H1-A — Contract compiler / formal structural schemas

把 `COGNITIVE_CONTRACT_DSL/v0.2` 的结构约束编译或等价落实为正式机器 validator。

优先方案：
- JSON Schema Draft 2020-12 或当前项目已有且更稳定的等价结构验证框架；
- 如果不用 JSON Schema，必须证明替代方案提供等价的确定性结构验证，并记录理由。

至少覆盖：
- DecisionEpisode/v1
- ProblemSignature/v1
- Mission/v1
- MissionGraph/v1
- Claim/v1
- ChallengeCase/v1
- VerificationResult/v1
- Adjudication/v1
- FormalHandoff/v1
- OutcomeLearning/v1
- ReworkRequest/v1

禁止：
- 把 YAML 文档原样当“schema已完成”；
- 用 LLM 判断字段合法性；
- 用自然语言 parser 替代 deterministic validation。

### H1-B — Semantic invariant validator

实现 `SemanticInvariantRegistry_v1` 中每个 H1 范围 invariant 的 deterministic validator。

至少包括：
- W7 veto cannot ACCEPT；
- execution states need current authorization ref；
- post-primary state needs resolvable trace；
- learning needs outcome/correction/audit trigger；
- causal ProblemSignature needs competing hypotheses；
- PIT request needs PIT capability；
- completed Mission needs result/no-work reason；
- causal material claim needs falsifier；
- C2-C4 Challenge needs independent_pass_ref；
- FormalHandoff needs raw trace lineage；
- rework target/budget/material-change rules；
- no direct FORMAL_SKILL from OutcomeLearning。

每条 invariant 必须：
- stable validator id；
- positive fixture；
- negative fixture；
- deterministic error code；
- error path；
- regression test。

### H1-C — DecisionEpisode state machine

实现 explicit transition validator：

- normal forward transitions；
- terminal transitions；
- bounded `ReworkRequest/v1` transitions；
- invalid transition fail-closed；
- no ordinal/enumeration-text comparisons；
- identical blind retry cannot bypass retry/material-change policy。

### H1-D — MissionGraph validator

至少检测：
- unknown node/edge endpoint；
- DEPENDS_ON/BLOCKS cycle；
- bounded rework exception；
- retry budget missing；
- termination missing；
- `CAN_PARALLEL_WITH` cannot imply authorization；
- HEAVY_LOCAL policy violation；
- executable state without external current authorization。

### H1-E — Department / Authority Graph validator

至少实现 OGV 中 H1 可离线验证的部分：
- unique authority；
- orphan node；
- dead-end material output；
- undeclared edge endpoint；
- dynamic return alias declaration；
- return alias resolves to exactly one allowed target in a fixture trace；
- role template nonauthority；
- W7 veto integrity；
- Harness nontruth authority；
- W3 single authority；
- no live trading edge；
- H1/H2 release separation invariant。

不允许 H1 为了让 validator 通过而修改 domain authority 定义。

### H1-F — Trace / Handoff fixture validator

使用 public-safe synthetic trace fixtures证明：
- Native trace ref 可被多个 Handoff 引用而不复制 payload；
- broken raw trace ref → `TRACE_INCOMPLETE`；
- `.analysis.md` 不能改变 `.handoff.json` epistemic status；
- private/secret fields 被禁止进入 generic ledger/fingerprint fixtures；
- T0-T3 completeness rules可 deterministic 验证。

### H1-G — Cognitive Reproducibility Fingerprint

实现 canonical fingerprint builder，至少绑定：
- SourceSnapshotHash
- ContextBundleHash
- UpstreamHandoffHashes
- PromptTemplateHash
- MethodSkillVersions
- ModelProvider
- ModelID
- ToolSchemaHash
- CodeCommit
- DomainRuleSnapshot
- SchemaVersion

要求：
- canonical field ordering；
- SHA-256；
- raw secret values forbidden；
- irrelevant UI metadata变化不能改变 cognitive fingerprint fixture；
- model/tool/code/rule/context/source关键变化必须改变 fingerprint。

---

## 4. Synthetic end-to-end fixtures

至少构造以下离线故事，不调用真实 Harness/Agent/W3：

### S1 Simple low-risk no-challenge
Mission → ProblemSignature → authorized synthetic work → Primary result → C0/C1 → Handoff → close。

### S2 High-risk causal challenge
Primary + C3 independent Challenge + Verifier + Adjudicator + W7 PASS_WITH_LIMITS fixture。

### S3 Evidence insufficient
Method/evidence不足 → ABSTAIN，不能强行进入 ACCEPT。

### S4 W7 veto
Adjudicator ACCEPT but W7 VETO → final decision不得 ACCEPT。

### S5 Bounded rework
Adjudication returns for evidence → new fingerprint/evidence → one retry → resolve。

### S6 Infinite retry attack
identical fingerprint + retry → deterministic reject/ABSTAIN/ESCALATE。

### S7 Correction-only learning
没有 real-world outcome，但存在 verified user correction/audit finding → OutcomeLearning合法；仍不得 Formal Skill promotion。

### S8 Broken trace
Handoff引用不存在的 raw trace → TRACE_INCOMPLETE，high-risk gate fail-closed。

### S9 Dynamic return alias
`RESPONSIBLE_UPSTREAM` 根据 trace/reason解析到唯一合法节点；ambiguous/missing lineage fail-closed。

### S10 H1/H2 boundary attack
fixture尝试从 H1 authorization推导 H2 Harness runtime authorization → validator必须拒绝。

---

## 5. Formal model / exhaustive exploration

H1 至少为以下模型提供可运行的 model-based state exploration：

- Mission lifecycle；
- Work Claim authorization abstraction；
- Challenge/Rework termination；
- Skill lifecycle no-one-shot-promotion；
- W7 veto/human gate；
- Trace/Handoff completeness；
- Resource max1 abstraction；
- dynamic return alias resolution；
- H1/H2 authorization separation。

可使用 TLA+/TLC，或证明具备等价 exhaustive-state capability 的方案。

若选择非 TLA+：报告里必须解释为什么更适合当前 repo/toolchain，以及如何验证 safety/liveness。

这一步是**关键状态机验证**，不是要求在 H1 把整个系统形式化。

---

## 6. 资源硬约束

必须针对用户机器历史进程风暴问题设计：

- local heavy stage max = 1；
- H1 本身应属于 light/medium，禁止把它变成 heavy multi-agent任务；
- nested process pools forbidden；
- test worker count有明确上限；
- task-owned child process tracking；
- task结束清理自身 descendants；
- 禁止全局 `kill python.exe` / `taskkill /IM python.exe`；
- 大矩阵优先 GitHub Actions remote CI；
- 不启动长期 daemon/server；
- 不安装/运行 Harness runtime。

必须增加至少一个 resource-policy regression fixture。

---

## 7. H1 禁止范围

**绝对禁止：**

- install/import/bind DeepSeek Harness as product runtime；
- Harness workflow/subagent/jobs integration；
- Codex App Server provider integration；
- real/private W3 read/write；
- 修改 W3 runtime/schema；
- 修改 #312 Method Router runtime；
- 修改 #308 A股 runtime；
- real market data；
- production scheduler/MCP/Gateway；
- credentials/secrets；
- permission/visibility changes；
- Formal PROJECT/GLOBAL Skill promotion；
- trading account/order/fund action；
- 创建 H2 route；
- Codex 自行 merge。

发现上面任何一项“顺手可以做”，必须报告为 future candidate，不得扩大本轮。

---

## 8. 测试要求

至少：

- structural schema positive/negative tests；
- every implemented semantic invariant positive + negative；
- state-machine invalid transitions；
- MissionGraph cycle/rework tests；
- authority duplicate/orphan/alias tests；
- trace/handoff broken lineage tests；
- fingerprint mutation tests；
- correction-only learning；
- W7 veto；
- H1/H2 boundary attack；
- deterministic repeated run；
- YAML/JSON/schema validation；
- `git diff --check`；
- Python 3.11 + 3.13 if using Python, or equivalent supported runtime matrix if another language is explicitly justified；
- exact-head CI on final implementation commit。

测试不得通过 monkeypatch 一个不存在的“未来 Harness”来冒充 runtime integration。

---

## 9. Codex必须回传

统一回执：

- task_id
- mode
- exact objective
- success criteria
- current phase
- completion percentage
- exact base/main SHA
- implementation branch
- PR
- tested head SHA
- changed files
- added/removed scope
- commands/tests
- per-suite counts
- CI run IDs and exact-head status
- workspace clean status
- authority/path audit
- placeholders/shadow implementation audit
- resource/process audit
- decisions + alternatives considered
- unresolved findings
- rollback procedure
- explicit statement: `Harness runtime was NOT installed/bound/activated`
- explicit statement: `No W3/domain/private/production/trading authority changed`

任何 `SUCCESS` 若缺上述实证，不视为验收。

---

## 10. 成功标准

H1 只有在以下全部满足才可进入 GPT review：

1. architecture DSL被真正落实成 formal structural validators；
2. named semantic invariants deterministic、可复现；
3. DecisionEpisode/MissionGraph/Rework状态机 fail-closed；
4. organization authority/alias validator工作；
5. trace/handoff/fingerprint fixtures工作；
6. H1/H2 authorization separation mechanically tested；
7. no private/live/prod/trading/Harness runtime scope；
8. resource constraints preserved；
9. exact-head CI PASS；
10. workspace clean；
11. rollback明确；
12. GPT exact-head review尚未给出 merge authorization。

完成信号候选：

`COGNITIVE_OS_H1_CONTRACT_SYNTHETIC_SKELETON_READY_FOR_GPT_REVIEW`

再次强调：**当前此文件只是 Draft。不要执行。**
