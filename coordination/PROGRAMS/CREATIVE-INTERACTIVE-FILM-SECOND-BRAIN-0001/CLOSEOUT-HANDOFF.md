# Continuous-build close-out handoff — Creative Runtime

agent_id: CODEX

## Audit status

**Executor status:** `EXECUTOR_VERIFIED_ONLY`  
**Requested next actor:** `GPT_INDEPENDENT_REVIEWER`  
**Integration status:** no pull request has been created or merged by CODEX.  
**Authority:** this document requests an independent audit only. It does not
authorize deployment, public release, external generation, customer-data
intake, credentials, canonical knowledge writes, or merge.

## Exact audit target

- Branch: `codex/creative-runtime-continuous-build`
- Implementation baseline:
  `1a514fe839b1c47a14d7fad4a96e8c9fd2365338`
- Audit commit: resolve the remote branch head recorded with the final
  close-out message before starting. The close-out message intentionally
  supplies the immutable SHA, so this committed document never asks a reviewer
  to infer a moving branch tip.
- Frozen historic candidates — do not modify, import, or revive:
  `#493`, `#495`, `#502`, `#506`, `#508`, `#511`, `#513`.

## What this continuous build adds

This is an offline, synthetic, deterministic vertical slice for a future
interactive-film product. It is not a live service.

1. **Truthful interactive story runtime.** Three bounded synthetic scenarios
   use append-only events, stable hashes, strict graph transitions, deterministic
   prefix replay, resumable sessions, and fail-closed timeline validation.
   A past state is reconstructed from its own event prefix rather than being
   backfilled from the final state.
2. **Director compilation and verification.** Every reachable story prefix is
   compiled into a constrained director brief with profile, asset, camera,
   lighting, sound, performance, axis, duration, knowledge, and content gates.
   `CreativeDirectorReviewBoard/v1` renders a review card for every prefix and
   proves that it rebuilds identically from the scenario evidence.
3. **Evidence-bound player.** The static player is render-only and accepts only
   a verified offline artifact/package. It displays transition IDs, timeline
   hashes, visible director evidence, trace IDs, and precomputed choice
   consequences. Free text is only mapped to exact, predeclared safe intent
   phrases; uncertain, unsafe, or unavailable text asks for clarification and
   cannot mutate story state.
4. **Multi-scenario offline library.** `CreativeRuntimeExperienceLibrary/v1`
   binds the Night Signal and Harbor Protocol artifacts to one catalog identity
   and one source Git SHA. The package builder/verifier creates a fixed local
   bundle and rejects changed members, manifests, catalog identity, or static
   player bytes.
5. **Local-only lifecycle safeguards.** Session slots are confined; stale and
   duplicate realtime commands are guarded; v1-to-v2 migration preserves the
   original source bytes; malformed, tampered, unrepresentable, or unsafe legacy
   sessions fail closed and do not create a shadow default session.
6. **Knowledge and user-understanding boundaries.** Derivations stay as
   evidence-backed, human-review candidates. The runtime maps explicit inputs,
   inferred state, explainable evidence, and opaque/out-of-scope areas, with
   numeric anchors and drift gates. No candidate writes to canonical knowledge.

## Contract and interface inventory

| Area | Auditable contract / entry point |
| --- | --- |
| Event truth | `CreativeEvent/v1`, ledger hash chain, `StoryGraph`, prefix replay |
| Session truth | `CreativeSession/v1`, v2 immutable source binding and migration guards |
| Director | `DirectorBrief`, shot plans, `CreativeDirectorReviewBoard/v1`, `creativectl director-review` |
| Player | `VerifiedExperienceArtifact/v1`, static `apps/web/verified_experience_player.html` |
| Scenario library | `CreativeRuntimeExperienceLibrary/v1`, `CreativeRuntimeExperienceLibraryPackage/v1` |
| Input safety | exact safe-text intent mapping with no state mutation on rejection |
| Knowledge | review-only evidence packets; named human review is required before reuse |
| Reproduction | `tools/verify_creative_runtime.py`, library package builder/verifier |

## Required independent reproduction

Use a fresh GitHub checkout, not a CODEX worktree. First compare the remote
branch SHA with the exact SHA in the final close-out message. Replace
`<EXACT_HEAD>` only after that comparison succeeds.

