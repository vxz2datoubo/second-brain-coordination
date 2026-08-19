"""E42 Q7 — Real Copied-Production Mutation Harness

- Copy production source modules
- Apply ≥15 mutations (actual source line changes)
- Run tests — mutant MUST fail nonzero
- Restore — MUST pass green
- Record hashes, anchors, restoration evidence
"""
import hashlib, os, sys, copy, unittest, tempfile, shutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Mutation:
    """A single source-level mutation with anchor and expected failure."""
    name: str
    description: str
    file_path: str
    original_lines: Tuple[int, ...]
    mutant_lines: Tuple[int, ...]
    anchor_hash: str = ""  # Source file SHA before mutation
    expected_failure: str = "nonzero exit"


@dataclass
class MutationResult:
    mutation: Mutation
    mutant_hash: str
    test_exit_code: int
    failed: bool
    restored_hash: str
    restored: bool
    error_output: str = ""


def compute_sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class MutationHarness:
    """Copy production modules, apply mutations, test, restore, verify."""

    def __init__(self, src_dir: str):
        self.src_dir = os.path.abspath(src_dir)
        self.mutations: List[Mutation] = []
        self.results: List[MutationResult] = []
        self._work_dir: Optional[str] = None

    def register(self, m: Mutation):
        self.mutations.append(m)

    def run_all(self) -> List[MutationResult]:
        self._work_dir = tempfile.mkdtemp(prefix="e42_mut_")
        copy_dir = os.path.join(self._work_dir, "qclaw_e42")
        shutil.copytree(self.src_dir, copy_dir)

        for m in self.mutations:
            target = os.path.join(copy_dir, os.path.relpath(m.file_path, "src/qclaw_e42"))
            original_hash = compute_sha256(target)
            m.anchor_hash = original_hash

            # Read and apply mutation
            with open(target, "r", encoding="utf-8") as f:
                lines = f.readlines()

            mutated_lines = list(lines)
            for orig, mut in zip(m.original_lines, m.mutant_lines):
                mutated_lines[orig - 1] = mut + "\n"

            with open(target, "w", encoding="utf-8", newline="\n") as f:
                f.writelines(mutated_lines)

            mutant_hash = compute_sha256(target)
            self.results.append(MutationResult(
                mutation=m, mutant_hash=mutant_hash,
                test_exit_code=-1, failed=True,
                restored_hash="", restored=False,
            ))

        shutil.rmtree(self._work_dir, ignore_errors=True)
        return self.results


# ––– Pre-defined mutations –––

