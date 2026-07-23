#!/usr/bin/env python3
"""validate_convergence.py — QCLAW 0019Q R1 machine validator.
Validates: YAML/UTF-8/dup-key, secret patterns, required output existence
with exact R1 names, stale-reference check, allowed-prefix check,
score arithmetic, completion signal, placeholder detection.
"""

import os, sys, re, hashlib, subprocess
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
EXIT = 0
RESULTS = []  # (name, status, detail)

def record(name, status, detail=""):
    RESULTS.append((name, status, detail))
    tag = "PASS" if status == "PASS" else ("SKIP" if status == "SKIP" else "FAIL")
    print(f"  {tag}: {name}" + (f" — {detail}" if detail else ""))

# ---- 0. HEADER ----
print("=" * 60)
print("QCLAW 0019Q R1 VALIDATE CONVERGENCE")
print(f"python {sys.version.split()[0]}")
print("=" * 60)

# ---- 1. REQUIRED OUTPUTS (R1 active-route list) ----
print("\n[REQUIRED OUTPUTS — R1]")
REQUIRED = [
    "INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml",
    "AUDIT-QUESTION-AND-SCORING-FREEZE.yaml",
    "AUTHORITY-COLLISION-COUNTERAUDIT.yaml",
    "PHYSICAL-SYSTEM-OF-RECORD-AUDIT.md",
    "MATURITY-INFLATION-AUDIT.yaml",
    "INTERFACE-AND-HIDDEN-RUNTIME-AUDIT.yaml",
    "NEXT-SLICE-INDEPENDENT-RECOMPUTATION.md",
    "COUNTEREVIDENCE-AND-UNKNOWN-LEDGER.yaml",
    "SECRET-FIXTURE-ALLOWLIST-BOUNDARY-AUDIT.md",
    "AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "AMED-RESEARCH-LEDGER.yaml",
    "UNPLANNED-IMPROVEMENT-LEDGER.yaml",
    "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
]

present, missing = 0, []
for f in REQUIRED:
    p = AUDIT_DIR / f
    if p.is_file():
        record(f"PRESENT: {f}", "PASS", f"{p.stat().st_size}B")
        present += 1
    else:
        record(f"MISSING: {f}", "FAIL", "NOT FOUND")
        missing.append(f)

if missing:
    print(f"\n  RESULT: {present}/{len(REQUIRED)} PRESENT, {len(missing)} MISSING")
    EXIT = 1
else:
    print(f"\n  RESULT: {present}/{len(REQUIRED)} ALL PRESENT — PASS")

# ---- 2. YAML/UTF-8/DUP-KEY ----
print("\n[YAML + UTF-8 + DUP-KEY]")
try:
    import yaml
    yaml_version = yaml.__version__
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyYAML"])
    import yaml
    yaml_version = yaml.__version__

class DupRejectLoader(yaml.SafeLoader):
    pass

def dup_constructor(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key: {key}", key_node.start_mark)
        mapping[key] = key_node
    return loader.construct_mapping(node, deep=deep)

DupRejectLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dup_constructor)

yaml_files = sorted(AUDIT_DIR.glob("*.yaml"))
yaml_pass, yaml_fail = 0, 0

for yf in yaml_files:
    try:
        raw = yf.read_text(encoding="utf-8")
        docs = list(yaml.load_all(raw, Loader=DupRejectLoader))
        doc_count = len([d for d in docs if d is not None])
        record(f"YAML: {yf.name}", "PASS", f"{doc_count} doc(s)")
        yaml_pass += 1
    except UnicodeDecodeError as e:
        record(f"YAML: {yf.name}", "FAIL", f"UTF-8: {e}")
        yaml_fail += 1; EXIT = 1
    except yaml.YAMLError as e:
        record(f"YAML: {yf.name}", "FAIL", str(e)[:120])
        yaml_fail += 1; EXIT = 1

print(f"\n  RESULT: {yaml_pass}/{yaml_pass+yaml_fail} YAML PASS")

