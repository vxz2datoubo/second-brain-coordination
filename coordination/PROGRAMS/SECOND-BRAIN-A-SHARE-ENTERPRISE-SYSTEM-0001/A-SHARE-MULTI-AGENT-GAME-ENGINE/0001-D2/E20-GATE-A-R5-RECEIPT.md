# E20 Gate A-R5 Receipt

## Identity

- `task_id`: `CODEX-D2-DUAL-ENTRY-TYPE-FIRST-ARBITRATION-AND-VERIFIER-TOTALITY-CLOSURE-0012-E20`
- `agent_id`: `CODEX`
- `status`: `SUCCESS_WITH_FINDINGS`
- `scope`: Gate A-R5 only. Gate B, Gate C, Gate D, live data, replay, backtest, fitting, account, order, and trade functions were not started.
- `accepted_base`: `d6f9e2e4d38861e91353be177c9ceacedde6d7ee`
- `tested_commit`: `7a290873f23b9f9218c02540b28862cdc8b9629a`
- `tested_parent`: `d6f9e2e4d38861e91353be177c9ceacedde6d7ee`
- `tested_tree`: `cc57c9db3be9ebe5c1cb4fcfd266133614a7be26`

## Delivered Boundary

`arbitrate` now rejects malformed nested caller values with an intentional,
deterministic `ValueError` before ID hashing, identity set construction,
sorting, market mutation, event construction, or portfolio mutation.

`verify_episode_ledger` now performs a total, non-mutating structural preflight
for stored `EpisodeState` values. Malformed nested state returns one stable
`EpisodeLedgerVerification(valid=False, reason_codes=(...))` result instead of
leaking a Python `TypeError` or `AttributeError`.

The contract validates collection shape and limits before nested values; nested
dataclass type and field shape before identity use; then leaves existing identity,
schedule, semantic, reconstruction, E16, E17, and E18 checks in place. No
coercion or normalization of malformed identifiers is performed. A legitimate
peer-only settlement with no external flow remains valid.

## Authorized File Surface

Only the two substantive Gate A files changed in the tested commit:

| Path | SHA256 at tested commit |
| --- | --- |
| `d2_game_core.py` | `b0d390f8950afe15b5255e147a48a4d8a02fdd885965b25d2ee41ed413b176dd` |
| `tests/test_d2_game_core.py` | `355c735a5e23538cc74b092d7dfeed3fab8d3ad28a00497fba3b023b86b59673` |

The tests add 16 malformed public-arbitration cases and 17 malformed stored-ledger
cases. They include arbitrary objects that raise on hashing, equality, ordering,
or nested attribute access. The successful assertions demonstrate that the new
type-first gate intercepts them before those operations can run.

## Verification Evidence

| Check | Exact command or result | Outcome |
| --- | --- | --- |
| Syntax | `python -B -m py_compile .../d2_game_core.py .../tests/test_d2_game_core.py` | pass |
| Focused suite | `python -B -m unittest coordination.PROGRAMS.SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001.A-SHARE-MULTI-AGENT-GAME-ENGINE.0001-D2.tests.test_d2_game_core` | 124 passed |
| Hash seed 1 | same focused suite with `PYTHONHASHSEED=1` | 124 passed |
| Hash seed 271828 | same focused suite with `PYTHONHASHSEED=271828` | 124 passed |
| Hash seed 314159 | same focused suite with `PYTHONHASHSEED=314159` | 124 passed |
| Recorded focused output | Python `3.13.13`; stdout/stderr SHA256 `878ce3264ed949ff8574a43ad900f84fd7ac69fe14aa84dcc4b33a92fbbe2a2c` | exit 0 |
| Changed-file public secret-pattern scan | `ghp_`, `sk-`, API-key, password, and bearer-token patterns | 0 hits |
| Diff hygiene | `git diff --check` | pass |

## Clean Archive Evidence

Three independent `git archive --format=tar 7a290873...` runs produced the
same SHA256:

`00463dd86780b7057ee6f32ba67f7daffde9f8e81a762a0551e4131ddf13ed0d`

Each archive had 422 tracked paths. Local Python cache directories were not
staged and are absent from Git archives.

## Provenance Check

The approved review head `9e694d1cca3fd867fe5b1d2deb6a7c3868546ae6` is an
ancestor of the tested commit through the accepted base. The requested older
local baseline `80f70013d097f57d21cbc60db82870a316e84a3c` is **not** an
ancestor of `9e694d1...`; both are separately authored E13 receipt lines with
common ancestor `e979f109225bf2d6f00a7890d79df3684dc9e129`.

This is a provenance finding, not repaired by reset, rebase, force-push, or a
synthetic merge. The tested delivery remains based solely on the approved E18
receipt `d6f9e2e...`. GPT should resolve the historical duplicate-line question
in control-plane records if a single lineage assertion is required later.

## Rollback

To remove this Gate A implementation, reset or revert the substantive commit
`7a290873...` and this receipt-only commit together from the delivery branch.
No database, run-state, market-data, account, order, or trading artifact was
created or changed.
