# WorkBuddy milestone verification runbook

agent_id: `CODEX`

Purpose: make the user-approved collaboration model executable after a future
governed WorkBuddy route is released. The current WorkBuddy ACTIVE route is
paused, so this document grants no present execution authority.

## Responsibility split

- Codex owns architecture, implementation, acceptance oracles and focused tests
  while editing.
- WorkBuddy locks a pushed exact SHA in a separate clean clone, runs the complete
  reproduction once per meaningful milestone, adds environment-specific probes,
  and reports consolidated findings.
- GPT is activated manually by the user only at `收尾` or `同步` for stage-level
  cross-module review. This runbook does not contact GPT.

## Required clean-clone command

After fetching the authorized branch and detaching at its exact pushed SHA:

```powershell
python tools/verify_creative_executor_checkpoint.py `
  --agent-id WORKBUDDY `
  --expected-head <EXACT_HEAD> `
  --remote-ref refs/remotes/origin/<AUTHORIZED_BRANCH> `
  --baseline <IMPLEMENTATION_BASELINE> `
  --policy-floor-ref <POLICY_FLOOR_COMMIT>
```

The command runs one supported local Python runtime. Multi-version execution is
reserved for a route or CI matrix that explicitly requires it.

## Receipt meaning

- `PASS` means the named executor reproduced the fixed command set from a clean
  worktree whose local and remote identities both matched the exact SHA.
- Captured stdout and stderr are represented by SHA-256 and byte counts, not
  copied into the receipt.
- `independent_acceptance` is always `false`. WorkBuddy may independently find a
  technical defect, but this receipt alone cannot Ready, accept, merge or make a
  candidate canonical.

## Finding format

Every WorkBuddy finding must contain:

1. exact tested SHA and remote ref;
2. exact command and platform;
3. expected behavior and actual behavior;
4. smallest reproducible input;
5. affected and unaffected surfaces;
6. whether the result blocks the milestone or is an improvement proposal.

WorkBuddy does not patch the Codex branch. A future WorkBuddy code task must use
a separate `workbuddy/...` branch and non-overlapping allowlist.