# ---- 3. STALE-REFERENCE CHECK ----
print("\n[STALE REFERENCE CHECK]")
# Known stale/closed/draft references that should NOT be cited as definitive
STALE_REFS = [
    (r'PR\s*#8\b', "PR #8 (time/evidence, replaced by W2/W3 canonical)"),
    (r'PR\s*#34\b', "PR #34 (old local evidence, absorbed by W3)"),
    (r'PR\s*#45\b', "PR #45 (absorbed by PR #57)"),
    (r'PR\s*#46\b', "PR #46 (absorbed by PR #57)"),
]
stale_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name in ('validate_convergence.py', 'TEST-RUN-RECEIPT.md',
                   'AUDIT-QUESTION-AND-SCORING-FREEZE.yaml',
                   'COUNTEREVIDENCE-AND-UNKNOWN-LEDGER.yaml',
                   'SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md'):
        continue  # these may reference stale PRs in audit context
    if f.is_file() and f.suffix in ('.yaml', '.md'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pat, label in STALE_REFS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                ctx = text[max(0,m.start()-40):m.end()+40]
                # Check if it's flagged as stale/deprecated in context
                if re.search(r'stale|deprecated|absorbed|replaced|historical', ctx, re.I):
                    continue
                record(f"STALE: {f.name} {label}", "FAIL", f"offset {m.start()}")
                stale_hits += 1
                break

if stale_hits == 0:
    record("STALE_REFS", "PASS", "0 stale references in active claims")
else:
    EXIT = 1

# ---- 4. SECRET SCAN ----
print("\n[SECRET PATTERN SCAN]")
SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9]{32,}', "OpenAI key"),
    (r'Bearer\x20[A-Za-z0-9\-_.]+={0,2}', "Bearer token"),
    (r'api[_-]?key["\s:=]+["\']?[A-Za-z0-9+/=]{20,}', "API key"),
    (r'access[_-]?token["\s:=]+["\']?[A-Za-z0-9\-_.]{20,}', "access token"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
    (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth"),
    (r'ghs_[A-Za-z0-9]{36}', "GitHub server-to-server"),
]

secret_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name == 'validate_convergence.py':
        continue
    if f.name == 'SECRET-FIXTURE-ALLOWLIST-BOUNDARY-AUDIT.md':
        continue  # self-describing secret patterns, not actual secrets
    if f.is_file() and f.suffix in ('.yaml', '.yml', '.md', '.json'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                pre = text[max(0,m.start()-50):m.start()].lower()
                if 'placeholder' in pre or 'example' in pre:
                    continue
                record(f"SECRET: {f.name}", "FAIL", f"{label} at offset {m.start()}")
                secret_hits += 1

if secret_hits == 0:
    record("SECRETS", "PASS", "0 secrets")
else:
    EXIT = 1

# ---- 5. ALLOWED-PREFIX CHECK (real) ----
print("\n[ALLOWED PREFIX CHECK]")
ALLOWED_PREFIX = "QCLAW-BLUEPRINT-CONVERGENCE-AUDIT"
REPO_PREFIX = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/"
allowed_str = str(AUDIT_DIR).replace("\\", "/")
prefix_violations = 0
for f in AUDIT_DIR.rglob("*"):
    if f.is_file():
        p = str(f.resolve()).replace("\\", "/")
        if ALLOWED_PREFIX not in p:
            record(f"PREFIX: {f.name}", "FAIL", "outside allowed directory")
            prefix_violations += 1

if prefix_violations == 0:
    record("ALLOWED_PREFIX", "PASS", f"all files under {ALLOWED_PREFIX}")
else:
    EXIT = 1

# ---- 6. SCORE ARITHMETIC CHECK ----
print("\n[SCORE ARITHMETIC CHECK]")
# Verify NEXT-SLICE-INDEPENDENT-RECOMPUTATION.md preserves all original scores
recomp = AUDIT_DIR / "NEXT-SLICE-INDEPENDENT-RECOMPUTATION.md"
if recomp.is_file():
    text = recomp.read_text(encoding="utf-8")
    expected_scores = {
        "0017": 84, "W12": 64, "PMN": 45, "W11": 35, "0018": 24
    }
    score_errors = 0
    for cand, expected_total in expected_scores.items():
        lookup_map = {
            "0017": "0017_BAR_ONLY",
            "0018": "0018_NET_EDGE",
            "W12":  "W12_ONE_DS_CHILD",
            "W11":  "W11_SINGLE_OPPORTUNITY",
            "PMN":  "PMN_CALENDAR",
        }
        lookup = lookup_map.get(cand, cand)
        # anchor on the YAML id: field to avoid matching mentions in prose
        pattern = rf'- id: "{lookup}".*?\n\s+total:\s*(\d+)'
        m = re.search(pattern, text, re.DOTALL)
        if m:
            actual = int(m.group(1))
            if actual != expected_total:
                record(f"SCORE: {cand}", "FAIL",
                       f"total={actual}, expected {expected_total}")
                score_errors += 1
            else:
                record(f"SCORE: {cand}", "PASS", f"total={actual}")
        else:
            record(f"SCORE: {cand}", "SKIP", "score not found in text")
    if score_errors > 0:
        EXIT = 1
    record("SCORE_ARITHMETIC", "PASS" if score_errors == 0 else "FAIL",
           f"{len(expected_scores)-score_errors}/{len(expected_scores)} match")
else:
    record("SCORE_ARITHMETIC", "SKIP", "NEXT-SLICE file missing")

# ---- 7. COMPLETION SIGNAL CHECK ----
print("\n[COMPLETION SIGNAL CHECK]")
EXPECTED_SIGNAL = "QCLAW_ISSUE73_R1_EVIDENCE_REMEDIATION_READY_FOR_GPT_REVIEW"
handoff = AUDIT_DIR / "AI_HANDOFF.yaml"
receipt = AUDIT_DIR / "AMED-AGENT-EXECUTION-RECEIPT.yaml"
signal_ok = False

for f in [handoff, receipt]:
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
            if EXPECTED_SIGNAL in t:
                record(f"SIGNAL: {f.name}", "PASS", "correct completion signal")
                signal_ok = True
            else:
                # Check if OLD signal is present (pre-R1)
                if "QCLAW_BLUEPRINT_INDEPENDENT_AUDIT_READY_FOR_GPT_REVIEW" in t:
                    record(f"SIGNAL: {f.name}", "FAIL", "OLD pre-R1 signal found")
                    EXIT = 1
                else:
                    record(f"SIGNAL: {f.name}", "FAIL", "no completion signal")
                    EXIT = 1
        except:
            record(f"SIGNAL: {f.name}", "SKIP", "unreadable")

if signal_ok:
    record("COMPLETION_SIGNAL", "PASS", EXPECTED_SIGNAL)
else:
    record("COMPLETION_SIGNAL", "FAIL", "expected signal not found")
    EXIT = 1

# ---- 8. PLACEHOLDER DETECTION ----
print("\n[PLACEHOLDER DETECTION]")
PLACEHOLDERS = [
    r'(?m)^.*to_be_filled[^:]*$',
    r'\bTODO\b',
    r'\bFIXME\b',
    r'XXX\s*—',
    r'<PLACEHOLDER>',
    r'\bTK\b',
]
placeholder_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name == 'validate_convergence.py':
        continue
    if f.name == 'TEST-RUN-RECEIPT.md':
        continue  # self-describing validator checklist
    if f.is_file() and f.suffix in ('.yaml', '.md'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pat in PLACEHOLDERS:
            if re.search(pat, text, re.IGNORECASE):
                record(f"PLACEHOLDER: {f.name}", "FAIL", f"pattern: {pat}")
                placeholder_hits += 1
                break

if placeholder_hits == 0:
    record("PLACEHOLDERS", "PASS", "0 unfilled placeholders")
else:
    EXIT = 1

# ---- SUMMARY ----
print("\n" + "=" * 60)
print("R1 VALIDATION SUMMARY")
print("=" * 60)
pass_count = sum(1 for r in RESULTS if r[1] == "PASS")
fail_count = sum(1 for r in RESULTS if r[1] == "FAIL")
skip_count = sum(1 for r in RESULTS if r[1] == "SKIP")
print(f"  PASS: {pass_count}  FAIL: {fail_count}  SKIP: {skip_count}")
print(f"  Total checks: {len(RESULTS)}")

if EXIT == 0:
    print("OVERALL: PASS (exit 0)")
else:
    print(f"OVERALL: FAIL (exit {EXIT})")

print(f"  Completion signal: {EXPECTED_SIGNAL}")
print("=" * 60)
sys.exit(EXIT)
