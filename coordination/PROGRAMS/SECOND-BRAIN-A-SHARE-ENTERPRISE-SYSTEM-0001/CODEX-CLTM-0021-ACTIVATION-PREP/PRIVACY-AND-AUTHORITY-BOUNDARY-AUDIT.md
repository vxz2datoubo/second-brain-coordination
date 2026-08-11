# Privacy and authority boundary audit

## Classification and admission

| Class | Public coordination repository | Candidate processing | Formal persistence |
| --- | --- | --- | --- |
| `PUBLIC_SAFE` | Architecture, schema, synthetic tests and minimized receipts only | May be represented as a synthetic/public-safe candidate | Still locked by route |
| `PRIVATE_OR_SENSITIVE` | No body, embeddings, identifiers or reversible payload | Private-local handling requires a future route | Locked |
| `SECRET_CREDENTIAL` | Prohibited | Prohibited from packets, logs, fixtures and context | Prohibited |

Conversation content is private by default. This repository may contain only non-reversible schemas, hashes where justified, aggregate receipts, and synthetic fixtures. Real names, contact information and ordinary account identifiers are also excluded from public reports by policy even when local handling is authorized.

## Authority findings

- W3 is the sole long-term-memory authority.
- Phase 3 remains candidate-only; E66's public-safe Git control path is not a real formal knowledge writer.
- Any future MCP is an integration surface, not authority. Remote MCP data retention is third-party policy territory and requires explicit review.
- No private repository or repository permission/visibility action is authorized in this route.

## Required future negative tests

- reject raw conversation body, reversible pointer, contact data and secret patterns from public payloads and logs;
- reject assistant analysis as a user assertion;
- reject cross-user/cross-project recall and stale/superseded current recall;
- reject untrusted prompt-injection text from answer context;
- prove correction creates a history-preserving successor, not an overwrite.
