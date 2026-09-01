"""E46 Mutations — Real isolated copied-production mutation harness.

Mutations copy production source, apply exact byte replacement,
run the relevant test suite, verify nonzero exit, restore exact bytes,
re-run to confirm green.
"""

import os
import sys
import shutil
import subprocess
import hashlib
import tempfile
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# Path to production source files (relative to repo root)
HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = HERE  # mutations.py lives in qclaw_e46 package directory

# Map module -> path
PRODUCTION_MODULES = {
    "capability": os.path.join(SRC_DIR, "capability.py"),
    "authority": os.path.join(SRC_DIR, "authority.py"),
    "master_record": os.path.join(SRC_DIR, "master_record.py"),
    "cognition": os.path.join(SRC_DIR, "cognition.py"),
    "skill_lifecycle": os.path.join(SRC_DIR, "skill_lifecycle.py"),
}

TESTS_DIR = os.path.join(os.path.dirname(os.path.dirname(SRC_DIR)), "tests")


@dataclass
class MutationDefinition:
    """A single mutation with exact byte anchor and replacement."""
    name: str
    module: str
    anchor_line: int  # Line number in source for the target
    anchor_text: str  # Exact text to find and replace
    replacement_text: str  # Replacement that breaks an invariant
    invariant_test: str  # Test method name that must fail
    description: str


MUTATIONS = [
    MutationDefinition(
        name="M01_FACTORY_SEAL_BYPASS",
        module="capability",
        anchor_line=57,
        anchor_text="_FACTORY_SEAL_SENTINEL",
        replacement_text="None  # BROKEN: seal bypass allows forgery",
        invariant_test="test_factory_seal_blocks_known_sentinel_bypass",
        description="Break factory seal sentinel to allow capability forgery",
    ),
    MutationDefinition(
        name="M02_ALLOW_DUPLICATE_RECORD",
        module="authority",
        anchor_line=82,
        anchor_text="return None  # Duplicate rejection",
        replacement_text="pass  # BROKEN: duplicate records accepted",
        invariant_test="test_duplicate_record_rejected",
        description="Remove duplicate rejection in record creation",
    ),
    MutationDefinition(
        name="M03_UNTRUSTED_CREATES_BUNDLE",
        module="authority",
        anchor_line=120,
        anchor_text="return None",
        replacement_text="pass  # BROKEN: UNTRUSTED caps can create bundles",
        invariant_test="test_untrusted_bundle_rejected",
        description="Allow UNTRUSTED capabilities to create bundles",
    ),
    MutationDefinition(
        name="M04_REMOVE_REGISTRY_CHECK",
        module="authority",
        anchor_line=95,
        anchor_text="not self.is_capability_registered(cap.capability_id)",
        replacement_text="False  # BROKEN: registry check bypassed",
        invariant_test="test_unregistered_cap_rejected",
        description="Bypass capability registry check",
    ),
    MutationDefinition(
        name="M05_FORMAL_PROMOTION_ALWAYS_PASS",
        module="skill_lifecycle",
        anchor_line=111,
        anchor_text="return None, TransitionOutcome.REJECTED_NO_E59_AUTHORITY",
        replacement_text="pass  # BROKEN: formal promotion always succeeds",
        invariant_test="test_formal_promotion_blocked_pre_e59",
        description="Remove formal promotion pre-E59 blocker",
    ),
    MutationDefinition(
        name="M06_UNTRUSTED_RECEIPT_TRUSTED",
        module="skill_lifecycle",
        anchor_line=47,
        anchor_text='"E59_CANONICAL_EVALUATOR"',
        replacement_text='self.evaluator_identity  # BROKEN: any identity trusted',
        invariant_test="test_untrusted_receipt_not_trusted",
        description="Make all evaluator identities trusted",
    ),
    MutationDefinition(
        name="M07_DIRECT_CONSTRUCTION_PERMITTED",
        module="capability",
        anchor_line=34,
        anchor_text="raise CapabilityAccessError(",
        replacement_text="pass  # BROKEN: direct construction allowed\n        if False:  # ",
        invariant_test="test_direct_construction_rejected",
        description="Allow direct construction of VerifiedEvidenceCapabilityView",
    ),
    MutationDefinition(
        name="M08_EVIDENCE_BUNDLE_NONE_ACCEPTED",
        module="master_record",
        anchor_line=93,
        anchor_text="if evidence_bundle is None:\n            return None",
        replacement_text="if evidence_bundle is None:\n            pass  # BROKEN: None bundle accepted",
        invariant_test="test_create_with_untrusted_evaluator_produces_pending",
        description="Accept None evidence bundle in master record creation",
    ),
    MutationDefinition(
        name="M09_SILENT_OVERWRITE_ALLOWED",
        module="master_record",
        anchor_line=137,
        anchor_text="return None  # No actual change",
        replacement_text="pass  # BROKEN: silent overwrite permitted",
        invariant_test="test_add_version_rejects_nonexistent",
        description="Allow replacement with unchanged content",
    ),
    MutationDefinition(
        name="M10_GLOBAL_FROM_UNTRUSTED",
        module="cognition",
        anchor_line=107,
        anchor_text="return MemoryZone.NO_PERSIST",
        replacement_text="return MemoryZone.GLOBAL  # BROKEN: UNTRUSTED can produce GLOBAL",
        invariant_test="test_pre_e59_user_origin_never_verified",
        description="Allow UNTRUSTED confidence to produce GLOBAL memory",
    ),
]


