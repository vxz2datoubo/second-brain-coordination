# E53 independently checkable execution report

## Disposition

This final repository evidence set is the receipt-only commit planned by
`PROJECT-PLAN.md`. Its exact Git commit SHA and the Provider run caused by that
commit are intentionally external bindings: including either future identity
inside a content-addressed final commit would change the identity itself. They
must be fetched from the sole Draft PR #169 and Issue #168 completion comment,
with no post-receipt repository commit.

The latest fully tested substantive head before this receipt is
`0e6b921ef39c11b932fe7f5624db993fcddc80c2`, parent
`2ec33f71f9fab3ed2c13da7b83f836c8d489cf5e`, tree
`d59156ca483f95ffa167fb91c47abe8c4e0a804d`. The plan-only head is
`3566f238e46685d17f23da693e0399a96e1afbe3`, parent
`a1f7146469082a975dce069942ca0965e7771ab3`, tree
`6a01a48cbf32478e4c7b078e2bbc57533b81527c`.

## Architecture and scope

`SourceEvidence` copies strict UTF-8 bytes and owns SHA-256, byte length and
identity. `FinalizedLedger` requires a total, nonoverlapping byte partition.
`AtomFactory` only issues exact `ATOM_CANDIDATE` spans, recomputes ID/text and
evidence digest, refuses lexical FACT promotion, and reruns field rules from
source bytes. Registry and relation factories accept only issued objects bound
to the same evidence. Packet creation recomputes coverage and forbids `NaN`,
infinity and undocumented JSON types.

All production source is newly written E53 code; the predecessor material is
an auditable selection ledger, not a runtime import. See
`E52-SOURCE-SELECTION.yaml` and `CLEAN-INTEGRATION-MANIFEST.yaml`.

## Commands and results

Local command:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 python -m unittest discover -s <E53>/tests -v
```

Result: exit `0`, 65 tests, 3.401 seconds. Seed-specific exit, duration and
stdout/stderr hashes are in `EVIDENCE-INDEX.json`. Local runtime was Python
3.13; the separate GitHub matrix verified Python 3.11 and 3.13.

Provider workflow:
`.github/workflows/codex-e53-night-clean-atomization-closure.yml`.
Tested run `31029691235` completed `success` on `0e6b921...`; it has six
matrix jobs and compare job `92387048542`. The independent local download
comparison found exactly six canonical files with SHA-256
`7c18f0c176fabb5b2d4c5e5d6ba97d8b2b53570d412d4aa5e6d5c5cf0ecbab79`.
Run log SHA-256 is
`6412956665b9a94a48a8ace7d388eae97da74fb038babca430f12fe815f1ddf3`.

## Mutations and corpus

`MUT-UTF8-STRICT`, `MUT-ATOM-LEDGER` and `MUT-JSON-NAN` copy actual E53
production source to a temporary directory, make exact documented replacements,
run copied `test_source_bound_authority.py` to a nonzero failure, restore copied
source from the E53 original and rerun it green. Details and counterexamples
are in `ADVERSARIAL-VALIDATION-DESIGN.md`; the source mutation harness is
`src/e53_authority/mutations.py`. The bounded corpus includes valid and invalid
UTF-8, JSON, JSONL, text and unsupported format cases. Markdown ownership,
redaction, foreign relations, caller fields, nonfinite values, fake artifacts,
premature receipt and child reaping have explicit tests.

## Failures, retries and residual limits

- The long initial worktree path failed before development; no work was lost.
- A relation parser initially rejected line-ending evidence; it now retains the
  exact range and only removes EOL for syntax recognition.
- Intermediate tested head `2ec33f7...` had a weaker mutation proof. It remains
  documented but is superseded by `0e6b921...` and run `31029691235`.
- Node 20 action deprecation warnings are retained as a follow-up, not silently
  “fixed” beyond task scope.
- This is a provenance/control boundary for public callers, not protection from
  hostile arbitrary Python memory reflection. Additional runtimes are UNKNOWN.

## Boundaries, rollback and handoff

Only synthetic public-safe fixtures were used. No credential, account, private
configuration, market data, fund, order or trading surface was read or changed.
No write was made to `main`, frozen E52, or repository settings. Rollback is to
close the unmerged Draft PR and abandon this branch after approval. GPT should
perform the checks in `AI_HANDOFF.yaml` after the receipt-head Provider run.
