#!/usr/bin/env python3
"""QCLAW E27 CLI — Knowledge atomization CLI entry point."""
import sys, argparse, json, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from qclaw_knowledge_digest.atomizer import (
    atomize_document, run_digest_queue, sha256
)

def main():
    parser = argparse.ArgumentParser(description="QCLAW E27 Knowledge Atomization Pipeline")
    sub = parser.add_subparsers(dest="command")
    
    # atomize
    atom = sub.add_parser("atomize", help="Atomize a single document")
    atom.add_argument("file", help="Path to source file")
    atom.add_argument("--output", "-o", default=None, help="Output JSON file path")
    atom.add_argument("--source-type", default="file", help="Source type tag")
    
    # digest
    dig = sub.add_parser("digest", help="Process a digest queue directory")
    dig.add_argument("queue", help="Path to queue directory")
    dig.add_argument("--output", "-o", default="output_packets", help="Output directory")
    
    # validate
    val = sub.add_parser("validate", help="Validate a LearningPacket JSON")
    val.add_argument("packet", help="Path to packet JSON file")
    
    args = parser.parse_args()
    
    if args.command == "atomize":
        result = atomize_document(args.file, {"source_type": args.source_type})
        output_data = {
            "atoms": result["atoms"],
            "relations": result["relations"],
            "unknowns": result["unknowns"],
            "conflicts": result["conflicts"],
            "parse_report": result["parse_report"]
        }
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            print(f"Output: {args.output}")
        else:
            print(json.dumps(output_data["parse_report"], ensure_ascii=False, indent=2))
        print(f"Atoms: {len(result['atoms'])}, Relations: {len(result['relations'])}, Unknowns: {len(result['unknowns'])}, Conflicts: {len(result['conflicts'])}")
        return 0
    
    elif args.command == "digest":
        res = run_digest_queue(args.queue, args.output)
        if res.get("status") != "DIGEST_COMPLETE":
            print(res.get("message",""))
            return 1
        r = res["report"]
        print(f"Files: {r['files_processed']}, Atoms: {r['total_atoms']}, Relations: {r['total_relations']}")
        print(f"Unknowns: {r['total_unknowns']}, Conflicts: {r['total_conflicts']}")
        return 0
    
    elif args.command == "validate":
        with open(args.packet, "r", encoding="utf-8") as f:
            packet = json.load(f)
        errors = []
        required = ["schema_version","packet_id","atoms","relations","unknowns","conflicts","no_trade_gate"]
        for k in required:
            if k not in packet:
                errors.append(f"Missing required field: {k}")
        if packet.get("no_trade_gate") is not True:
            errors.append("no_trade_gate must be true")
        if errors:
            for e in errors: print(f"FAIL: {e}")
            return 1
        print(f"PASS: {args.packet} ({len(packet.get('atoms',[]))} atoms, {len(packet.get('relations',[]))} relations)")
        return 0
    
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
