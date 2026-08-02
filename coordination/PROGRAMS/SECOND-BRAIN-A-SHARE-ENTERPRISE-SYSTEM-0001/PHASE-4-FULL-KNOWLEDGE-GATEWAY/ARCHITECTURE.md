# Phase 4 Architecture

## Runtime Ownership

Phase 3 remains the system of record and query runtime:

- `MemoryStore`: one SQLite candidate store.
- `FusionEngine`: one candidate-only import path.
- `QueryPlan`: one internal query contract.
- `ContextAssembler`: one retrieval and relation-expansion runtime.
- `ContextBundle`: one semantic context projection.

Phase 4 adds wrappers and projections inside the same Python package:

- `KnowledgeSourceManifest`: knowledge-specific source, authorization, license, privacy, format, hash, version and revocation metadata.
- `LocalKnowledgeReference`: opaque local reference; public metadata never contains the real path or body.
- `KnowledgeGatewayPolicy`: manifest-bound, hash-bound, read-only access policy.
- `KnowledgeAccessDecision`: deterministic grant, denial, waiting or revocation receipt.
- `KnowledgeQuery`: external request that compiles into the existing `QueryPlan`.
- `LocalFileKnowledgeAdapter` and `LocalDirectoryKnowledgeAdapter`: exact hash-bound local readers.
- `ExistingServiceKnowledgeAdapter`: interface-only until a separately approved local protocol exists.

## Data Flow

```text
opaque reference + exact runtime path
-> manifest and policy validation
-> license and credential-value gates
-> size and SHA256 verification
-> deterministic local parsing
-> semantic duplicate consolidation
-> candidate LearningPacket
-> existing MemoryStore and automatic index
-> KnowledgeQuery to existing QueryPlan
-> existing ContextAssembler and ContextBundle
```

## Access Axes

- `knowledge_status`: candidate, approved, conflict, unknown, superseded, rejected or quarantined.
- `gpt_access`: authorized candidate knowledge remains `FULL_SEMANTIC_ACCESS`.
- `transport_visibility`: public-safe body or private local-only body.
- `authority_level`: always `CANDIDATE_ONLY` in this task.

Current queries exclude superseded and revoked sources by default. Historical or audit queries must request those states explicitly. Credential documentation may be retrieved; credential values and queries asking to reveal them are denied.

## Public Evidence

Public receipts may contain manifest IDs, hashes, counts, reason codes, deterministic packet/query/context hashes and boolean safety states. They may not contain local paths, private bodies, raw authentication material, database files or query result text from private sources.
