"""
R4 Fail-Closed Self-Auditing Verifier — PR #91
Uses Path(__file__)+git rev-parse. Scans ALL files. Exits non-zero on any failure.
Constructs patterns from safe fragments. Includes deterministic negative tests.
"""
import subprocess, hashlib, os, re, json, sys, tempfile, shutil, time, platform
from pathlib import Path

PACKAGE = Path(__file__).resolve().parent

try:
    REPO = Path(subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True, cwd=str(PACKAGE)).stdout.strip())
except:
    print("FATAL: git rev-parse failed"); sys.exit(1)

QCLAW_HEAD = "63c344084d9af86cb26c1cc65a30d409fefa872f"
TESTED_HEAD = subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True, cwd=str(REPO)).stdout.strip()
OS_NAME = platform.system()
PY_VER = sys.version.split()[0]
TS = time.time()

print(f"VERIFIER|os={OS_NAME}|python={PY_VER}|qclaw_head={QCLAW_HEAD}|tested_head={TESTED_HEAD}")
print(f"VERIFIER|timestamp={TS}")

# ======= SAFE PATTERN CONSTRUCTION =======
pats = [
    (re.compile(r"[A-Za-z]:[/\\][A-Za-z]"), "windows_drive"),
    (re.compile("/" + "Users/"), "users_path"),
    (re.compile("/" + "home/"), "home_path"),
    (re.compile("\\\\" + "\\\\" + r"[A-Za-z]"), "unc_path"),
    (re.compile("ghp" + "_" + r"[A-Za-z0-9]{30,}"), "github_token"),
    (re.compile("sk" + "-" + r"[A-Za-z0-9]{30,}"), "openai_key"),
    (re.compile(r"ya29\.[A-Za-z0-9_\-]{50,}"), "google_token"),
    (re.compile("-"*5 + "BEGIN.*PRIVATE KEY" + "-"*5), "private_key"),
    (re.compile(r"(?:password|secret|token|credential)\s*[:=]\s*\S+", re.I), "credential_assign"),
]
SAFE = {"<CLEANROOM_WORKSPACE>", "CLEANROOM_WORKSPACE"}

# ======= SCAN ALL FILES =======
scanned = 0
findings = []
manifest = []
exit_code = 0

for fpath in sorted(PACKAGE.rglob("*")):
    if not fpath.is_file(): continue
    if fpath.suffix == '.pyc': continue
    rel = fpath.relative_to(PACKAGE)
    try:
        content = fpath.read_text(errors='ignore')
    except:
        print(f"SCAN|SKIP|{rel}|unreadable")
        exit_code = 1
        continue
    
    scanned += 1
    manifest.append(str(rel))
    
    for pat, label in pats:
        for m in pat.finditer(content):
            hit = m.group(0)
            if any(s in hit for s in SAFE): continue
            ctx = content[max(0,m.start()-12):m.end()+12].replace('\n',' ')[:50]
            findings.append({"file":str(rel),"pattern":label,"context":ctx})

manifest_hash = hashlib.sha256("\n".join(sorted(manifest)).encode()).hexdigest()
fjson = json.dumps(findings, sort_keys=True)
findings_hash = hashlib.sha256(fjson.encode()).hexdigest()

if findings:
    exit_code = 1

print(f"SCAN|files={scanned}|findings={len(findings)}|manifest_hash={manifest_hash}|findings_hash={findings_hash}")
for f in findings:
    print(f"FIND|{f['file']}|{f['pattern']}|{f['context'][:30]}")

# ======= NEGATIVE TEST: memory-only, no literal paths in source =======
_drv = re.compile(r"[A-Za-z]:[/\\][A-Za-z]")
_t1 = chr(88)+":"+"\\"+"tmp"
assert _drv.search(_t1), "NEGTEST: drive path pattern broken"
assert not _drv.search("CLEANROOM"), "NEGTEST: alias false positive"
assert re.compile("ghp_"+("[A-Za-z0-9]"*1)+"{30,}").search("ghp_"+"A"*35), "NEGTEST: github token broken"
assert re.compile(r"ya29\.[A-Za-z0-9_\-]{50,}").search("ya29."+"A"*50), "NEGTEST: google token broken"
print("NEGTEST|PASS|4 assertions")

# ======= QCLAW REPRODUCTION =======
td = tempfile.mkdtemp()
QCLAW_15 = [
    "P1-AI-HANDOFF.yaml","P1-AMED-AGENT-EXECUTION-RECEIPT.yaml","P1-AMED-RESEARCH-LEDGER.yaml",
    "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml","P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
    "P1-BLOCKING-FAILURE-ASSESSMENT.yaml","P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
    "P1-DIMENSION-SCORECARD.yaml","P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml","P1-FROZEN-MANIFEST.yaml",
    "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml","P1-TEST-RUN-RECEIPT.md",
    "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml","P1-VALIDATE-AUDIT.py",
    "P1-VERDICT-AND-GPT-RECOMMENDATION.yaml",
]

# Verify via git ls-tree
ls_tree = subprocess.run(["git","ls-tree","--name-only",f"{QCLAW_HEAD}:"], capture_output=True, text=True, cwd=str(REPO))
actual_files = {f.strip() for f in ls_tree.stdout.split('\n') if f.strip().startswith("P1-")}
expected_files = set(QCLAW_15)
extra = actual_files - expected_files
missing = expected_files - actual_files
if extra or missing:
    print(f"QCLAW_MANIFEST|MISMATCH|extra={extra}|missing={missing}")
    exit_code = 1

all_extracted = True
for fn in QCLAW_15:
    r = subprocess.run(["git","show",f"{QCLAW_HEAD}:{fn}"], capture_output=True, cwd=str(REPO))
    if r.returncode != 0:
        print(f"QCLAW|FAIL|{fn}|extraction_failed")
        all_extracted = False
        exit_code = 1
        continue
    (Path(td)/fn).write_bytes(r.stdout)
    sha = hashlib.sha256(r.stdout).hexdigest()
    print(f"QCLAW|OK|{fn}|{len(r.stdout)}B|{sha[:16]}")

if not all_extracted:
    print("QCLAW|ABORT|extraction_failed")
    shutil.rmtree(td)
    sys.exit(exit_code)

# Run validator as file
vp = Path(td) / "P1-VALIDATE-AUDIT.py"
if not vp.exists():
    print("QCLAW|ABORT|validator_not_found")
    shutil.rmtree(td)
    sys.exit(1)

v_start = time.time()
vr = subprocess.run([sys.executable, str(vp)], capture_output=True, text=True, timeout=30, cwd=str(td))
v_dur = time.time() - v_start

if vr.returncode != 0:
    exit_code = 1

v_stdout_h = hashlib.sha256(vr.stdout.encode()).hexdigest()
v_stderr_h = hashlib.sha256(vr.stderr.encode()).hexdigest()
last = vr.stdout.strip().split('\n')[-1] if vr.stdout.strip() else "EMPTY"

print(f"QCLAW_VALIDATOR|exit={vr.returncode}|duration={v_dur:.1f}s|stdout_hash={v_stdout_h}|stderr_hash={v_stderr_h}")
for l in vr.stdout.split('\n'):
    if any(k in l for k in ['Combined SHA','Files hashed','Results:']):
        print(f"QCLAW_RESULT|{l.strip()}")

shutil.rmtree(td)

# ======= SUMMARY =======
final = "PASS" if exit_code == 0 else "FAIL"
print(f"\nFINAL|status={final}|exit_code={exit_code}|scan={len(findings)}_findings")
sys.exit(exit_code)
