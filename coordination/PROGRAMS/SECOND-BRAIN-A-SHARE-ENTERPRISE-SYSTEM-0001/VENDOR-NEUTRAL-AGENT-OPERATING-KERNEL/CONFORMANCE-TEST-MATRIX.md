# Conformance Test Matrix

> `agent_id: CODEX`
>
> `scope: reference runtime and candidate documentation`

## Matrix

| Area | Required behavior | Automated evidence |
|---|---|---|
| Authority | Hard denials accumulate; W1 lease scopes intersect; same-layer conflicts fail closed | `test_authority_intent.py` |
| Determinism | Directive and provider input order do not change hashes | `test_authority_intent.py`, `test_routing.py` |
| Intent | Duplicate requirements and invalid budgets are rejected | `test_authority_intent.py` |
| Provenance | Inference requires evidence; UNKNOWN has confidence 0 | `test_contracts.py`, `test_epistemic_memory.py` |
| Memory | Candidate-only, idempotent, no canonical self-promotion | `test_epistemic_memory.py` |
| Routing | Brand display name does not affect score or hash | `test_routing.py` |
| Fail closed | Stale, unavailable, over-cost, over-latency, and side-effect routes reject | `test_routing.py` |
| Recovery | Authority drift, external drift, their combined state, and duplicate effects detect | `test_recovery_completion.py` |
| Completion | Requirement-evidence scope prevents overclaim | `test_recovery_completion.py` |
| Schema | Draft 2020-12 validates all ten serialized contract instances | `test_schema_surface.py`, `test_schema_instances.py` |
| Public neutrality | Common Prompt has no named vendor/product | `test_public_neutrality.py` |
| Source boundary | Raw capture is absent and source remains unverified | `test_public_neutrality.py` |
| Blueprint protection | Canonical PEOS hash remains unchanged | `test_public_neutrality.py` |
| Activation | Candidate status and disabled activation remain explicit | `test_public_neutrality.py` |
| Archive evidence | Three clean archives have stable machine-readable reports | `ci_verify.py`, dedicated CI workflow |

## Claim Limits

Passing these tests proves only:

- the reference implementation behaves as specified on the covered synthetic
  cases;
- the candidate documentation is internally aligned with key contract fields;
- the common runtime Prompt is free of the named vendor/product identifiers
  checked by the test;
- canonical PEOS v1.0 was not modified in this branch.

It does not prove:

- authenticity of the third-party capture;
- production readiness;
- cross-model behavioral equivalence;
- live tool-provider optimality;
- market validity;
- real trading safety;
- correct integration with W1, W3, W8, W10, or Phase 3.

## Required Future Suites

1. Cross-model semantic equivalence with at least two versioned models.
2. Mutation tests for authority, provenance, memory promotion, and routing.
3. Simulated process interruption at every checkpoint boundary.
4. Adapter tests against accepted W1/W3/W8 contracts.
5. Long-context recovery with stale and contradictory project state.
6. Shadow evaluation of unnecessary verification and tool-route quality.
