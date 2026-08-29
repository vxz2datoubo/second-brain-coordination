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
