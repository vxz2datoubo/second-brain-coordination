# ============================================================================
# DECISION LOG — P0 Architecture Foundation
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## Purpose

This document records all significant architecture and design decisions made during
P0 (Architecture Foundation) of the knowledge atomization task. Each decision entry
includes context, options considered, chosen option, rationale, consequences, and
reversibility assessment.

Decisions are referenced by `AtomizationDecision.decision_id` entries when atoms
are extracted from these documents in subsequent phases (META-DIGEST).

---

## Decisions

### DEC-001: Use SHA-256 Content-Addressable IDs

| Field | Value |
|---|---|
| **decision_id** | `DEC-001` |
| **date** | 2026-07-22 |
| **context** | Knowledge atoms need unique identifiers that are deterministic (same content → same ID), collision-resistant, and human-readable enough for debugging and cross-referencing. Options: sequential integers, UUIDs, content-addressed hashes, or hybrid approaches. |
| **options_considered** | 1. Sequential integers (1, 2, 3...) — simple but non-deterministic across rebuilds. Collisions guaranteed between agents.<br>2. UUIDv4 — unique but non-deterministic. Same atom regenerated gets a different UUID.<br>3. SHA-256 content hash — deterministic, content-addressed, collision-resistant. Slightly longer and less human-readable.<br>4. Semantic ID with namespace (PRJ-TYPE-0001) — human-readable but requires global coordination to avoid collisions. |
| **chosen_option** | SHA-256 content-addressed IDs with type prefix (`AT-`, `REL-`, `CNF-`, `UNK-`, `SRC-`, `DIG-`) and 8-character hex suffix. |
| **rationale** | Deterministic IDs are required by the architecture's principle #20 (Deterministic Reproducibility). Content addressing ensures different agents cannot create conflicting IDs for the same knowledge. SHA-256 is widely available, well-understood, and collision-resistant at our scale. The 8-character truncation keeps IDs compact while maintaining adequate uniqueness for knowledge graph navigation. |
| **consequences** | Positive: Rebuild verification possible. Cross-agent deduplication automatic. Merge safety guaranteed. Negative: IDs are opaque (not human-meaningful without a lookup). 8-char truncation has non-zero collision probability at large scale (>10,000 atoms). Requires Unicode normalization for consistent hashing. |
| **reversibility** | MODERATE. Switching to a different ID scheme would require regenerating all atom IDs and updating all relation references. Existing atoms would need SUPERSEDES chains. The architecture includes a versioned hash scheme that accommodates future changes. |

---

### DEC-002: Privacy Class Is Descriptive, Not Access Control

| Field | Value |
|---|---|
| **decision_id** | `DEC-002` |
| **date** | 2026-07-22 |
| **context** | The architecture needed a mental model for handling knowledge with different privacy natures. Early versions conflated privacy classification with storage decisions (private knowledge → local storage only). Issue #59 explicitly corrects this: "privacy_class does NOT block public storage." |
| **options_considered** | 1. Privacy class controls storage and transport (private = local only) — simpler mental model but conflates independent concerns.<br>2. Privacy class is purely descriptive; separate fields control storage, transport, and AI access — more complex but architecturally correct.<br>3. Drop privacy_class entirely; use only storage_targets + transport_visibility — less expressive, loses useful metadata. |
| **chosen_option** | Six independent fields: `privacy_class` (descriptive), `storage_targets` (placement), `transport_visibility` (transmission), `gpt_access` (AI readability), `authority_level` (trust), `knowledge_status` (lifecycle). Only CREDENTIAL_VALUE and FINANCIAL_VALUE have hard boundaries (storage_targets=NONE). |
| **rationale** | Issue #59 explicitly corrects the conflation: privacy_class describes the knowledge's NATURE, not its storage policy. Separating these concerns allows: (1) private knowledge to be shared publicly with user authorization, (2) public knowledge to be stored privately if desired, (3) different access patterns for different audiences. The six-field model is more expressive without being more restrictive. |
| **consequences** | Positive: Flexible, expressive, architecturally clean. Each field does one thing. Negative: 72 theoretical combinations (4×3×3×2) — more complex for new agents to learn. Requires STORAGE-TRANSPORT-ACCESS-MATRIX.yaml to guide default assignments. Quality gates enforce invalid combinations (CREDENTIAL_VALUE + PUBLIC_GITHUB → FAIL). |
| **reversibility** | LOW. Once atoms exist with this six-field model, collapsing fields would lose information. Adding more fields is easy; removing or merging fields is hard. |

