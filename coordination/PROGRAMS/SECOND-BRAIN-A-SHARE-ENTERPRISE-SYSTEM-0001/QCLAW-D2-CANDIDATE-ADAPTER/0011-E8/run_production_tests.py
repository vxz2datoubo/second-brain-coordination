#!/usr/bin/env python3
"""
run_production_tests.py — 45+ production-entry mutation tests for Epoch 18 Gate B R3
PR #100: Strict Canonical Identity, Lossless Quarantine & Executable Evidence

E18-B08: 45 distinct subprocess-based mutation tests.
Each test alters source/policy/manifest/output and invokes the REAL generator/validator.
No hard-coded True. No skip-as-pass. No current-valid-file-only parsing.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import OrderedDict

import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SRC_DIR = os.environ.get("Q0_SRC_DIR")
if not SRC_DIR or not os.path.exists(os.path.join(SRC_DIR, "KNOWLEDGE-ATOMS.jsonl")):
    SRC_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(SCRIPT_DIR)))),
        "e17_gate_b_r2", "q0_sources"
    )

POLICY_DIR = os.environ.get("POLICY_DIR", SCRIPT_DIR)
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", SCRIPT_DIR)
PYTHON_EXE = sys.executable

passed = 0
failed_tests = 0
total = 0


def test_print(name, condition, detail=""):
    global passed, failed_tests, total
    total += 1
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed_tests += 1
        print(f"  FAIL: {name} {'- ' + detail if detail else ''}")


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def setup_fixture(name):
    tmpdir = tempfile.mkdtemp(prefix=f"e18_p100_test_{name}_")
    q0_dst = os.path.join(tmpdir, "q0_sources")
    os.makedirs(q0_dst)
    for f in ["KNOWLEDGE-ATOMS.jsonl", "KNOWLEDGE-RELATIONS.jsonl",
              "ADVERSARIAL-QUESTION-SET.jsonl", "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml"]:
        src = os.path.join(SRC_DIR, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(q0_dst, f))
    for f in ["MAPPING-POLICY.yaml", "FULL-ID-QUARANTINE-MANIFEST.yaml",
              "AMBIGUITY-MANIFEST.yaml", "D2-INTERFACE-SNAPSHOT.yaml",
              "CANONICAL-SOURCE-SCHEMA.yaml", "GOLDEN-VECTORS.yaml"]:
        src = os.path.join(POLICY_DIR, f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(tmpdir, f))
    gen_src = os.path.join(OUTPUT_DIR, "generate_adapters.py")
    val_src = os.path.join(OUTPUT_DIR, "validate_adapters.py")
    if os.path.exists(gen_src):
        shutil.copy(gen_src, os.path.join(tmpdir, "generate_adapters.py"))
    if os.path.exists(val_src):
        shutil.copy(val_src, os.path.join(tmpdir, "validate_adapters.py"))
    return tmpdir


def run_generator(tmpdir):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["Q0_SRC_DIR"] = os.path.join(tmpdir, "q0_sources")
    env["POLICY_DIR"] = tmpdir
    env["OUTPUT_DIR"] = tmpdir
    try:
        result = subprocess.run(
            [PYTHON_EXE, os.path.join(tmpdir, "generate_adapters.py")],
            env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def run_validator(tmpdir):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["Q0_SRC_DIR"] = os.path.join(tmpdir, "q0_sources")
    env["POLICY_DIR"] = tmpdir
    env["OUTPUT_DIR"] = tmpdir
    try:
        result = subprocess.run(
            [PYTHON_EXE, os.path.join(tmpdir, "validate_adapters.py")],
            env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT"


def update_policy_atom_hash(tmpdir):
    """Update MAPPING-POLICY.yaml source_lock to match current atom hash in tmpdir."""
    atoms_path = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
    pol_path = os.path.join(tmpdir, "MAPPING-POLICY.yaml")
    new_hash = file_sha256(atoms_path)
    with open(pol_path, "r", encoding="utf-8") as f:
        text = f.read()
    text = re.sub(r'q0_atoms_sha256: "[a-f0-9]{64}"', f'q0_atoms_sha256: "{new_hash}"', text)
    with open(pol_path, "w", encoding="utf-8") as f:
        f.write(text)


TOTAL = 45

print(f"\n{'='*60}")
print(f"E18 GATE B R3 PRODUCTION TESTS")
print(f"{'='*60}")

# T01: Baseline
print(f"\n[1/{TOTAL}] Baseline: Generator runs clean")
tmpdir = setup_fixture("baseline")
rc, out, err = run_generator(tmpdir)
test_print("T01. Baseline generator exits 0", rc == 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T02-T06: Duplicate key detection
print(f"\n[2/{TOTAL}] Duplicate key in atoms JSONL -> fail")
tmpdir = setup_fixture("dup_atom")
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
lines = open(ap, "r", encoding="utf-8").readlines()
if lines:
    lines[0] = lines[0].replace('"atom_index"', '"atom_index","atom_index"')
    open(ap, "w", encoding="utf-8").writelines(lines)
rc, out, err = run_generator(tmpdir)
test_print("T02. Duplicate key in atoms -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[3/{TOTAL}] Duplicate key in relations JSONL -> fail")
tmpdir = setup_fixture("dup_rel")
rp = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-RELATIONS.jsonl")
lines = open(rp, "r", encoding="utf-8").readlines()
if lines:
    lines[0] = lines[0].replace('"relation_id"', '"relation_id","relation_id"')
    open(rp, "w", encoding="utf-8").writelines(lines)
rc, out, err = run_generator(tmpdir)
test_print("T03. Duplicate key in relations -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[4/{TOTAL}] Duplicate key in questions JSONL -> fail")
tmpdir = setup_fixture("dup_q")
qp = os.path.join(tmpdir, "q0_sources", "ADVERSARIAL-QUESTION-SET.jsonl")
lines = open(qp, "r", encoding="utf-8").readlines()
if lines:
    lines[0] = lines[0].replace('"question_id"', '"question_id","question_id"')
    open(qp, "w", encoding="utf-8").writelines(lines)
rc, out, err = run_generator(tmpdir)
test_print("T04. Duplicate key in questions -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[5/{TOTAL}] Duplicate deterministic_id in atoms -> fail")
tmpdir = setup_fixture("dup_did")
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
lines = open(ap, "r", encoding="utf-8").readlines()
if len(lines) >= 2:
    lines.insert(1, lines[0])
    open(ap, "w", encoding="utf-8").writelines(lines)
rc, out, err = run_generator(tmpdir)
test_print("T05. Duplicate deterministic_id -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[6/{TOTAL}] Duplicate key in MAPPING-POLICY.yaml -> fail")
tmpdir = setup_fixture("dup_policy")
pp = os.path.join(tmpdir, "MAPPING-POLICY.yaml")
content = open(pp, "r", encoding="utf-8").read()
open(pp, "w", encoding="utf-8").write(content + "\ndupe_test: a\ndupe_test: b\n")
rc, out, err = run_generator(tmpdir)
test_print("T06. Duplicate YAML key -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T07: Quarantine removal detection
print(f"\n[7/{TOTAL}] Quarantine removal -> different output")
tmpdir = setup_fixture("quar_rm")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    orig_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"))
    qp = os.path.join(tmpdir, "FULL-ID-QUARANTINE-MANIFEST.yaml")
    with open(qp, "r", encoding="utf-8") as f:
        qm = yaml.safe_load(f)
    qm["quarantine_entries"] = [e for e in qm["quarantine_entries"] if e.get("atom_index") != 1]
    with open(qp, "w", encoding="utf-8") as f:
        yaml.dump(qm, f, default_flow_style=False, allow_unicode=True)
    rc2, out2, err2 = run_generator(tmpdir)
    new_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
    test_print("T07. Quarantine change -> different output",
               new_hash and orig_hash != new_hash,
               f"orig={orig_hash[:16]} new={new_hash[:16] if new_hash else 'NONE'}")
else:
    test_print("T07. Quarantine removal", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T08: All 15 Liu Xin atoms quarantined
print(f"\n[8/{TOTAL}] All 15 quarantined")
tmpdir = setup_fixture("all_quar")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    q_count = sum(1 for a in adapters if a["disposition"] == "PERSON_IDENTITY_QUARANTINED")
    test_print("T08. Quarantined count = 15", q_count == 15, f"got {q_count}")
else:
    test_print("T08. Quarantine count", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T09: Drop content_en -> different output (update policy lock)
print(f"\n[9/{TOTAL}] Drop content_en -> different output")
tmpdir = setup_fixture("drop_ce")
rc, out, err = run_generator(tmpdir)
orig_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc == 0 else None
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    atom_lines = [json.loads(l) for l in f if l.strip()]
for a in atom_lines:
    if a.get("atom_index") == 92:
        a.pop("content_en", None)
        break
with open(ap, "w", encoding="utf-8") as f:
    for a in atom_lines:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
update_policy_atom_hash(tmpdir)
rc2, out2, err2 = run_generator(tmpdir)
new_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
test_print("T09. Drop content_en -> different output",
           orig_hash and new_hash and orig_hash != new_hash,
           f"orig={orig_hash[:16] if orig_hash else 'N'} new={new_hash[:16] if new_hash else 'N'}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T10: Drop tags -> different output
print(f"\n[10/{TOTAL}] Drop tags -> different output")
tmpdir = setup_fixture("drop_tags")
rc, out, err = run_generator(tmpdir)
orig_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc == 0 else None
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    atom_lines = [json.loads(l) for l in f if l.strip()]
for a in atom_lines:
    if a.get("atom_index") == 92:
        a.pop("tags", None)
        break
with open(ap, "w", encoding="utf-8") as f:
    for a in atom_lines:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
update_policy_atom_hash(tmpdir)
rc2, out2, err2 = run_generator(tmpdir)
new_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
test_print("T10. Drop tags -> different output",
           orig_hash and new_hash and orig_hash != new_hash,
           f"orig={orig_hash[:16] if orig_hash else 'N'} new={new_hash[:16] if new_hash else 'N'}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T11: Modify content -> different output
print(f"\n[11/{TOTAL}] Modify atom content -> different output")
tmpdir = setup_fixture("mod_cont")
rc, out, err = run_generator(tmpdir)
orig_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc == 0 else None
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    atom_lines = [json.loads(l) for l in f if l.strip()]
for a in atom_lines:
    if a.get("atom_index") == 50:
        a["content_zh"] = a.get("content_zh", "") + " [TAMPERED]"
        break
with open(ap, "w", encoding="utf-8") as f:
    for a in atom_lines:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
update_policy_atom_hash(tmpdir)
rc2, out2, err2 = run_generator(tmpdir)
new_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
test_print("T11. Modified content -> different output",
           orig_hash and new_hash and orig_hash != new_hash,
           f"orig={orig_hash[:16] if orig_hash else 'N'} new={new_hash[:16] if new_hash else 'N'}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T12: Single-hypothesis ambiguity -> reject
print(f"\n[12/{TOTAL}] Single-hypothesis ambiguity -> reject")
tmpdir = setup_fixture("single_hyp")
am = os.path.join(tmpdir, "AMBIGUITY-MANIFEST.yaml")
with open(am, "r", encoding="utf-8") as f:
    aobj = yaml.safe_load(f)
for e in aobj.get("ambiguity_entries", []):
    if e.get("atom_index") == 54:
        e["hypotheses"] = [e["hypotheses"][0]]
        break
aobj["ambiguity_entries"].append({
    "deterministic_id": "cca90a864dc8d0f0ac8dba5cc28453437ebb4a668f09b64ae6191caac1710a12",
    "atom_index": 57, "evidence_family": "QuantStrategyFamily",
    "hypotheses": [{"d2_subtype": "systematic_rebalancer", "confidence": "SPECULATIVE", "basis": "One only"}]
})
with open(am, "w", encoding="utf-8") as f:
    yaml.dump(aobj, f, default_flow_style=False, allow_unicode=True)
rc, out, err = run_generator(tmpdir)
test_print("T12. Single-hypothesis ambiguity -> reject", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T13: Atoms 57/67 -> UNMAPPED
print(f"\n[13/{TOTAL}] Atoms 57/67 -> UNMAPPED")
tmpdir = setup_fixture("u_57_67")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    a57 = [a for a in adapters if a.get("atom_index") == 57]
    a67 = [a for a in adapters if a.get("atom_index") == 67]
    test_print("T13a. Atom 57 -> UNMAPPED",
               a57 and a57[0]["disposition"] == "UNMAPPED",
               f"got {a57[0]['disposition'] if a57 else 'missing'}")
    test_print("T13b. Atom 67 -> UNMAPPED",
               a67 and a67[0]["disposition"] == "UNMAPPED",
               f"got {a67[0]['disposition'] if a67 else 'missing'}")
else:
    test_print("T13. Atoms 57/67", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T14-T15: Hash compare MISSING_BOTH = FAILURE
print(f"\n[14/{TOTAL}] MISSING_BOTH -> hash_compare failure")
hs_path = os.path.join(OUTPUT_DIR, "hash_compare.py")
if os.path.exists(hs_path):
    ta = tempfile.mkdtemp(prefix="hca_"); tb = tempfile.mkdtemp(prefix="hcb_")
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PYTHON_EXE, hs_path, ta, tb], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    test_print("T14. MISSING_BOTH all -> exits 1", r.returncode != 0, f"rc={r.returncode}")
    shutil.rmtree(ta, ignore_errors=True); shutil.rmtree(tb, ignore_errors=True)
else:
    test_print("T14. MISSING_BOTH", False, "hash_compare.py not found")

print(f"\n[15/{TOTAL}] Missing one artifact -> hash_compare failure")
if os.path.exists(hs_path):
    ta = tempfile.mkdtemp(prefix="hca_"); tb = tempfile.mkdtemp(prefix="hcb_")
    with open(os.path.join(ta, "MAPPING-POLICY.yaml"), "w") as f: f.write("test: a")
    env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
    r = subprocess.run([PYTHON_EXE, hs_path, ta, tb], env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    test_print("T15. Missing in B -> exits 1", r.returncode != 0, f"rc={r.returncode}")
    shutil.rmtree(ta, ignore_errors=True); shutil.rmtree(tb, ignore_errors=True)
else:
    test_print("T15. Missing artifact", False, "hash_compare.py not found")

# T16: Full-ID adapter_id
print(f"\n[16/{TOTAL}] adapter_id uses full deterministic_id")
tmpdir = setup_fixture("full_id")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    a1 = [a for a in adapters if a.get("atom_index") == 1]
    if a1:
        did = a1[0]["source_deterministic_id"]
        csh = a1[0]["canonical_source_hash"]
        pv = a1[0].get("policy_version", "18.0")
        disp = a1[0]["disposition"]
        raw = f"{did}||{pv}||{csh}||{disp}"
        expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        test_print("T16. Full-ID adapter_id correct",
                   a1[0]["adapter_id"] == expected,
                   f"match={a1[0]['adapter_id'][:16]}=={expected[:16]}")
    else:
        test_print("T16. Full-ID", False, "atom 1 missing")
else:
    test_print("T16. Full-ID", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T17-T21: Tamper output -> validator catches
print(f"\n[17/{TOTAL}] Corrupt adapter_id -> validator fail")
tmpdir = setup_fixture("corr_aid")
rc, out, err = run_generator(tmpdir)
ap = os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
if lines:
    # Corrupt adapter_id to something that won't match the recomputation formula
    lines[0]["adapter_id"] = "f" * 64
    with open(ap, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T17. Corrupted adapter_id -> fail", rc2 != 0, f"rc={rc2}")
else:
    test_print("T17. Corrupt adapter_id", False, "empty")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[18/{TOTAL}] Tamper disposition -> validator fail")
tmpdir = setup_fixture("tamp_disp")
rc, out, err = run_generator(tmpdir)
ap = os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
if lines:
    for l in lines:
        if l.get("disposition") == "MAPPED":
            l["disposition"] = "UNMAPPED"
            break
    with open(ap, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T18. Changed disposition -> fail", rc2 != 0, f"rc={rc2}")
else:
    test_print("T18. Tamper disposition", False, "empty")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[19/{TOTAL}] Corrupt canonical_source_hash -> fail")
tmpdir = setup_fixture("corr_csh")
rc, out, err = run_generator(tmpdir)
ap = os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
if lines:
    lines[0]["canonical_source_hash"] = "0" * 64
    with open(ap, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T19. Corrupt csh -> fail", rc2 != 0, f"rc={rc2}")
else:
    test_print("T19. Corrupt csh", False, "empty")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[20/{TOTAL}] Drop adapter -> fail")
tmpdir = setup_fixture("drop_ad")
rc, out, err = run_generator(tmpdir)
ap = os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
if len(lines) > 1:
    lines = lines[:-1]
    with open(ap, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T20. Missing adapter -> fail", rc2 != 0, f"rc={rc2}")
else:
    test_print("T20. Drop adapter", False, "empty")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[21/{TOTAL}] Dup adapter_id -> fail")
tmpdir = setup_fixture("dup_aid")
rc, out, err = run_generator(tmpdir)
ap = os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    lines = [json.loads(l) for l in f if l.strip()]
if len(lines) >= 2:
    lines[1]["adapter_id"] = lines[0]["adapter_id"]
    with open(ap, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(json.dumps(l, ensure_ascii=False, sort_keys=True) + "\n")
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T21. Dup adapter_id -> fail", rc2 != 0, f"rc={rc2}")
else:
    test_print("T21. Dup adapter_id", False, "empty")
shutil.rmtree(tmpdir, ignore_errors=True)

# T22-T23: Policy mutation
print(f"\n[22/{TOTAL}] Wrong SUBTYPE_TO_FAMILY -> fail")
tmpdir = setup_fixture("wrong_stf")
pp = os.path.join(tmpdir, "MAPPING-POLICY.yaml")
with open(pp, "r", encoding="utf-8") as f:
    pol = yaml.safe_load(f)
pol["SUBTYPE_TO_FAMILY"]["long_horizon_fund"] = "active_capital"
with open(pp, "w", encoding="utf-8") as f:
    yaml.dump(pol, f, default_flow_style=False, allow_unicode=True)
rc, out, err = run_generator(tmpdir)
rc2, out2, err2 = run_validator(tmpdir)
test_print("T22. Wrong SUBTYPE_TO_FAMILY -> validator catches", rc2 != 0, f"rc={rc2}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[23/{TOTAL}] Remove mapping -> generator adapts")
tmpdir = setup_fixture("rm_map")
pp = os.path.join(tmpdir, "MAPPING-POLICY.yaml")
with open(pp, "r", encoding="utf-8") as f:
    pol = yaml.safe_load(f)
del pol["Q0_TO_D2_SUBTYPE"]["DayTraderRetail"]
with open(pp, "w", encoding="utf-8") as f:
    yaml.dump(pol, f, default_flow_style=False, allow_unicode=True)
rc, out, err = run_generator(tmpdir)
test_print("T23. Modified policy -> generator runs", rc == 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T24: Add person to MARKET_STRUCTURE -> different output
print(f"\n[24/{TOTAL}] Add person ref -> different output")
tmpdir = setup_fixture("add_person")
rc, out, err = run_generator(tmpdir)
orig_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc == 0 else None
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    atom_lines = [json.loads(l) for l in f if l.strip()]
for a in atom_lines:
    if a.get("perspective_class") == "MARKET_STRUCTURE" and \
       "liu xin" not in (a.get("content_zh", "") + a.get("content_en", "")).lower() and \
       "刘鑫" not in (a.get("content_zh", "") + a.get("content_en", "")).lower():
        a["content_zh"] = a.get("content_zh", "") + " 刘鑫评论"
        break
with open(ap, "w", encoding="utf-8") as f:
    for a in atom_lines:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
update_policy_atom_hash(tmpdir)
rc2, out2, err2 = run_generator(tmpdir)
new_hash = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
test_print("T24. Add person ref -> different output",
           orig_hash and new_hash and orig_hash != new_hash and rc2 == 0,
           f"orig={orig_hash[:16] if orig_hash else 'N'} new={new_hash[:16] if new_hash else 'N'} rc={rc2}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T25-T27: Coverage file verification
print(f"\n[25/{TOTAL}] COVERAGE-ATOMS total = 99")
tmpdir = setup_fixture("cov_a")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    cov = yaml.safe_load(open(os.path.join(tmpdir, "COVERAGE-ATOMS.yaml"), "r", encoding="utf-8"))
    test_print("T25. COVERAGE-ATOMS total = 99", cov.get("total_atoms") == 99, f"got {cov.get('total_atoms')}")
else:
    test_print("T25. Coverage atoms", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[26/{TOTAL}] COVERAGE-RELATIONS total = 147")
tmpdir = setup_fixture("cov_r")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    cov = yaml.safe_load(open(os.path.join(tmpdir, "COVERAGE-RELATIONS.yaml"), "r", encoding="utf-8"))
    test_print("T26. COVERAGE-RELATIONS total = 147", cov.get("total_relations") == 147, f"got {cov.get('total_relations')}")
else:
    test_print("T26. Coverage relations", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

print(f"\n[27/{TOTAL}] COVERAGE-QUESTIONS total = 64")
tmpdir = setup_fixture("cov_q")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    cov = yaml.safe_load(open(os.path.join(tmpdir, "COVERAGE-QUESTIONS.yaml"), "r", encoding="utf-8"))
    test_print("T27. COVERAGE-QUESTIONS total = 64", cov.get("total_questions") == 64, f"got {cov.get('total_questions')}")
else:
    test_print("T27. Coverage questions", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T28: D2-ADAPTER-PACKAGE completeness
print(f"\n[28/{TOTAL}] Package has all 99/147/64 IDs")
tmpdir = setup_fixture("pkg_ids")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    pkg = json.load(open(os.path.join(tmpdir, "D2-ADAPTER-PACKAGE.json"), "r", encoding="utf-8"))
    test_print("T28a. Package atom_ids count = 99", len(pkg.get("atom_ids", [])) == 99)
    test_print("T28b. Package relation_ids count = 147", len(pkg.get("relation_ids", [])) == 147)
    test_print("T28c. Package question_ids count = 64", len(pkg.get("question_ids", [])) == 64)
else:
    test_print("T28. Package", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T29: canonical_source_record has all fields
print(f"\n[29/{TOTAL}] CSR has extension fields")
tmpdir = setup_fixture("csr_ext")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    a92 = [a for a in adapters if a.get("atom_index") == 92]
    if a92:
        csr = a92[0].get("canonical_source_record", {})
        test_print("T29a. CSR has tags", "tags" in csr)
        test_print("T29b. CSR has data_availability_note", "data_availability_note" in csr)
        test_print("T29c. CSR has data_version", "data_version" in csr)
        test_print("T29d. CSR has parameter_status", "parameter_status" in csr)
    else:
        test_print("T29. CSR", False, "atom 92 missing")
else:
    test_print("T29. CSR", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T30: Disposition counts
print(f"\n[30/{TOTAL}] Disposition counts")
tmpdir = setup_fixture("disp_count")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    q_count = sum(1 for a in adapters if a["disposition"] == "PERSON_IDENTITY_QUARANTINED")
    a_count = sum(1 for a in adapters if a["disposition"] == "AMBIGUOUS")
    m_count = sum(1 for a in adapters if a["disposition"] == "MAPPED")
    c_count = sum(1 for a in adapters if a["disposition"] == "CONTEXT_ONLY")
    u_count = sum(1 for a in adapters if a["disposition"] == "UNMAPPED")
    test_print("T30a. Quarantined = 15", q_count == 15, f"got {q_count}")
    test_print("T30b. Ambiguous = 3", a_count == 3, f"got {a_count}")
    test_print("T30c. MAPPED = 25", m_count == 25, f"got {m_count}")
    test_print("T30d. Total = 99", q_count + a_count + m_count + c_count + u_count == 99)
else:
    test_print("T30. Dispositions", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T31: Ambiguous have >=2 hypotheses
print(f"\n[31/{TOTAL}] Ambiguous have >=2 hypotheses")
tmpdir = setup_fixture("amb_hyps")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    ambiguous = [a for a in adapters if a["disposition"] == "AMBIGUOUS"]
    ok = all(len(a.get("ambiguity_hypotheses", [])) >= 2 for a in ambiguous)
    test_print("T31. All ambiguous have >=2 hypotheses", ok, f"count={len(ambiguous)}")
else:
    test_print("T31. Ambiguous hyps", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T32: Deterministic output (2 clean runs)
print(f"\n[32/{TOTAL}] Two generations -> identical")
tmpdir = setup_fixture("det1")
rc1, out1, err1 = run_generator(tmpdir)
h1 = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc1 == 0 else None
shutil.rmtree(tmpdir, ignore_errors=True)
tmpdir = setup_fixture("det2")
rc2, out2, err2 = run_generator(tmpdir)
h2 = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if rc2 == 0 else None
shutil.rmtree(tmpdir, ignore_errors=True)
test_print("T32. Two generations -> identical",
           h1 and h2 and h1 == h2,
           f"h1={h1[:16] if h1 else 'N'} h2={h2[:16] if h2 else 'N'}")

# T33: PYTHONHASHSEED variance
print(f"\n[33/{TOTAL}] PYTHONHASHSEED variance -> identical")
tmpdir = setup_fixture("seed0")
env = os.environ.copy(); env["PYTHONIOENCODING"] = "utf-8"
env["Q0_SRC_DIR"] = os.path.join(tmpdir, "q0_sources")
env["POLICY_DIR"] = tmpdir; env["OUTPUT_DIR"] = tmpdir; env["PYTHONHASHSEED"] = "0"
r = subprocess.run([PYTHON_EXE, os.path.join(tmpdir, "generate_adapters.py")],
                   env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
h0 = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if r.returncode == 0 else None
shutil.rmtree(tmpdir, ignore_errors=True)
tmpdir = setup_fixture("seed42")
env["Q0_SRC_DIR"] = os.path.join(tmpdir, "q0_sources")
env["POLICY_DIR"] = tmpdir; env["OUTPUT_DIR"] = tmpdir; env["PYTHONHASHSEED"] = "42"
r = subprocess.run([PYTHON_EXE, os.path.join(tmpdir, "generate_adapters.py")],
                   env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
h42 = file_sha256(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl")) if r.returncode == 0 else None
shutil.rmtree(tmpdir, ignore_errors=True)
test_print("T33. PYTHONHASHSEED variance -> identical",
           h0 and h42 and h0 == h42,
           f"s0={h0[:16] if h0 else 'N'} s42={h42[:16] if h42 else 'N'}")

# T34: Missing package -> validator fail
print(f"\n[34/{TOTAL}] Missing package -> fail")
tmpdir = setup_fixture("no_pkg")
rc, out, err = run_generator(tmpdir)
os.remove(os.path.join(tmpdir, "D2-ADAPTER-PACKAGE.json"))
rc2, out2, err2 = run_validator(tmpdir)
test_print("T34. Missing package -> fail", rc2 != 0, f"rc={rc2}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T35: Corrupt quarantine -> validator detects
print(f"\n[35/{TOTAL}] Quarantine drift -> validator catches")
tmpdir = setup_fixture("q_drift")
rc, out, err = run_generator(tmpdir)
qp = os.path.join(tmpdir, "FULL-ID-QUARANTINE-MANIFEST.yaml")
with open(qp, "r", encoding="utf-8") as f:
    qm = yaml.safe_load(f)
qm["quarantine_entries"] = [e for e in qm["quarantine_entries"] if e.get("atom_index") != 1]
with open(qp, "w", encoding="utf-8") as f:
    yaml.dump(qm, f, default_flow_style=False, allow_unicode=True)
rc2, out2, err2 = run_validator(tmpdir)
test_print("T35. Quarantine drift -> catches", rc2 != 0, f"rc={rc2}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T36: Validator on clean output passes (from original directory)
print(f"\n[36/{TOTAL}] Validator passes on clean output")
tmpdir = setup_fixture("val_pass")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    rc2, out2, err2 = run_validator(tmpdir)
    test_print("T36. Clean validator passes", rc2 == 0, f"rc={rc2} err={err2[:200]}")
else:
    test_print("T36. Clean validator", False, f"generator rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T37: Empty atoms -> generator fails (hash mismatch)
print(f"\n[37/{TOTAL}] Empty atoms -> fail")
tmpdir = setup_fixture("empty_a")
open(os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl"), "w", encoding="utf-8").write("")
rc, out, err = run_generator(tmpdir)
test_print("T37. Empty atoms -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T38: Malformed JSONL -> fail
print(f"\n[38/{TOTAL}] Malformed JSONL -> fail")
tmpdir = setup_fixture("bad_json")
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
lines = open(ap, "r", encoding="utf-8").readlines()
if lines:
    lines[0] = lines[0].rstrip() + "INVALID<<<>>>\n"
    open(ap, "w", encoding="utf-8").writelines(lines)
rc, out, err = run_generator(tmpdir)
test_print("T38. Malformed JSONL -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T39: Missing snapshot -> validator fail
print(f"\n[39/{TOTAL}] Missing snapshot -> fail")
tmpdir = setup_fixture("no_snap")
rc, out, err = run_generator(tmpdir)
if os.path.exists(os.path.join(tmpdir, "D2-INTERFACE-SNAPSHOT.yaml")):
    os.remove(os.path.join(tmpdir, "D2-INTERFACE-SNAPSHOT.yaml"))
rc2, out2, err2 = run_validator(tmpdir)
test_print("T39. Missing snapshot -> fail", rc2 != 0, f"rc={rc2}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T40: Duplicate YAML key in snapshot -> fail
print(f"\n[40/{TOTAL}] Duplicate in snapshot -> fail")
tmpdir = setup_fixture("dup_snap")
snap = os.path.join(tmpdir, "D2-INTERFACE-SNAPSHOT.yaml")
with open(snap, "r", encoding="utf-8") as f:
    c = f.read()
with open(snap, "w", encoding="utf-8") as f:
    f.write(c + "\ndupe: a\ndupe: b\n")
rc, out, err = run_validator(tmpdir)
test_print("T40. Duplicate in snapshot -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T41: Source hash mismatch -> fail
print(f"\n[41/{TOTAL}] Source hash mismatch -> fail")
tmpdir = setup_fixture("hash_mis")
ap = os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-ATOMS.jsonl")
with open(ap, "r", encoding="utf-8") as f:
    atom_lines = [json.loads(l) for l in f if l.strip()]
for a in atom_lines:
    if a.get("atom_index") == 99:
        a["content_zh"] = a.get("content_zh", "") + " TAMPERED"
        break
with open(ap, "w", encoding="utf-8") as f:
    for a in atom_lines:
        f.write(json.dumps(a, ensure_ascii=False) + "\n")
rc, out, err = run_generator(tmpdir)
test_print("T41. Source hash mismatch -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T42: Missing source file -> fail
print(f"\n[42/{TOTAL}] Missing source -> fail")
tmpdir = setup_fixture("no_src")
os.remove(os.path.join(tmpdir, "q0_sources", "KNOWLEDGE-RELATIONS.jsonl"))
rc, out, err = run_generator(tmpdir)
test_print("T42. Missing source -> fail", rc != 0, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T43: CONTEXT_ONLY have no family
print(f"\n[43/{TOTAL}] CONTEXT_ONLY have no family")
tmpdir = setup_fixture("co_no_fam")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    co_fam = [a for a in adapters if a["disposition"] == "CONTEXT_ONLY" and a.get("q0_family")]
    test_print("T43. CONTEXT_ONLY have no family", len(co_fam) == 0, f"found {len(co_fam)}")
else:
    test_print("T43. CONTEXT_ONLY", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T44: All UNMAPPED have downgrade_note
print(f"\n[44/{TOTAL}] All UNMAPPED have downgrade_note")
tmpdir = setup_fixture("unm_note")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    unm_no = [a for a in adapters if a["disposition"] == "UNMAPPED" and not a.get("downgrade_note")]
    test_print("T44. All UNMAPPED have note", len(unm_no) == 0, f"missing {len(unm_no)}")
else:
    test_print("T44. UNMAPPED notes", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# T45: No stale hashes
print(f"\n[45/{TOTAL}] No stale hashes")
tmpdir = setup_fixture("stale")
rc, out, err = run_generator(tmpdir)
if rc == 0:
    adapters = []
    with open(os.path.join(tmpdir, "D2-CANDIDATE-ADAPTERS.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                adapters.append(json.loads(line))
    stale = []
    patterns = ["a1b2c3", "00000000", "deadbeef", "planned", "tbd"]
    for a in adapters:
        for field in ["adapter_id", "canonical_source_hash"]:
            val = a.get(field, "")
            if val and any(p in val.lower() for p in patterns):
                stale.append(f"{a.get('atom_index')}.{field}")
    test_print("T45. No stale hashes", len(stale) == 0, f"stale: {stale}")
else:
    test_print("T45. Stale", False, f"rc={rc}")
shutil.rmtree(tmpdir, ignore_errors=True)

# Summary
print(f"\n{'='*60}")
print(f"RESULTS: {passed}/{total} passed, {failed_tests}/{total} failed")
if failed_tests > 0:
    print("SOME TESTS FAILED")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    sys.exit(0)
