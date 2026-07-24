"""Public-safe structural validator for the 0017 D0 planning package.

This is intentionally not a market-data parser, labeler, backtest, or trading tool.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
REQUIRED = {
    "PROJECT-PLAN.yaml",
    "CURRENT-REPOSITORY-AND-LOCAL-REALITY-AUDIT.md",
    "LEGACY-REUSE-AND-NON-DUPLICATION-MATRIX.yaml",
    "DATA-CAPABILITY-AND-PIT-CONTRACT.yaml",
    "LOCAL-DATA-INVENTORY-AND-REPRODUCIBILITY-RECEIPT.yaml",
    "REFERENCE-ZONE-DEFINITION-CONTRACT.yaml",
    "BREACH-RECLAIM-LABEL-STATE-MACHINE.yaml",
    "A-SHARE-VERSIONED-RULE-SNAPSHOT-CONTRACT.yaml",
    "TPLUSONE-INVENTORY-AND-UNTRADEABLE-CONTRACT.yaml",
    "COST-NONFILL-AND-CAPACITY-CONTRACT.yaml",
    "VALIDATION-OOS-AND-LOCKBOX-DESIGN.yaml",
    "BASELINE-NEGATIVE-CONTROL-AND-FAILURE-MATRIX.yaml",
    "QCLAW-P0-QUESTION-COVERAGE-MAP.yaml",
    "UNKNOWN-REGISTRY.yaml",
    "ALTERNATIVE-AND-TRADEOFF-MATRIX.yaml",
    "AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "AMED-RESEARCH-LEDGER.yaml",
    "UNPLANNED-IMPROVEMENT-LEDGER.yaml",
    "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
}
OBJECTS = {
    "ReferenceLiquidityZone",
    "ReferenceZoneBreachEvent",
    "ReclaimAssessment",
    "PostSweepStabilizationAssessment",
    "TPlusOneInventoryState",
    "SweepReclaimExperimentFamily",
    "SweepReclaimValidationReport",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    missing = sorted(name for name in REQUIRED if not (ROOT / name).is_file())
    if missing:
        fail(f"missing required artifacts: {', '.join(missing)}")

    corpus = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.iterdir()
        if path.is_file() and path.suffix in {".yaml", ".md"}
    )
    absent = sorted(name for name in OBJECTS if name not in corpus)
    if absent:
        fail(f"missing required object contract names: {', '.join(absent)}")

    coverage = (ROOT / "QCLAW-P0-QUESTION-COVERAGE-MAP.yaml").read_text(encoding="utf-8")
    mapped = re.findall(r"^  Q(\d{2}):", coverage, flags=re.MULTILINE)
    expected = [f"{number:02d}" for number in range(1, 43)]
    if mapped != expected:
        fail(f"QCLAW mapping must contain Q01..Q42 exactly once; found {mapped}")

    for name in (
        "DATA-CAPABILITY-AND-PIT-CONTRACT.yaml",
        "REFERENCE-ZONE-DEFINITION-CONTRACT.yaml",
        "BREACH-RECLAIM-LABEL-STATE-MACHINE.yaml",
        "TPLUSONE-INVENTORY-AND-UNTRADEABLE-CONTRACT.yaml",
    ):
        text = (ROOT / name).read_text(encoding="utf-8")
        for field in ("source", "event_time", "observed_at", "available_at", "rule_version", "missing_error_state"):
            if field not in text:
                fail(f"{name} lacks point-in-time provenance field {field}")

    forbidden_success_claims = ("BACKTEST_PASSED", "ALPHA_VERIFIED", "LIVE_TRADING_ENABLED")
    hit = [claim for claim in forbidden_success_claims if claim in corpus]
    if hit:
        fail(f"D0 planning package contains forbidden success claim(s): {', '.join(hit)}")

    print(f"PASS: {len(REQUIRED)} required artifacts, 42 QCLAW mappings, {len(OBJECTS)} object names")


if __name__ == "__main__":
    main()
