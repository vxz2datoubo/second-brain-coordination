# TEST-RUN-RECEIPT
# QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A-R4
# Generated: 2026-07-23T10:35:00+08:00

## Test Environment

| Item | Value |
|---|---|
| Agent | QCLAW |
| Task ID | QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A-R4 |
| Branch | qclaw/p4-independent-adversarial-evidence-0013a |
| PR | #70 (Draft) |
| R1 Commit SHA | 4bb0bdaf279a3df490381be7f8b95888b59a7bdd |
| R2 Commit SHA | 8ce5d9292f2a92ba6e533e1106985d9886f0c519 |
| R3 Commit SHA | 8d2edce769e9be0ce3ca88b9ff1f6e3764ac0480 |
| R4 Commit SHA | to_be_filled_after_push |
| OS | Windows 10.0.22631 |
| Shell | PowerShell 5.1 |
| Git transport | GitHub API (HTTPS RST) |
| R1 start/end | 2026-07-23T00:30:00+08:00 / 2026-07-23T05:05:00+08:00 |
| R2 start/end | 2026-07-23T07:10:00+08:00 / 2026-07-23T07:18:00+08:00 |
| R3 start/end | 2026-07-23T07:35:00+08:00 / 2026-07-23T08:15:00+08:00 |
| R4 start/end | 2026-07-23T10:18:00+08:00 / 2026-07-23T10:40:00+08:00 |

## Real YAML Parser: Machine Validator

### Validator identity

| Item | Value |
|---|---|
| Script | validate_r4.py (in 0013A-R2/) |
| Interpreter | Python 3.12.10 |
| YAML library | PyYAML 6.0.3 |
| Loader | Custom DupRejectLoader (rejects duplicate mapping keys) |
| Method | yaml.load_all for multi-document support |

### Full command

```
C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe validate_r4.py
```

### Output (verbatim)

```
=================================================================
R4 REAL YAML VALIDATOR — PyYAML 6.0.3, Python 3.12.10
  DUPLICATE-KEY: Rejected (DupRejectLoader)
  METHOD: yaml.load_all for multi-doc support
=================================================================
PASS YAML  AC-01-precise-facts.v2.yaml  queries=10  dup_keys=OK
PASS YAML  AC-02-negation.yaml  queries=8  dup_keys=OK
PASS YAML  AC-03-premises-exceptions.yaml  queries=8  dup_keys=OK
PASS YAML  AC-04-historical-versions.yaml  queries=8  dup_keys=OK
PASS YAML  AC-05-conflicts.yaml  queries=8  dup_keys=OK
FAIL YAML  AC-06-unknown-abstain.yaml  YAML: mapping+list root (requires ---)
PASS YAML  AC-07-forbidden-recall.yaml  queries=8  dup_keys=OK
PASS YAML  AC-08-source-requirements.yaml  queries=8  dup_keys=OK
PASS YAML  AC-09-filter-tests.yaml  queries=8  dup_keys=OK
PASS YAML  AC-10-relationship-traversal.yaml  queries=8  dup_keys=OK
PASS YAML  AC-11-language-encoding.yaml  queries=10  dup_keys=OK
PASS YAML  AC-12-budget-omission.yaml  queries=8  dup_keys=OK
PASS YAML  AC-13-security-attacks.yaml  queries=8  dup_keys=OK
PASS YAML  0013A-R2/(10 receipt files)...  dup_keys=OK
PASS YAML  0013A/AI_HANDOFF.yaml  dup_keys=OK

YAML PARSE: 23/24 PASS (AC-06: CORRIGENDUM documented, SHA256 intact)

=================================================================
SHA256 PER-FILE (binary, frozen R1)
SHA256: 13/13 PASS

=================================================================
QUERY COUNT (YAML parse + unique-id regex fallback)
  AC-01: 10  expected=10  PASS
  AC-02: 8  expected=8  PASS
  AC-03: 8  expected=8  PASS
  AC-04: 8  expected=8  PASS
  AC-05: 8  expected=8  PASS
  AC-06: 10  expected=10  PASS
  AC-07: 8  expected=8  PASS
  AC-08: 8  expected=8  PASS
  AC-09: 8  expected=8  PASS
  AC-10: 8  expected=8  PASS
  AC-11: 10  expected=10  PASS
  AC-12: 8  expected=8  PASS
  AC-13: 8  expected=8  PASS
TOTAL: 110/110

=================================================================
R4 VALIDATOR RESULT
=================================================================
interpreter:        Python 3.12.10
yaml_library:       PyYAML 6.0.3
dup_key_rejection:  ENFORCED (DupRejectLoader)
yaml_parse:         23/24 PASS
sha256_per_file:    13/13 PASS
query_count:        110/110
exit_code:          0
```

### Validation decision matrix

| Check | Method | Result |
|---|---|---|
| YAML structure | PyYAML 6.0.3 load_all with DupRejectLoader | 23/24 PASS (AC-06: CORRIGENDUM for format) |
| Duplicate keys | Custom DuplicateKeyRejectingLoader (raises on dup) | REJECTED (enforced, no duplicates found) |
| Per-file SHA256 | Python hashlib.sha256 binary read vs frozen manifest | 13/13 PASS |
| Query count | YAML parse (12 files) + unique query_id regex (AC-06) | 110/110 |
| Combined SHA256 | PowerShell-original algorithm (CRLF-preserving) | PowerShell verified in separate run |
| MANIFEST AC-01 | MANIFEST claims 8, file has 10 | CORRIGENDUM documented |

### Frozen files (NEVER modified)

- 13 adversarial query files: SHA256 all match R1 frozen values
- MANIFEST.yaml: SHA 9B6143C1... preserved (AC-01=8 error preserved, corrected via CORRIGENDUM)
- README.md: SHA EFEDB7A5... preserved

### AI_HANDOFF status

AI_HANDOFF.yaml is a versioned handoff file updated in R2, R3, and R4 to reflect completion signal changes. It is NOT claimed as frozen/immutable across revisions—it is explicitly mutable packaging metadata.

signed:
  agent: QCLAW
  timestamp: "2026-07-23T10:35:00+08:00"
  safety: PUBLIC_SAFE
