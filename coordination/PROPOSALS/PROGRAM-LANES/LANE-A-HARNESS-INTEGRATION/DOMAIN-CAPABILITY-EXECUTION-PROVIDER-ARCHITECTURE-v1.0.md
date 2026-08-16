# R138 Domain Capability Execution Provider Architecture v1.0

Status: `GPT_ARCHITECTURE_CANDIDATE / PLANNING_ONLY / NOT_EXECUTABLE`

Issue: #366
Owner: USER
Architecture owner: GPT
Predecessor canonical main at planning start: `8d69e3b7c27ac8f4fb42a15b8065be8738a9afa2`

## 1. Purpose

R136 deliberately leaves every mandatory domain scan `UNKNOWN` when there is no mechanism-backed execution provider. Exact file reads prove inputs were consumed; they do not prove a scan or capability actually ran. R137 then solved a different problem: trustworthy live observation of current GitHub/control-plane facts.

R138 closes the next gap: prove that an allowed domain capability actually executed, on exact inputs, through an attributable provider, with bounded process/tool evidence and result identity that can be consumed by `RuntimeInvocationReceipt`.

R138 is not a domain reasoning authority. It may prove **that an operation ran** and bind what it ran against; it may not decide that the operation's conclusion is true merely because execution succeeded.

Initial trust class:

`BOUNDED_DOMAIN_CAPABILITY_EXECUTION_EVIDENCE_V1`

## 2. Frozen authority boundaries

R138 MUST NOT become:

- Control Tower or task-release authority;
- Signal truth or Signal satisfaction authority;
- W3 knowledge/memory authority;
- AI Film or any domain canonical-truth authority;
- a general shell, generic command runner or generic network client;
- a model chain-of-thought recorder;
- a merge authority;
- a daemon/webhook/poller/scheduler;
- a production service;
- a trading/account/order/fund executor.

Provider success means only: `this exact governed capability invocation executed and has attributable mechanism evidence`.

Outcome truth remains separately evaluated by domain policy, user feedback, validation or later evidence.

## 3. Problem statement from the accepted substrate

The accepted `RuntimeInvocationReceipt` already separates process compliance from outcome quality. In R136, exact repository reads can populate `actual_reads`, but `actual_scans` and `capability_invocations` remain empty and mandatory scans resolve to `UNKNOWN / DOMAIN_CAPABILITY_EXECUTION_PROVIDER_NOT_AVAILABLE`.

R138 SHALL preserve that fail-closed behavior unless a valid capability-execution proof is supplied. It MUST NOT reinterpret file presence, a capability label, a model statement or output similarity as execution evidence.

## 4. Capability classes

R138 v1 recognizes three classes, but does not pretend all are supported.

### 4.1 `EXACT_REPOSITORY_EXECUTABLE`

A domain-owned executable or validator pinned to an exact repository commit and exact executable/code identity. This is the primary R138 v1 execution class.

Requirements:

- repository and commit must be allowlisted by the task/provider contract;
- executable entrypoint must be derived from a governed capability manifest or exact approved adapter, never arbitrary caller shell text;
- every source/input file is bound by exact commit/blob/content digest or equivalent immutable result identity;
- execution occurs in a bounded task-owned temporary workspace;
- no mutation of the canonical source repository;
- command execution uses an argument vector, never `shell=True`;
- timeout, output size, child-process/resource and cleanup limits are explicit;
- environment variables are allowlisted; credentials/secrets are absent;
- network is deny-by-default. If the runtime cannot mechanically enforce a required isolation property, the proof cannot claim it was enforced;
- stdout/stderr may be reduced to bounded public-safe digests/selected structured fields; private/raw payloads are not copied into public receipts.

### 4.2 `ATTRIBUTABLE_TOOL_OR_CONNECTOR_INVOCATION`

Contract class for a future tool/connector provider whose operation is independently attributable to the execution/trace and returns an immutable or replayable result ref.

