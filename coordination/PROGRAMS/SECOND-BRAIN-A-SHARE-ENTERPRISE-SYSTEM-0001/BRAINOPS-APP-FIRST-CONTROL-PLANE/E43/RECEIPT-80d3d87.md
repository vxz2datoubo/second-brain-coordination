# E43 Exact-Head Evidence Receipt

- `agent_id`: `CODEX`
- `task_id`: `CODEX-BRAINOPS-TERMINAL-EXECUTION-ATTESTATION-RECOVERY-AUTHORITY-AND-FRESHNESS-CLOSURE-0039-E43`
- `route_epoch`: `45`
- `status`: `READY_FOR_GPT_REVIEW`
- `base_commit`: `925cc111c433823530adbdbef4ded5e332d88afe`
- `branch`: `codex/brainops-terminal-attestation-recovery-freshness-0039-e43`
- `pull_request`: `#136` (Draft)
- `issue`: `#134`
- `parent_issue`: `#31`

## Immutable Commit Topology

| role | SHA | parent | tree |
| --- | --- | --- | --- |
| plan | `7b324cfbbb766689618ca3fd81d9cbe917b949dc` | `925cc111c433823530adbdbef4ded5e332d88afe` | recorded by Git |
| substantive tested delivery | `80d3d87d0caad132bb59a5dfe0bc6878a6af7ec7` | `7b324cfbbb766689618ca3fd81d9cbe917b949dc` | `2878a052d5af62658de0a8eff6bb4fce8d3122f0` |
| receipt only | `THIS_COMMIT` | `80d3d87d0caad132bb59a5dfe0bc6878a6af7ec7` | externally bound in the PR and Issue completion report |

## Exact-Head CI Evidence

Both runs checked out and asserted the substantive SHA before compiling the
E43 package and discovering `test_e43_*.py`.

| run | head | Python 3.11 | Python 3.13 | result |
| --- | --- | --- | --- | --- |
| `30763337910` | `80d3d87d0caad132bb59a5dfe0bc6878a6af7ec7` | pass | pass | success |
| `30763335596` | `80d3d87d0caad132bb59a5dfe0bc6878a6af7ec7` | pass | pass | success |

The workflow command surface is:

```text
git rev-parse HEAD == github.event.pull_request.head.sha || github.sha
python -m py_compile .../src/brainops_control_plane/*.py
python -m unittest discover -s .../tests -p "test_e43_*.py" -v
```

Local synthetic regression: Python 3.12 and Python 3.13 each passed 71 tests;
both compiled the package.  Local Python 3.11 is unavailable, so the
exact-head Python 3.11 result above is the authoritative test evidence.

## Boundaries And Negative Evidence

- No live GitHub authority write, Canary, App Automation, or Codex CLI
  invocation occurred.
- No credential, private configuration, model setting, account, order, funds,
  or trading surface was read or mutated.
- Live runtime authenticity remains `UNKNOWN`; all contract evidence is
  synthetic and must not be promoted to operational authority.
- The legacy evidence classifier is deliberately observational-only until the
  E43 reconciler verifies one durable terminal record against the same
  invocation object.

## Recovery And Rollback

Recovery can only mark an expired original claim `RECOVERY_REQUIRED`; it cannot
impersonate its holder, attach execution evidence, or mint an effect permit.
Rollback is a reviewable reversion of the substantive commit followed by this
receipt commit; no external authority state was created by this delivery.
