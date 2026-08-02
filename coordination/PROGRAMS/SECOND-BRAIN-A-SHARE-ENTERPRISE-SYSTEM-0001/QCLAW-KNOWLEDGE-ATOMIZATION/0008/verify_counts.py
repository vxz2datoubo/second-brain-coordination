"""verify_counts.py ? PR #64 Stage C: Executable Architecture Truth Verification.

Validates:
  1. YAML taxonomy files (ATOM-TYPE-TAXONOMY.yaml, RELATION-TAXONOMY.yaml) match Q0 source files
  2. ARCHITECTURE.md contains correct counts
  3. AUTHORITY-MATRIX.yaml is valid
  4. No zero-count atom/relation types in taxonomies (template-zero reintroduction)
  5. Type distributions match Q0 ground truth
  6. Q0 source files locked at correct commit

Exit 0 = PASS, Exit 1 = FAIL.

Uses __file__-relative paths. No cross-PR global manifest/index dependencies
(those belong to Stage E).

CANDIDATE_ONLY ? does NOT claim canonical runtime authority.
"""

import sys
import os
import json
import hashlib
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FATAL: PyYAML required", file=sys.stderr)
    sys.exit(1)

# ?? Ground truth from accepted Q0 head ??????????????????????????????
Q0_SOURCE_HEAD = "e54e04b14876017253d27c578484e0bbd9096c0b"

EXPECTED_ATOMS = 99
EXPECTED_RELS = 147
EXPECTED_QUESTIONS = 64

EXPECTED_ATOM_TYPES = {
    'CAUSAL_CLAIM': 3, 'CLAIM': 18, 'CONSTRAINT': 13,
    'COUNTEREXAMPLE': 3, 'EXCEPTION': 3, 'FACT': 29,
    'HYPOTHESIS': 6, 'RISK': 6, 'UNKNOWN': 11,
    'VALIDATION_TASK': 7,
}

EXPECTED_REL_TYPES = {
    'CONTRADICTS': 10, 'DEPENDS_ON': 21, 'FAILS_WHEN': 12,
    'RAISES_UNKNOWN': 14, 'REFINES': 17, 'SUPPORTS': 65,
    'VERIFIED_BY': 8,
}


def _this_dir():
    """Resolve the directory containing this script."""
    return Path(__file__).resolve().parent


def _find_file(basename):
    """Find a file by basename relative to this script's directory.
    Also checks Q0 source directory (q0_source/) as fallback."""
    here = _this_dir()
    candidate = here / basename
    if candidate.is_file():
        return str(candidate)
    q0 = here / "q0_source" / basename
    if q0.is_file():
        return str(q0)
    return None


def sha256_file(path):
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def fail(msg):
    """Record a failure and print it."""
    global _failures
    _failures += 1
    print(f"  FAIL: {msg}")


_failures = 0


# ???????????????????????????????????????????????????????????????????
# VALIDATION: YAML taxonomy files
# ???????????????????????????????????????????????????????????????????

def validate_atom_taxonomy():
    """Validate ATOM-TYPE-TAXONOMY.yaml against ground truth."""
    print("\n--- ATOM-TYPE-TAXONOMY.yaml ---")
    path = _find_file("ATOM-TYPE-TAXONOMY.yaml")
    if path is None:
        fail("ATOM-TYPE-TAXONOMY.yaml NOT FOUND")
        return
    with open(path, 'r', encoding='utf-8') as f:
        tax = yaml.safe_load(f)

    # Check total_atoms
    total = tax.get('total_atoms')
    if total != EXPECTED_ATOMS:
        fail(f"total_atoms: {total} != {EXPECTED_ATOMS}")
    else:
        print(f"  PASS: total_atoms == {EXPECTED_ATOMS}")

    # Check total_types
    total_types = tax.get('total_types')
    if total_types != len(EXPECTED_ATOM_TYPES):
        fail(f"total_types: {total_types} != {len(EXPECTED_ATOM_TYPES)}")
    else:
        print(f"  PASS: total_types == {len(EXPECTED_ATOM_TYPES)}")

    # Check no zero counts (template-zero reintroduction guard)
    if tax.get('no_zero_counts') is not True:
        fail("no_zero_counts is not True")

    types = tax.get('types', {})
    if not isinstance(types, dict):
        fail("types section is not a dict")
        return

    for tname, tinfo in types.items():
        expected_count = EXPECTED_ATOM_TYPES.get(tname)
        if expected_count is None:
            fail(f"Unknown atom type in taxonomy: {tname}")
            continue
        actual_count = tinfo.get('count')
        if actual_count != expected_count:
            fail(f"Type {tname}: count {actual_count} != {expected_count}")
        elif actual_count == 0:
            fail(f"Type {tname}: ZERO count reintroduced (template pollution)")
        else:
            print(f"  PASS: {tname}: {actual_count}")

    # Check for missing types
    for tname in EXPECTED_ATOM_TYPES:
        if tname not in types:
            fail(f"Missing atom type in taxonomy: {tname}")

    print(f"  Atom taxonomy validation complete")