```powershell
python -m unittest discover -s tests -p "test_creative*.py" -v
python tools/verify_creative_runtime.py --expected-head <EXACT_HEAD>
$package = Join-Path $env:TEMP "creative-runtime-independent-library"
python tools/build_experience_library_package.py --expected-head <EXACT_HEAD> --output-dir $package
python tools/verify_experience_library.py --expected-head <EXACT_HEAD> --package-dir $package
python apps/cli/creativectl.py director-review --scenario night_signal
```

The second command is the principal end-to-end proof. It verifies exact Git
identity, clean worktree, full dependency-free creative suite, whitespace,
three-scene play-through, all-prefix timeline/director consistency,
understanding-map drift checks, review-only knowledge derivation, migration,
session isolation, offline generation simulation, and absence of a real
provider path.

For a narrow boundary spot-check, the following searches should produce no
runtime networking/credential patterns in the scoped offline paths:

```powershell
rg -n --glob '*.py' '(requests\\.|urllib\\.request|httpx|openai|anthropic|os\\.environ)' creative_runtime apps/cli tools
rg -n --glob '*.html' '(fetch\\(|XMLHttpRequest|WebSocket|navigator\\.sendBeacon|https?://|<script[^>]+src=)' apps/web
```

## Failure and attack cases already covered by tests

- A hash-valid event whose action, transition ID, or resulting patch disagrees
  with the graph is rejected; no plausible-but-false timeline is emitted.
- A forged post-prefix migration bridge is rejected unless its source binding
  and bridge position exactly match the immutable migrated source.
- Legacy `listen -> approach -> leave` is rejected when the current mapping
  would silently add a new `clue=heard` fact. The original file remains byte
  identical and no default save masks it.
- Unknown actions, corrupt JSON, path escapes, stale commands, duplicate
  command IDs, altered library files, altered manifests, altered static player
  bytes, altered director cards, and altered source shots all fail closed.
- Unsafe/non-explicit-boundary free text, ambiguous text, and text not present
  in the verified phrase hints never become a new model instruction or a story
  mutation.

## Executor clean-reproduction evidence

Before this handoff, CODEX ran the full verifier from the separate clean clone
`F:\\aidanao-worktrees\\standalone-clones\\second-brain-continuous-build-verify`
against the pre-handoff implementation commit
`71751fb099a957a81bcfabc9f66819ae0c11e02d`.

- `python tools/verify_creative_runtime.py --expected-head 71751...` passed.
- The clean clone reported `unit_test_status=pass`, clean-worktree identity,
  whitespace check, all three director review boards, and the synthetic
  end-to-end lifecycle.
- The multi-scenario package build and verifier passed with two scenarios and
  three package members. Its manifest SHA-256 was
  `74e311388c1a56acae7b8fa579095cd719395c285524b695f36d08ad61c645a5`;
  its library SHA-256 was
  `6fd1e6d52189d94ea5be30513f518b3304f6955230ba80149865d4b908db3dea`.

This is **executor clean reproduction**, not independent acceptance. Repeat it
against the final exact audit commit before issuing a verdict.

## Scope and known limits

- The player is static/offline and has no real browser-driven customer session
  test, external account, media provider, payment, deployment, or telemetry.
  Structural tests and the full Python runtime suite cover the artifact path;
  a local Node syntax probe was unavailable in this environment and is not
  claimed as passing evidence.
- Scenarios, adults, assets, and generation results are synthetic. No Eustia or
  other local/WorkBuddy material was imported.
- No real user/corporate data may enter this branch. A future local intake
  adapter requires separate user approval, an approved retention model, and a
  non-Git runtime directory.
- GitHub Actions should be checked for the exact final head as supplemental
  observable evidence, but a green run is not an independent-review verdict.

## Reviewer decision protocol

1. Record the exact reviewed SHA and the commands actually executed.
2. Confirm the reviewer did not author the audited implementation.
3. Return one explicit result: `ACCEPT`, `CHANGES_REQUIRED`, or `BLOCKED`.
4. A rejection must name the broken invariant and a reproducible input. A repair
   must be released as a new clean task/branch; do not edit a frozen candidate.
5. An acceptance is still not a merge. The GPT integrator must apply the
   project authority chain and the user's release/risk decision separately.

## Rollback

Nothing is merged by this close-out. The immediate rollback is to leave this
branch unmerged and start a fresh successor from a verified base. If a future
authorized merge must be reverted, use ordinary revert commits in reverse
order; never force-push, rebase, amend, reset, or rewrite shared history.
