# R60 UNKNOWN Registry

Items where the governing contract is **not frozen** or **ambiguous**. Per the
R60 `case_contract.epistemic_rule`, QCLAW must mark UNKNOWN and escalate to GPT —
it must NOT invent a rule and then grade Codex against its own invention.

## UNKNOWN-001 — `aggregate_equivalence_key` is a P2.2 concept not emitted by the P1 knowledge path

- **What:** The accepted R116 P2 plan requires synthetic aggregate to count
  `aggregate_equivalence_key` (not raw atom count) for the no-double-vote rule.
  The current Phase-3 `retrieval.py` `_trust_gate()` already *reads*
  `aggregate_equivalence_key` from `memory_metadata.knowledge`, but the P1
  `capture_knowledge` path does not **emit** it. So the P2.1 runtime cannot
  exercise P2.2 aggregate semantics today.
- **Cases affected:** r60-020, r60-065 (both set `runnable=false`, traced to
  `r116_plan`).
- **Escalation:** Codex P2.2 must define where `aggregate_equivalence_key` is
  assigned; until then the no-double-vote dimension is SPEC-PENDING.

## UNKNOWN-002 — semantic provider transport contract (P2.4)

- **What:** R116 plan makes the semantic provider **optional** and **disabled by
  default** (P2.4). The exact transport contract (request/response shape, error
  semantics, fallback-to-lexical path) is not frozen in canonical main.
- **Cases affected:** P2.4 slice (3 cases, `runnable=false`).
- **Escalation:** GPT must freeze the semantic provider contract before any P2.4
  adversarial case can be graded.

## UNKNOWN-003 — structural analogy representation (P2.4)

- **What:** R116 plan says `AnalogyItem` is explicitly `non_evidentiary: true`
  and cannot contribute a support vote. But the concrete representation of a
  "structural analogy" (how it is computed / stored / keyed) is not defined.
- **Cases affected:** P2.4 slice (analogy-related cases, `runnable=false`).
- **Escalation:** GPT must define the structural analogy representation before
  grading analogy channel admission parity.

## UNKNOWN-004 — Memory Palace migration (P2.3)

- **What:** P2.3 (Memory Palace migration) has no runtime in canonical main; the
  `memory_palace.py` module exists but the "migration" slice contract is not
  frozen as a route. Expected outcomes are spec-traced only.
- **Cases affected:** P2.3 slice (5 cases, `runnable=false`).
- **Escalation:** GPT must freeze the P2.3 route before grading.

## UNKNOWN-005 — cross-source near-duplicate / structural analogy semantic hash

- **What:** The benchmark probes "cross-domain denial" and "support + strongest
  counter/alternative coverage" but the canonical identity for cross-source
  near-duplicate detection (the semantic identity hash that says two differently
  phrased statements are the same proposition) is a P2.x concern, not frozen in
  the P1 runtime. The P1 runtime keys on `canonical_statement` normalization
  (NFKC), which is lexical, not semantic.
- **Escalation:** GPT should confirm whether P2.1 admission is expected to do
  semantic (not just lexical) near-dup collapse; if yes, that's a P2.2+ contract.

## UNKNOWN-006 — resource/process lifecycle measurability on the grading host

- **What:** `required_postflight` demands "measured zero task-owned descendants,
  zero orphans, zero unrelated terminations; UNKNOWN if not measurable". On this
  host the benchmark is a single synchronous Python process with no spawned
  children (stdlib only, no multiprocessing/subprocess workers). "Zero" is
  trivially true but not *instrumented*; `psutil` is intentionally NOT a
  dependency (matches E48/E50 zero-third-party constraint).
- **Escalation:** GPT should confirm that "single synchronous process, no child
  spawn, stdlib-only" satisfies the postflight requirement, or require a
  psutil-instrumented CI variant.

## UNKNOWN-007 — P2.2/P2.3/P2.4 grading authority

- **What:** 30 spec-pending cases carry an expected outcome traced to the R116
  plan / R117 route text, but the plan text is prose, not executable. The exact
  PASS/FAIL threshold for each spec-pending case cannot be machine-verified until
  Codex lands the slice and GPT freezes the executable contract.
- **Escalation:** GPT is the authority that turns plan prose into a gradable
  contract; QCLAW will not grade Codex against un-frozen prose.
