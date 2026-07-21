#!/usr/bin/env python3
"""Candidate Memory Library — CLI + Health Report

Work Package H: command-line interface for memory operations and
health/status reporting.

Usage:
  python cli.py import <packet.json>               # Import a LearningPacket
  python cli.py search <query>                      # Search memory
  python cli.py stats                                # Memory statistics
  python cli.py health                               # Health check + integrity report
  python cli.py snapshot                             # Create a snapshot
  python cli.py revisions                            # List revisions
  python cli.py rollback <revision_id>               # Rollback to revision
  python cli.py diff <rev_a> <rev_b>                 # Diff two revisions
  python cli.py eval                                  # Run regression evaluation
  python cli.py export <output.json>                  # Export full state
"""

import sys
import json
import os
import time
import argparse
from typing import Optional


def get_store(db_path: str = ":memory:"):
    """Get a connected MemoryStore (lazy import)."""
    from store import MemoryStore
    s = MemoryStore(db_path).connect()
    return s


def cmd_import(store, args):
    """Import a LearningPacket JSON file."""
    from fusion import FusionEngine
    path = args.path
    with open(path, 'r', encoding='utf-8') as f:
        pkt = json.load(f)
    fe = FusionEngine(store)
    report = fe.fuse_packet(pkt)
    print(json.dumps(report.summary(), indent=2))


def cmd_search(store, args):
    """Search memory."""
    from context import ContextAssembler
    ca = ContextAssembler(store)
    bundle = ca.quick_search(args.query, budget=getattr(args, 'budget', 20))
    print(bundle.to_json())


def cmd_deep_search(store, args):
    """Deep search with relation expansion."""
    from context import ContextAssembler
    ca = ContextAssembler(store)
    bundle = ca.deep_search(args.topic, budget=getattr(args, 'budget', 100))
    print(bundle.to_json())


def cmd_stats(store, args):
    """Print memory statistics."""
    st = store.stats()
    ic = store.integrity_check()
    print(json.dumps({"stats": st, "integrity": ic}, indent=2))


def cmd_health(store, args):
    """Run full health check."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stats": store.stats(),
        "integrity": store.integrity_check(),
        "revisions": [],
    }

    # Version chain
    chain = se.get_version_chain()
    report["revision_count"] = len(chain)

    # Per-revision integrity
    for rev in chain:
        vi = se.verify_revision_integrity(rev["revision_id"])
        report["revisions"].append({
            "revision_id": rev["revision_id"][:16] + "...",
            "parent": (rev.get("parent_revision_id", "") or "")[:16] + "..." if rev.get("parent_revision_id") else None,
            "created": rev["created_at"],
            "valid": vi.get("valid", False),
            "hash_match": vi.get("hash_match", False),
            "issues": len(vi.get("issues", [])),
        })

    # Audit trail summary
    events = store.get_audit_events(10)
    report["recent_audit"] = [{
        "type": e["event_type"],
        "detail": e.get("detail", "")[:200],
        "timestamp": e["timestamp"],
    } for e in events]

    overall_ok = report["integrity"]["integrity_ok"]
    print(f"Health: {'✅ OK' if overall_ok else '❌ Issues Found'}")
    print(json.dumps(report, indent=2, ensure_ascii=False))


def cmd_snapshot(store, args):
    """Create a snapshot."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)
    rev = se.snapshot(args.parent if hasattr(args, 'parent') and args.parent else None)
    print(f"Snapshot created: {rev}")


def cmd_revisions(store, args):
    """List revisions."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)
    chain = se.get_version_chain()
    for r in chain:
        parent = (r.get("parent_revision_id") or "")[:16]
        print(f"{r['revision_id'][:16]}... <- {parent}... | {r['created_at']}")


def cmd_rollback(store, args):
    """Rollback to a specific revision."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)
    result = se.rollback(args.revision_id)
    print(json.dumps(result, indent=2))


