# P2.4 semantic provider and structural analogy implementation contract

agent_id: CODEX

## Decision record

P2.4 remains **disabled by default** and no runtime code is changed in epoch 127. A later implementation must have exactly one candidate authority: `ContextAssembler._consider_candidate`, which calls caller-observability and admission before an atom can affect deduplication, budget, ranking, channel attribution or public telemetry. A provider is an optional discovery input, never an authority, dependency, store, vector database, or external service requirement.

## Provider contract proposal

`SemanticProviderRequest/v1` contains only: `schema_version`, opaque `request_id`, normalized public-safe `query_terms`, `query_language` if already caller supplied, `max_suggestions`, and a non-reversible scope/privacy-mode fingerprint. It excludes raw query/body, source pointer, source hash, atom IDs, private identifiers, credentials, hidden metadata, provenance and lifecycle data.

`SemanticProviderResult/v1` contains `schema_version`, `request_id`, `state`, and an optional bounded ordered list of opaque **public-safe query-term enrichments**. It never returns atom IDs, source locations, scores, embeddings, reasoning, raw text, or private metadata. Accepted states are `NOT_CONFIGURED`, `AVAILABLE`, `UNAVAILABLE`, `DENIED`, and `INVALID_RESPONSE`. Only `AVAILABLE` with a schema-valid, injection/secret-clean, bounded term list may enrich the assembler's lexical discovery input. `UNAVAILABLE`, exception/timeout-equivalent, `DENIED`, and `INVALID_RESPONSE` all fall back to P2.3 with no candidate/count/reason telemetry that distinguishes hidden data.

Provider terms are normalized, deduplicated and deterministically ordered before existing lexical search. All resulting atom candidates enter `ContextAssembler._consider_candidate` identically to lexical candidates. The provider supplies no numeric score; it may not change frozen lexical/relation ranking, budget, or tie ordering. If a later design needs a semantic numeric weight, it must stop as `UNKNOWN_NEEDS_GPT` rather than select one.

## Legacy callable migration

The current `retrieve_memory_palace(..., semantic_provider=callable)` directly appends arbitrary callable output to `expanded` query text. It is a legacy compatibility seam, not the P2.4 authority. A future P2.4 implementation must replace it with a private adapter that converts only a caller-supplied local synthetic provider result to `SemanticProviderResult/v1`, then invokes the single assembler-owned discovery path. The callable must be deprecated and rejected once the adapter exists; it must not coexist as a second text-expansion authority. Default absence of a provider must produce P2.3 semantic/byte parity.

## Structural analogy contract proposal

`StructuralFeature/v1` is derived only after each endpoint independently passes caller observability and admission. Permitted fields are redacted atom type, public-safe role class, normalized lifecycle bucket, bounded relation-type multiset, and redacted temporal-shape bucket. It excludes canonical statement/body, source refs/pointers/hashes, atom/user/project identities, privacy domains, raw provenance, confidence, hidden counts and embeddings.

`AnalogyItem/v1` contains a deterministic feature digest, redacted source/target evidence references already present in the admitted bundle, feature labels, `non_evidentiary: true`, and an independent analogy-context budget position. Its source and target must each remain admitted for the same plan; hidden, foreign, restricted, revoked, invalid-time, or cross-privacy endpoint suppresses the whole item. It never enters `evidence`, strongest support/counter, semantic votes, confidence promotion, `trust_gate`, or atom ranking. Its budget is independent of evidence atom budget and reports only public-safe omitted counts.

## Frozen invariants and slices

1. Slice A: add internal provider result normalizer and default-off parity tests; no external API.
2. Slice B: assembler-owned semantic discovery through `_consider_candidate`; preserve dedup/channel attribution and frozen rank/budget.
3. Slice C: internal redacted structural feature extraction and non-evidentiary analogy projection; no graph/store redesign.
4. Slice D: oracle, lifecycle, restart/index-rebuild and legacy-callable removal tests.

Rollback is feature disable/removal of the adapter and analogy projection, restoring the merged P2.3 lexical/temporal/relation/provenance path. No migration or external state rollback is required.