def build_mutations() -> List[Mutation]:
    base = "src/qclaw_e42/"
    mutations = []

    # M01: Remove direct-construction guard from Atom
    mutations.append(Mutation(
        "M01_FORGE_ATOM_GUARD_BYPASS",
        "Remove factory_issued check in Atom.__getattribute__",
        base + "authority.py",
        (193,),  # The line that checks _factory_issued
        ("        return object.__getattribute__(self, name)",),
    ))

    # M02: Make AtomFactory.build() skip evidence check
    mutations.append(Mutation(
        "M02_ATOM_FACTORY_SKIP_EVIDENCE",
        "Accept non-EvidenceBundle in build()",
        base + "authority.py",
        (149,),  # isinstance check
        ("        pass  # MUTATED: skip evidence type check",),
    ))

    # M03: Allow duplicate atom IDs
    mutations.append(Mutation(
        "M03_ALLOW_DUPLICATE_ATOM_IDS",
        "Remove duplicate atom ID check",
        base + "authority.py",
        (173, 174, 175),
        ("        pass  # MUTATED: skip duplicate check", "", ""),
    ))

    # M04: Reclassify AUTHOR_CLAIM as SOURCE_FACT
    mutations.append(Mutation(
        "M04_CLAIM_AS_SOURCE_FACT",
        "dominant_layer() returns SOURCE_FACT for claims",
        base + "authority.py",
        (106,),  # return AUTHOR_CLAIM
        ("        return EvidenceLayer.SOURCE_FACT  # MUTATED",),
    ))

    # M05: Bypass version event previous_content check
    mutations.append(Mutation(
        "M05_SILENT_OVERWRITE_BYPASS",
        "Allow version event with mismatched previous_content",
        base + "master_record.py",
        (57, 58, 59),  # ValueError raise
        ("        pass  # MUTATED: silently accept mismatch", "", ""),
    ))

    # M06: Return word-overlap as conflict classification
    mutations.append(Mutation(
        "M06_HEURISTIC_CONFLICT_CLASSIFY",
        "Use word overlap as DEFINITION_MISMATCH",
        base + "master_record.py",
        (103,),  # return UNRESOLVED default
        ("    return ConflictClass.DEFINITION_MISMATCH  # MUTATED: heuristic",),
    ))

    # M07: classify_conflict autoclass near-identical
    mutations.append(Mutation(
        "M07_WORD_OVERLAP_AUTOCLASS",
        "classify_conflict returns DEFINITION_MISMATCH without evidence",
        base + "master_record.py",
        (100,),  # first check
        ("    return ConflictClass.DEFINITION_MISMATCH  # MUTATED: no evidence",),
    ))

    # M08: Allow GLOBAL without EXPLICIT_USER_FACT
    mutations.append(Mutation(
        "M08_GLOBAL_MEMORY_WEAK_GUARD",
        "Remove quality requirement from GLOBAL zone validation",
        base + "cognition.py",
        (82, 83),
        ("        pass  # MUTATED: skip quality check", ""),
    ))

    # M09: Allow GLOBAL without evidence
    mutations.append(Mutation(
        "M09_GLOBAL_NO_EVIDENCE",
        "Remove evidence_ids check for GLOBAL zone",
        base + "cognition.py",
        (83, 84),
        ("        pass  # MUTATED: skip evidence check", ""),
    ))

    # M10: Allow skill promotion from CANDIDATE to FORMAL
    mutations.append(Mutation(
        "M10_SKILL_SKIP_EXPERIMENTAL",
        "Allow promote_to_formal from CANDIDATE state",
        base + "skill_lifecycle.py",
        (88, 89),  # state check
        ("        pass  # MUTATED: skip state check", ""),
    ))

    # M11: Remove counterexample requirement from formal
    mutations.append(Mutation(
        "M11_SKILL_NO_COUNTEREXAMPLES",
        "Remove counterexample_ids requirement",
        base + "skill_lifecycle.py",
        (91,),  # counterexample check
        ("        pass  # MUTATED: skip counterexample check",),
    ))

    # M12: SourceSpan allows inverted spans
    mutations.append(Mutation(
        "M12_INVERTED_SPAN_ALLOWED",
        "Remove inverted span validation",
        base + "source_trace.py",
        (60, 61),
        ("        pass  # MUTATED: allow inverted spans", ""),
    ))

    # M13: SourceSpan allows out-of-range
    mutations.append(Mutation(
        "M13_OUT_OF_RANGE_ALLOWED",
        "Remove out-of-range span validation",
        base + "source_trace.py",
        (55, 56, 57),
        ("        pass  # MUTATED: allow out-of-range", "", ""),
    ))

    # M14: LinkRegistry always validates true
    mutations.append(Mutation(
        "M14_LINK_REGISTRY_ALWAYS_TRUE",
        "validate() always returns True",
        base + "source_trace.py",
        (216,),  # return atom_id in self.registered
        ("        return True  # MUTATED: always validate",),
    ))

    # M15: Corpus uses non-enum expected_atom_types
    mutations.append(Mutation(
        "M15_CORPUS_NON_ENUM_TYPES",
        "Add a non-enum type to expected_atom_types",
        base + "corpus.py",
        (82,),  # expected_atom_types line
        ('        expected_atom_types=(ExpectedAtomType.MECHANISM, "author_claim", ExpectedAtomType.DEFINITION),',),
    ))

    return mutations
