"""Static public-safety check for the additive R136 delivery surface."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "src" / "global_signal_gateway"
PERSISTED = [ROOT / name for name in (
    "AI_HANDOFF.yaml", "IMPLEMENTATION-RECEIPT.yaml", "UNKNOWN-REGISTRY.yaml", "WPDCR.md",
    "AMED-RESEARCH-LEDGER.md", "UNPLANNED-IMPROVEMENT-LEDGER.md", "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "AMED-EXECUTION-RECEIPT.yaml", "TASK-IMPACT-FORECAST.yaml", "SCOPE-AND-POSTFLIGHT-AUDIT.md",
    "MECHANISM-TEST-MATRIX.md", "run_ai_film_smoke.py",
)]
FORBIDDEN = ("git push", "git commit", "git reset", "git clean", "gh api", "requests", "urllib", "socket", "private_chat", "production mcp", "trade order")
PLACEHOLDERS = ("todo", "fixme", "notimplementederror", "placeholder")
SHADOW_ARTIFACT_SUFFIXES = (".pyc", ".sqlite", ".db")
files = list(RUNTIME.rglob("*.py")) + PERSISTED
hits = []
for path in files:
    content = path.read_text(encoding="utf-8").casefold()
    for token in FORBIDDEN:
        if token in content:
            hits.append(f"{path.relative_to(ROOT)}:{token}")
for path in list(RUNTIME.rglob("*.py")) + [ROOT / "run_ai_film_smoke.py"]:
    content = path.read_text(encoding="utf-8").casefold()
    for token in PLACEHOLDERS:
        if token in content:
            hits.append(f"{path.relative_to(ROOT)}:{token}")
for path in ROOT.rglob("*"):
    if path.is_file() and (path.suffix in SHADOW_ARTIFACT_SUFFIXES or "__pycache__" in path.parts):
        hits.append(f"{path.relative_to(ROOT)}:shadow-artifact")
print("R136_PUBLIC_SAFETY_PASS" if not hits else "R136_PUBLIC_SAFETY_FAIL\n" + "\n".join(hits))
raise SystemExit(bool(hits))
