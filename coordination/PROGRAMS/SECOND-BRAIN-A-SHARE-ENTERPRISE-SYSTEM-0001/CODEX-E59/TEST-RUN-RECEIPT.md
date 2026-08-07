# Local Test Run Receipt

`agent_id: CODEX`  
`classification: VERIFIED_LOCAL`  
`working_directory: CODEX-E59 task root`  
`interpreter: Python 3.13.13`

| Command | Exit | Result | stdout SHA-256 | stderr SHA-256 |
|---|---:|---|---|---|
| `python -W error::ResourceWarning tools/run_local_suite.py` | 0 | 41 tests passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `c3c79c53825a711a6132a3666a4ae64e4086024f2299360e70b85666166fd1a5` |
| `python tools/run_p0_canary.py` | 0 | 7 P0 scenarios passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python tools/run_mutations.py` | 0 | 9 of 9 mutations killed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python tools/run_provider_evidence.py` plus six-copy compare fixture | 0 | canonical source manifest byte comparison passed | local test output retained in tool receipt | local test output retained in tool receipt |

Thread controls were set to one for OpenMP, MKL, OpenBLAS, NumExpr, and tokenizer work. Local mutation and P0 runs were serial. The P0 receipt records no owned descendants after every case and no unrelated termination.

## Provider Correction

The first public Provider run on `77696d2a4f234f7b23d3dc61e4c1a28dc9dcde35` failed in all six matrix jobs before mutation execution because a multiline mutation catalogue spelling only matched LF while the Windows checkout preserved CRLF. The mutation engine now selects exactly one byte-level LF or CRLF spelling and fails closed for zero, multiple, or mixed dual matches. It has dedicated regression coverage for CRLF, mixed spelling ambiguity, and single-line candidate deduplication. `CODEX-E59/.gitattributes` pins future E59 text checkout to LF without weakening the CRLF capability test.

This receipt is local evidence only. The required replacement remote Provider matrix is still pending and cannot be replaced by this interpreter run.
