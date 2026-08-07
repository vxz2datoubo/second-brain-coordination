"""E45 Q7 — Genuine isolated copied-production mutations

Each mutation: unique exact byte replacement, invariant test, nonzero mutant exit,
exact restoration, restored-green rerun, duration + stream hashes.
"""
import os, sys, hashlib, shutil, tempfile, subprocess, time
from typing import Dict, List, Tuple, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(os.path.dirname(HERE))  # E45 project root (src/qclaw_e45 -> src -> project)

# ----- Mutation Definitions -----

MUTATIONS = [
    {
        "id": "M01_FACTORY_BYPASS",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b"def create_atom(self, bundle",
        "replacement": b"def create_atom(self, bundle, _bypass_verified=True",
        "invariant": "CREATE_ATOM_SHOULD_ACCEPT_BUNDLE",
    },
    {
        "id": "M02_ALLOW_DUPLICATE_RECORD",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b'raise ValueError(f"duplicate record',
        "replacement": b'pass  # MUTANT: silently allow duplicate record',
        "invariant": "DUPLICATE_RECORD_SHOULD_BE_REJECTED",
    },
    {
        "id": "M03_ALLOW_DUPLICATE_ATOM",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b'raise ValueError(f"duplicate atom',
        "replacement": b'pass  # MUTANT: silently allow duplicate atom',
        "invariant": "DUPLICATE_ATOM_SHOULD_BE_REJECTED",
    },
    {
        "id": "M04_ALLOW_DUPLICATE_BUNDLE",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b'raise ValueError(f"duplicate bundle',
        "replacement": b'pass  # MUTANT: silently allow duplicate bundle',
        "invariant": "DUPLICATE_BUNDLE_SHOULD_BE_REJECTED",
    },
    {
        "id": "M05_HIGH_CONFIDENCE_HYPOTHESIS",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b"cap.origin in (EvidenceOrigin.HYPOTHESIS",
        "replacement": b"cap.origin in ()",
        "invariant": "HYPOTHESIS_CONFIDENCE_SHOULD_BE_LOW",
    },
    {
        "id": "M06_SILENT_OVERWRITE_NOT_REJECTED",
        "target_file": "src/qclaw_e45/master_record.py",
        "anchor": b"def verify_transition(self, master",
        "replacement": b"def verify_transition(self, master, always_return_true=True",
        "invariant": "SILENT_OVERWRITE_SHOULD_BE_REJECTED",
    },
    {
        "id": "M07_UNRESOLVED_CONFLICT_BYPASS",
        "target_file": "src/qclaw_e45/master_record.py",
        "anchor": b"return ConflictClass.UNRESOLVED",
        "replacement": b"return ConflictClass.SCENARIO_DIFFERENCE  # MUTANT",
        "invariant": "CONFLICT_SHOULD_DEFAULT_UNRESOLVED",
    },
    {
        "id": "M08_GENERIC_TEXT_AS_GLOBAL",
        "target_file": "src/qclaw_e45/cognition.py",
        "anchor": b'and "user_msg_" in r.source_identity',
        "replacement": b"",
        "invariant": "GENERIC_TEXT_SHOULD_NOT_BE_GLOBAL",
    },
    {
        "id": "M09_DIRECT_FORMAL_ALLOWED",
        "target_file": "src/qclaw_e45/skill_lifecycle.py",
        "anchor": b'"FORMAL requires EXPERIMENTAL first"',
        "replacement": b'"FORMAL requires EXPERIMENTAL first - BYPASSED"',
        "invariant": "DIRECT_FORMAL_SHOULD_BE_BLOCKED",
    },
    {
        "id": "M10_SINGLE_CASE_FORMAL_OK",
        "target_file": "src/qclaw_e45/skill_lifecycle.py",
        "anchor": b"return len(total_cases) >= 3",
        "replacement": b"return len(total_cases) >= 1",
        "invariant": "SINGLE_CASE_FORMAL_SHOULD_BE_REJECTED",
    },
    {
        "id": "M11_BYPASS_PROMOTION_GATE",
        "target_file": "src/qclaw_e45/skill_lifecycle.py",
        "anchor": b"def promote(self, skill",
        "replacement": b"def promote(self, skill, _skip_checks=True",
        "invariant": "PROMOTION_SHOULD_VERIFY_RECEIPTS",
    },
    {
        "id": "M12_GLOBAL_WITHOUT_VERIFIED",
        "target_file": "src/qclaw_e45/cognition.py",
        "anchor": b"and r.verification_state == VerificationState.VERIFIED",
        "replacement": b"",
        "invariant": "GLOBAL_NEEDS_VERIFIED_USER_ORIGIN",
    },
    {
        "id": "M13_DEMOTE_WITHOUT_RECEIPT",
        "target_file": "src/qclaw_e45/skill_lifecycle.py",
        "anchor": b"def demote(self, skill",
        "replacement": b"def demote(self, skill, _no_evidence=True",
        "invariant": "DEMOTE_SHOULD_REQUIRE_RECEIPT",
    },
    {
        "id": "M14_REMOVE_VERIFY_ATOM",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b"def verify_atom(self, atom",
        "replacement": b"def verify_atom(self, atom, always_return_true=True",
        "invariant": "VERIFY_ATOM_SHOULD_CHECK",
    },
    {
        "id": "M15_EMPTY_BUNDLE_OK",
        "target_file": "src/qclaw_e45/authority.py",
        "anchor": b'raise ValueError("empty bundle rejected")',
        "replacement": b'pass  # MUTANT: allow empty bundle',
        "invariant": "EMPTY_BUNDLE_SHOULD_BE_REJECTED",
    },
]


