# E60 Project Plan: Canonical Trust Root, External Attestation, and Whole-Task Resource Closure

## 1. Lease and scope

| Field | Value |
|---|---|
| Task | `CODEX-E59-POST-AUDIT-CANONICAL-TRUST-ROOT-EXTERNAL-ATTESTATION-RESOURCE-TREE-CLOSURE-0056-E60` |
| Route epoch | `62` |
| Canonical base | `dbf4fd9933dfd12eeb1abe7e5c5818c5a1a77d38` |
| Frozen input | PR #198 / `4f45114034fa244e044446ca53e05d76e38757e8` |
| Working branch | `codex/e59-post-audit-canonical-trust-root-resource-closure-0056-e60` |
| Status | `CLAIMED_IN_PROGRESS` |
| Operating boundary | Public-safe synthetic fixtures; `research_only / NO_TRADE` |

This is a clean successor. It must not merge, rebase, cherry-pick, or import the E59 branch as a unit. Every later reuse is selected by exact source path, Git blob SHA-1, and content SHA-256. E60 does not claim a deployed or hostile-environment trust root. It establishes a testable boundary for the local runtime and labels every synthetic issuer as non-production.

## 2. Fundamental outcome and non-goals

The outcome is a knowledge-ingestion gate where an ordinary runtime caller cannot create a locally accepted verifier, source, span, evidence, or relation merely by importing a private helper or by supplying arbitrary bytes. The gate must also account for the outer mutation/test runner and all owned descendants before launch, during execution, and after a bounded cleanup grace.

Non-goals are production PKI, a persistent authority service, secrets, credentials, real source ingestion, provider configuration, market data, accounts, or trading. A same-machine caller with code-modification rights is outside the synthetic fixture threat model; the runtime must state that limitation rather than imply a production trust guarantee.

## 3. Frozen-source selection ledger

The following E59 paths were inspected from the frozen commit. This table is a selection decision, not a copy operation. Later implementation must recompute each selected blob and content digest before use.

| Frozen path | Blob SHA-1 | Content SHA-256 | Disposition | Reason |
|---|---|---|---|---|
| `CODEX-E59/PROJECT-PLAN.md` | `a524e893c1e66d076c0869aba6445ea9b0291cc9` | `e3a777e9fcd7931f679863e04f02a139e09e3ca23ab13c5fbd3c89f73ff4006c` | `REFERENCE_ONLY` | Retain prior constraints and negative evidence, not its architecture. |
| `CODEX-E59/src/e59_runtime/authority_client.py` | `ff0f9958bfe0f7165d76b935f894df8b8516d9ad` | `587856af4ba2f81d48d4a003715f61f35a31687f02202c28dc13da86201592de` | `REPLACE` | Its private synthetic harness was caller-importable. |
| `CODEX-E59/src/e59_runtime/authority_host.py` | `b01cbb31cec0696417378388473bf3f3116fdac8` | `488b31229de589548832e85c2803475ec93b7c63f1e6d720b8fe7e74bc8ae163` | `REPLACE` | It accepted caller-supplied raw bytes in the issuance path. |
| `CODEX-E59/src/e59_runtime/process_tree.py` | `587326468eb48d7a1096c0ef68c048da32f7a13e` | `807cca631190049f47a29f56015fa509c4b26c0f12b02e4e308150ba552e1caf` | `SELECTIVE_REUSE_CANDIDATE` | PID-plus-creation-time and root-exit cleanup ideas are useful, but accounting must move outside mutation internals. |
| `CODEX-E59/src/e59_runtime/mutations.py` | `a540690252d53a9c09247c59c247a2a1168fc03e` | `4ff101426fb96a21feafcd7801e69f1bcfb59d11343f4a9eaa220c620c5fe6a8` | `REPLACE` | The outer runner spawned outside the lease and did not test the bootstrap attack. |
| `CODEX-E59/tests/test_authority_boundary.py` | `c7399dd045001ff28442da4cf0403037289cc304` | `8024fe15d578ac9c9ee43503626c1440209c3a079309084a52b6b9a5a71cf040` | `REPLACE` | It imported the same private fixture that the audit used to bypass the boundary. |
| `CODEX-E59/tests/test_process_tree.py` | `0e73756ff59216b7403ed0ca7213e14fd4d1c091` | `70b9367caaa2d196d973f258aeb0c7441bfa185acc58fd65835371e31dc0b6ac` | `SELECTIVE_REUSE_CANDIDATE` | Preserve scenario coverage while adding outer-runner reservation and grace-window assertions. |

## 4. Architecture to implement

### 4.1 Authority and Source/Span boundary

E60 will create a new `e60_runtime` package, not an E59 import wrapper.

1. The runtime verifier exposes verification only. It has no public or private in-runtime issuer, factory marker, bootstrap harness, or caller-supplied authority constructor.
2. A `CanonicalAuthorityDescriptor` is accepted only when it matches an externally attested public verification key, canonical runtime identity, exact source digest, and declared synthetic/non-production domain.
3. A `SourceSpanGrant` carries the source digest, byte range, decoded-text digest, grant identifier, provenance descriptor digest, and signature. Evidence and derived relations consume a validated grant; raw bytes, a source label, or an arbitrary relation string cannot be promoted into accepted authority.
4. Relations are derived from registered relation rules and accepted proposition semantics. A caller-provided label remains untrusted metadata.
5. Test-only issuance code lives outside the runtime package. A direct import of the former E59 private names, an alternate issuer, a forged descriptor, a mismatched source digest, and arbitrary raw bytes must each fail closed.

