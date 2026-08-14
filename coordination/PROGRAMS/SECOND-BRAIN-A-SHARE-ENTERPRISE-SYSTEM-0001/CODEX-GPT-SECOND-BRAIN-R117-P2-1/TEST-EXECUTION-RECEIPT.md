# R117 P2.1 test execution receipt

agent_id: CODEX

| Check | Result | Evidence |
| --- | --- | --- |
| Focused P2.1 adversarial tests | PASS 5/5 | Shared lexical/relation gate; redacted report; malformed bindings; CURRENT/HISTORICAL lifecycle; packet provenance; synthetic aggregate no-double-vote. |
| Full Phase-3 regression | PASS 267/267 | `python -m unittest discover -s tests -v` after the P2.1 change. |
| Memory Palace/P1 parity | PASS | Existing Memory Palace, conversation and knowledge suites are within the 267 passing tests. |
| Public safety/YAML/diff | PASS | public safety 76 files / 0 issues; changed-path secret-shape scan PASS from clone root; YAML 4 artifacts plus semantic assertions and retrieval compile PASS; diff PASS. |

All fixtures are synthetic. No private source, source body, credentials or real store was read.
