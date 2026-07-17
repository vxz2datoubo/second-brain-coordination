"""Build a finance watchlist CSV from a local market-data directory.

Each input CSV should contain at least date and close columns. File names can be
plain symbols, e.g. 300750.csv, or symbol-name, e.g. 300750-宁德时代.csv.

Optional metadata JSON:
{
  "300750": {"name": "宁德时代", "theme": "新能源"},
  "SAMPLE": {"name": "样例趋势股", "theme": "AI算力"}
}
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.finance_advisor import load_price_csv  # noqa: E402


def load_meta(path: str) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    with p.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def infer_symbol_name(path: Path) -> tuple[str, str]:
    stem = path.stem.strip()
    parts = re.split(r"[-_\s]+", stem, maxsplit=1)
    symbol = parts[0].strip()
    name = parts[1].strip() if len(parts) > 1 else symbol
    return symbol, name


def build_watchlist(
    market_dir: Path,
    output: Path,
    meta: dict | None = None,
    min_bars: int = 30,
    strategy: str = "optimize",
) -> dict:
    meta = meta or {}
    rows = []
    skipped = []
    for csv_path in sorted(market_dir.rglob("*.csv")):
        symbol, name = infer_symbol_name(csv_path)
        info = meta.get(symbol, {}) if isinstance(meta.get(symbol, {}), dict) else {}
        try:
            bars = load_price_csv(csv_path)
            if len(bars) < min_bars:
                skipped.append({"path": str(csv_path), "reason": f"bars {len(bars)} < min_bars {min_bars}"})
                continue
        except Exception as exc:
            skipped.append({"path": str(csv_path), "reason": f"{type(exc).__name__}: {exc}"})
            continue
        rows.append({
            "symbol": symbol,
            "name": info.get("name") or name,
            "theme": info.get("theme", ""),
            "csv_path": str(csv_path).replace("\\", "/"),
            "strategy": info.get("strategy", strategy),
            "short_window": info.get("short_window", 5),
            "long_window": info.get("long_window", 20),
            "bars": len(bars),
            "start_date": bars[0].date,
            "end_date": bars[-1].date,
        })

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "symbol", "name", "theme", "csv_path", "strategy",
            "short_window", "long_window", "bars", "start_date", "end_date",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return {"output": str(output), "count": len(rows), "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build watchlist from local market CSV directory.")
    parser.add_argument("--market-dir", required=True)
    parser.add_argument("--output", default=str(ROOT / "qclaw-output" / "finance-watchlist-generated.csv"))
    parser.add_argument("--meta", default="", help="Optional symbol metadata JSON")
    parser.add_argument("--min-bars", type=int, default=30)
    parser.add_argument("--strategy", default="optimize")
    args = parser.parse_args()

    result = build_watchlist(
        Path(args.market_dir),
        Path(args.output),
        meta=load_meta(args.meta),
        min_bars=args.min_bars,
        strategy=args.strategy,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
