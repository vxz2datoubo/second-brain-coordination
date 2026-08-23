"""Visualization & graph-export tests.

Verifies the library-neutral graph JSON, the generated HTML, the GraphML
export, and the determinism of all three outputs.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve()
ROOT = _HERE.parents[1]
SRC = ROOT / "src"
TESTS = ROOT / "tests"
CANARY_OUT = ROOT / "canary" / "out"
CANARY_GRAPH = CANARY_OUT / "canary_graph.json"
CANARY_DIGESTS = CANARY_OUT / "canary_digests.json"


def _run_python(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, *args],
        capture_output=True, text=True, timeout=60,
    )


def _ensure_canary_outputs() -> None:
    """Run build_canary_projection.py if its outputs are missing."""
    if CANARY_GRAPH.exists() and CANARY_DIGESTS.exists():
        return
    build = ROOT / "canary" / "build_canary_projection.py"
    proc = _run_python([str(build)])
    assert proc.returncode == 0, f"build failed: {proc.stderr}"


def test_visualization_html_is_self_contained():
    _ensure_canary_outputs()
    gen = ROOT / "visualization" / "generate_visualization.py"
    out_html = CANARY_OUT / "canary_graph.html"
    proc = _run_python([str(gen),
                        "--projection", str(CANARY_GRAPH),
                        "--output", str(out_html),
                        "--title", "E48 Canary Knowledge Graph"])
    assert proc.returncode == 0, proc.stderr
    html_text = out_html.read_text(encoding="utf-8")
    assert "<html" in html_text and "</html>" in html_text
    assert "vis-network" in html_text
    # The projection JSON must be embedded, not fetched from a server.
    assert str(CANARY_GRAPH.name) not in html_text  # no relative fetch
    # All node / edge ids must appear in the HTML so the page is usable.
    proj = json.loads(CANARY_GRAPH.read_text(encoding="utf-8"))
    for n in proj["nodes"]:
        assert n["node_id"] in html_text
    for e in proj["edges"]:
        assert e["source_node_id"] in html_text
        assert e["target_node_id"] in html_text


def test_graphml_export_is_well_formed():
    _ensure_canary_outputs()
    exp = ROOT / "visualization" / "graphml_export.py"
    out = CANARY_OUT / "canary_graph.graphml"
    proc = _run_python([str(exp),
                        "--projection", str(CANARY_GRAPH),
                        "--output", str(out)])
    assert proc.returncode == 0, proc.stderr
    text = out.read_text(encoding="utf-8")
    assert text.startswith("<?xml")
    assert "graphml" in text
    assert "<graph " in text
    # Every edge id appears in the graphml. XML attribute values escape `>`
    # to `&gt;` when serialized, so normalize before checking.
    proj = json.loads(CANARY_GRAPH.read_text(encoding="utf-8"))
    for e in proj["edges"]:
        assert e["edge_id"].replace(">", "&gt;") in text


def test_visualization_outputs_are_deterministic():
    _ensure_canary_outputs()
    gen = ROOT / "visualization" / "generate_visualization.py"
    out1 = CANARY_OUT / "canary_graph.v1.html"
    out2 = CANARY_OUT / "canary_graph.v2.html"
    args = [str(gen), "--projection", str(CANARY_GRAPH),
            "--output", str(out1), "--title", "E48"]
    proc1 = _run_python(args)
    assert proc1.returncode == 0, proc1.stderr
    args[-3] = str(out2)
    proc2 = _run_python(args)
    assert proc2.returncode == 0, proc2.stderr
    # Same projection + same template → byte-identical HTML.
    assert out1.read_text(encoding="utf-8") == out2.read_text(encoding="utf-8")


def test_canary_digests_match_known_contract():
    _ensure_canary_outputs()
    dig = json.loads(CANARY_DIGESTS.read_text(encoding="utf-8"))
    assert set(dig) >= {
        "raw_artifact_sha256",
        "canonical_semantic_sha256",
        "l0_provenance_sha256",
        "projection_sha256",
        "view_sha256",
        "l0_source_sha256",
        "legacy_content_hash_compat_only",
    }
    # All hash fields except the legacy compat field are 64-hex.
    for k in ("raw_artifact_sha256", "canonical_semantic_sha256",
              "l0_provenance_sha256", "projection_sha256",
              "view_sha256", "l0_source_sha256"):
        assert len(dig[k]) == 64, f"{k} must be 64-hex"
        int(dig[k], 16)  # must parse as hex


class TestVisualization(unittest.TestCase):
    def test_visualization_html_is_self_contained(self):
        test_visualization_html_is_self_contained()

    def test_graphml_export_is_well_formed(self):
        test_graphml_export_is_well_formed()

    def test_visualization_outputs_are_deterministic(self):
        test_visualization_outputs_are_deterministic()

    def test_canary_digests_match_known_contract(self):
        test_canary_digests_match_known_contract()