# E53 Project Plan: source-bound atomization authority

## Identity and frozen inputs

- Task: `CODEX-NIGHT-CLEAN-SOURCE-BOUND-ATOMIZATION-AUTHORITY-ADVERSARIAL-PROVIDER-AND-RECEIPT-CLOSURE-0049-E53`
- Route epoch: `55`
- Executor: `CODEX`; independent reviewer: `GPT`
- Exact base: `a1f7146469082a975dce069942ca0965e7771ab3`
- Branch: `codex/night-clean-atomization-authority-0049-e53`
- Frozen candidate: E52 Issue #166 / PR #167 at
  `62f12f563797c643714fe0ad40e3e9ea5291693d`
- Completion signal:
  `CODEX_E53_NIGHT_CLEAN_ATOMIZATION_PROVIDER_RECEIPT_CLOSURE_READY_FOR_GPT_REVIEW`

E53 is a clean selective integration. It will not merge, rebase, cherry-pick
wholesale, or modify the frozen E52 branch. Each imported blob is first listed
with source commit, Git blob ID, content SHA-256, disposition, and reason.
Every imported implementation remains untrusted until E53 product tests pass.

## Objective

Build a deterministic public-safe atomization authority in which canonical
claims, extracted fields, relations, coverage, and packet identity all derive
from immutable exact source bytes. A caller must not be able to manufacture a
valid canonical atom or packet from self-declared digest, text, spans, coverage
or relation endpoints.

The task remains engineering-only with synthetic fixtures. It does not access
private configuration, credentials, accounts, market data, orders or trading.

## Architecture decision

E53 will use five explicit layers:

1. **SourceEvidence** owns copied source bytes, strict UTF-8 index, digest,
   byte length, format and immutable source identity.
2. **FinalizedLedger** partitions those exact bytes. It is the only admission
   authority for automatic `ATOM_CANDIDATE` claim extraction.
3. **CanonicalAtomFactory** creates opaque, immutable atoms from legal source
   spans; IDs, text and evidence digests are recomputed, never accepted from a
   caller.
4. **VerifiedAtomRegistry** admits only factory-finalized atoms bound to one
   SourceEvidence. Typed relations are verified against that registry and the
   exact evidence bytes.
5. **CanonicalPacketFactory** binds SourceEvidence and FinalizedLedger,
   recomputes coverage and semantic validation, then emits canonical JSON and
   a content-derived packet ID.

Alternative considered: retain public frozen dataclasses and strengthen their
`__post_init__` checks. Rejected because a constructor without source bytes
cannot prove atom text, ID, coverage or source identity. A controlled factory
with opaque construction is the smaller trustworthy boundary.

## Work packages and gates

| Work package | Delivery | Exit gate |
| --- | --- | --- |
| WP0 | Claim, one-file plan, Draft PR, source-selection ledger | This first commit adds only this file. |
| WP1 | SourceEvidence and controlled atom factory | Forged ID/text/digest/span/manual atom cases fail. |
| WP2 | Ledger-bound packet and executable fields | Caller coverage/source mappings and mismatched field values fail. |
| WP3 | Registry, typed relations, canonical value domain | Foreign/forged endpoints and non-finite values fail. |
| WP4 | Commit-range hygiene and clean integration manifest | Current tree and every base..head commit are clean or explicitly quarantined. |
| WP5 | Product mutations, bounded corpus, cleanup proof | Actual copied production source mutation makes its gate fail; restoration is green. |
| WP6 | Exact-head Draft-PR Provider six-matrix artifacts | Six canonical artifacts are byte-identical and compare job proves exact count. |
| WP7 | Tested-head receipt-only commit and receipt-head rerun | Receipt is nonempty, placeholder-free, final, and externally bound. |
| WP8 | Independent-verification report and handoff | Every checklist field is linked to a path, SHA, command or Provider object. |

No package may be skipped. S4/Provider/receipt terminology from E52 is not
reused as evidence; E53 creates its own product and provider evidence.

## Verification strategy

The suite will use standard-library `unittest`, deterministic fixtures and
`PYTHONHASHSEED=0,1,777`. It will test byte boundaries, ownership, provenance,
field extractors, relation evidence, canonical JSON domain, packet identity,
history hygiene, mutation fail-closed behavior, corpus counterexamples and
child-process cleanup. No test receives credit merely for import, existence,
printing or an unconditional assertion.

The Provider workflow at
`.github/workflows/codex-e53-night-clean-atomization-closure.yml` will assert
the pull-request event head after checkout, run Python 3.11/3.13 by three hash
seeds, upload canonical plus environment evidence from each job, and compare
exactly six canonical artifacts byte-for-byte.

## Delivery topology and rollback

The plan-only commit is followed by a substantive tested commit before any
receipt. Only after tested-head Provider success may one evidence-only receipt
commit be created. The receipt-head Provider rerun must succeed and no further
commit may follow.

All implementation stays in this E53 program path plus the declared workflow.
Rollback is abandonment of this unmerged Draft PR and branch; no main, frozen
E52, account, data, or configuration state is changed.

## Initial UNKNOWN register

- Provider run, job and artifact identifiers do not exist yet and will never be
  predicted into a receipt.
- Exact E52 blobs eligible for reuse are unknown until the source-selection
  ledger records their hashes and E53 retests them.
- Cross-runtime behavior beyond the required Python 3.11/3.13 matrix remains
  unverified unless public Provider evidence is produced.
