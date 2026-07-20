#!/usr/bin/env python3
"""QCLAW Deterministic Learning Packet Pipeline CLI."""
import sys, json, os, yaml, hashlib
from . import canonical, adapters, compare

USAGE = """qclaw_pipeline <command> [args]

Commands:
  validate-input <file>         Validate a source file
  build-packet <source-file>    Build LearningPacket from source
  verify-packet <packet-file>   Verify a LearningPacket structure
  compare-runs <run1> <run2>    Compare two runs for determinism
  run-regression                Run regression test suite
  export-handoff <packet-file>  Export AI_HANDOFF format

Options:
  --output-dir DIR              Output directory (default: ./_packets)
  --version                     Show version
"""

def cmd_validate_input(args):
    path = args[0]
    content = open(path, "r", encoding="utf-8").read()
    source_hash = canonical.content_hash(content)
    result = {
        "valid": True,
        "source_hash": source_hash,
        "size_bytes": len(content.encode("utf-8")),
        "preview": content[:200],
    }
    print(json.dumps(result, indent=2))

def cmd_build_packet(args):
    """Build from synthetic test cases."""
    out_dir = "./_packets"
    for i, a in enumerate(args):
        if a == "--output-dir" and i + 1 < len(args):
            out_dir = args[i + 1]
            break

    from .tests import test_cases
    os.makedirs(out_dir, exist_ok=True)
    
    for case_key, mats in test_cases.items():
        for mat in mats:
            pkt = adapters.build_packet(
                source_id=mat["source_id"],
                source_content=mat["content"],
                source_time=mat.get("source_time", "2024-01-01"),
                atoms=mat.get("atoms", []),
                relations=mat.get("relations", []),
                unknowns=mat.get("unknowns", []),
                privacy_class=mat.get("privacy_class", "PUBLIC_SAFE"),
            )
            fname = f"{case_key}_{mat['source_id']}.json"
            path = os.path.join(out_dir, fname)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(pkt, f, indent=2, ensure_ascii=False)
            print(f"  Built: {fname} -> {pkt['packet_semantic_id']}")
    
    print(f"\nDone. Packets in {out_dir}")

def cmd_verify_packet(args):
    path = args[0]
    with open(path, "r", encoding="utf-8") as f:
        pkt = json.load(f)
    result = adapters.verify_packet(pkt)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)

def cmd_compare_runs(args):
    r1 = json.load(open(args[0], "r", encoding="utf-8"))
    r2 = json.load(open(args[1], "r", encoding="utf-8"))
    result = compare.compare_runs(r1, r2)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["deterministic"] else 1)

def cmd_run_regression(args):
    """Run all regression tests."""
    from .tests import run_all_tests
    results = run_all_tests()
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    print(f"\nRegression: {passed}/{total} passed")
    for r in results:
        status = "✅" if r.get("passed") else "❌"
        print(f"  {status} {r['name']}")
    sys.exit(0 if passed == total else 1)

def cmd_export_handoff(args):
    path = args[0]
    with open(path, "r", encoding="utf-8") as f:
        pkt = json.load(f)
    handoff = {
        "schema_version": "1.0",
        "agent_id": "QCLAW",
        "target_agent": "GPT",
        "handoff_type": "LEARNING_PACKET",
        "packet_semantic_id": pkt.get("packet_semantic_id"),
        "packet_content_hash": pkt.get("packet_content_hash"),
        "knowledge_status": pkt.get("knowledge_status"),
        "authority_level": pkt.get("authority_level"),
        "atom_count": len(pkt.get("atoms", [])),
        "relation_count": len(pkt.get("relations", [])),
    }
    print(json.dumps(handoff, indent=2))

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print(USAGE)
        sys.exit(0)
    
    cmd = sys.argv[1]
    args = sys.argv[2:]
    
    handlers = {
        "validate-input": cmd_validate_input,
        "build-packet": cmd_build_packet,
        "verify-packet": cmd_verify_packet,
        "compare-runs": cmd_compare_runs,
        "run-regression": cmd_run_regression,
        "export-handoff": cmd_export_handoff,
    }
    
    if cmd in handlers:
        handlers[cmd](args)
    else:
        print(f"Unknown command: {cmd}")
        print(USAGE)
        sys.exit(1)

if __name__ == "__main__":
    main()
