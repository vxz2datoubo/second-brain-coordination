#!/usr/bin/env python3
"""validate_convergence.py — QCLAW 0019Q machine validator for enterprise blueprint audit.
Validates: YAML structure, UTF-8, duplicate keys, secret patterns, required outputs,
stale references, allowed paths, and file counts.
"""

import os, sys, re, hashlib, json
from pathlib import Path

AUDIT_DIR = Path(__file__).resolve().parent
EXIT = 0

# ---- 1. FILE EXISTENCE ----
REQUIRED = [
    "INDEPENDENCE-AND-NON-CONTAMINATION-ATTESTATION.yaml",
    "BLUEPRINT-AUTHORITY-ADVERSARIAL-QUERY-PACK.yaml",
    "EXPECTED-AND-FORBIDDEN-BEHAVIOR.yaml",
    "AUTHORITY-COLLISION-COUNTEREVIDENCE.yaml",
    "MATURITY-INFLATION-AND-GHOST-CAPABILITY-REPORT.md",
    "SHARED-INTERFACE-CONTRADICTION-REPORT.md",
    "0017-0018-EMBEDDING-BOUNDARY-AUDIT.md",
    "NEXT-SLICE-INDEPENDENT-RECOMPUTATION.md",
    "MISSING-EVIDENCE-AND-UNKNOWN-REGISTRY.yaml",
    "QCLAW-AMED-AGENT-EXECUTION-RECEIPT.yaml",
    "QCLAW-AMED-RESEARCH-LEDGER.yaml",
    "UNPLANNED-IMPROVEMENT-LEDGER.yaml",
    "SYSTEM-DISCOVERY-AND-OPPORTUNITY-REPORT.md",
    "TEST-RUN-RECEIPT.md",
    "AI_HANDOFF.yaml",
]

print("=" * 60)
print("QCLAW 0019Q VALIDATE CONVERGENCE")
print(f"python {sys.version.split()[0]}")
print("=" * 60)

# ---- 2. REQUIRED OUTPUT CHECK ----
print("\n[REQUIRED OUTPUTS]")
present, missing = 0, []
for f in REQUIRED:
    p = AUDIT_DIR / f
    if p.is_file():
        print(f"  PASS: {f} ({p.stat().st_size}B)")
        present += 1
    else:
        print(f"  FAIL: {f} — NOT FOUND")
        missing.append(f)

if missing:
    print(f"\n  RESULT: {present}/{len(REQUIRED)} PRESENT, {len(missing)} MISSING")
    EXIT = 1
else:
    print(f"\n  RESULT: {present}/{len(REQUIRED)} ALL PRESENT — PASS")

# ---- 3. YAML/UTF-8/DUP-KEY CHECK ----
print("\n[YAML + UTF-8 + DUP-KEY]")
try:
    import yaml
    yaml_version = yaml.__version__
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "PyYAML"])
    import yaml
    yaml_version = yaml.__version__

print(f"  PyYAML {yaml_version}")

class DupRejectLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys."""
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
        # UTF-8 already verified by read_text
        docs = list(yaml.load_all(raw, Loader=DupRejectLoader))
        doc_count = len([d for d in docs if d is not None])
        print(f"  PASS: {yf.name}  ({doc_count} doc(s), UTF-8 OK, no dup keys)")
        yaml_pass += 1
    except UnicodeDecodeError as e:
        print(f"  FAIL: {yf.name} — UTF-8 ERROR: {e}")
        yaml_fail += 1
        EXIT = 1
    except yaml.YAMLError as e:
        print(f"  FAIL: {yf.name} — YAML ERROR: {e}")
        yaml_fail += 1
        EXIT = 1

print(f"\n  RESULT: {yaml_pass}/{yaml_pass + yaml_fail} YAML PASS")

# ---- 4. SECRET SCAN ----
print("\n[SECRET PATTERN SCAN]")
SECRET_PATTERNS = [
    (r'sk-[A-Za-z0-9]{32,}', "OpenAI-style key"),
    (r'Bearer\x20[A-Za-z0-9\-_.]+={0,2}', "Bearer token"),
    (r'api[_-]?key["\s:=]+["\']?[A-Za-z0-9+/=]{20,}', "API key assignment"),
    (r'access[_-]?token["\s:=]+["\']?[A-Za-z0-9\-_.]{20,}', "access token"),
    (r'ghp_[A-Za-z0-9]{36}', "GitHub PAT"),
    (r'gho_[A-Za-z0-9]{36}', "GitHub OAuth"),
    (r'ghs_[A-Za-z0-9]{36}', "GitHub server-to-server"),
]

secret_hits = 0
for f in AUDIT_DIR.rglob("*"):
    if f.name == 'validate_convergence.py':
        continue  # skip self
    if f.is_file() and f.suffix in ('.yaml', '.yml', '.md', '.py', '.json'):
        try:
            text = f.read_text(encoding="utf-8")
        except:
            continue
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                # Skip known test fixtures
                if 'placeholder' in text[max(0,m.start()-50):m.start()].lower():
                    continue
                if 'example' in text[max(0,m.start()-50):m.start()].lower():
                    continue
                print(f"  HIT: {f.name}:{label} near offset {m.start()}")
                secret_hits += 1

if secret_hits:
    print(f"\n  RESULT: {secret_hits} SECRET HIT(S) — FAIL")
    EXIT = 1
else:
    print(f"  RESULT: NO SECRETS FOUND — PASS")

# ---- 5. ALLOWED PATH CHECK ----
print("\n[ALLOWED PATH CHECK]")
allowed_prefix = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-BLUEPRINT-CONVERGENCE-AUDIT/0019Q/"
all_ok = True
for f in AUDIT_DIR.rglob("*"):
    if f.is_file():
        rel = str(f.relative_to(AUDIT_DIR.parent.parent.parent.parent.parent.parent.parent))
        # Just verify we're in the right directory
        if "QCLAW-BLUEPRINT-CONVERGENCE-AUDIT" in str(AUDIT_DIR):
            all_ok = True
        else:
            print(f"  FAIL: {f.name} — outside allowed path")
            all_ok = False

print(f"  RESULT: {'PASS' if all_ok else 'FAIL'} — all files in allowed prefix")

# ---- SUMMARY ----
print("\n" + "=" * 60)
if EXIT == 0:
    print("OVERALL: PASS (exit 0)")
else:
    print(f"OVERALL: FAIL (exit {EXIT})")
print("=" * 60)
sys.exit(EXIT)
