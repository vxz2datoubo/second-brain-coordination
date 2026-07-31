# E22 Evaluation V2 Receipt

## Identity

- `task_id`: `CODEX-D2-EVALUATION-V2-EXECUTABLE-MUTATION-METAMORPHIC-AND-FAIL-CLOSED-EVIDENCE-0014-E22`
- `agent_id`: `CODEX`
- `status`: `SUCCESS_WITH_FINDINGS`
- `accepted_base`: `fa68186ea81644b406b58e2ab56d65feeb4d4d94`
- `plan_commit`: `0441f84367ccabe6072c144abb014c8ca16011b1`
- `substantive_commit`: `696ed005add87301f5f1bdbb13732d154a58da8e`
- `substantive_parent`: `0441f84367ccabe6072c144abb014c8ca16011b1`
- `substantive_tree`: `7bebe4852fe37e1c35f090412e2401b548896a47`
- `scope`: Evaluation Gate B only. Gate C, Gate D, Issue #92, real data,
  replay, backtest, fitting, performance claim, identity inference, account,
  order, and trade were not started.

## Delivered Evaluation Boundary

Evaluation V2 is a new synthetic-only package. It treats accepted D2 as a
black-box SUT, validates the exact accepted core fingerprint, and avoids using
the production reducer, verifier, or hash helpers as an oracle. The new oracle
reconstructs inventory deltas, peer conservation, external offsets, causal
precedence, conflict ownership, identity binding, and a separate public digest.

The registry activates eight real fault artifacts and records whether each
changed behavior. Every one was killed by a named independent oracle or a
fail-closed exact-boundary check. The harness also executes eight metamorphic
properties and re-executes 24 cross-family mutation/property rows rather than
reusing a count from one baseline execution.

## Verification Evidence

Platform: Windows 11 `10.0.22631`, Python `3.13.13`.

| Check | Command | Exit | stdout SHA256 | stderr SHA256 |
| --- | --- | ---: | --- | --- |
| Syntax | `python -m py_compile` over 8 E22 Python files | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Focused E22 | `python .../0001-D2-EVALUATION-V2/tests/test_evaluation_v2.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `771a628bc8e17726dd40ee21ffcf12d3cce1fbe89ecc69fe00c52d936b11033d` |
| Inherited D1/D2 | `python -B -m unittest .../0001-D1/tests/test_synthetic_engine.py .../0001-D2/tests/test_d2_game_core.py` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `8c30874f898ca40be436a3303d280e63337eff1d3b75bbfe93485cca7ff62dc5` |
| Full V2 report | `python .../0001-D2-EVALUATION-V2/tests/run_evaluation_v2.py --full` | 0 | `181ee5012131701e9950f5cbf132c8916958caf6e3cc87b98bfaa67d11d588ef` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Public safety | `rg` credential patterns over the E22 directory | 1 meaning zero matches | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Diff hygiene | `git diff --check 0441f84... 696ed00...` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

The full runner reports 72 scenarios, 80 executable invariants, 37 negative
cases, 24 stateful episodes, 36 counterfactual pairs, 24 cross-family
interactions, mutation score `1.0`, no property failures, and no survivors.

## CI Finding

The tracked GitHub Actions workflow is a Python 3.11/3.13 matrix but currently
does not call the E22 test or runner. Local Python 3.11 is unavailable. The
workflow may be green without executing E22, so Python 3.11/3.13 E22 CI is not
claimed. This requires an explicit GPT-authorized workflow-path decision.

## Rollback And Handoff

Revert the substantive commit and this receipt-only commit from PR #106. No
database, credentials, data source, service, account, order, or trading state
was modified. Review `AI_HANDOFF.yaml` and stop at Gate B pending GPT review.
