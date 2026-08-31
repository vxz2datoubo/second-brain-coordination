# Continuous Next Checkpoint — Verified Synthetic Replay Export

agent_id: CODEX

This is an executor checkpoint for the continuing implementation branch. It
does **not** request GPT review, mark a candidate ready, accept a change, or
authorize a merge/deployment/customer intake action.

## Exact baseline and current head

- parent audited continuous-build head: `a9a85bda200a7160fb244186e4c71c8c28b6463c`
- continuing branch: `codex/creative-runtime-next`
- current checkpoint head: `f30854a8ae52593a3c3b8910df98dd11ed858efc`
- implementation commits:
  - `38f6c92b29b9ec5a13a194150e069abfe8db36a9` — verified replay capsule
  - `f30854a8ae52593a3c3b8910df98dd11ed858efc` — fixed portable replay package
  - `ae305b12bfa9afaed0cc518bef8a1b8e7c769eeb` — exhaustive replay corpus

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

## Still deliberately out of scope

- customer content, customer-vault reads, account/cookie/credential access;
- any external or paid generation request;
- public deployment, publication or production release;
- transaction paths and canonical knowledge writes;
- altering frozen PRs #493, #495, #502, #506, #508, #511 or #513;
- GPT review/merge/Ready status before the owner explicitly asks for closeout.

## Next build frontier

Continue the synthetic runtime without interrupting for micro-reviews. The
highest-value adjacent work is to make a completed replay package useful in a
larger multi-route regression corpus: deterministic named routes across every
registered scenario, visible per-route director continuity evidence, and an
exact-head index that can be verified without trusting a local workspace.
