# Clean-Clone Runbook

agent_id: CODEX

## Preconditions

- Clone `vxz2datoubo/second-brain-coordination` fresh.
- Check out `codex/creative-interactive-film-second-brain-0001` from GitHub.
- Use Python 3.11+; no dependency installation is required.
- Do not supply credentials, provider configuration, or external source assets.

## Verify identity before code execution

```text
git rev-parse HEAD
git merge-base HEAD 963acf85f0e38890c8eea8a0469980246ce3f1ce
git diff --check 963acf85f0e38890c8eea8a0469980246ce3f1ce...HEAD
git status --short
```

The merge-base must be the published implementation baseline. Reconcile the
actual remote head with `STATUS.yaml` and PR #491; do not treat a remembered SHA
as current truth.

## Verify functionality

```text
python -m json.tool coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/AUTHORIZED-PATH-MANIFEST.json
python -m unittest discover -s tests -p test_creative_s*.py -v
```

Expected result: **22 tests pass**. `python -m pytest -q` is not an equivalent
requirement here because `pytest` is not installed in the validated clean
environment.

## Optional offline-only CLI demonstration

```text
python apps/cli/creativectl.py --workspace .creative-runtime init
python apps/cli/creativectl.py --workspace .creative-runtime say "I listen at the door"
python apps/cli/creativectl.py --workspace .creative-runtime replay
```

The workspace is Git-ignored. The expected result is JSON only: it must not call
a model, create media, contact a provider, or access credentials.

## Rollback

Before merge, freeze or abandon the draft branch and preserve evidence. For a
merged correction, use a normal revert from a successor branch. Never force push,
rebase, amend, or rewrite task history.
