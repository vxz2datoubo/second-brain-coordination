# PROTOCOL_DIFF — CHATGPT-BRAIN-PROTOCOL v1 vs v2

> Task: ORG-CODEX-MERGE-0002 | Date: 2026-07-16 03:44 UTC+8

## Structural changes

| Aspect | v1 (original) | v2 (candidate) |
|--------|---------------|----------------|
| QClaw role | Listed as "纯算力引擎" with bridge instructions | **Removed** — QClaw not in this project |
| Codex status | Under WorkBuddy management ("在WorkBuddy管理框架下") | Independent role — "首席工程师与代码审查者" |
| ChatGPT role | Implied as "大脑" via document | Explicit strategic architect + independent reviewer |
| Role count | 3 (User / WorkBuddy / QClaw) + Codex under WB | 4 equals (User / ChatGPT / Codex / WorkBuddy) |
| "铁律" framing | Presented as absolute rules | Reframed as "经验参考，非铁律" with pointers to verified vs unverified status |

## Content removed

| Content | Reason |
|---------|--------|
| QClaw bridge instructions (端口8799, `qclaw.py`) | QClaw not in this project |
| Codex as WorkBuddy subordinate | New equal-role model |
| Absolute "铁律" language for unverified rules | Migrated to STRATEGY-HYPOTHESES.md |

## Content added

| Content | Purpose |
|---------|---------|
| 4-role authority boundary table | Clear decision rights |
| Pointers to `docs/trading/STRATEGY-HYPOTHESES.md` | Informed reader where to check verification status |
| Pointers to `config/trading/*.yaml` | Parameters are config-managed, not hardcoded |
| Pointers to `daytrade_system/AGENTS.md` | Trading-specific rules have their own scope |

## Preserved

| Content | Status |
|---------|--------|
| WorkBuddy 250 skill capabilities | ✅ Preserved |
| Data source priority table | ✅ Preserved |
| System architecture diagram | ✅ Updated for 4-role model |
| ChatGPT ↔ WorkBuddy command format | ✅ Preserved |
| Capability boundaries | ✅ Preserved |
| Quick reference (stock codes, core scripts) | ✅ Preserved |
