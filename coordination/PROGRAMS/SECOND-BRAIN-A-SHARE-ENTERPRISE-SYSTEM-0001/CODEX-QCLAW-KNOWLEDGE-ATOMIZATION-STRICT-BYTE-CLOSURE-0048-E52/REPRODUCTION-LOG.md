# E40 failure reproduction log

## Scope

This record covers the first S0 reproductions against the exact frozen E40
candidate selected in `E40-SOURCE-SELECTION.yaml`. The candidate is isolated
under `src/e52_strict_byte/e40_candidate` and is not production code.

## Command and observed result

```text
python coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/CODEX-QCLAW-KNOWLEDGE-ATOMIZATION-STRICT-BYTE-CLOSURE-0048-E52/tests/test_e40_recorded_failure_reproductions.py
exit_code=1
tests_run=5
pass=1
failures=1
errors=3
```

The passing identity check proved the copied candidate is byte-identical to
frozen blob `d1d3e9df42fb0e6851820603d56aedb3ebb1b6dc` with SHA-256
`abea1e50dfe37cfa22908d7cf11c3402da1a0083796e944af3f31c52c57699b2`.

## Reproduced defects

| Review finding | Executable observation | Disposition |
| --- | --- | --- |
| Private index state is mutable | Assigning `_total_bytes` did not raise. | REPRODUCED |
| No explicit EOF-inclusive boundary-to-codepoint API | `codepoint_index_at_boundary` is absent. | REPRODUCED |
| Containing-byte lookup is not explicitly separated | `chunk_containing_byte` is absent; only ambiguous `chunk_at_byte` exists. | REPRODUCED |
| Canonical `LineRecord` model is absent | `line_records` is absent for a CRLF-final-terminator input. | REPRODUCED |

## Next gate

Implement S0 in a new production namespace, then rerun these tests against the
new implementation. The production 0xED mutation/reap proof will be added as a
separate real-source mutation test; it is not credited by this candidate-only
reproduction.
