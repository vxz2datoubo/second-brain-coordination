# E18 Gate A-R3 Receipt: Fail-Closed Peer Declaration Composability

- `agent_id`: `CODEX`
- `task_id`: `CODEX-D2-FAIL-CLOSED-PEER-DECLARATION-AND-COMPOSABLE-EPISODE-PROOF-0010-E18`
- `route_epoch`: `18`; `active_issue` / `owner_pr`: `#23` / `#101`
- `gate`: `A_R3_PR101_FAIL_CLOSED_PEER_COMPOSABILITY`
- `status`: `SUCCESS_WITH_FINDINGS / WAITING_FOR_GPT_INDEPENDENT_REVIEW`
- `boundary`: `PUBLIC_SAFE_REMOTE_OUTPUTS / SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`
- `reviewed_base`: `9c3bc2c6797c68a457b28cf2f28d4da1680e626d`
- `tested_head_full_sha`: `6ddd68e8c244d7296f5f980cc93b0a5677f25180`
- `tested_head_parent`: `9c3bc2c6797c68a457b28cf2f28d4da1680e626d`
- `receipt_head_ref`: `THIS_COMMIT`
- `receipt_parent_tested_head_full_sha`: `6ddd68e8c244d7296f5f980cc93b0a5677f25180`
- `completion_signal`: `CODEX_E18_D2_FAIL_CLOSED_PEER_DECLARATION_AND_COMPOSABLE_EPISODE_READY_FOR_GPT_REVIEW`

## Main Result

Malformed `PEER_TO_PEER_TRANSFER` declarations now terminate as explicit,
deterministic, zero-mutation `BLOCKED` declaration aborts. The independent
episode verifier accepts those honest terminal histories, so their resulting
`EpisodeState` can be supplied as `prior_episode_state` to a later external or
valid reciprocal peer action.

The declaration path is intentionally narrower than normal peer settlement.
It records group-shape and exact declaration faults, preserves action-to-event
binding, requires deterministic one-event-per-action ordering, rejects any
fill or owner/system mutation, and disallows external flows. An altered
reciprocal commit cannot be relabelled as a declaration abort: the verifier
emits an independent reciprocal-action failure in addition to reconstruction
mismatches.

No participant identity claim, real market data, replay, strategy, account,
order, broker, credential, or production surface changed.

## Authorized Delivery And Rollback

Substantive tested paths:

1. `d2_game_core.py`
2. `tests/test_d2_game_core.py`

The tested-to-receipt delta contains only this receipt. Roll back by reverting
the substantive tested commit, then the receipt-only commit. A rollback must
not release Gate B, C, or D.

One local public-safe checkpoint ref was created at the tested head:
`codex/checkpoint-a-share-multi-agent-game-engine-0001-d2-e18`. Its first
ordinary push was interrupted by a Git HTTPS connection reset; no force-push,
reset, amendment, or history rewrite was used. The PR branch remains at the
reviewed base until ordinary fast-forward publication succeeds.

## Verification Evidence

Environment: Windows `10.0.22631.0`, Python `3.13.13`.

```text
python -B -m unittest discover -s tests -p test_d2_game_core.py
# exit 0; 91 tests passed for PYTHONHASHSEED=0, 1, and 42
python -m py_compile d2_game_core.py
# exit 0
python -B tests/run_determinism.py
# exit 0; stable ledger hash for PYTHONHASHSEED=0, 1, and 42
```

The focused suite grew from 76 to 91 tests, including 15 E18 regressions:
lone and mismatched declarations, missing transfer/counterparty/order,
three-member, same-side, non-reciprocal, and non-adjacent declarations;
identity reuse; member/event injection; relabelled commit; terminal matrix; and
composable prior-state cases.

All three deterministic runs emitted:

```text
D2_LEDGER_SHA256=e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc
```

Three clean full-repository Git archives from the tested head were byte-stable:

```text
SHA-256=3b8b21f4c52726461b985d128256068d28826bd4487203f5b73d09c22b255496
bytes=1935360
```

`git diff --check` passed. The non-disclosing credential-pattern scan of the
substantive base-to-head diff returned zero matches.

## Calibration, Findings, And Remaining Gates

The observed repair matches the E18 forecast: malformed declarations remain
fail-closed while their validly recorded terminal state is composable; forged
or mutated histories are rejected by both semantic invariants and deterministic
reconstruction. The adjacent invalid-order guard now rejects an arbitrary
order value before any attribute access.

Preserved `UNKNOWN`: trusted timestamping, root-capsule origin authentication,
and canonical registry publication require later trust-anchor work. Atomic
peer resource effects remain `NOT_IMPLEMENTED_YET`. Gate B/C/D, Issue #92,
evaluation V2, real data, replay, backtest, fitting, account, order, and trade
remain closed. GPT alone may accept, reject, or release a later gate; no
self-approval or merge occurred.
