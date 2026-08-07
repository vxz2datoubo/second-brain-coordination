# QCLAW E46 PROJECT PLAN

## Task
- **Issue**: #202
- **Epoch**: 46
- **Task ID**: QCLAW-E45-POST-AUDIT-TRUTHFUL-CAPABILITY-USER-ORIGIN-RECEIPT-MUTATION-CI-AND-DESCENDANT-CLOSURE-0027-E46
- **Branch**: `qclaw/e45-post-audit-truthful-semantic-evidence-0027-e46`
- **Checkpoint signal**: `QCLAW_E46_PRE_E59_TRUTHFUL_SEMANTIC_MUTATION_PROVIDER_REPAIR_READY_FOR_GPT_REVIEW`

## Source
- E45 PR #195 frozen at `9e3649b0f6c8d76eaab8c44ee44b9937f0c209a7`
- E45 evaluated: BOTH Provider runs FAILED; capability/user-origin/receipt/mutation gaps identified

## Binding Constraints
- **LOCAL RESOURCE SAFETY IS BINDING**: obey P0 process protocol; sequential local execution; no nested parallelism; own every child; clean full tree; verify baseline return; never kill unrelated processes
- Single-agent Python process cap: 6; CPU workers: 3
- Heavy stage mutex: `SECOND_BRAIN_LOCAL_HEAVY_TEST_LOCK`
- Dual-agent cap: ≤4 Python proc + ≤2 CPU workers/agent

## Phase Plan
1. **Q0**: E45-SOURCE-SELECTION.yaml + plan commit + Draft PR + TaskLeaseClaim + P0 descendant canary
2. **Q1**: Capability anti-forgery — no caller can construct VERIFIED authority
3. **Q2**: User-origin gate — remove prose heuristics, narrow E59 consumer interface
4. **Q3**: Record/bundle/atom membership verification
5. **Q4**: Master transition — independent receipt required
6. **Q5**: Skill lifecycle — verifier-only receipt view
7. **Q6**: Corpus + end-to-end evaluator
8. **Q7**: Real isolated mutations + invariant-kill proof
9. **Q8**: Provider workflow `qclaw-e46-truthful-semantic-evidence.yml`
10. **Q9**: Receipt (tested Provider green → receipt-only commit)

## Credit Budget
- Target: 50-55 credits; Reserve: 15-20 of 70 total
- Stop optional expansion at visible balance 20

## Dependency
- Codex E59 (Issue #197/PR #198) — canonical verifier authority; E46 checkpoint only, not final authority
