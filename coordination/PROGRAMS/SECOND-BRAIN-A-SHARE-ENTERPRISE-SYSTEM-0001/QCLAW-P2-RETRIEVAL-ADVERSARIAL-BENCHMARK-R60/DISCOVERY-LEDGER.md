# R60 Discovery Ledger

Negative / failed probes and discovered gaps discovered while building the
benchmark. This is the honest record of what the audit revealed, not a success
narrative.

## D1 — Prompt-injection markers are split across two files with different sets

- `conversation_memory.py` uses a **4-marker** list (`_PROMPT_INJECTION_MARKERS`).
- `learning_packet.py` uses a **larger** marker set (11 entries incl. Chinese +
  `<system>`) PLUS a regex fallback (`ignore|disregard` variants + 中文"忽略…指令").
- **Gap:** a caller going through the conversation path (not the learning-packet
  verify path) is protected by only the 4-marker list. Paraphrased injection
  ("please act as if the earlier rules do not apply") is caught by neither.
  This is a **generalization gap**, not a P0 — the fail-closed *principle* holds
  for the enumerated markers.

## D2 — `_trust_gate` outcome is `ADMIT_CANDIDATE_ONLY`, not a bare `ADMIT`

- The canonical trust gate never emits a plain "ADMIT"; it emits
  `ADMIT_CANDIDATE_ONLY` with reason `scope_privacy_status_and_valid_time_passed`.
  The benchmark's `ADMIT` verdict maps to this outcome. Recorded to avoid the
  earlier harness bug where it compared against the wrong string.

## D3 — Knowledge atoms require the `capture_knowledge` path, not direct insert

- `MemoryStore.insert_atom` on a `knowledge_atom` raises
  `knowledge_requires_learning_packet_import`. The harness must use
  `capture_knowledge()` (which also enforces `knowledge_passage_not_derived_from_source`
  extraction binding and post-write scoped recall). This is a **strength** of the
  canonical design (no arbitrary caller text can inherit episode lineage), but it
  means the adversarial harness must go through the full reconciliation path.

## D4 — `capture_knowledge` post-write scoped recall is a hard gate

- `capture_knowledge` refuses a `semantic_query` that equals a candidate statement
  (`knowledge_paraphrase_or_relation_query_required`) and fails if post-write
  scoped recall cannot find the atom (`knowledge_post_write_scoped_recall_failed`).
  This is a real anti-Goodhart check: a source echo cannot masquerade as semantic
  recall. Two aggregate cases (r60-020, r60-065) hit this because P1 does not emit
  `aggregate_equivalence_key` → correctly downgraded to spec-pending.

## D5 — Orphan relation is fail-closed via SQLite FK, not via integrity_check

- With `PRAGMA foreign_keys=ON`, `insert_relation` on missing endpoints raises
  `IntegrityError: FOREIGN KEY constraint failed`. The invariant holds at the
  storage layer (stronger than a post-hoc integrity scan). The harness grades this
  as REJECT/PASS on the IntegrityError.

## D6 — Supersession valid-time ordering is enforced at correction build

- `build_conversation_correction` + `import_learning_packet` raises
  `conversation_supersession_valid_time_invalid` when the correction's
  `valid_from` is not later than the target's `valid_from`. Verified pass.

## D7 — Determinism / dedup / budget

- `canonical_json` (sort_keys) and `content_hash` are key-order independent;
  `plan_hash` is a property (not a callable) — recorded to avoid the recurring
  `TypeError: 'str' object is not callable` footgun.

## D8 — No hidden/disallowed relation endpoint leak

- `relations_around(selected_set)` only surfaces relations whose endpoints are in
  the admitted set; a relation to a forbidden atom is not traversed into the
  bundle (relation_depth=0 default confirms neighbor exclusion). Verified.

## Discovered gaps (carried to UNKNOWN-REGISTRY)

- `aggregate_equivalence_key` not emitted by P1 knowledge path → P2.2 (UNKNOWN-001).
- semantic provider transport contract unfrozen → P2.4 (UNKNOWN-002).
- structural analogy representation undefined → P2.4 (UNKNOWN-003).
- Memory Palace migration route unfrozen → P2.3 (UNKNOWN-004).
- cross-source semantic near-dup identity hash not in P1 → P2.x (UNKNOWN-005).
