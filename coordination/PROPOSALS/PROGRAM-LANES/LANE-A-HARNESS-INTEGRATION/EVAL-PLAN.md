# Cognitive OS × Harness Evaluation Plan

Status: `PROPOSAL_ONLY / NO_RUNTIME_AUTHORIZATION / NO_TRADE`

## 1. 目标

这个系统不能靠“看起来更聪明”验收。必须证明：

1. 该召回时能召回，不该召回时能 abstain；
2. 该选的方法能选到，前置条件不满足时不会硬套；
3. 主解与挑战解保持足够独立；
4. 证据验证能纠正错误，而不是只让回答更长；
5. 反馈能形成可审计二次学习，但不会把一次成功过拟合成永久规则；
6. 所有跨部门传递、审核、退回、重做、取消、超时、失败都可追踪；
7. Harness 接入后不夺取 W3 / #312 / W7 / Control Tower 的 authority；
8. 本机资源上限不会因为 Agent 并行被击穿；
9. #308 A 股首个 consumer 在 PIT、证据语言和 competing hypotheses 上显著优于旧叙事式流程。

---

## 2. Evaluation Families

### E1. Long-term Memory / Retrieval

参考 LongMemEval/LoCoMo 的能力分解，但使用本项目自己的 synthetic + historical fixtures。

测试维度：
- information extraction；
- cross-session recall；
- temporal reasoning；
- knowledge update；
- current vs historical；
- correction/supersession；
- abstention；
- provenance；
- user/project/privacy isolation；
- stale/revoked no-resurrection；
- structural analogy isolation；
- semantic provider default-off parity。

关键指标：
- recall precision / recall coverage；
- wrong-memory injection rate；
- stale resurrection rate；
- privacy leakage rate；
- abstention precision；
- temporal correctness；
- provenance completeness。

### E2. ProblemSignature / Method Discovery

构造同主题不同结构问题，以及不同主题同结构问题。

必须测试：
- topic similarity 不应压过 structural fit；
- 方法前置数据缺失时返回 NO_SUITABLE_METHOD；
- 多方法组合不能绕过权限或前置条件；
- 方法历史成功不能跨 regime 无条件迁移；
- 旧失败案例能在相似 failure condition 下被召回；
- 方法说明 progressive disclosure，不能每次把整个 Skill 内容塞进上下文。

指标：
- method top-k structural fit；
- prerequisite violation rate；
- false positive method activation；
- valid abstention rate；
- composition contract violation rate；
- token/context cost。

### E3. Independent Challenge

实验组：Independent-first / Reveal-later。
对照组：Producer 输出先展示给 Challenger。

测试：
- seeded false premise；
- incomplete evidence；
- persuasive wrong answer；
- correct-but-counterintuitive answer；
- conflicting sources；
- judge order reversal。

指标：
- material error catch rate；
- correct-to-wrong flip rate；
- agreement collapse rate；
- false challenge rate；
- evidence-grounded challenge rate；
- adjudicator position consistency；
- unresolved/abstain honesty。

### E4. Tool-grounded Verification

按照 CRITIC 类思想，验证“外部工具反馈是否真的改变错误结论”。

场景：
- code test；
- GitHub artifact check；
- source freshness；
- numeric calculation；
- PIT event lookup；
- schema validation。

指标：
- unsupported claim removal；
- correction rate after tool evidence；
- tool result misuse rate；
- stale tool result acceptance；
- verification cost。

### E5. DecisionEpisode / Trace / Handoff

必须验证：
- every material output -> DecisionEpisode；
- every agent/tool stage -> trace span/ref；
- every handoff -> machine JSON + human analysis；
- every input change changes reproducibility fingerprint；
- same inputs produce attributable differences；
- missing native trace triggers TRACE_INCOMPLETE；
- prose cannot upgrade JSON epistemic status。

指标：
- trace completeness；
- lineage resolution success；
- replay explanation completeness；
- orphan artifact rate；
- fingerprint collision/missing component rate。

### E6. Learning / Reflection / Method Credit

构造 repeated tasks：

T0 baseline
→ failure/correction
→ reflection candidate
→ method credit
→ T1 similar case
→ T2 shifted-regime case。

必须证明：
- T1 对真正相似 failure pattern 有改善；
- T2 regime shift 不因旧经验盲目自信；
- 一次成功不会晋升 Formal Skill；
- 错误 lesson 可被 WEAKEN/REVOKE；
- failure 能定位到 claim/method/tool/data/route，而非全部归因模型。

指标：
- next-episode improvement；
- wrong-lesson rate；
- cross-context generalization；
- overgeneralization rate；
- promotion precision；
- degradation detection latency；
- credit attribution stability。

### E7. Department Contract Graph

