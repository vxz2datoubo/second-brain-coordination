# E54 Project Plan: authority repair and provider recertification

## Identity and starting state

- Task: `CODEX-E53-POST-RECEIPT-AUTHORITY-REPAIR-FORMAT-OWNERSHIP-MANIFEST-IMMUTABILITY-RELATION-EVIDENCE-MUTATION-COVERAGE-AND-PROVIDER-RECERTIFICATION-0050-E54`
- Route epoch: `56`; Issue: `#170`; branch: `codex/e53-post-receipt-authority-repair-0050-e54`.
- Canonical base: `67f6f82236f25009a628a8db86570eefec67e4aa` from `vxz2datoubo/second-brain-coordination`.
- Frozen input only: E53 Issue `#168`, PR `#169`, receipt `95f3d4b9e2149c5bce4e22d94755900335ae75d1`.
- E53 is an untrusted, partial candidate. No E53/E52/QCLAW branch write, whole-branch integration, rebase, or history rewrite is permitted.

## Fundamental goal

Deliver a public-safe, source-bound atomization authority candidate whose format ownership, immutable coverage manifest, relation evidence, complete packet verification, history hygiene, adversarial mutations, Provider evidence, and receipt topology can be independently recomputed. The result remains research-only and requires GPT review; it is not authority, production, market-data, or trading capability.

## Non-negotiable constraints

- Begin with this strict one-file plan-only commit, then open one Draft PR and publish the lease claim.
- Copy E53 only after an exact path/blob/content selection ledger exists. Each copied blob remains untrusted until E54 tests and mutations kill its relevant failure mode.
- Use synthetic, public-safe fixtures only. Do not read or modify private configuration, model/provider settings, credentials, accounts, market data, or trading interfaces.
- Do not write `main`, merge, auto-merge, force-push, rebase, amend, or alter frozen branches.
- Final delivery shape is one substantive tested commit followed by one receipt-only commit; no post-receipt code commit.

## Work packages and stage gates

### WP0 - source inventory and acceptance contract

Create the E53 exact-selection ledger before copying code. Record source commit, path, blob ID, content SHA-256, license/public-safety disposition, and E54 destination. Freeze the task impact forecast, unknowns, decision log, execution contract, report schema, receipt allowlist, and rollback plan. Verify task/route/lease freshness and source PR freeze.

**Gate:** all imported paths are individually selected; E53 whole-branch trust is explicitly rejected.

### WP1 - clean E54 implementation boundary

Port only selected public-safe implementation and test scaffolding into an E54-owned package. Establish deterministic source evidence, UTF-8 indexing, format adapters, atom registry, ledger, relations, packet factory, hygiene scanner, topology validator, and provider-evidence writer. Preserve E53 negative findings in E54 documentation rather than silently rewriting history.

**Gate:** copied tests identify the original E53 defect cases before repair; allowed-path validation is deterministic.

### WP2 - deep ledger and packet authority

Implement deep immutable snapshots and a complete manifest recomputation from source bytes, sorted spans, ownership totals, boundaries, and validator evidence. Make packet issuance and verification rebuild the complete graph from verified snapshots, including field evidence, unknowns, conflicts, redaction lineage, relations, and validation results. Reject mutable aliases, foreign and stale objects, and projection/canonical divergence.

**Gate:** ordinary-caller alias mutations and copied-source mutations both fail closed; restored suite is green.

### WP3 - exact format and relation semantics

Implement byte-complete format-specific ownership. JSON and JSONL structural bytes (keys, punctuation, delimiters, escapes, line boundaries) stay structural; only explicit value content can become atom candidates. Markdown headings, blockquotes, lists, tables, code fences, code bodies, terminators, and separators have explicit ownership. Relations bind type, endpoints, source digest, exact slice bytes/digest, and span.

**Gate:** no gaps/overlaps; adversarial fixtures prove keys or Markdown structure cannot be promoted and relation evidence cannot be substituted.

### WP4 - historical hygiene and mutation matrix

Scan each commit and all changed tree entries plus final tree. Build real copied-production-source mutations for every mandated class: ledger/packet alias, JSON and JSONL ownership, Markdown categories, field provenance, relation evidence/endpoints, graph reconstruction, redaction/private-marker blocking, generated add-then-delete history, Provider artifacts, and receipt topology. Every mutant must make its relevant product suite fail nonzero, then restore the exact original source and rerun green.

**Gate:** mutation evidence records anchors, replacement counts, source hashes, command, exit status, stdout/stderr hashes, counterexample seed, and restoration result.

### WP5 - deterministic Provider recertification and delivery

Create canonical multi-format synthetic evidence and per-job environment evidence containing exact head, test/mutation counts and IDs, command/result hashes. Run Python 3.11 and 3.13 with hash seeds `0`, `1`, and `777`; publish exactly six canonical artifacts, six environment artifacts, and one independent byte-compare artifact for both tested and receipt heads. Receipt validators enforce exact task/signal/workflow identities, SHA-40 shapes, run/job/artifact bindings, allowlist topology, and the external receipt-head binding schema.

**Gate:** exact-head workflow evidence is green and byte-identical across the six job artifacts; receipt remains the only post-tested commit.

## Verification approach

1. Unit and integration tests assert full recomputation rather than stored-metadata equality.
2. Metamorphic tests alter aliases, identity fields, spans, relation slices, ordering, exposed projections, and historical commit paths.
3. Mutation tests edit copied production source in isolated copies, observe nonzero failure, restore byte identity, then rerun green.
4. Public-safe scanners check every changed path, final tree, generated/transient exclusions, secrets, and non-allowlisted receipt paths.
5. Provider and independent artifact comparison repeat the exact head matrix, not a summary reconstruction.

## Initial UNKNOWNs and decision rules

- A task-specific `TaskImpactForecast` is not present on canonical `main`; WP0 will create one from the approved Issue and record this as a routing-quality finding without changing scope.
- E53 source code may require replacement rather than reuse. E54 selects blobs only after local inspection and test mapping.
- Python 3.13 availability and Provider workflow execution remain environment dependencies. If unavailable locally, local evidence records `UNKNOWN` and the exact-head Provider gate remains required.

## Rollback and completion

The E54 branch is isolated from `main`; rollback is branch disposal after GPT review. No frozen E53 object is changed. Before completion, the final report will enumerate base, plan, tested, and receipt commit/parent/tree IDs; source/destination blob hashes; command evidence; all mutations; Provider job/artifact digests; UNKNOWNs; and exact rollback commands. Completion is the route signal `CODEX_E54_E53_AUTHORITY_REPAIR_PROVIDER_RECERTIFICATION_READY_FOR_GPT_REVIEW`, never self-acceptance or merge authorization.
