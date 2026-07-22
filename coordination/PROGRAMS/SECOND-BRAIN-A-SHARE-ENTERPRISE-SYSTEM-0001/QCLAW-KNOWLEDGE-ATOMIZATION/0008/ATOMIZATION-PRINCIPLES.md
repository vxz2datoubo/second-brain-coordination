# ============================================================================
# ATOMIZATION PRINCIPLES
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## First Principles

### 1. Minimum Complete Semantic Unit
Every atom must be the smallest unit that is still semantically complete — it can be
understood, evaluated, and used independently without losing its truth conditions.

❌ **Too long:** "The system supports Markdown, TXT, JSON, JSONL, and YAML formats for
knowledge ingestion, each with its own parser and validation rules, and additionally
supports conversation transcripts through a conversational parser."
→ This merges format support with parser architecture.

✅ **Atom 1:** "The system supports Markdown, TXT, JSON, JSONL, and YAML formats for
knowledge source ingestion."
✅ **Atom 2:** "Each supported format has a dedicated parser with format-specific
validation rules."
✅ **Atom 3:** "Conversation transcripts are supported through a conversational parser
that is separate from the document format parsers."

❌ **Too short:** "Markdown is supported." → Loses object (supported for what? by what?)

### 2. Preserve Full Semantic Content
The canonical_statement must carry the complete semantic payload. Do not summarize.
Do not simplify. Do not lose nuance. The full_semantic_content field can carry
additional context, but the canonical_statement must stand alone.

### 3. Conditions Are Part of the Atom
Conditions are not metadata — they are part of the knowledge itself. An atom that
says "X causes Y" without "when Z holds" is a different atom than one with the
condition. Conditions must be explicit.

### 4. Exceptions Are Knowledge, Not Noise
If a source says "except in case E," that exception is valuable knowledge. Removing it
creates a false assertion. The HAS_EXCEPTION relation must link to the exception atom.

### 5. Failure Conditions Are Essential
Knowing when something fails is often more valuable than knowing when it works.
FAILURE_CONDITION and COUNTEREXAMPLE atom types exist for this reason.

### 6. Negations Must Be Preserved
"X does NOT cause Y" is fundamentally different from "X causes Y." The negation is
part of the semantic content. If the source says "not/never/no," the atom must
carry that negation.

### 7. Conflicts Are Not Errors
Two atoms that contradict each other are BOTH valid knowledge. The conflict itself
is knowledge. CONFLICT_NOT_RETURNED is a critical failure in the adversarial
evaluation framework.

### 8. UNKNOWN Is Knowledge
Admitting what we don't know is more honest than pretending to know. UNKNOWN atoms
document gaps and their verification paths. They must not be deleted or replaced
with fabricated answers.

### 9. Source Lineage Is Not Optional
Every atom must trace back to its source. If the source changes, the atom must be
updated or superseded. Source lineage enables verification, correction, and
revocation.

### 10. Version Chains Are Mandatory
When knowledge is updated, the old atom is superseded (not deleted). The version
chain (supersedes/superseded_by) preserves history. This enables historical queries
and audit trails.

### 11. Confidence Must Have Basis
Never assign confidence without stating WHY. The confidence_basis field must
explain the evidence, reasoning, or authority behind the confidence level.

### 12. Opinions Are Not Facts
A CLAIM or HYPOTHESIS must not be atom-typed as FACT. If the source presents
an opinion, the atom_type must reflect that (CLAIM, HYPOTHESIS, OBSERVATION).
The confidence and confidence_basis must reflect the evidence quality.

### 13. Correlation Is Not Causation
"CORRELATES_WITH" and "CAUSES" are different relation types. Do not upgrade
correlation to causation without explicit causal evidence from the source.

### 14. Source Authority Is Not Atom Authority
Even if a source is authoritative, the atom's authority_level starts at
CANDIDATE_ONLY. Authority promotion requires explicit review, not automatic
inheritance from source prestige.

### 15. Candidate Does Not Mean Inaccessible
`authority_level: CANDIDATE_ONLY` means the atom has not been reviewed/approved as
authoritative. It does NOT mean GPT cannot access it. `gpt_access:
FULL_SEMANTIC_ACCESS` is the default for all authorized candidate atoms.

### 16. Privacy Class Does Not Control Storage
`privacy_class` describes the knowledge's origin and nature. It does NOT
automatically block public storage. Storage decisions are in `storage_targets`.
Transport decisions are in `transport_visibility`. These fields are independent.

### 17. Secret Values Are the Only Hard Boundary
API keys, tokens, passwords, private keys, and financial authentication secrets
are the ONLY content permanently denied from ALL outputs. Regular knowledge —
even private, personal, or internal knowledge — may be stored publicly if
user-authorized.

### 18. Mixed Documents: Redact, Don't Discard
If a document contains both knowledge and secret values, redact only the secret
values and continue digesting the knowledge. Do not discard the entire document.

### 19. Relations Survive Mapping
Use the most specific relation type available. If no existing type captures
the relationship, use RELATED_TO and document the original relationship in the
relation's description field. Never downgrade a specific relationship to
RELATED_TO just for convenience.

### 20. Deterministic Reproducibility
Same source + same configuration → same atoms, same IDs, same packet hash.
This is non-negotiable. The rebuild must produce byte-for-byte identical output.

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Correct Approach |
|---|---|---|
| Whole paragraph as one atom | Loses granularity, mixes topics | Decompose into minimum complete units |
| Sentence fragments as atoms | Loses context, subject, conditions | Keep subject-predicate-object intact |
| Stripping conditions for brevity | Creates false unconditional claims | Include conditions in canonical_statement |
| Merging conflicting claims into one "balanced" atom | Destroys the conflict, which is knowledge | Create two atoms + conflict relation |
| Deleting UNKNOWN entries | Pretends knowledge is complete | Preserve UNKNOWN atoms |
| Summarizing instead of preserving | Loses semantic precision | Keep original semantic content |
| Auto-upgrading correlation to causation | Creates false causal claims | Use CORRELATES_WITH until causation is proven |
| Treating candidate as hidden | Blocks GPT from accessing knowledge | gpt_access: FULL_SEMANTIC_ACCESS for candidates |
| privacy_class blocking public storage | Misuses privacy field as access control | Use storage_targets for storage decisions |
| Discarding documents with secrets | Loses valid knowledge | Redact secrets, keep knowledge |

## Atom Quality Checklist

Before finalizing any atom, verify:

- [ ] Can this atom be understood independently?
- [ ] Does it carry all its conditions and exceptions?
- [ ] Are negations preserved exactly as in source?
- [ ] Is the time scope explicit?
- [ ] Is the subject clearly identified?
- [ ] Is the atom_type accurate (FACT vs CLAIM vs HYPOTHESIS)?
- [ ] Is confidence justified by confidence_basis?
- [ ] Are source_id, source_location, and source_hash present?
- [ ] Is the canonical_statement semantically complete?
- [ ] Would GPT correctly answer a question using only this atom?
- [ ] Are there any conflicting atoms that need conflict relations?
- [ ] Are there any UNKNOWN gaps that need documentation?
