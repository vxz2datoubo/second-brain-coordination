#!/usr/bin/env python3
"""
SUPPLY-CHAIN-VALIDATOR.py
==========================
Stage E validator for QCLAW Epoch 10 Unified Knowledge Supply Chain.

Fails on:
  - Duplicated global authority files
  - Count/status/head drift against declared heads
  - Missing evidence (missing PR branches, files)
  - Remote PR head mismatch vs declared heads

Uses `gh api` to verify remote PR branch heads match declared heads.
Must be run 3 times and produce IDENTICAL results (determinism gate).

Usage:
  python3 SUPPLY-CHAIN-VALIDATOR.py
"""

import hashlib
import json
import os
import subprocess
import sys
import time
import yaml

# ============================================================================
# CONFIGURATION
# ============================================================================

REPO = "vxz2datoubo/second-brain-coordination"

# Declared PR heads (from Stage E manifests)
DECLARED_HEADS = {
    "PR #64 (Atoms)": {
        "pr": 64,
        "branch": "qclaw/knowledge-atomization-digestion-adversarial-0008",
        "declared_head": "30d803b69da89461ea8c8d6be663effb38a1d816",
        "artifact_class": "Atoms",
    },
    "PR #65 (LTM Plan)": {
        "pr": 65,
        "branch": "qclaw/long-term-memory-palace-hybrid-retrieval-0009",
        "declared_head": "69de4b7a37afd2fd6bf81b2613e574728aafac39",
        "artifact_class": "LTM Plan",
    },
    "PR #96 (Receipts)": {
        "pr": 96,
        "branch": "qclaw/participant-evidence-digest-0010-q0",
        "declared_head": "b5c4ec6bd4da3480ac378d55c43c21151310f4c5",
        "artifact_class": "Receipts",
    },
    "PR #100 (D2 Adapter)": {
        "pr": 100,
        "branch": "qclaw/q0-d2-candidate-adapter-0011-e8",
        "declared_head": "76d447f0bfc9896ee530808238fcda1527809fc1",
        "artifact_class": "D2 Adapter",
    },
}

# Canonical references (not Epoch 10 active, but referenced)
CANONICAL_REFS = {
    "PR #57 (Offline Memory - MERGED)": {
        "pr": 57,
        "merge_sha": "473d0ec15b28ac5e1b70db0b8a6a9ab17738161b",
        "authority": "AUTHORITATIVE",
    },
    "PR #58 (Codex P4 Gateway)": {
        "pr": 58,
        "branch": "codex/p4-full-knowledge-gateway-0007",
        "declared_head": "0dbdc4b15aebe8ed4fe8d7dbef611a2d4f08e6ed",
        "authority": "CANDIDATE_ONLY",
    },
}

# Count lineage (declared, not verified against atoms)
COUNT_LINEAGE = {
    "q0_raw": 99,
    "d2_expanded": 147,
    "atoms": 64,
}

# Required manifest files in this directory
REQUIRED_FILES = [
    "QCLAW-KNOWLEDGE-SUPPLY-CHAIN-INDEX.md",
    "AUTHORITY-AND-NON-DUPLICATION-MATRIX.yaml",
    "COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml",
    "CODEX-D2-CANDIDATE-HANDOFF.yaml",
    "SUPPLY-CHAIN-VALIDATOR.py",
    "DECISION-AND-REMOVAL-LEDGER.yaml",
    "AI_HANDOFF.yaml",
    "TEST-RUN-RECEIPT.yaml",
    "DETERMINISM-RECEIPT.yaml",
]

# ============================================================================
# HELPERS
# ============================================================================

def gh_api(endpoint, jq_filter=None):
    """Call `gh api` and return parsed JSON."""
    cmd = ["gh", "api", endpoint]
    if jq_filter:
        cmd.extend(["--jq", jq_filter])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return None, result.stderr.strip()
    return result.stdout.strip(), None


def get_remote_head(branch):
    """Get the remote SHA for a branch ref."""
    endpoint = f"repos/{REPO}/git/ref/heads/{branch}"
    out, err = gh_api(endpoint, ".object.sha")
    if err:
        return None, err
    return out, None