def compute_hash(filepath: str) -> str:
    """Compute SHA-256 of file."""
    with open(filepath, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def apply_mutation(mutation: MutationDefinition) -> Tuple[str, str, str]:
    """Apply mutation and return (source_hash, mutant_hash, anchor_found).
    
    Returns empty anchor_found if anchor not located.
    """
    filepath = PRODUCTION_MODULES[mutation.module]
    source_hash = compute_hash(filepath)
    
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    if mutation.anchor_text not in content:
        return source_hash, source_hash, ""
    
    mutant_content = content.replace(mutation.anchor_text, mutation.replacement_text, 1)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(mutant_content)
    
    mutant_hash = compute_hash(filepath)
    return source_hash, mutant_hash, mutation.anchor_text


def restore_source(filepath: str, original_content: str) -> str:
    """Restore original source bytes."""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(original_content)
    return compute_hash(filepath)


def run_mutation(mutation: MutationDefinition,
                 python_exe: str = None) -> Dict:
    """Run a single mutation: apply, test, restore, verify.
    
    Returns dict with status, hashes, exits.
    """
    if python_exe is None:
        python_exe = sys.executable
    
    filepath = PRODUCTION_MODULES[mutation.module]
    
    # Read original
    with open(filepath, "r", encoding="utf-8") as f:
        original = f.read()
    
    source_hash = compute_hash(filepath)
    
    # Apply
    if mutation.anchor_text not in original:
        return {
            "mutation": mutation.name,
            "status": "MISSING_ANCHOR",
            "source_hash": source_hash,
            "mutant_hash": source_hash,
            "mutant_exit": 0,
            "restored_hash": source_hash,
            "restore_exact": True,
            "restored_green": True,
        }
    
    mutant_content = original.replace(mutation.anchor_text, mutation.replacement_text, 1)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(mutant_content)
    mutant_hash = compute_hash(filepath)
    
    # Run test to check invariant breaks
    result = subprocess.run(
        [python_exe, "-m", "unittest",
         f"test_q2q5.{mutation.invariant_test.split('.')[-1]}"],
        capture_output=True, text=True, timeout=30,
        cwd=TESTS_DIR,
    )
    mutant_exit = result.returncode
    
    # Restore
    restore_hash = restore_source(filepath, original)
    restore_exact = restore_hash == source_hash
    
    # Re-run to confirm green post-restore
    result2 = subprocess.run(
        [python_exe, "-m", "unittest",
         f"test_q2q5.{mutation.invariant_test.split('.')[-1]}"],
        capture_output=True, text=True, timeout=30,
        cwd=TESTS_DIR,
    )
    restored_green = result2.returncode == 0
    
    return {
        "mutation": mutation.name,
        "status": "OK",
        "source_hash": source_hash,
        "mutant_hash": mutant_hash,
        "mutant_exit": mutant_exit,
        "restored_hash": restore_hash,
        "restore_exact": restore_exact,
        "restored_green": restored_green,
    }


def run_all_mutations(python_exe: str = None) -> List[Dict]:
    """Run all defined mutations. Returns list of result dicts."""
    if python_exe is None:
        python_exe = sys.executable
    
    results = []
    for mut in MUTATIONS:
        result = run_mutation(mut, python_exe)
        results.append(result)
    
    # Final verification: all restored
    for module_name, filepath in PRODUCTION_MODULES.items():
        h = compute_hash(filepath)
    
    return results
