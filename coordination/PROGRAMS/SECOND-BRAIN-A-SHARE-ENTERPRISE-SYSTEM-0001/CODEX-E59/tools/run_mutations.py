"""Run E59 mutations sequentially and retain only public-safe hashes/results."""

from __future__ import annotations

import json
from pathlib import Path
import sys


TASK_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK_ROOT / "src"))

from e59_runtime.mutations import catalog_digest, run_all_mutations


def main() -> int:
    results = run_all_mutations()
    payload = {
        "catalog_digest": catalog_digest(),
        "mutation_count": len(results),
        "killed_count": sum(1 for result in results if result["killed"]),
        "results": results,
    }
    output = TASK_ROOT / "MUTATION-EXECUTION-RESULTS.json"
    output.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0 if payload["killed_count"] == payload["mutation_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
