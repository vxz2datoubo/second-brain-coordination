# E56 Project Plan

## Route Contract

- Task: `CODEX-E55-POST-RECEIPT-CANONICAL-EVALUATION-FORMAT-OWNERSHIP-PROVIDER-COMPARE-MUTATION-RESULT-TOPOLOGY-HYGIENE-AND-RECEIPT-CLOSURE-0052-E56`
- Route epoch: `58`
- Canonical main at plan start: `64f6219057252a310953e8faf84eae560dbed045`
- Source candidate: frozen E55 PR #182 at `414c24f557bdaa5d8ec9ebdd1279bf33cb147a81`; no branch merge or cherry-pick is allowed.
- Parallel boundary: QCLAW E43 / Issue #183 owns semantic evidence issuance and must not be changed by this task.
- Safety state: public-safe synthetic fixtures only; `research_only / NO_TRADE`.

## Fundamental Goal

Turn the accepted but insufficient E55 engineering into a clean, independently verifiable E56 authority closure. The result must make source admission and format ownership fail closed, construct canonical evidence from the actual authority graph and adversarial results, and prove Provider, topology, mutation and receipt evidence with no self-authored shortcut.

## Delivery Topology

1. This commit adds only this plan path.
2. A later substantive commit will contain the selected source inventory, implementation, fixtures, tools, workflow, tests and cumulative reports.
3. The final receipt-only commit will contain only nonempty receipt/governance/evidence files and will be a direct child of the tested commit.
4. No commit follows the receipt. No merge, rebase, amend, force-push or direct `main` write is permitted.

## Work Packages

### WP0: Provenance and Contract Freeze

- Create `E55-SOURCE-SELECTION.yaml` before any source copy, with commit, path, Git blob SHA-1, content SHA-256, destination, disposition and reason for every selected source file.
- Publish literal task lease and visibility packets after the first public-safe substantive checkpoint.
- Freeze an independent versioned provider contract: six matrix jobs, one compare job, thirteen artifacts, required names and inner payload expectations.

### WP1: Fail-Closed Admission

- Replace exposed mutable admission internals with opaque capability-scoped issuance and immutable private policy/registry state.
- Verify retained exact bytes, UTF-8, source ID, format, digest, policy identity and blocked-content rules on every replay.
- Test direct-construction, copied-state, `object.__new__`, seal reuse, self-registration, registry substitution, policy replacement and object-field mutation attacks.

### WP2: Total Format Ownership

- Implement versioned tokenization and byte ownership for text, Markdown, JSON and JSONL.
- Keep Markdown syntax and JSON syntax structural while admitting only governed semantic content.
- Emit exact raw-to-decoded escaped-value evidence, including raw span, decoded text and digest binding.
- Prove complete non-overlapping byte partitions and legal UTF-8 boundaries.

### WP3: Bound Evidence and Typed Packets

- Derive evidence statements from admitted spans or reject unrelated caller prose.
- Model UNKNOWN, CONFLICT, REDACTION and VALIDATION as kind-specific records with explicit transition and evidence requirements.
- Rebuild graph projections only through verified registries and validate relation endpoint, type, span and decoded/raw provenance.

### WP4: Topology, Hygiene and Provider Authority

- Fail closed unless plan parent equals base, the first diff contains exactly this plan path, the chain is linear, and the final receipt is exact-path-only.
- Scan task-defined versioned hygiene patterns over commit, per-parent merge, rename/copy and final-tree surfaces with exact parent attribution.
- Generate canonical artifacts from actual production graph evaluations, fixture outcomes and real mutation summaries.
- Make Provider compare reject differing canonical bytes, bind every mutation result payload and reject any unexpected job or artifact.

### WP5: Real Mutations and Exact-head Recertification

- Execute named mutations against copied E56 production/tool bytes; each must produce a nonzero named invariant failure, restore exactly and rerun green.
- Cover every blocker family identified by the E55 formal review.
- Run local tests, public-safe scans and exact provider matrix at the tested head; independently fetch and validate jobs, archives and inner bytes before receipt creation.
- Rerun the exact matrix on the receipt head and independently validate it before publishing the completion signal.

## Acceptance Gates

- All E55 blockers have a production implementation, adversarial fixture and genuine mutation or an explicit UNKNOWN with an owner and closure gate.
- The Provider workflow has exactly six matrix jobs and one compare job, emits exactly thirteen artifacts, and the compare job itself fails for divergent canonical inner files.
- Each canonical artifact is byte-identical across the matrix but changes when an actual authority outcome, fixture outcome, graph projection or mutation summary changes.
- Mutation-result payloads are extracted, digest-bound and semantically revalidated independently from the producer.
- Public reports carry literal SHA values; unresolved public executor attribution remains `UNKNOWN`.
- The only final receipt commit is nonempty, receipt-only, direct-child and followed by no later commit.

## Authorized Initiative and Boundaries

- A/B improvements: deterministic validators, fixtures, tests, observability and receipt evidence within this task root and E56-specific tooling/workflow.
- C proposals only: new canonical systems, QCLAW semantic runtime, new data sources or cross-agent authority changes.
- Stop/escalate for private configuration, credentials, accounts, market data, trading, source-license ambiguity or a required QCLAW path change.

## Known Risks and Recovery

- The highest risk is constructing a green test suite that validates declarations rather than actual production outcomes. Independent byte extraction and real source mutation are required controls.
- A second risk is accidental scope overlap with QCLAW E43. Any semantic-production path conflict is reported as `BOUNDARY_CONFLICT` and not edited.
- Recovery is commit-level: retain the plan, substantive and receipt commits; rollback is a normal new revert commit after GPT authorization, never history rewrite.
