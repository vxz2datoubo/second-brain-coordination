"""
H1 Fail-Closed Independent Verifier — python H1-INDEPENDENT-VERIFIER.py [normal|nt1|nt2|nt3]
All modes share one production function. Strict UTF-8. Fail-closed everywhere.
"""
import subprocess, hashlib, os, re, json, sys, tempfile, shutil, platform
from pathlib import Path

EXIT = 0
def fail(msg): global EXIT; EXIT = 1; print(f"FAIL|{msg}")
def chk(args, **kw): return subprocess.run(args, capture_output=True, text=True, **kw)
def H(s): return hashlib.sha256(s.encode()).hexdigest()

MODE = sys.argv[1] if len(sys.argv) > 1 else "normal"
QH = "63c344084d9af86cb26c1cc65a30d409fefa872f"
Q15 = {"P1-AI-HANDOFF.yaml","P1-AMED-AGENT-EXECUTION-RECEIPT.yaml","P1-AMED-RESEARCH-LEDGER.yaml",
       "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml","P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
       "P1-BLOCKING-FAILURE-ASSESSMENT.yaml","P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
       "P1-DIMENSION-SCORECARD.yaml","P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml","P1-FROZEN-MANIFEST.yaml",
       "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml","P1-TEST-RUN-RECEIPT.md",
       "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml","P1-VALIDATE-AUDIT.py","P1-VERDICT-AND-GPT-RECOMMENDATION.yaml"}

PACKAGE = Path(__file__).resolve().parent
rr = chk(["git","rev-parse","--show-toplevel"], cwd=str(PACKAGE), timeout=10)
if rr.returncode != 0 or not rr.stdout.strip(): fail("rev_parse"); sys.exit(1)
REPO = Path(rr.stdout.strip())
if not REPO.exists(): fail("repo_missing"); sys.exit(1)
th = chk(["git","rev-parse","HEAD"], cwd=str(REPO), timeout=10)
if th.returncode != 0 or not th.stdout.strip(): fail("rev_parse_head"); sys.exit(1)

print(f"H1|mode={MODE}|os={platform.system()}|py={sys.version.split()[0]}|head={th.stdout.strip()}")

# === SAFETY PATTERNS (safe-fragment) ===
SP = [(re.compile(r"[A-Za-z]:[/\\][A-Za-z]"),"drv"),(re.compile("/"+"Users/"),"usr"),
      (re.compile("/"+"home/"),"hom"),(re.compile("\\\\"+"\\\\"+r"[A-Za-z]"),"unc"),
      (re.compile("ghp_"+r"[A-Za-z0-9]{30,}"),"gh"),(re.compile("sk-"+r"[A-Za-z0-9]{30,}"),"ai"),
      (re.compile(r"ya29\.[A-Za-z0-9_\-]{50,}"),"gl"),
      (re.compile("-"*5+"BEGIN.*PRIVATE KEY"+"-"*5),"pem"),
      (re.compile(r"(?:password|secret|token|credential)\s*[:=]\s*\S+",re.I),"cred")]

def scan_h1_files():
    """Scan all 5 H1 files in the delivery directory"""
    F = []
    files = []
    for fp in sorted(PACKAGE.rglob("*")):
        if not fp.is_file() or fp.suffix == '.pyc': continue
        rel = fp.relative_to(PACKAGE)
        files.append(str(rel))
        try: c = fp.read_text(encoding="utf-8")
        except: fail(f"decode={rel}"); continue
        for p,lab in SP:
            for m in p.finditer(c):
                if any(s in m.group(0) for s in {"CLEANROOM_WORKSPACE"}): continue
                F.append({"file":str(rel),"pat":lab})
    return files, F, H("\n".join(sorted(files))), H(json.dumps(F,sort_keys=True))

