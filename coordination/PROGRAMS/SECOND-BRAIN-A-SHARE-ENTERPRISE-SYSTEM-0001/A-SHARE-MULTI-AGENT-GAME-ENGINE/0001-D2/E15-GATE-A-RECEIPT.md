# E15 Gate A Receipt

- `agent_id`: `CODEX`
- `task_id`: `CODEX-D2-SEQUENTIAL-SEMANTIC-PROOF-EVALUATION-V2-QUARANTINE-AND-PREREG-CLOSURE-0007-E15`
- `route_epoch`: `15`
- `active_gate`: `A_PR101_CORE_PROOF`
- `boundary`: `SYNTHETIC_ONLY / CANDIDATE_INTERFACES / research_only / NO_TRADE`

## Route And Base Reconciliation

GitHub Contents API confirmed `coordination/ACTIVE-CODEX-TASK.yaml` blob
`4de401834438d8bb8a62c097394a7abbab3e66ed` on remote `main`
`cf57c7114587ece09c311a5c05124a437f498588`: schema `16.0`, E15,
`READY`, `execution_allowed: true`, and Gate A active. Direct `git fetch origin
main --prune` was attempted but failed with Git HTTPS `Recv failure: Connection
was reset`; the stale local `origin/main` was not used as route authority.

The local recovery bridge is content-equivalent, not a false commit-ancestry
claim:

| object | commit | parent | tree |
|---|---|---|---|
| local baseline | `80f70013d097f57d21cbc60db82870a316e84a3c` | `95237b0f6f373cbf5823c7fa6948f73e78eb6c50` | `36034f2523d327d6c5b9d024c93e3dbff29517c5` |
| remote reviewed Gate A head | `9e694d1cca3fd867fe5b1d2deb6a7c3868546ae6` | `1b7a1b896d778fbf525d3b9bb70920e24fd315c1` | `36034f2523d327d6c5b9d024c93e3dbff29517c5` |
| remote tested commit | `9a1c50eb2fd26bbf4dfd029152cceaca15bf1a3d` | `9e694d1cca3fd867fe5b1d2deb6a7c3868546ae6` | `61d7583d8ae8abe87af6f26c7efcc5b99337ff80` |

Therefore the remote tested commit is a direct child of the reviewed PR head.
The local baseline and remote reviewed head share an exact tree, but have
different parents; they are a verified tree bridge, not literal ancestors.
The preserved local recovery commits were `f6ddfe7a7b379dfb7b9798d9504c23a9e7e95956`
then `4bce7eca2da7aa37168b10f8415cf8bff7138e98`. Their two D2 files were
selectively migrated without publishing either partial commit.

## Tested Delta

The substantive tested tree changes exactly these authorized Gate A paths:

1. `d2_game_core.py`
2. `tests/test_d2_game_core.py`

It adds an immutable episode carrier, pre-emission replay rejection, explicit
claim/release/expire lifecycle handling, separate external-flow and matched
peer-transfer accounting, and an independent reducer-based ledger verifier.
External synthetic inventory offsets are recorded as explicit flow events;
they are accounted, never described as closed-system conservation.

## Reproducible Evidence

Environment: Windows `10.0.22631.0`, Python `3.13.13`.

Focused command:

```text
python -m unittest tests.test_d2_game_core -q
```

Result: exit `0`, `36` tests passed. Syntax check also passed:

```text
python -m py_compile d2_game_core.py tests\test_d2_game_core.py
```

Three clean Git-archive extractions were created from tree
`61d7583d8ae8abe87af6f26c7efcc5b99337ff80`. In each extraction:

```text
PYTHONHASHSEED=<seed> python -m unittest tests.test_d2_game_core -q
PYTHONHASHSEED=<seed> python tests\run_determinism.py
```

| seed | unit exit | unit stdout SHA-256 | unit stderr SHA-256 | deterministic ledger SHA-256 |
|---|---:|---|---|---|
| `1` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `f8699593c035b38b9c0e559585e53f9b4297fb0b8b6a84340b6849301d1acdcd` | `d68b3308eeff16af6aad6c2124131d1df3ff50c0ce41717280bb2795aa7be524` |
| `777` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `7ac2ae70d65477c0e89eecae1974ec43a8c76ee3575fb7919895457aca9fb79b` | `d68b3308eeff16af6aad6c2124131d1df3ff50c0ce41717280bb2795aa7be524` |
| `2027` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `101e5ee43a3003cf9518dce6c236de935c6a39dac29fed06f3ba54c28ec3d25f` | `d68b3308eeff16af6aad6c2124131d1df3ff50c0ce41717280bb2795aa7be524` |

The varying unit-test stderr hashes contain elapsed time only. The normalized
deterministic ledger output and its stdout SHA-256
`2139a13bdf0d4b99b6437925e153f446a5075debe33c47e3e3cd36e96f62b613`
match across all three clean archives.

Public safety scan over the substantive paths found no credential-pattern
matches. No real market source, replay, fitting, account, order route, or trade
was invoked.

## Gate Boundary

This is the receipt-only follow-up to the tested commit. Its own commit SHA,
parent, tree, PR #101 anchor, and Issue #23/#31 anchors are recorded externally
after publication; this file deliberately does not contain a self-referential
commit hash. Gate B, Gate C, Gate D, PR #102, PR #103, and PR #105 remain
untouched.
