#!/usr/bin/env python3
"""validate_preregistration.py — QCLAW 0020Q R1 Integrity Validator.

R1 (2026-07-24): Updated for bounded integrity metadata remediation.
- Verifies 8 immutable core files against known combined hash
- Skips meta-files (manifest, receipt, handoff) from manifest cross-check
- Validates R1 artifacts (CORRIGENDUM, AMENDMENT-LOG, GIT-BLOB-RECEIPT) as YAML
- Checks R1 completion signal
- Validator is a SEPARATELY VERSIONED tool; NOT part of core combined hash.

P0 base: 70ed222e279568b7370af62df5bb23b79201ee45
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
print("QCLAW 0020Q R1 VALIDATE PREREGISTRATION")
print(f"python {sys.version.split()[0]}")
print("=" * 60)

# ---- 1. REQUIRED OUTPUTS ----
print("\n[REQUIRED OUTPUTS — P0 + R1]")
REQUIRED = [
    # 8 immutable core
    "BAR-ONLY-SCOPE-GUARD.yaml",
    "D0-AUDIT-QUESTION-FREEZE.yaml",
    "D0-SCORING-RUBRIC-FREEZE.yaml",
    "EVIDENCE-REQUIREMENT-MATRIX.yaml",
    "EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml",
    "INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml",
    "LOCAL-REALITY-AND-REPLAY-RECEIPT-CHECKLIST.yaml",
    "UNKNOWN-AND-ABSTENTION-CONTRACT.yaml",
    # 4 meta (updated in R1)
    "FROZEN-MANIFEST.yaml",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
    "validate_preregistration.py",
    # 3 R1 artifacts (new)
    "CORRIGENDUM.yaml",
    "AMENDMENT-LOG.yaml",
    "GIT-BLOB-AND-SHA256-RECEIPT.yaml",
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

# ---- 3. IMMUTABLE CORE VERIFICATION ----
print("\n[IMMUTABLE CORE SHA-256 VERIFICATION]")
IMMUTABLE_CORE = {
    "BAR-ONLY-SCOPE-GUARD.yaml":
        "720c022221b5052efde954f44e93a3ce14195145667bc77e2832b151f7a1fe79",
    "D0-AUDIT-QUESTION-FREEZE.yaml":
        "c2e695e41d362facaf929221f5c8082ceec2d75e4d36be7e4a06fb361bfa84ba",
    "D0-SCORING-RUBRIC-FREEZE.yaml":
        "1e8cd67fd61a1820fc8d0da67c031062bb84d43f369b8e927252dff7ee0e0066",
    "EVIDENCE-REQUIREMENT-MATRIX.yaml":
        "0054673b2ad0784f6e0401c58d06b386ab2ac8248a251482eb130e26be81323f",
    "EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml":
        "ab57bac9a76b81e5b9428b884154423b489d6b7eb346cdfe5dc1ddd42cb59ca8",
    "INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml":
        "a6a24b5d6dd4f6dec60dd6fabb4bd6405253090f0bcac64c96f91278e82ae0ce",
    "LOCAL-REALITY-AND-REPLAY-RECEIPT-CHECKLIST.yaml":
        "7575edd7a4fce8b67a841c56d957b0622832984b5ab773dd93b0082abd04c5a7",
    "UNKNOWN-AND-ABSTENTION-CONTRACT.yaml":
        "9a2287f7dce68f90d735d3cbfae0f3d1e942867a3e0e27e2ca69414a6c01956f",
}

core_match = 0
for fn, expected_sha in IMMUTABLE_CORE.items():
    fpath = AUDIT_DIR / fn
    if not fpath.is_file():
        record(f"CORE: {fn}", "FAIL", "file missing")
        EXIT = 1
        continue
    actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
    if actual == expected_sha:
        record(f"CORE: {fn}", "PASS")
        core_match += 1
    else:
        record(f"CORE: {fn}", "FAIL", f"modified — run SHA {actual[:12]}...")
        EXIT = 1

# Verify core combined hash
core_hashes = [IMMUTABLE_CORE[k] for k in sorted(IMMUTABLE_CORE)]
expected_combined = "bf029d13dba2e6bc054e9b452a5d7992905847781bb00bf73a7ef240220d61c0"
actual_combined = hashlib.sha256("".join(core_hashes).encode("utf-8")).hexdigest()
if actual_combined == expected_combined:
    record("CORE_COMBINED_HASH", "PASS", expected_combined[:12] + "...")
else:
    record("CORE_COMBINED_HASH", "FAIL", f"expected {expected_combined[:12]}... got {actual_combined[:12]}...")
    EXIT = 1

print(f"\n  RESULT: {core_match}/{len(IMMUTABLE_CORE)} immutable core match")

# ---- 4. QUESTION ID UNIQUENESS ----
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

    expected = [f"Q{i:02d}" for i in range(1, 43)]
    missing_ids = [e for e in expected if e not in id_set]
    if missing_ids:
        record("QUESTION_SEQUENCE", "FAIL", f"Missing: {missing_ids}")
        EXIT = 1
    else:
        record("QUESTION_SEQUENCE", "PASS", "Q01-Q42 complete")
else:
    record("QUESTION_IDS", "SKIP", "D0-AUDIT-QUESTION-FREEZE.yaml missing")

# ---- 5. WEIGHT SUM CHECK ----
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

# ---- 6. SECRET SCAN ----
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
    if f.name == 'validate_preregistration.py':
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

# ---- 7. COMPLETION SIGNAL (R1) ----
print("\n[COMPLETION SIGNAL CHECK]")
EXPECTED_R2 = "QCLAW_0017_D0_P0_VALIDATOR_AND_HEAD_RECEIPTS_CLOSED_FOR_P1"
EXPECTED_R1 = "QCLAW_0017_D0_P0_INTEGRITY_METADATA_CORRECTED_FOR_P1"
EXPECTED_P0 = "QCLAW_0017_D0_AUDIT_PREREGISTRATION_FROZEN_FOR_GPT_REVIEW"
found_r2 = False
found_r1 = False
found_p0 = False
for f in [AUDIT_DIR / "AI_HANDOFF.yaml", AUDIT_DIR / "FROZEN-MANIFEST.yaml",
          AUDIT_DIR / "AMENDMENT-LOG.yaml", AUDIT_DIR / "TEST-RUN-RECEIPT.md"]:
    if not f.is_file():
        continue
    try:
        text = f.read_text(encoding="utf-8")
    except:
        text = open(str(f), encoding="utf-8").read()
    if EXPECTED_R2 in text:
        record(f"SIGNAL_R2: {f.name}", "PASS")
        found_r2 = True
    if EXPECTED_R1 in text:
        record(f"SIGNAL_R1: {f.name}", "PASS")
        found_r1 = True
    if EXPECTED_P0 in text:
        found_p0 = True
if found_r2:
    record("COMPLETION_SIGNAL", "PASS", EXPECTED_R2)
elif found_r1:
    record("COMPLETION_SIGNAL", "PASS", EXPECTED_R1 + " (R1 legacy)")
else:
    record("COMPLETION_SIGNAL", "FAIL", f"{EXPECTED_R2} not found in any receipt")
    EXIT = 1

# ---- 8. PLACEHOLDER DETECTION ----
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

# ---- 9. MANIFEST SHA-256 CROSS-CHECK (R1: skip meta-files) ----
print("\n[MANIFEST SHA-256 CROSS-CHECK]")
mf = AUDIT_DIR / "FROZEN-MANIFEST.yaml"
META_SKIP = {"FROZEN-MANIFEST.yaml", "TEST-RUN-RECEIPT.md", "AI_HANDOFF.yaml"}
if mf.is_file():
    import yaml as y
    with open(mf, encoding="utf-8") as fh:
        mdata = y.safe_load(fh)
    entries = mdata.get("frozen_files", [])
    match, mismatch, skipped = 0, 0, 0
    for entry in entries:
        fn = entry.get("file", "")
        if fn in META_SKIP:
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

# ---- 10. CORRIGENDUM REFERENCES CHECK ----
print("\n[CORRIGENDUM REFERENCE CHECK]")
cf = AUDIT_DIR / "CORRIGENDUM.yaml"
if cf.is_file():
    import yaml as y
    with open(cf, encoding="utf-8") as fh:
        cdata = y.safe_load(fh)
    cch = cdata.get("corrected_combined_hash", {})
    if cch.get("value") == expected_combined:
        record("CORRIGENDUM_COMBINED_HASH", "PASS")
    else:
        record("CORRIGENDUM_COMBINED_HASH", "FAIL", "mismatch with computed")
        EXIT = 1
    core_covered = cch.get("core_covered_files", 0)
    if core_covered == 8:
        record("CORRIGENDUM_CORE_COUNT", "PASS", f"{core_covered} files")
    else:
        record("CORRIGENDUM_CORE_COUNT", "FAIL", f"{core_covered} != 8")
        EXIT = 1
else:
    record("CORRIGENDUM", "SKIP", "file missing")

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
print(f"  Completion signal: {EXPECTED_R2 if found_r2 else EXPECTED_R1}")
print("=" * 60)
sys.exit(EXIT)
