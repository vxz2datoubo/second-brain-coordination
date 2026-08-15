# Harness PoC Contract — Cognitive OS Runtime Adapter

- status: `PROPOSAL_ONLY / FUTURE_IMPLEMENTATION_CANDIDATE`
- owner: `USER`
- architecture_owner: `GPT`
- implementation_owner: `UNASSIGNED`
- current_runtime_authorization: `NONE`
- boundary: `PUBLIC_SAFE_SYNTHETIC / NO_PRIVATE / NO_PRODUCTION / NO_TRADE`

## 1. Mission

未来 PoC 只回答一个问题：

> 在不把 Harness 变成第二大脑、第二 Control Tower、第二 Method Router 或第二 Risk Authority 的前提下，能否用 Adapter 把一个完整 DecisionEpisode 安全地映射到 Harness workflow，并保留 session/subagent/tool/retry/cancel/native-trace 能力？

PoC 不是“把整套系统一次写完”。

---

## 2. Synthetic Vertical Slice

固定最小闭环：

`Synthetic User Mission`
→ `ProblemSignature fixture`
→ `Synthetic W3 ContextBundle fixture`
→ `MethodExecutionPlan fixture`
→ `Synthetic ExecutionAuthorization`
→ `Harness Adapter`
→ `Primary Worker`
→ `Independent Challenger`
→ `Evidence Verifier tool fixture`
→ `Adjudicator`
→ `FormalHandoff`
→ `Synthetic Outcome or Correction/Audit Event`
→ `W9 Reflection/MethodCredit candidate`
→ `W3 feedback candidate (not durable formal promotion)`。

---

## 3. PoC 必须证明

### C1. Authority Isolation

Harness 只能执行输入计划，不能：
- 修改 W3 truth；
- 决定 Formal Skill promotion；
- 绕过 Control Tower；
- 覆盖 W7 veto；
- 生成交易授权。

### C2. Session Isolation

Primary / Challenger 独立 session/context；高风险模式下 Challenger 不读取 Primary conclusion，直到 reveal phase。

### C3. Trace Linkage

每一步必须绑定：
- mission_id
- decision_episode_id
- trace_id/span_id
- workflow_id
- provider-native trace ref
- handoff_id
- input fingerprint

### C4. Formal Handoff

机器 JSON 与 human analysis 成对输出。

### C5. Bounded Failure

至少注入：
- provider timeout
- child crash
- tool failure
- malformed response
- stale authorization
- cancellation
- retry exhaustion
- trace sink unavailable

### C6. Resource Closure

- no nested pools
- bounded workers
- one heavy local stage
- child process ownership
- task descendant cleanup
- no global process kill

### C7. Replay / Diagnosis

PoC 必须能回答：
- 哪个输入触发了结果变化？
- 哪个 agent/tool/method 失败？
- 是否发生 retry？
- 最终 claim 是如何被接受/拒绝？
- 哪些 unknown 未解决？

---

## 4. PoC 明确不做

- 不读用户真实 private W3；
- 不部署 production MCP/Gateway；
- 不启动 scheduler/daemon；
- 不绑定真实 A 股实时数据；
- 不连接交易账户；
- 不写 Formal PROJECT/GLOBAL knowledge；
- 不实现真正 Skill promotion；
- 不允许 Agent 自主新增 Program Lane；
- 不长期 fork Harness upstream；
- 不把 provider-specific API 泄漏到 domain code。

---

## 5. Harness Upstream & Runtime Binding Gate

H0 已独立验证 canonical upstream：

- repository: `deepseek-ai/deepseek-harness`
- exact design snapshot: `47f943859bef60e4160492346772ded9b24f765a`
- package family/root version: `0.1.0-rc.5`
- license: MIT
- maturity: developer preview / breaking changes expected

因此 PoC 不再把“仓库身份未知”当作未决项。真正未通过的是 **runtime binding gate**。

任何 install/import/runtime code binding 之前必须再次确认当前执行头没有悄然替换 pinned snapshot，并完成：

1. exact pinned SHA/package provenance check；
2. reproducible clean install/pack smoke；
3. exact consumed package names and public Service Definition signatures；
4. session/context/skill/subagent/workflow/jobs/guard/bundle/interaction capability smoke；
5. provider adapter behavior；
6. target Windows/local or isolated CI compatibility；
7. breaking-change compatibility test against latest upstream radar；
8. rollback + no-residual-process test；
9. fresh Control Tower Work Claim / O0-O4 / WIP / authorization witness。

任何一项关键证据缺失：

`STOP / RUNTIME_BINDING_NOT_AUTHORIZED`。

---

## 6. Provider Candidate

Codex provider若进入 PoC，优先保留公开 App Server 的 Thread/Turn/Item、approval、auth、progress 等 native events，通过 Provider Adapter 映射，而不是只返回 final answer。

Provider 不是 authority；native events 只进入 Raw Trace。

---

## 7. Acceptance Matrix

| Gate | Requirement |
|---|---|
| POC-A1 | canonical Harness identity + pinned SHA/version provenance PASS |
| POC-A2 | Adapter-only integration; no domain direct internal imports |
| POC-A3 | Primary/Challenger isolation provable |
| POC-A4 | native trace → DecisionEpisode lineage complete |
| POC-A5 | compiled JSON Handoff schema + semantic validators PASS |
| POC-A6 | stale authorization fails closed |
| POC-A7 | retry/cancel termination bounded |
| POC-A8 | process/resource caps pass |
| POC-A9 | authority leakage tests all fail closed |
| POC-A10 | synthetic learning candidate produced without automatic skill promotion |
| POC-A11 | fresh Control Tower Work Claim/witness exists before implementation commit |
| POC-A12 | rollback removes PoC runtime surface without modifying W3/domain truth |
| POC-A13 | clean install/pack/provider smoke on target or isolated CI PASS |
| POC-A14 | pinned-vs-latest compatibility radar detects breaking drift without auto-upgrade |

---

## 8. Rollback

PoC 必须可通过删除/禁用 Adapter 与 PoC fixtures 回滚。

回滚后：
- W3 数据/schema 不变；
- W2-W13 authority 不变；
- Control Tower 不变；
- existing Agent routes 不变；
- no residual background process；
- no scheduled task；
- no private data copy；
- no provider credential persisted in repo。

---

## 9. Completion Signal

未来执行器只有在所有 Gate 可复现通过后才可报告：

`HARNESS_COGNITIVE_OS_ADAPTER_POC_READY_FOR_GPT_REVIEW`

这不是 merge / production / private / trading authorization。
