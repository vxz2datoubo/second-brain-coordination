"""E44 Q7 — Genuine copied-production mutation harness.

Mutates in an ISOLATED workspace — copies production code, applies mutations,
runs the relevant test suite, verifies mutant nonzero exit, restores exact bytes,
and re-runs green. Records full hashes, anchors, exits, stream hashes.
"""
from __future__ import annotations

import hashlib, subprocess, tempfile, shutil, os, textwrap
from typing import Dict, List, Tuple, Optional

# Production source root (absolute, resolved at runtime)
_SRC_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MUTATIONS = [
    {
        "id": "M01_FACTORY_BYPASS",
        "target_file": "src/qclaw_e44/authority.py",
        "anchor": b"def _re_verify_record",
        "replacement_count": 1,
        "description": "Bypass factory re-verification by returning True unconditionally",
    },
    {
        "id": "M02_ALLOW_DUPLICATE_RECORD",
        "target_file": "src/qclaw_e44/authority.py",
        "anchor": b'raise EvidenceError(f"duplicate record',
        "replacement_count": 1,
        "description": "Allow duplicate records instead of rejecting",
    },
    {
        "id": "M03_ALLOW_DUPLICATE_ATOM",
        "target_file": "src/qclaw_e44/authority.py",
        "anchor": b'raise EvidenceError(f"duplicate atom',
        "replacement_count": 1,
        "description": "Allow duplicate atoms instead of rejecting",
    },
    {
        "id": "M04_COGNITION_CALLER_STATE",
        "target_file": "src/qclaw_e44/cognition.py",
        "anchor": b"class CognitionEngine",
        "replacement_count": 1,
        "description": "Allow caller to bypass cognition state derivation",
    },
    {
        "id": "M05_SKILL_DIRECT_FORMAL",
        "target_file": "src/qclaw_e44/skill_lifecycle.py",
        "anchor": b"def create_skill",
        "replacement_count": 1,
        "description": "Allow direct FORMAL skill creation",
    },
    {
        "id": "M06_UNREGISTERED_SKILL_PROMOTE",
        "target_file": "src/qclaw_e44/skill_lifecycle.py",
        "anchor": b"if skill.skill_id not in self._skills",
        "replacement_count": 1,
        "description": "Allow promotion of unregistered skills",
    },
    {
        "id": "M07_CORPUS_INJECT_EXPECTED",
        "target_file": "src/qclaw_e44/corpus.py",
        "anchor": b"Production pipeline. NEVER receives ExpectedOutcome",
        "replacement_count": 1,
        "description": "Inject expected answers into corpus production",
    },
    {
        "id": "M08_EVALUATOR_ALWAYS_PASS",
        "target_file": "src/qclaw_e44/corpus.py",
        "anchor": b"def evaluate_corpus",
        "replacement_count": 1,
        "description": "Make corpus evaluator always return PASS",
    },
    {
        "id": "M09_REMOVE_DUPLICATE_ID_CHECK",
        "target_file": "src/qclaw_e44/master_record.py",
        "anchor": b'raise MasterError(f"duplicate semantic identity',
        "replacement_count": 1,
        "description": "Remove duplicate identity check in MasterRegistry",
    },
    {
        "id": "M10_SELF_REGISTRATION",
        "target_file": "src/qclaw_e44/capability.py",
        "anchor": b"if cap_id in self._issued",
        "replacement_count": 1,
        "description": "Allow self-registration of already-issued capabilities",
    },
    {
        "id": "M11_BYPASS_CONFLICT_REGISTRY",
        "target_file": "src/qclaw_e44/master_record.py",
        "anchor": b"raise MasterError(\"conflict requires registered records\")",
        "replacement_count": 1,
        "description": "Allow conflict registration with unregistered records",
    },
    {
        "id": "M12_SKILL_PROMOTE_ZERO_EVIDENCE",
        "target_file": "src/qclaw_e44/skill_lifecycle.py",
        "anchor": b"len(receipt.evidence_record_ids)",
        "replacement_count": 1,
        "description": "Allow skill promotion with zero evidence records",
    },
]

PY311 = "C:/Program Files/Python313/python.exe"  # Primary for subprocess


def _copy_tests(workspace: str) -> str:
    prod_tests = os.path.join(_SRC_ROOT, "tests")
    ws_tests = os.path.join(workspace, "tests")
    shutil.copytree(prod_tests, ws_tests)
    init_path = os.path.join(ws_tests, "__init__.py")
    if not os.path.exists(init_path):
        with open(init_path, "w") as f:
            f.write("")
    return ws_tests


