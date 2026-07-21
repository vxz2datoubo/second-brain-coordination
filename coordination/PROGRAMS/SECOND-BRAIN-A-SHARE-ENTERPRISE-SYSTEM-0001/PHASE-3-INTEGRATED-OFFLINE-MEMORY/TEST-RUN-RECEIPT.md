# Test Run Receipt: 100 Percent

- agent_id: `CODEX`
- boundary: `research_only / NO_TRADE / offline_only`
- Python: `3.13.13`
- P1 foundation contracts: 12 passed
- P2 offline replay: 25 passed
- PR #51 local adapter suite: 61 passed
- Phase 3 parser/adapter/replay/memory/integration suite: 183 passed
- distinct tests across the four suites: 281 passed
- XT-001 through XT-006: 6 passed
- retrieval regression: 32 of 32 passed
- schema round trips and unsupported/unknown fields: passed
- compile and `git diff --check`: passed
- public safety scan: 57 files scanned, 0 issues
- failures: 0

The automated Phase 3 suite uses regenerated synthetic bytes only. Review regressions cover unknown/undeclared license rejection, explicit UNKNOWN ST/suspension, vendor-volume exclusion from P2 signals and simulation, empty-file rejection and out-of-order source rejection. Two independent read-only runs of the hash-bound local sample produced identical packet, query-plan and semantic ContextBundle hashes in `LOCAL-SAMPLE-VALIDATION-RECEIPT.yaml`; raw bars and runtime databases were not written or exported. The strategy result is `ABSTAIN` with zero simulated actions. No remote market API, credential, service or order path was used. A dependency-free validator covers the JSON Schema keywords used by this package. GitHub CI installs only the pinned test-time YAML parser and runs Python 3.11/3.13 synthetic and public-safe suites.
