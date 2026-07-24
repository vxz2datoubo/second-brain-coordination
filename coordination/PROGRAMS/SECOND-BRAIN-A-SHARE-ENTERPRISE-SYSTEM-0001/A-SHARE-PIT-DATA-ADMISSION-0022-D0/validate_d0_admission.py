"""Structural validator for the 0022 D0 public-safe planning package."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "CURRENT-DATA-ADMISSION-REALITY-AUDIT.md",
    "SOURCE-CANDIDATE-AND-LICENSE-MATRIX.yaml",
    "PR51-REUSE-AND-NON-DUPLICATION-MATRIX.yaml",
    "PIT-AVAILABLE-AT-SEMANTICS-CONTRACT.yaml",
    "FIELD-UNIT-ADJUSTMENT-SEMANTICS-MATRIX.yaml",
    "HISTORICAL-SECURITY-STATUS-AND-RULE-SNAPSHOT-PLAN.yaml",
    "W3-W7-READONLY-INTERFACE-DEPENDENCY-MAP.yaml",
    "AUTHORIZED-AGENT-REPRODUCIBILITY-EQUIVALENCE-CONTRACT.yaml",
    "ONE-SOURCE-ACTIVATION-PLAN.yaml",
    "NEGATIVE-AND-ABSTENTION-TEST-MATRIX.yaml",
    "UNKNOWN-REGISTRY.yaml",
    "DISCOVERY-PACKETS.yaml",
    "AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "AMED-RESEARCH-LEDGER.yaml",
    "UNPLANNED-IMPROVEMENT-LEDGER.yaml",
    "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
}


def require(filename: str, fragment: str) -> list[str]:
    path = ROOT / filename
    if not path.is_file():
        return [f"missing: {filename}"]
    return [] if fragment in path.read_text(encoding="utf-8") else [f"missing fragment in {filename}: {fragment}"]


def main() -> int:
    errors = [f"missing: {name}" for name in sorted(REQUIRED) if not (ROOT / name).is_file()]
    errors += require("SOURCE-CANDIDATE-AND-LICENSE-MATRIX.yaml", "decision: ABSTAIN")
    errors += require("PR51-REUSE-AND-NON-DUPLICATION-MATRIX.yaml", "REUSE_ONLY_NO_SCHEMA_FORK")
    errors += require("ONE-SOURCE-ACTIVATION-PLAN.yaml", "current_decision: ABSTAIN")
    errors += require("AI_HANDOFF.yaml", "- D1")
    if errors:
        print("D0 admission package invalid")
        print("\n".join(errors))
        return 1
    print("D0 admission package valid: abstention, reuse, and no-D1 gates are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
