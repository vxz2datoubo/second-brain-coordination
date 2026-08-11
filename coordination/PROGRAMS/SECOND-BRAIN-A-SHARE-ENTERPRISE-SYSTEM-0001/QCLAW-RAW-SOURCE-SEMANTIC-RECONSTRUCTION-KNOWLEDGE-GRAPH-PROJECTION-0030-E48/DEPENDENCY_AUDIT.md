# Visualization dependency audit (E48)

> Per E48 plan §4 + Issue #216 hard rule:
> "Pick a visualization library after auditing the existing repo/runtime.
> Prefer reuse or a low-maintenance, easily-rolled-back option. If an
> external library is required, compare at least two candidates against
> official documentation. No hidden telemetry, no credentials."

## Existing repo / runtime inventory

```
$ ls second-brain-coordination/coordination
BLUEPRINTS/  ENGINEERING-LEARNING/  EVIDENCE/  GOVERNANCE/  INCIDENTS/
PROGRAMS/    PROVIDER-ATTESTATIONS/  QCLAW-TASK-ROUTER.md  RESULTS/
ROUTES/      SKILLS/  TASK-BRIEFS/  TEMPLATES/  AGENTS.md  README.md
```

There are **no Python modules** in this governance / blueprint repository
(no `*.py`, no `src/`, no `tests/`, no `pyproject.toml`, no `requirements.txt`).
E47's `qclaw_e47_digest` lives in PR #207's worktree, not on main.

Conclusion: **no existing visualization tooling to reuse**.

## Candidate comparison (offline-only constraint)

E48 must run on the QCLAW task machine, which is FOREGROUND_PRIORITY,
CPU-bound worker count ≤ 1, no cloud services, no network egress at
runtime. We considered:

| Candidate | License | Bundling | Browser-only? | Rollback cost | Verdict |
|-----------|---------|----------|---------------|---------------|---------|
| **vis-network** (visjs.org) | MIT/Apache-2.0 (vis.js) | Single static HTML + CDN pin (or local copy) | Yes | Trivial — delete the HTML artifact | **Chosen** |
| Cytoscape.js | MIT | Single static HTML + CDN pin | Yes | Trivial | Equal quality, larger bundle |
| Plotly.js graph | MIT | Larger bundle (~3 MB) | Yes | Trivial | Bigger download, slower for >200 nodes |
| D3 force | ISC | Hand-rolled UI | Yes | Bigger rewrite | High maintenance, low value |
| pyvis / networkx + server | BSD/MIT | Requires Python web server | No (server) | Medium | Violates browser-only constraint |

We chose **vis-network** because:
1. Single static HTML page — no Python web server, no worker process,
   no port, fully compatible with FOREGROUND_PRIORITY / zero-orphan.
2. Force-directed layout suitable for 50–500 nodes (typical L3 graphs).
3. Built-in search, highlight, node click events — covers the required
   "click a node to display content / confidence / evidence / source /
   raw / normalized context" requirement without writing UI code.
4. License is MIT (vis.js) / Apache-2.0 (vis-network fork). No telemetry,
   no credentials, no network call at runtime if the library is bundled
   in the artifact (we pin the script tag and serve locally).
5. Rollback = delete the HTML artifact. Zero coupling to repo Python.

## Telemetry / credential check

- vis-network source on GitHub: https://github.com/visjs/vis-network
  Audit confirmed: no analytics endpoints, no required auth, no external
  API calls. Static JS only.
- We embed vis-network via a stable CDN pin with `integrity=` attribute.
  For fully offline operation we ship a vendored copy in `vendor/`
  (license file included).
- No env vars, tokens, or credentials are referenced from the HTML or
  the generator.

## How to roll back

```bash
git rm coordination/.../E48/visualization/canary_graph.html
git rm coordination/.../E48/visualization/generate_visualization.py
git commit -m "qclaw(E48): roll back visualization artifact"
```

No downstream repo file depends on the HTML. Test suite is unaffected.