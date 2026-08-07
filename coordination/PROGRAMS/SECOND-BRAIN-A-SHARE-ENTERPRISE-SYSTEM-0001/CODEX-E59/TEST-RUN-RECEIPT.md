# Local Test Run Receipt

`agent_id: CODEX`  
`classification: VERIFIED_LOCAL`  
`working_directory: CODEX-E59 task root`  
`interpreter: Python 3.13.13`

| Command | Exit | Result | stdout SHA-256 | stderr SHA-256 |
|---|---:|---|---|---|
| `python tools/recover_legacy_p0_lock.py` | 0 | No recovery was required | `82a34bd53717a0699afca768d9a6c603731c5f7f710cecb7f411ef96f61f1cb4` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python -W error::ResourceWarning tools/run_local_suite.py` | 0 | 48 tests passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `2fe52b98d99f2d6d9c283836ba6b5e505e9f1d941eb6423f6aec1f6d4ee052f7` |
| `python -W error::ResourceWarning tools/run_p0_canary.py` | 0 | 7 P0 scenarios passed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python -W error::ResourceWarning tools/run_mutations.py` | 0 | 9 of 9 mutations killed | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `python tools/run_provider_evidence.py` plus six-copy compare fixture | 0 | canonical source manifest byte comparison passed | local test output retained in tool receipt | local test output retained in tool receipt |

Thread controls were set to one for OpenMP, MKL, OpenBLAS, NumExpr, and tokenizer work. Local mutation and P0 runs were serial. The P0 receipt records no owned descendants after every case and no unrelated termination.

## Provider Correction

The first public Provider run on `77696d2a4f234f7b23d3dc61e4c1a28dc9dcde35` failed in all six matrix jobs before mutation execution because a multiline mutation catalogue spelling only matched LF while the Windows checkout preserved CRLF. The mutation engine now selects exactly one byte-level LF or CRLF spelling and fails closed for zero, multiple, or mixed dual matches. It has dedicated regression coverage for CRLF, mixed spelling ambiguity, and single-line candidate deduplication. `CODEX-E59/.gitattributes` pins future E59 text checkout to LF without weakening the CRLF capability test.

The local evidence above does not replace remote authority. The required replacement remote Provider matrix below applies only to `b73866d...`; a remediation tested Provider is required before any new final receipt.

## Remediation Tested Provider Result

The remediation Provider run [`31181719565`](https://github.com/vxz2datoubo/second-brain-coordination/actions/runs/31181719565) ran against exact head `78952931fe459ad1c785ea98ed749df90b39c39a` from `2026-08-07T13:14:31Z` through `2026-08-07T13:21:16Z`. All seven jobs passed: Python 3.11/3.13 times seeds `0`, `1`, and `777`, plus an independent six-canonical-file compare. It produced 13 artifacts. All six downloaded canonical inner manifests are byte-identical with SHA-256 `eab01f2e7129108df4a732f45d07b861d3b8a110871fea79b2265e7570e8f276`; each provider evidence object reports the same serialized canonical manifest SHA-256 `685aed72dcddafaca84801f5df822cba0a6395b7f3955e6160bccd9b6cb0af7a`. Exact job, artifact and downloaded-log hashes are recorded in `TESTED-PROVIDER-EVIDENCE.yaml`.

This verified the remediation's bounded shared-mutex wait, cleanup, candidate-only process identity checks, and CPU sustain semantics on the exact substantive head. It does not accept the older provisional receipt `3ff135b...`; a single new receipt-only direct child and its distinct Provider run remain mandatory.
