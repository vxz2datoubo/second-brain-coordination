"""Static public-safety boundary check for the persisted S0D delivery surface."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "src" / "global_signal_shadow"
PERSISTED = [
    ROOT / "REAL-SOURCE-ONE-SHOT-SHADOW-RECEIPT.json",
    ROOT / "DURABLE-S0C-REPLAY-RECEIPT.json",
    ROOT / "SECOND-BRAIN-SELF-SHADOW-RECEIPT.json",
    ROOT / "AI_HANDOFF.yaml",
    ROOT / "IMPLEMENTATION-RECEIPT.yaml",
    ROOT / "UNKNOWN-REGISTRY.yaml",
    ROOT / "WPDCR.md",
]

# ``subprocess`` is permitted only because adapter.py invokes read-only local
# Git inspection.  The forbidden list instead targets transport and mutation
# capabilities, while focused tests exercise the adapter's explicit denials.
FORBIDDEN = (
    "git push", "git commit", "git checkout", "git reset", "git clean", "gh api",
    "requests", "urllib", "socket", "private_chat", "access_token", "api_key",
    "raw_source_body", "production mcp", "trade order",
)

files = [path for path in RUNTIME.rglob("*.py") if "__pycache__" not in path.parts and path.name != "fixtures.py"] + PERSISTED
hits = []
for path in files:
    content = path.read_text(encoding="utf-8").casefold()
    for token in FORBIDDEN:
        if token in content:
            hits.append(f"{path.relative_to(ROOT)}:{token}")

print("S0D_PUBLIC_SAFETY_PASS" if not hits else "S0D_PUBLIC_SAFETY_FAIL\n" + "\n".join(hits))
raise SystemExit(bool(hits))