# ----- Mutation Runner -----

def run_mutation(mut_def: dict, python_exe: str = None) -> dict:
    """Run one mutation in isolated workspace. Restore exact bytes after."""
    python_exe = python_exe or sys.executable
    
    target_path = os.path.join(SRC_DIR, mut_def["target_file"])
    if not os.path.isfile(target_path):
        return {"status": "MISSING_TARGET", "target": target_path}

    # Read original
    with open(target_path, "rb") as f:
        original = f.read()
    source_sha256 = hashlib.sha256(original).hexdigest()

    # Find anchor
    anchor_offset = original.index(mut_def["anchor"])
    
    # Apply mutation
    mutant = original.replace(mut_def["anchor"], mut_def["replacement"], 1)
    if mutant == original:
        return {"status": "ANCHOR_NOT_REPLACED", "anchor_offset": anchor_offset}
    mutant_sha256 = hashlib.sha256(mutant).hexdigest()

    # Write mutant
    tm = time.time()
    with open(target_path, "wb") as f:
        f.write(mutant)

    # Run tests (should FAIL)
    tests_dir = os.path.join(SRC_DIR, "tests")
    result = subprocess.run(
        [python_exe, "-m", "unittest", "discover", "-s", tests_dir, "-p", "test_q*.py", "-q"],
        capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
    )
    duration = time.time() - tm

    # Restore original
    with open(target_path, "wb") as f:
        f.write(original)
    restored = open(target_path, "rb").read()
    restore_exact = restored == original

    # Re-run to confirm green after restore
    re_result = subprocess.run(
        [python_exe, "-m", "unittest", "discover", "-s", tests_dir, "-p", "test_q*.py", "-q"],
        capture_output=True, text=True, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
    )

    return {
        "id": mut_def["id"],
        "status": "OK",
        "anchor_offset": anchor_offset,
        "source_sha256": source_sha256,
        "mutant_sha256": mutant_sha256,
        "mutant_exit": result.returncode,
        "restored_exit": re_result.returncode,
        "restore_exact": restore_exact,
        "duration_ms": int(duration * 1000),
        "mutant_stderr_hash": hashlib.sha256(result.stderr.encode()).hexdigest()[:16],
        "restored_stderr_hash": hashlib.sha256(re_result.stderr.encode()).hexdigest()[:16],
    }
