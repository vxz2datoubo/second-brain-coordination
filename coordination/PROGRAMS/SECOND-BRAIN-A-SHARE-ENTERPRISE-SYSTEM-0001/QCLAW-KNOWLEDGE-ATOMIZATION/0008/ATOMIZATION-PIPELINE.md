# ============================================================================
# QCLAW KNOWLEDGE ATOMIZATION PIPELINE
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## Overview

The QCLAW Knowledge Atomization Pipeline transforms raw knowledge sources into
deterministic, traceable, and reusable KnowledgeAtoms, KnowledgeRelations,
KnowledgeConflicts, KnowledgeUnknowns, and canonical-compatible LearningPackets.

This document describes each stage in detail: inputs, processing steps, outputs,
failure modes, recovery procedures, and quality gates.

The pipeline has **10 stages** executed sequentially with checkpoint-based recovery.

```
SOURCE → SECRET SCAN → PARSE → SEGMENT → ATOM EXTRACTION → RELATION EXTRACTION
→ CONFLICT/UNKNOWN DETECTION → QUALITY GATE → PACKET ASSEMBLY → STORAGE
```

---

## Stage 0: Source Discovery & Queue Management

### Purpose
Identify, prioritize, and prepare knowledge sources for digestion.

### Inputs
- File system scan of the coordination workspace
- GitHub issues (Issue #38, #59, #31)
- GitHub pull requests (PR #57, #45, #46)
- Configuration files (ACTIVE-QCLAW-TASK.yaml, AGENTS.md, SOUL.md)
- Agent workspace documents
- Router protocol documents

### Processing Steps

**0.1 Scan for New Sources**
1. Walk the coordination directory tree for architecture documents, schemas, configs
2. Check GitHub issues/PRs for new or modified content
3. For each candidate: check if it already has a KnowledgeSourceManifest entry
4. If new: create pending source manifest with `source_type`, `source_location`, and initial hash
5. If modified (hash differs): create new version entry in the source manifest
6. Set status to `PENDING`

**0.2 Sort and Prioritize Queue**
1. Walk all PENDING sources and resolve their `digest_dependencies`
2. Topological sort: dependencies must be digested before dependents
3. Within the same dependency level, sort by `digest_priority`:
   `CRITICAL > HIGH > MEDIUM > LOW > BACKGROUND`
4. Set status to `QUEUED`
5. Validate that all dependencies have digest status `DIGESTED` or are themselves in the batch

**0.3 Pop Next Batch**
1. Select source(s) from QUEUED where all dependencies are DIGESTED
2. Group compatible formats (multiple small sources may be batched)
3. Set status to `IN_PROGRESS`
4. Generate `digest_run_id` for this batch
5. Log batch creation in `AtomizationDecision`

### Outputs
- Updated `KnowledgeDigestQueue` with batch assignments
- `KnowledgeSourceManifest` entries for new sources
- `AtomizationDecisions` for queue prioritization choices

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Circular dependency | Sources A, B, C form a cycle in digest_dependencies | Break the cycle at the weakest link; document in Decision; set the broken dependency to WAITING_SOURCE |
| Missing source | Source location is unreachable (deleted file, private repo) | Set status to FAILED; document in Decision; remove from dependency tree |
| Queue overflow | Too many sources to process in one session | Split into multiple batches; prioritize CRITICAL+HIGH; defer LOW+BACKGROUND to next run |
| Source hash mismatch | Source changed between queue entry and ingestion | Create new version entry; old entry marked as STALE; new entry processed instead |

### Rollback Strategy
- Rollback: Clear `IN_PROGRESS` status back to `QUEUED`
- Recover: Re-scan and rebuild queue from scratch
- Cost: Low — only queue metadata changes at this stage

---

## Stage 1: Secret Scan

### Purpose
Detect and redact credential, authentication, access, and financial secret values
from source content before any knowledge extraction occurs.

### Inputs
- Raw source content (file contents, API responses, issue/PR bodies)
- `SECRET-SCAN.yaml` pattern definitions
- `SecretScanReceipt` schema

### Processing Steps

**1.1 Pattern-Based Scanning**
1. For each source, apply ALL regex patterns from `SECRET-SCAN.yaml` against the full text
2. Patterns cover:
   - API keys (generic, OpenAI, GitHub, broker)
   - JWT/OAuth tokens
   - Passwords in config files
   - Private keys (PEM, SSH)
   - Connection strings (database, JDBC)
   - Financial auth values (broker keys, payment keys, crypto keys)
   - Webhook secret URLs
3. For each match, classify: `VALUE` (actual secret) vs `METADATA_REFERENCE` (describes where secret lives)

**1.2 Value vs Metadata Classification**
- VALUE: The match contains an actual secret (e.g., `API_KEY=sk-abc123...`)
- METADATA_REFERENCE: The match describes where a secret is stored without the value
  (e.g., "API key is stored in environment variable OPENAI_API_KEY")
- METADATA_REFERENCE entries are NOT redacted — they are knowledge, not secrets

**1.3 Redaction**
1. For each VALUE match:
   - Replace the secret value with the appropriate placeholder (e.g., `[REDACTED:API_KEY]`)
   - Record: position (start, end), secret_type, severity, placeholder used
2. Compute SHA-256 of the redacted content
3. Never log or store the actual secret value

**1.4 Semantic Damage Assessment**
1. Compare atomizable content before/after redaction
2. Classify damage level:
   - `NONE`: No secrets found, or redacted text contained no knowledge
   - `MINIMAL`: Only non-semantic content removed (e.g., API key in code example)
   - `MODERATE`: Some semantic context lost but core knowledge preserved
   - `SIGNIFICANT`: Important semantic information lost
   - `CRITICAL`: Essential knowledge destroyed; source cannot be atomized

**1.5 Generate SecretScanReceipt**
1. Record: scan_timestamp, secrets_found_count, redaction_positions (types only, NEVER values)
2. Record: hash_before_scan, hash_after_redaction
3. Record: semantic_damage_level, semantic_damage_description
4. Store receipt — never expose actual secret values

### Outputs
- Redacted source content (safe for knowledge extraction)
- `SecretScanReceipt` (proof of scanning, no secrets)
- Semantic damage assessment

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Pattern false positive | Redacts non-secret text (e.g., base64 data mistaken for token) | Manual review of redaction positions; refine patterns; re-scan |
| Pattern false negative | Secret not detected by regex patterns | Add new pattern to SECRET-SCAN.yaml; re-scan all sources |
| Critical semantic damage | Redaction destroys essential knowledge | Flag for human review; if truly critical, document what knowledge was lost; source may need manual preprocessing |
| Source is entirely secrets | Every atomizable segment contains secret values | Mark source as SKIPPED_SECRETS; no atoms produced; document loss |

### Rollback Strategy
- Rollback: If false positive detected, revert redactions and re-scan with corrected patterns
- Recover: Re-run Stage 1 with updated SECRET-SCAN.yaml
- Cost: Medium — sources must be re-scanned but no atoms have been created yet

---

## Stage 2: Structure Parse

### Purpose
Parse the redacted source content into a structured `KnowledgeDocument` with
logical `KnowledgeSegments`.

### Inputs
- Redacted source content (from Stage 1)
- Source type classification (FILE, ISSUE, PR, CONVERSATION, etc.)
- SecretScanReceipt

### Processing Steps

**2.1 Format Detection**
1. Detect format from:
   - File extension (`.md`, `.txt`, `.json`, `.yaml`, `.py`, `.js`, etc.)
   - Content heuristics (JSON starts with `{` or `[`, YAML has `---`, etc.)
   - Source type metadata (ISSUE → Markdown body + comments)
2. Select parser based on detected format

**2.2 Format-Specific Parsing**
| Format | Parser Behavior |
|---|---|
| Markdown (`.md`) | Parse headings (H1-H6), paragraphs, code blocks (fenced + indented), bullet/numbered lists, blockquotes, tables, horizontal rules |
| Plain Text (`.txt`) | Segment by double-newline paragraph boundaries |
| JSON (`.json`) | Parse into structured segments preserving key paths; handle nested objects |
| YAML (`.yaml`, `.yml`) | Parse into structured segments; preserve hierarchy through indentation |
| JSONL (`.jsonl`) | Process line-by-line; each line is a separate logical unit |
| Python/JS/Code | Treat as single or few segments; preserve code structure with line numbers |
| Conversation Log | Segment by speaker turns; preserve speaker identity and turn ordering |
| GitHub Issue | Parse issue body as Markdown; each comment as separate segment; preserve comment threading |
| GitHub PR | Parse PR body as Markdown; diff as structured segments; review comments linked to diff lines |

**2.3 Document Assembly**
1. Create `KnowledgeDocument` with:
   - `document_id`: derived from source_id
   - `source_info`: link to KnowledgeSourceManifest
   - `segments`: ordered list of KnowledgeSegments
   - `format`: detected format
2. Each segment gets:
   - `segment_id`: deterministic (SHA-256 of content + position)
   - `segment_type`: HEADING, PARAGRAPH, CODE_BLOCK, LIST_ITEM, TABLE, QUOTE, etc.
   - `raw_text`: original text (after redaction)
   - `position`: ordinal position in document (1-indexed)
   - `parent_heading`: nearest heading that contains this segment
   - `metadata`: format-specific metadata (heading_level, code_language, list_depth, etc.)

**2.4 Parse Validation**
1. Verify all segments are non-empty
2. Verify heading hierarchy is valid (no H3 without H2, etc.)
3. Verify code blocks have matching open/close fences
4. If parsing errors detected: document in AtomizationDecision

### Outputs
- `KnowledgeDocument` with ordered `KnowledgeSegments`
- Parse validation report
- AtomizationDecisions for any parsing anomalies

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Unsupported format | No parser available for detected format | Mark source as SKIPPED_FORMAT; document in Decision; add parser in future version |
| Corrupted content | Parser errors on malformed content | Attempt best-effort parse; document lost content in Decision |
| Encoding issues | Garbled text from wrong encoding detection | Detect encoding (UTF-8, UTF-16, Latin-1, GBK); re-parse with correct encoding |
| Segment explosion | Source produces >10,000 segments | Apply segment merging (adjacent paragraphs of same type); batch processing |

### Rollback Strategy
- Rollback: Re-parse with different encoding or corrected format detection
- Recover: If format is truly unsupported, skip source; if encoding issue, re-fetch source with correct encoding
- Cost: Low — only parsing, no semantic extraction yet

---

## Stage 3: Segmentation

### Purpose
Refine KnowledgeSegments into candidate extraction units. Large segments are split;
small adjacent segments are merged where appropriate.

### Inputs
- `KnowledgeDocument` with `KnowledgeSegments` (from Stage 2)
- Atomization Principles (ATOMIZATION-PRINCIPLES.md)
- Atom Type Taxonomy (ATOM-TYPE-TAXONOMY.yaml)

### Processing Steps

**3.1 Oversized Segment Detection**
1. Check each segment's `raw_text` length against thresholds:
   - > 5000 chars: MUST split
   - > 2000 chars: SHOULD split (quality gate QG-ATOM-002)
   - < 30 chars: MAY merge with adjacent segment
2. For oversized segments: identify natural split points (sentence boundaries, paragraph breaks, list items)

**3.2 Segment Splitting**
1. Split at sentence boundaries (`. `, `! `, `? ` followed by capital letter)
2. Split at paragraph breaks (double newline)
3. Split at list item boundaries (bullet points or numbered items)
4. Preserve cross-segment context: if a split creates a dependent segment, mark the dependency
5. Document all split decisions in `AtomizationDecision`

**3.3 Segment Merging**
1. Identify adjacent segments that are too short to be standalone atoms (< 30 chars)
2. Merge with preceding or following segment based on semantic continuity
3. Never merge across heading boundaries or code block boundaries
4. Never merge list items with different subjects

**3.4 Segment Classification**
1. Classify each segment by potential atom type(s) based on content patterns:
   - Contains "must", "should", "shall" → potential RULE
   - Contains "causes", "leads to" → potential CAUSAL_CLAIM
   - Contains "if", "when", "provided" → potential CONDITION
   - Contains "except", "unless" → potential EXCEPTION
   - Contains "not", "never", "no" → flag for negation preservation
   - Contains dates/times → flag for time_scope extraction
   - Contains step-by-step instructions → potential PROCEDURE/METHOD
2. This classification is preliminary — atom type is finalized in Stage 4

### Outputs
- Refined `KnowledgeSegments` (split and merged as needed)
- Segment classification annotations
- `AtomizationDecisions` for all split/merge operations

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Over-splitting | Single semantic unit split across multiple segments | Merge segments; document merge decision |
| Under-splitting | Multiple independent claims in one segment | Re-split at logical boundaries |
| Cross-boundary damage | Split breaks a code block, quote, or table | Preserve code/quote/table boundaries; split only at semantic boundaries outside these |
| Lost context | Split segment loses its connection to source context | Add context breadcrumb to each segment linking back to parent segment |

### Rollback Strategy
- Rollback: Undo splits/merges; return to original segment boundaries
- Recover: Re-run segmentation with adjusted thresholds
- Cost: Low — only segmentation, no atom creation yet

---

## Stage 4: Atom Extraction

### Purpose
Extract `KnowledgeAtoms` from `KnowledgeSegments` — the core knowledge creation step.

### Inputs
- Refined `KnowledgeSegments` (from Stage 3)
- `ATOM-TYPE-TAXONOMY.yaml` (32 atom types with decision tree)
- `ATOMIZATION-PRINCIPLES.md` (20 principles, anti-patterns)
- `DETERMINISTIC-IDENTITY.md` (ID generation rules)

### Processing Steps

**4.1 Independent Assertion Extraction**
For each KnowledgeSegment, identify:
1. **Subject**: What is this about? (extract from text)
2. **Predicate**: What is claimed about the subject?
3. **Object**: What is the claim's target/value?
4. **Conditions**: Under what circumstances is this true?
5. **Exceptions**: When does this NOT apply?
6. **Negations**: Is this stating that something is NOT true?
7. **Time scope**: When is/was this valid?

Decision rules:
- Each FACT/CLAIM/OBSERVATION should be ONE independently evaluable assertion
- Conditions that are part of the truth value MUST be part of the atom
- Exceptions that limit scope MUST be documented (HAS_EXCEPTION relation)
- Separate but related claims → separate atoms + relations
- If uncertain about split/merge → document in AtomizationDecision

**4.2 Canonical Statement Construction**
For each candidate atom:
1. Build canonical_statement preserving original source wording as much as possible
2. Include conditions as part of the statement where truth depends on them
3. Preserve negations exactly (`not`, `never`, `no` must survive)
4. Preserve scope qualifiers (temporal, spatial, domain)
5. If source text is imprecise or ambiguous → document in Decision
6. Never "improve" or "correct" source text → preserve as-is
7. Verify minimum semantic completeness: can this be understood independently?

**4.3 Atom Type Assignment**
Apply the decision tree from `ATOM-TYPE-TAXONOMY.yaml`:
```
Is this a verifiable statement of fact? → FACT
Is it an unverified assertion? → CLAIM
Is it a proposed explanation? → HYPOTHESIS
Is it a recorded observation? → OBSERVATION
Is it a definition? → DEFINITION
Is it a rule or constraint? → RULE / CONSTRAINT
Is it a process or method? → METHOD / PROCEDURE / SKILL
Is it a decision? → DECISION / ARCHITECTURE_DECISION
Is it an unknown gap? → UNKNOWN
Is it a question? → QUESTION
Is it a failure or counterexample? → FAILURE_CONDITION / COUNTEREXAMPLE / FAILURE_LESSON
Is it a risk? → RISK
Is it user input? → USER_PREFERENCE / USER_CORRECTION
```
Document type selection rationale in `AtomizationDecision`.

**4.4 ID Generation**
For each atom, generate `atom_id` using `DETERMINISTIC-IDENTITY.md` rules:
```
atom_id = "AT-" + SHA256(NFKC(canonical_statement) ∥ NFKC(scope) ∥ NFKC(time_scope.valid_from))[:8]
```

**4.5 Metadata Population**
For each atom, populate:
- `knowledge_status`: `candidate` (default — all atoms start here)
- `authority_level`: `CANDIDATE_ONLY` (default — must be explicitly promoted)
- `gpt_access`: `FULL_SEMANTIC_ACCESS` (default — see STORAGE-TRANSPORT-ACCESS-MATRIX.yaml)
- `transport_visibility`: `PUBLIC_ALLOWED` (default)
- `privacy_class`: based on source type and content (descriptive only)
- `storage_targets`: based on privacy_class defaults (see MATRIX)
- `confidence`: based on source quality and evidence
- `confidence_basis`: MANDATORY — WHY this confidence level
- `sources`: link to KnowledgeSourceManifest entries

**4.6 Anti-Pattern Check**
Verify each atom does not match known anti-patterns:
- ❌ Whole paragraph as one atom (check against segment word count)
- ❌ Sentence fragments as atoms (check for missing subject or predicate)
- ❌ Stripped conditions (check source vs canonical_statement for "if/when")
- ❌ Merged conflicts (check if two opposing claims were "balanced")
- ❌ Summarized content (check if canonical_statement is significantly shorter than source)
- ❌ Opinion-as-fact (check CLAIM/HYPOTHESIS with VERY_HIGH confidence)

### Outputs
- List of candidate `KnowledgeAtoms` with full metadata
- `AtomizationDecisions` for type assignments, splits, merges
- Anti-pattern detection report

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Semantic overreach | Atom claims more than source actually states | Reduce canonical_statement scope; lower confidence; document in Decision |
| Condition loss | Source has "if/when" but atom has no conditions | Extract conditions from source; add to conditions field; quality gate QG-ATOM-003 |
| Negation loss | Source says "not X" but atom says "X" | Preserve negation; quality gate QG-ATOM-005 catches this |
| Subject drift | Atom's subject differs from source's actual subject | Re-extract with correct subject; quality gate QG-ATOM-007 |
| Empty extraction | Segment produces zero valid atoms | Document as DECISION: source segment had no extractable knowledge |
| ID collision | Two different atoms produce same atom_id | Expand ID to 12 chars; document collision in Decision; follow DETERMINISTIC-IDENTITY.md collision policy |

### Rollback Strategy
- Rollback: Return to post-segmentation state; re-extract with corrected rules
- Recover: If systemic issue (wrong extraction strategy), restart from Stage 3
- Cost: High — atoms with IDs exist but may need regeneration

---

## Stage 5: Relation Extraction

### Purpose
Identify and type relationships between extracted atoms, both explicit (stated in
source) and implicit (inferable from semantics).

### Inputs
- List of `KnowledgeAtoms` (from Stage 4)
- `RELATION-TAXONOMY.yaml` (27 relation types, decision flow)
- Original source text for explicit relation detection
- `DETERMINISTIC-IDENTITY.md` (relation ID generation)

### Processing Steps

**5.1 Explicit Relation Detection**
For each pair of atoms from the same source:
1. Check if source text of atom A references atom B (or vice versa)
2. Map source language to relation types:
   - "supports/confirms/proves" → `SUPPORTS`
   - "contradicts/disproves/conflicts" → `CONTRADICTS`
   - "specifically/more precisely/in particular" → `REFINES`
   - "requires/depends on/needs" → `REQUIRES`
   - "causes/leads to/results in" → `CAUSES` (if causal evidence exists)
   - "correlates with/associated with" → `CORRELATES_WITH`
   - "is part of/component of" → `PART_OF`
   - "is an example of" → `INSTANCE_OF`
   - "is a counterexample to" → `HAS_COUNTEREXAMPLE`
   - "supersedes/replaces/updates" → `SUPERSEDES`/`REPLACES`/`UPDATES`
   - "because/the reason is" → `EXPLAINS`
   - "derived from/synthesized from" → `DERIVED_FROM`
   - "fails when/breaks when" → `FAILS_WHEN`
   - "if/when/provided that" → `HAS_CONDITION`
   - "except/unless/but not" → `HAS_EXCEPTION`
3. Prefer most specific type; use `RELATED_TO` only as last resort

**5.2 Implicit Relation Detection**
For pairs of atoms (even across different sources):
1. **Contradiction detection**: same subject, opposite truth value → `CONTRADICTS`
   (trigger conflict creation in Stage 6)
2. **Refinement detection**: one atom's scope is a proper subset of another's → `REFINES`
3. **Prerequisite detection**: one atom's truth logically requires another → `REQUIRES`
4. **Version chain**: same subject, same source, different versions → `SUPERSEDES`
5. **Conceptual overlap**: same subject, different aspects, complementary → `SUPPLEMENTS`
6. **Inverse relation**: for every directional relation A→B, check if B→A inverse applies

Document ALL implicit relations in `AtomizationDecision` (these are less reliable
than explicit relations and carry lower confidence).

**5.3 Relation ID Generation**
For each relation:
```
relation_id = "REL-" + SHA256(source_atom_id ∥ target_atom_id ∥ relation_type)[:8]
```

**5.4 Deduplication**
1. Check if relation already exists (same pair + same type)
2. `A SUPPORTS B` and `B SUPPORTS A` are different relations (direction matters)
3. `A CONTRADICTS B` and `B CONTRADICTS A` are the same (BIDIRECTIONAL)
4. Remove true duplicates; for near-duplicates, keep the explicit one (higher confidence)

### Outputs
- List of `KnowledgeRelations` with deterministic IDs
- `AtomizationDecisions` for implicit relations and type selections
- Relation type distribution statistics

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| False relation | Non-existent relation claimed between atoms | Lower confidence; require source evidence; quality gate QG-REL-002 |
| Missing relation | Real relationship not detected | Expand detection patterns; re-run detection |
| Wrong type | `CAUSES` used for correlation | Quality gate QG-ATOM-008 catches causality overreach |
| Orphan target | Relation references atom not in packet | Quality gate QG-REL-001 catches this; include target atom or remove relation |
| Too generic | `RELATED_TO` used when specific type exists | Quality gate QG-REL-002 warns; reclassify with correct type |

### Rollback Strategy
- Rollback: Remove all implicit relations (keep explicit); re-run implicit detection
- Recover: If systemic misclassification, re-run with corrected relation mapping
- Cost: Medium — relations are metadata; atoms themselves unaffected

---

## Stage 6: Conflict & Unknown Detection

### Purpose
Detect contradictory atom pairs (conflicts) and knowledge gaps (unknowns). Both are
first-class knowledge — conflicts are not errors, and unknowns are not failures.

### Inputs
- List of `KnowledgeAtoms` (from Stage 4)
- List of `KnowledgeRelations` (from Stage 5)
- Source documents (for UNKNOWN extraction)
- `KNOWLEDGE-CONFLICT.schema.json` and `KNOWLEDGE-UNKNOWN.schema.json`

### Processing Steps

**6.1 Conflict Detection — Explicit**
1. For each `CONTRADICTS` relation detected in Stage 5, create a `KnowledgeConflict` entry
2. Classify conflict type:
   - Same subject, opposite truth values → `DIRECT_FACTUAL`
   - Different methods yield different results → `METHODOLOGICAL`
   - Same data, different conclusions → `INTERPRETIVE`
   - Valid at different times → `TEMPORAL`
   - Different applicability domains → `SCOPE`
   - Different definitions → `DEFINITIONAL`
   - Disagreement about cause/effect → `CAUSAL_DIRECTION`
   - Different measured values → `MEASUREMENT`
   - Different predictions → `PREDICTIVE`
   - Different recommended actions → `PRESCRIPTIVE`
   - Conflicting sources of different quality → `SOURCE_QUALITY`
   - Both plausible, evidence insufficient → `UNRESOLVED_EVIDENCE`

**6.2 Conflict Detection — Implicit**
1. Scan all atom pairs for semantic contradiction not yet captured by relations
2. For each conflict: create BOTH a `CONTRADICTS` relation AND a `KnowledgeConflict` entry
3. Set `resolution_status` based on nature:
   - If one atom `SUPERSEDES` the other → `RESOLVED_BY_SUPERSEDES`
   - If both are valid in different scopes → `RESOLVED_BY_SCOPE_CLARIFICATION`
   - If one methodology is proven flawed → `RESOLVED_BY_METHODOLOGY_CORRECTION`
   - If neither can be disproven → `UNRESOLVED`
   - If both may be true simultaneously in some interpretations → `ACKNOWLEDGED_PARADOX`
4. BOTH atoms MUST be preserved; NEVER delete the "wrong" one

**6.3 Conflict ID Generation**
```
conflict_id = "CNF-" + SHA256(sorted(atom_id_a, atom_id_b) ∥ conflict_type)[:8]
```

**6.4 Unknown Extraction**
For each source document and segment:
1. Identify explicit "unknown" markers: "unknown", "TBD", "TODO", "needs investigation", "unclear", "?"
2. Identify implicit unknowns: claims qualified by "might", "possibly", "speculated", "not yet verified"
3. For each unknown:
   - Extract the precise question
   - Document what IS known (bounding context)
   - Define the verification path (how to resolve)
   - Assess impact if unresolved (why it matters)
   - Classify unknown type: `MISSING_DATA`, `MISSING_METHOD`, etc.

**6.5 Unknown Deduplication**
1. Same `question` across different sources produces same `unknown_id`
2. Merge duplicate unknowns: keep the most detailed `what_is_known` and `verification_path`
3. Track all `raised_by` sources in a combined entry

**6.6 Cross-Reference**
1. Link unknowns to related atoms via `related_atom_ids`
2. Check if any existing atom resolves a previously documented unknown → mark as `RESOLVED`
3. Make `RAISES_UNKNOWN` relations between atoms and the unknowns they introduce

### Outputs
- List of `KnowledgeConflicts` with deterministic IDs
- List of `KnowledgeUnknowns` with deterministic IDs
- Updated `KnowledgeAtoms` with `RAISES_UNKNOWN`/`RESOLVES_UNKNOWN` relations
- Conflict and unknown statistics

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Conflict one-sided | Only one atom of a conflict pair is present | Quality gate QG-CNF-001 FAIL; include both atoms |
| Conflict resolved without evidence | `resolution_status` is `RESOLVED_*` but `resolution_evidence` is empty | Quality gate QG-CNF-002 WARN; provide evidence or mark UNRESOLVED |
| Unknown deleted | Source's unknowns not carried forward | Quality gate QG-UNK-001 FAIL; restore unknowns |
| Unknown fabricated | "Unknown" created for something actually known | Review and delete; document in Decision |
| Unknown no path | Unknown lacks `verification_path` | Quality gate QG-UNK-002 WARN; add verification path |

### Rollback Strategy
- Rollback: Regenerate conflicts and unknowns from atom list
- Recover: If conflict resolution was premature, revert to UNRESOLVED status
- Cost: Low — conflicts and unknowns derive from atoms; atoms unaffected

---

## Stage 7: Quality Gate

### Purpose
Apply all quality checks defined in `QUALITY-GATES.yaml` against the produced atoms,
relations, conflicts, and unknowns. Block, warn, or accept based on gate severity.

### Inputs
- Complete set of `KnowledgeAtoms`, `KnowledgeRelations`, `KnowledgeConflicts`, `KnowledgeUnknowns`
- `QUALITY-GATES.yaml` (28 gate definitions)
- `QUALITY-GATE-REPORT.schema.json`
- `SecretScanReceipt` (for security gates)

### Processing Steps

**7.1 Run Automatic Gates**
For each gate where `auto_detect: true`:
1. Execute the detection method (regex, length check, cross-reference, etc.)
2. Record result: `PASS`, `WARN`, or `FAIL`
3. For `WARN`: document findings but continue processing
4. For `FAIL`: block unless explicitly overridden with documented justification
5. Store individual gate results

**7.2 Run Manual Gates**
For gates where `auto_detect: false`:
1. Apply heuristic or LLM-based analysis
2. Examples:
   - `QG-ATOM-007` (subject_mismatch): LLM compares atom subject vs source subject
   - `QG-REL-002` (relation_type_too_generic): LLM checks description for specific type signals
   - `QG-SEC-003` (post_redaction_semantic_damage): LLM compares redacted vs unredacted semantics
   - `QG-SEM-001` (internal_contradiction): LLM checks semantic consistency across atoms
3. Record result with reasoning
4. Document in `AtomizationDecision`

**7.3 Gate Categories and Their Order**

Apply in this order (blocking gates first):

1. **Security Gates** (QG-SEC-*) — Blocking: secrets in output
2. **Determinism Gates** (QG-DET-*) — Blocking: non-deterministic IDs
3. **Field Pollution Gates** (QG-FLD-*) — Blocking: privacy/storage conflicts
4. **Source Integrity Gates** (QG-SRC-*) — Blocking: broken source chains
5. **Conflict Preservation Gates** (QG-CNF-*) — Blocking: one-sided conflicts
6. **Unknown Preservation Gates** (QG-UNK-*) — Blocking: deleted unknowns
7. **Atom Integrity Gates** (QG-ATOM-*) — Warning: content quality issues
8. **Relation Integrity Gates** (QG-REL-*) — Warning: relation quality issues
9. **Semantic Consistency Gates** (QG-SEM-*) — Warning: internal contradictions
10. **Compatibility Gates** (QG-COM-*) — Blocking: schema incompatibility
11. **Completeness Gates** (QG-CMP-*) — Warning: missing items

**7.4 Overall Assessment**
1. Count results: PASS, WARN, FAIL, SKIPPED
2. Decision:
   - Any FAIL with severity `FAIL` (blocking) → `REJECT`
   - No FAIL, some WARN → `ACCEPT_WITH_WARNINGS`
   - All PASS → `ACCEPT`
   - All SKIPPED → `INCONCLUSIVE` (no gates applicable)
3. Generate `QualityGateReport`

**7.5 Remediation**
If `REJECT`:
1. Identify all FAIL gates
2. Apply remediation from gate definition
3. Re-run affected stages
4. Re-run quality gates until all blocking gates pass

If `ACCEPT_WITH_WARNINGS`:
1. Document all warnings in `QualityGateReport`
2. Flag for attention in `AI_HANDOFF`
3. Continue to next stage (warnings don't block)

### Outputs
- `QualityGateReport` with per-gate results
- Updated atoms/relations/conflicts (if remediation applied)
- `AtomizationDecisions` for any gate overrides

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Gate false positive | Correct content flagged as failure | Override gate with documented justification; refine gate pattern |
| Gate false negative | Problem content passes quality check | Add new gate or refine existing pattern |
| Circular remediation | Fixing one gate failure causes another | Resolve in dependency order; document the circularity |
| All gates skipped | No gates applicable to this content | Verify gate conditions; add new gates for this content type |

### Rollback Strategy
- Rollback: Accept previous gate results; investigate false positive
- Recover: Fix the underlying issue (wrong atom type, missing field, etc.) and re-run specific gates
- Cost: Variable — depends on what needs fixing; atoms may need re-extraction

---

## Stage 8: Learning Packet Assembly

### Purpose
Assemble all artifacts (atoms, relations, conflicts, unknowns, skills, structures,
source manifests, secret scan receipts, decisions, quality reports) into a
canonical-compatible `LearningPacket`.

### Inputs
- All `KnowledgeAtoms` (from Stage 4, validated in Stage 7)
- All `KnowledgeRelations` (from Stage 5)
- All `KnowledgeConflicts` (from Stage 6)
- All `KnowledgeUnknowns` (from Stage 6)
- `KnowledgeSourceManifest` entries (from Stage 0)
- `SecretScanReceipts` (from Stage 1)
- `AtomizationDecisions` (from all stages)
- `QualityGateReport` (from Stage 7)
- `LEARNING-PACKET.schema.json`

### Processing Steps

**8.1 Packet Envelope**
1. Generate `packet_id` from `digest_run_id`
2. Fill metadata:
   - `version`, `label`, `parent_program`, `task_id`
   - `created_at`, `transport_visibility`, `gpt_access`
   - Set from MOST RESTRICTIVE atom in the packet
3. Link to `TASK-EXECUTION-PLAN.yaml` checkpoint targets

**8.2 Insert Artifacts (Deterministic Order)**
1. Sort atoms by `atom_id` (alphabetical)
2. Sort relations by `relation_id`
3. Sort conflicts by `conflict_id`
4. Sort unknowns by `unknown_id`
5. Include source manifests sorted by `source_id`
6. Include secret scan receipts sorted by timestamp
7. Include atomization decisions sorted by `decision_id`
8. Include quality gate report
9. Include statistics block

**8.3 Statistics Generation**
1. Count atoms by `atom_type`
2. Count relations by `relation_type`
3. Distribution of `confidence` levels
4. Distribution of `authority_level`
5. Quality gate summary (PASS/WARN/FAIL counts)
6. Source coverage: which sources were fully/partially digested

**8.4 Deterministic Packet Hash**
1. Build canonical content (see DETERMINISTIC-IDENTITY.md):
   - Include ONLY hash-input fields (exclude `created_at`, `updated_at`, etc.)
   - Sort all objects by deterministic ID
   - Sort all keys alphabetically
2. Serialize as compact JSON
3. Compute SHA-256
4. Set `packet_hash`
5. Verify: `SHA256(canonical_content) == packet.packet_hash`

**8.5 Schema Validation**
1. Validate complete packet against `LEARNING-PACKET.schema.json`
2. Validate each atom against `KNOWLEDGE-ATOM.schema.json`
3. Validate each relation against `KNOWLEDGE-RELATION.schema.json`
4. Validate each conflict against `KNOWLEDGE-CONFLICT.schema.json`
5. Validate each unknown against `KNOWLEDGE-UNKNOWN.schema.json`
6. Any schema violation → Quality gate QG-COM-001 FAIL

### Outputs
- Complete `LearningPacket` with deterministic hash
- Schema validation results
- Statistics block

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Schema violation | Packet fails JSON Schema validation | Fix violating fields; re-validate |
| Hash mismatch | SHA256(canonical_content) != packet_hash | Re-check canonical serialization; regenerate hash |
| Empty packet | Zero atoms despite digesting sources | Quality gate QG-CMP-002 WARN; investigate extraction failures |
| Oversized packet | Packet exceeds practical size limits | Split into multiple packets; adjust batch sizes |

### Rollback Strategy
- Rollback: Re-assemble packet with corrected content
- Recover: Fix individual atom/relation issues and re-assemble
- Cost: Low — assembly is deterministic composition

---

## Stage 9: Storage & Handoff

### Purpose
Write the LearningPacket, update all tracking files, generate handoff document,
and prepare for next agent or next run.

### Inputs
- Complete `LearningPacket` (from Stage 8)
- `KnowledgeDigestQueue` (from Stage 0)
- `STORAGE-TRANSPORT-ACCESS-MATRIX.yaml`
- `PROGRESS-CHECKPOINT.yaml`

### Processing Steps

**9.1 Write LearningPacket**
1. Per `storage_targets` in the packet:
   - `PUBLIC_GITHUB`: write to `learning-packets/digest-XXX-{label}.json`
   - `LOCAL_KNOWLEDGE_ARCHITECTURE`: write to local architecture directory
   - `NONE`: skip (for hard-secret atoms only)
2. Use deterministic filename based on `digest_run_id`
3. Write as pretty-printed JSON (2-space indent) for human readability
4. Verify file written correctly (read back and validate)

**9.2 Write AtomizationRunManifest**
1. Create manifest containing:
   - `digest_run_id`, `timestamp`, `duration`
   - Sources processed (with status: `DIGESTED`, `PARTIALLY_DIGESTED`, or `FAILED`)
   - Atom/relation/conflict/unknown counts
   - Quality gate results summary
   - Errors and warnings
   - Key decisions made
2. Write as `learning-packets/digest-XXX-manifest.yaml`

**9.3 Update KnowledgeDigestQueue**
1. For each digested source:
   - Set status to `DIGESTED` (or `PARTIALLY_DIGESTED` if some segments skipped)
   - Record `last_digest_run_id`
   - Record `atom_count_produced`, `relation_count_produced`
2. For failed sources:
   - Set status to `FAILED`
   - Record `failure_reason`
3. For sources with remaining content:
   - Set status to `PARTIALLY_DIGESTED`
   - Create follow-up entry for remaining segments

**9.4 Update PROGRESS-CHECKPOINT.yaml**
1. Increment `overall_percent` based on deliverables completed
2. Update `last_updated` timestamp
3. Add completed deliverables to `deliverables_produced`
4. Update `work_package_status`
5. Update `total_bytes` and `total_files`

**9.5 Generate AI_HANDOFF.yaml**
1. Summarize what was produced (atom/relation/conflict/unknown counts)
2. List remaining queue items
3. List known UNKNOWNs carried forward
4. List quality warnings needing attention
5. List decisions awaiting review
6. Provide verification commands
7. Specify next steps for the receiving agent

### Outputs
- Written `LearningPacket` file(s)
- Written `AtomizationRunManifest`
- Updated `KnowledgeDigestQueue`
- Updated `PROGRESS-CHECKPOINT.yaml`
- `AI_HANDOFF.yaml`

### Failure Modes
| Failure | Symptoms | Recovery |
|---|---|---|
| Write permission error | Cannot write to storage target | Retry with elevated permissions; fall back to LOCAL_KNOWLEDGE_ARCHITECTURE only |
| Disk full | Write fails with space error | Clean up old packets; compress; alert user |
| Queue update conflict | Another process modified queue during run | Re-read queue; merge changes; re-write |
| Incomplete handoff | Handoff missing critical sections | Re-generate from packet metadata and quality report |

### Rollback Strategy
- Rollback: Revert queue status changes; re-write corrupted files
- Recover: If storage fails for one target, use alternate; document in handoff
- Cost: Low — all content already validated; only I/O operations

---

## Pipeline-Wide Concerns

### Checkpoint-Based Recovery

The pipeline saves state at the end of each stage:
```
Stage 0 → Save: source manifests + queue state
Stage 1 → Save: redacted sources + SecretScanReceipts
Stage 2 → Save: parsed KnowledgeDocuments
Stage 3 → Save: refined KnowledgeSegments
Stage 4 → Save: candidate KnowledgeAtoms
Stage 5 → Save: KnowledgeAtoms + KnowledgeRelations
Stage 6 → Save: all entities + conflicts + unknowns
Stage 7 → Save: QualityGateReport
Stage 8 → Save: assembled LearningPacket
Stage 9 → Save: written files + updated manifests
```

**Resume procedure:**
1. Load most recent valid checkpoint
2. Validate checkpoint integrity (hash check)
3. Resume from next stage
4. If checkpoint is invalid (hash mismatch): restart from Stage 0 for affected sources

### Determinism Guarantee

**Contract:**
Same source content + same configuration (quality gate thresholds, pipeline version)
→ identical `packet_hash`

**Excluded from determinism:**
- `created_at`, `updated_at` — wall-clock timestamps
- `run_duration_ms` — varies by hardware
- `host_name` — varies by execution environment
- `access_timestamp` — varies by run

**Included in determinism:**
- All semantic content (canonical_statements, relation types, etc.)
- Deterministic ordering (all arrays sorted by ID)
- Hash scheme version
- Pipeline version

### Pipeline Version

```
pipeline_version: "1.0.0"
hash_scheme_version: "1.0.0"
```

Version changes are recorded in `pipeline_version` metadata of every LearningPacket,
enabling consumers to handle format evolution.

### Monitoring & Observability

Each stage emits:
- **Stage start/end timestamps** → duration tracking
- **Input/output counts** → throughput monitoring (atoms/second)
- **Warning/error counts** → quality trending
- **Decision log entries** → audit trail

These are aggregated into the `AtomizationRunManifest` and `QualityGateReport`.

---

## Appendix A: Full Pipeline Configuration Reference

See `PIPELINE.yaml` for the machine-readable pipeline definition including all
stage definitions, step details, error handling configurations, and recovery
procedures in YAML format. This Markdown document is the human-readable companion
to that file.

## Appendix B: Stage Dependency Graph

```
Stage 0 (Source Discovery)
  └─→ Stage 1 (Secret Scan)
        └─→ Stage 2 (Structure Parse)
              └─→ Stage 3 (Segmentation)
                    └─→ Stage 4 (Atom Extraction) ← uses Stage 3 output
                          ├─→ Stage 5 (Relation Extraction) ← uses Stage 4 output
                          └─→ Stage 6 (Conflict/Unknown Detection) ← uses Stage 4+5 output
                                └─→ Stage 7 (Quality Gate) ← uses all previous output
                                      └─→ Stage 8 (Packet Assembly) ← uses all previous output
                                            └─→ Stage 9 (Storage & Handoff)
```

## Appendix C: Stage Time Estimates

| Stage | Estimated Time (per source) | Bottleneck |
|---|---|---|
| 0: Source Discovery | <1s | I/O (file/network reads) |
| 1: Secret Scan | 1-5s | Regex matching on full text |
| 2: Structure Parse | 1-10s | Format complexity |
| 3: Segmentation | 1-5s | Segment count |
| 4: Atom Extraction | 30-120s | LLM-based semantic extraction |
| 5: Relation Extraction | 10-60s | O(n²) atom pair comparison |
| 6: Conflict/Unknown Detection | 10-30s | O(n²) comparison + LLM analysis |
| 7: Quality Gate | 5-30s | Gate count × atom count |
| 8: Packet Assembly | <5s | Serialization + hashing |
| 9: Storage & Handoff | <5s | I/O (file writes) |
| **TOTAL (estimated)** | **2-5 minutes per source** | Stage 4 (Atom Extraction) |
