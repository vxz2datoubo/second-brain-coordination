# E57 Project Plan

## Route identity

| Field | Value |
| --- | --- |
| Task | `CODEX-E56-POST-RECEIPT-ORDINARY-CALLER-CAPABILITY-REGISTRY-SEMANTIC-RECORD-RAW-DECODED-DUAL-PROVIDER-ANCHOR-AND-RECEIPT-CLOSURE-0053-E57` |
| Epoch | `59` |
| Issue | `#190` |
| Branch | `codex/e56-post-receipt-capability-authority-closure-0053-e57` |
| Base | `437b0f7e1a78d868342a0a4b205e47ffb719aebb` |
| Completion signal | `CODEX_E57_CAPABILITY_REGISTRY_SEMANTIC_RECORD_DUAL_PROVIDER_RECEIPT_AUTHORITY_READY_FOR_GPT_REVIEW` |
| Boundary | `PUBLIC_SAFE_SYNTHETIC_ONLY / NO_PRIVATE_CONFIG / NO_TRADE / NO_MERGE` |

## Fundamental goal

Deliver a small, independently reviewable E57 authority boundary that does not
confuse Python object construction with issuance. An ordinary consumer must be
unable to manufacture accepted source, atom, evidence, packet, or relation
authority by importing modules, enumerating globals, replacing registries, or
injecting a same-ID object. A green result is meaningful only if semantic
records are derived from verified inputs and actual execution receipts, all
known bypasses are exercised by adversarial cases and genuine mutations, and
tested and receipt Provider evidence are separate downloaded-byte records.

This task does not establish a cryptographic guarantee against arbitrary code
already executing inside the issuer process. If process isolation is not
available in the allowed scope, the claim will be narrowed to the deterministic
service boundary actually tested; it will not be described as protection from
untrusted code in the same interpreter.

## Frozen inputs and source-selection rule

- E56 Issue #185 and Draft PR #186 are frozen at
  `e98102f2753086ede2471f6176ee6a761b0df431`.
- E56 has execution credit but is untrusted source material until E57 rebuilds
  and attacks it.
- Before any E56 path is adapted, create `E56-SOURCE-SELECTION.yaml`. For each
  selected path it will record the frozen source head, source commit, full path,
  Git blob SHA-1, content SHA-256, destination, disposition, and reason.
- No E56 branch merge, cherry-pick, copied receipt claim, or QCLAW E44 edit is
  permitted. QCLAW E44 is read-only interface context only.

## Architecture decision and alternatives

### Chosen direction: narrow issuer boundary

E57 will use a task-local issuer boundary that keeps mutable authority state
outside record objects and prevents normal consumers from receiving insertion
capabilities. Records will carry opaque, deterministic attestations and will
be independently rebuilt from issuer-owned event data. Tests will treat module
global enumeration, `object.__new__`, copied state, foreign issuer objects,
registry replacement, stale policy, and same-ID substitution as adversaries.

Python privacy conventions (`_name`) and ordinary module dictionaries are not
authority boundaries. If the implementation cannot make the intended claim
truthful with a local process/service boundary, E57 will keep a fail-closed
in-process test double and report the process-isolation design as AMED-C rather
than claiming completion.

### Rejected alternatives

1. Reuse E56 mutable module/factory registries: rejected because an importer
   can reach or replace them.
2. Caller-supplied expected outcomes or PASS/FAIL labels: rejected because
   they make the evaluator tautological.
3. A hidden Python module key as a security claim: rejected because arbitrary
   same-process code can inspect or replace it.
4. A new cross-agent canonical schema: proposal only; it would exceed E57
   ownership and collide with QCLAW E44.

## Work packages and gates

### P0: source selection and task controls

Create the source-selection ledger, execution contract, status, decision log,
research and negative-result ledgers, UNKNOWN registry, task receipt templates,
and the first WPDCR entries. Verify every selected E56 blob before adaptation.

**Gate:** source provenance is complete before any copied/adapted code exists.

### P1: issuer capability and adversarial issuance closure

Implement task-local source, atom, evidence, packet, and relation issuance.
Verification must rebuild authority from issuer-owned data, not a
caller-controlled dictionary. Add ordinary-import attacks for direct
construction, module-global enumeration, state insertion/replacement,
foreign-issuer substitution, copied state, stale policy, and same-ID objects.

**Gate:** every issuance attack fails with named evidence; no normal import
exposes an accepted insertion route. The threat-model limitation is explicit.

### P2: semantic and raw/decoded authority

Implement raw-to-decoded per-character mapping with raw ranges and escaped
flags, including UTF-8 and JSON surrogate behavior. Make string, number,
boolean, and null values typed. Represent unsupported Markdown constructs as
typed `UNKNOWN` rather than silently accepting or discarding them. Require
verified two-sided evidence for conflicts, evaluator execution receipts for
validation outcomes, exact redaction ranges and policy lineage, and endpoint-
relevant provenance for relations.

