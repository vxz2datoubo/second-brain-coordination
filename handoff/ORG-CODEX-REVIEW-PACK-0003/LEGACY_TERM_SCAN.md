# LEGACY_TERM_SCAN — 遗留旧组织术语扫描

> Task: ORG-CODEX-REVIEW-PACK-0003 | Date: 2026-07-16 03:55 UTC+8

## Scan target terms

| # | Term | Allowed in audit/history docs | Allowed in active protocol | Violations found |
|---|------|:---:|:---:|:--:|
| 1 | QClaw | ✅ | ❌ | 0 in active protocol files |
| 2 | "Codex从属于WorkBuddy" / "Codex under WorkBuddy" | ✅ | ❌ | 0 (removed from candidate) |
| 3 | "Codex不常用" | ✅ | ❌ | 0 |
| 4 | "三方协作" (should be 四方) | ✅ | ❌ | 0 |
| 5 | "强制Wyckoff前置" / "必须按Phase" | ✅ | ❌ | **1 found in CHATGPT-BRAIN-PROTOCOL.candidate.md** (see below) |
| 6 | "大单必然等于机构" / "大单=纯机构" | ✅ | ❌ | 0 |
| 7 | "固定3.8倍已验证" | ✅ | ❌ | 0 |
| 8 | "固定15技能必须调用" | ✅ | ❌ | 0 |

## Detailed findings

### AGENTS.merged-candidate.md — CLEAN
- ✅ No QClaw references
- ✅ Codex as equal peer, no subordination language
- ✅ Wyckoff Phase: "treat as model feature or hypothesis, not infallible prerequisite"
- ✅ No "三方" language (explicit 4-role model)
- ✅ No unverified claims

### CHATGPT-BRAIN-PROTOCOL.candidate.md — ⚠️ 1 finding

**T5-1**: "A股量化（69项技能）包含威科夫全周期..."

- Status: ⚠️ **MINOR** — Lists Wyckoff as capability description (not as mandatory rule). This is acceptable because the document describes WorkBuddy's available skills, not requires them.
- Recommendation: No action needed. Skill listing ≠ mandatory usage rule.

### daytrade_system/AGENTS.candidate.md — CLEAN
- ✅ No QClaw
- ✅ No Codex subordination
- ✅ Wyckoff not mentioned as prerequisite

### LEGACY-RULES-AUDIT.md — EXPECTED
- ✅ ALL legacy terms appear as audit items (this is the audit document)
- ✅ Each term properly classified and disposition documented

### STRATEGY-HYPOTHESES.md — EXPECTED
- ✅ "Wyckoff Phase" listed as hypothesis H01 with status "部分验证"
- ✅ "大单=机构" listed as H03 with "部分验证" 
- ✅ "3.8x增强" listed as H04 with "待验证"
- ✅ "15技能必须调用" listed as H14 with "工作流预设"

### Current AGENTS.md (unchanged) — NOT AUDITED
- The current AGENTS.md is the OLD version and HAS NOT been changed. This is expected — it will be replaced on approval.

## Summary

| File | Violations | Status |
|------|:----------:|--------|
| AGENTS.merged-candidate.md | 0 | ✅ CLEAN |
| CHATGPT-BRAIN-PROTOCOL.candidate.md | 0 active / 1 skill-description | ✅ PASS |
| daytrade_system/AGENTS.candidate.md | 0 | ✅ CLEAN |
| LEGACY-RULES-AUDIT.md | All terms in audit context | ✅ EXPECTED |
| STRATEGY-HYPOTHESES.md | All terms as hypotheses | ✅ EXPECTED |

**No blocking violations. All legacy terms correctly confined to audit/hypothesis context.**