The verifier public key is an identity anchor, not a claim that repository-local test material is secret. The synthetic test issuer is explicitly `NON_PRODUCTION_TEST_ISSUER`; a later deployed trust root requires a separate architecture decision and task.

### 4.2 External attestation

E60 will define a canonical, content-addressed `ExternalAttestation` schema with full 40-character tested and receipt SHAs, parent/tree SHAs, Provider run/job identifiers, artifact digests, workflow identity, reviewer/GPT acceptance reference, and a signed or independently verified payload digest.

The runtime validates schema, exact-head topology, payload digest, source manifest digest, and non-contradictory lifecycle state. It will reject a mismatched attestation, an attestation for another receipt, truncated SHAs, duplicate conflicting status, and a self-issued runtime attestation. The final external anchor is authored outside the tested code path after Provider results exist. No tested or receipt commit may state that such an anchor has already happened when it has not.

### 4.3 Whole-task resource lease

All local E60 test, mutation, child, and grandchild creation will pass through one outer `TaskResourceLease`. Before each spawn it reserves capacity from a shared, ownership-aware ledger and verifies the dual-agent cap of four owned Python processes, global cap of eight, CPU/RAM thresholds, named heavy-stage mutex, and serial inner execution. The outer mutation runner is itself leased; inner tests do not create independent untracked leases.

The owned-process registry records PID, creation time, parent, command digest, purpose, and expected exit. Cleanup uses verified PID-plus-creation-time identity, graceful shutdown first, bounded grace, then only task-owned tree termination. It never kills by executable name or touches unknown/preexisting processes. Start, peak, and postflight snapshots will be produced for normal exit, exception, timeout, cancellation, Ctrl-C, and root-exit-with-grandchild scenarios.

## 5. Work packages and gates

| Package | Delivery | Required proof | Stop/fail condition |
|---|---|---|---|
| WP0 | Plan-only commit, Draft PR, lease and resource baseline | Exact base, clean worktree, preflight process classification | Any owned-process or mutex ambiguity blocks heavy work. |
| WP1 | Source-selection manifest and E60 contracts | Full blob/content recomputation and strict schema tests | A selected E59 path differs from ledger. |
| WP2 | Runtime verifier, Source/Span grants, relation rules | Direct former-private-import and arbitrary-bytes attack fail closed | Any caller can issue accepted evidence. |
| WP3 | External-attestation parser/verifier | Exact-head, digest, lifecycle, and conflicting-attestation negatives | Receipt claims an unavailable anchor. |
| WP4 | Outer resource lease and canaries | Spawn reserve, peak cap, cleanup grace, no unrelated termination | Any task-owned orphan after grace. |
| WP5 | Mutations and local regression | Each mutation changes a real attack surface and restores in `finally` | A mutation is label-only or survives. |
| WP6 | Tested Provider evidence | Exact checkout SHA, required Python matrix, artifacts and logs | Matrix/run evidence mismatches tested head. |
| WP7 | Receipt-only commit and receipt Provider evidence | Direct-child topology, no executable changes, external attestation binding | Receipt-only scope is empty, broad, or contradictory. |
| WP8 | Cumulative report and GPT review request | Fresh route reread, complete AMED/WPDCR/UNKNOWN/handoff | Route changes, Provider evidence missing, or audit attack still works. |

## 6. Test strategy

Tests must be independent enough to attack the public runtime rather than reproduce its own boolean flags. Required negative cases include:

- direct import of each E59 private harness/factory name;
- substitute canonical descriptor and substitute public key;
- arbitrary raw source bytes, stale digest, altered byte range, and altered decoded digest;
- source/span grant from a different attestation domain;
- caller relation label without registered semantic rule;
- mismatched tested/receipt/parent/tree SHA, artifact digest, Provider job, reviewer reference, and lifecycle state;
- outer mutation runner with child/grandchild canaries under normal, failure, timeout, cancellation, Ctrl-C, and root-exit-first paths;
- capacity exhaustion, mutex contention, PID reuse mismatch, and postflight grace expiration.

All local work is serial by default with thread/BLAS/tokenizer parallelism disabled. Remote Provider runs supply the required version/seed matrix. A green ordinary workflow is not accepted as evidence until its checkout SHA, job logs, artifacts, and content digests bind to the tested head.

## 7. Reporting, rollback, and open limits

Every material checkpoint will publish an InProgressVisibilityPacket with route/base/head, changed paths, test command, resource snapshot, D-level difficulty, discoveries, negative results, and next gate. Final artifacts will include the AMED execution receipt, research ledger, improvement ledger, discovery report, WPDCR, test receipt, UNKNOWN registry, and AI handoff.

Rollback is additive: revert the receipt-only commit first, then the tested implementation commit. Do not modify E59 history. The pre-existing E59 bootstrap bypass, incomplete receipt binding, and mutation-runner over-cap measurement remain retained historical negative evidence until E60 independently disproves them.

Open limits: this task cannot make a public repository fixture a production-grade trust root; it cannot establish historical attribution for the 119-process incident; and it cannot constrain unrelated processes that do not enter the shared lease. Those limits must remain explicit in E60 status and final evidence.