**Gate:** semantic records cannot be admitted from caller prose or unrelated
spans, and byte partition/replay invariants pass.

### P3: canonical evaluator and genuine mutations

Build canonical cases that execute production verification without supplying
expected outcomes to the production path. Include every P1/P2 bypass plus
topology and dual-anchor failures. Each mutation changes actual E57 source or
tool bytes, has a unique target and command, fails its named invariant, restores
the exact original bytes in `finally`, and reruns green.

**Gate:** all named mutations are killed and restored; a surviving mutation is
an explicit stop or remediation item, never hidden by a count.

### P4: Provider, topology, hygiene, and final receipt

Create the required workflow with Python 3.11 and 3.13 across hash seeds 0, 1,
and 777. Each exact-head run must have six matrix jobs, one compare job, and
thirteen artifacts. Independently download job and artifact metadata plus
archive bytes. Store separate immutable `tested_provider_evidence` and
`receipt_provider_evidence`; each has its own run, seven job records, thirteen
artifact records, archive hashes, inner payload hashes, and verifier output.

Verify actual branch topology and commit-range hygiene. The tested commit is
the final executable change. The receipt commit is a nonempty direct child that
changes only the declared receipt allowlist. Receipt-head Provider verification
must finish before publication of a literal external anchor. No commit follows
the receipt.

**Gate:** all external evidence is independently reconstructable and the exact
completion signal is posted only after the frozen receipt head is remotely
resolvable.

## Testing strategy

- Unit and adversarial tests cover every object family and every listed bypass.
- Property tests cover raw byte partition, UTF-8 boundaries, decode/replay,
  escaped mapping, deterministic canonical bytes, typed JSON values, and
  explicit Markdown UNKNOWNs.
- Mutation tests alter real implementation/tool bytes, not predicates or test
  fixtures alone; restoration must be byte-exact.
- Provider tools verify real job/artifact identities, distinct tested/receipt
  run sets, archive bytes, inner payload bytes, workflow constants, branch,
  and exact checkout SHA.
- Topology/hygiene tools inspect the actual branch and range, including parent,
  add/delete, rename/copy, allowed paths, inherited baseline, and final tree.
- Public CI uses only synthetic data. Local and CI commands, exit codes,
  counts, and normalized stdout/stderr hashes are captured in receipts.

## Reporting and visibility

After this plan commit, open exactly one Draft PR and post a literal
`TaskLeaseClaim` containing the canonical main, plan parent/head/tree, route
fields, boundaries, and first-action evidence. At each material checkpoint post
an `InProgressVisibilityPacket` to the Issue and Draft PR. Task artifacts must
include AMED execution receipt, research ledger, improvement ledger, discovery
report, WPDCR, test receipt, UNKNOWN registry, AI handoff, decision log,
execution contract, source selection, Provider contract, receipt allowlist,
external Provider anchor, final report, and run receipt.

All reports carry failures, retries, rejected alternatives, UNKNOWNs, precise
cross-agent requests, rollback, and non-claims. No source/object identity,
Provider completion, or production-security claim is upgraded merely because a
test passes.

## Boundaries and stop conditions

- Authorized writes are limited to `CODEX-E57/**` and the one E57 workflow.
- All fixtures are synthetic and public-safe. Do not read credentials, accounts,
  private config, market data, orders, positions, funds, or trading systems.
- Do not touch frozen E52-E56 paths or branches, the QCLAW E44 worktree/paths,
  `main`, repository settings, history, or merge controls.
- Stop and publish the precise blocker if the active route changes, a path
  outside the allowlist is required, canonical remote identity diverges, or a
  truthful boundary requires an AMED-C/D decision.

## Rollback and recovery

No merge is authorized. Before the receipt, a failed stage is recoverable by
reverting only E57 task-local commits on this branch or by freezing the Draft PR
and routing a successor from a fresh canonical main. After the receipt, no
correction commit is allowed: preserve the branch, publish the defect and let
GPT route a clean successor. Every selected E56 source remains read-only.

## Initial difficulty and discovery posture

Planned difficulty is D3: the central question is whether a truthful ordinary-
caller guarantee can be made in Python without process separation while keeping
deterministic tests and independent Provider evidence. This plan therefore
prefers narrowing claims over hidden state and records the following questions
throughout: reachable consumer authority; E56 reuse versus taint; semantic
derivation; unsupported format edges; dual-run reconstruction; QCLAW boundary;
and protocol/template feedback candidates. AMED A/B work is implementable only
inside E57. Process isolation and cross-agent canonical changes remain AMED-C;
private, destructive, credential, market, and trading work is AMED-D stop.
