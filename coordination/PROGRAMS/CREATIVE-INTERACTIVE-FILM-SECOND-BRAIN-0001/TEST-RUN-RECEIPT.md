# Test Run Receipt — S00

agent_id: CODEX

**Status:** `EXECUTOR_VERIFIED_ONLY`

**Scope:** S00 governance and handoff foundation
**No independent review has occurred.**

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m json.tool coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/AUTHORIZED-PATH-MANIFEST.json` | Passed | JSON parsed successfully. |
| YAML parse of lease, provenance, dependency, PDER, unknown, and handoff records | Passed | All six documents loaded with PyYAML. |
| `python -m unittest discover -s tests -p test_creative_s00_governance.py -v` | Passed | 4 tests passed: allowed paths, protected paths, complete authority, and missing boundary rejection. |
| `git diff --check` | Passed | No whitespace errors. |

Reproduction must occur on the pushed task-branch head declared in
`AI_HANDOFF.yaml`; a different SHA is not a substitute for independent review.

## S01 update

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m unittest discover -s tests -p test_creative_s*.py -v` | Passed | 8 tests passed. The S01 tests prove stable artifact provenance, deterministic event records/replay, chain tamper rejection, and non-finite JSON rejection. |

The S01 results are also `EXECUTOR_VERIFIED_ONLY`; GPT must reproduce them at
the remote branch head for independent acceptance.

`python -m pytest -q` was attempted but this clean environment has no `pytest`
module. The branch deliberately uses the Python standard-library `unittest`
runner instead of installing an undeclared dependency.

## S02 update

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m unittest discover -s tests -p test_creative_s*.py -v` | Passed | 11 tests passed. The S02 tests cover initialization, legal choice, free-text interpretation, ambiguity/unsafe fallback without state mutation, resume, and replay. |

The first S02 run found two response-status assertions; the state persistence
itself remained correct. A narrowly scoped field-order correction was made and
the suite then passed in full.

## S03 update

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m unittest discover -s tests -p test_creative_s*.py -v` | Passed | 14 tests passed. S03 covers valid compile plus fail-closed missing asset, adult identity, knowledge, content, axis, duration, and change gates. |

## S04 update

| Command | Result | Evidence |
| --- | --- | --- |
| `python -m unittest discover -s tests -p test_creative_s*.py -v` | Passed | 17 tests passed. S04 covers provenance-required correction, local-only search/review, non-executor named review, and absence of canonical-write authority. |
