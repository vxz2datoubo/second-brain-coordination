"""Small deterministic scope/public-safety scan for the S0C delivery."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
FORBIDDEN = ("import requests", "from requests", "import urllib.request", "import subprocess", "from subprocess", "import multiprocessing", "import threading", "import socket", "subprocess.", "socket.", "api.github.com", "gh api")


def main() -> int:
    hits = []
    files = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts and path.suffix in {".py", ".json", ".yaml", ".yml", ".md"} and path.name != "public_safety_scan.py"]
    for path in files:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            if token.lower() in text.lower():
                hits.append(f"{path.relative_to(ROOT)}:{token}")
    if hits:
        print("PUBLIC_SAFE_FAIL", *hits, sep="\n")
        return 1
    print(f"PUBLIC_SAFE_PASS files_scanned={len(files)} NO_NETWORK_NO_CHILD_PROCESS_NO_PRIVATE_RUNTIME")
    return 0


if __name__ == "__main__":
    sys.exit(main())
