"""Risk throttle state for the finance advisor.

Reads a plan-review report and writes the next-run risk parameters. This lets
execution discipline affect future position sizing automatically.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE = ROOT / "qclaw-output" / "finance-risk-state.json"


def parse_review_report(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    score = _extract_number(text, r"纪律分:\s*([0-9.]+)", 100)
    penalty = _extract_number(text, r"扣分:\s*([0-9.]+)", 0)
    issues = []
    for line in text.splitlines():
        if line.startswith("| ") and "问题" not in line and "---" not in line:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 8 and cells[7]:
                issues.append(cells[7])
    return {"discipline_score": score, "penalty": penalty, "issues": issues}


def _extract_number(text: str, pattern: str, default: float) -> float:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else default


def compute_risk_state(
    review: dict,
    base_risk_per_trade: float,
    base_max_position_pct: float,
    base_max_total_exposure: float,
) -> dict:
    score = float(review.get("discipline_score", 100))
    penalty = float(review.get("penalty", 0))
    multiplier = 1.0
    mode = "normal"
    reasons = []

    if score < 60:
        multiplier = 0.0
        mode = "pause_new_positions"
        reasons.append("纪律分低于60，暂停新开仓")
    elif score < 80:
        multiplier = 0.5
        mode = "strict"
        reasons.append("纪律分低于80，单笔风险减半")
    elif score < 90 or penalty > 0:
        multiplier = 0.75
        mode = "cautious"
        reasons.append("存在执行扣分，下一轮单笔风险降至75%")
    else:
        reasons.append("纪律良好，维持基础风险参数")

    issue_text = " ".join(review.get("issues", []))
    if "计划外交易" in issue_text:
        multiplier = min(multiplier, 0.5)
        mode = "strict"
        reasons.append("出现计划外交易，强制降风险")
    if "买入数量超计划" in issue_text:
        multiplier = min(multiplier, 0.75)
        reasons.append("出现超计划买入，降低单笔风险")

    return {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "discipline_score": score,
        "penalty": penalty,
        "risk_multiplier": multiplier,
        "risk_per_trade": round(base_risk_per_trade * multiplier, 6),
        "max_position_pct": round(base_max_position_pct * (0.5 if mode == "pause_new_positions" else multiplier), 6),
        "max_total_exposure": round(base_max_total_exposure * (0.5 if mode == "pause_new_positions" else max(multiplier, 0.5)), 6),
        "reasons": reasons,
    }


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update finance risk throttle state from plan review.")
    parser.add_argument("--review", required=True)
    parser.add_argument("--state", default=str(DEFAULT_STATE))
    parser.add_argument("--base-risk-per-trade", type=float, default=0.005)
    parser.add_argument("--base-max-position-pct", type=float, default=0.2)
    parser.add_argument("--base-max-total-exposure", type=float, default=0.6)
    args = parser.parse_args()

    review = parse_review_report(Path(args.review))
    state = compute_risk_state(
        review,
        base_risk_per_trade=args.base_risk_per_trade,
        base_max_position_pct=args.base_max_position_pct,
        base_max_total_exposure=args.base_max_total_exposure,
    )
    save_state(Path(args.state), state)
    print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
