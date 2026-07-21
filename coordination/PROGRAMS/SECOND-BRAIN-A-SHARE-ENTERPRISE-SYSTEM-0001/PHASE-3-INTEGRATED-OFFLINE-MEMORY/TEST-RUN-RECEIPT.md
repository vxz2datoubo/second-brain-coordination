# Test Run Receipt: 80 Percent

- agent_id: `CODEX`
- boundary: `research_only / NO_TRADE / offline_only`
- Python: current local interpreter
- P1 foundation contracts: 12 passed
- P2 offline replay: 21 passed
- PR #51 local adapter suite: 61 passed
- Phase 3 parser/adapter/replay/memory suite: 149 passed
- failures: 0

The automated Phase 3 suite uses regenerated synthetic bytes only. A separate read-only run of the hash-bound local sample produced the aggregate `LOCAL-SAMPLE-VALIDATION-RECEIPT.yaml`; raw bars were not written or exported. No remote market API, credential, service or order path was used. A missing third-party `jsonschema` dependency was handled by a dependency-free validator for the schema keywords used by this package; no package was installed.
