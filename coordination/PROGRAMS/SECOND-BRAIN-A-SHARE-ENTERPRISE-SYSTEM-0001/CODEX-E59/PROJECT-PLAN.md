# E59 Project Plan: Canonical Trust, Source Evidence, and Descendant-Tree Closure

- `agent_id`: `CODEX`
- `task_id`: `CODEX-E58-POST-RECEIPT-CANONICAL-VERIFIER-SOURCE-BOUND-EVIDENCE-RELATION-ONTOLOGY-DESCENDANT-PROCESS-TREE-AND-P0-CLOSURE-0055-E59`
- `route_epoch`: `61`
- `mode`: `project_plan`
- `issue`: `#197`
- `branch`: `codex/e58-post-receipt-canonical-trust-process-tree-closure-0055-e59`
- `base`: `75371943bd4e5d977ef89c200c8863795e90b276`
- `completion_signal`: `CODEX_E59_CANONICAL_VERIFIER_SOURCE_EVIDENCE_DESCENDANT_TREE_P0_DUAL_PROVIDER_READY_FOR_GPT_REVIEW`
- `boundary`: `PUBLIC_SAFE_SYNTHETIC_ONLY / QCLAW_E45_READ_ONLY / NO_PRIVATE_CONFIG / NO_TRADE / NO_MERGE`

## Goal And Truth Standard

E58 remains frozen at `4d92747098ab18f03c7379b2fa82c5f33251f82c`. Its tested Provider and JSONL/Unicode/conflict improvements are reusable only by exact commit/path/blob/content selection. No E58 branch merge or cherry-pick is permitted.

The E59 success condition is narrower and stronger than a green unit-test suite:

> An ordinary caller cannot manufacture or substitute accepted verifier, source, evidence, or relation authority; and no task-owned Python descendant survives or escapes resource accounting on normal completion, root exit, exception, timeout, cancellation, or Ctrl-C.

All claims are classified as `VERIFIED_TEST`, `VERIFIED_PROVIDER`, `VERIFIED_REPOSITORY`, `HISTORICAL_ATTRIBUTION_UNRECOVERABLE`, `PROPOSAL_ONLY`, or `UNKNOWN`. A test that merely passes a Boolean to an oracle is never accepted as evidence of a controlled violation.

## Binding Resource Rule

LOCAL RESOURCE SAFETY IS BINDING: obey the local process protocol; default to sequential local mutation/provider execution; never exceed the per-agent or global Python process caps; disable nested parallelism; own every child process; clean the full owned process tree on success, error, timeout and cancellation; verify return to baseline; never kill unrelated Python processes.

Limits: project-owned Python processes including descendants <= 8, single-agent <= 6, single-agent CPU-bound workers <= 3, and dual-agent allocation <= 4 processes / <= 2 CPU-bound workers per agent. Heavy local mutation and Provider stages are serial under `SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK`. New launches pause when available RAM < 8 GiB or combined CPU is > 70 percent for 15 seconds. All owned children run at Windows below-normal priority; nested parallelism is disabled.

## Source Freeze And Reuse Procedure

Before copying any E58 content, publish `E58-SOURCE-SELECTION.yaml` containing, for every selected path, the exact E58 commit, Git blob SHA-1, content SHA-256, selected role, and a rejection rationale for unselected helpers. The plan treats E58 as a source of candidate implementation and tests, never as an authority assertion.

Expected reuse candidates are the JSONL/Unicode semantic execution fixtures, conflict evidence fixtures, and their test patterns. Public bootstrap APIs, caller-created `EvidenceStatement` acceptance, caller-controlled relation type, direct-child-only cleanup, and incomplete receipts are explicit replace targets.

## Work Packages And Checkpoints

### WP0: Lease, Baseline, And Bounded Process Canaries

1. Create this one-file plan commit, push it, open the only Draft PR, and publish a literal TaskLeaseClaim to Issue and PR.
2. Record a resource baseline: PID, PPID, executable, command digest, creation time, ownership classification, process counts, CPU, and available RAM. Unknown or pre-existing processes are never terminated.
3. Implement and run a bounded two-process descendant canary before semantic adaptation. It must cover: live child with multiple grandchildren, root-exits-first, timeout, exception/cancel, Ctrl-C, and dual-agent/cap contention simulation. The run must persist spawn/exit and cleanup evidence.
4. Close no P0 root-cause category without direct evidence. Historical attribution is reported separately from experimentally prevented current failure modes.

Checkpoint: publish an InProgressVisibilityPacket for `RESOURCE_BASELINE` and `DESCENDANT_CANARY`. Stop if ownership cannot be proven, a cap is exceeded, a verified owned process remains after grace, or cleanup could affect an unrelated process.

### WP1: Canonical Authority Boundary

Replace public self-bootstrap with a separate authority host/process and an immutable, externally pinned descriptor. Consumers receive a limited verifier client; they cannot create an accepted authority merely by importing a public constructor or supplying a candidate descriptor. The task-local design is only claimed for its tested boundary. A persistent/deployed authority service remains `PROPOSAL_ONLY`.