R138 architecture defines the evidence shape but v1 implementation MUST NOT create a generic connector registry or claim support unless a separately governed provider exists.

Absent provider => `UNKNOWN`, not PASS.

### 4.3 `MODEL_MEDIATED_COGNITIVE_SCAN`

Many AI Film mandatory scans (`narrative_multiplex`, `observable_screen_evidence`, `map_authority`, etc.) are cognitive/directorial operations, not currently executable repository programs.

R138 v1 MUST NOT fake them with a scan-name echo, a model self-report or a hidden reasoning transcript. Until a governed model/tool provider can prove an invocation without exposing chain-of-thought, these scans remain `UNKNOWN` unless the domain itself supplies an executable, versioned capability contract.

This is an intentional truthfulness boundary, not a failure to be papered over.

## 5. Provider-neutral request contract

`CapabilityExecutionRequest_v1` minimum fields:

- `request_id`
- `execution_id`
- `trace_id`
- `domain_id`
- `capability_id`
- `capability_class`
- `provider_contract_revision`
- `source_repository`
- `source_commit`
- `capability_contract_ref`
- `executor_ref`
- `input_refs[]`
- `result_schema_ref`
- `timeout_seconds`
- `max_output_bytes`
- `resource_policy_ref`
- `network_policy_ref`
- `write_policy_ref`
- `privacy_scope_ref`
- `requested_at`

Caller-supplied values are requests, not authority. The provider independently resolves exact code/input identities and rejects any mismatch.

The caller may not provide a trusted `executed=true`, exit status, output digest, result identity, cleanup status or provider seal.

## 6. Execution evidence bundle

`CapabilityExecutionEvidenceBundle_v1` binds at least:

- provider id / contract revision / provider code ref+digest;
- execution id / trace id / request id;
- domain id / capability id / capability class;
- exact source repository and commit;
- exact capability contract identity;
- exact executor code identity and dependency/lock identity where applicable;
- exact input object/result identities;
- deterministic invocation descriptor (argv digest, working-directory policy, environment allowlist digest);
- runtime identity needed for replay analysis (OS/runtime/interpreter version, without secrets);
- started/completed timestamps and duration;
- timeout/resource/network/write policies and which were mechanically enforced;
- exit/termination status;
- bounded stdout/stderr digest metadata;
- exact output/result refs and content digests;
- before/after source-workspace mutation evidence;
- child-process/resource observations where available;
- cleanup status;
- warnings / unknowns;
- evidence refs;
- canonical bundle digest.

A bundle with a required but unenforced boundary is not silently upgraded. It becomes `UNKNOWN`, `UNVERIFIED` or `FAIL` according to materiality.

## 7. Compact capability proof

`CapabilityExecutionProof_v1` is derived only from a validated evidence bundle and binds:

- provider id and evidence-bundle identity/digest;
- execution id / trace id;
- domain/capability identity;
- exact source commit;
- executor digest;
- input-set digest;
- result digest/ref;
- execution status;
- boundary-enforcement digest;
- completed_at;
- invalidation fingerprints.

The proof is a compact mechanism witness, not a portable bearer token granting permission.

Historical execution does not become false merely because time passes, but its use as **current** process-compliance evidence is invalidated by source/capability/executor/input/ruleset drift or a downstream freshness policy.

## 8. RuntimeInvocationReceipt integration

R138 upgrades only the scan/capability evidence lane.

For each mandatory scan the final canonical status remains exactly one of:

- `EXECUTED_WITH_EVIDENCE`
- `NOT_APPLICABLE_WITH_REASON`
- `UNKNOWN`
- `FAIL`

Rules:

