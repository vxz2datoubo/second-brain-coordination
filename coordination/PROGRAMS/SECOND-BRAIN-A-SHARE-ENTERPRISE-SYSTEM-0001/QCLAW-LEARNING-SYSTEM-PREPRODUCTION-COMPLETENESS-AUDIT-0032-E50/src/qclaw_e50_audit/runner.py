"""E50 R2 audit runner: orchestrates D1-D12 against canonical implementations.

Usage:
    python -m qclaw_e50_audit.runner
or:
    from qclaw_e50_audit.runner import run_audit
    result = run_audit()
"""
from __future__ import annotations

import json
import os
import sys

from . import coverage as coverage_mod
from . import recommendation as recommendation_mod
from .evidence_matrix import EvidenceMatrix
from . import authoritative as access
from .dimensions import (
    d1_ingestion, d2_reconstruction, d3_atom_taxonomy, d4_cross_source,
    d5_evidence, d6_cognition, d7_skill_promotion, d8_retrieval,
    d9_codex_boundary, d10_adversarial, d11_determinism, d12_resource,
)


DIMENSION_MODULES = [
    d1_ingestion,
    d2_reconstruction,
    d3_atom_taxonomy,
    d4_cross_source,
    d5_evidence,
    d6_cognition,
    d7_skill_promotion,
    d8_retrieval,
    d9_codex_boundary,
    d10_adversarial,
    d11_determinism,
    d12_resource,
]


def run_audit() -> dict:
    access.setup_import_path()
    bindings = access.canonical_ref_bindings()
    head_sha = bindings["audited_head_sha"]

    dimensions = [m.run() for m in DIMENSION_MODULES]
    matrix = EvidenceMatrix(
        canonical_head_sha=head_sha,
        audited_tree_root=str(access.REPO_ROOT),
        dimensions=dimensions,
    )
    cov = coverage_mod.build_coverage_report()
    rec = recommendation_mod.recommend(dimensions)

    result = {
        "canonical_head_sha": head_sha,
        "canonical_ref_bindings": bindings,
        "matrix": matrix.to_dict(),
        "coverage": cov.to_dict(),
        "recommendation": rec,
    }
    return result


def main() -> int:
    result = run_audit()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
