# P2 unified retrieval and ContextBundle v1 implementation plan

agent_id: CODEX  
route: `CODEX-GPT-SECOND-BRAIN-COGNITIVE-CLOSED-LOOP-FUSION-R116-P2-UNIFIED-RETRIEVAL-CONTEXT-PLAN`  
mode: `project_plan`  
scope: `P2_PLAN_AND_PUBLIC_SAFE_AUDIT_ONLY`

## Decision

P2 will extend the existing `QueryPlan` and `ContextAssembler` over the existing `MemoryStore`.  It will not create a new memory store, raw-source path, promotion path, scheduler or production bridge.  The target is a versioned `GPTSecondBrainContextBundle v1` produced only after uniform admission and carried by redacted provenance.

## Admission matrix (performed before any ranking, expansion or voting)

| Object family | Required identity and scope | Privacy/time/lifecycle admission | Bundle role if admitted |
| --- | --- | --- | --- |
| Conversation memory | project scope and matching `user_scope`; packet and episode provenance | source-class/privacy match; permitted user role; `valid_at`; CURRENT rejects effective closure/supersession | evidence or current lineage head |
| Knowledge atom | project scope, user scope, privacy-domain compatibility, source/extraction binding | valid time; identity and epistemic role; CURRENT revalidation; multi-domain only explicit synthetic aggregate/no-vote | evidence, support, counter or conflict endpoint |
| Plan/event/constraint | packet-derived claim role and relation identity | user/project scope; freshness profile; valid time; lifecycle state | temporal/relationship context, never an authority escalation |
| Stance/evaluation | packet-derived user evaluation, credibility or bias role | matching user; privacy and valid-time checks | labeled perspective, never converted into fact evidence |
| Conflict | both endpoints and conflict record are independently admissible | reject hidden endpoint, disallowed scope/domain, stale-only CURRENT endpoint | visible conflict with redacted explanation |
| Unknown | related atom(s) or explicit open unknown is admissible | scope/privacy-compatible related IDs; no raw source payload | unresolved item and ABSTAIN reason |

The same policy is called by lexical retrieval, optional semantic-provider results, temporal lookup, relation traversal, provenance adjacency and structural analogy.  No channel may append an atom after admission, and an analogy may neither serve as evidence nor bypass scope, privacy, time, lifecycle or budget rules.

## `GPTSecondBrainContextBundle v1`

The implementation will add a versioned projection over the existing `ContextBundle`; compatibility fields remain until a later approved migration.

```yaml
schema_version: GPTSecondBrainContextBundle/v1
request:
  query_id: opaque-deterministic-id
  plan_hash: content-addressed-hash
  intent: CURRENT|HISTORICAL
  valid_at: UTC-instant-or-null
  scope_fingerprint: redacted-hash
  privacy_mode: isolated|synthetic_aggregate_no_vote
admission:
  admitted_atom_ids: [opaque-id]
  rejected_counts_by_reason: {reason: integer}
  semantic_provider_state: NOT_CONFIGURED|AVAILABLE|UNAVAILABLE|DENIED
evidence:
  current_lineage_heads: [EvidenceItem]
  strongest_support: [EvidenceItem]
  strongest_counter_or_alternative: [EvidenceItem]
  conflicts: [ConflictItem]
  unknowns: [UnknownItem]
context:
  relations: [RelationItem]
  temporal_context: [TemporalItem]
  stance_context: [StanceItem]
  analogies: [AnalogyItem]
provenance:
  adjacency: [RedactedProvenanceEdge]
  freshness_explanation: [FreshnessItem]
ranking:
  policy_version: unified-retrieval-v1
  ordered_ids: [opaque-id]
  omitted_due_to_budget: integer
trust_gate:
  state: CANDIDATE_ONLY|ABSTAIN
  reasons: [public-safe-reason]
authority:
  formal_project_global_write: LOCKED
  no_trade: true
```

`EvidenceItem` includes opaque atom ID, atom type, role label, score components, current/historical lifecycle label, confidence and a redacted provenance reference. `RedactedProvenanceEdge` contains packet hash, manifest identity/hash and relation type only; it never contains a raw pointer, conversation text or private source body. `AnalogyItem` is explicitly `non_evidentiary: true` and cannot contribute to support votes or a trust-gate pass.

## Retrieval algorithm and determinism