1. `EXECUTED_WITH_EVIDENCE` requires a valid `CapabilityExecutionProof` whose execution_id/trace_id, domain, capability, exact source and inputs match the receipt.
2. A capability label alone is never sufficient.
3. `NOT_APPLICABLE_WITH_REASON` is a routing/domain-policy decision with an attributable reason/ref; the execution provider itself cannot launder an applicable scan into N/A.
4. Missing provider, unsupported capability class, source drift or non-attributable execution => `UNKNOWN` or `FAIL`, never PASS.
5. Process compliance may become PASS only when every applicable mandatory obligation has mechanism-backed evidence or a valid not-applicable disposition.
6. Outcome quality remains independent. `process_compliance=PASS` may coexist with `outcome_quality=FAIL`.

## 9. Bounded execution sequence

For `EXACT_REPOSITORY_EXECUTABLE`:

1. Validate request shape and provider/capability allowlist.
2. Resolve current requested source commit against the accepted control-plane/domain-freshness evidence.
3. Materialize an exact task-owned temporary source workspace at the pinned commit.
4. Resolve capability contract, executor code and required inputs by exact object identity.
5. Record source-workspace status and execution environment before invocation.
6. Construct argv from the governed contract/adapter. Reject caller shell fragments and path escape.
7. Apply bounded timeout/resource/output/environment/network/write policy.
8. Execute once with serial provider concurrency by default.
9. Capture exit/termination, structured result refs/digests and bounded log metadata.
10. Verify canonical source repository was never mutated and temporary workspace mutations are inside the allowed task-owned output surface only.
11. Verify cleanup of task-owned processes/temp/cache.
12. Emit evidence bundle and derive compact proof only if all required boundaries are proven.

Any source/executor/input drift between resolution and invocation is fail-closed.

## 10. Domain capability manifest rule

R138 MUST NOT create a second copy of domain semantics in Second Brain.

A production capability mapping must be one of:

- a domain-owned versioned capability manifest at an exact domain commit; or
- a narrowly approved coordination adapter that references exact domain objects and contains only transport/execution mapping, not domain truth.

If an AI Film route names a cognitive scan but no executable domain capability contract exists, the mapping is `UNAVAILABLE / UNKNOWN`.

The initial architecture may use AI Film's existing deterministic `tools/golden_case_ingestor` only as a **candidate bounded executable smoke**, because it is domain-owned and explicitly describes itself as a deterministic evidence layer. It must not be relabeled as proof that unrelated directing scans ran.

## 11. Initial smoke strategy

R138 implementation SHOULD contain two distinct evidence tiers:

### Tier A — substrate mechanism smoke

A synthetic exact-repository capability fixture proves provider plumbing, forgery resistance, timeout/cleanup, source/input/result binding and `RuntimeInvocationReceipt` integration.

Synthetic success proves mechanism correctness only.

### Tier B — real external-domain executable smoke

If preconditions remain valid, use a read-only/bounded operation from `vxz2datoubo/eustia-ai-film@44c383afd2207a97caf45b1b0da6ee1dece43a76`, preferably a deterministic validator/test surface under `tools/golden_case_ingestor`, in a disposable exact clone/workspace with zero canonical-domain mutation.

This smoke proves only that the named domain executable capability ran. It does not prove directorial cognitive scans such as `narrative_multiplex` or `observable_screen_evidence` unless the domain later maps them through an explicit executable contract.

If dependencies, ffmpeg, network isolation or other prerequisites cannot be proven safely, Tier B must report `UNKNOWN/PARTIAL` rather than weakening the boundary.

## 12. Threat/failure semantics

Hard failures include:

- arbitrary command/shell injection;
- executable/path traversal or symlink escape;
- source/executor/input revision drift;
- caller-forged result/status/proof;
- evidence bundle/result substitution;
- cross-domain capability-id collision;
- capability mapping not owned/approved by the domain;
- required network/write isolation not enforced;
- canonical domain mutation;
- timeout/resource escape;
- cleanup failure for task-owned execution;
- stale/replayed proof presented as current after invalidating drift;
- private/secret content leakage into public evidence;
- provider attempting to grant release/merge/domain authority.

