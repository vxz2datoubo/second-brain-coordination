#!/usr/bin/env python3
"""
hash_compare.py — Complete canonical artifact comparison for Epoch 17 Gate B R2
PR #100: Policy Single-Source Uncertainty & Truthful Evidence

Compares ALL canonical artifacts across two generation directories.
Used to verify that 3 clean PYTHONHASHSEED generations produce IDENTICAL outputs.
"""
import hashlib
import os
import sys

CANONICAL_ARTIFACTS = [
    "D2-CANDIDATE-ADAPTERS.jsonl",
    "D2-ADAPTER-PACKAGE.json",
    "D2-ADAPTER-SUMMARY.yaml",
    "COVERAGE-ATOMS.yaml",
    "COVERAGE-RELATIONS.yaml",
    "COVERAGE-QUESTIONS.yaml",
    "SOURCE-LOCK.yaml",
    "GENERATION-RECEIPT.json",
    "MAPPING-POLICY.yaml",
    "QUARANTINE-MANIFEST.yaml",
    "AMBIGUITY-MANIFEST.yaml",
    "D2-INTERFACE-SNAPSHOT.yaml",
]


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare_dirs(dir_a, dir_b):
    """Compare canonical artifacts between two directories."""
    results = {}
    all_identical = True

    for art in CANONICAL_ARTIFACTS:
        path_a = os.path.join(dir_a, art)
        path_b = os.path.join(dir_b, art)
        exists_a = os.path.exists(path_a)
        exists_b = os.path.exists(path_b)

        if not exists_a and not exists_b:
            results[art] = {"status": "MISSING_BOTH", "match": True}
            print(f"  MISSING: {art} (both)")
            continue
        elif not exists_a:
            results[art] = {"status": "MISSING_A", "match": False}
            print(f"  MISMATCH: {art} (missing in A)")
            all_identical = False
            continue
        elif not exists_b:
            results[art] = {"status": "MISSING_B", "match": False}
            print(f"  MISMATCH: {art} (missing in B)")
            all_identical = False
            continue

        hash_a = file_sha256(path_a)
        hash_b = file_sha256(path_b)
        match = hash_a == hash_b
        results[art] = {"status": "HASHED", "hash_a": hash_a, "hash_b": hash_b, "match": match}

        status = "MATCH" if match else "MISMATCH"
        print(f"  {status}: {art}")
        if not match:
            print(f"    A: {hash_a}")
            print(f"    B: {hash_b}")
            all_identical = False

    return results, all_identical


def main():
    if len(sys.argv) < 3:
        print("Usage: hash_compare.py <dir_a> <dir_b> [dir_c]")
        print("Compares canonical artifacts between 2-3 generation directories.")
        sys.exit(1)

    dir_a = sys.argv[1]
    dir_b = sys.argv[2]
    dir_c = sys.argv[3] if len(sys.argv) > 3 else None

    print(f"Comparing canonical artifacts:")
    print(f"  A: {dir_a}")
    print(f"  B: {dir_b}")

    # First comparison: A vs B
    print(f"\n=== A vs B ===")
    results_ab, identical_ab = compare_dirs(dir_a, dir_b)

    # Second comparison: A vs C (if provided)
    identical_ac = True
    if dir_c:
        print(f"\n=== A vs C ===")
        print(f"  C: {dir_c}")
        results_ac, identical_ac = compare_dirs(dir_a, dir_c)

    # Summary
    print(f"\n=== SUMMARY ===")
    print(f"A vs B: {'IDENTICAL' if identical_ab else 'DIFFERENT'}")
    if dir_c:
        print(f"A vs C: {'IDENTICAL' if identical_ac else 'DIFFERENT'}")

    if identical_ab and identical_ac:
        print("\nALL CANONICAL ARTIFACTS IDENTICAL")
        sys.exit(0)
    else:
        print("\nCANONICAL ARTIFACTS DIFFER")
        sys.exit(1)


if __name__ == "__main__":
    main()
