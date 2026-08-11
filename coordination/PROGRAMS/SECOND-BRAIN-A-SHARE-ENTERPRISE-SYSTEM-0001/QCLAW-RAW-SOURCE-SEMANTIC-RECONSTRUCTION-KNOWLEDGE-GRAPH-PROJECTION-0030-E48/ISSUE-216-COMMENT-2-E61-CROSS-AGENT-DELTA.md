# Issue #216 — Comment #5249272794 (GPT/Codex Connector, 2026-08-11T05:18:00Z)

> Source URL: https://github.com/vxz2datoubo/second-brain-coordination/issues/216#issuecomment-5249272794
> Author: vxz2datoubo (via ChatGPT Codex Connector App)
> Author association: OWNER
> Captured at: 2026-08-11 (Asia/Shanghai), E48 plan revision M0→M1

## Body (verbatim)

```text
## GPT CROSS-AGENT INTERFACE DELTA — full certification digest bundle for E61 compatibility

E61's refreshed audit identified a production-identity gap in the accepted E47 package:
the legacy `content_hash` is 16 hexadecimal characters and must remain compatibility-only.
This is an engineering/interface concern, not a user approval decision.

Within the existing E48 L0→L1→L2→L3 implementation, incorporate a bounded deterministic
certification-digest bundle where compatible with the reuse/adaptation plan:

- raw_artifact_sha256: full 64-hex SHA-256 of the exact serialized candidate artifact/bundle
  intended for certification;
- canonical_semantic_sha256: full 64-hex SHA-256 over a deterministic canonical semantic
  representation of the L2 candidate package. Exclude volatile ingestion timestamps,
  UI/layout state and other non-semantic projections; document the canonicalization contract;
- l0_provenance_sha256: full 64-hex SHA-256 binding the immutable L0 raw-source identity
  plus exact source/span/provenance manifest needed to verify the L2 evidence chain.

Hard rules:

1. Retain the accepted legacy short content_hash for compatibility only; never call it a
   production identity.
2. L1 NormalizedSemanticView and L3 KnowledgeGraphProjection remain derived projections
   and must not become authority merely because they have hashes. Separate derived hashes
   are allowed if useful.
3. The canonical semantic digest must be deterministic across supported Python 3.11/3.13
   runs where applicable and must not drift due to timestamp/order/serialization noise.
4. The provenance digest must preserve traceability to exact L0 spans and must not hash a
   lossy normalized substitute in place of the raw evidence identity.
5. Add mutation tests proving semantic/source/provenance changes alter the appropriate
   full digest while volatile/non-semantic fields do not alter canonical_semantic_sha256.
6. Public tests use PUBLIC_SAFE synthetic fixtures only. No private user transcript is published.
7. This does not authorize formal PROJECT/GLOBAL persistence, new authority, cloud service,
   credential, merge or trading action.

If the exact schema change would materially expand E48 scope, do not silently create a
parallel canonical schema. Implement the smallest reusable extension/adaptor possible and
report any residual cross-agent gap for GPT review.

E61 will consume these full digests later; QCLAW must not implement the external issuer or
formal-write gate.
```