Unsupported or unobservable conditions remain explicit `UNKNOWN`.

## 13. Acceptance matrix requirements

Implementation must include adversarial cases covering at least:

1. valid exact executable capability produces evidence;
2. caller self-report cannot produce proof;
3. caller cannot register arbitrary production provider/executor;
4. arbitrary shell text rejected;
5. path traversal/absolute/out-of-root executor rejected;
6. symlink escape rejected;
7. wrong source commit rejected;
8. executor blob/content substitution rejected;
9. input substitution rejected;
10. output/result substitution rejected;
11. evidence bundle digest mutation rejected;
12. execution_id/trace_id mismatch rejected;
13. domain/capability mismatch rejected;
14. timeout blocks PASS;
15. non-zero failure cannot be relabeled success;
16. oversized stdout/stderr bounded/fails according to policy;
17. forbidden environment/credential input rejected;
18. unsupported network isolation cannot claim enforced;
19. canonical domain mutation blocks proof;
20. temp/output write escape blocks proof;
21. cleanup failure blocks or downgrades according to materiality;
22. nested/unbounded process spawning blocked or detected;
23. unsupported capability class => UNKNOWN;
24. cognitive scan self-report => UNKNOWN;
25. scan-name echo is not invocation evidence;
26. N/A requires separate attributable reason;
27. proof replay after source/executor/input drift invalid;
28. exact same immutable historical execution remains replay-verifiable as historical evidence;
29. R136 exact reads alone still cannot prove scans;
30. valid capability proof can populate `actual_scans/capability_invocations`;
31. mixed executed+unknown mandatory scans cannot yield process PASS;
32. complete mandatory evidence can yield process PASS while outcome quality remains UNKNOWN/FAIL;
33. provider cannot authorize release;
34. provider cannot authorize merge;
35. provider cannot write W3/domain canonical truth;
36. public evidence contains no chain-of-thought/private body/secrets;
37. zero-domain-mutation smoke;
38. resource single-worker/no nested-pool behavior;
39. bounded task-owned cleanup;
40. exact-head Python 3.11/3.13 CI;
41. retained R136/R137 fail-closed regressions;
42. real external-domain smoke is labeled narrowly and cannot satisfy unrelated scan ids;
43. stale domain capability contract blocks current compliance;
44. cross-window/task drift requires fresh reconciliation.

## 14. Resource governance

Implementation resource class: `MEDIUM_IMPLEMENTATION` initially.

- one active Codex route maximum;
- one local heavy stage maximum;
- capability execution concurrency 1 by default;
- no nested process pools;
- no global `kill python`;
- only task-owned process/temp/cache cleanup;
- broad matrices prefer remote CI;
- no daemon/server.

## 15. R138 planning/activation gates

Architecture merge does not authorize implementation.

Before non-executable reservation:

- fresh accepted R137 observation of current main/control-plane;
- fresh Global Reconciliation;
- O0-O4/same-agent/resource/permission boundary scan;
- exact implementation write/read set proposed;
- reservation route and Work Claim must say `execution_allowed=false`.

Before implementation:

- reservation must be canonical and fresh;
- re-run live observation/reconciliation after reservation merge;
- explicit user command `启动 R138`;
- GPT activation PR/receipt passes exact-head Control Tower CI;
- only then may Codex receive a Launch Envelope.

## 16. Falsifiability / strongest counterexample

The strongest counterexample to a successful R138 is an execution report that can still be forged by supplying plausible capability/result fields without the provider having actually launched the exact executor. Acceptance therefore requires mutation tests against the proof/bundle, process-level evidence, exact code/input/result binding and a real bounded execution smoke.

A second counterexample is semantic overclaim: a real domain tool ran, but the system labels unrelated cognitive scans as executed. R138 must make such mapping impossible without an exact governed domain capability contract.
