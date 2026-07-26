from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation_harness import normalized_evaluation_hash

print("D2_EVALUATION_NORMALIZED_SHA256=" + normalized_evaluation_hash())
