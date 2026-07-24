"""
R2 Deterministic Scanner — PR #91 Path & Credential Hygiene
Tested head: ce1704c (R1)
Scans PR91 output package only — P1 files verified via git show separately.
"""
import subprocess, hashlib, re, os, json
from pathlib import Path
from datetime import datetime

PACKAGE = Path(r"F:\aidanao\_cleanroom\coordination\PROGRAMS\SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001\WORKBUDDY-QCLAW-P1-CLEANROOM-VERIFICATION\0023-H0")
REPO = Path(r"F:\aidanao\_cleanroom")

danger_patterns = [
    (re.compile(r"[A-Za-z]:[/\\][A-Za-z]"), "Windows_drive_path"),
    (re.compile(r"/Users/"), "Users_path"),
    (re.compile(r"/home/"), "Home_path"),
    (re.compile(r"\\\\[A-Za-z]"), "UNC_path"),
    (re.compile(r"ghp_[A-Za-z0-9]{30,}"), "GitHub_token"),
    (re.compile(r"sk-[A-Za-z0-9]{30,}"), "OpenAI_key"),
    (re.compile(r"-----BEGIN.*PRIVATE KEY-----"), "Private_key_header"),
]

# Exclude scanner scripts from scan (pattern self-hits)
self_path = Path(__file__).resolve()
iv_path = PACKAGE / "INDEPENDENT-VERIFICATION-SCRIPT.py"
exclude_paths = {self_path, iv_path.resolve() if iv_path.exists() else None}

scanned = 0
findings = []

for fpath in sorted(PACKAGE.rglob("*")):
    if not fpath.is_file() or fpath.suffix in ['.pyc', '.DS_Store']:
        continue
    if fpath.resolve() in exclude_paths:
        continue
    
    try:
        content = fpath.read_text(errors='ignore')
    except:
        continue
    
    scanned += 1
    rel = fpath.relative_to(PACKAGE)
    
    for pat, label in danger_patterns:
        for m in pat.finditer(content):
            match_text = m.group(0)
            ctx_start = max(0, m.start()-20)
            ctx = content[ctx_start:m.end()+20].replace('\n','\\n')[:80]
            
            # Allow <CLEANROOM_WORKSPACE>
            if label == "Windows_drive_path" and "<CLEANROOM_WORKSPACE>" in ctx:
                continue
            
            findings.append({
                "file": str(rel),
                "pattern": label,
                "context": ctx,
            })

print(f"SCAN|scanned={scanned}|findings={len(findings)}")
for f in findings:
    print(f"FIND|{f['file']}|{f['pattern']}|{f['context']}")

result = "CLEAN" if len(findings) == 0 else f"FAIL_{len(findings)}"
output_hash = hashlib.sha256(json.dumps(findings, sort_keys=True).encode()).hexdigest()
print(f"RESULT|{result}")
print(f"HASH|{output_hash}")

# === QCLAW Validator Rerun ===
print("\n=== QCLAW Validator (PR84 head) ===")
v_sha = hashlib.sha256(
    subprocess.run(["git", "-C", str(REPO), "show", "63c34408:P1-VALIDATE-AUDIT.py"],
                   capture_output=True).stdout
).hexdigest()
print(f"VALIDATOR_SHA256|{v_sha}")

# Extract and run in temp
import tempfile, shutil
td = Path("F:/aidanao/_qclaw_p1")
td.mkdir(exist_ok=True)
for fn in ["AI-HANDOFF","AMED-AGENT-EXECUTION-RECEIPT","AMED-RESEARCH-LEDGER",
           "AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT","BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW",
           "BLOCKING-FAILURE-ASSESSMENT","COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT",
           "DIMENSION-SCORECARD","DISCOVERED-DEFECTS-AND-AMENDMENTS","FROZEN-MANIFEST",
           "QUESTION-BY-QUESTION-EVIDENCE-MAP","TEST-RUN-RECEIPT",
           "UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT","VERDICT-AND-GPT-RECOMMENDATION"]:
    ext = ".md" if "REPORT" in fn else ".yaml"
    subprocess.run(["git","-C",str(REPO),"show",f"63c34408:P1-{fn}{ext}"],
                   stdout=open(td / f"P1-{fn}{ext}", "wb"))

validator_code = subprocess.run(["git","-C",str(REPO),"show","63c34408:P1-VALIDATE-AUDIT.py"],
                                capture_output=True).stdout

import sys, time
start = time.time()
result = subprocess.run([sys.executable, "-c", validator_code.decode()],
                        cwd=str(td), capture_output=True, text=True, timeout=30)
duration = time.time() - start

result_hash = hashlib.sha256(result.stdout.encode()).hexdigest()
print(f"VALIDATOR_EXIT|{result.returncode}")
print(f"VALIDATOR_DURATION|{duration:.1f}s")
print(f"VALIDATOR_STDOUT_HASH|{result_hash}")

# Last line
last = result.stdout.strip().split('\n')[-1] if result.stdout.strip() else "EMPTY"
print(f"VALIDATOR_RESULT|{last}")
