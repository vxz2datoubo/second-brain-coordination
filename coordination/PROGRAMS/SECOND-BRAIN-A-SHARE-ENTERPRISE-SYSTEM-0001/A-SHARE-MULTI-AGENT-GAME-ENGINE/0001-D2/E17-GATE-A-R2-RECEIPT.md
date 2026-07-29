# E17 Gate A-R2 Receipt: Atomic Peer Settlement

- `agent_id`: `CODEX`
- `task_id`: `CODEX-D2-ATOMIC-PEER-TRANSFER-AND-CLOSED-SYSTEM-SETTLEMENT-PROOF-0009-E17`
- `route_epoch`: `17`; `active_issue` / `owner_pr`: `#23` / `#101`
- `gate`: `A_R2_PR101_ATOMIC_PEER_SETTLEMENT`
- `status`: `SUCCESS_WITH_FINDINGS / WAITING_FOR_GPT_INDEPENDENT_REVIEW`
- `boundary`: `PUBLIC_SAFE_REMOTE_OUTPUTS / SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`
- `remote_main_head_at_lease_and_pre_completion_revalidation`: `648ff1929cc3c93b7fda9faf1f5d5a0690142e5f`
- `reviewed_base`: `ff942e345e92374cd9653533b9cb9549b25949fc`
- `tested_head_full_sha`: `a1a4aa2b31c137e65d687ca50e571c6f52e62579`
- `tested_head_parent`: `ff942e345e92374cd9653533b9cb9549b25949fc`
- `tested_head_tree`: `4b256e9fb9c39e1cc7af9dc8e2a7844d1568fffc`
- `receipt_head_ref`: `THIS_COMMIT`
- `receipt_parent_tested_head_full_sha`: `a1a4aa2b31c137e65d687ca50e571c6f52e62579`
- `completion_signal`: `CODEX_E17_D2_ATOMIC_PEER_TRANSFER_AND_CLOSED_SYSTEM_SETTLEMENT_READY_FOR_GPT_REVIEW`

## AMED Agent Execution Receipt

### Main Result

Every structurally valid `PEER_TO_PEER_TRANSFER` pair now follows a shared-prestate
atomic settlement plan. Both reciprocal actions are preflighted before either
portfolio or claim state mutates. A successful plan emits exactly two
deterministically ordered peer events with equal fills, opposite signed deltas,
one shared system pre-hash, one shared system post-hash, and no external flow.
A failed plan emits two zero-fill `BLOCKED` events and mutates neither portfolio
nor claim state.

Peer actions carrying a conflict key, `RELEASE`, or `EXPIRE` are explicitly
`NOT_IMPLEMENTED_YET` in the atomic resource contract and abort both legs before
mutation. This is fail-closed, not a compensating rollback.

The independent verifier now checks pair membership, reciprocal action shape,
same-step coverage, deterministic event membership/order, action-event binding,
complete commit-or-abort disposition, complementary deltas, no peer external
flow, and peer-only aggregate conservation. These checks are separate from
reducer replay.

### Baseline And Repair

At the E16 base, both required reproductions accepted the first leg with fill
`2`, blocked the second with fill `0`, returned `total_system_accounted=false`,
and still returned `verify_episode_ledger=true`: an unknown/forward causal parent
on the second leg, and `RELEASE` on an unclaimed resource. The repaired core
returns `[false, false]`, `[0, 0]`, and true verifier/conserved/accounted results
for both peer-only abort cases.

### Delivery, Rollback And Handoff

Substantive changed paths:

1. `d2_game_core.py`
2. `tests/test_d2_game_core.py`

The tested-to-receipt delta contains only `E17-GATE-A-R2-RECEIPT.md`. Rollback
is one revert of the substantive tested commit to the E16 accepted base. No
rollback may release Gate B/C/D.

The public-safe checkpoint is
`codex/checkpoint/CODEX-D2-ATOMIC-PEER-TRANSFER-AND-CLOSED-SYSTEM-SETTLEMENT-PROOF-0009-E17/A_R2`
at `85124e00e2ac30688fd800f2749a8ec7526c6dce`, parent
`ff942e345e92374cd9653533b9cb9549b25949fc`. It is recovery evidence only,
not a tested or receipt head.

## AMED Research And Improvement Ledgers

- `research_trigger`: `L1_LOCAL_CODE_AND_TEST_REASONING`; no external research
  was needed because the defect was executable in the synthetic reducer.
- Evidence: baseline exploits, D1 reducer behavior, E16 reconstruction, focused
  adversarial tests, and clean archives.
- Negative result: a caller-only final accounting assertion cannot fix an invalid
  one-legged history.
- `B_BOUNDED_IMPLEMENT_AND_REPORT`: `peer_transfer_id` is terminally reserved
  across the episode registry, preventing group-ID ambiguity after commit or abort.
- Rejected: caller-only assertion, compensating rollback events, disabling peer
  transfers, and atomic resource effects without a separately approved contract.

## Discovery, Calibration And UNKNOWN

Observed results match the E17 forecast: both mandatory exploits abort
symmetrically and the verifier rejects coordinated one-legged, missing,
duplicate, non-complementary, binding, side, and external-flow forgeries.
The focused suite rose from 54 to 76 tests, including 22 E17 regressions.
No D1 code, external contract, real data, credential, replay, fitting, account,
order, trade, privacy, or production surface changed.

`S1`: the first checkpoint push had a transient Git HTTPS reset; the preserved
checkpoint reached GitHub on one ordinary non-force retry. `S1`: PowerShell
blocked a binary-pipeline archive attempt and a cleanup command, so final
archives used `git archive --output` and retained temporary evidence.

Preserved `UNKNOWN`: root-capsule origin authentication, trusted timestamping,
and canonical registry publication require a downstream trust-anchor gate.
Atomic peer-resource effects remain `NOT_IMPLEMENTED_YET`. Gate B/C/D, Issue
#92, evaluation V2, real data, replay, backtest, fitting, account, order, and
trade remain closed.

## Test Evidence

Environment: Windows `10.0.22631.0`, Python `3.13.13`.

```text
python -m unittest discover -s tests -p test_d2_game_core.py -q
# exit 0; 76 tests passed
python -m py_compile d2_game_core.py tests/test_d2_game_core.py
# exit 0
```

Three clean full-repository Git archives from the tested head used
`PYTHONHASHSEED=1`, `777`, and `2027`. Each focused suite, syntax check, and
`python tests/run_determinism.py` exited `0`; each deterministic ledger was
`e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc`.

| seed | unit stderr SHA-256 | deterministic stdout SHA-256 |
|---|---|---|
| `1` | `7a5af3bb1176ede853334c5bc9841e17b6c6eebbe4c08e27fb6273e285255b2c` | `2521ae711d3753189975a7ca43d8b89629971d1e7c39811b59bb264bdf0cf5ac` |
| `777` | `06fdf1e2904bf53d720d813f877ab6eb723d8af68f5d9e15242101030c17ecf0` | `2521ae711d3753189975a7ca43d8b89629971d1e7c39811b59bb264bdf0cf5ac` |
| `2027` | `e203d11bf09e6bbedf273ba7f6a8a279bf91443e64f72edd49762f5208417cec` | `2521ae711d3753189975a7ca43d8b89629971d1e7c39811b59bb264bdf0cf5ac` |

Archive unit stdout, compile stdout/stderr, and determinism stderr hashes
were `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Unit stderr differs only by elapsed time. `git diff --check` passed and the
non-disclosing credential-pattern scan returned zero matches.

GPT alone may accept, reject, or release a later gate. No self-approval or
merge occurred.
