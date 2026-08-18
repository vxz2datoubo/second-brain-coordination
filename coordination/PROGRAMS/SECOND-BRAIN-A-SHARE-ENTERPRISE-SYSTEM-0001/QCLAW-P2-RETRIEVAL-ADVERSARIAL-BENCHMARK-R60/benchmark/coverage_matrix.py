"""R60 coverage matrix generator.

Reads benchmark_cases.json + harness_results.json and emits:
  - coverage matrix (dimension x slice) with runnable/graded/spec-pending counts
  - canonical-contract traceability summary (per case)
Deterministic, no external deps.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent          # .../benchmark
R60_DIR = HERE.parent
CASES = HERE / "cases" / "benchmark_cases.json"
RESULTS = R60_DIR / "evidence" / "harness_results.json"

DIMENSIONS = (
    "scope_isolation_cross_domain_denial",
    "current_historical_valid_at",
    "stale_revoked_superseded_no_resurrection",
    "channel_admission_parity",
    "hidden_disallowed_relation_conflict_endpoint",
    "synthetic_aggregate_no_double_vote",
    "support_and_counter_alternative_coverage",
    "material_unknown_and_no_evidence_abstain",
    "provenance_redaction_no_raw_pointer_body",
    "deterministic_ordering_dedup_budget",
    "prompt_injection_secret_fail_closed",
)
SLICES = ("P2.1", "P2.2", "P2.3", "P2.4")


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    results_by_id = {}
    if RESULTS.exists():
        res = json.loads(RESULTS.read_text(encoding="utf-8"))
        results_by_id = {r["case_id"]: r for r in res.get("results", [])}

    dim_slice = defaultdict(lambda: defaultdict(int))
    dim_slice_runnable = defaultdict(lambda: defaultdict(int))
    dim_slice_graded = defaultdict(lambda: defaultdict(int))
    dim_total = Counter()
    dim_runnable = Counter()
    dim_graded = Counter()
    dim_pending = Counter()
    slice_total = Counter()
    contract_counts = Counter()
    verdict_counts = Counter()

    for c in cases:
        dim = c["dimension"]
        sl = c["applicable_slice"]
        runnable = c["runnable"]
        dim_slice[dim][sl] += 1
        dim_total[dim] += 1
        slice_total[sl] += 1
        contract_counts[c["canonical_contract_source"]] += 1
        if runnable:
            dim_slice_runnable[dim][sl] += 1
            dim_runnable[dim] += 1
        else:
            dim_pending[dim] += 1
        r = results_by_id.get(c["case_id"])
        if r is not None and r["verdict"] in ("PASS", "FAIL"):
            dim_slice_graded[dim][sl] += 1
            dim_graded[dim] += 1
            verdict_counts[r["verdict"]] += 1

    matrix = {
        "schema_version": "r60-coverage-matrix-v1",
        "total_cases": len(cases),
        "runnable_cases": sum(1 for c in cases if c["runnable"]),
        "spec_pending_cases": sum(1 for c in cases if not c["runnable"]),
        "graded_cases": sum(verdict_counts.values()),
        "verdicts": dict(verdict_counts),
        "dimensions": {},
        "slices": {},
        "canonical_contract_sources": {},
    }
    for dim in DIMENSIONS:
        matrix["dimensions"][dim] = {
            "total": dim_total[dim],
            "runnable": dim_runnable[dim],
            "spec_pending": dim_pending[dim],
            "graded": dim_graded[dim],
            "by_slice": {sl: dim_slice[dim][sl] for sl in SLICES if dim_slice[dim][sl]},
            "runnable_by_slice": {sl: dim_slice_runnable[dim][sl] for sl in SLICES if dim_slice_runnable[dim][sl]},
        }
    for sl in SLICES:
        matrix["slices"][sl] = {
            "total": slice_total[sl],
            "runnable": sum(dim_slice_runnable[d][sl] for d in DIMENSIONS),
            "spec_pending": sum(dim_slice[d][sl] - dim_slice_runnable[d][sl] for d in DIMENSIONS),
        }
    for src, n in sorted(contract_counts.items()):
        matrix["canonical_contract_sources"][src] = n

    out = R60_DIR / "evidence" / "coverage_matrix.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    # Markdown rendering
    md = ["# R60 Coverage Matrix\n", f"- total_cases: {matrix['total_cases']}",
          f"- runnable: {matrix['runnable_cases']}  spec_pending: {matrix['spec_pending_cases']}  graded: {matrix['graded_cases']}",
          f"- verdicts: {matrix['verdicts']}\n", "## By dimension\n"]
    md.append("| dimension | total | runnable | pending | graded |")
    md.append("|---|---|---|---|---|")
    for dim in DIMENSIONS:
        e = matrix["dimensions"][dim]
        md.append(f"| {dim} | {e['total']} | {e['runnable']} | {e['spec_pending']} | {e['graded']} |")
    md.append("\n## By slice\n")
    md.append("| slice | total | runnable | pending |")
    md.append("|---|---|---|---|")
    for sl in SLICES:
        e = matrix["slices"][sl]
        md.append(f"| {sl} | {e['total']} | {e['runnable']} | {e['spec_pending']} |")
    md.append("\n## Canonical contract sources\n")
    for src, n in sorted(contract_counts.items()):
        md.append(f"- {src}: {n}")

    md_path = R60_DIR / "evidence" / "coverage_matrix.md"
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
