# E52 Project Plan: strict byte truth, semantic evidence, and Provider closure

## Identity and authority

- `task_id`: `CODEX-QCLAW-E40-TAKEOVER-STRICT-BYTE-TRUTH-EXACT-OWNERSHIP-SEMANTIC-EVIDENCE-AND-PROVIDER-CLOSURE-0048-E52`
- `route_epoch`: `54`
- `agent_id`: `CODEX`
- `reviewer`: `GPT`
- `remote_main_at_claim`: `3d15f0c62877db5841b985f740e9bc348f65ddc5`
- `planned_branch`: `codex/qclaw-e40-takeover-strict-byte-closure-0048-e52`
- `source_status`: `QCLAW_E40_PARTIAL_CANDIDATE_FROZEN`
- `source_frozen_head`: `e58b39fcabbe9dae4f75a6570c86a88754176766`
- `completion_signal`: `CODEX_E52_QCLAW_E40_TAKEOVER_STRICT_BYTE_PROVIDER_CLOSURE_READY_FOR_GPT_REVIEW`

E52 is the sole successor for the remaining E40 closure.  The frozen QCLAW
branch is read-only candidate material.  This task will never merge, rebase,
cherry-pick wholesale, or write to it.  Each later selected source blob is
recorded in `E40-SOURCE-SELECTION.yaml` before it is copied, adapted, or
rewritten.  Imported material is `UNTRUSTED_CANDIDATE` until E52's own product
tests, source mutations, and provider evidence pass.

## Fundamental goal

Create a reproducible, public-safe atomization pipeline whose semantic output
can be traced back to an exact, gapless and disjoint original-byte ownership
ledger.  The pipeline must fail closed for malformed input, unsafe redaction,
invalid semantic claims, incomplete provenance, and missing provider artifacts.
It is not a market-data, credential, account, model-provider, or trading task.

## Scope and non-negotiable boundaries

Permitted repository paths are only this E52 program directory and
`.github/workflows/codex-e52-qclaw-strict-byte-closure.yml`.  Fixtures are
synthetic and public-safe.  E52 does not read or change model settings,
provider/default/session/workspace/private configuration, credentials, accounts,
orders, funds, market data, or the WorkBuddy route.  Direct `main` writes,
auto-merge, force-push, and history rewriting remain forbidden.

## Recoverable phase plan

| Phase | Required implementation and proof | Exit gate |
| --- | --- | --- |
| Plan/source selection | Create this one-file plan first; then exact E40 blob ledger, frozen-source reproduction evidence, and a Draft PR/lease. | First commit changes this file only; selection ledger has no imported code credit. |
| Reproduce failures | Add red regressions for every recorded E40 defect before replacing production candidates. | Each regression demonstrably fails against its copied E40 candidate or otherwise records an exact unsupported claim. |
| S0 | Immutable `ByteTruthIndex`; EOF-exclusive boundary-to-codepoint API; separate containing-byte API; actual production 0xED non-progress mutation with reaped child; shared `LineRecord`. | Direct private, collection, alias and item mutation fail; all line forms have no zero-length owner spans. |
| S1 | Finalized exact-one-owner ledger and six adapters. | Every input byte has exactly one `ATOM_CANDIDATE`, `STRUCTURE`, or `UNKNOWN_ERROR` owner; no gaps/overlaps/duplicates. |
| S2 | Production irreversible redaction. | No safe-example bypass and no returned/persisted secret-derived bytes, hashes, or fingerprints. |
| S3 | Schema-governed atoms, executable relations, and full canonical packet. | Fields/provenance/UNKNOWNs validate; relation endpoints/evidence are real; packet holds full canonical content. |
| S4 | Product validators and copied-production mutation harness. | A mutation of real copied source makes the target product gate fail nonzero and restoration is green. |
| S5 | Draft-PR provider matrix and six byte-identical canonical artifacts. | Python 3.11/3.13 times seeds 0/1/777 pass at the exact tested head; compare job proves six artifacts are present and identical. |
| S6 | Nonempty evidence-only receipt after tested-head CI, then receipt-head CI. | Placeholder-free receipt has externally bound provider facts; receipt remains the final task commit. |

