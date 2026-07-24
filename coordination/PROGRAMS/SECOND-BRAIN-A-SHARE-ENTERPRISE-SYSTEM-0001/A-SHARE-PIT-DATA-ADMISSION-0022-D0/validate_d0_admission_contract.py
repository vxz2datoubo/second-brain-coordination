"""Structural validator for the public-safe 0022 D0 admission-contract package."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "PROJECT-PLAN.yaml",
    "CURRENT-DATA-ADMISSION-AND-NON-DUPLICATION-AUDIT.md",
    "PR51-REUSE-AND-AUTHORITY-MATRIX.yaml",
    "SOURCE-ADMISSION-REQUIREMENTS-AND-EVIDENCE-MATRIX.yaml",
    "PIT-FIELD-TIME-UNIT-ADJUSTMENT-CONTRACT.yaml",
    "HISTORICAL-SECURITY-STATUS-AND-RULE-SNAPSHOT-CONTRACT.yaml",
    "W2-W3-W7-READONLY-OWNERSHIP-AND-DEPENDENCY-MAP.yaml",
    "ONE-SOURCE-ADMISSION-DECISION-PROCEDURE.yaml",
    "WORKBUDDY-ISSUE92-LOCAL-EVIDENCE-EXECUTION-CONTRACT.yaml",
    "OFFICIAL-SOURCE-EVIDENCE-REGISTER.yaml",
    "NEGATIVE-ABSTENTION-AND-FAILURE-TEST-MATRIX.yaml",
    "UNKNOWN-REGISTRY.yaml",
    "TEST-RUN-RECEIPT.md",
    "CODEX-FEEDBACK-v2.yaml",
    "AI_HANDOFF.yaml",
}


def has(name: str, fragment: str) -> list[str]:
    file = ROOT / name
    if not file.is_file():
        return [f"missing: {name}"]
    return [] if fragment in file.read_text(encoding="utf-8") else [f"missing fragment: {name}: {fragment}"]


def main() -> int:
    errors = [f"missing: {name}" for name in sorted(REQUIRED) if not (ROOT / name).is_file()]
    errors += has("PR51-REUSE-AND-AUTHORITY-MATRIX.yaml", "REUSE_EXISTING_CANONICAL_AUTHORITIES")
    errors += has("ONE-SOURCE-ADMISSION-DECISION-PROCEDURE.yaml", "NO_SOURCE_SUBMITTED_NO_DECISION")
    errors += has("WORKBUDDY-ISSUE92-LOCAL-EVIDENCE-EXECUTION-CONTRACT.yaml", "QUEUED_UNTIL_GPT_RELEASE")
    errors += has("AI_HANDOFF.yaml", "NO_LOCAL_EXECUTION")
    register = "OFFICIAL-SOURCE-EVIDENCE-REGISTER.yaml"
    for fragment in (
        "SSE-2026-TRADING-RULES",
        "SZSE-2026-TRADING-RULES",
        "BSE-2026-TRADING-RULES",
        "上证发〔2026〕41号",
        "深证上〔2026〕551号",
        "北证公告〔2026〕17号",
        "publication_date: '2026-04-24'",
        "effective_from: '2026-07-06'",
        "page_access_status: VERIFIED_ACCESSIBLE",
        "document_authority_status: VERIFIED_OFFICIAL_EXCHANGE_RULE",
        "deferred_provision_status:",
        "historical_coverage_status: UNKNOWN_REMAINS_OPEN",
    ):
        errors += has(register, fragment)
    if (ROOT / register).is_file() and "ACCESS_NOT_AVAILABLE" in (ROOT / register).read_text(encoding="utf-8"):
        errors.append("official rule register still conflates access with historical coverage")
    if errors:
        print("D0 admission contract package invalid")
        print("\n".join(errors))
        return 1
    print("D0 admission contract package valid: no source selected and Issue92 remains queued")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