Tests must show that caller-created descriptors, verifier hosts, forged capability fields, and bootstrap-like APIs cannot be accepted by a verifier client bound to the canonical descriptor.

### WP2: Source-Span Evidence And Relation Semantics

Accepted semantic evidence must originate from an authority-issued `SourceCapability` and `SpanCapability` whose source digest, byte range, decoded ownership, and exact excerpt are verified by the authority host. Caller strings are hints only. They cannot receive PASS without accepted source/span verification.

Relation type is derived from a registered, versioned ontology/rule evaluator. Caller relation labels are rejected, mapped as non-authoritative hints, or contradicted by the evaluator; they can never create a semantic relation by assertion alone.

### WP3: Full Descendant Lifecycle And Shared Gates

Use Windows Job Objects when assignment works. When outer-job assignment returns `ERROR_ACCESS_DENIED`, maintain a verified task-owned descendant registry using PID, creation time, command digest, and observed ancestry. Poll while the root is alive so root-exits-first descendants remain attributable. Termination is graceful first, then a verified owned PID subtree only after identity recheck; no executable-name or global-Python killing.

The shared resource authority enforces process, CPU-worker, CPU/RAM, mutex, duplicate-daemon, and dual-agent limits as executable gates. Tests prove that rejected launches do not increment counters and that cleanup returns all owned state to baseline.

### WP4: Adversarial Tests, Mutations, And P0 Closure

Every audit blocker gets a real correct object and a derived controlled-violation object. The named oracle reevaluates the actual object and records specific evidence. Each mutation changes an owned copy, executes the affected test, records the failure/survival outcome, and restores the exact source bytes in `finally`.

P0 categories to exercise: nested fan-out, orphan on error/timeout/cancel, repeated-launch accumulation, duplicate persistent daemon, and dual-agent collision. The final P0 statement must distinguish `HISTORICAL_ATTRIBUTION_UNRECOVERABLE` from `CURRENT_PREVENTION_EXPERIMENTALLY_VERIFIED`.

### WP5: Tested Commit, Provider, Receipt, And External Anchor

The substantive tested commit contains implementation, tests, workflow, source selection, cumulative AMED/WPDCR/unknown/discovery evidence, and test receipts. It has no future receipt self-reference.

The workflow runs Python `3.11` and `3.13` with `PYTHONHASHSEED=0,1,777`: six matrix jobs plus one compare job, seven jobs total and thirteen artifacts per tested or receipt run. Canonical inner files must be byte-identical after independent artifact download and archive/inner-byte verification.

After tested Provider evidence is complete, create exactly one non-empty receipt-only direct child commit. It may alter only E59 receipt/governance/evidence paths, records literal external anchors, then receives a distinct receipt Provider run. Completion requires remote-resolvable tested and receipt SHAs, fresh route reread, exact archive execution evidence, and Issue/PR external anchors.

## Authorized Files And Ownership

Writable paths are limited to:

1. `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-E59/**`
2. `.github/workflows/codex-e59-canonical-trust-process-tree-closure.yml`

Everything else, including E58 and QCLAW E45, is read-only. No main write, merge, rebase, amend, force-push, private configuration, real data, credentials, account, market, or trading operation is authorized.

## Test Strategy

- Deterministic unit and integration tests for canonical descriptor rejection, forged authority rejection, source-byte tampering, decoded/excerpt mismatch, source digest mismatch, caller evidence rejection, ontology derivation, unknown/rejected relation labels, and JSONL/Unicode/conflict regressions.
- Process tests for normal completion, root-exits-first, timeout, exception/cancellation, Ctrl-C, repeated launch, duplicate daemon, cap rejection, and dual-agent contention. They are bounded and sequential locally.
- Mutation tests for every E58 audit blocker. A passing mutation is an unresolved defect, not a success.
- Static validation of YAML/JSON/JSONL, no duplicate keys, authorized-path allowlist, no-secret scan, worktree cleanliness, commit topology, receipt-only file scope, and artifact byte identity.

## Recovery And Rollback

Every checkpoint records the exact commit, parent, tree, changed files, commands, exit codes, output hashes, owned-process registry, and remaining UNKNOWNs. On a resource violation, stop launching workers, clean only verified owned identities, publish the visibility packet, and retain the branch for GPT repair. No reset, force-push, or history rewrite is allowed.

Reverting E59 means reverting the tested commit and its receipt-only direct child from a reviewed branch; it does not alter frozen E58, main, or unrelated worktrees.

## Known Unknowns And Escalation

- A task-local authority host is not a production, cross-machine trust root. Persistent/deployed canonical authority is a C-level proposal requiring a later task.
- The historic 119-process incident may lack sufficient original telemetry for causal attribution. It remains `HISTORICAL_ATTRIBUTION_UNRECOVERABLE` unless original evidence becomes available.
- Windows outer-job restrictions may reject Job Object assignment. The verified registry fallback must be demonstrated, not assumed.

Escalate immediately for a route change, blocked canonical remote identity, any unauthorized path need, private configuration, resource cap breach, orphan after grace, or any requirement that needs a deployed authority service.
