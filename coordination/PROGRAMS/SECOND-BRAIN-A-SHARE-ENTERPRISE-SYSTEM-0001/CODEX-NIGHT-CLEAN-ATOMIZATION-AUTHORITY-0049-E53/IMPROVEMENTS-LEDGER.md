# E53 improvements ledger

| Improvement | Why | Alternative rejected |
| --- | --- | --- |
| `SourceEvidence` factory | Declared digest/text cannot establish provenance. | Public dataclass plus `__post_init__` cannot reconstruct exact source bytes. |
| Total `FinalizedLedger` | Prevent gaps, overlaps and caller-authored coverage. | Partial span list leaves unowned bytes ambiguous. |
| Active-factory identity admission | Refuse forged or foreign atom objects. | Matching fields alone permits rebuilt copies. |
| Span-addressed explicit relations | Avoid source-digest recursive endpoint construction. | Embedding atom IDs in source creates a circular identity dependency. |
| Separate canonical/environment artifacts | Deterministic semantic bytes must not include runtime details. | One combined artifact varies across matrix jobs. |
| Product-copy mutations | Demonstrate the actual gate is necessary. | Synthetic helpers or boolean oracles can create a green echo chamber. |
