"""Static public-safety check for the additive R136 delivery surface."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "src" / "global_signal_gateway"
PERSISTED = [ROOT / name for name in (
    "AI_HANDOFF.yaml", "IMPLEMENTATION-RECEIPT.yaml", "UNKNOWN-REGISTRY.yaml", "WPDCR.md",
    "AMED-RESEARCH-LEDGER.md", "UNPLANNED-IMPROVEMENT-LEDGER.md", "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "AMED-EXECUTION-RECEIPT.yaml", "TASK-IMPACT-FORECAST.yaml", "SCOPE-AND-POSTFLIGHT-AUDIT.md",
    "AI-FILM-READ-ONLY-SMOKE-RECEIPT.json", "MECHANISM-TEST-MATRIX.md",
)]
FORBIDDEN = ("git push", "git commit", "git reset", "git clean", "gh api", "requests", "urllib", "socket", "private_chat", "production mcp", "trade order")
files = list(RUNTIME.rglob("*.py")) + PERSISTED
hits = []
for path in files:
    content = path.read_text(encoding="utf-8").casefold()
    for token in FORBIDDEN:
        if token in content:
            hits.append(f"{path.relative_to(ROOT)}:{token}")
print("R136_PUBLIC_SAFETY_PASS" if not hits else "R136_PUBLIC_SAFETY_FAIL\n" + "\n".join(hits))
raise SystemExit(bool(hits))
