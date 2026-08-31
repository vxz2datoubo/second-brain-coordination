# Offline Runbook — Realtime Interactive Film Game 0002

agent_id: CODEX

## Clean-clone verification

From the exact implementation branch/head recorded in `AI_HANDOFF.yaml`, run:

```powershell
python -m unittest discover -s tests -p 'test_creative_s*.py' -v
python -m unittest discover -s tests -p 'test_interactive_s*.py' -v
```

Both commands are offline and require only Python's standard library. Do not
provide credentials or enable any provider.

## Scripted S07 playthrough

```powershell
$workspace = Join-Path $env:TEMP 'creative-runtime-demo'
python apps/cli/creativectl.py --workspace $workspace init
python apps/cli/creativectl.py --workspace $workspace choose listen
python apps/cli/creativectl.py --workspace $workspace slot save heard
python apps/cli/creativectl.py --workspace $workspace choose knock
python apps/cli/creativectl.py --workspace $workspace transcript
python apps/cli/creativectl.py --workspace $workspace compare default heard
python apps/cli/creativectl.py --workspace $workspace director --duration-budget 90
python apps/cli/creativectl.py --workspace $workspace review-packet --duration-budget 90
```

Expected behavior: the initial scene is `archive_gate/arrival`; `listen` moves
to `archive_gate/echo`; `knock` moves to `interior_archive/threshold`. Output
contains a stable manifest hash and never makes a network/provider call.

`director` exports ordered director packets and continuity diagnostics only;
`review-packet` adds the session/event digests and deterministic transcript. In
both outputs `generation_called` is `false` and no media is produced.

## Save safety checks

Use only names matching lowercase letters/digits/underscore/hyphen. Names such
as `../escape`, `con`, or names with dots are rejected. A corrupt slot must
return an error and leave any valid sibling slot usable.

## Rollback

Do not rewrite history. Preserve the candidate branch and create a new repair
commit or successor branch if a reviewed issue is found.
