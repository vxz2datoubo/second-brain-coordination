# E48 dependency audit

## Repo inventory

The E48 module lives under `coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-RAW-SOURCE-SEMANTIC-RECONSTRUCTION-KNOWLEDGE-GRAPH-PROJECTION-0030-E48/`.
It is a governance/blueprint-only repository — there are no other Python
projects, no existing visualization dependencies, no prior L1/L2/L3
implementations to reuse. E47's `qclaw_e47_digest` module is imported as the
L2 upstream through a thin stub (`tests/_e47_stub.py`) for cross-agent
contract parity.

## Visualization dependency audit

After re-evaluating the R0 claim of "self-contained HTML" (which actually
loaded vis-network from a CDN), the R1 visualization is truly offline.

| Library | Version | License | Telemetry | Auth | Notes |
|---------|---------|---------|-----------|------|-------|
| vis-network (vendored) | 9.1.9 | MIT / Apache-2.0 | None | None | Selected: inlined into HTML, no CDN, no server, no build step |
| Cytoscape.js | 3.x | MIT | None | None | Equivalent offline story; larger community but heavier DOM model |
| Plotly.js | 2.x | MIT | None | None | Heavier; good for metrics but overkill for graph exploration |
| D3.js | 7.x | ISC | None | None | Maximum flexibility, but every interaction is hand-written |
| pyvis | 0.3.x | MIT | None | None | Python wrapper around vis-network; adds a server side |

**Decision (R1):** vendored `vis-network@9.1.9` (689 KB MIT) is inlined into
the output HTML by `visualization/generate_visualization.py`. The output file
opens in any modern browser with zero network access. Rollback = delete the
generated HTML + the vendored `vis-network.min.js`; nothing else to undo.

## Python dependencies

None beyond the standard library. Tests use `unittest` (stdlib) — no
`pytest`, no `hypothesis`, no third-party graph libraries. This was
deliberate to satisfy the FOREGROUND_PRIORITY resource policy (combined
project Python cap = 4; no nested parallelism; bounded local fanout).

## CI dependencies (R1)

GitHub Actions workflow `.github/workflows/qclaw-e48-semantic-reconstruction.yml`
runs the E48 test suite on a 2-cell matrix (Python 3.11 + 3.13) using only
`actions/checkout` and `actions/setup-python`. No nested parallelism, no
heavy fanout, no matrix fan-out beyond the two language versions.