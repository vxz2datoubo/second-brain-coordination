# Why Decision Skills Were Missed

## Finding

The repository has many decision-science terms, schemas and workflow fragments,
but it lacks a deterministic bridge from a blueprint term to an owned runtime,
tests and maturity evidence. The gap is structural rather than a shortage of
indicator names.

## Root Causes

1. **Breadth-first blueprints:** a named method was often treated as coverage
   even when no Skill ID, input/output contract or executable test existed.
2. **Coarse module buckets:** portfolio, risk, execution and validation headings
   hid distinct decisions such as framing, belief updating and experiment-family
   auditing.
3. **No enforced maturity transition:** `mentioned`, `mapped`, `contracted`,
   `implemented` and `validated` were not machine-distinct states.
4. **No lifecycle coverage check:** no deterministic scan proved that FRAME
   through EVOLVE had owners and non-overlapping contracts.
5. **No provenance compiler:** research terms were not required to map to source,
   applicability, A-share limits, Issue, owner, test and stop condition.
6. **Data-first sequencing debt:** building the data and memory foundation first
   was defensible, but decision contracts remained implicit.
7. **Distributed ownership:** no single gap-governance owner detected orphan and
   duplicate capabilities across agents.
8. **Catalogue inflation:** legacy catalogues mix executable skills with adapters,
   stores and concepts, causing documentation to be mistaken for runtime.

## Evidence

- `PUBLIC-REPOSITORY-SKILL-REALITY-MATRIX.yaml` records PR and repository states.
- `LOCAL-SKILL-REALITY-MATRIX.yaml` records accessible local code and skill facts.
- `ORPHAN-GHOST-DUPLICATE-FINDINGS.yaml` records machine-oriented gap findings.
- `DUPLICATE-OR-ORPHAN-CAPABILITY-FINDINGS.md` explains the most material cases.

## Corrective Control

The D1 Gap Compiler must make every material blueprint term resolve to exactly
one of `EXISTING_SUBCAPABILITY`, `CANDIDATE_SKILL`, `REFERENCE_ONLY`, `REJECTED`
or `UNKNOWN`. Maturity must be evidence-derived and sequential. This D0 report
does not implement that compiler.

