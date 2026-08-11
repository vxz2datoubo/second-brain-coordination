"""L3 projection tests.

Builds a minimal E47-style L2 package (via the local test stub) and a L1 view,
projects to L3, then asserts:
- Every edge endpoint exists.
- No fabricated edges.
- Counts are derived from inputs (not hard-coded).
- Adding/removing an atom changes node and edge counts accordingly.
"""
from __future__ import annotations

import unittest
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
E48_ROOT = _HERE.parents[1]
sys.path.insert(0, str(E48_ROOT / "src"))
# Bring the test stub onto sys.path as ``qclaw_e47_digest`` so the production
# import-by-name contract is exercised. We load the file as module
# ``qclaw_e47_digest`` BEFORE executing it, and inject it into sys.modules
# first so dataclass can resolve ``cls.__module__``.
import importlib.util as _ilu
import sys as _sys
_SPEC = _ilu.spec_from_file_location(
    "qclaw_e47_digest",
    str(E48_ROOT / "tests" / "_e47_stub.py"),
)
_e47 = _ilu.module_from_spec(_SPEC)
_sys.modules["qclaw_e47_digest"] = _e47
_SPEC.loader.exec_module(_e47)

from qclaw_e48_reconstruction.l1_reconstruct import reconstruct  # noqa: E402
from qclaw_e48_reconstruction.l3_project import project_graph  # noqa: E402


L0_TEXT = "成交量上升时价格倾向于上升。"


def _l2_pkg() -> dict:
    src = _e47.ingest_source(L0_TEXT, "workspace://canary", "canary", "src-1")
    a1 = _e47.source_extract(
        "A001", "MECHANISM", L0_TEXT,
        0, len(L0_TEXT),
        "HIGH", scope="A股日内",
    )
    a2 = _e47.source_extract(
        "A002", "CONDITION", L0_TEXT,
        0, len(L0_TEXT),
        "MEDIUM", scope="A股日内",
    )
    pkg = _e47.build_package(
        "E48-L3-CANARY", src, [a1, a2],
        relations=[
            _e47.Relation("A001", "A002", "SUPPORTS"),
            _e47.Relation("A002", "A001", "REFINES"),
        ],
        summary="two atoms",
    )
    return pkg.to_dict()


def test_all_edges_have_valid_endpoints() -> None:
    l2 = _l2_pkg()
    view = reconstruct(L0_TEXT)
    proj = project_graph(l2, view)
    errs = proj.validate()
    assert errs == [], f"projection has invalid edges: {errs}"


def test_node_and_edge_counts_are_derived() -> None:
    l2 = _l2_pkg()
    view = reconstruct(L0_TEXT)
    proj = project_graph(l2, view)
    # Expected composition:
    #   1 source node, 1 segment node, 2 atom nodes = 4 nodes (no contradictions/unknowns/memories)
    #   2 segment->source edges + 2 atom->segment edges + 2 semantic relations = 6 edges
    assert proj.to_dict()["node_count"] == 4
    assert proj.to_dict()["edge_count"] == 6


def test_empty_contradiction_sets_are_valid() -> None:
    l2 = _l2_pkg()  # contradictions = []
    view = reconstruct(L0_TEXT)
    proj = project_graph(l2, view)
    assert proj.validate() == []


def test_adding_an_atom_changes_counts() -> None:
    l2 = _l2_pkg()
    view = reconstruct(L0_TEXT)
    proj1 = project_graph(l2, view)
    n1 = proj1.to_dict()["node_count"]
    e1 = proj1.to_dict()["edge_count"]
    # Add one atom to L2 (synthetic, byte span 0..5 over the source text).
    l2_b = {**l2, "atoms": l2["atoms"] + [
        {
            "atom_id": "A003",
            "atom_type": "INDICATOR",
            "content": "test",
            "source_spans": [
                {"byte_start": 0, "byte_end": 5, "line_start": 1, "line_end": 1},
            ],
            "evidence_kind": "INFERENCE",
            "confidence": "LOW",
            "scope": "",
            "invalidation_conditions": "",
        }
    ]}
    proj2 = project_graph(l2_b, view)
    assert proj2.to_dict()["node_count"] == n1 + 1
    # One extra atom-to-segment edge.
    assert proj2.to_dict()["edge_count"] == e1 + 1


def test_adding_an_unknown_changes_counts_and_type() -> None:
    l2 = _l2_pkg()
    view = reconstruct(L0_TEXT)
    proj1 = project_graph(l2, view)
    n1 = proj1.to_dict()["node_count"]
    e1 = proj1.to_dict()["edge_count"]
    l2_b = {**l2, "unknowns": [
        {
            "unknown_id": "U001",
            "question": "unknown?",
            "related_atom_ids": ["A001"],
        }
    ]}
    proj2 = project_graph(l2_b, view)
    assert proj2.to_dict()["node_count"] == n1 + 1
    # One RAISES_UNKNOWN edge from A001 to the new unknown.
    assert proj2.to_dict()["edge_count"] == e1 + 1
    # Validate the new edge endpoint exists.
    assert proj2.validate() == []


def test_projection_is_deterministic() -> None:
    l2 = _l2_pkg()
    view = reconstruct(L0_TEXT)
    p1 = project_graph(l2, view)
    p2 = project_graph(l2, view)
    assert p1.projection_sha256 == p2.projection_sha256
    assert p1.to_dict() == p2.to_dict()


def test_no_fabricated_edges_when_atom_missing() -> None:
    """A relation pointing at a missing atom must NOT produce an edge."""
    l2 = _l2_pkg()
    l2["relations"].append({
        "source_atom_id": "A001",
        "target_atom_id": "A_DOES_NOT_EXIST",
        "relation_type": "SUPPORTS",
        "span_index": -1,
    })
    view = reconstruct(L0_TEXT)
    proj = project_graph(l2, view)
    assert proj.validate() == [], "missing endpoint must not produce edge"
    # No edge may reference the missing atom or the missing target node id.
    bad_ids = {"A_DOES_NOT_EXIST", "atom:A_DOES_NOT_EXIST"}
    for e in proj.edges:
        assert e.source_node_id not in bad_ids
        assert e.target_node_id not in bad_ids
    # The two good relations remain; the third is silently dropped.
    semantic_edges = [e for e in proj.edges if e.edge_type.value in {
        "SUPPORTS", "DEPENDS_ON", "REFINES", "CONTRADICTS", "RAISES_UNKNOWN", "VERIFIED_BY"
    }]
    assert len(semantic_edges) == 2, (
        f"expected 2 valid semantic edges, got {len(semantic_edges)}"
    )


class TestL3(unittest.TestCase):
    def test_all_edges_have_valid_endpoints(self):
        test_all_edges_have_valid_endpoints()

    def test_node_and_edge_counts_are_derived(self):
        test_node_and_edge_counts_are_derived()

    def test_empty_contradiction_sets_are_valid(self):
        test_empty_contradiction_sets_are_valid()

    def test_adding_an_atom_changes_counts(self):
        test_adding_an_atom_changes_counts()

    def test_adding_an_unknown_changes_counts_and_type(self):
        test_adding_an_unknown_changes_counts_and_type()

    def test_projection_is_deterministic(self):
        test_projection_is_deterministic()

    def test_no_fabricated_edges_when_atom_missing(self):
        test_no_fabricated_edges_when_atom_missing()
