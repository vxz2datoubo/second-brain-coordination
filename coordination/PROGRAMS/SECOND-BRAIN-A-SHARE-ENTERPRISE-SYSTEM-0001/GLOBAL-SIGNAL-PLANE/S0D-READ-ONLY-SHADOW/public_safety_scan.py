from pathlib import Path
ROOT = Path(__file__).resolve().parent
FORBIDDEN = ("git push", "gh api", "requests", "urllib", "socket", "subprocess", "private_chat", "access_token")
hits = [f"{p.relative_to(ROOT)}:{token}" for p in ROOT.rglob("*") if p.is_file() and p.name != "public_safety_scan.py" and p.suffix in {".py", ".json", ".yaml", ".md"} and "__pycache__" not in p.parts for token in FORBIDDEN if token in p.read_text(encoding="utf-8").casefold()]
print("S0D_PUBLIC_SAFETY_PASS" if not hits else "S0D_PUBLIC_SAFETY_FAIL\n" + "\n".join(hits))
raise SystemExit(bool(hits))
