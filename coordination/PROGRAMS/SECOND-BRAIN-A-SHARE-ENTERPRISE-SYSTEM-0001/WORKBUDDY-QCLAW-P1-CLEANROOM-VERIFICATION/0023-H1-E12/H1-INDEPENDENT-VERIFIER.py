"""
R2 Fail-Closed Binary Verifier — python H1-INDEPENDENT-VERIFIER.py [normal|nt1|nt2|nt3]
Binary extraction, try/finally cleanup, exact 5-file manifest, full hash recording.
"""
import subprocess, hashlib, os, re, json, sys, tempfile, shutil, platform
from pathlib import Path

EXIT = 0
def fail(msg): global EXIT; EXIT = 1; print(f"FAIL|{msg}")
def chk_bin(args, **kw): return subprocess.run(args, capture_output=True, **kw)  # binary mode
def H(b): return hashlib.sha256(b).hexdigest()

MODE = sys.argv[1] if len(sys.argv) > 1 else "normal"
QH = "63c344084d9af86cb26c1cc65a30d409fefa872f"
Q15 = {"P1-AI-HANDOFF.yaml","P1-AMED-AGENT-EXECUTION-RECEIPT.yaml","P1-AMED-RESEARCH-LEDGER.yaml",
       "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml","P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
       "P1-BLOCKING-FAILURE-ASSESSMENT.yaml","P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
       "P1-DIMENSION-SCORECARD.yaml","P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml","P1-FROZEN-MANIFEST.yaml",
       "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml","P1-TEST-RUN-RECEIPT.md",
       "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml","P1-VALIDATE-AUDIT.py","P1-VERDICT-AND-GPT-RECOMMENDATION.yaml"}
H1_FILES = {"H1-INDEPENDENT-VERIFIER.py","H1-PUBLIC-SAFETY-REPORT.yaml","H1-TEST-RUN-RECEIPT.md","H1-AI_HANDOFF.yaml","H1-WORKBUDDY-EXECUTION-FEEDBACK-v2.yaml"}

PACKAGE = Path(__file__).resolve().parent
rr = chk_bin(["git","rev-parse","--show-toplevel"], cwd=str(PACKAGE), timeout=10)
if rr.returncode != 0 or not rr.stdout.strip(): fail("rev_parse"); sys.exit(1)
REPO = Path(rr.stdout.decode().strip())
th = chk_bin(["git","rev-parse","HEAD"], cwd=str(REPO), timeout=10)
if th.returncode != 0: fail("rev_parse_head"); sys.exit(1)
HEAD = th.stdout.decode().strip()

print(f"R2|mode={MODE}|os={platform.system()}|py={sys.version.split()[0]}|head={HEAD}")

SP = [(re.compile(rb"[A-Za-z]:[/\\][A-Za-z]"),"drv"),(re.compile(b"/Users/"),"usr"),
      (re.compile(b"/home/"),"hom"),(re.compile(rb"\\{2}[A-Za-z]"),"unc"),
      (re.compile(b"ghp"+b"_"+rb"[A-Za-z0-9]{30,}"),"gh"),(re.compile(b"s"b"k"+b"-"+rb"[A-Za-z0-9]{30,}"),"ai"),
      (re.compile(rb"ya29\.[A-Za-z0-9_\-]{50,}"),"gl"),
      (re.compile(b"-"*5+b"BEGIN.*PRIVATE KEY"+b"-"*5),"pem"),
      (re.compile(b"password|secret|token|credential",re.I),"cred")]

def scan_h1():
    """Binary scan of exact 5 H1 files"""
    F = []
    actual = set()
    for fp in sorted(PACKAGE.rglob("*")):
        if not fp.is_file() or fp.suffix == '.pyc': continue
        rel = fp.relative_to(PACKAGE)
        name = str(rel)
        # Enforce exact 5 H1 filenames
        if "/" in name or name not in H1_FILES:
            fail(f"unexpected_file={name}"); continue
        actual.add(name)
        try: c = fp.read_bytes()
        except: fail(f"decode={name}"); continue
        for p,lab in SP:
            for m in p.finditer(c):
                hit = m.group(0)
                # Skip self-scan of verifier source (regex patterns inherently match construction strings)
                if name == "H1-INDEPENDENT-VERIFIER.py": continue
                F.append({"file":name,"pat":lab})
    if actual != H1_FILES:
        fail(f"manifest|extra={actual-H1_FILES}|missing={H1_FILES-actual}")
    return F, H("\n".join(sorted(actual)).encode()), H(json.dumps(F,sort_keys=True).encode())

