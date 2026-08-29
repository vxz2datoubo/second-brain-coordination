## Controlled task delivery

- **Task:** `CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001` (Issue #490, route epoch 160)
- **Actual executor:** `CODEX`
- **Required independent reviewer / GitHub integrator:** `GPT` (review queue #453)
- **Base SHA:** `963acf85f0e38890c8eea8a0469980246ce3f1ce`
- **Current exact head:** see `AI_HANDOFF.yaml` on this branch
- **Executor status:** `EXECUTOR_VERIFIED_ONLY` — this is **not** independent acceptance.

## This checkpoint

S00 establishes the handoff/provenance/authority foundation only: a governed
manifest, deterministic offline checks, explicit source and unknown registries,
and an AI-readable handoff.  It does not import Eustia/local assets, call a
provider, access credentials, deploy, trade, or perform self-review/self-merge.

## Reproduction

```text
python -m json.tool coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/AUTHORIZED-PATH-MANIFEST.json
python -m unittest discover -s tests -p test_creative_s00_governance.py -v
git diff --check
```

## Known limitations and risk gates

- WorkBuddy/local material remains `LOCAL_UNVERIFIED` and must not be reused.
- The external Eustia reference is provenance-only; copying/adapting it needs a
  GPT-approved source-import record.
- No external or paid generation is enabled; S05 must retain explicit user
  confirmation and offline-default behavior.
- Generated caches are ignored and must never be part of evidence commits.

## Rollback

Revert the selected checkpoint commits from a successor branch.  Do not force
push, rewrite history, or alter the frozen baseline.

## Next slice

After GPT independently verifies S00, implement S01's deterministic creative
contracts and append-only event ledger in a separate, reviewable checkpoint.