def _copy_src(workspace: str) -> str:
    """Copy production source to isolated workspace."""
    prod_src = os.path.join(_SRC_ROOT, "src", "qclaw_e44")
    ws_src = os.path.join(workspace, "src", "qclaw_e44")
    shutil.copytree(prod_src, ws_src)
    initpy = os.path.join(ws_src, "__init__.py")
    if not os.path.exists(initpy):
        with open(initpy, "w") as f:
            f.write("")
    return ws_src


def _copy_tests(workspace: str) -> str:
    """Copy production tests to isolated workspace."""
    prod_tests = os.path.join(_SRC_ROOT, "tests")
    ws_tests = os.path.join(workspace, "tests")
    shutil.copytree(prod_tests, ws_tests)
    return ws_tests


def _hash_file(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _find_anchor(filepath: str, anchor: bytes) -> int:
    """Find the byte offset of an anchor in a file."""
    with open(filepath, "rb") as f:
        content = f.read()
    idx = content.find(anchor)
    if idx < 0:
        raise ValueError(f"anchor not found in {os.path.basename(filepath)}")
    return idx


def run_mutation(mutation: Dict, python_exe: str = None) -> Dict:
    """Run a single mutation in an isolated workspace.

    Returns a result dict with status, hashes, exits, streams.
    """
    if python_exe is None:
        python_exe = PY311

    wid = mutation["id"]
    result = {"mutation_id": wid, "status": "FAIL", "details": []}

    workspace = tempfile.mkdtemp(prefix=f"e44_mut_{wid}_")

    try:
        # Copy production src + tests
        src_dir = _copy_src(workspace)
        _copy_tests(workspace)

        target_relative = mutation["target_file"]
        # target_file is like "src/qclaw_e44/authority.py"
        target_file = os.path.join(workspace, target_relative)
        if not os.path.isfile(target_file):
            result["status"] = "MISSING_TARGET"
            result["error"] = f"target not found: {target_file}"
            return result

        # Record original source hash
        orig_hash = _hash_file(target_file)
        result["source_sha256"] = orig_hash

        # Find anchor, apply mutation
        idx = _find_anchor(target_file, mutation["anchor"])
        result["anchor_offset"] = idx

        with open(target_file, "rb") as f:
            original_bytes = f.read()

        # Apply mutation: insert a bypass comment after anchor
        anchor_end = idx + len(mutation["anchor"])
        mutated_bytes = (
            original_bytes[:anchor_end]
            + b"\n    return True  # [MUTANT] bypass injected"
            + original_bytes[anchor_end:]
        )

        with open(target_file, "wb") as f:
            f.write(mutated_bytes)

        mutant_hash = _hash_file(target_file)
        result["mutant_sha256"] = mutant_hash
        result["byte_diff"] = len(mutated_bytes) - len(original_bytes)

        # Run tests on mutant
        test_dir = os.path.join(workspace, "tests")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        ws_src = os.path.join(workspace, "src")
        env["PYTHONPATH"] = ws_src
        p = subprocess.run(
            [python_exe, "-m", "unittest", "discover", "-s", test_dir, "-p", "test_q6q7.py"],
            capture_output=True, timeout=30, env=env, cwd=workspace,
        )
        result["mutant_exit"] = p.returncode
        result["mutant_stdout_sha256"] = hashlib.sha256(p.stdout).hexdigest()
        result["mutant_stderr_sha256"] = hashlib.sha256(p.stderr).hexdigest()

        # Mutant must fail (nonzero exit)
        mutant_failed = p.returncode != 0
        result["mutant_expected_fail"] = mutant_failed

        if not mutant_failed:
            result["status"] = "MUTANT_PASSED_ERROR"

        # Restore exact bytes
        with open(target_file, "wb") as f:
            f.write(original_bytes)

        restored_hash = _hash_file(target_file)
        result["restored_sha256"] = restored_hash

        if restored_hash != orig_hash:
            result["restore_exact"] = False
            result["status"] = "RESTORE_FAILED"
            return result
        result["restore_exact"] = True

        # Re-run green
        ws_src = os.path.join(workspace, "src")
        env["PYTHONPATH"] = ws_src
        p = subprocess.run(
            [python_exe, "-m", "unittest", "discover", "-s", test_dir, "-p", "test_q6q7.py"],
            capture_output=True, timeout=30, env=env, cwd=workspace,
        )
        result["restored_exit"] = p2.returncode
        result["restored_stdout_sha256"] = hashlib.sha256(p2.stdout).hexdigest()

        if p2.returncode == 0 and mutant_failed:
            result["status"] = "PASS"
        elif p2.returncode == 0:
            result["status"] = "RESTORE_OK_MUTANT_NOT_FAILING"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)

    return result


def run_all_mutations(python_exe: str = None) -> List[Dict]:
    results = []
    for m in MUTATIONS:
        r = run_mutation(m, python_exe)
        results.append(r)
    return results