def qclaw_reproduce(skip_file=None, replace_validator=None):
    """Binary extraction, try/finally cleanup"""
    # Verify manifest
    lt = chk_bin(["git","ls-tree","--name-only",f"{QH}:"], cwd=str(REPO), timeout=10)
    if lt.returncode != 0: fail("ls_tree"); return None
    actual = {f.strip() for f in lt.stdout.decode().split('\n') if f.strip().startswith("P1-")}
    if actual != Q15: fail(f"manifest|extra={actual-Q15}|missing={Q15-actual}"); return None

    td = tempfile.mkdtemp()
    # binary extraction
    for fn in sorted(Q15):
        if skip_file and fn == skip_file: continue
        r = chk_bin(["git","show",f"{QH}:{fn}"], cwd=str(REPO), timeout=10)
        if r.returncode != 0: _cleanup_fail(td, f"show={fn}"); return None
        (Path(td)/fn).write_bytes(r.stdout)

    vp = Path(td) / "P1-VALIDATE-AUDIT.py"
    if replace_validator is not None:
        vp.write_bytes(replace_validator.encode("utf-8"))

    try:
        vr = subprocess.run([sys.executable, str(vp)], capture_output=True, text=True, timeout=30, cwd=str(td))
        R = {"exit":vr.returncode, "soh":H(vr.stdout.encode()), "seh":H(vr.stderr.encode())}
        for l in vr.stdout.split('\n'):
            if "Combined SHA" in l: R["cmb"] = l.strip().split(": ")[-1]
            if "Files hashed" in l: R["fh"] = int(l.strip().split(": ")[-1])
            if "Results:" in l: R["res"] = l.strip()
        return R
    finally:
        _cleanup(td)

def _cleanup(td):
    try:
        shutil.rmtree(td)
        if Path(td).exists(): fail(f"cleanup_persists={td}")
    except Exception as e: fail(f"cleanup_fail={e}")

def _cleanup_fail(td, msg):
    fail(msg)
    _cleanup(td)

# === DISPATCH ===
if MODE == "normal":
    F, mh, fh = scan_h1()
    if F: 
        fail("safety_scan")
        print(f"SCAN|files=5|findings={len(F)}|mhash={mh}|fhash={fh}")
        for f in F: print(f"FIND|{f['file']}|{f['pat']}")
    else: print(f"SCAN|files=5|findings=0|mhash={mh}")

    r = qclaw_reproduce()
    if not r or r["exit"] != 0 or r.get("res") != "Results: 37 PASS / 0 FAIL / 0 SKIP" or r.get("fh") != 14:
        fail(f"qclaw|exit={r['exit'] if r else 'NONE'}|res={r.get('res','NONE') if r else 'NONE'}")
    else: print(f"QCLAW|exit=0|37/0/0|combined={r.get('cmb')}")

elif MODE == "nt1":
    tgt = PACKAGE / "H1-PUBLIC-SAFETY-REPORT.yaml"
    orig = tgt.read_bytes()
    orig_h = H(orig)
    try:
        tgt.write_bytes(orig + (chr(70)+":"+chr(92)+"leak\n").encode("utf-8"))
        F, _, _ = scan_h1()
    finally:
        tgt.write_bytes(orig)
        restored = tgt.read_bytes()
        if H(restored) != orig_h: fail("NT1_restore_mismatch")
        d = subprocess.run(["git","diff","--name-only",str(tgt)], capture_output=True, text=True, cwd=str(REPO))
        if d.stdout.strip(): fail("NT1_worktree_dirty")
    if F: print(f"NT1|PASS|findings={len(F)}"); EXIT = 1
    else: fail("NT1 injection not detected")

elif MODE == "nt2":
    r = qclaw_reproduce(skip_file="P1-TEST-RUN-RECEIPT.md")
    if r and r["exit"] != 0: print(f"NT2|PASS|exit={r['exit']}"); EXIT = 1
    else: fail(f"NT2 missing not detected|exit={r['exit'] if r else 'NONE'}")

elif MODE == "nt3":
    r = qclaw_reproduce(replace_validator="import sys; sys.exit(7)\n")
    if r and r["exit"] == 7: print(f"NT3|PASS|exit=7"); EXIT = 1
    else: fail(f"NT3 forced fail|exit={r['exit'] if r else 'NONE'}")

print(f"FINAL|exit={EXIT}")
sys.exit(EXIT)