自动生成 graph checks：
- orphan node；
- dead-end；
- unauthorized writer；
- duplicate authority；
- no return path；
- no abstain path；
- unbounded cycle；
- no reviewer on material path；
- version mismatch；
- stale route；
- no trace edge；
- no feedback edge。

关键状态机候选使用 model-based exploration / TLA+：
- Mission lifecycle；
- Work Claim authorization；
- review -> return -> rework termination；
- skill promotion/degradation；
- W7 veto/human gate；
- cancellation/retry after runtime failure。

### E8. Harness Runtime PoC

仅 synthetic fixture。

Fault injection：
- provider timeout；
- child-agent crash；
- tool exception；
- malformed handoff；
- stale authorization；
- cancel mid-workflow；
- retry exhaustion；
- trace exporter unavailable；
- upstream interface version mismatch。

必须证明：
- durable/recoverable workflow behavior 或明确 fail-closed；
- no hidden second authority；
- no loss of lineage；
- cancellation stops descendants；
- retries bounded；
- adapter shields domain from Harness internals。

### E9. Resource Governance

本机测试上限：
- one heavy local stage；
- no nested process pools；
- process ownership tracked；
- task descendant cleanup；
- CPU/memory/process budget observability；
- no global kill of unrelated Python；
- stress test uses bounded workers；
- large matrix can shift to remote CI。

必须测试真实历史失败模式：后台几十/上百 Python 进程造成电脑卡死。

### E10. #308 A-share Shadow Consumer

只做历史/PIT/replay，NO_TRADE。

Regression anchor：BlueFocus/Kunlun intraday attribution failure class。

测试：
- event sensor coverage；
- event backfill after unexplained price anomaly；
- evidence language discipline；
- H1 event / H2 beta / H3 technical-liquidity / H4 company residual / H5 unknown；
- strongest counterargument；
- negative control；
- cross-sectional comparison；
- PIT timing；
- no unsupported 主力/洗盘/吸筹 narrative；
- accepts UNRESOLVED_MIXED / EVENT_CAUSE_UNKNOWN。

指标：
- missed-event rate；
- false causal attribution；
- unsupported-personification rate；
- PIT violation rate；
- unresolved honesty；
- evidence coverage before attribution。

---

## 3. A/B 与消融

必须做：
- with vs without Second Brain retrieval；
- semantic only vs structural method retrieval；
- with vs without independent challenge；
- self-refine only vs external verifier；
- with vs without historical failure cases；
- with vs without MethodCredit；
- with vs without regime filter；
- direct Harness binding vs Adapter isolation contract test；
- single pass vs DecisionEpisode closed-loop。

若复杂架构没有在关键指标上优于简单基线，则不因“架构更漂亮”而保留复杂度。

---

## 4. Negative / Counterfactual Tests

必须维护：
- no relevant memory exists；
- relevant memory exists but is revoked；
- similar case from wrong user/project/privacy；
- method succeeded historically but prerequisite missing now；
- two agents agree and both are wrong；
- challenger is wrong but producer correct；
- evidence source duplicated by syndication；
- outcome good due luck despite bad method；
- outcome bad despite sound method due regime shock；
- runtime SUCCESS but artifact missing；
- runtime failed after artifact committed；
- stale Work Claim appears valid except peer claim changed。

---

## 5. Promotion Gates

### H0 -> H1
- authority graph valid；
- interface map frozen enough for synthetic contracts；
- no unresolved O3/O4 architecture collision；
- Harness source/version identity reverified；
- rollback paths defined。

### H1 -> H2
- schema/state-machine tests pass；
- organization validator pass；
- no production/private path；
- Control Tower fresh implementation claim candidate accepted。

### H2 -> H3
- Harness PoC demonstrates bounded lifecycle/trace/failure behavior；
- Adapter contract prevents authority leakage；
- resource caps pass。

### H3 -> H5
- cognitive synthetic slice beats simple baseline on recall + method selection + challenge without material false-positive increase；
- learning loop demonstrates next-episode improvement and no one-shot promotion。

### H5 -> later
- #308 shadow replay meets PIT/evidence/attribution gates；
- W7 / NO_TRADE preserved；
- production still separately gated。

---

## 6. Stop / Reject Conditions

直接停止或退回架构的情况：
- Harness 必须成为第二 W3 才能工作；
- Harness 必须成为 Skill/Method authority；
- runtime trace 无法和 DecisionEpisode 稳定关联；
- review/rework 产生不可终止循环；
- repeated learning 提高过拟合而非泛化；
- challenge 提高篇幅但不提高错误发现；
- resource caps 无法保证；
- #308 consumer 仍能在证据不足时输出确定因果故事；
- adapter 无法隔离 Harness breaking changes；
- source identity / license / version 无法可靠验证。

遇到上述情况允许 `REJECT_WITH_REASON`，但必须给替代方案与影响范围。
