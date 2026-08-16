# R138 Domain Capability Execution Provider Threat Model v1.0

Status: `PLANNING_ONLY / NOT_EXECUTABLE`
Issue: #366
Boundary: `EXECUTION_EVIDENCE / NO_DOMAIN_TRUTH / NO_RELEASE_AUTHORITY`

## Assets to protect

1. Truthfulness of the claim that an exact capability actually executed.
2. Exact binding between domain/source/executor/inputs/results and one execution/trace.
3. Canonical domain repositories from mutation.
4. User machine from unbounded process/resource use.
5. Public evidence surfaces from private content, secrets and chain-of-thought.
6. Control Tower, W3 and domain authority boundaries from provider escalation.
7. Replay/currentness semantics of `RuntimeInvocationReceipt`.

## Trust boundaries

- Caller is untrusted for execution/result facts.
- Capability provider may attest only facts it mechanically observes.
- Domain repository owns capability semantics.
- R137 provider owns live GitHub/control-plane observation evidence only.
- Control Tower owns task/lease/release policy.
- `RuntimeInvocationReceipt` is process evidence, not outcome truth.

## Threats and required controls

### T01 Caller self-certification
Attack: caller supplies `executed=true`, exit code, result digest or a plausible capability label.
Control: trusted execution/result fields are provider-derived only; caller-filled proof fails.

### T02 Arbitrary command execution
Attack: capability request smuggles shell text, executable path or arbitrary argv that turns the provider into a remote shell.
Control: no shell; capability id resolves through exact governed manifest/adapter to a bounded argv template; caller values fill only typed allowlisted parameters.

### T03 Path traversal / symlink escape
Attack: executor or input resolves outside the exact source/output root.
Control: normalized relative paths, no absolute/`..`, exact tree object resolution, symlink/reparse-point escape checks before execution and output collection.

### T04 Source/executor/input substitution
Attack: code or input changes after approval or between resolution and execution.
Control: exact commit/blob/content identities; recheck before launch; proof binds exact identities; drift fail-closed.

### T05 Result substitution
Attack: real capability runs but caller swaps output or digest afterward.
Control: provider captures result directly from task-owned output/structured channel and computes result digest before exposure; compact proof binds bundle/result digest.

### T06 Cross-domain capability confusion
Attack: a capability id from one domain is reused to satisfy another domain's mandatory scan.
Control: proof key includes domain id + capability id + domain-owned contract identity; no global name-only matching.

### T07 Fake scan mapping
Attack: a real deterministic tool execution is relabeled as `narrative_multiplex` or another cognitive scan it does not implement.
Control: scan->capability mapping requires exact domain-owned manifest or separately approved narrow adapter; no mapping => UNKNOWN.

### T08 N/A laundering
Attack: provider avoids a required scan by returning NOT_APPLICABLE.
Control: provider cannot adjudicate N/A; N/A requires separate route/domain-policy reason and authority ref.

### T09 Environment/credential injection
Attack: caller passes tokens, HOME/PYTHONPATH hooks or other environment values that change code or leak credentials.
Control: minimal allowlisted environment; credentials/secrets explicitly rejected and never logged; environment digest records only safe names/values or redacted identities.

### T10 Network exfiltration
Attack: executed code accesses network or exfiltrates data.
Control: deny network by policy; if isolation cannot be mechanically enforced for a capability that requires it, evidence cannot claim enforcement and the run cannot be accepted for full compliance. V1 avoids private data entirely.

### T11 Canonical domain mutation
Attack: capability writes into the domain checkout or pushes changes.
Control: disposable exact clone/workspace, read-only source semantics where feasible, before/after status/object checks, no credentials, no GitHub write API; canonical remote never receives provider writes.

### T12 Write escape
Attack: capability writes outside task-owned output/temp roots.
Control: output allowlist, before/after filesystem evidence where enforceable, path checks, fail on observed escape; unsupported enforcement remains UNKNOWN.

### T13 Resource exhaustion
Attack: infinite loop, fork bomb, excessive output or nested parallelism freezes user machine.
Control: timeout, single capability worker by default, no nested pools, bounded stdout/stderr, task-owned child/process tracking, remote CI preferred for broad matrices; never global-kill Python.

### T14 Child-process escape
Attack: parent exits while children remain.
Control: process-group/task ownership where supported; post-execution task-owned child scan; cleanup status is evidence. Unknown ownership => no full PASS.

### T15 Cleanup false-green
Attack: report says clean while temp/process/cache remains.
Control: evidence records bounded cleanup checks; only task-owned cleanup allowed. Existing unrelated user processes/files must never be touched.

### T16 Replay/staleness
Attack: old execution proof is reused after source, executor, input or ruleset changed.
Control: invalidation fingerprints + downstream freshness/currentness comparison. Historical proof may remain historically valid but cannot satisfy current compliance after drift.

### T17 Provider code drift
Attack: proof created by one provider implementation is verified by a different unbound implementation.
Control: provider code ref/digest and contract revision are part of bundle/proof verification.

### T18 Same-process hostile mutation
Attack: malicious code already executing in the same Python process tampers with module-private state.
Control: R138 does not claim cryptographic same-process isolation. Prefer process boundary for execution provider; module-private seals are governance/API integrity only. This limitation must remain explicit.

### T19 Private evidence leakage
Attack: logs/results include private text, media, secrets or chain-of-thought and are copied into public receipt.
Control: R138 v1 public-safe inputs only; bounded digest/result metadata; no chain-of-thought storage; private provider is future separate architecture.

### T20 Authority escalation
Attack: a valid execution proof is treated as permission to run another task, write domain truth, merge or trade.
Control: provider proof has no authorization field; Control Tower remains mandatory; all such actions separately gated.

### T21 Outcome/process conflation
Attack: exit 0 or a valid proof is interpreted as the domain conclusion being correct.
Control: `process_compliance` and `outcome_quality` remain independent; provider attests execution only.

### T22 External dependency drift
Attack: unpinned dependencies alter behavior while executor source commit is unchanged.
Control: bind lock/requirements identity and resolved runtime package fingerprint where needed; missing dependency identity downgrades current-compliance evidence.

### T23 TOCTOU between R137 and R138
Attack: Control Tower/main/domain freshness changes after planning observation but before execution.
Control: fresh R137 observation + reconciliation at reservation and again at activation/use; stale receipt fails closed.

### T24 Generic provider registry injection
Attack: caller registers a fake provider/verifier and self-signs execution evidence.
Control: no caller-facing production registry in R138 v1; explicit provider id/static integration or separately governed provider lifecycle only.

## Security verdict required before implementation

Implementation may proceed only if GPT review confirms:

- provider is not an arbitrary command runner;
- exact domain ownership/mapping is preserved;
- unsupported cognitive scans remain UNKNOWN;
- no private/credential path appears;
- process/resource cleanup is bounded;
- no release/merge/trading authority is introduced;
- all high-risk threats above have positive and adversarial tests.
