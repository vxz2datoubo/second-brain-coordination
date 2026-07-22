# SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT
# QCLAW-P4-INDEPENDENT-ADVERSARIAL-EVIDENCE-0013A-R2
# Generated: 2026-07-23T07:10:00+08:00

## 1. Architecture Drift Detection

### 1.1 ACTIVE-QCLAW-TASK.yaml Missing from Remote
**Discovery:** `coordination/ACTIVE-QCLAW-TASK.yaml` does not exist on remote `main`.
QCLAW-TASK-ROUTER.md (the routing protocol) specifies this file as the unique
source of truth for task routing, yet it was never created on the canonical branch.

**Impact:** Every QCLAW cold start must reverse-engineer the active task from
Issue #59 comments + ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml + inference. This
adds latency and ambiguity.

**Opportunity:** Create `coordination/ACTIVE-QCLAW-TASK.yaml` on main after
PR #70 acceptance, synced with ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml Lane A.

### 1.2 Task Router Points to Missing File
**Discovery:** QCLAW-TASK-ROUTER.md §2 mandates reading `ACTIVE-QCLAW-TASK.yaml`
which doesn't exist. The protocol's single-source-of-truth claim is broken.

**Opportunity:** Either create the file or update the router to reference
ACTIVE-EXECUTION-SEQUENCE-v1.0.yaml as the canonical task source.

### 1.3 Network Constraint: Git HTTPS Blocked
**Discovery:** Both `git clone` and `git push` over HTTPS fail with RST.
GitHub API (gh CLI) works for all operations but requires manual blob-tree-commit-ref
orchestration per delivery.

**Impact:** Each delivery is ~5-15 minutes of API construction vs ~30 seconds
of git push. Error-prone (PowerShell string escaping, JSON construction).

**Opportunity:** Investigate SSH-based git as a fallback, or formalize the
API pipeline into a reusable script (see Unplanned Improvement UPI-005).

## 2. Cross-Agent Coordination Gaps

### 2.1 Atom ID Namespace Collision Risk
**Discovery:** QCLAW uses AMNS-XXXX atom IDs; Codex may use a different
namespace. No shared atom ID registry exists. Adversarial queries reference
QCLAW atom IDs, which may not resolve in the Codex knowledge store.

**Opportunity:** A shared ATOM-ID-NAMESPACE-REGISTRY.yaml (C-class proposal UPI-006).

### 2.2 No Shared Adversarial Query Schema
**Discovery:** QCLAW defined its own YAML schema (query_id, question_text,
expected_behavior, forbidden_behavior, expected_atom_ids, forbidden_atom_ids,
rationale, pass_criteria, failure_classification). Codex may have a different
consumption format, creating a mapping burden.

**Opportunity:** Standardize as ADVERARIAL-QUERY-PACK.schema.json (C-class proposal UPI-004).

### 2.3 PR #64 / #65 Frozen State
**Discovery:** PR #64 (Issue #59 knowledge architecture) and PR #65 (Issue #60
long-term memory) were created in R1 but frozen by GPT. PR #64 has known
format issues; PR #65 requires re-audit.

**Opportunity:** After PR #70 acceptance, prioritize PR #64 cleanup to unlock
the Issue #59 P1 digestion pipeline.

## 3. Knowledge Quality Observations

### 3.1 UNKNOWN/ABSTAIN Distinction
**Discovery:** AC-06 query design revealed that the distinction between
UNKNOWN (knowledge not in store) and ABSTAIN (knowledge exists but safety/
authority rules prevent disclosure) is critical but subtle. If PR #58 conflates
these, false negatives will occur.

### 3.2 Sycophancy Risk Patterns
**Discovery:** During AC-01 design, identified three high-risk sycophancy patterns:
  1. User-preference-labeled-as-external-fact → agent agrees without evidence
  2. Source-viewpoint-labeled-as-authority-fact → agent upgrades confidence
  3. Temporal proximity bias → agent prefers recent corrections over older
     verified facts without checking supersede chains

### 3.3 Historical Version Chain Gaps
**Discovery:** AC-04 queries assume PR #58 can distinguish current from
historical knowledge. If the runtime does not maintain effective_from/
effective_to/supersedes/superseded_by chains, the entire AC-04 category
will produce noise rather than signal.

## 4. Process Improvements

### 4.1 Cold-Start Bootstrap Gap
**Discovery:** QCLAW cold start requires reading 4-6 sources (TASK-ROUTER,
Issue #59, Issue comments, ACTIVE-EXECUTION-SEQUENCE, PR #70 comments) to
determine the single active task. A one-file bootstrap would reduce latency.

### 4.2 PowerShell JSON Reliability
**Discovery:** PowerShell ConvertTo-Json produces invalid JSON for multi-line
strings with special characters. The stdin pipe approach (here-string → gh api --input -)
is more reliable and should be the documented pattern.

## 5. Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| PR #58 cannot map QCLAW atom IDs | High | Atom ID namespace registry (UPI-006) |
| PR #58 has no established AC-06 baseline | Medium | AC-06 queries include pass_criteria with tolerance zones |
| Git network RST persists for all deliveries | Medium | Formalize API pipeline or investigate SSH |
| Codex may reject adversarial package format | Low | Format is documented in README + each YAML is self-describing |

signed:
  agent: QCLAW
  timestamp: "2026-07-23T07:10:00+08:00"
  safety: PUBLIC_SAFE
