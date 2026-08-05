#!/usr/bin/env python3
"""QCLAW E27 — CI Workflow for exact-head evidence."""
import subprocess, sys, os, json, hashlib
from pathlib import Path
from datetime import datetime, timezone

E27_DIR = Path(__file__).resolve().parent
SRC = E27_DIR / "src"
sys.path.insert(0, str(SRC))

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)

def main():
    py311 = os.environ.get("PYTHON_311", sys.executable)
    py313 = os.environ.get("PYTHON_313", sys.executable)
    
    results = {}
    for label, py in [("3.11", py311), ("3.13", py313)]:
        if not Path(py).exists():
            print(f"SKIP {label}: {py} not found")
            continue
        
        r = run([
            py, str(E27_DIR / "tests" / "run_all_tests.py")
        ], encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        
        results[label] = {
            "exit_code": r.returncode,
            "stdout": r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout,
            "stderr": r.stderr[-1000:] if len(r.stderr) > 1000 else r.stderr
        }
        
        passed = "FAILED: 0" in r.stdout
        print(f"[CI] Python {label}: {'PASS' if r.returncode == 0 else 'FAIL'} (exit={r.returncode})")
    
    return 0 if all(v["exit_code"] == 0 for v in results.values()) else 1

if __name__ == "__main__":
    sys.exit(main())
