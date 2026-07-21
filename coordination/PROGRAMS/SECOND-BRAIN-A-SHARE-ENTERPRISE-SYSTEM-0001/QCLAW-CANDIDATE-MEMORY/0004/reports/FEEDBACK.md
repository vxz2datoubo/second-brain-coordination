# FEEDBACK — Candidate Memory Library v0.2

**Task ID:** QCLAW-CANDIDATE-MEMORY-LIBRARY-RETRIEVAL-0004
**Date:** 2026-07-21
**Agent:** QCLAW (QQ)
**Category:** OUTCOME_CALIBRATION

## What Went Well

1. **Serial execution strategy was correct** — Building WP-A then B then C/D/E sequentially prevented the dependency hell that plagued Issue #40's parallel sub-agent approach (42/44 timeout, 2 sub-agents lost).

2. **Test-first design paid off** — Writing tests concurrently with implementation caught 3 critical bugs early:
   - FK constraint ordering in rollback restore
   - `type_filter` vs `atom_type_filter` variable name mismatch
   - Corollary: testing in `:memory:` SQLite is fast enough (<2s per suite) to allow rapid iteration

3. **4-axis independence was validated** — Store schema designed from the start with `knowledge_status`, `gpt_access`, `transport_visibility`, `authority_level` as separate columns. No retrofitting needed.

4. **FTS5 + SHA256 = zero external dependencies** — No pip installs, no model downloads, no cloud services. Entire system runs on Python stdlib.

5. **Revision determinism achieved** — Same packets → same revision hash. Critical for audit trail and reproducibility.

## What Could Be Better

1. **Variable naming drift** — `type_filter` vs `atom_type_filter` in `retrieval.py` went undetected until test run. The parameter was renamed mid-implementation but the post-filter block wasn't updated. Lesson: when renaming a parameter, search all usages in the same file.

2. **Snapshot engine initialization in tests** — Each test in `_test_cde.py` creates its own `:memory:` store + 3 packets + conflicts. Setup code is 30 lines duplicated. Should have extracted a `setup_test_store()` fixture earlier.

3. **Regression dataset design** — 7/32 queries fail because they test structured API usage (`""` + flags, `"scope:test"`, `"confidence>0.7"`) rather than natural language queries. These are valid adversarial tests but their expected values were optimistic given the current parser. Should have labeled them as "stretch goals" rather than "expected minimums."

4. **CLI manual testing only** — The CLI has no automated test suite. `python3 cli.py --db :memory: stats` was verified manually but a `_test_cli.py` with `subprocess.run` would catch regressions.

5. **FTS5 index not auto-populated** — Atoms are not automatically FTS-indexed on insert. The test harness explicitly calls `index_atom_terms()`. Production usage would require a trigger or middleware.

## Engineering Impact Forecast Accuracy

Forecast in Issue #44 predicted:
- Implementation effort: medium-high ✅ (accurate — 9 modules, ~90KB total)
- Determinism risk: low ✅ (revision hash matches across builds)
- Integration risk with Codex: low ✅ (8/8 gates compatible)
- Chinese tokenizer risk: medium — deferred (not in scope)

## Recommendations for Next Iteration

1. Implement auto-FTS-indexing on atom insert (SQLite trigger)
2. Add structured query parser for `"scope:xxx"` and `"confidence>0.7"` syntax
3. Extract shared test fixtures to `conftest.py`
4. Add `_test_cli.py` automated CLI tests
5. Reduce `_gen_report.py` → embed report generation into `eval.py` directly
