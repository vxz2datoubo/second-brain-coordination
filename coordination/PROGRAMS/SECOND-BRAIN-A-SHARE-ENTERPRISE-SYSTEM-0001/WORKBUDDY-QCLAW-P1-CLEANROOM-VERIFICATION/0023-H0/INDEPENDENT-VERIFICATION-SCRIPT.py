"""
R10 Unified Wrapper Verifier — python INDEPENDENT-VERIFICATION-SCRIPT.py [normal|nt1|nt2|nt3]
All modes share the same qclaw_wrapper(). Strict UTF-8. Fail-closed.
"""
import subprocess, hashlib, os, re, json, sys, tempfile, shutil, platform
from pathlib import Path

EXIT = 0
def fail(msg): global EXIT; EXIT = 1; print(f"FAIL|{msg}")
def chk(args, **kw): return subprocess.run(args, capture_output=True, text=True, **kw)
def H(s): return hashlib.sha256(s.encode()).hexdigest()

PACKAGE = Path(__file__).resolve().parent
rr = chk(["git","rev-parse","--show-toplevel"], cwd=str(PACKAGE), timeout=10)
if rr.returncode != 0 or not rr.stdout.strip(): fail("rev_parse"); sys.exit(1)
REPO = Path(rr.stdout.strip())
th = chk(["git","rev-parse","HEAD"], cwd=str(REPO), timeout=10)
if th.returncode != 0 or not th.stdout.strip(): fail("rev_parse_head"); sys.exit(1)

MODE = sys.argv[1] if len(sys.argv) > 1 else "normal"
QH = "63c344084d9af86cb26c1cc65a30d409fefa872f"
RV = "f5f25dafe7b02bf0e20e75865e1610d836ab380a"
Q15 = {"P1-AI-HANDOFF.yaml","P1-AMED-AGENT-EXECUTION-RECEIPT.yaml","P1-AMED-RESEARCH-LEDGER.yaml",
       "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml","P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
       "P1-BLOCKING-FAILURE-ASSESSMENT.yaml","P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
       "P1-DIMENSION-SCORECARD.yaml","P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml","P1-FROZEN-MANIFEST.yaml",
       "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml","P1-TEST-RUN-RECEIPT.md",
       "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml","P1-VALIDATE-AUDIT.py","P1-VERDICT-AND-GPT-RECOMMENDATION.yaml"}

print(f"R10|mode={MODE}|os={platform.system()}|head={th.stdout.strip()}")

def scan(against=RV):
    dn = chk(["git","diff","--name-only",against], cwd=str(REPO), timeout=10)
    if dn.returncode != 0: fail("git_diff"); return [],[],"",""
    changed = [c.strip() for c in dn.stdout.split('\n') if c.strip()]
    P = [(re.compile(r"[A-Za-z]:[/\\][A-Za-z]"),"drv"),(re.compile("/"+"Users/"),"usr"),
         (re.compile("/"+"home/"),"hom"),(re.compile("\\\\"+"\\\\"+r"[A-Za-z]"),"unc"),
         (re.compile("ghp_"+r"[A-Za-z0-9]{30,}"),"gh"),(re.compile("sk-"+r"[A-Za-z0-9]{30,}"),"ai"),
         (re.compile(r"ya29\.[A-Za-z0-9_\-]{50,}"),"gl"),
         (re.compile("-"*5+"BEGIN.*PRIVATE KEY"+"-"*5),"pem"),
         (re.compile(r"(?:password|secret|token|credential)\s*[:=]\s*\S+",re.I),"cred")]
    F = []
    for f in changed:
        fp = REPO / f
        if not fp.is_file(): continue
        try: c = fp.read_text(encoding="utf-8")
        except: fail(f"decode={f}"); continue
        for p,lab in P:
            for m in p.finditer(c):
                if any(s in m.group(0) for s in {"CLEANROOM_WORKSPACE"}): continue
                F.append({"file":f,"pat":lab})
    return changed, F, H("\n".join(sorted(changed))), H(json.dumps(F, sort_keys=True))

def qclaw_wrapper(skip_file=None, replace_validator=None):
    """Unified QCLAW reproduction wrapper. All modes use this."""
    lt = chk(["git","ls-tree","--name-only",f"{QH}:"], cwd=str(REPO), timeout=10)
    if lt.returncode != 0: fail("ls_tree"); return None
    actual = {f.strip() for f in lt.stdout.split('\n') if f.strip().startswith("P1-")}
    if actual != Q15: fail(f"manifest|extra={actual-Q15}|missing={Q15-actual}"); return None
    
    td = tempfile.mkdtemp()
    for fn in sorted(Q15):
        if skip_file and fn == skip_file: continue
        r = chk(["git","show",f"{QH}:{fn}"], cwd=str(REPO), timeout=10)
        if r.returncode != 0: shutil.rmtree(td); fail(f"show={fn}"); return None
        (Path(td)/fn).write_bytes(r.stdout.encode() if isinstance(r.stdout,str) else r.stdout)
    
    vpath = Path(td) / "P1-VALIDATE-AUDIT.py"
    if replace_validator is not None:
        vpath.write_text(replace_validator, encoding="utf-8")
    
    vr = chk([sys.executable, str(vpath)], cwd=str(td), timeout=30)
    R = {"exit":vr.returncode, "soh":H(vr.stdout), "seh":H(vr.stderr)}
    for l in vr.stdout.split('\n'):
        if "Combined SHA" in l: R["cmb"] = l.strip().split(": ")[-1]
        if "Files hashed" in l: R["fh"] = int(l.strip().split(": ")[-1])
        if "Results:" in l: R["res"] = l.strip()
    shutil.rmtree(td)
    return R

# === MODE DISPATCH (all use production wrapper) ===
if MODE == "normal":
    C,F,mh,fh = scan()
    if F: EXIT = 1
    print(f"SCAN|files={len(C)}|findings={len(F)}|mhash={mh}|fhash={fh}")
    r = qclaw_wrapper()
    if r: print(f"QCLAW|exit={r['exit']}|{r.get('res')}|combined={r.get('cmb')}")
    else: EXIT = 1

elif MODE == "nt1":
    tgt = REPO / "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION/0023-H0/AI_HANDOFF.yaml"
    orig = tgt.read_text(encoding="utf-8")
    tgt.write_text(orig + "\n" + chr(70) + ":" + chr(92) + "leak\n", encoding="utf-8")
    _,F,_,fh = scan()
    tgt.write_text(orig, encoding="utf-8")
    if F: print(f"NT1|PASS|findings={len(F)}|fhash={fh}"); EXIT = 1
    else: print(f"NT1|FAIL"); EXIT = 1

elif MODE == "nt2":
    r = qclaw_wrapper(skip_file="P1-TEST-RUN-RECEIPT.md")
    if r and r["exit"] != 0:
        print(f"NT2|PASS|exit={r['exit']}|soh={r['soh']}"); EXIT = 1
    else: print(f"NT2|FAIL|exit={r['exit'] if r else 'WRAPPER_FAILED'}"); EXIT = 1

elif MODE == "nt3":
    r = qclaw_wrapper(replace_validator="import sys; sys.exit(7)")
    if r and r["exit"] == 7:
        print(f"NT3|PASS|expected=7|actual={r['exit']}"); EXIT = 1
    else: print(f"NT3|FAIL|actual={r['exit'] if r else 'WRAPPER_FAILED'}"); EXIT = 1

print(f"FINAL|exit={EXIT}")
sys.exit(EXIT)