---

### DEC-003: Use 8-Character Hash Suffix for Atom IDs (with Collision Fallback to 12)

| Field | Value |
|---|---|
| **decision_id** | `DEC-003` |
| **date** | 2026-07-22 |
| **context** | SHA-256 produces 64 hex characters. Using the full hash makes IDs unwieldy for human reference. A shorter suffix balances readability with collision avoidance. |
| **options_considered** | 1. Full 64-char hash — maximum collision resistance but unreadable (e.g., AT-A7F3B92CE1D204F5...).<br>2. 8-char suffix — readable, 50% collision probability at ~77,000 atoms.<br>3. 12-char suffix — somewhat less readable, 50% collision at ~20,000,000 atoms.<br>4. 6-char suffix — very readable, 50% collision at only ~3,000 atoms (too risky). |
| **chosen_option** | 8-char suffix by default, with automatic expansion to 12 chars on collision. Collision trigger: switch to 12 chars globally if >0.1% of atoms collide. |
| **rationale** | 8 characters balances readability and uniqueness. At 200 expected atoms (this task), collision probability is ~0.001%. The dynamic expansion strategy avoids the cost of 12-char IDs until needed. The collision trigger (0.1% = 1 in 1000) is conservative and can be tightened based on actual collision rates. |
| **consequences** | Positive: Readable IDs for human debugging and cross-reference. Adequate collision resistance at our scale. Negative: Collision handling adds complexity (expanded IDs, relation updates). Schema must accept both 8 and 12-char IDs (`{8,12}` pattern). |
| **reversibility** | MODERATE. If collision rates exceed expectations, bump hash_scheme_version to 2.0.0 and use 12-char globally. Existing 8-char IDs can continue to work for non-colliding atoms. |

---

### DEC-004: 27 Explicit Relation Types + RELATED_TO Fallback

| Field | Value |
|---|---|
| **decision_id** | `DEC-004` |
| **date** | 2026-07-22 |
| **context** | Knowledge relationships between atoms can be highly specific. A taxonomy with too few types loses semantic precision; too many types creates classification burden. |
| **options_considered** | 1. 5 generic types (supports, contradicts, depends_on, part_of, related_to) — simple but loses semantics (correlation vs causation indistinguishable).<br>2. 27 specific types across 7 categories — preserves original semantics but requires learning curve.<br>3. Free-form string relations — most expressive but cannot be queried systematically, defeats purpose of typed relations. |
| **chosen_option** | 27 typed relations with RELATED_TO as escape hatch. 7 categories: Logical/Evidential (7), Dependency (5), Structural/Taxonomic (3), Provenance/Lineage (5), Gap/Unknown (4), Implementation/Verification (2), Fallback (1). |
| **rationale** | Specific relation types enable precise queries ("find all atoms that CONTRADICTS the claim that X causes Y"). The 24-step decision flow provides clear classification guidance. RELATED_TO with mandatory description field captures edge cases without blocking classification. The relational taxonomy preserves the original semantics from source text rather than degrading them. |
| **consequences** | Positive: Query precision, semantic preservation, clear decision tree. Negative: Classification burden — agents must learn 27 types. Quality gate QG-REL-002 monitors RELATED_TO overuse. Schema has 30 types vs taxonomy 27 (3 convenience inverse relations for querying). |
| **reversibility** | MODERATE. New relation types can be added (schema extended). Existing types are hard to remove (would require reclassifying all relations). The version chain would handle type taxonomy evolution. |

---

