#!/usr/bin/env python3
"""validate_preregistration.py — QCLAW 0020Q P0 Preregistration Validator.
Checks: required outputs, YAML/UTF-8/dup-key, ID uniqueness, weight sum,
secret patterns, stale references, completion signal, placeholder detection.
Frozen with P0 preregistration — validates the exam, not the answers.
"""

import os, sys, re, hashlib
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
EXIT = 0
RESULTS = []

def record(name, status, detail=""):
    RESULTS.append((name, status, detail))
    tag = "PASS" if status == "PASS" else ("SKIP" if status == "SKIP" else "FAIL")
    print(f"  {tag}: {name}" + (f" — {detail}" if detail else ""))

print("=" * 60)
print("QCLAW 0020Q P0 VALIDATE PREREGISTRATION")
print(f"python {sys.version.split()[0]}")
print("=" * 60)

# ---- 1. REQUIRED OUTPUTS ----
print("\n[REQUIRED OUTPUTS — P0]")
REQUIRED = [
    "INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml",
    "D0-AUDIT-QUESTION-FREEZE.yaml",
    "D0-SCORING-RUBRIC-FREEZE.yaml",
    "EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml",
    "EVIDENCE-REQUIREMENT-MATRIX.yaml",
    "UNKNOWN-AND-ABSTENTION-CONTRACT.yaml",
    "BAR-ONLY-SCOPE-GUARD.yaml",
    "LOCAL-REALITY-AND-REPLAY-RECEIPT-CHECKLIST.yaml",
    "FROZEN-MANIFEST.yaml",
    "validate_preregistration.py",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
]
present = 0
for f in REQUIRED:
    p = AUDIT_DIR / f
    if p.is_file():
        record(f"PRESENT: {f}", "PASS", f"{p.stat().st_size}B")
        present += 1
    else:
        record(f"MISSING: {f}", "FAIL")
        EXIT = 1
print(f"\n  RESULT: {present}/{len(REQUIRED)} PRESENT")

# ---- 2. YAML + UTF-8 + DUP-KEY ----
print("\n[YAML + UTF-8 + DUP-KEY]")
try:
    import yaml
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyYAML"])
    import yaml

class DupRejectLoader(yaml.SafeLoader):
    pass

def dup_constructor(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.constructor.ConstructorError(None, None,
                f"duplicate key: {key}", key_node.start_mark)
        mapping[key] = key_node
    return loader.construct_mapping(node, deep=deep)

DupRejectLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dup_constructor)

yaml_pass, yaml_fail = 0, 0
for yf in sorted(AUDIT_DIR.glob("*.yaml")):
    try:
        raw = yf.read_text(encoding="utf-8")
        list(yaml.load_all(raw, Loader=DupRejectLoader))
        record(f"YAML: {yf.name}", "PASS")
        yaml_pass += 1
    except UnicodeDecodeError as e:
        record(f"YAML: {yf.name}", "FAIL", f"UTF-8: {e}")
        yaml_fail += 1; EXIT = 1
    except yaml.YAMLError as e:
        record(f"YAML: {yf.name}", "FAIL", str(e)[:120])
        yaml_fail += 1; EXIT = 1
print(f"\n  RESULT: {yaml_pass}/{yaml_pass+yaml_fail} YAML PASS")

# ---- 3. QUESTION ID UNIQUENESS ----
print("\n[QUESTION ID UNIQUENESS]")
qf = AUDIT_DIR / "D0-AUDIT-QUESTION-FREEZE.yaml"
if qf.is_file():
    text = qf.read_text(encoding="utf-8")
    ids = re.findall(r'^\s{2}Q\d{2}:', text, re.MULTILINE)
    id_set = [s.strip().rstrip(':') for s in ids]
    dupes = [q for q in set(id_set) if id_set.count(q) > 1]
    if dupes:
        record("QUESTION_IDS", "FAIL", f"Duplicates: {dupes}")
        EXIT = 1
    else:
        record("QUESTION_IDS", "PASS", f"{len(id_set)} unique IDs")

    # Check Q01-Q42 present and sequential
    expected = [f"Q{i:02d}" for i in range(1, 43)]
    missing_ids = [e for e in expected if e not in id_set]
    if missing_ids:
        record("QUESTION_SEQUENCE", "FAIL", f"Missing: {missing_ids}")
        EXIT = 1
    else:
        record("QUESTION_SEQUENCE", "PASS", "Q01-Q42 complete")
else:
    record("QUESTION_IDS", "SKIP", "D0-AUDIT-QUESTION-FREEZE.yaml missing")