## Required failure reproductions

Before any green replacement, E52 must reproduce or explicitly disprove with
an executable regression all reviewed E40 claims: mutable private index state;
missing boundary-to-codepoint mapping; non-production 0xED mutation; EOF
zero-length spans; malformed JSON/trailing-byte misclassification; JSONL blank
line/terminator loss; conversation role/colon offset drift; `safe_examples`
secret bypass; secret-bearing redaction candidate; default-only atom fields;
relation acceptance without valid evidence/endpoints; counts-only packets;
shallow validators; invalid workflow matrix reference; and placeholder or
signal-mismatched receipt.  A passing Boolean helper is not reproduction.

## Data and semantic invariants

1. `codepoint_index_at_boundary(offset)` accepts only codepoint boundaries in
   `[0,total_bytes]`, maps EOF to `codepoint_count`, and rejects continuation
   and out-of-range offsets. `chunk_containing_byte(offset)` separately accepts
   only `[0,total_bytes)` and may locate continuation bytes.
2. `LineRecord` carries non-empty content and terminator spans where they exist;
   trailing-empty-line state is explicit rather than represented as a zero-byte
   ownership span.
3. JSON, JSONL, Markdown/TXT and structured conversation preserve original
   bytes. Invalid grammar or trailing bytes becomes `UNKNOWN_ERROR` or fails
   closed; it is never silently converted to whitespace.
4. Atom defaults have declared source/default rules and UNKNOWN reasons.
   Automatic extraction never upgrades directly to `FACT`.
5. Relations require a typed evidence object, source-byte/span/digest linkage,
   valid endpoints, and at least one executable extraction route.
6. Canonical packet identity hashes its complete canonical payload while
   excluding self-referential identity fields.

## Test and Provider evidence design

Local tests use only synthetic fixtures.  Mutation tests create a temporary
copy of the actual E52 production module, alter the relevant branch, run the
real scanner/gate in a bounded child process, collect the required nonzero
failure, kill/reap children on every exit path, and verify a restored source
returns green.  Validators receive no credit for imports, existence, printing,
documentation, or unconditional truth assertions.

The Draft-PR workflow checks out the exact event head and asserts it.  It runs
the same suite under Python 3.11 and 3.13 with `PYTHONHASHSEED=0,1,777`.  Each
matrix job produces a byte-stable `canonical-evidence.json` and a separate
environment-specific evidence file.  Uploads fail for missing artifacts; the
compare job requires exactly six canonical artifacts and compares their bytes.
The same matrix is required at the tested and receipt heads.

## Control files and delivery topology

After this plan-only commit, E52 will add: an exact source-selection ledger;
reproduction, research, discovery, UNKNOWN, test, WPDCR, AMED and handoff
artifacts; implementation/tests under this program directory; and the one
workflow file.  The tested commit contains executable implementation and tests.
Only after independently visible tested-head provider success may a single,
nonempty, receipt-only commit be added.  No later E52 commit is allowed.

## Rollback and stop conditions

All work is confined to a normal descendant branch and new allowed paths, so
rollback is branch/PR abandonment without touching `main` or QCLAW E40.  Stop
and request GPT direction for a route-epoch change, missing lease/forecast
fields, accidental protected-path change, secret-bearing input, any real data
or trading surface, or a provider result that cannot be independently bound to
the exact branch head.

## Initial UNKNOWN register

- The exact E40 candidate files worth retaining are not yet accepted; selection
  requires blob-level inspection and failure reproduction.
- No E40 provider matrix run/artifact proof is accepted as E52 evidence.
- The final provider-run IDs and receipt-head external facts do not exist yet
  and will not be predicted or placed in a receipt placeholder.
