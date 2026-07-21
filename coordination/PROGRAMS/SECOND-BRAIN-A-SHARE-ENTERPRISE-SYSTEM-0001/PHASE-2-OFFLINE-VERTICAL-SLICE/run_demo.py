"""CLI for the public-safe P2 demonstration. No network or broker operations exist here."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from offline_research.engine import OfflineResearchRunner, load_fixture  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Research-only deterministic A-share offline replay demo (NO_TRADE).")
    parser.add_argument("command", choices=["run-demo", "ingest-fixture", "validate-dataset"])
    parser.add_argument("--fixture", type=Path, default=ROOT / "fixtures" / "synthetic_bars.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "demo")
    parser.add_argument("--as-of", default="2026-01-31T23:59:59Z")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.command == "run-demo":
        result = OfflineResearchRunner(args.fixture, args.output, args.as_of).run(args.resume)
        print(json.dumps(result, sort_keys=True))
        return 0
    bars, quarantine, manifest = load_fixture(args.fixture, args.as_of)
    print(json.dumps({"records": len(bars), "quarantine": [item.__dict__ for item in quarantine], "manifest": manifest}, sort_keys=True))
    return 0 if not quarantine else 2


if __name__ == "__main__":
    raise SystemExit(main())