### DEC-005: Conflicts Are First-Class Knowledge, Not Errors to Resolve

| Field | Value |
|---|---|
| **decision_id** | `DEC-005` |
| **date** | 2026-07-22 |
| **context** | When two knowledge atoms contradict each other, what should the system do? Options range from picking the "best" one to preserving both with explicit conflict documentation. |
| **options_considered** | 1. Resolve conflicts by choosing the highest-confidence atom — simple but destroys valuable knowledge. The "wrong" atom may be contextually correct. Violates adversarial evaluation principle CONFLICT_NOT_RETURNED.<br>2. Merge conflicting claims into a "balanced" atom — creates false compromise, loses both original claims.<br>3. Preserve both atoms with explicit CONTRADICTS relation and KnowledgeConflict entry — most complex but preserves all knowledge. |
| **chosen_option** | Both conflicting atoms are preserved. A CONTRADICTS relation links them, and a KnowledgeConflict entry documents: conflict_type, resolution_status, evidence for each side, and impact assessment. Neither atom is deleted. Resolution status tracks whether the conflict has been resolved, but even resolved conflicts preserve both atoms. |
| **rationale** | Conflicts ARE knowledge. A system that hides contradictions is less trustworthy than one that surfaces them. The adversarial evaluation framework in PR #57 explicitly tests CONFLICT_NOT_RETURNED as a critical failure. 12 conflict types capture the nuance of different contradiction categories. |
| **consequences** | Positive: Trustworthy system, complete knowledge preservation, supports adversarial evaluation. Negative: Knowledge graph contains contradictory information — requires consumer awareness. Storage cost doubles for conflicting claims. Quality gates must ensure both atoms are always present (QG-CNF-001). |
| **reversibility** | VERY LOW. Once deployed, removing conflict preservation would lose knowledge. This is a fundamental architectural choice. |

---

### DEC-006: UNKNOWN Is Knowledge — Never Delete Unknowns

| Field | Value |
|---|---|
| **decision_id** | `DEC-006` |
| **date** | 2026-07-22 |
| **context** | Knowledge sources frequently contain explicit statements of uncertainty, knowledge gaps, and unanswered questions. What should happen to these when digesting knowledge? |
| **options_considered** | 1. Filter out unknowns — "if we don't know it, don't store it." Creates false impression of completeness.<br>2. Store unknowns inline in atoms — embeds gaps but doesn't track resolution.<br>3. First-class KnowledgeUnknown entities with deterministic IDs, verification paths, and resolution tracking. |
| **chosen_option** | KnowledgeUnknown as first-class entities. Every UNKNOWN has: a precise question, bounded by what IS known, a verification path, an impact assessment, and resolution tracking. Unknowns are never deleted; when resolved, they are marked as RESOLVED with a link to the resolving atom. |
| **rationale** | Principle #8: "UNKNOWN Is Knowledge — admitting what we don't know is more honest than pretending to know." Unknowns guide research, prevent wasted effort investigating solved problems, and maintain intellectual honesty. The deterministic `unknown_id` ensures the same question raised by different sources is deduplicated. |
| **consequences** | Positive: Honest knowledge representation, research guidance, duplicate prevention. Negative: UNKNOWN count may be larger than KNOWN count in early phases. Verification paths impose documentation burden. Quality gate QG-UNK-001 enforces preservation. |
| **reversibility** | VERY LOW. This is a fundamental philosophical choice about the nature of the knowledge system. Removing unknown support would require deleting all UNKNOWN entries and their relations. |

---

### DEC-007: All Knowledge Starts as CANDIDATE_ONLY

