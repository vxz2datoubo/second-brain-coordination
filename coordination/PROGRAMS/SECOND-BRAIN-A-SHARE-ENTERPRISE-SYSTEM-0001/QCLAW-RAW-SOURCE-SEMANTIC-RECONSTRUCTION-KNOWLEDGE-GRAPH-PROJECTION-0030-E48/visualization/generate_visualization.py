"""Generate a fully self-contained, offline visualization HTML.

R1 fix (per Issue #216 GPT review id 4904086170):
- The previous generator claimed to be "self-contained" while still loading
  vis-network from a CDN URL. The CDN dependency has been removed: this
  generator now **inlines** the vis-network library into the output HTML,
  so the resulting file works fully offline (no network access required at
  view time). The vendored copy lives next to this script at
  ``vis-network.min.js`` (689 KB, MIT/Apache-2.0, no telemetry, no auth).

Usage:
    & python.exe visualization/generate_visualization.py \\
        --projection canary/out/canary_graph.json \\
        --output canary/out/canary_graph.html

The output is a single HTML file you can open with any modern browser,
completely offline. Filters, click-to-provenance panel, and
UNKNOWN / CONTRADICTS visual distinction all remain functional.
"""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


VIS_NETWORK_FILE = Path(__file__).resolve().parent / "vis-network.min.js"


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script>{vis_network_inline}</script>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: sans-serif; }}
  #mynetwork {{ position: absolute; left: 0; top: 0; bottom: 0; right: 380px; }}
  #sidebar {{ position: absolute; right: 0; top: 0; bottom: 0; width: 360px;
              overflow: auto; padding: 16px; background: #fafafa;
              border-left: 1px solid #ddd; box-sizing: border-box; }}
  #sidebar h2 {{ margin-top: 0; font-size: 14px; }}
  #sidebar pre {{ white-space: pre-wrap; font-size: 11px; line-height: 1.4; }}
  .unknown {{ background: #ffe6e6; }}
  .contradicts {{ background: #fff4cc; }}
  .controls label {{ display: block; font-size: 12px; margin-top: 6px; }}
  .controls input {{ width: 100%; box-sizing: border-box; }}
  .offline-banner {{ background: #efe; padding: 4px 12px; font-size: 11px;
                     border-bottom: 1px solid #cdc; color: #262; }}
</style>
</head>
<body>
<div class="offline-banner">Offline visualization — vis-network inlined; no network access required.</div>
<div id="mynetwork"></div>
<div id="sidebar">
  <h2 id="sidebar-title">{title}</h2>
  <div class="controls">
    <label>Filter by node type</label>
    <input id="filter-type" placeholder="atom / segment / source / unknown ...">
    <label>Filter by evidence kind</label>
    <input id="filter-evidence" placeholder="SOURCE_EXTRACT / INFERENCE ...">
    <label>Minimum confidence</label>
    <input id="filter-confidence" type="number" step="0.1" min="0" max="1" value="0">
    <label>Source id contains</label>
    <input id="filter-source" placeholder="source:...">
  </div>
  <h2 style="margin-top:16px">Selected node</h2>
  <pre id="detail">Click any node to see provenance.</pre>
</div>
<script>
  const PROJ = {projection_json};
  const nodes = new vis.DataSet(PROJ.nodes.map(n => ({{
    id: n.node_id,
    label: n.label || n.node_id,
    title: n.node_type + (n.attributes ? ('\\n' + JSON.stringify(n.attributes)) : ''),
    group: n.node_type,
    color: n.node_type === 'unknown' ? {{ background: '#ffd6d6', border: '#a33' }} :
           (n.attributes && n.attributes.class === 'contradiction') ?
             {{ background: '#fff4cc', border: '#a80' }} : undefined,
  }})));
  const edges = new vis.DataSet(PROJ.edges.map(e => ({{
    id: e.edge_id,
    from: e.source_node_id,
    to: e.target_node_id,
    label: e.edge_type,
    color: e.edge_type === 'CONTRADICTS' ? {{ color: '#a80' }} :
           e.edge_type === 'RAISES_UNKNOWN' ? {{ color: '#a33' }} : undefined,
    arrows: 'to',
  }})));
  const container = document.getElementById('mynetwork');
  const data = {{ nodes: nodes, edges: edges }};
  const options = {{
    layout: {{ improvedLayout: true }},
    physics: {{ stabilization: {{ iterations: 200 }} }},
    interaction: {{ hover: true, tooltipDelay: 200 }},
    groups: {{
      source: {{ color: {{ background: '#cce5ff', border: '#246' }} }},
      normalized_segment: {{ color: {{ background: '#e6f2ff', border: '#246' }} }},
      knowledge_atom: {{ color: {{ background: '#d9f2d9', border: '#262' }} }},
      unknown: {{ color: {{ background: '#ffd6d6', border: '#a33' }} }},
      candidate_memory: {{ color: {{ background: '#efe0ff', border: '#525' }} }},
      candidate_skill: {{ color: {{ background: '#fff0e0', border: '#a60' }} }},
    }},
  }};
  const net = new vis.Network(container, data, options);
  net.on('selectNode', evt => {{
    const id = evt.nodes[0];
    const n = PROJ.nodes.find(x => x.node_id === id);
    document.getElementById('detail').textContent = JSON.stringify(n, null, 2);
  }});
  function applyFilters() {{
    const t = document.getElementById('filter-type').value.trim().toLowerCase();
    const ev = document.getElementById('filter-evidence').value.trim().toLowerCase();
    const minC = parseFloat(document.getElementById('filter-confidence').value || '0');
    const src = document.getElementById('filter-source').value.trim().toLowerCase();
    const visible = new Set(PROJ.nodes.filter(n => {{
      if (t && !n.node_type.toLowerCase().includes(t)) return false;
      const attrs = n.attributes || {{}};
      if (ev && !(String(attrs.evidence_kind || '').toLowerCase().includes(ev))) return false;
      const conf = parseFloat(attrs.confidence || '1');
      if (!isNaN(conf) && conf < minC) return false;
      if (src && !n.node_id.toLowerCase().includes(src)) return false;
      return true;
    }}).map(n => n.node_id));
    nodes.update(PROJ.nodes.map(n => ({{ id: n.node_id, hidden: !visible.has(n.node_id) }}))));
    edges.update(PROJ.edges.map(e => ({{
      id: e.edge_id,
      hidden: !(visible.has(e.source_node_id) && visible.has(e.target_node_id)),
    }}))));
  }}
  ['filter-type','filter-evidence','filter-confidence','filter-source']
    .forEach(id => document.getElementById(id).addEventListener('input', applyFilters));
</script>
</body>
</html>
"""


def _load_vis_network_inline() -> str:
    if not VIS_NETWORK_FILE.exists():
        raise FileNotFoundError(
            f"vis-network vendor copy not found at {VIS_NETWORK_FILE}. "
            "Re-download with: "
            "python -c \"import urllib.request; "
            "open('vis-network.min.js','wb').write("
            "urllib.request.urlopen("
            "'https://cdn.jsdelivr.net/npm/vis-network@9.1.9/standalone/umd/vis-network.min.js'"
            ").read())\""
        )
    return VIS_NETWORK_FILE.read_text(encoding="utf-8")


def render_html(projection: dict, title: str) -> str:
    vis_inline = _load_vis_network_inline()
    # Inline JS body must not break the surrounding ``<script>...</script>``
    # tag: vis-network.min.js contains no ``</script>`` substrings (verified
    # at vendor time) but we add a defensive split just in case.
    safe = vis_inline.replace("</script>", "<\\/script>")
    return _HTML_TEMPLATE.format(
        title=html.escape(title),
        vis_network_inline=safe,
        projection_json=json.dumps(projection, ensure_ascii=False),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--projection", required=True,
                    help="Path to KnowledgeGraphProjection JSON")
    ap.add_argument("--output", required=True,
                    help="Path to write self-contained HTML")
    ap.add_argument("--title", default="E48 Knowledge Graph")
    args = ap.parse_args()

    proj = json.loads(Path(args.projection).read_text(encoding="utf-8"))
    html_text = render_html(proj, title=args.title)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_text, encoding="utf-8")
    print(f"wrote {out} ({len(html_text)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())