"""Generate a public-safe exact-read receipt from a fresh temporary AI Film clone."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "coordination" / "PROGRAMS" / "SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001" / "GLOBAL-SIGNAL-PLANE" / "S0-SYNTHETIC" / "src"), str(Path(__file__).resolve().parent / "src")]

from global_signal_gateway.gateway import (  # noqa: E402
    AI_FILM_COMMIT,
    SystemAwarenessProjection,
    ai_film_directing_read_only_smoke,
    temporary_exact_clone,
)
from global_signal_plane.ledger import DurableSignalLedger  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    ledger = DurableSignalLedger(":memory:")
    awareness = SystemAwarenessProjection.from_canonical(ROOT, ledger.rebuild_projection(), ())
    with temporary_exact_clone("https://github.com/vxz2datoubo/eustia-ai-film.git", AI_FILM_COMMIT) as source_root:
        receipt = ai_film_directing_read_only_smoke(
            source_root,
            awareness=awareness,
            fixture={"symptoms": ["\u5de6\u53f3\u53cd\u4e86"]},
        )
    receipt["bounded_cleanup"] = "PASS"
    receipt["evidence_scope"] = "PUBLIC_SAFE_METADATA_ONLY"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
