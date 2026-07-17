# CANDIDATE_REFERENCE_CHECK — 候选文档路径引用检查

> Task: ORG-CODEX-REVIEW-PACK-0003 | Date: 2026-07-16 03:55 UTC+8

## Cross-references audited

### AGENTS.merged-candidate.md

| Reference | Real Path | Status |
|-----------|-----------|:------:|
| `coordination/TASK-PACKET.template.md` | ✅ exists | ✅ |
| `daytrade_system/AGENTS.md` | ⚠️ only `AGENTS.candidate.md` exists | 🔸 POINTS TO NON-EXISTENT FILE (candidate not yet activated) |
| `docs/trading/TRADING-GOVERNANCE.md` | ✅ exists | ✅ |
| `docs/trading/STRATEGY-HYPOTHESES.md` | ✅ exists | ✅ |
| `CHATGPT-BRAIN-PROTOCOL.md` | ✅ exists (v1) | ✅ |
| `config/trading/risk_limits.yaml` | ⚠️ only `.candidate.yaml` exists | 🔸 POINTS TO NON-EXISTENT FILE (candidate not yet activated) |
| `config/trading/session_windows.yaml` | ⚠️ only `.candidate.yaml` exists | 🔸 POINTS TO NON-EXISTENT FILE |
| `config/trading/strategy_parameters.yaml` | ⚠️ only `.candidate.yaml` exists | 🔸 POINTS TO NON-EXISTENT FILE |

**Assessment**: All 3 config references and 1 daytrade AGENTS reference point to files that don't exist yet (candidate not activated). This is correct behavior — references forward to post-activation paths. ⚠️ If approved, the activation step (`.candidate.yaml` → `.yaml`, `AGENTS.candidate.md` → `AGENTS.md`) will resolve these.

### CHATGPT-BRAIN-PROTOCOL.candidate.md

| Reference | Real Path | Status |
|-----------|-----------|:------:|
| `SKILLS-CATALOG.md` | ✅ exists | ✅ |
| `AGENTS.md` | ✅ exists (current v1) | ✅ |
| `coordination/SYSTEM-STATE.md` | ✅ exists | ✅ |
| `coordination/TASK-PACKET.template.md` | ✅ exists | ✅ |
| `daytrade_system/AGENTS.md` | ⚠️ only candidate | 🔸 SAME ISSUE |
| `docs/trading/LEGACY-RULES-AUDIT.md` | ✅ exists | ✅ |
| `docs/trading/STRATEGY-HYPOTHESES.md` | ✅ exists | ✅ |
| `docs/trading/TRADING-GOVERNANCE.md` | ✅ exists | ✅ |
| `config/trading/*.yaml` | ⚠️ only candidates | 🔸 SAME ISSUE |

### daytrade_system/AGENTS.candidate.md

| Reference | Real Path | Status |
|-----------|-----------|:------:|
| `config/trading/risk_limits.yaml` | ⚠️ only candidate | 🔸 |
| `config/trading/session_windows.yaml` | ⚠️ only candidate | 🔸 |
| `config/trading/strategy_parameters.yaml` | ⚠️ only candidate | 🔸 |
| `daytrade_system/runner.py` | ✅ exists | ✅ |
| `coordination/SYSTEM-STATE.md` | ✅ exists | ✅ |

## Summary

| Type | Count |
|------|:----:|
| ✅ Valid references | 12 |
| 🔸 References to not-yet-activated files (resolved post-approval) | 8 |
| ❌ Broken references | 0 |
| ⚠️ Candidate file referencing formal file name (expected behavior) | 8 |

**No action required.** All 🔸 references will auto-resolve when candidate files are activated (D1-D4 in APPROVAL_CHECKLIST).
