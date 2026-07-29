"""Emit a deterministic public-safe E22 summary; no external inputs or writes."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D2_ROOT = ROOT.parent / "0001-D2"
for item in (ROOT, D2_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from evaluation_v2_contract import public_value
from evaluation_v2_harness import run_evaluation


if __name__ == "__main__":
    summary, report = run_evaluation()
    payload = report if "--full" in sys.argv[1:] else public_value(summary)
    print(json.dumps(public_value(payload), ensure_ascii=True, sort_keys=True, separators=(",", ":")))
