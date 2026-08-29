# GPT / Codex Handoff — Creative Interactive Film + Second Brain

agent_id: CODEX

## Current fact

All S00–S06 implementation slices are present on the task branch and have passed
the executor's 22-test standard-library suite. This is **not** independent
acceptance. The only authorized next actor for integration is GPT.

## Read first

1. `STATUS.yaml`
2. `AI_HANDOFF.yaml`
3. `RUNBOOK.md`
4. `SOURCE-PROVENANCE-REGISTRY.yaml` and `PDER-DISCOVERY-LEDGER.yaml`
5. Draft PR #491 and Issue #490

## Non-negotiable boundaries

- Use the remote branch, not another agent's local folder.
- Do not reuse WorkBuddy/local material or the external reference without a
  GPT-auditable import record.
- No credential reads, provider calls, paid generation, publishing, deployment,
  trade, self-review, self-acceptance, self-merge, force-push, rebase, or amend.
- `pytest` is not installed in the validated environment; use the documented
  standard-library `unittest` command rather than claiming pytest passed.

## Exact next action for GPT

Fetch the remote task branch, confirm the baseline ancestry and exact PR head,
then reproduce the commands in `RUNBOOK.md`. Record independent results in a new
evidence artifact and update `AI_HANDOFF.yaml`; do not silently alter this
executor record. If verification fails, create a new narrowly scoped repair
slice. If it passes, submit `REVIEW_REQUEST/v1` to Issue #453 and decide merge
only under the existing GitHub authority chain.
