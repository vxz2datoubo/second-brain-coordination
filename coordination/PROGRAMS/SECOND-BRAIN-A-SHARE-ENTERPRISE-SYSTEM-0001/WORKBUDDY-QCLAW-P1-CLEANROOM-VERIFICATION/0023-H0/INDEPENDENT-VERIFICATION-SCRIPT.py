"""
R3 Self-Auditing Verifier — PR #91 Public-Safety & QCLAW Reproduction
Uses Path(__file__) + git rev-parse for workspace detection.
Scans ALL files including itself. Constructs patterns from safe fragments.
"""
import subprocess, hashlib, os, re, json, sys, tempfile, shutil, time
from pathlib import Path
from datetime import datetime

PACKAGE = Path(__file__).resolve().parent
REPO_RAW = subprocess.run(["git","rev-parse","--show-toplevel"], capture_output=True, text=True, cwd=str(PACKAGE))
REPO = Path(REPO_RAW.stdout.strip())
QCLAW_HEAD = "63c344084d9af86cb26c1cc65a30d409fefa872f"  # 40-char full head
TESTED_HEAD_RAW = subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True, cwd=str(REPO))
TESTED_HEAD = TESTED_HEAD_RAW.stdout.strip()

print(f"Workspace: <CLEANROOM_WORKSPACE>")
print(f"Tested head: {TESTED_HEAD}")
print(f"QCLAW head: {QCLAW_HEAD}")
print(f"Python: {sys.version.split()[0]}")
print(f"OS: Windows")

# ======= STEP 1: BUILD PATTERNS FROM SAFE FRAGMENTS =======
# Avoid embedding literal patterns that would self-match.
# Instead, construct regex from run-time fragments.
def mkdrv(): return re.compile(r"[A-Za-z]:[/\\][A-Za-z]")
def mkusr(): return re.compile("/" + "Users/")
def mkhome(): return re.compile("/" + "home/")
def mkunc(): return re.compile("\\\\" + "\\\\" + r"[A-Za-z]")
def mkgit(): return re.compile("ghp" + "_" + r"[A-Za-z0-9]{30,}")
def mkai(): return re.compile("sk" + "-" + r"[A-Za-z0-9]{30,}")
def mkpem(): return re.compile("-" * 5 + "BEGIN.*PRIVATE KEY" + "-" * 5)

patterns = [
    (mkdrv(), "Windows_drive_path"),
    (mkusr(), "Users_path"),
    (mkhome(), "Home_path"),
    (mkunc(), "UNC_path"),
    (mkgit(), "GitHub_token"),
    (mkai(), "OpenAI_key"),
    (mkpem(), "Private_key"),
]

# Build a literal safety whitelist
SAFE = {"<CLEANROOM_WORKSPACE>", "CLEANROOM_WORKSPACE"}

# ======= STEP 2: SCAN ALL FILES (NO EXCLUSION) =======
scanned = 0
findings = []
manifest_lines = []

for fpath in sorted(PACKAGE.rglob("*")):
    if not fpath.is_file(): continue
    if fpath.suffix in ['.pyc']: continue
    
    rel = fpath.relative_to(PACKAGE)
    try:
        content = fpath.read_text(errors='ignore')
    except:
        print(f"  SKIP (unreadable): {rel}")
        continue
    
    scanned += 1
    manifest_lines.append(str(rel))
    
    for pat, label in patterns:
        for m in pat.finditer(content):
            hit = m.group(0)
            if any(s in hit for s in SAFE):
                continue
            ctx_s = max(0, m.start()-15)
            ctx = content[ctx_s:m.end()+15].replace('\n',' ')[:60]
            findings.append({"file": str(rel), "pattern": label, "context": ctx})

manifest_hash = hashlib.sha256("\n".join(sorted(manifest_lines)).encode()).hexdigest()
findings_json = json.dumps(findings, sort_keys=True)
findings_hash = hashlib.sha256(findings_json.encode()).hexdigest()

result = "CLEAN" if len(findings) == 0 else f"FAIL"
print(f"\nSCAN|files={scanned}|findings={len(findings)}|result={result}")
print(f"SCAN|manifest_hash={manifest_hash}")
print(f"SCAN|findings_hash={findings_hash}")
for f in findings:
    print(f"FIND|{f['file']}|{f['pattern']}|{f['context'][:40]}")

# ======= STEP 3: FAITHFUL QCLAW REPRODUCTION =======
print(f"\n=== QCLAW Reproduction (head {QCLAW_HEAD}) ===")

# Exact 15-file manifest (real extensions from git ls-tree)
QCLAW_15 = [
    "P1-AI-HANDOFF.yaml",
    "P1-AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "P1-AMED-RESEARCH-LEDGER.yaml",
    "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml",
    "P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
    "P1-BLOCKING-FAILURE-ASSESSMENT.yaml",
    "P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
    "P1-DIMENSION-SCORECARD.yaml",
    "P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml",
    "P1-FROZEN-MANIFEST.yaml",
    "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml",
    "P1-TEST-RUN-RECEIPT.md",
    "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml",
    "P1-VALIDATE-AUDIT.py",
    "P1-VERDICT-AND-GPT-RECOMMENDATION.yaml",
]

td = tempfile.mkdtemp()
for fn in QCLAW_15:
    content = subprocess.run(["git","show",f"{QCLAW_HEAD}:{fn}"], capture_output=True, cwd=str(REPO))
    if content.returncode != 0:
        print(f"  FAIL extract: {fn} (rc={content.returncode})")
        continue
    dest = Path(td) / fn
    dest.write_bytes(content.stdout)
    # Use file-based hashing instead of stdin pipe to avoid Py3.13 subprocess issue
    blob = subprocess.run(["git","hash-object",str(dest)], capture_output=True, text=True, cwd=str(REPO)).stdout.strip()
    sha = hashlib.sha256(content.stdout).hexdigest()
    print(f"  OK {fn}: {len(content.stdout):,}B blob={blob[:8]} sha256={sha[:16]}")

# Run validator as file (not python -c)
validator_path = Path(td) / "P1-VALIDATE-AUDIT.py"
v_start = time.time()
v_result = subprocess.run([sys.executable, str(validator_path)], capture_output=True, text=True, timeout=30, cwd=str(td))
v_duration = time.time() - v_start

v_stdout_hash = hashlib.sha256(v_result.stdout.encode()).hexdigest()
v_stderr_hash = hashlib.sha256(v_result.stderr.encode()).hexdigest()
last_line = v_result.stdout.strip().split('\n')[-1] if v_result.stdout.strip() else "EMPTY"
combined_line = [l for l in v_result.stdout.split('\n') if 'Combined SHA' in l or 'Files hashed' in l or 'Results:' in l]

print(f"\nQCLAW_VALIDATOR|exit={v_result.returncode}|duration={v_duration:.1f}s")
print(f"QCLAW_VALIDATOR|stdout_sha256={v_stdout_hash}")
print(f"QCLAW_VALIDATOR|stderr_sha256={v_stderr_hash}")
print(f"QCLAW_VALIDATOR|last_line={last_line}")
for cl in combined_line:
    print(f"QCLAW_RESULT|{cl.strip()}")

shutil.rmtree(td)

# ======= SUMMARY LINE =======
print(f"\nR3_COMPLETE|tested_head={TESTED_HEAD}|scan={result}|findings={len(findings)}")