def cmd_diff(store, args):
    """Diff two revisions."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)
    d = se.diff(args.rev_a, args.rev_b)
    print(json.dumps(d, indent=2))


def cmd_eval(store, args):
    """Run regression evaluation."""
    from eval import RetrievalEvaluator
    evaluator = RetrievalEvaluator(store)
    report = evaluator.run(args.dataset_name if hasattr(args, 'dataset_name') else "regression")
    s2 = report.summary()
    print(json.dumps(s2, indent=2))
    if report.failed > 0:
        print(f"\nFailed queries:")
        for qr in report.query_results:
            if not qr.passed:
                print(f"  - {qr.query.get('query','')}: {qr.failures}")


def cmd_export(store, args):
    """Export full memory state to JSON."""
    from snapshot import SnapshotEngine
    se = SnapshotEngine(store)
    state = se._capture_state()
    path = args.output
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)
    print(f"Exported {sum(state['counts'].values())} entities to {path}")


def cmd_input(store, args):
    """Import a batch from JSON Lines (one packet per line)."""
    from fusion import FusionEngine
    fe = FusionEngine(store)
    total = {"atoms": 0, "relations": 0, "unknowns": 0, "packets": 0}
    with open(args.path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            line = line.strip()
            if not line:
                continue
            pkt = json.loads(line)
            r = fe.fuse_packet(pkt)
            s = r.summary()
            total["atoms"] += s["atoms"]["inserted"]
            total["relations"] += s["relations"]["inserted"]
            total["unknowns"] += s["unknowns"]["inserted"]
            total["packets"] += 1
    print(f"Imported {total['packets']} packets: "
          f"{total['atoms']} atoms, {total['relations']} relations, "
          f"{total['unknowns']} unknowns")


def cmd_fact_check(store, args):
    """Run a fact check against memory."""
    from context import QueryPlan, ContextAssembler
    ca = ContextAssembler(store)
    plan = QueryPlan.for_fact_check(args.claim)
    bundle = ca.assemble(plan)
    print(bundle.to_text_summary())
    if bundle.conflicts:
        print("\n⚠️  Conflicts detected:")
        for c in bundle.conflicts:
            print(f"  - {c.get('conflict_type')}: {c.get('resolution_status')}")


def main():
    parser = argparse.ArgumentParser(description="Candidate Memory Library CLI")
    parser.add_argument("--db", default=":memory:", help="SQLite DB path")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import", help="Import a LearningPacket JSON")
    p.add_argument("path", help="Path to packet JSON")

    p = sub.add_parser("input", help="Import JSON Lines batch")
    p.add_argument("path", help="Path to JSONL file")

    p = sub.add_parser("search", help="Search memory")
    p.add_argument("query", help="Search query")
    p.add_argument("--budget", type=int, default=20)

    p = sub.add_parser("deep", help="Deep search with relation expansion")
    p.add_argument("topic", help="Search topic")
    p.add_argument("--budget", type=int, default=100)

    p = sub.add_parser("fact", help="Fact check a claim")
    p.add_argument("claim", help="Claim to check")

    sub.add_parser("stats", help="Memory statistics")
    sub.add_parser("health", help="Health check")

    p = sub.add_parser("snapshot", help="Create revision snapshot")
    p.add_argument("--parent", default=None)

    sub.add_parser("revisions", help="List revisions")

    p = sub.add_parser("rollback", help="Rollback to revision")
    p.add_argument("revision_id")

    p = sub.add_parser("diff", help="Diff revisions")
    p.add_argument("rev_a")
    p.add_argument("rev_b")

    p = sub.add_parser("eval", help="Run regression evaluation")
    p.add_argument("--dataset", dest="dataset_name", default="regression")

    p = sub.add_parser("export", help="Export full state to JSON")
    p.add_argument("output")

    args = parser.parse_args()

    store = get_store(args.db)

    cmds = {
        "import": cmd_import,
        "input": cmd_input,
        "search": cmd_search,
        "deep": cmd_deep_search,
        "fact": cmd_fact_check,
        "stats": cmd_stats,
        "health": cmd_health,
        "snapshot": cmd_snapshot,
        "revisions": cmd_revisions,
        "rollback": cmd_rollback,
        "diff": cmd_diff,
        "eval": cmd_eval,
        "export": cmd_export,
    }

    cmds[args.command](store, args)
    store.close()


if __name__ == "__main__":
    main()
