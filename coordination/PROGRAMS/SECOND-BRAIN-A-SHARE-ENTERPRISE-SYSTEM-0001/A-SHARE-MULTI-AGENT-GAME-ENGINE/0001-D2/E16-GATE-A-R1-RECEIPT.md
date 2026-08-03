# E16 Gate A-R1 Receipt

- `agent_id`: `CODEX`
- `status`: `SUCCESS_WITH_FINDINGS / WAITING_FOR_GPT_INDEPENDENT_REVIEW`
- `task_id`: `CODEX-D2-INDEPENDENT-EVENT-RECONSTRUCTION-AND-BLOCKED-IDENTITY-CLOSURE-0008-E16`
- `route_epoch`: `16`
- `active_issue` / `pull_request`: `#23` / `#101`
- `active_gate`: `A_R1_PR101_INDEPENDENT_EVENT_RECONSTRUCTION`
- `boundary`: `SYNTHETIC_ONLY / CANDIDATE_ONLY / research_only / NO_TRADE`
- `remote_main_head_at_claim`: `e03639be027787f33e3d59216e40b968e314943c`
- `authorized_reviewed_base`: `b4a544063e0ef7056f9e0f97ef8d130c36c149b4`
- `tested_head_full_sha`: `bf128db6077b505cb646acb9ea97ed8a00775fa6`
- `tested_head_parent`: `b4a544063e0ef7056f9e0f97ef8d130c36c149b4`
- `tested_head_tree`: `b1f088d89680fe2557f1601a67f28ff6b17a59ae`
- `receipt_head_ref`: `THIS_COMMIT`
- `receipt_parent_tested_head_full_sha`: `bf128db6077b505cb646acb9ea97ed8a00775fa6`
- `completion_signal`: `CODEX_E16_D2_INDEPENDENT_EVENT_RECONSTRUCTION_AND_BLOCKED_IDENTITY_READY_FOR_GPT_REVIEW`

## Delivered Gate-A Repair

The ledger verifier now reconstructs an episode solely from frozen initial
agents, root run identity, market state, action registry, deterministic step
boundaries, and the D1 reducer. Stored `LedgerEvent` values are compared with
the reconstruction; no stored `accepted` flag, result status, fill, hash, or
identity field selects the reducer branch.

The substantive commit changes only the two authorized tested paths:

1. `d2_game_core.py`
2. `tests/test_d2_game_core.py`

The implementation adds a content-addressed episode identity, content-addressed
event IDs, a resolved immutable action step schedule, and exact event semantic
comparison. Every emitted terminal event, including generated `BLOCKED` and
`ABSTAIN` events, reserves its action ID, invocation ID, and supplied order ID.
The chosen order rule is explicit: a supplied order identity is non-reusable
after any terminal event, even if the order did not fill.

The reconstruction checks exact action/event binding for event ID, ordinal,
agent/action/invocation IDs, label, acceptance, status, fill, reason codes,
evidence/cause references, causal parents, owner/system hashes, liquidity mode,
conflict transition, counterparty, peer-transfer ID, and step index. It also
checks prior registry collisions before emitting a new event, verifies action
step coverage/order, and rebuilds CLAIM/RELEASE/EXPIRE plus external-versus-peer
accounting through the existing D1 reducer path.

## Baseline Exploit Reproductions

Before claiming a fix, executable synthetic scenarios were run against the
reviewed E15 base `b4a544063e0ef7056f9e0f97ef8d130c36c149b4`. Each result below
was `true`, proving that the baseline accepted the coordinated forged state or
replay attempt:

- `E16-B01`: accepted-to-no-op ledger substitution;
- `E16-B02`: event-ID replacement with claim and external-flow references
  rewritten;
- `E16-B03`: stored label substitution;
- `E16-B04`: a different action reused a generated-block invocation through the
  legacy prior-event interface;
- `E16-B05`: episode step-index modification with a recomputed state hash.

The final focused suite includes direct regressions for those cases and for
reason, cause, invocation, liquidity, conflict-transition, counterparty,
peer-transfer, causal-parent, blocked-order, RELEASE, and EXPIRE substitutions.

## Test Evidence

Environment: Windows `10.0.22631.0`, Python `3.13.13`.

Focused command:

```text
python -m unittest tests.test_d2_game_core -q
```

Result: exit `0`; `54` tests passed.

Syntax command:

```text
python -m py_compile d2_game_core.py tests/test_d2_game_core.py
```

