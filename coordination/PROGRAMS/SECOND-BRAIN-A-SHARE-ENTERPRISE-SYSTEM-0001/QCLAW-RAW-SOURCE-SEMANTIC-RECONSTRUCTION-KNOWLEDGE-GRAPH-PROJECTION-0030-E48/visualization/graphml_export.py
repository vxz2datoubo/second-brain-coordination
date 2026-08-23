"""Library-neutral GraphML 1.0 export for a KnowledgeGraphProjection.

GraphML is the W3C-standard graph interchange format, supported by yEd,
Gephi, Cytoscape, NetworkX, and many other tools. We use the stdlib XML
writer so the export is dependency-free and deterministic.

Usage:
    & python.exe visualization/graphml_export.py \\
        --projection canary_graph.json \\
        --output canary_graph.graphml
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


_GRAPHML_HEADER = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<graphml xmlns="http://graphml.graphstruct.org/xmlns"\n'
    '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n'
    '         xsi:schemaLocation="http://graphml.graphstruct.org/xmlns '
    'http://graphml.graphstruct.org/xmlns/1.0/graphml.xsd">\n'
    '  <key id="node_type" for="node" attr.name="node_type" attr.type="string"/>\n'
    '  <key id="label" for="node" attr.name="label" attr.type="string"/>\n'
    '  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>\n'
    '  <key id="confidence" for="edge" attr.name="confidence" attr.type="double"/>\n'
    '  <graph id="E48" edgedefault="directed">\n'
)
_GRAPHML_FOOTER = "  </graph>\n</graphml>\n"


def _attrs_to_data_elements(parent: Element, attrs: dict) -> None:
    """Flatten a string-keyed attributes dict as <data> children."""
    for k, v in attrs.items():
        d = SubElement(parent, "data", {"key": k})
        d.text = str(v)


def to_graphml(projection: dict) -> str:
    root = Element("dummy")  # placeholder; we build raw string for determinism
    g = SubElement(root, "graph", {"id": "E48", "edgedefault": "directed"})
    for n in projection.get("nodes", []):
        attrs = {
            "node_type": n.get("node_type", ""),
            "label": n.get("label", ""),
        }
        for k, v in (n.get("attributes") or {}).items():
            attrs[k] = v
        node_el = SubElement(g, "node", {"id": n["node_id"]})
        for key, val in attrs.items():
            d = SubElement(node_el, "data", {"key": key})
            d.text = str(val)
    for e in projection.get("edges", []):
        edge_el = SubElement(g, "edge", {
            "id": e["edge_id"],
            "source": e["source_node_id"],
            "target": e["target_node_id"],
        })
        for key, val in {
            "edge_type": e.get("edge_type", ""),
            "confidence": float(e.get("confidence", 1.0)),
        }.items():
            d = SubElement(edge_el, "data", {"key": key})
            d.text = str(val)
    body = tostring(g, encoding="unicode")
    # Replace the placeholder root open tag with our literal header.
    body = body.split(">", 1)[1].rsplit("<", 1)[0]
    return _GRAPHML_HEADER + body + _GRAPHML_FOOTER


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--projection", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    proj = json.loads(Path(args.projection).read_text(encoding="utf-8"))
    out_text = to_graphml(proj)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(out_text, encoding="utf-8")
    print(f"wrote {out} ({len(out_text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())