| Field | Value |
|---|---|
| **decision_id** | `DEC-007` |
| **date** | 2026-07-22 |
| **context** | When a new atom is created, what is its initial authority level? Options: trust the source (inherit source authority) or start conservative (candidate until reviewed). |
| **options_considered** | 1. Inherit authority from source quality — authoritative sources produce AUTHORITATIVE atoms. Fast but propagates errors from "authoritative" sources.<br>2. Always start at CANDIDATE_ONLY — all atoms must be explicitly reviewed and promoted. Conservative but honest.<br>3. Auto-promote after N independent confirmations — algorithmic trust. Complex and error-prone. |
| **chosen_option** | All atoms start with `authority_level: CANDIDATE_ONLY`. Promotion to REVIEWED, APPROVED, or AUTHORITATIVE requires explicit review. Source prestige does NOT automatically confer atom authority. |
| **rationale** | Principle #14: "Source Authority Is Not Atom Authority." Even the most prestigious source can contain errors, outdated information, or context-dependent claims. Starting conservative prevents false authority propagation. The promotion path (CANDIDATE_ONLY → REVIEWED → APPROVED → AUTHORITATIVE) provides a clear trust escalation mechanism. |
| **consequences** | Positive: Honest trust representation, prevents authority laundering. Negative: All atoms start equally untrusted — review process needed for trust escalation. Query results must distinguish candidate vs authoritative atoms. |
| **reversibility** | LOW. Changing the default would require updating all existing atoms' authority_level. The promotion pipeline would need redesign. |

---

### DEC-008: Deterministic Field Ordering and Canonicalization for Packet Hash

| Field | Value |
|---|---|
| **decision_id** | `DEC-008` |
| **date** | 2026-07-22 |
| **context** | The LearningPacket hash must be deterministic for rebuild verification. This requires precise specification of which fields are included and how they are serialized. |
| **options_considered** | 1. Hash the raw JSON file — simple but breaks on whitespace/formatting changes; non-deterministic with pretty-printing variations.<br>2. Hash a canonical subset of fields — requires defining the subset but ensures determinism.<br>3. Use a canonical serialization format (e.g., Canonical JSON, JCS) — well-defined but adds dependency. |
| **chosen_option** | Define a canonical subset of hash-input fields for each entity type. Sort all arrays by deterministic ID. Sort all object keys alphabetically. Serialize as compact JSON (no indentation). Exclude wall-clock timestamps (`created_at`, `updated_at`), process metadata (`run_duration_ms`, `host_name`, `access_timestamp`). |
| **rationale** | Including only semantic fields (not timestamps) ensures rebuilds produce identical hashes. This was a lesson learned from PR #57's ContextBundle hash drift (caused by including wall-clock timestamps in the semantic hash). The canonical subset is clearly defined in DETERMINISTIC-IDENTITY.md. |
| **consequences** | Positive: True deterministic reproducibility. Rebuild verification possible. Negative: If a field should be hash-relevant but was excluded, identical hashes could mask content differences. Hash scheme versioning handles changes. |
| **reversibility** | MODERATE. Changing the hash input schema requires bumping hash_scheme_version. Old packets retain old hash scheme. Version chain handles migration. |

---

### DEC-009: Secret Values Are the Only Hard Boundary

| Field | Value |
|---|---|
| **decision_id** | `DEC-009` |
| **date** | 2026-07-22 |
| **context** | The system needs a clear, simple security boundary. What content is permanently denied from all outputs? |
| **options_considered** | 1. Block all PRIVATE_KNOWLEDGE from public storage — conservative but over-restrictive. Prevents user-authorized sharing.<br>2. Block only explicitly marked sensitive content — permissive but risk of missing secrets.<br>3. Block CREDENTIAL_VALUE and FINANCIAL_VALUE only — narrow boundary with automated detection. |
| **chosen_option** | Only authentication, access, and financial secret VALUES are permanently denied. CREDENTIAL_VALUE (API keys, tokens, passwords, private keys) and FINANCIAL_VALUE (broker keys, payment keys, crypto keys). All other knowledge (private, personal, internal) may be stored publicly with user authorization. Metadata ABOUT secrets (where they live, what type) IS allowed. |
| **rationale** | Principle #17: "Secret Values Are the Only Hard Boundary." This provides a clear, automatable rule with regex-based detection in SECRET-SCAN.yaml. It doesn't require subjective classification of what constitutes "private." The boundary is narrow enough to be enforced automatically and broad enough to catch the most dangerous content. |
| **consequences** | Positive: Simple, automatable rule. Clear security model. Knowledge is maximally preserved. Negative: Requires user authorization for sharing private knowledge publicly. The 14 regex patterns need ongoing maintenance. False negatives (undetected secrets) remain a risk — mitigated by SECRET-SCAN.yaml pattern refinement. |
| **reversibility** | LOW. Expanding the boundary (blocking more content) is easy. Shrinking it (allowing more) would require re-scanning and potentially un-redacting. |

