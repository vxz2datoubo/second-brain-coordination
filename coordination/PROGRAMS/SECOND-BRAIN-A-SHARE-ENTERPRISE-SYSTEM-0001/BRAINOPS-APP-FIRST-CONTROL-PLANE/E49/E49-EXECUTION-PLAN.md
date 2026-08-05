# E49 Execution Plan: Crash-Complete Recovery and Provider-Bound Release Evidence

## Authority and baseline

- Task: `CODEX-BRAINOPS-CRASH-COMPLETE-STAGE-JOURNAL-PROVIDER-RELEASE-EVIDENCE-AND-PLACEHOLDER-FREE-RECEIPT-CLOSURE-0045-E49`
- Route epoch: `51`
- Canonical main at claim: `8db26c0bcf5759425117061f8507dea31dac01e9`
- Frozen E48 source head: `6bf4ab05096e16f889733e42603bdf1f068380d3`
- Boundary: synthetic, public-safe engineering only; `research_only / NO_TRADE`.

E49 is a successor implementation. It imports selected blobs from the frozen E48
head through an explicit manifest; it neither mutates E48 nor merges, rebases,
or cherry-picks the frozen branch.

## Fundamental correctness rule

After a durable claim or lease compare-and-swap succeeds, the process may end
before its next journal write. Restart must derive one legal continuation from
actual durable claim, lease, and journal facts. It may fill missing journal
phases, but it must not repeat a business mutation or return a positive result
without rechecking binding, route, provenance, temporal order, and expiry.

## Delivery stages

1. **Selected-source import and failing specifications**
   - Add an imported-source manifest with frozen path, blob SHA-256, purpose,
     and exclusion reason for every imported E48 file.
   - Import only the BrainOps authority, models, proof, release, mutation,
     workflow-policy, receipt-scope modules and their required tests.
   - Add failing isolated-process tests that terminate immediately after effect
     lease CAS, invocation claim CAS, and invocation lease CAS, before the
     next journal CAS.
   - Add failing release/receipt tests for topology bypass, provider identity
     substitution, placeholders, incomplete evidence families, and invalid
     reproduction commands.

2. **Crash-complete stage reconciliation**
   - Represent the effect and invocation state matrix explicitly.
   - Cover journal-only, record-only, and partially advanced combinations:
     `REQUESTED`, `BINDINGS_VERIFIED`, `CLAIM_MUTATION_APPLIED`, and
     `LEASE_MUTATION_APPLIED`.
   - Reconcile from durable state after a separate process restart. Each
     positive recovery first verifies request digest, purpose, holder, target,
     invocation, provenance, route, time, and expiry.
   - Preserve conflict and impossible combinations as fail-closed evidence;
     do not infer production-store behavior from synthetic file-CAS fixtures.

3. **Provider-bound release verifier**
   - Add a product entrypoint that consumes canonical route/task data, git
     graph and diff facts, provider run/job/artifact records, receipt topology,
     evidence-family inventory, receipt scans, and reproduction-command
     validation.
   - Keep same-job self-certification non-authoritative. Tests use public-safe
     provider fixtures; final completed provider facts come from GitHub after
     tested-head CI.
   - Require exact tested and receipt heads, both Python 3.11 and 3.13 jobs,
     success conclusions, matching job checkout heads, named unexpired
     artifacts, and immutable artifact digests.

4. **Active mutation and deterministic validation**
   - Mutate every mandated hard-crash cut, provider field, topology gate,
     receipt placeholder/evidence family, and reproduction command. A mutation
     counts only when its named target test executes and fails for the intended
     reason.
   - Run schema/serialization, full synthetic regression, release verifier,
     exact command validation, public-safe secret scan, and clean-clone
     reproduction checks.

5. **Tested head and receipt**
   - Push one or more implementation commits only after all local gates pass.
   - Wait for exact-head E49 CI and provider artifacts on Python 3.11 and
     3.13 before creating the final receipt.
   - Create exactly one nonempty evidence-only receipt commit. The receipt
     contains complete tested-head provider facts and the marker
     `receipt_commit_identity: EXTERNAL_POST_COMMIT_PROVIDER_FACT`; it never
     contains a future/self SHA placeholder.
   - Wait for receipt-head E49 CI, then stop for GPT independent remote-head
     recheck. No post-receipt commit is permitted.

## Acceptance matrix

| Gate | Required evidence | Fail-closed outcome |
| --- | --- | --- |
| Hard crash | Isolated process dies after each durable CAS; restart fills only the missing journal phase | A duplicate mutation, changed binding, expired request, or impossible state fails |
| State matrix | Every legal partial state has one continuation and every illegal state is rejected | Positive output with incomplete journal state fails |
| Provider release | Route, graph, run, job, artifact, head, topology, receipt and command facts agree | Caller-declared success, wrong identity, expired/missing artifact, or head mismatch fails |
| Receipt | Nonempty evidence-only child of tested head; tested provider facts complete; no placeholders | Any TODO, deferred self-SHA, forbidden content, or invalid command fails |
| Mutations | All required mutations execute their target tests and produce nonzero failure | Loader failure or skipped target does not count as a kill |
| CI | Exact tested and final receipt heads pass 3.11 and 3.13 E49 jobs with artifacts | Adjacent interpreter, merge SHA, or local-only result is insufficient |

## Bounded initiative and exclusions

Authorized A/B improvements are limited to clearer deterministic state
reconciliation, validator correctness, and regression coverage inside the E49
allowlist. A future authenticated provider aggregation service is C-level only:
it requires a separate route, trust-root decision, and independent review.

No real authority, Canary, App/CLI invocation, credential access, account,
order, market data, trading, model/provider/default configuration, or other
Agent route is touched. No new canonical authority or parallel runtime is
created.

## Recovery and reporting

Every material checkpoint records plan deviation, failures, UNKNOWNs, tests,
and rollback. Before the final signal, re-read canonical main and validate the
route/branch/base tuple. If the route changes, preserve the work and emit a
route-bridge packet rather than modifying the frozen E48 branch.
