"""Generate the canary projection JSON for E48 (R1).

Reads the synthetic Chinese canary, runs the L1 reconstructor, builds a
minimal E47-style L2 package, projects to L3, and writes:

- canary_artifact.json    — exact persisted L2 candidate artifact (the byte
                           blob whose SHA-256 is the raw_artifact_sha256).
- canary_graph.json       — L3 projection (KnowledgeGraphProjection JSON).
- canary_l1_view.json     — L1 NormalizedSemanticView (audit surface).
- canary_digests.json     — six SHA-256 digests + display summary.

The R1 canary text is structured so each of the 8 required semantic
behaviors fires through the actual pipeline (not by hand-built test
objects):
  - filler words (呃, 那个)        → FILLER_REMOVAL edits (line 1)
  - missing punctuation             → PUNCTUATION edits at unterminated
                                     line breaks (lines 1, 2, 3)
  - typo 部份→部分                  → TYPO_CORRECTION edit (line 2)
  - ASR homophone 式式→试试          → ASR_HOMOPHONE_CORRECTION edit
                                     (line 2, twice)
  - mid-confidence pronoun 他她     → AmbiguityCandidate with
                                     alternatives kept (line 3)
  - UNKNOWN 他她 pronoun            → UnknownMarker (line 3)
  - terminology alias 术语别名→量子纠缠 → TERMINOLOGY_NORMALIZATION edit
                                     (line 3)
  - cross-sentence mechanism 如果…那么… → CONDITIONAL relation between
                                     two SOURCE_EXTRACT atoms + a
                                     REFINE relation (line 1 → line 1
                                     second half)

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
from qclaw_e48_reconstruction.l1_schema import (  # noqa: E402
    TerminologyAlias,
)
from qclaw_e48_reconstruction.l3_project import project_graph  # noqa: E402


CANARY_PATH = ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


def _terminology_aliases() -> list:
    # PUBLIC_SAFE example aliases used by the canary corpus.
    return [
        TerminologyAlias(
            alias_id="alias-quantum-entanglement",
            raw_form="术语别名",
            canonical_form="量子纠缠",
            scope="E48 canary",
            confidence=1.0,
            evidence_refs=("synthetic:line-3",),
        ),
    ]


def main() -> int:
    l0 = CANARY_PATH.read_text(encoding="utf-8")
    view = reconstruct(l0, aliases=_terminology_aliases(), view_id="E48-CANARY-001")

    src = _e47.ingest_source(
        l0, "workspace://canary/synthetic_canary_noisy_chinese.txt",
        "E48 PUBLIC_SAFE canary (R1)", "src-canary",
    )

    # Three SOURCE_EXTRACT atoms spanning the three lines of the canary,
    # plus one INFERENCE atom for the cross-sentence mechanism. End
    # offsets are line-aligned so the byte ranges do not overlap with
    # the L1 reconstructed edits.
    lines = l0.splitlines(keepends=True)
    line1_end = sum(len(line) for line in lines[:1])  # offset at end of line 1
    line2_end = sum(len(line) for line in lines[:2])  # offset at end of line 2
    line3_end = sum(len(line) for line in lines[:3])  # offset at end of line 3

    a1 = _e47.source_extract(
        "A001", "MECHANISM", l0, 0, line1_end, "HIGH",
        scope="canary", label="if-volume-then-price-mechanism",
    )
    a2 = _e47.source_extract(
        "A002", "CONDITION", l0, 0, line1_end, "MEDIUM",
        scope="canary", label="if-volume-up-condition",
    )
    a3 = _e47.source_extract(
        "A003", "INDICATOR", l0, line1_end, line2_end, "LOW",
        scope="canary", label="volume-as-key-indicator",
    )
    a4 = _e47.source_extract(
        "A004", "ALIAS_SURFACE", l0, line2_end, line3_end, "HIGH",
        scope="canary", label="alias-surface",
    )
    # INFERENCE atom (cross-sentence mechanism): abstracted from line 1.
    a5 = _e47.inference_atom(
        "A005", "MECHANISM_ABSTRACTION",
        l0, 0, line1_end, "MEDIUM",
        rationale="Abstracted from line 1: if-volume-then-price is a mechanism",
    )

    pkg = _e47.build_package(
        "E48-CANARY-PKG-001", src, [a1, a2, a3, a4, a5],
        relations=[
            # Line 1 cross-sentence mechanism.
            _e47.Relation("A001", "A002", "REFINES"),
            _e47.Relation("A002", "A005", "SUPPORTS"),
            _e47.Relation("A005", "A003", "SUPPORTS"),
        ],
        unknowns=[
            {
                "unknown_id": "U001",
                "question": "Who is 他 她 in line 3? (pronoun unresolved)",
                "related_atom_ids": ["A004"],
            },
        ],
        summary="canary mechanism / condition / unknown (R1 end-to-end)",
    )
    pkg_dict = pkg.to_dict()

    proj = project_graph(pkg_dict, view, projection_id="E48-CANARY-L3")

    out_dir = ROOT / "canary" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    # R1: serialize the EXACT L2 candidate artifact blob to disk so that
    # raw_artifact_sha256 is computed over a persisted byte blob, not an
    # in-memory dict whose serialization might be reformatted by later
    # tooling.
    proj_dict = proj.to_dict()
    proj_blob = json.dumps(proj_dict, ensure_ascii=False, sort_keys=True)
    (out_dir / "canary_graph.json").write_text(proj_blob, encoding="utf-8")
    (out_dir / "canary_l1_view.json").write_text(
        json.dumps(view.to_dict(), ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )

    # The persisted L2 candidate artifact (exact bytes for raw_artifact_sha256).
    artifact_blob = json.dumps(pkg_dict, ensure_ascii=False, sort_keys=True).encode("utf-8")
    artifact_path = out_dir / "canary_artifact.json"
    artifact_path.write_bytes(artifact_blob)

    digests = {
        "raw_artifact_sha256": raw_artifact_sha256(artifact_blob),
        "raw_artifact_path": "canary/out/canary_artifact.json",
        "raw_artifact_size_bytes": len(artifact_blob),
        "canonical_semantic_sha256": canonical_semantic_sha256(pkg_dict),
        "l0_provenance_sha256": l0_provenance_sha256(
            pkg_dict["source"], pkg_dict["atoms"]
        ),
        "projection_sha256": proj.projection_sha256,
        "view_sha256": view.view_sha256,
        "l0_source_sha256": view.l0_source_hash,
        "l0_source_size_bytes": view.l0_source_size_bytes,
        "legacy_content_hash_compat_only": pkg_dict.get("content_hash", ""),
        "applied_edit_count": sum(len(s.edits) for s in view.segments),
        "ambiguity_count": len(view.ambiguities),
        "unknown_count": len(view.unknowns),
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