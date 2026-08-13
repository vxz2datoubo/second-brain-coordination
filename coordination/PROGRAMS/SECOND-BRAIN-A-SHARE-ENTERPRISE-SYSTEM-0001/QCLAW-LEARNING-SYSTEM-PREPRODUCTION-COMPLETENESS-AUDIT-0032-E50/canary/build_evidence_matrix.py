"""Generate persisted E50 R2 evidence matrix JSON into evidence/."""
import json
import os
import sys

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from qclaw_e50_audit import runner  # noqa: E402

res = runner.run_audit()
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence")
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "evidence_matrix.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(res, f, ensure_ascii=False, indent=2, default=str)
print("wrote", os.path.abspath(out_path))
print("head:", res["canonical_head_sha"])
print("recommendation:", res["recommendation"]["recommendation"])
