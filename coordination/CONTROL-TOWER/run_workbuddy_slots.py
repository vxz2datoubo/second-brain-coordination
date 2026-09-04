from __future__ import annotations

import argparse
import json
from pathlib import Path

from workbuddy_slots import validate_workbuddy_slots


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate canonical WorkBuddy multi-slot registry and collisions.")
    parser.add_argument("--repo-root", default="../..")
    args = parser.parse_args()

    report = validate_workbuddy_slots(Path(args.repo_root))
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0 if report["structural_check"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
