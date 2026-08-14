# R115 P1 Source-Passage Provenance Binding WPDCR

agent_id: CODEX

## Plan, difficulty and result

R115 closes the remaining P1 provenance-integrity gap: caller-supplied extraction text could previously inherit a KnowledgeEpisode manifest and source hash without proving derivation. The implemented P1 contract is deliberately narrow and verifiable: normalized full-body equality or normalized contiguous source span only.

The resulting `knowledge-extraction-binding-v1` is privacy-minimized. It contains the full source content hash, extracted passage hash, normalized start/end offsets and schema version; it contains no source body or raw pointer. The binding is constructed before decomposition, packet creation, store import or index mutation.

## Validation and negative evidence

Focused R115 tests: 17/17 PASS. Full Phase-3 regression: 263/263 PASS. Adversarial coverage proves fabricated passage rejection before mutation, normalized exact-body and valid subspan acceptance, malformed binding verifier denial, and duplicate-union/restart/index-rebuild preservation.

## Boundaries and next gate

P1 intentionally does not support discontinuous extraction; that requires a future governed contract. No private source/store was read, no real ingestion ran, and formal PROJECT/GLOBAL promotion, P2-P5, production bridge, scheduler, QCLAW dependency, permissions, trading and merge remain locked. The next gate is exact-head GitHub CI and GPT final P1 review.