---

### DEC-010: 8-Stage Pipeline with Checkpoint-Based Recovery

| Field | Value |
|---|---|
| **decision_id** | `DEC-010` |
| **date** | 2026-07-22 |
| **context** | The atomization process has multiple stages with different failure modes and costs. A monolithic process would require full restart on any failure; a staged process allows partial recovery. |
| **options_considered** | 1. Single monolithic pass — simplest implementation but no partial recovery; any failure requires full restart.<br>2. 8 discrete stages with checkpoints — more complex but enables targeted recovery and incremental progress.<br>3. Event-driven micro-pipeline — most flexible but over-engineered for current scale. |
| **chosen_option** | 8-stage pipeline: Source Discovery → Secret Scan → Structure Parse → Segmentation → Atom Extraction → Relation Extraction → Conflict/Unknown Detection → Quality Gate. Each stage saves a checkpoint. Failure in stage N resumes from stage N (not from scratch). |
| **rationale** | The most expensive stages (4: Atom Extraction, 5: Relation Extraction) involve LLM calls. Restarting from scratch on failure would waste significant tokens. Checkpoints preserve progress. The staged design also enables independent testing of each stage. |
| **consequences** | Positive: Efficient failure recovery, independent stage testing, progress visibility. Negative: Checkpoint storage overhead, stage coupling (later stages depend on earlier output format), potential for inconsistent partial states. |
| **reversibility** | MODERATE. Adding stages is easy (insert at appropriate point). Merging stages is harder (checkpoint migration). The stage boundary definitions serve as the interface contract. |

---

### DEC-011: P0 Deliverables Include All 12 Gap-Filling Files as Architecture Documents

| Field | Value |
|---|---|
| **decision_id** | `DEC-011` |
| **date** | 2026-07-22 |
| **context** | The initial P0 checkpoint (20%) declared 21 deliverables. Eleven additional gap-filling deliverables were identified as necessary for architecture completeness: RELATION-TAXONOMY.yaml, STORAGE-TRANSPORT-ACCESS-MATRIX.yaml, DETERMINISTIC-IDENTITY.md, ATOMIZATION-PIPELINE.md, QUALITY-GATE-REPORT.md, UNKNOWN-REGISTRY.yaml, DECISION-LOG.md, QCLAW-FEEDBACK.yaml, OUTCOME-CALIBRATION-REVIEW.yaml, AI_HANDOFF.yaml, KNOWLEDGE-DIGEST-RECEIPTS/README.md, and STAGE-MANIFEST.md. |
| **options_considered** | 1. Defer gap-filling files to P1 or P2 — keeps P0 scope small but leaves architecture incomplete.<br>2. Add gap-filling files as P0-A sub-package — extends P0 but maintains clean checkpoint.<br>3. Absorb into P0 as additional deliverables — simplest but increases P0 file count from 21 to 33. |
| **chosen_option** | Gap-filling files are absorbed into P0 as additional deliverables. PROGRESS-CHECKPOINT.yaml is updated to reflect 33 total files (21 original + 12 new). The checkpoint percentage remains at 20% (P0 is "Architecture Foundation" regardless of file count). |
| **rationale** | These files are architecture documentation (taxonomies, matrices, manifests, reports), not digestion output. They belong in P0 because they define the system before digestion begins. Deferring them would leave P0 incomplete and force P1 to reference undefined structures. |
| **consequences** | Positive: Complete architecture foundation. All structures defined before P1 digestion begins. Negative: P0 scope grew slightly (12 additional deliverables). PROGRESS-CHECKPOINT.yaml needs recalibration. |
| **reversibility** | HIGH. These are documentation files — they can be revised, split, or merged without affecting downstream artifacts. |

