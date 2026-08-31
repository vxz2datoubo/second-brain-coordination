# Continuous Next Checkpoint — Verified Synthetic Replay Export

agent_id: CODEX

This is an executor checkpoint for the continuing implementation branch. It
does **not** request GPT review, mark a candidate ready, accept a change, or
authorize a merge/deployment/customer intake action.

## Exact baseline and code checkpoint

- parent audited continuous-build head: `a9a85bda200a7160fb244186e4c71c8c28b6463c`
- continuing branch: `codex/creative-runtime-next`
- current code checkpoint head: `dca51287ad487b0ede2ee225cbfa8a97ada1496b`
- implementation commits:
  - `38f6c92b29b9ec5a13a194150e069abfe8db36a9` — verified replay capsule
  - `f30854a8ae52593a3c3b8910df98dd11ed858efc` — fixed portable replay package
  - `ae305b12bfa9afaed0cc518bef8a1b8e7c769eeb` — exhaustive replay corpus
  - `f6007632f126095b39a38a544044a85731e6e859` — portable exhaustive replay-corpus package
  - `9dad166ab85c4037e79293a7bd34e6b443db2b8e` — immutable per-process corpus-build cache
  - `dca51287ad487b0ede2ee225cbfa8a97ada1496b` — source-bound branch review board

Rollback is Git-native: leave the preceding audited branch untouched, or
select the preceding exact commit in a new review/implementation branch. Do
not force-push, amend, reset, or rewrite either branch.

## Delivered vertical capability

One fixed-graph, canonical-choice playthrough can now be exported as a
`CreativeSyntheticReplayCapsule/v1` and, separately, as an exact-head-bound
four-file package:

1. `replay_capsule.json` — source events plus independently rebuilt timeline,
   experience, sequence, director result, coverage and declared boundary.
2. `verified_replay_capsule_player.html` — local read-only renderer; no story
   mutation, model/provider invocation, network request, account, cookie or
   browser persistence.
3. `README.md` — the offline use and verification path.
4. `replay_capsule_package_manifest.json` — exact member digests and source
   Git SHA.

`python tools/build_replay_capsule_package.py --workspace <synthetic-workspace>
--expected-head <SHA> --output-dir <new-directory>` refuses to overwrite any
existing directory. `python tools/verify_replay_capsule_package.py
--expected-head <SHA> --package-dir <directory>` requires the fixed member set,
checks the manifest and checked-out viewer/guide bytes, then reconstructs the
capsule from its source event ledger through the live exact-head contracts.

The exporter fails closed before it writes a package if any recorded action is
caller-authored `say` text, an unknown/non-canonical action label, a forged
patch, an altered transition, an unregistered initial scenario, an invalid
ledger, an incomplete route graph, or a failing director quality gate. It does
not create a shadow/default session on failure.

## Portable exhaustive replay-corpus package

Every completed safe terminal route across all registered synthetic scenarios
can now be exported as one fixed five-file package:

1. `replay_corpus.json` — exact-head corpus containing all 38 source-bound
   route capsules.
2. `replay_review_board.json` — exact source-derived comparison of every real
   branch point and the verified terminal deltas behind each legal choice.
3. `verified_replay_corpus_viewer.html` — local, read-only route index; it
   can display a route but cannot calculate a state, accept a choice, persist
   data, call a network/provider, or acquire story authority.
4. `README.md` — offline opening and verification instructions.
5. `replay_corpus_package_manifest.json` — exact member digests and the
   source Git SHA.

`python tools/build_replay_corpus_package.py --expected-head <SHA>
--output-dir <new-directory>` refuses to overwrite a path and atomically writes
the package. `python tools/verify_replay_corpus_package.py --expected-head
<SHA> --package-dir <directory>` requires precisely the fixed members,
rebuilds every route from the checked-out graph, checks all capsule/timeline/
director contracts, verifies all 26 real branch comparisons and compares the
static viewer and guide bytes to the exact source. A changed route, missing
scenario, forged transition, altered terminal delta, modified member or extra
file fails closed.

The GitHub offline workflow now includes a Python 3.13-only
`synthetic-replay-corpus` job. It builds, verifies and retains the package for
seven days under `creative-runtime-replay-corpus-<exact-SHA>`. This is a
downloadable synthetic evidence artifact, not deployment, publication,
customer intake, provider generation or an acceptance decision.

## Exhaustive replay corpus

`python tools/build_replay_corpus.py --expected-head <SHA> --output-file
<new-file>` constructs a `CreativeSyntheticReplayCorpus/v1` directly from the
bounded production graph coverage, not from a local player workspace. It
contains a verified replay capsule for every terminal safe route across every
registered scenario. `python tools/verify_replay_corpus.py --expected-head
<SHA> --corpus <file>` rejects any changed Git identity, scenario set, route
metadata, action/transition, capsule, director field or source-bound timeline.
It also refuses an already existing output file rather than overwriting it.

