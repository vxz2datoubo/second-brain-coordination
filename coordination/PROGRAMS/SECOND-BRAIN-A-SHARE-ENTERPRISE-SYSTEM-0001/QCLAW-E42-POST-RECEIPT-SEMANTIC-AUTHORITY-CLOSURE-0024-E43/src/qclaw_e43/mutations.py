"""
E43 Q7 — Real Copied-Production Mutations

Each mutation copies actual E43 production/evaluator code, applies a targeted
modification, executes the relevant test suite, verifies nonzero failure,
restores exact original bytes, and re-runs green.

No prefilled `failed=True`, import-only, or `assertTrue(True)` credit.
"""
from __future__ import annotations

import hashlib, os, subprocess, json, dataclasses, time, shutil
from typing import Dict, List, Tuple, Optional, Any

__all__ = ["Mutation", "MutationRunner", "build_mutations",
           "MUTATION_FAMILIES", "compute_file_hash"]


def compute_file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


@dataclasses.dataclass(frozen=True)
class Mutation:
    name: str
    family: str
    description: str
    file_path: str  # relative to src/qclaw_e43/
    anchor_line: int  # 1-indexed line where mutation is applied
    original_text: str  # exact original text to replace
    mutant_text: str  # replacement text that should cause test failure
    target_test: str  # test module name (e.g. "test_q1")

    def apply(self, src_dir: str) -> bool:
        """Apply mutation in-place. Returns True if applied."""
        full_path = os.path.join(src_dir, "qclaw_e43", self.file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if self.original_text not in content:
            return False
        content = content.replace(self.original_text, self.mutant_text, 1)
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return True

    def restore(self, src_dir: str) -> bool:
        """Restore original text. Returns True if restored."""
        full_path = os.path.join(src_dir, "qclaw_e43", self.file_path)
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        if self.mutant_text not in content:
            return False
        content = content.replace(self.mutant_text, self.original_text, 1)
        with open(full_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return True


# ── Mutation definitions ────────────────────────────────────────
MUTATION_FAMILIES = [
    "forgery", "factory_bypass", "mutable_alias", "omitted_field",
    "source_digest_forgery", "utf8_replacement", "dropped_structure",
    "arbitrary_interpretation", "duplicate_master", "silent_overwrite",
    "caller_cognition_certain", "skill_direct_formal",
    "corpus_drift", "evaluator_bypass", "receipt_topology",
]


def build_mutations() -> Tuple[List[Mutation], str]:
    """Build all E43 mutations. Returns (mutations, harness_hash)."""
    mutations = [
        # M01: Forge atom outside factory (authority.py)
        Mutation(
            name="M01_ATOM_FORGERY", family="forgery",
            description="Tamper atom factory_signature to test verifier rejects forgeries",
            file_path="authority.py", anchor_line=260,
            original_text="return self._secret.verify(payload.encode(), atom.factory_signature)",
            mutant_text="return True  # BYPASSED: accept any signature",
            target_test="test_q1",
        ),
        # M02: Bypass EvidenceFactory signature (authority.py)
        Mutation(
            name="M02_EVIDENCE_FACTORY_BYPASS", family="factory_bypass",
            description="Bypass EvidenceFactory record verification",
            file_path="authority.py", anchor_line=285,
            original_text="return self._secret.verify(payload.encode(), record.factory_signature)",
            mutant_text="return True  # FORGERY_BYPASS",
            target_test="test_q1",
        ),
        # M03: Remove strict UTF-8 check (source_trace.py)
        Mutation(
            name="M03_REMOVE_UTF8_CHECK", family="utf8_replacement",
            description="Remove strict UTF-8 decoding → invalid bytes pass silently",
            file_path="source_trace.py", anchor_line=60,
            original_text="data.decode(\"utf-8\")",
            mutant_text="data.decode(\"utf-8\", errors=\"replace\")",
            target_test="test_q2q6",
        ),
        # M04: Skip overlap detection in partition (source_trace.py)
        Mutation(
            name="M04_SKIP_OVERLAP_DETECTION", family="dropped_structure",
            description="Skip overlap check → overlapping spans allowed",
            file_path="source_trace.py", anchor_line=100,
            original_text='raise ValueError(f"[overlap] at byte {i}")',
            mutant_text="pass  # MUTANT: skip overlap",
            target_test="test_q2q6",
        ),
        # M05: Allow duplicate semantic identity (master_record.py)
        Mutation(
            name="M05_ALLOW_DUPLICATE_MASTER", family="duplicate_master",
            description="Allow duplicate semantic identity in master registry",
            file_path="master_record.py", anchor_line=163,
            original_text='raise ValueError(f"REGISTRY_REJECTED: duplicate semantic identity {sid}")',
            mutant_text='return MasterRecord(rid, content)  # MUTANT: silently create duplicate',
            target_test="test_q2q6",
        ),
        # M06: Bypass transition evidence check (master_record.py)
        Mutation(
            name="M06_BYPASS_TRANSITION_EVIDENCE", family="silent_overwrite",
            description="Allow transition without evidence",
            file_path="master_record.py", anchor_line=120,
            original_text="return bool(evidence_record_id and len(evidence_record_id) > 0)",
            mutant_text="return True  # MUTANT: always allow transition",
            target_test="test_q2q6",
        ),
        # M07: CognitionEngine bypasses registry (cognition.py)
        Mutation(
            name="M07_COGNITION_REGISTRY_BYPASS", family="caller_cognition_certain",
            description="Skip evidence registry verification in cognition",
            file_path="cognition.py", anchor_line=68,
            original_text='raise ValueError("REGISTRY_REJECTED: evidence record not in registry")',
            mutant_text='pass  # MUTANT: skip registry check',
            target_test="test_q2q6",
        ),
        # M08: Skill formal without gate check (skill_lifecycle.py)
        Mutation(
            name="M08_SKILL_DIRECT_FORMAL", family="skill_direct_formal",
            description="Allow creating skill directly in FORMAL state",
            file_path="skill_lifecycle.py", anchor_line=144,
            original_text='f"{sid}|{name}|{SkillState.CANDIDATE.value}"',
            mutant_text='f"{sid}|{name}|{SkillState.FORMAL.value}"',
            target_test="test_q2q6",
        ),
        # M09: Remove promotion gate check (skill_lifecycle.py)
        Mutation(
            name="M09_SKIP_PROMOTION_GATE", family="skill_direct_formal",
            description="Skip promotion gate check → any transition allowed",
            file_path="skill_lifecycle.py", anchor_line=173,
            original_text='raise ValueError(f"PROMOTION_REJECTED: gate not satisfied for candidate→experimental")',
            mutant_text='pass  # MUTANT: skip gate check',
            target_test="test_q2q6",
        ),
        # M10: Corpus drift — change expected outcome (corpus.py)
        Mutation(
            name="M10_CORPUS_DRIFT", family="corpus_drift",
            description="Change expected outcome of a corpus case → evaluator should catch",
            file_path="corpus.py", anchor_line=305,
            original_text='ExpectedOutcome(atom_type=AtomType.CONCEPT, should_succeed=True, min_stability=0.4)',
            mutant_text='ExpectedOutcome(atom_type=AtomType.FAILURE_CONDITION, should_succeed=False, min_stability=0.99)',
            target_test="test_q2q6",
        ),
        # M11: Evaluator always PASS (corpus.py)
        Mutation(
            name="M11_EVALUATOR_ALWAYS_PASS", family="evaluator_bypass",
            description="CorpusEvaluator always returns PASS",
            file_path="corpus.py", anchor_line=260,
            original_text='result["verdict"] = "FAIL"',
            mutant_text='if False:  # MUTANT: never fail\n            result["verdict"] = "FAIL"',
            target_test="test_q2q6",
        ),
        # M12: Remove empty input check (corpus.py)
        Mutation(
            name="M12_REMOVE_EMPTY_CHECK", family="evaluator_bypass",
            description="Don't check should_succeed flag in evaluator",
            file_path="corpus.py", anchor_line=257,
            original_text="if not case.expected.should_succeed:",
            mutant_text="if False:  # MUTANT: never check should_succeed",
            target_test="test_q2q6",
        ),
        # M13: Authority registry allows unregistered atom (authority.py)
        Mutation(
            name="M13_ALLOW_UNREGISTERED_ATOM", family="forgery",
            description="Atom verification skip registry lookup",
            file_path="authority.py", anchor_line=300,
            original_text="raise ValueError(f\"REGISTRY_REJECTED: duplicate atom {atom.atom_id}\")",
            mutant_text="pass  # MUTANT: allow duplicate atom silently",
            target_test="test_q1",
        ),
        # M14: Remove record verification in bundle (authority.py)
        Mutation(
            name="M14_SKIP_RECORD_VERIFY_IN_BUNDLE", family="omitted_field",
            description="Bundle verify skips per-record verification",
            file_path="authority.py", anchor_line=240,
            original_text="for r in self.records:\n            if not r.verify(registry, factory):\n                return False",
            mutant_text="# MUTANT: records skipped\n        pass",
            target_test="test_q1",
        ),
        # M15: Allow inverted span (source_trace.py)
        Mutation(
            name="M15_ALLOW_INVERTED_SPAN", family="dropped_structure",
            description="Allow inverted byte ranges in SourceDocument",
            file_path="source_trace.py", anchor_line=91,
            original_text='raise ValueError(f"[inverted] {byte_start}:{byte_end}")',
            mutant_text="pass  # MUTANT: allow inverted spans",
            target_test="test_q2q6",
        ),
    ]

    # Compute harness hash
    h = hashlib.sha256()
    for m in sorted(mutations, key=lambda x: x.name):
        h.update(m.name.encode())
        h.update(m.family.encode())
        h.update(m.file_path.encode())
        h.update(m.original_text.encode())
        h.update(m.mutant_text.encode())
    harness_hash = h.hexdigest()

    return mutations, harness_hash


class MutationRunner:
    """Executes mutations: apply→test→verify_fail→restore→test→verify_pass→record"""

    def __init__(self, src_dir: str, tests_dir: str, python_path: str):
        self.src_dir = os.path.abspath(src_dir)
        self.tests_dir = os.path.abspath(tests_dir)
        self.python = python_path
        self.results: List[Dict] = []

    def run_all(self, mutations: List[Mutation]) -> Dict:
        """Run all mutations. Returns summary dict."""
        for m in mutations:
            result = self.run_one(m)
            self.results.append(result)

        passed = sum(1 for r in self.results if r["verdict"] == "PASS")
        failed = sum(1 for r in self.results if r["verdict"] != "PASS")
        return {
            "total": len(mutations),
            "passed": passed,
            "failed": failed,
            "results": self.results,
        }

    def run_one(self, m: Mutation) -> Dict:
        """Run one mutation: apply→fail→restore→pass"""
        result = {"name": m.name, "family": m.family, "verdict": "PASS"}
        full_path = os.path.join(self.src_dir, "qclaw_e43", m.file_path)

        # Pre-hash
        original_hash = compute_file_hash(full_path)

        # Apply mutation
        applied = m.apply(self.src_dir)
        if not applied:
            result["verdict"] = "FAIL"
            result["error"] = "apply_failed: text not found"
            return result
        result["original_hash"] = original_hash
        mutant_hash = compute_file_hash(full_path)
        result["mutant_hash"] = mutant_hash

        # Run test — MUST FAIL
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        p = subprocess.run(
            [self.python, "-m", "unittest", f"tests.{m.target_test}"],
            cwd=os.path.dirname(self.src_dir) + "/..",
            capture_output=True, text=True, timeout=30, env=env,
        )
        mutant_exit = p.returncode
        result["mutant_exit"] = mutant_exit
        result["mutant_stderr_hash"] = hashlib.sha256(p.stderr.encode()).hexdigest()[:16]

        if mutant_exit == 0:
            result["verdict"] = "FAIL"
            result["error"] = "mutant_did_not_fail: exit 0 when mutation should cause failure"
            # Still restore
            m.restore(self.src_dir)
            return result

        # Restore
        m.restore(self.src_dir)
        restored_hash = compute_file_hash(full_path)
        result["restored_hash"] = restored_hash
        result["restored_matches_original"] = (restored_hash == original_hash)

        if restored_hash != original_hash:
            result["verdict"] = "FAIL"
            result["error"] = "restore_mismatch"
            return result

        # Re-run test — MUST PASS
        p2 = subprocess.run(
            [self.python, "-m", "unittest", f"tests.{m.target_test}"],
            cwd=os.path.dirname(self.src_dir) + "/..",
            capture_output=True, text=True, timeout=30, env=env,
        )
        restored_exit = p2.returncode
        result["restored_exit"] = restored_exit

        if restored_exit != 0:
            result["verdict"] = "FAIL"
            result["error"] = f"restore_still_fails: exit={restored_exit}"
            return result

        return result
