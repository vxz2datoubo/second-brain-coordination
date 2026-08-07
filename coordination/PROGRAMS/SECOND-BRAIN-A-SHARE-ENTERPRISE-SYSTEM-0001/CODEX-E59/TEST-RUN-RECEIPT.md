# Local Test Run Receipt

`agent_id: CODEX`  
`classification: VERIFIED_LOCAL`  
`working_directory: CODEX-E59 task root`  
`interpreter: Python 3.13.13`

| Command | Exit | Result | stdout SHA-256 | stderr SHA-256 |
|---|---:|---|---|---|
| `python -W error::ResourceWarning tools/run_local_suite.py` | 0 | 38 tests passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `2b0c5493f9e061fffe9be7bd1497053ca7b84a9f1680f5a5334afbb7720f7206` |
| `python tools/run_p0_canary.py` | 0 | 7 P0 scenarios passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python tools/run_mutations.py` | 0 | 9 of 9 mutations killed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python tools/run_provider_evidence.py` plus six-copy compare fixture | 0 | canonical source manifest byte comparison passed | local test output retained in tool receipt | local test output retained in tool receipt |

Thread controls were set to one for OpenMP, MKL, OpenBLAS, NumExpr, and tokenizer work. Local mutation and P0 runs were serial. The P0 receipt records no owned descendants after every case and no unrelated termination.

This receipt is local evidence only. The required remote Provider matrix is still pending and cannot be replaced by this interpreter run.