At `ae305b12bfa9afaed0cc518bef8a1b8e7c769eeb`, a clean clone built and
verified 38 routes: `harbor_protocol: 14`, `legacy_archive: 6`,
`night_signal: 12`, and `three_scene: 6`. The corpus ID was
`replay_corpus_5a7e5d55977bd620ee6c`; its byte hash was
`00545b904a14ff2c328371ce9a80e9c706dcd94fc09d1390ec7151e0e8c1c110`.

## Reproduction evidence

At `f30854a8ae52593a3c3b8910df98dd11ed858efc` (historical dual-runtime
evidence, before the daily-runtime policy changed):

| Check | Result |
| --- | --- |
| Targeted capsule + package suite | 8/8 passed |
| Full creative suite on Python 3.13 | 123/123 passed |
| Full creative suite on Python 3.12 | 123/123 passed |
| `git diff --check` | passed |
| Independent clean-clone verifier | passed |

The clean verifier ran from
`F:\aidanao-worktrees\standalone-clones\second-brain-continuous-build-verify`
at the exact current head with:

```text
python tools/verify_creative_runtime.py --expected-head f30854a8ae52593a3c3b8910df98dd11ed858efc
```

Its receipt confirms a 4-event three-scene route, matching timeline hash
`26f33b0088141765a68202ca51503c7516cac86394123504323fe5247a85d964`, matching
capsule/package ID `capsule_09fe81517beb47fdb780`, a three-member package
payload plus manifest, and `contains_caller_free_text: false`. It remains
executor-provided reproducibility evidence, not independent acceptance.

After the corpus commit, the full creative suite increased to **126** tests
and passed historically on both Python 3.13 (157.153 seconds) and Python 3.12
(165.417 seconds). The deliberate increase is the cost of all-route
reconstruction, not a hidden remote service or paid operation. The clean clone
also passed the same 126-test runtime verifier at exact head
`ae305b12bfa9afaed0cc518bef8a1b8e7c769eeb`.

## Daily verification policy (current)

From this checkpoint forward, routine local milestones and the GitHub offline
workflow run the suite **once**, on Python **3.13**. The earlier Python 3.12
result remains historical compatibility evidence; it is not repeated by
default. A second interpreter is allowed only for an owner-requested
compatibility promise, a supported-runtime change, or an explicitly approved
release gate. At the measured 126-test size this avoids roughly 165 seconds of
additional local compute for each otherwise identical full milestone run.

At exact head `9dad166ab85c4037e79293a7bd34e6b443db2b8e`, the 131-test Python
3.13 suite passed in **225.036 seconds**. Before the immutable
per-process replay-corpus cache, the same evolving suite took 525.661 seconds
for 130 tests because multiple test cases re-built the identical 38-route
corpus independently. The cache stores only canonical JSON for one exact head
inside one Python process, then returns fresh parsed objects; a caller cannot
mutate later checks. Each command-line builder/verifier and clean clone remains
a new process and performs its own full source reconstruction.

The task-owned clean clone
`F:\aidanao-worktrees\standalone-clones\second-brain-continuous-build-verify`
checked out that exact head with a clean worktree and independently built then
verified the package. Its verified corpus had 38 routes
(`harbor_protocol: 14`, `legacy_archive: 6`, `night_signal: 12`,
`three_scene: 6`), corpus ID `replay_corpus_5241b519ef39af8c410d`, corpus
SHA-256 `66a9019c8f8cc072981f321a6f26ccbf7c6430f4d2b25c2ba150cc9ee8bc3f5e`,
and manifest SHA-256
`fd4899c00a5ffe0edcdc1e43b836bcf68265a787568ddd200228d23baeff4d52`.
This is executor clean-reproduction evidence, not independent acceptance.

At exact head `dca51287ad487b0ede2ee225cbfa8a97ada1496b`, the expanded
**135-test** Python 3.13 suite passed in **234.601 seconds**. The task-owned
clean clone rebuilt and verified the new five-file package with a clean
worktree: 38 routes, 26 source-derived branch points, corpus ID
`replay_corpus_b32460830935f375e519`, review-board ID
`replay_review_6051177c3d40386abdcd`, corpus SHA-256
`34316066d678141b4eabad902ca046961a4e7a31fcb7ccc12f97f7b787b89eb1`,
review-board SHA-256
`c0d1ca11cffa78c4365fffcc03d3e82cfc397e32ab6973f5a27be95acb007771`, and
manifest SHA-256
`7a2c97ae837a9925d79eb47b3918c43ec816e148c610fea19c295ea9663fb130`.
This is again executor clean-reproduction evidence, not independent acceptance.

## Still deliberately out of scope

- customer content, customer-vault reads, account/cookie/credential access;
- any external or paid generation request;
- public deployment, publication or production release;
- transaction paths and canonical knowledge writes;
- altering frozen PRs #493, #495, #502, #506, #508, #511 or #513;
- GPT review/merge/Ready status before the owner explicitly asks for closeout.

## Next build frontier

Continue the synthetic runtime without interrupting for micro-reviews. The
highest-value adjacent work is now to make the verified corpus more useful for
human review without weakening its read-only authority: reviewer-oriented
filters over the existing source-bound branch board, concise film-language
explanations of continuity differences, and a review packet that still never
exports customer sessions or lets the browser calculate story state.
