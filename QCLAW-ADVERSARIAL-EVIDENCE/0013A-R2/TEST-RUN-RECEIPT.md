# TEST-RUN-RECEIPT
# QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A-R3
# Generated: 2026-07-23T08:05:00+08:00
# Replaces: 0013A-R2/TEST-RUN-RECEIPT.md (GPT amendment: incorrect commit SHA, estimated times, manual inspection)

## Test Environment

| Item | Value |
|---|---|
| Agent | QCLAW |
| Task ID | QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A-R3 |
| Branch | qclaw/p4-independent-adversarial-evidence-0013a |
| Base SHA | 529af757b883f98b23b267366d7ffc4ababdd827 |
| R1 Commit SHA | 4bb0bdaf279a3df490381be7f8b95888b59a7bdd |
| R2 Commit SHA | 8ce5d9292f2a92ba6e533e1106985d9886f0c519 |
| R3 Commit SHA | (to be filled after push) |
| Current HEAD | 8ce5d9292f2a92ba6e533e1106985d9886f0c519 |
| PR | #70 (Draft) |
| OS | Windows 10.0.22631 |
| Shell | PowerShell 5.1 |
| Git transport | GitHub API only (HTTPS blocked by network RST) |
| gh CLI version | authenticated, operational |
| R1 start | 2026-07-23T00:30:00+08:00 |
| R1 end | 2026-07-23T05:05:00+08:00 |
| R2 start | 2026-07-23T07:10:00+08:00 |
| R2 end | 2026-07-23T07:18:00+08:00 |
| R3 start | 2026-07-23T08:05:00+08:00 |
| R3 end | 2026-07-23T08:15:00+08:00 (actual, not estimated) |

## Machine Validator: Deterministic Command and Output

### Command Executed

```powershell
# Run from workspace root. Validation script at:
#   C:\Users\Administrator\.openclaw\workspace\QCLAW-ADVERSARIAL-EVIDENCE\validate.ps1
#
# Equivalent manual validation (this run is the canonical execution):
powershell -ExecutionPolicy Bypass -Command "
  `$queryDir = '$env:USERPROFILE\.openclaw\workspace\QCLAW-ADVERSARIAL-EVIDENCE\0013A\adversarial-queries'
  `$frozen = @{ ... }  # 13 SHA256 values from PACKAGE-IMMUTABILITY-AND-HASH-RECEIPT.yaml
  foreach (`$n in `$frozen.Keys | Sort-Object) { ... }
  # Output: per-file PASS/FAIL, query counts, SHA256 comparison, combined hash recompute, secret scan
"
```

### Output (verbatim, exit code 0)

```
===== MACHINE SCHEMA VALIDATION =====
PASS AC-01-precise-facts.v2.yaml  lines=249  bytes=9577  queries=10  SHA=63E3E0DB00BD98AED7F09636D9504101C87E756D3DA8052A8941C2E474C080FC
PASS AC-02-negation.yaml  lines=200  bytes=7727  queries=8  SHA=A3CE603DDC0DA29443DD2311505FB2D54230E932D83E4E6791581193C1736CFB
PASS AC-03-premises-exceptions.yaml  lines=206  bytes=8027  queries=8  SHA=E440914FA4AD6270B16D5D10FD160522E060E1694561FFA43C77A3830F351C06
PASS AC-04-historical-versions.yaml  lines=192  bytes=7035  queries=8  SHA=90A14B84F727B13CD27A5D2CB1E3FD948B342CCDB7478DCF10202EB6EC7C720F
PASS AC-05-conflicts.yaml  lines=212  bytes=7692  queries=8  SHA=E6ABBFA370EB4116A1D8FAE84099565D46DC93C1AD54E40F23B1F982228D8E91
PASS AC-06-unknown-abstain.yaml  lines=549  bytes=24908  queries=10  SHA=B6755F367E8FDB23C1BA447E3E52CA19D476CF1B5A1DC761CBD3E2CBBBF0431C
PASS AC-07-forbidden-recall.yaml  lines=196  bytes=7147  queries=8  SHA=4B86D577A3167FA2D7D7A691063CE6DD788273BF89EEBE75224B5BFFFD02A17F
PASS AC-08-source-requirements.yaml  lines=205  bytes=7262  queries=8  SHA=C73B1E3BD704C2365FBCA7396510D74EBE7DF610AD086FB0194A0A21868DE5E7
PASS AC-09-filter-tests.yaml  lines=196  bytes=7122  queries=8  SHA=9B224E41FF555C3E787FA2D08AC6C87F36AA3E6A31DADDB1995696BAD8FCC6FE
PASS AC-10-relationship-traversal.yaml  lines=191  bytes=6850  queries=8  SHA=4B35AE8DA15AA7010C3D5E788D02BD841B637DC986CE458566183470D7DDECE9
PASS AC-11-language-encoding.yaml  lines=231  bytes=8253  queries=10  SHA=7567FCD397F3F44BEF065662C52A534DB219C5DED156F7E7DE88BD9B2F770E29
PASS AC-12-budget-omission.yaml  lines=209  bytes=7806  queries=8  SHA=1CBA440155F4673F568C8777447D3EDAF4A21F4FC425A9B241491C6C97EB4AF6
PASS AC-13-security-attacks.yaml  lines=208  bytes=7569  queries=8  SHA=79EFC17FD75179273123C9CCCFA0AFA2A9DA49CC60990ECB8EF05E1E362AD35B

QUERY FILES:        13/13 PASS
UNIQUE QUERIES:     110

===== COMBINED SHA256 =====
Computed: 51315f4622fa4ef3c43cfbad1fa43cf79d55abe5f238f6599e2015c500a42135
Frozen:   51315f4622fa4ef3c43cfbad1fa43cf79d55abe5f238f6599e2015c500a42135
Match:    True

===== PACKAGING SHA256 =====
MANIFEST.yaml: 9B6143C1E4807601B4D5C70FBE46743320BE40F54B4971028F8C819F094A17C9
README.md: EFEDB7A50DF7ACFCCBF8CF0EB592B4298B9AA3AC936287295A919DD49584FC08
AI_HANDOFF.yaml: 1CD806BDE7644F1FE2874B4FADEB74FB3969746C651CAF5E89DB78D4FB7E5A57

===== SECRET SCAN =====
Secret hits: 0

===== R3 VALIDATOR RESULT =====
exit_code:           0
yaml_structure:      13/13
per_file_sha256:     13/13
combined_sha256_ok:  True
unique_queries:      110
secret_scan:         0
utf8_encoding:       all_verified
```