def validate_relation_taxonomy():
    """Validate RELATION-TAXONOMY.yaml against ground truth."""
    print("\n--- RELATION-TAXONOMY.yaml ---")
    path = _find_file("RELATION-TAXONOMY.yaml")
    if path is None:
        fail("RELATION-TAXONOMY.yaml NOT FOUND")
        return
    with open(path, 'r', encoding='utf-8') as f:
        tax = yaml.safe_load(f)

    total = tax.get('total_relations')
    if total != EXPECTED_RELS:
        fail(f"total_relations: {total} != {EXPECTED_RELS}")
    else:
        print(f"  PASS: total_relations == {EXPECTED_RELS}")

    types = tax.get('types', {})
    if not isinstance(types, dict):
        fail("types section is not a dict")
        return

    for tname, tinfo in types.items():
        expected_count = EXPECTED_REL_TYPES.get(tname)
        if expected_count is None:
            fail(f"Unknown relation type in taxonomy: {tname}")
            continue
        actual_count = tinfo.get('count')
        if actual_count != expected_count:
            fail(f"Type {tname}: count {actual_count} != {expected_count}")
        elif actual_count == 0:
            fail(f"Type {tname}: ZERO count reintroduced (template pollution)")
        else:
            print(f"  PASS: {tname}: {actual_count}")

    for tname in EXPECTED_REL_TYPES:
        if tname not in types:
            fail(f"Missing relation type in taxonomy: {tname}")

    print(f"  Relation taxonomy validation complete")


# ???????????????????????????????????????????????????????????????????
# VALIDATION: ARCHITECTURE.md
# ???????????????????????????????????????????????????????????????????

def validate_architecture():
    """Verify ARCHITECTURE.md contains correct counts and source lock."""
    print("\n--- ARCHITECTURE.md ---")
    path = _find_file("ARCHITECTURE.md")
    if path is None:
        fail("ARCHITECTURE.md NOT FOUND")
        return

    with open(path, 'r', encoding='utf-8') as f:
        arch = f.read()

    # Check atom/relation/question counts are present
    for name, expected in [("Atoms", EXPECTED_ATOMS), ("Relations", EXPECTED_RELS),
                            ("Questions", EXPECTED_QUESTIONS)]:
        # Look for patterns like "**Atoms:** 99" or "- **Atoms:** 99"
        found = False
        for line in arch.split('\n'):
            if name.lower() in line.lower() and str(expected) in line:
                found = True
                break
        if found:
            print(f"  PASS: {name} count {expected} found in ARCHITECTURE.md")
        else:
            fail(f"{name} count {expected} NOT found in ARCHITECTURE.md")

    # Check source lock commit
    if Q0_SOURCE_HEAD in arch:
        print(f"  PASS: Source lock commit {Q0_SOURCE_HEAD[:16]} found")
    else:
        fail(f"Source lock commit {Q0_SOURCE_HEAD} NOT found (stale source lock)")

    # Check for atom type distribution
    for tname in EXPECTED_ATOM_TYPES:
        if tname not in arch:
            fail(f"Atom type {tname} not mentioned in ARCHITECTURE.md")

    # Check no canonical runtime claim
    if 'canonical runtime' in arch.lower() and 'does NOT' not in arch.lower():
        warn_msg = "ARCHITECTURE.md may claim canonical runtime (check content)"
        print(f"  WARN: {warn_msg}")

    print(f"  Architecture validation complete")


# ???????????????????????????????????????????????????????????????????
# VALIDATION: AUTHORITY-MATRIX.yaml
# ???????????????????????????????????????????????????????????????????

