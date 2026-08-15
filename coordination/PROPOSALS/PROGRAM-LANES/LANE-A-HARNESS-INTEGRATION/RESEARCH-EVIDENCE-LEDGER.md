# Research Evidence Ledger — Cognitive OS × Harness

Status: `REFERENCE_EVIDENCE / NOT_PRODUCT_TRUTH`

本文件记录本轮架构采用的外部研究依据。任何论文结果都不能直接升级成本系统规则，必须经过本项目 synthetic / historical / shadow validation。

## A. Reasoning / Acting / Reflection

### ReAct — arXiv:2210.03629
- 类型：peer-reviewed research lineage / primary paper
- 可迁移洞见：reasoning 与 action 交替，行动用于主动获取外部信息，适合 Evidence Acquisition 与 tool loop。
- 不直接采用：不把模型内部 reasoning 当作业务真源；不要求保存 private chain-of-thought。

### Reflexion — arXiv:2303.11366
- 类型：primary research paper
- 可迁移洞见：不更新模型权重，也可以把 task feedback 转成 episodic reflection，影响后续试验。
- 对应本系统：ReflectionCandidate + FailureCase + MethodCredit + W3 candidate。
- 风险：反思可能学到错误经验，因此禁止自动 truth/skill promotion。

### Self-Refine — arXiv:2303.17651
- 类型：primary research paper
- 可迁移洞见：first-pass output 经过 feedback/refinement 可提升。
- 对应本系统：RETURN_FOR_REWORK / bounded refine loop。
- 风险：同模型自评可能形成自洽错误，必须与独立 challenge / external verifier 区分。

### CRITIC — arXiv:2305.11738
- 类型：primary research paper
- 可迁移洞见：外部工具反馈对事实、代码等纠错有重要价值。
- 对应本系统：Evidence Verifier；工具结果进入 evidence contract，而不是只用于润色。

## B. Lifelong Skill / Method Evolution

### Voyager — arXiv:2305.16291
- 类型：primary research paper
- 可迁移洞见：skill library、environment feedback、自验证、可组合技能可以支持长期能力积累。
- 对应本系统：MethodMemory / SkillManifest / DynamicMethodComposition / SkillHealth。
- 不直接采用：Minecraft 成功不能证明 A 股/工程场景泛化；Formal Skill promotion 仍需多阶段 gate。

## C. Long-term Memory

### MemGPT — arXiv:2310.08560
- 类型：primary research paper
- 可迁移洞见：分层 memory / virtual context management，按需把长期信息搬入有限上下文。
- 对应本系统：W3 durable memory + compact ContextBundle；Harness session 不成为长期 memory truth。

### LongMemEval — arXiv:2410.10813
- 类型：primary benchmark paper
- 关键能力：information extraction、multi-session reasoning、temporal reasoning、knowledge update、abstention。
- 对应本系统：E1 memory evaluation family。

### LoCoMo — arXiv:2402.17753
- 类型：primary benchmark paper
- 可迁移洞见：长时间、多会话的 temporal/causal consistency 仍是困难问题。
- 对应本系统：跨 session、时间、事件图、current/historical regression。

### A-MEM — arXiv:2502.12110
- 类型：primary research paper
- 可迁移洞见：动态记忆链接与 memory evolution。
- 约束：本系统任何 memory evolution 必须通过 W3 provenance/lifecycle，不能让 Agent 静默改旧知识。

## D. Multi-agent / Judge Risk

### Talk Isn't Always Cheap — arXiv:2509.05396
- 类型：primary research paper
- 结论方向：multi-agent debate 不总是提升正确率，Agent 可能被错误 peer reasoning 带偏并趋向一致。
- 对应本系统：Independent-first / Reveal-later；禁止“讨论到一致”作为 correctness criterion。

### Judging the Judges — arXiv:2406.07791
- 类型：primary research paper
- 结论方向：LLM-as-a-Judge 存在 position bias。
- 对应本系统：blinded/randomized order、rubric、repetition stability；Judge 不是 truth authority。

## E. Observability / Durable Runtime / Formal Validation

### OpenTelemetry official specifications
- 类型：official technical standard/docs
- 当前检索到 Semantic Conventions 1.43.0；signals 包含 traces/metrics/logs/baggage。
- 可迁移洞见：DecisionEpisode ≈ Trace、stage/agent/tool ≈ Span；利用 context propagation 和 stable semantic naming。
- 隐私注意：GenAI prompt/input/output attributes 可能含敏感信息，本系统默认不把 raw private content 放 telemetry attributes。

### Temporal official docs
- 类型：official engineering docs
- 可迁移洞见：durable execution、event history、crash/network failure 后从历史恢复的 workflow 思路。
- 约束：只作为 workflow reliability 参考，不自动引入第二 durable workflow authority。

### TLA+ / TLC official repository
- 类型：formal methods official tooling
- 可迁移洞见：critical workflow state machines 可做 model checking，验证 deadlock / safety / liveness，并导出 error traces。
- 对应本系统：Mission lifecycle、Work Claim、review/rework termination、skill promotion、veto/human gate。

### NIST AI RMF Generative AI Profile / AIRC TEVV
- 类型：government risk/evaluation guidance
- 可迁移洞见：风险自适应治理、测试/评估/验证/确认、持续监控。
- 对应本系统：Challenge Level、H0-H8 gates、TEVV evidence。

## F. Codex external-agent adapter

### OpenAI Codex App Server public README
- 类型：official provider documentation
- 已确认公开能力方向：JSON-RPC bidirectional protocol、thread start/resume/fork、turn/item events、approvals、skills/apps/auth endpoints。
- 对应本系统：未来 richer Codex Provider Adapter 保留 native progress/artifact trace，而不是只拿 final text。

## G. Harness source identity watchpoint

### Current status: `REVERIFY_BEFORE_IMPLEMENTATION`

本轮公开检索出现多个不同项目使用 `deepseek-harness` 名称，无法仅凭名称确认此前架构研究所使用 Harness source identity。

因此冻结原则：
- 本轮只采用抽象能力/Adapter-first 架构；
- 不在代码中绑定某个未重新确认的 repo/package；
- H0 -> H1/H2 之前必须重新确认 canonical repo/tag/commit/license/service definitions；
- 如果 source identity 无法可靠确认，停止 runtime binding。

这个 watchpoint 不是架构 blocker，因为当前设计刻意把 Harness 隔离在 Adapter 后面；它是 implementation blocker。