def qclaw_reproduce(skip_file=None, replace_validator=None):
    """Unified QCLAW reproduction — all modes use this."""
    lt = chk(["git","ls-tree","--name-only",f"{QH}:"], cwd=str(REPO), timeout=10)
    if lt.returncode != 0: fail("ls_tree"); return None
    actual = {f.strip() for f in lt.stdout.split('\n') if f.strip().startswith("P1-")}
    if actual != Q15: fail(f"manifest|extra={actual-Q15}|missing={Q15-actual}"); return None

    td = tempfile.mkdtemp()
    try:
        for fn in sorted(Q15):
            if skip_file and fn == skip_file: continue
            r = chk(["git","show",f"{QH}:{fn}"], cwd=str(REPO), timeout=10)
            if r.returncode != 0: fail(f"show={fn}"); return None
            (Path(td)/fn).write_bytes(r.stdout.encode() if isinstance(r.stdout,str) else r.stdout)

        vp = Path(td) / "P1-VALIDATE-AUDIT.py"
        if replace_validator is not None:
            vp.write_text(replace_validator, encoding="utf-8")

        vr = chk([sys.executable, str(vp)], cwd=str(td), timeout=30)
        R = {"exit":vr.returncode, "soh":H(vr.stdout), "seh":H(vr.stderr)}
        for l in vr.stdout.split('\n'):
            if "Combined SHA" in l: R["cmb"] = l.strip().split(": ")[-1]
            if "Files hashed" in l: R["fh"] = int(l.strip().split(": ")[-1])
            if "Results:" in l: R["res"] = l.strip()
        return R
    finally:
        shutil.rmtree(td, ignore_errors=True)

# === DISPATCH ===
if MODE == "normal":
    files, F, mh, fh = scan_h1_files()
    if F: fail("safety_scan"); print(f"SCAN|files={len(files)}|findings={len(F)}|mhash={mh}|fhash={fh}")
    else: print(f"SCAN|files={len(files)}|findings=0|mhash={mh}")

    r = qclaw_reproduce()
    if not r or r["exit"] != 0 or r.get("res") != "Results: 37 PASS / 0 FAIL / 0 SKIP" or r.get("fh") != 14:
        fail(f"qclaw|exit={r['exit'] if r else 'NONE'}|res={r.get('res') if r else 'NONE'}")
    else:
        print(f"QCLAW|exit=0|37/0/0|combined={r.get('cmb')}")

elif MODE == "nt1":
    # Inject unsafe content
    tgt = PACKAGE / "H1-PUBLIC-SAFETY-REPORT.yaml"
    if tgt.exists():
        orig = tgt.read_text(encoding="utf-8")
        tgt.write_text(orig + "\n" + chr(70) + ":" + chr(92) + "leak\n", encoding="utf-8")
        _, F, _, _ = scan_h1_files()
        tgt.write_text(orig, encoding="utf-8")
    else:
        # Create temp file
        tf = PACKAGE / "_nt1_tmp.txt"
        tf.write_text(chr(70) + ":" + chr(92) + "leak\n", encoding="utf-8")
        _, F, _, _ = scan_h1_files()
        tf.unlink()
    if F: print(f"NT1|PASS|findings={len(F)}"); EXIT = 1
    else: fail("NT1 injection not detected")

elif MODE == "nt2":
    r = qclaw_reproduce(skip_file="P1-TEST-RUN-RECEIPT.md")
    if r and r["exit"] != 0:
        print(f"NT2|PASS|exit={r['exit']}"); EXIT = 1
    else: fail(f"NT2 missing file not detected|exit={r['exit'] if r else 'NONE'}")

elif MODE == "nt3":
    r = qclaw_reproduce(replace_validator="import sys; sys.exit(7)\n")
    if r and r["exit"] == 7:
        print(f"NT3|PASS|exit=7"); EXIT = 1
    else: fail(f"NT3 forced fail|exit={r['exit'] if r else 'NONE'}")

print(f"FINAL|exit={EXIT}")
sys.exit(EXIT)
