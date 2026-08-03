# Batch 001 — First Real Public-Safe Knowledge Digest Queue

## Source: superbrain-knowledge / Phase-3 canonical contracts

### 1. Knowledge Atomization Principles

Knowledge atomization is the process of decomposing source material into its
minimum complete semantic units while preserving all contextual richness. A
minimum complete semantic unit (MCSU) is the smallest self-contained fragment
that retains truth-functional meaning when read in isolation.

The pipeline must satisfy these invariant properties:
- **Losslessness**: no semantic content from source is discarded
- **Determinism**: same input always produces same atom IDs and packet hashes
- **Traceability**: every atom references its source location
- **Revisability**: atoms support versioning and supersession

### 2. Conditions and Boundaries

If and only if a claim is qualified by a condition (e.g., "when the market is
open", "assuming no transaction costs"), that condition must be preserved as
a separate atom linked by a "precondition_for" relation to the claim atom.

Precondition: the source document must be in a supported format (Markdown,
plain text, JSON, YAML, or JSONL). Binary formats require external conversion.

The pipeline shall not:
- Create a second canonical memory, fusion, or retrieval runtime
- Upgrade candidate atoms to accepted without external review
- Include secret values (API keys, tokens, passwords) in any output
- Fabricate atom count, relation count, or confidence without actual processing

### 3. Semantic Taxonomy

Each atom is classified into exactly one content type:
1. **statement_fact** — verifiable factual assertion
2. **statement_claim** — an assertion that may be debated
3. **statement_opinion** — subjective expression
4. **condition_precondition** — what must be true first
5. **condition_trigger** — what triggers an action
6. **condition_stop** — what terminates an action
7. **exception_explicit** — stated exception
8. **exception_implicit** — implicit boundary
9. **negation** — explicit negative form
10. **failure_condition** — what causes failure
11. **counterexample** — example that disproves a claim
12. **temporal_scope** — when something is valid
13. **temporal_assertion** — time-bounded claim
14. **method** — procedural knowledge
15. **decision_chain** — structured decision logic
16. **skill** — reusable capability pattern
17. **definition** — term definition
18. **constraint** — boundary or limitation
19. **metric** — measurement specification
20. **source_meta** — metadata about sources
21. **evidence_chain** — chain of evidence

### 4. Unknown Handling

Unknowns are first-class citizens. When a source explicitly states that
something is unknown, uncertain, or an open question, that must be preserved
as an UNKNOWN annotation linked to the relevant atom.

The exact mechanism of knowledge consolidation in large language models is
unknown and remains an active area of research.

Open question: what is the optimal balance between atom granularity and
retrieval efficiency in a real-world knowledge system?

### 5. Conflict and Counterevidence

Conflicts and counterevidence must be explicitly preserved, not silently
merged. If two sources disagree on a claim, both atoms must be retained
with a "conflicts" relation between them.

Example: Source A claims "factor X predicts returns Y," while Source B shows
"factor X has no predictive power for returns Y after controlling for Z."
Both claims must be preserved with the conflict relation intact.

### 6. Supersession and Versioning

Knowledge evolves. When a new finding supersedes an old one:
- The old atom's status changes to "superseded"
- A "supersedes" relation links new → old
- The version chain records all predecessors
- The new atom's version_info includes the previous atom ID and change reason

### 7. Redaction Protocol

Documents that contain both knowledge and secret values must be processed
with precise redaction, not wholesale rejection:
1. Identify secret patterns (API keys, tokens, passwords, private keys)
2. Replace with [REDACTED:secret_type] marker
3. Preserve all surrounding knowledge content
4. Record redaction in the parse_report
5. Verify zero secrets in final output via adversarial scan

### 8. Real-World Test Case: PEOS Cognitive Calibration

From the PEOS research corpus, a key finding:

"Calibration is the alignment between subjective probability estimates and
observed frequencies. Most humans exhibit overconfidence bias: their 90%
confidence intervals contain the true value only 40-60% of the time.

However, structured calibration training (e.g., the SPIES method — Subjective
Probability Interval EStimation) improves calibration significantly. After
training, participants' 90% intervals typically contain 80-85% of true values.

Open question: whether AI-assisted calibration feedback provides durable
improvement or only temporary correction remains unresolved.

Counterexample: domain experts in some fields (meteorologists, bridge players)
show near-perfect calibration without formal training, suggesting that
frequent, unambiguous, immediate feedback is the key mechanism."

### 9. Real-World Test Case: Kelly Criterion Fundamentals

From the Kelly/Thorp research corpus:

"The Kelly Criterion (Kelly 1956) specifies the optimal fraction f* of capital
to allocate to a favorable bet with probability p of winning and odds b:

f* = (p(b+1) - 1) / b

Condition: this formula applies only when the bet is repeated many times and
the goal is to maximize the logarithm of wealth (maximize geometric mean).

Exception: when b = p/(1-p), the optimal bet is zero, as the edge disappears.

Failure condition: full Kelly betting (f = f*) produces extreme volatility
and significant drawdown probability. Half-Kelly (f = f*/2) is commonly used
in practice to reduce volatility at the cost of lower expected growth rate.

Negation: the Kelly Criterion does NOT maximize arithmetic mean return, does
NOT guarantee profit, and does NOT apply to one-shot decisions.

Unknown: the exact optimal fraction for non-stationary probability
distributions (where p varies over time) is not known in closed form."

### 10. Cross-Reference: Agent Architecture Constraints

The QCLAW agent must operate within these hard boundaries:
- No second canonical memory, database, fusion, retrieval, QueryPlan, or
  ContextBundle runtime beyond the one in Phase-3 integrated offline memory
- No authentication, access, payment, banking, broker, or trade secret values
- No direct main write, merge, force push, rebase, or reset
- No account, order, trade, or production activation

These constraints are DESIGN_NOT_ERROR and represent the intended architecture.
