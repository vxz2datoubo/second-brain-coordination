# E41 — Atomic Knowledge Digestion & Learning System

## Route
- **Epoch**: 41
- **Task ID**: `QCLAW-KNOWLEDGE-DIGESTION-ATOMIC-LEARNING-SYSTEM-TAXONOMY-EVIDENCE-CONTRADICTION-SKILL-PROMOTION-AND-EVALUATION-CORPUS-0022-E41`
- **Mode**: project_plan
- **Branch**: `qclaw/knowledge-digestion-atomic-learning-system-0022-e41`
- **Base**: `main` at `8c1a352900`
- **Frozen predecessor**: E40 Issue #164 / PR #165 `e58b39fc`
- **Parallel active**: Codex E54 Issue #170 (separate repo, no E41 overlap edits)

## Architecture

E41 is a **semantic, methodological and evaluation-focused layer**. It does not re-implement byte parsing, format ownership, mutation infrastructure or Provider recertification (E54 domain). It builds the Second Brain's upper knowledge-digestion and learning loop on top of public-safe synthetic inputs.

### Work Packages

| Q | Name | Scope |
|---|------|-------|
| Q0 | Plan & Boundary | Verify + branch + plan-only commit + Draft PR + overlap-exclusion manifest |
| Q1 | Knowledge Atom Taxonomy | 12 atomic types + 6 evidence-layer distinctions |
| Q2 | Digestion Pipeline & Traceability | Extraction → interpretation → normalization → linking |
| Q3 | Contradiction, Dedup, Version & Master Record | Merge-duplicate-with-provenance, conflict classification, version governance |
| Q4 | User Cognition Mapping | Known/unknown layering, memory routing, inference confidence bands |
| Q5 | Skill Promotion & Failure Conditions | Candidate → experimental → formal lifecycle |
| Q6 | Synthetic Corpus & Adversarial Evaluation | Deterministic public-safe corpus with ground-truth |
| Q7 | Evaluator Tests, Mutations & Provider Evidence | E41-only evaluator, copied-source mutations, 6-matrix CI |
| Q8 | Report & Handoff | Full heads/trees/files/commands/artifacts report |

### Hard Boundaries
- No modification of QCLAW E40 or Codex E52/E53/E54 branches/files
- No merge, direct main write, rebase, force-push, history rewrite
- No model/provider/config/privacy access
- No credentials, accounts, orders or trading
- Synthetic/public-safe fixtures only

### Provider Contract
- Workflow: `.github/workflows/qclaw-e41-knowledge-digestion-evaluation.yml`
- Python 3.11 + 3.13, seeds 0/1/777, 6 matrix jobs
- Canonical summary per job + byte-exact compare
- Run while Draft; exact event head assertion

### Completion
- Signal: `QCLAW_E41_ATOMIC_KNOWLEDGE_DIGESTION_LEARNING_EVALUATION_READY_FOR_GPT_REVIEW`
- After completion: `STOP_AND_REQUEST_GPT_SECOND_PASS`