1. Validate `QueryPlan` and canonicalize all scope/privacy/time inputs to UTC instants and deterministic tuples.
2. Produce channel candidates: lexical index; optional semantic-provider boundary; exact temporal predicates; relation/entity graph; provenance adjacency; and optional structural analogy.
3. Run the shared admission predicate on every candidate and every traversed endpoint before it can enter a channel set. Record only public-safe rejection counts/reasons.
4. Canonically deduplicate by atom ID. Merge channel contributions into named score components; analogous results receive `non_evidentiary` only.
5. Compute a stable score with the frozen `unified-retrieval-v1` weights. Ties sort by canonical atom ID. An explicit synthetic aggregate may present cross-domain coverage but must not vote or raise confidence.
6. Apply independent evidence, relation and context budgets in stable order. Count omissions without exposing rejected identities.
7. Resolve lineages: CURRENT selects only active current heads; HISTORICAL requires `valid_at` and renders only atoms valid at that instant. Superseded/revoked/closed atoms never reappear in CURRENT merely due to graph or provenance adjacency.
8. Emit support, strongest alternative/counter, conflicts and unknowns separately. If no eligible evidence, required provenance is absent, scope is ambiguous, conflict prevents a safe response, or a required channel is unavailable, emit `ABSTAIN` with a non-sensitive reason.

The semantic provider is optional and receives only the minimum public-safe query representation approved by the caller. Provider failure is recorded as unavailable/denied and falls back to lexical/temporal/graph only; it cannot weaken admission or cause raw-source disclosure.

## Lifecycle and freshness rules

| Intent | Required time | Eligible lifecycle | Prohibition |
| --- | --- | --- | --- |
| CURRENT | query time or canonical now | active lineage head, not revoked, not expired, not superseded | no stale/closed atom resurrection through any channel |
| HISTORICAL | explicit timezone-aware `valid_at` | atom whose effective validity contains `valid_at`; historical conflict/unknown labels preserved | no current-state rewrite of historical facts |

Conversation `effective_valid_to` and `superseded_by`, and knowledge supersession/revocation rules, remain source-of-truth. Freshness is a disclosed context property, not a confidence promotion. Temporal parsing uses only deterministic timezone-aware instants; unparseable or naive timestamps fail closed.

## Adversarial acceptance matrix

| Test family | Required proof |
| --- | --- |
| Scope/privacy | same statement across users/projects; disallowed privacy domain; hidden graph endpoint; aggregate mode cannot vote |
| Time/lifecycle | naive/malformed time rejected; offsets compare as same instant; expired/superseded/revoked excluded from CURRENT; valid historical recall works |
| Channels | semantic provider unavailable; temporal-only hit; graph/provenance hit; every channel invokes admission; analogy never becomes evidence |
| Conflict/unknown | strongest counter appears beside support; hidden endpoint suppresses record; unresolved unknown triggers honest ABSTAIN when material |
| Provenance | packet-required atom rejected without packet lineage; bundle adjacency follows atom-to-packet-to-episode hashes; no raw pointer/body in bundle/log/fixture |
| Determinism | same fixture gives byte-equivalent ordered IDs and scores; tie ordering; dedup; budget omission count |
| Injection/secrets | generic prompt-injection forms and credential-shaped text rejected; public-safety scan remains clean |

## Authorized implementation slices and rollback

| Slice | Change boundary | Acceptance checkpoint | Rollback |
| --- | --- | --- | --- |
| P2.1 | Add internal candidate-set/admission report and tests to `retrieval.py` only | Existing `ContextBundle` compatibility plus admission parity | Remove new projection, retain existing assembler |
| P2.2 | Add `GPTSecondBrainContextBundle/v1` projection and deterministic multi-channel score combiner | Fixture exactness and no raw provenance | Feature flag/schema adapter removal |
| P2.3 | Move Memory Palace temporal/provenance/graph behavior behind the unified assembler; leave compatibility adapter delegating | Adapter parity tests and CURRENT/HISTORICAL tests | Restore adapter delegation boundary |
| P2.4 | Add optional semantic-provider interface and structural analogy projection, disabled by default | Provider-unavailable/no-evidence tests | Disable provider and analogy features; lexical path remains |

Every slice is candidate-only. No slice may read a real private source, instantiate a real private store, run ingestion/canary/scheduler, publish formal PROJECT/GLOBAL knowledge, deploy MCP/Gateway, alter E48/live/trading gates, or merge itself.

## Review gates

Before any P2 runtime code, GPT must accept this plan, schema, admission matrix, lifecycle table and adversarial matrix. After each later slice: focused synthetic tests, full Phase-3 regression, public-safety scan, YAML/JSON parser validation, `git diff --check`, exact-head CI and GPT review are required. This epoch does not authorize those runtime changes.