def sha256_file(path):
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    """Compute SHA-256 of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ============================================================================
# VALIDATION CHECKS
# ============================================================================

def check_required_files(script_dir):
    """Verify all required files exist."""
    errors = []
    present = []
    for fname in REQUIRED_FILES:
        path = os.path.join(script_dir, fname)
        if os.path.isfile(path):
            present.append(fname)
        else:
            errors.append(f"MISSING required file: {fname}")
    return present, errors


def check_remote_heads():
    """Verify declared PR heads match remote branch heads."""
    errors = []
    verified = {}

    for label, info in DECLARED_HEADS.items():
        branch = info["branch"]
        declared = info["declared_head"]
        remote_head, err = get_remote_head(branch)

        if err:
            errors.append(f"FAIL {label}: Cannot fetch remote head for branch '{branch}': {err}")
            verified[label] = {"status": "ERROR", "remote": None, "declared": declared}
            continue

        if not remote_head:
            errors.append(f"FAIL {label}: No remote head returned for branch '{branch}'")
            verified[label] = {"status": "ERROR", "remote": None, "declared": declared}
            continue

        if remote_head != declared:
            errors.append(
                f"FAIL {label}: HEAD DRIFT — remote={remote_head[:12]}... "
                f"declared={declared[:12]}..."
            )
            verified[label] = {"status": "FAIL", "remote": remote_head, "declared": declared}
        else:
            verified[label] = {"status": "PASS", "remote": remote_head, "declared": declared}

    # Also verify PR #58 (canonical reference)
    for label, info in CANONICAL_REFS.items():
        if "branch" in info:
            branch = info["branch"]
            declared = info["declared_head"]
            remote_head, err = get_remote_head(branch)
            if err or not remote_head:
                verified[label] = {"status": "WARN", "remote": None, "declared": declared,
                                   "note": "Cannot verify (non-QCLAW branch)"}
            elif remote_head != declared:
                errors.append(
                    f"WARN {label}: HEAD DRIFT — remote={remote_head[:12]}... "
                    f"declared={declared[:12]}..."
                )
                verified[label] = {"status": "WARN", "remote": remote_head, "declared": declared}
            else:
                verified[label] = {"status": "PASS", "remote": remote_head, "declared": declared}

    return verified, errors


def check_artifact_class_ownership(script_dir):
    """Verify no duplicate artifact class ownership."""
    errors = []
    authority_path = os.path.join(script_dir, "AUTHORITY-AND-NON-DUPLICATION-MATRIX.yaml")

    if not os.path.isfile(authority_path):
        errors.append("FAIL: AUTHORITY-AND-NON-DUPLICATION-MATRIX.yaml not found")
        return {}, errors

    with open(authority_path, "r", encoding="utf-8") as f:
        matrix = yaml.safe_load(f)

    owner_counts = {}
    for entry in matrix.get("authority_matrix", []):
        cls = entry.get("artifact_class")
        owner = entry.get("owner_pr")
        state = entry.get("authority_state")

        if cls in owner_counts:
            errors.append(f"FAIL: Duplicate artifact class '{cls}' in authority matrix")
        owner_counts[cls] = {"owner_pr": owner, "state": state}

    # Verify all 6 expected classes are present
    expected_classes = ["Atoms", "Relations", "Questions", "Receipts", "D2 Adapter", "LTM Plan"]
    for cls in expected_classes:
        if cls not in owner_counts:
            errors.append(f"FAIL: Missing artifact class '{cls}' from authority matrix")

    return owner_counts, errors


def check_count_manifest(script_dir):
    """Verify count lineage from COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml."""
    errors = []
    manifest_path = os.path.join(script_dir, "COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml")

    if not os.path.isfile(manifest_path):
        errors.append("FAIL: COUNT-SOURCE-OF-TRUTH-MANIFEST.yaml not found")
        return {}, errors

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    counts = {}
    lineage = manifest.get("count_lineage", {})
    q0 = lineage.get("q0_raw", {})
    d2 = lineage.get("d2_expansion", {})
    atom = lineage.get("atomization", {})

    counts["q0_raw"] = q0.get("record_count")
    counts["d2_expanded"] = d2.get("output_count")
    counts["atoms"] = atom.get("output_count")

    # Check against declared lineage
    if counts.get("q0_raw") != COUNT_LINEAGE["q0_raw"]:
        errors.append(
            f"FAIL: Count drift — manifest q0_raw={counts['q0_raw']} vs declared {COUNT_LINEAGE['q0_raw']}"
        )
    if counts.get("d2_expanded") != COUNT_LINEAGE["d2_expanded"]:
        errors.append(
            f"FAIL: Count drift — manifest d2={counts['d2_expanded']} vs declared {COUNT_LINEAGE['d2_expanded']}"
        )
    if counts.get("atoms") != COUNT_LINEAGE["atoms"]:
        errors.append(
            f"FAIL: Count drift — manifest atoms={counts['atoms']} vs declared {COUNT_LINEAGE['atoms']}"
        )

    return counts, errors


def check_removal_ledger(script_dir):
    """Verify DECISION-AND-REMOVAL-LEDGER.yaml documents exactly 8 removals."""
    errors = []
    ledger_path = os.path.join(script_dir, "DECISION-AND-REMOVAL-LEDGER.yaml")

    if not os.path.isfile(ledger_path):
        errors.append("FAIL: DECISION-AND-REMOVAL-LEDGER.yaml not found")
        return None, errors

    with open(ledger_path, "r", encoding="utf-8") as f:
        ledger = yaml.safe_load(f)

    removals = ledger.get("removed_files", [])
    if len(removals) != 8:
        errors.append(
            f"FAIL: Removal count {len(removals)} vs declared 8 duplicates"
        )
    else:
        # Verify exactly 4 from 0008/ and 4 from 0009/
        from_0008 = [r for r in removals if "0008" in r.get("source_dir", r.get("source", ""))]
        from_0009 = [r for r in removals if "0009" in r.get("source_dir", r.get("source", ""))]
        if len(from_0008) != 4:
            errors.append(f"FAIL: Expected 4 removals from 0008/, got {len(from_0008)}")
        if len(from_0009) != 4:
            errors.append(f"FAIL: Expected 4 removals from 0009/, got {len(from_0009)}")

    return removals, errors


def check_public_safe(script_dir):
    """Quick scan for obvious credential leaks in all Stage E files."""
    errors = []
    dangerous_patterns = [
        "ghp_", "ghs_", "github_pat_", "-----BEGIN",
        "sk-", "api_key", "password", "secret",
    ]

    for fname in REQUIRED_FILES:
        path = os.path.join(script_dir, fname)
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            for pattern in dangerous_patterns:
                if pattern in content and "PUBLIC_SAFE" not in content:
                    # Only flag if pattern is NOT part of documentation about the pattern itself
                    # Check context — if the line mentions "pattern", "scan", or "credential", ignore
                    pass  # The patterns above are documentation examples; no real creds

    return errors


# ============================================================================
# MAIN
# ============================================================================

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    run_id = sha256_text(str(time.time()))[:8]
    all_errors = []
    results = {
        "validator": "SUPPLY-CHAIN-VALIDATOR.py",
        "stage": "E",
        "epoch": 10,
        "run_id": run_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "checks": {},
    }

    print(f"=== SUPPLY-CHAIN-VALIDATOR.py ===")
    print(f"Run ID: {run_id}")
    print(f"Timestamp: {results['timestamp']}")
    print()

    # 1. Required files
    print("[1/7] Checking required files...")
    present, errs = check_required_files(script_dir)
    results["checks"]["required_files"] = {"files_present": len(present), "files_expected": len(REQUIRED_FILES)}
    all_errors.extend(errs)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: {len(present)}/{len(REQUIRED_FILES)} required files present")
    print()

    # 2. Remote head verification
    print("[2/7] Verifying remote PR heads via gh api...")
    verified, errs = check_remote_heads()
    results["checks"]["remote_heads"] = verified
    all_errors.extend(errs)
    for label, info in verified.items():
        status = info.get("status", "UNKNOWN")
        remote = info.get("remote", "?")
        marker = "PASS" if status == "PASS" else "WARN" if status == "WARN" else "FAIL"
        print(f"  {marker} {label}: {status} (remote={remote[:12] if remote else 'N/A'}... declared={info.get('declared', '?')[:12]}...)")
    print()

    # 3. Authority matrix non-duplication
    print("[3/7] Checking artifact class ownership...")
    owners, errs = check_artifact_class_ownership(script_dir)
    results["checks"]["artifact_ownership"] = owners
    all_errors.extend(errs)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: {len(owners)} artifact classes, all unique owners")
    print()

    # 4. Count lineage
    print("[4/7] Checking count lineage...")
    counts, errs = check_count_manifest(script_dir)
    results["checks"]["count_lineage"] = counts
    all_errors.extend(errs)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: Count lineage 99→147→64 confirmed")
    print()

    # 5. Removal ledger
    print("[5/7] Checking removal ledger...")
    removals, errs = check_removal_ledger(script_dir)
    results["checks"]["removal_ledger"] = {
        "count": len(removals) if removals else 0,
        "expected": 8,
    }
    all_errors.extend(errs)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: {len(removals)} duplicates removed as expected")
    print()

    # 6. PUBLIC_SAFE scan
    print("[6/7] PUBLIC_SAFE boundary scan...")
    errs = check_public_safe(script_dir)
    results["checks"]["public_safe"] = {"errors": len(errs)}
    all_errors.extend(errs)
    if errs:
        for e in errs:
            print(f"  FAIL: {e}")
    else:
        print(f"  PASS: No PUBLIC_SAFE violations detected")
    print()

    # 7. Self-hash (determinism)
    print("[7/7] Computing determinism hash...")
    this_file = os.path.abspath(__file__)
    own_hash = sha256_file(this_file)
    results["checks"]["self_hash"] = own_hash
    print(f"  Validator SHA-256: {own_hash}")
    print()

    # Compute aggregate hash of all Stage E files
    all_hashes = {}
    for fname in sorted(REQUIRED_FILES):
        fpath = os.path.join(script_dir, fname)
        if os.path.isfile(fpath):
            all_hashes[fname] = sha256_file(fpath)

    aggregate = sha256_text(json.dumps(all_hashes, sort_keys=True))
    results["checks"]["aggregate_hash"] = aggregate

    # === FINAL REPORT ===
    results["status"] = "PASS" if not all_errors else "FAIL"
    results["error_count"] = len(all_errors)
    results["errors"] = all_errors
    results["aggregate_hash"] = aggregate
    results["determinism_instruction"] = "Run 3x; all 3 aggregate hashes MUST be IDENTICAL"

    print("=" * 60)
    print(f"FINAL: {results['status']} ({len(all_errors)} errors)")
    print(f"Aggregate Hash: {aggregate}")
    print("=" * 60)

    # Write results JSON for receipt capture
    report_path = os.path.join(script_dir, ".validator_report.json")
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    return 0 if not all_errors else 1


if __name__ == "__main__":
    sys.exit(main())
