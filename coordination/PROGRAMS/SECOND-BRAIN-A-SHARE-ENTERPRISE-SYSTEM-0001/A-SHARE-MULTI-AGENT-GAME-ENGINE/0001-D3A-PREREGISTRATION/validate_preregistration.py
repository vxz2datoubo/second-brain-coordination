"""Fail-closed static validator for D3A preregistration; it runs no model."""
from __future__ import annotations

import hashlib
from pathlib import Path


def validate_text(text: str) -> tuple[bool, tuple[str, ...]]:
    reasons = []
    required = ("lockbox: {", "lockbox: {fixture_ids:", "brier_score", "no_model_abstention_baseline", "NOT_RUN")
    if any(item not in text for item in required):
        reasons.append("MISSING_PREREGISTRATION_REQUIREMENT")
    lockbox_line = next((line for line in text.splitlines() if line.lstrip().startswith("lockbox:")), "")
    if "immutable_hash" not in lockbox_line:
        reasons.append("LOCKBOX_NOT_IMMUTABLE")
    if "real_data_allowed: true" in text or "\nprofit:" in text.lower() or "\ntrade:" in text.lower():
        reasons.append("FORBIDDEN_RUNTIME_OR_MARKET_LANGUAGE")
    if "max_experiments: 0" not in text or "post_lockbox_tuning: forbidden" not in text:
        reasons.append("POSTHOC_TUNING_NOT_BLOCKED")
    return not reasons, tuple(reasons)


def normalized_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    target = Path(__file__).with_name("D3A-PREREGISTRATION.yaml")
    ok, reasons = validate_text(target.read_text(encoding="utf-8"))
    if not ok:
        raise SystemExit(",".join(reasons))
    print(normalized_hash(target))