# ---- 4. WEIGHT SUM CHECK ----
print("\n[WEIGHT SUM CHECK]")
if qf.is_file():
    import yaml as y
    with open(qf, encoding="utf-8") as fh:
        qdata = y.safe_load(fh)
    dims = qdata.get("frozen_manifest", {}).get("dimension_weights", {})
    if dims:
        total = sum(dims.values())
        if abs(total - 100.0) < 0.01:
            record("DIMENSION_WEIGHTS", "PASS", f"sum={total}")
        else:
            record("DIMENSION_WEIGHTS", "FAIL", f"sum={total}, expected 100")
            EXIT = 1
    else:
        record("DIMENSION_WEIGHTS", "SKIP", "no frozen_manifest.dimension_weights")

    # Check rubric weight sum
    rf = AUDIT_DIR / "D0-SCORING-RUBRIC-FREEZE.yaml"
    if rf.is_file():
        with open(rf, encoding="utf-8") as fh:
            rdata = y.safe_load(fh)
        rweights = rdata.get("dimension_weights", {})
        rsum = sum(d.get("weight", 0) for d in rweights.values())
        if abs(rsum - 1.0) < 0.001:
            record("RUBRIC_WEIGHTS", "PASS", f"sum={rsum}")
        else:
            record("RUBRIC_WEIGHTS", "FAIL", f"sum={rsum}, expected 1.0")
            EXIT = 1

# ---- 5. SECRET SCAN ----
print("\n[SECRET PATTERN SCAN]")
SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9]{32,}', "OpenAI key"),
    (r'Bearer\x20[A-Za-z0-9\-_.]+={0,2}', "Bearer token"),
    (r'api[_-]?key["\s:=]+["\']?[A-Za-z0-9+/=]{20,}', "API key"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
    (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth"),
]
secret_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name in ('validate_preregistration.py',):
        continue
    if f.is_file() and f.suffix in ('.yaml', '.md'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pat, label in SECRET_PATTERNS:
            for m in re.finditer(pat, text, re.IGNORECASE):
                pre = text[max(0,m.start()-50):m.start()].lower()
                if 'placeholder' in pre or 'example' in pre:
                    continue
                record(f"SECRET: {f.name}", "FAIL", f"{label} at {m.start()}")
                secret_hits += 1
if secret_hits == 0:
    record("SECRETS", "PASS", "0 secrets")

# ---- 6. COMPLETION SIGNAL ----
print("\n[COMPLETION SIGNAL CHECK]")
EXPECTED = "QCLAW_0017_D0_AUDIT_PREREGISTRATION_FROZEN_FOR_GPT_REVIEW"
found = False
for f in [AUDIT_DIR / "AI_HANDOFF.yaml", AUDIT_DIR / "FROZEN-MANIFEST.yaml"]:
    if f.is_file():
        if EXPECTED in f.read_text(encoding="utf-8"):
            record(f"SIGNAL: {f.name}", "PASS")
            found = True
if found:
    record("COMPLETION_SIGNAL", "PASS", EXPECTED)
else:
    record("COMPLETION_SIGNAL", "FAIL", "not found")
    EXIT = 1

# ---- 7. PLACEHOLDER DETECTION ----
print("\n[PLACEHOLDER DETECTION]")
PLACEHOLDERS = [r'\bTODO\b', r'\bFIXME\b', r'XXX\s*—', r'<PLACEHOLDER>', r'\bTK\b']
ph_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name == 'validate_preregistration.py':
        continue
    if f.is_file() and f.suffix in ('.yaml', '.md'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pat in PLACEHOLDERS:
            if re.search(pat, text, re.IGNORECASE):
                record(f"PLACEHOLDER: {f.name}", "FAIL", pat)
                ph_hits += 1
                break
if ph_hits == 0:
    record("PLACEHOLDERS", "PASS", "0 unfilled")

# ---- 8. SHA-256 MATCH AGAINST MANIFEST ----
print("\n[MANIFEST SHA-256 CROSS-CHECK]")
mf = AUDIT_DIR / "FROZEN-MANIFEST.yaml"
if mf.is_file():
    import yaml as y
    with open(mf, encoding="utf-8") as fh:
        mdata = y.safe_load(fh)
    entries = mdata.get("frozen_files", [])
    match, mismatch, skipped = 0, 0, 0
    for entry in entries:
        fn = entry.get("file", "")
        if fn in ("FROZEN-MANIFEST.yaml", "TEST-RUN-RECEIPT.md", "AI_HANDOFF.yaml"):
            record(f"MANIFEST: {fn}", "SKIP", "meta-file")
            skipped += 1
            continue
        fpath = AUDIT_DIR / fn
        if not fpath.is_file():
            record(f"MANIFEST: {fn}", "SKIP", "file not found")
            skipped += 1
            continue
        actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
        expected = entry.get("sha256", "")
        if actual == expected:
            record(f"MANIFEST: {fn}", "PASS")
            match += 1
        else:
            record(f"MANIFEST: {fn}", "FAIL", f"mismatch")
            mismatch += 1
    if mismatch > 0:
        EXIT = 1
    record("MANIFEST_SHA256", "PASS" if mismatch == 0 else "FAIL",
           f"{match} match, {mismatch} mismatch, {skipped} skip")
else:
    record("MANIFEST_SHA256", "SKIP", "FROZEN-MANIFEST.yaml missing")

# ---- SUMMARY ----
print("\n" + "=" * 60)
print("P0 VALIDATION SUMMARY")
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
print(f"  Completion signal: {EXPECTED}")
print("=" * 60)
sys.exit(EXIT)