Result: exit `0`.

Three clean full-repository `git archive` extractions were made from the tested
head. Each ran the focused suite, the syntax command, and
`python tests/run_determinism.py` with a distinct `PYTHONHASHSEED`.

| seed | unit exit | unit stdout SHA-256 | unit stderr SHA-256 | determinism exit | deterministic ledger SHA-256 |
|---|---:|---|---|---:|---|
| `1` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `d43c2593bd06856bdcc1ef335c671280d71cce3615ffd251ce0b869638ae9dd0` | `0` | `e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc` |
| `777` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `c1898e4d035274470cf940a75991e683b0cbff68d46c90544447444c93fa6247` | `0` | `e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc` |
| `2027` | `0` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `20f3b24bdac08b36e1212452567aea934f11a9a25deb3ed53c3b576a89e9d322` | `0` | `e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc` |

All deterministic runner stdout values were the same:

```text
D2_LEDGER_SHA256=e6ca812370bdc4bd0acd711e15fe2e31ea41b9ac15de374ff0e04b8a416b32cc
```

The unit-test stderr hashes differ only because the framework reports elapsed
time. Determinism stdout SHA-256 was
`2521ae711d3753189975a7ca43d8b89629971d1e7c39811b59bb264bdf0cf5ac` in all
three archives. Compile stdout/stderr SHA-256 were both
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

## Delivery Surface And Public Safety

- Reviewed-to-tested delta: exactly the two authorized tested paths.
- Tested-to-receipt delta: this receipt only.
- `git diff --check`: exit `0`.
- Non-disclosing credential-pattern scan of the delivery surface: `0` matches.
- No credential, private data, raw market data, account, order, trade, replay,
  fitting, or production interface was used or added.

## AMED Ledger, Findings, And Unknowns

### Primary result

The expected gain was a bounded proof repair without changing the D2 authority
or opening downstream gates. That result was achieved: event semantics now come
from independent reconstruction, and the old five exploit classes have direct
regressions.

### Implemented bounded improvement

`B_BOUNDED_IMPLEMENT_AND_REPORT`: resolved action step boundaries and terminal
order reservation were added inside the authorized D2 core. They are
backward-compatible for callers because `CandidateAction.scheduled_step_index`
is optional at input and is resolved only by arbitration. Rollback is one
revert of the substantive tested commit.

### Active discovery

`S2_MATERIAL / CONTROL_PLANE_NORMALIZATION_NEEDED`: active route schema `17.0`
does not expose an E16-specific `task_impact_forecast` as a top-level reference.
This execution used the inherited Issue #23 Phase-0 forecast and the explicit
E16 review disposition. GPT should normalize this reference in a future route;
it does not change the completed Gate-A scope.

`S1_MINOR / ARCHIVE_TRANSPORT`: the first local clean-archive attempt used a
PowerShell binary pipeline, which damaged the tar stream. Git `archive --output`
followed by extraction was used for the three passing runs above. This was a
test harness transport issue, not a product failure.

`S1_MINOR / COMMENT_ENCODING`: an initial GitHub CLI form-field call encoded
some backslash-prefixed characters as controls in two public status comments.
All four affected lease/visibility comments were patched through JSON stdin and
re-read successfully. No repository artifact, commit, secret, or test evidence
was affected.

### Preserved UNKNOWN

The episode capsule proves consistency relative to its declared immutable root
inputs. It does not itself provide an external signature, trusted timestamp, or
canonical registry publication mechanism that authenticates a wholly replaced
root input set. Such origin authentication is outside Gate A-R1 and remains
`UNKNOWN / FOLLOW_UP_GATE_REQUIRED`; it must not be represented as solved by
this internal reconstruction proof.

### Alternatives considered and rejected

- Keep the old verifier and add field-by-field checks: rejected because stored
  acceptance would still control reconstruction.
- Include system post-hash in event ID: rejected because CLAIM event IDs are
  themselves part of the claimed-state hash, creating circular identity input.
- Treat only accepted events as identity-consuming: rejected because generated
  blocked events then permit replay ambiguity.

## Handoff And Gate Boundary

Push this receipt as the second, receipt-only commit after the tested head. The
external full receipt SHA must be anchored on PR #101, Issue #23, and Issue #31.
GPT alone decides acceptance. Gate B, Gate C, Gate D, Issue #92, evaluation V2,
real data, replay, backtest, fitting, account, order, and trade remain closed.
