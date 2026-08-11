"""Generate the canary projection JSON for E48.

Reads the synthetic Chinese canary, runs the L1 reconstructor, builds a
minimal E47-style L2 package, projects to L3, and writes both
``canary_graph.json`` and ``canary_digests.json`` so the visualization
generator and the E61 digest tests have stable inputs.

This script is deterministic: identical invocation → identical bytes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Load E47 stub for typing and engine contracts.
import importlib.util as _ilu
_sys = sys.modules
_SPEC = _ilu.spec_from_file_location("qclaw_e47_digest", str(ROOT / "tests" / "_e47_stub.py"))
_e47 = _ilu.module_from_spec(_SPEC)
_sys["qclaw_e47_digest"] = _e47
_SPEC.loader.exec_module(_e47)

from qclaw_e48_reconstruction.digests import (  # noqa: E402
    canonical_semantic_sha256,
    l0_provenance_sha256,
    raw_artifact_sha256,
)
from qclaw_e48_reconstruction.l1_reconstruct import reconstruct  # noqa: E402
from qclaw_e48_reconstruction.l3_project import project_graph  # noqa: E402


CANARY_PATH = ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


def main() -> int:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0, view_id="E48-CANARY-001")
    src = _e47.ingest_source(
        l0, "workspace://canary/synthetic_canary_noisy_chinese.txt",
        "E48 PUBLIC_SAFE canary", "src-canary",
    )
    # 3 atoms spanning the canary: a concept, a mechanism, an unknown.
    a1 = _e47.source_extract(
        "A001", "MECHANISM", l0, 0, min(len(l0), 60), "HIGH",
        scope="canary", label="if-volume-then-price",
    )
    a2 = _e47.source_extract(
        "A002", "CONDITION", l0, 60, min(len(l0), 120), "MEDIUM",
        scope="canary", label="if-volume-then-tendency",
    )
    a3 = _e47.source_extract(
        "A003", "INDICATOR", l0, 120, min(len(l0), 180), "LOW",
        scope="canary", label="volume-as-key",
    )
    pkg = _e47.build_package(
        "E48-CANARY-PKG-001", src, [a1, a2, a3],
        relations=[
            _e47.Relation("A001", "A002", "SUPPORTS"),
            _e47.Relation("A002", "A003", "REFINES"),
        ],
        unknowns=[{
            "unknown_id": "U001",
            "question": "Who is 他 她 in the third paragraph?",
            "related_atom_ids": ["A001"],
        }],
        summary="canary mechanism / condition / unknown",
    )
    pkg_dict = pkg.to_dict()
    proj = project_graph(pkg_dict, view, projection_id="E48-CANARY-L3")

    out_dir = ROOT / "canary" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    proj_dict = proj.to_dict()
    proj_blob = json.dumps(proj_dict, ensure_ascii=False, sort_keys=True)
    (out_dir / "canary_graph.json").write_text(proj_blob, encoding="utf-8")
    (out_dir / "canary_l1_view.json").write_text(
        json.dumps(view.to_dict(), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    digests = {
        "raw_artifact_sha256": raw_artifact_sha256(
            json.dumps(pkg_dict, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ),
        "canonical_semantic_sha256": canonical_semantic_sha256(pkg_dict),
        "l0_provenance_sha256": l0_provenance_sha256(
            pkg_dict["source"], pkg_dict["atoms"]
        ),
        "projection_sha256": proj.projection_sha256,
        "view_sha256": view.view_sha256,
        "l0_source_sha256": view.l0_source_hash,
        "l0_source_size_bytes": view.l0_source_size_bytes,
        "legacy_content_hash_compat_only": pkg_dict.get("content_hash", ""),
    }
    (out_dir / "canary_digests.json").write_text(
        json.dumps(digests, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    # Print a short receipt to stdout for the CI gate.
    print(json.dumps(digests, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())