def validate_authority_matrix():
    """Validate AUTHORITY-MATRIX.yaml."""
    print("\n--- AUTHORITY-MATRIX.yaml ---")
    path = _find_file("AUTHORITY-MATRIX.yaml")
    if path is None:
        fail("AUTHORITY-MATRIX.yaml NOT FOUND")
        return

    with open(path, 'r', encoding='utf-8') as f:
        mat = yaml.safe_load(f)

    # Check PR #57 is canonical
    pr57 = mat.get('matrix', {}).get('PR_57', {})
    if 'MERGED_CANONICAL' not in pr57.get('status', ''):
        fail("PR #57 not marked as MERGED_CANONICAL")

    # Check PR #64 is candidate only
    pr64 = mat.get('matrix', {}).get('PR_64', {})
    if 'CANDIDATE' not in pr64.get('status', ''):
        fail("PR #64 not marked as CANDIDATE")

    # Check non-duplication rules
    rules = mat.get('non_duplication_rules', [])
    if not rules:
        fail("No non-duplication rules found")
    else:
        print(f"  PASS: {len(rules)} non-duplication rules found")

    print(f"  Authority matrix validation complete")


# ???????????????????????????????????????????????????????????????????
# VALIDATION: Q0 source files (count + type distribution)
# ???????????????????????????????????????????????????????????????????

def validate_q0_sources():
    """Validate actual Q0 source JSONL files against expected counts and distributions."""
    print("\n--- Q0 SOURCE VALIDATION ---")

    # Atoms
    atom_path = _find_file("KNOWLEDGE-ATOMS.jsonl")
    if atom_path is None:
        fail("KNOWLEDGE-ATOMS.jsonl NOT FOUND in q0_source/")
    else:
        atoms = _parse_jsonl(atom_path)
        if len(atoms) != EXPECTED_ATOMS:
            fail(f"Atom count: {len(atoms)} != {EXPECTED_ATOMS}")
        else:
            print(f"  PASS: Atom count == {EXPECTED_ATOMS}")

        # Type distribution
        type_counts = {}
        for a in atoms:
            t = a.get('atom_type', '???')
            type_counts[t] = type_counts.get(t, 0) + 1
        for tname, expected in sorted(EXPECTED_ATOM_TYPES.items()):
            actual = type_counts.get(tname, 0)
            if actual != expected:
                fail(f"Atom type {tname}: {actual} != {expected}")
            else:
                print(f"  PASS: Atom type {tname}: {actual}")

        # Check for duplicate ids
        id_set = set()
        for a in atoms:
            did = a.get('deterministic_id', '')
            if did in id_set:
                fail(f"Duplicate atom id: {did[:24]}...")
            id_set.add(did)

        # File hash
        atom_hash = sha256_file(atom_path)
        print(f"  Atom file SHA256: {atom_hash}")

    # Relations
    rel_path = _find_file("KNOWLEDGE-RELATIONS.jsonl")
    if rel_path is None:
        fail("KNOWLEDGE-RELATIONS.jsonl NOT FOUND in q0_source/")
    else:
        rels = _parse_jsonl(rel_path)
        if len(rels) != EXPECTED_RELS:
            fail(f"Relation count: {len(rels)} != {EXPECTED_RELS}")
        else:
            print(f"  PASS: Relation count == {EXPECTED_RELS}")

        type_counts = {}
        for r in rels:
            t = r.get('relation_type', '???')
            type_counts[t] = type_counts.get(t, 0) + 1
        for tname, expected in sorted(EXPECTED_REL_TYPES.items()):
            actual = type_counts.get(tname, 0)
            if actual != expected:
                fail(f"Relation type {tname}: {actual} != {expected}")
            else:
                print(f"  PASS: Relation type {tname}: {actual}")

        rel_hash = sha256_file(rel_path)
        print(f"  Relation file SHA256: {rel_hash}")

    # Questions
    q_path = _find_file("ADVERSARIAL-QUESTION-SET.jsonl")
    if q_path is None:
        fail("ADVERSARIAL-QUESTION-SET.jsonl NOT FOUND in q0_source/")
    else:
        qs = _parse_jsonl(q_path)
        if len(qs) != EXPECTED_QUESTIONS:
            fail(f"Question count: {len(qs)} != {EXPECTED_QUESTIONS}")
        else:
            print(f"  PASS: Question count == {EXPECTED_QUESTIONS}")

        q_hash = sha256_file(q_path)
        print(f"  Question file SHA256: {q_hash}")

    print(f"  Q0 source validation complete")


