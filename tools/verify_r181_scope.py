from __future__ import annotations
import argparse, subprocess, sys
BASE = "330745146be7726c42c517623a6feb5a8eaf5eb0"
ALLOWED = {"creative_runtime/shot_bundle.py", "creative_runtime/SHOT_BUNDLE_V1.md",
           "tests/test_creative_shot_bundle.py", "tools/verify_r181_scope.py",
           ".github/workflows/creative-runtime-r181-offline.yml"}
PREFIX = "coordination/PROGRAMS/CREATIVE-INTERACTIVE-FILM-SECOND-BRAIN-0001/CODEX-R181-A2-2/"
def main():
    p=argparse.ArgumentParser(); p.add_argument("--base",default=BASE); p.add_argument("--head",default="HEAD"); a=p.parse_args()
    out=subprocess.run(["git","diff","--name-only",f"{a.base}...{a.head}"],check=True,text=True,capture_output=True).stdout
    paths=tuple(x.strip().replace("\\","/") for x in out.splitlines() if x.strip())
    bad=[x for x in paths if x not in ALLOWED and not x.startswith(PREFIX)]
    print(f"base={a.base}\nhead={a.head}\nchanged_files={len(paths)}"); [print(f"ALLOW {x}") for x in paths]
    [print(f"DENY {x}",file=sys.stderr) for x in bad]; print("scope_verdict="+("PASS" if not bad else "FAIL")); return bool(bad)
if __name__ == "__main__": raise SystemExit(main())