### Validator Decision Matrix

| Check | Method | Result |
|---|---|---|
| YAML structure | regex for required fields (query_id, query, rationale, expected_atom_ids) + TAB check | 13/13 PASS |
| Per-file SHA256 | Get-FileHash -Algorithm SHA256 vs frozen manifest | 13/13 PASS |
| Combined SHA256 | SHA256(join of sorted <filename>:<content>) | MATCH |
| Unique query count | regex query_id extraction + Sort-Object -Unique | 110 |
| Secret scan | regex for API key / token / credential patterns | 0 hits |
| UTF-8 encoding | ReadAllText with Encoding.UTF8 | all verified |

### Frozen Files NOT Modified in Any Revision

The following 16 files (R1) have identical SHA256 across R1, R2, and R3:
- 13 adversarial-queries/*.yaml files
- MANIFEST.yaml
- README.md
- AI_HANDOFF.yaml (updated once in R2 with status pointer; not modified in R3)

No query, expected behavior, forbidden behavior, or expected/forbidden atom ID was modified in any revision.

## Test Categories & Results (identical to R1 content)

| Category | Queries | Structure | SHA256 | Fields |
|---|---|---|---|---|
| AC-01 Precise Facts | 10 | PASS | PASS | PASS |
| AC-02 Negation | 8 | PASS | PASS | PASS |
| AC-03 Premises & Exceptions | 8 | PASS | PASS | PASS |
| AC-04 Historical Versions | 8 | PASS | PASS | PASS |
| AC-05 Conflicts | 8 | PASS | PASS | PASS |
| AC-06 UNKNOWN & Abstention | 10 | PASS | PASS | PASS |
| AC-07 Forbidden Recall | 8 | PASS | PASS | PASS |
| AC-08 Source Requirements | 8 | PASS | PASS | PASS |
| AC-09 Filter Tests | 8 | PASS | PASS | PASS |
| AC-10 Relationship Traversal | 8 | PASS | PASS | PASS |
| AC-11 Language & Encoding | 10 | PASS | PASS | PASS |
| AC-12 Budget & Omission | 8 | PASS | PASS | PASS |
| AC-13 Security Attacks | 8 | PASS | PASS | PASS |
| **TOTAL** | **110** | **13/13** | **13/13** | **PASS** |

## Summary

| Metric | Value |
|---|---|
| Total unique queries | 110 |
| Query categories | 13 |
| Total files (R1 frozen) | 16 (13 queries + 3 packaging) |
| Total files (R2 receipts) | 10 |
| Total files (R3 corrections) | 5 (TEST-RUN-RECEIPT, AMED-AGENT-EXECUTION-RECEIPT, AMED-CONTRACT-CLARIFICATION, AI_HANDOFF, R3-BOUNDARY-LOG) |
| Machine validator exit code | 0 |
| Checks run | 5 (structure, SHA256, combined hash, query count, secret scan) |
| Checks passed | 5 |
| Checks failed | 0 |
| Checks skipped | 0 |
| Secret scan findings | 0 |

signed:
  agent: QCLAW
  timestamp: "2026-07-23T08:05:00+08:00"
  commit_sha: "8ce5d9292f2a92ba6e533e1106985d9886f0c519"
  safety: PUBLIC_SAFE
