"""Run E55 real candidate-source mutations and emit a public-safe JSON receipt."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from e55_authority.mutations import run_production_source_mutations  # noqa: E402


def main() -> int:
    results = run_production_source_mutations(ROOT / "src" / "e55_authority", ROOT / "tests")
    print(json.dumps({"schema": "e55-mutation-receipt-v1", "results": [asdict(item) for item in results]}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