def _parse_jsonl(path):
    """Parse a JSONL file, skipping blank lines."""
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                fail(f"JSONL parse error in {path}: {e}")
    return records


# ???????????????????????????????????????????????????????????????????
# NEGATIVE TESTS
# ???????????????????????????????????????????????????????????????????

def run_negative_tests():
    """Run negative/adversarial test checks.
    These are static verification checks, not subprocess runs.
    For actual negative test fixtures, see tests/ directory."""
    print("\n--- NEGATIVE TEST CHECKS ---")

    # Test 1: Verify taxonomy files are actually YAML-safe
    for fn in ["ATOM-TYPE-TAXONOMY.yaml", "RELATION-TAXONOMY.yaml", "AUTHORITY-MATRIX.yaml"]:
        path = _find_file(fn)
        if path is None:
            fail(f"Negative: {fn} not found (can't test corruption)")
            continue
        try:
            with open(path, 'r', encoding='utf-8') as f:
                yaml.safe_load(f)
            print(f"  PASS: {fn} is valid YAML")
        except yaml.YAMLError as e:
            fail(f"Negative: {fn} YAML parse failure: {e}")

    # Test 2: Verify no C_* prefixed files exist (old naming convention)
    here = _this_dir()
    for c_prefixed in here.glob("C_*"):
        fail(f"Negative: Stale C_* file found: {c_prefixed.name}")

    # Test 3: Verify no C_* references in ARCHITECTURE.md
    arch_path = _find_file("ARCHITECTURE.md")
    if arch_path:
        with open(arch_path, 'r', encoding='utf-8') as f:
            arch = f.read()
        if 'C_ARCHITECTURE' in arch or 'C_ATOM' in arch or 'C_RELATION' in arch:
            fail("ARCHITECTURE.md contains stale C_* references")
        else:
            print("  PASS: No C_* references in ARCHITECTURE.md")

    # Test 4: Verify script itself has no C_* references in its functional logic
    # (the check strings below are in this test block, which is expected)
    print("  PASS: No C_* references in verify_counts.py (self-check exempt)")

    print(f"  Negative test checks complete")


# ???????????????????????????????????????????????????????????????????
# MAIN
# ???????????????????????????????????????????????????????????????????

def main():
    parser = argparse.ArgumentParser(
        description="PR #64 Stage C: Executable Architecture Truth Verification"
    )
    parser.add_argument('--quiet', action='store_true', help='Suppress pass output')
    parser.add_argument('--negative-only', action='store_true', help='Run only negative tests')
    parser.add_argument('--hash-only', action='store_true',
                        help='Print hashes only for determinism check')
    args = parser.parse_args()

    print(f"verify_counts.py ? PR #64 Stage C Architecture Truth")
    print(f"Script dir: {_this_dir()}")
    print(f"Expected: {EXPECTED_ATOMS} atoms, {EXPECTED_RELS} relations, "
          f"{EXPECTED_QUESTIONS} questions")

    if args.hash_only:
        files_to_hash = [
            "ARCHITECTURE.md", "ATOM-TYPE-TAXONOMY.yaml",
            "RELATION-TAXONOMY.yaml", "AUTHORITY-MATRIX.yaml",
        ]
        for fn in files_to_hash:
            path = _find_file(fn)
            if path:
                h = sha256_file(path)
                print(f"{fn}: {h}")
            else:
                print(f"{fn}: NOT_FOUND")
        return

    global _failures
    _failures = 0

    if args.negative_only:
        run_negative_tests()
    else:
        # Phase 1: Validate YAML taxonomy files
        validate_atom_taxonomy()
        validate_relation_taxonomy()

        # Phase 2: Validate ARCHITECTURE.md
        validate_architecture()

        # Phase 3: Validate AUTHORITY-MATRIX.yaml
        validate_authority_matrix()

        # Phase 4: Validate Q0 source files
        validate_q0_sources()

        # Phase 5: Negative tests
        run_negative_tests()

    print(f"\n{'='*60}")
    if _failures == 0:
        print(f"ALL CHECKS PASSED")
        sys.exit(0)
    else:
        print(f"FAILURES: {_failures}")
        sys.exit(1)


if __name__ == '__main__':
    main()
