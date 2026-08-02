# P1-VALIDATE-AUDIT.py
# QCLAW-0017-D0-INDEPENDENT-AUDIT-0020Q-P1
# Validates P1 audit package completeness

import yaml, os, sys, hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
PASS, FAIL, SKIP = 0, 0, 0

def check(desc, ok):
    global PASS, FAIL
    if ok: PASS += 1; print(f"  PASS  {desc}")
    else: FAIL += 1; print(f"  FAIL  {desc}")

def skip(desc):
    global SKIP; SKIP += 1; print(f"  SKIP  {desc}")

# 14 mandatory P1 files
MANDATORY = [
    "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml",
    "P1-BLOCKING-FAILURE-ASSESSMENT.yaml",
    "P1-DIMENSION-SCORECARD.yaml",
    "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml",
    "P1-VERDICT-AND-GPT-RECOMMENDATION.yaml",
    "P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml",
    "P1-COUNTEREVIDENCE-AND-SELF-VERIFICATION-LOOP-REPORT.md",
    "P1-UNKNOWN-ABSTENTION-AND-EVIDENCE-GAP-REPORT.yaml",
    "P1-DISCOVERED-DEFECTS-AND-AMENDMENTS.yaml",
    "P1-FROZEN-MANIFEST.yaml",
    "P1-TEST-RUN-RECEIPT.md",
    "P1-AI-HANDOFF.yaml",
    "P1-AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "P1-AMED-RESEARCH-LEDGER.yaml",
]

print("P1 Audit Validator")
print(f"Directory: {ROOT}\n")

# Check files exist
for f in MANDATORY:
    fp = os.path.join(ROOT, f)
    check(f"File exists: {f}", os.path.exists(fp))

# Parse YAML files
for f in MANDATORY:
    if not f.endswith(('.yaml', '.yml')): continue
    fp = os.path.join(ROOT, f)
    if not os.path.exists(fp): continue
    try:
        with open(fp, 'r', encoding='utf-8') as fh:
            data = yaml.safe_load(fh)
        check(f"YAML parse: {f}", isinstance(data, dict) or isinstance(data, list))
    except Exception as e:
        check(f"YAML parse: {f}", False)

# Check verdict file contains completion signal
verdict_path = os.path.join(ROOT, "P1-VERDICT-AND-GPT-RECOMMENDATION.yaml")
if os.path.exists(verdict_path):
    with open(verdict_path, 'r', encoding='utf-8') as fh:
        v = yaml.safe_load(fh)
    sig = v.get("completion_signal", "")
    check("Verdict has completion_signal", 
          "QCLAW_0017_D0_P1_INDEPENDENT_FROZEN_INSTRUMENT_AUDIT_READY_FOR_GPT_REVIEW" in sig)

# Check scorecard has all 10 dimensions
sc_path = os.path.join(ROOT, "P1-DIMENSION-SCORECARD.yaml")
if os.path.exists(sc_path):
    with open(sc_path, 'r', encoding='utf-8') as fh:
        sc = yaml.safe_load(fh)
    dims = [k for k in sc.keys() if k.startswith("D") and "_" in k]
    check(f"Scorecard has all dimensions (found {len(dims)})", len(dims) >= 10)
    check("Scorecard has composite section", "composite" in sc)

# Check blocking assessment has all 4 modes
ba_path = os.path.join(ROOT, "P1-BLOCKING-FAILURE-ASSESSMENT.yaml")
if os.path.exists(ba_path):
    with open(ba_path, 'r', encoding='utf-8') as fh:
        ba = yaml.safe_load(fh)
    modes = ["BAR_ONLY_VIOLATION", "SELF_VERIFICATION_LOOP", "LOOK_AHEAD_LEAKAGE", "MISSING_MANDATORY_OBJECT"]
    for m in modes:
        check(f"Blocking mode assessed: {m}", m in ba)

# Check evidence map has 42 questions
ev_path = os.path.join(ROOT, "P1-QUESTION-BY-QUESTION-EVIDENCE-MAP.yaml")
if os.path.exists(ev_path):
    with open(ev_path, 'r', encoding='utf-8') as fh:
        ev = yaml.safe_load(fh)
    qs = ev.get("questions", {})
    qids = [k for k in qs.keys() if k.startswith("Q")]
    check(f"Evidence map has questions (found {len(qids)})", len(qids) >= 42)

# Check identity receipt
id_path = os.path.join(ROOT, "P1-AUDIT-IDENTITY-AND-INDEPENDENCE-RECEIPT.yaml")
if os.path.exists(id_path):
    with open(id_path, 'r', encoding='utf-8') as fh:
        idr = yaml.safe_load(fh)
    check("Identity receipt: role_class TEMPORARY_BORROW",
          idr.get("role_class") == "TEMPORARY_BORROW")
    check("Identity receipt: boundary PUBLIC_SAFE/CANDIDATE_ONLY/NO_TRADE",
          "NO_TRADE" in idr.get("boundary", ""))

# Check BAR_ONLY review has all SV checks
bar_path = os.path.join(ROOT, "P1-BAR-ONLY-PIT-RULE-AND-LOCAL-REALITY-REVIEW.yaml")
if os.path.exists(bar_path):
    with open(bar_path, 'r', encoding='utf-8') as fh:
        b = yaml.safe_load(fh)
    sv = b.get("scope_violation_scan", {})
    sv_keys = [k for k in sv.keys() if k.startswith("SV-")]
    check(f"BAR_ONLY has SV checks (found {len(sv_keys)})", len(sv_keys) >= 8)

# COMBINED hash of all P1 files
hasher = hashlib.sha256()
files = sorted([f for f in MANDATORY if os.path.exists(os.path.join(ROOT, f))])
for f in files:
    with open(os.path.join(ROOT, f), 'rb') as fh:
        hasher.update(fh.read())
combined = hasher.hexdigest()
print(f"\nCombined SHA-256: {combined}")
print(f"Files hashed: {len(files)}")

print(f"\nResults: {PASS} PASS / {FAIL} FAIL / {SKIP} SKIP")
sys.exit(0 if FAIL == 0 else 1)
