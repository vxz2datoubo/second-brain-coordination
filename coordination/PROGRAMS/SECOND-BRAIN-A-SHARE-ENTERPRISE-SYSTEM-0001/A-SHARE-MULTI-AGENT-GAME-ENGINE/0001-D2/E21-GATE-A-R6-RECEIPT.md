# E21 Gate A-R6 Receipt

## Identity

- `task_id`: `CODEX-D2-EXACT-PRIMITIVE-ENUM-AND-CARRIER-OPERATION-SAFETY-CLOSURE-0013-E21`
- `agent_id`: `CODEX`
- `status`: `SUCCESS_WITH_FINDINGS`
- `scope`: Gate A-R6 only. Gate B, Gate C, Gate D, live data, replay,
  backtest, fitting, account, order, and trade functions were not started.
- `accepted_base`: `bf9c726de6f48a27612971f94fee1d12cc26cb5b`
- `tested_commit`: `d51857a93d716e6e9e1d0816a453eb8688588cdb`
- `tested_parent`: `bf9c726de6f48a27612971f94fee1d12cc26cb5b`
- `tested_tree`: `e2967ed0b14be49f0ca14c22adfaf4f3e78a36c2`
- `ancestry`: `git merge-base --is-ancestor bf9c726... d51857a...` exited `0`.

## Delivered Boundary

The public `arbitrate` and `verify_episode_ledger` boundaries now prove exact
built-in primitives, exact documented enum classes, and exact documented
carrier classes before length, truthiness, bounds, sorting, hashing, equality,
or field dereference can occur. No conversion, copying, string fallback, broad
`Enum` acceptance, or arbitrary dataclass serialization is used for untrusted
input.

The closed serializer accepts only explicitly listed D1/D2 carriers, approved
enum classes, exact primitive/container types, and exact-string mapping keys.
Unsupported values return an intentional `ValueError`, rather than invoking
user-defined `str`, enum value, dataclass, mapping-key, or comparison behavior.

`arbitrate` rejects invalid public input before construction or mutation.
`verify_episode_ledger` still returns a deterministic invalid verification
object for malformed stored state. Multiple faults retain the frozen first
reason by validation order.

## Authorized File Surface

The substantive commit changes only the authorized E21 files:

| Path | SHA256 at tested commit |
| --- | --- |
| `d2_game_core.py` | `0bc7c7fba622440113bacb476c43f12245504fff35b3492969b485ac0f619afb` |
| `tests/test_d2_game_core.py` | `2e1132dd6d6a85b2185be926691e1c97485ada334ba4ca6cff6b0bc032613ae7` |

The test suite contains 153 D2 tests, including 29 E21 regressions for
primitive subclasses, carrier subclasses, broad-enum stand-ins, hostile
containers, canonicalization, verifier totality, and multi-fault precedence.

## Verification Evidence

| Check | Exact command or result | Outcome |
| --- | --- | --- |
| Syntax | `python -m py_compile .../d2_game_core.py .../tests/test_d2_game_core.py` | pass |
| D1 plus D2 | `python -B -m unittest coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-MULTI-AGENT-GAME-ENGINE/0001-D1/tests/test_synthetic_engine.py coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/A-SHARE-MULTI-AGENT-GAME-ENGINE/0001-D2/tests/test_d2_game_core.py` | 179 passed; exit 0 |
| Recorded D1/D2 output | Python `3.13.13`; SHA256 `1a4d7ae14530415d5cd08c018641b9e6914c72319c141043a8347f5a13eb38ef` | exit 0 |
| Python compatibility | Python `3.12` D1/D2 execution | 179 passed; exit 0 |
| Existing Phase 3 local adapter | `python -B run_all_tests.py` | 12, 25, and 61 passed |
| Existing Phase 3 integrated memory | `python -B run_all_tests.py` | 183 passed |
| Public safety scan | `python -B .../public_safety_scan.py` | PASS; 57 files; 0 issues; output SHA256 `a50514d2c369b292194f02cdd57c4a309b7c2a26b43266249e527167f8a9b8b3` |
| Diff hygiene | `git diff --check bf9c726... d51857a...` | pass |

The tracked GitHub Actions matrix remains Python 3.11 and 3.13. Python 3.11
is not installed in this local environment, so its verification is explicitly
deferred to the remote CI run and is not claimed as locally passed.

## Determinism And Archive Evidence

The same synthetic conflict trace was evaluated with `PYTHONHASHSEED=1`, `7`,
and `97`. Each run produced semantic trace SHA256:

`58a8f763997687cb6e78de9fc0ca3bcf0569aad4fa8c7a20c27ac050700d12a3`

Three independent `git archive --format=tar d51857a...` files had 375 tracked
paths and identical archive SHA256:

`51ed03e985ed8ed0adda64d17ccafba691ba7dd1d8b27f0b2151dadf02f1d816`

Each archive was extracted into its own temporary root, then ran the D1/D2
suite successfully: 179 passed for seeds 1, 7, and 97. Generated Python cache
directories are untracked, were not staged, and are absent from the archives.

## OutcomeCalibrationReview

| Item | Result |
| --- | --- |
| Expected outcome | Reject hostile subclasses and unrelated enums before user-controlled operations. |
| Observed outcome | 29 E21 regressions and 179 D1/D2 tests pass; hostile values receive deterministic contract errors. |
| Compatibility cost | Legacy string stand-ins for documented enums now fail closed by design. |
| Remaining unknown | Remote Python 3.11 CI is pending; no local 3.11 interpreter exists. |
| Prohibited claim | This is not a market, replay, strategy, performance, identity, account, order, or trade capability. |

## Rollback

Revert the substantive commit `d51857a...` and this receipt-only commit
together from the delivery branch. No database, run-state, market-data,
account, order, or trading artifact was created or modified.
