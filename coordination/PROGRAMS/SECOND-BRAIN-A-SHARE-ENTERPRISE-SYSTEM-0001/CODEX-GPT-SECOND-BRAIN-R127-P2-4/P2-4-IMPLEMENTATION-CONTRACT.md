# P2.4 semantic provider and structural analogy implementation contract

agent_id: CODEX

## Decision record

P2.4 remains **disabled by default** and no runtime code is changed in epoch 127. A later implementation must have exactly one candidate authority: `ContextAssembler._consider_candidate`, which calls caller-observability and admission before an atom can affect deduplication, budget, ranking, channel attribution or public telemetry. A provider is an optional discovery input, never an authority, dependency, store, vector database, or external service requirement.

## Provider contract proposal

`SemanticProviderRequest/v1` contains only: `schema_version`, opaque `request_id`, normalized public-safe `query_terms`, `query_language` if already caller supplied, `max_suggestions`, and a non-reversible scope/privacy-mode fingerprint. It excludes raw query/body, source pointer, source hash, atom IDs, private identifiers, credentials, hidden metadata, provenance and lifecycle data.

`SemanticProviderResult/v1` contains `schema_version`, `request_id`, `state`, and an optional bounded ordered list of opaque **public-safe discovery terms**. It never returns atom IDs, source locations, scores, embeddings, reasoning, raw text, or private metadata. Accepted states are `NOT_CONFIGURED`, `AVAILABLE`, `UNAVAILABLE`, `DENIED`, and `INVALID_RESPONSE`. Only `AVAILABLE` with a schema-valid, injection/secret-clean, bounded term list may start semantic discovery. `UNAVAILABLE`, exception/timeout-equivalent, `DENIED`, and `INVALID_RESPONSE` all fall back to P2.3 with no candidate/count/reason telemetry that distinguishes hidden data.

Provider terms are normalized, deduplicated and deterministically ordered, but **must never be concatenated into the caller lexical query**. For each term, the existing index may discover candidate IDs; the implementation must discard its numeric term score and submit each sorted unique atom through `ContextAssembler._consider_candidate(..., score=None, channel="semantic")`. Semantic-only hits therefore use the existing deterministic supplemental placement. If an atom already has lexical or relation score, semantic discovery may add only its channel attribution and must not alter the numeric score, ranking, budget, or tie ordering. `NOT_CONFIGURED` performs no provider operation and emits no new public provider field, preserving P2.3 byte/semantic parity. GPT has decided `P2_4_SEMANTIC_NUMERIC_WEIGHT = GPT_DECIDED_NO_NUMERIC_SCORE_V1`; a future numeric policy is out of scope and requires a separate benchmarked review.

## Legacy callable migration

The current `retrieve_memory_palace(..., semantic_provider=callable)` directly appends arbitrary callable output to `expanded` query text. It is a legacy compatibility seam, not the P2.4 authority. A future P2.4 implementation must replace it with a private adapter that converts only a caller-supplied local synthetic provider result to `SemanticProviderResult/v1`, then invokes the single assembler-owned discovery path. The callable must be deprecated and rejected once the adapter exists; it must not coexist as a second text-expansion authority. Default absence of a provider must produce P2.3 semantic/byte parity.

## Structural analogy contract proposal

`StructuralFeature/v1` is derived only after each endpoint independently passes caller observability and admission. Its relation-type multiset comes from **endpoint-safe admitted relations only**: each relation source **and** target must pass the same endpoint-safe admission/observability checks for the plan, and feature extraction must not inspect raw adjacency. Permitted fields are redacted atom type, public-safe role class, normalized lifecycle bucket, this endpoint-safe bounded relation-type multiset, and redacted temporal-shape bucket. It excludes canonical statement/body, source refs/pointers/hashes, atom/user/project identities, privacy domains, raw provenance, confidence, hidden-neighbor counts/types, and embeddings. Hidden adjacency may affect neither features, digest, analogy count nor omission telemetry.

`AnalogyItem/v1` contains a deterministic feature digest, redacted source/target evidence references already present in the admitted bundle, feature labels, `non_evidentiary: true`, and an independent analogy-context budget position. Its source and target must each remain admitted for the same plan; hidden, foreign, restricted, revoked, invalid-time, or cross-privacy endpoint suppresses the whole item. It never enters `evidence`, strongest support/counter, semantic votes, confidence promotion, `trust_gate`, or atom ranking. Its budget is independent of evidence atom budget and reports only public-safe omitted counts.

## Frozen invariants and slices

1. Slice A: add internal provider result normalizer and default-off parity tests; no external API.
2. Slice B: assembler-owned semantic discovery through `_consider_candidate`; preserve dedup/channel attribution and frozen rank/budget.
3. Slice C: internal redacted structural feature extraction and non-evidentiary analogy projection; no graph/store redesign.
4. Slice D: oracle, lifecycle, restart/index-rebuild and legacy-callable removal tests, including zero/one/many hidden relation-neighbor analogy parity.

Rollback is feature disable/removal of the adapter and analogy projection, restoring the merged P2.3 lexical/temporal/relation/provenance path. No migration or external state rollback is required.
