"""Generate the R2 canary projection JSON for E48 — end-to-end.

R2 changes:
- Pure raw 中文 canary text (no comments / metadata).
- L2 atoms and relations are derived by ``qclaw_e48_reconstruction.l2_derive``
  from the L1 view + L0 raw text — NOT hand-built here.
- Mid-confidence caller rule injects an ambiguity case (成交量 → 交易量
  at confidence 0.5). The reconstructor keeps alternatives and rejects
  the edit from being promoted to a SOURCE_EXTRACT atom.
- UNKNOWN_MARKER caller rule emits an UnknownMarker for "他她".
- Cross-sentence "如果…那么…" detection derives 2 SOURCE_EXTRACT atoms
  + 1 REFINES relation. All other relations are derived only from
  applied, type-threshold-passing edits; nothing is hand-quota-filled.
- The exact bytes of the L2 candidate artifact are persisted to
  canary/out/canary_artifact.json; raw_artifact_sha256 is computed over
  those persisted bytes (not over a temp json.dumps blob).

Hard boundary: no private user text; canary is PUBLIC_SAFE synthetic.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qclaw_e48_reconstruction.digests import (  # noqa: E402
    canonical_semantic_sha256,
    l0_provenance_sha256,
    raw_artifact_sha256,
)
from qclaw_e48_reconstruction.l1_reconstruct import (  # noqa: E402
    ReconstructionRuleset,
    reconstruct,
)
from qclaw_e48_reconstruction.l1_schema import (  # noqa: E402
    EditType,
    TerminologyAlias,
)
from qclaw_e48_reconstruction.l2_derive import derive_l2_package  # noqa: E402
from qclaw_e48_reconstruction.l3_project import project_graph  # noqa: E402


CANARY_PATH = ROOT / "canary" / "synthetic_canary_noisy_chinese.txt"


# Caller-supplied ruleset used to inject the (e) mid-confidence and the
# (f) UNKNOWN cases. These rules are PUBLIC_SAFE synthetic examples and
# produce the required ambiguity + UNKNOWN behaviour through the actual
# reconstructor (not via hand-built test objects).
CANARY_RULESET = ReconstructionRuleset(
    rules=(
        # (e) mid-confidence alias: keep alternatives, do not promote to fact.
        (
            r"成交量",
            r"交易量",
            0.5,
            EditType.TERMINOLOGY_NORMALIZATION,
            "mid-confidence alias: 成交量 → 交易量 (test canary, kept ambiguous)",
        ),
        # (f) UNKNOWN_MARKER for the unresolvable pronoun "他她".
        (
            r"他她",
            r"他她",
            0.3,
            EditType.UNKNOWN_MARKER,
            "ambiguous pronoun cannot be resolved (kept as UNKNOWN)",
        ),
    )
)


def _terminology_aliases() -> list:
    return [
        TerminologyAlias(
            alias_id="alias-quantum-entanglement",
            raw_form="量子隐传",
            canonical_form="量子纠缠",
            scope="E48 canary",
            confidence=1.0,
            evidence_refs=("synthetic:line-4",),
        ),
    ]


def main() -> int:
    l0 = CANARY_PATH.read_text(encoding="utf-8")

    view = reconstruct(
        l0,
        ruleset=CANARY_RULESET,
        aliases=_terminology_aliases(),
        view_id="E48-CANARY-001",
    )

    pkg_dict = derive_l2_package(
        l0,
        view,
        package_id="E48-CANARY-PKG-001",
        source_meta={
            "source_id": "src-canary",
            "source_url": "workspace://canary/synthetic_canary_noisy_chinese.txt",
            "source_title": "E48 PUBLIC_SAFE canary (R3)",
        },
    )

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
        "applied_edit_count": sum(1 for s in view.segments for e in s.edits if e.applied),
        "ambiguity_count": len(view.ambiguities),
        "unknown_count": len(view.unknowns),
    }
    (out_dir / "canary_digests.json").write_text(
        json.dumps(digests, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(digests, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