---

### DEC-012: Use NFKC Unicode Normalization for Deterministic Hashing

| Field | Value |
|---|---|
| **decision_id** | `DEC-012` |
| **date** | 2026-07-22 |
| **context** | Identical semantic content encoded in different Unicode forms (e.g., `ﬁ` ligature vs `fi`, fullwidth `Ａ` vs halfwidth `A`) would produce different SHA-256 hashes without normalization. A normalization standard is needed for deterministic identity. |
| **options_considered** | 1. No normalization — fastest but breaks determinism across different text sources.<br>2. NFC normalization — handles composed characters but NOT compatibility characters (e.g., `²` stays as `²`).<br>3. NFKC normalization — most aggressive; handles both composition and compatibility equivalence.<br>4. NFD normalization — decomposed form; produces longer strings. |
| **chosen_option** | NFKC (Normalization Form Compatibility Composition). |
| **rationale** | NFKC handles the broadest range of Unicode equivalence: fullwidth/halfwidth (`Ａ` → `A`), ligatures (`ﬁ` → `fi`), superscripts (`²` → `2`), and other compatibility characters. This ensures that the same semantic content encoded in different Unicode forms produces the same hash. NFKC is widely supported in standard libraries across languages. |
| **consequences** | Positive: Robust determinism across diverse text sources. Cross-language consistency. Negative: NFKC is lossy — canonicalization may change visual appearance. Some legitimate semantic distinctions (superscript in mathematical notation) may be lost. Mitigation: the normalization is applied ONLY for hash computation, not for display or storage. |
| **reversibility** | LOW. Changing the normalization standard would change all atom IDs (different hash output). Would require hash_scheme_version bump and full regeneration. |

---

## Decision Summary

| ID | Decision | Reversibility | Risk |
|---|---|---|---|
| DEC-001 | SHA-256 content-addressable IDs | MODERATE | Collision at scale |
| DEC-002 | Privacy class is descriptive, not access control | LOW | Agent confusion |
| DEC-003 | 8-char hash suffix (12 on collision) | MODERATE | Collision at scale |
| DEC-004 | 27 relation types + RELATED_TO fallback | MODERATE | Classification learning curve |
| DEC-005 | Conflicts as first-class knowledge | VERY LOW | Knowledge graph complexity |
| DEC-006 | UNKNOWN as first-class knowledge | VERY LOW | Documentation burden |
| DEC-007 | CANDIDATE_ONLY by default | LOW | Review backlog |
| DEC-008 | Deterministic field ordering for packet hash | MODERATE | Field exclusion errors |
| DEC-009 | Secret values as only hard boundary | LOW | False negatives in detection |
| DEC-010 | 8-stage checkpoint pipeline | MODERATE | Stage coupling |
| DEC-011 | P0 absorbs 12 gap-filling files | HIGH | Scope creep perception |
| DEC-012 | NFKC Unicode normalization | LOW | Semantic loss in math notation |

## Reversibility Heat Map

```
HIGH REVERSIBILITY:    DEC-011 (file structure)
                       DEC-003 (hash suffix length)

MODERATE REVERSIBILITY: DEC-001 (ID scheme), DEC-004 (relation types),
                        DEC-008 (hash fields), DEC-010 (pipeline stages)

LOW REVERSIBILITY:      DEC-002 (six-field model), DEC-007 (candidate default),
                        DEC-009 (secret boundary), DEC-012 (NFKC normalization)

VERY LOW REVERSIBILITY: DEC-005 (conflict preservation), DEC-006 (unknown preservation)
```

The two "VERY LOW" reversibility decisions (conflicts and unknowns as first-class
knowledge) are the most consequential architectural choices. They define the
fundamental philosophy of the knowledge system: preserve ALL knowledge, including
contradictions and gaps, rather than curating a "clean" but incomplete picture.
