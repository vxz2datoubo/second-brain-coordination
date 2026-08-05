"""
QCLAW E34 — CLI Entry Point
"""
import sys
import os
import json
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qclaw_knowledge_digest.atomizer import Atomizer, AtomizationResult
from qclaw_knowledge_digest.redact import redact, SAFE_EXAMPLES
from qclaw_knowledge_digest.relations import extract_proximity_relations


def serialize_atom(atom) -> dict:
    return {
        "deterministic_id": atom.deterministic_id,
        "content_zh": atom.content_zh,
        "content_en": atom.content_en,
        "content_type": atom.content_type.value,
        "source_span": {
            "start_byte": atom.source_span.start_byte if atom.source_span else 0,
            "end_byte": atom.source_span.end_byte if atom.source_span else 0,
        } if atom.source_span else None,
        "source_blob_sha": atom.source_blob_sha,
        "source_commit_sha": atom.source_commit_sha,
        "conditions": atom.conditions,
        "exceptions": atom.exceptions,
        "negations": atom.negations,
        "temporal_scope": atom.temporal_scope,
        "confidence": atom.confidence,
        "authority": atom.authority,
        "version": atom.version,
    }


def serialize_result(result: AtomizationResult, source_path: str = "") -> dict:
    source_hash = hashlib.sha256(
        json.dumps(serialize_atom(result.atoms[0]) if result.atoms else {}, sort_keys=True).encode()
    ).hexdigest() if result.atoms else "0000000000000000000000000000000000000000000000000000000000000000"
    
    full_hash = hashlib.sha256(
        json.dumps([
            [serialize_atom(a) for a in result.atoms],
            [{"source": r.source_atom_id, "target": r.target_atom_id, "type": r.relation_type} for r in result.relations],
            [{"desc": u.description} for u in result.unknowns],
            [{"a": c.atom_id_a, "b": c.atom_id_b, "desc": c.description} for c in result.conflicts],
        ], sort_keys=True, default=str).encode()
    ).hexdigest()
    
    return {
        "schema_version": "1.0.0-e34",
        "packet_id": full_hash[:32],
        "packet_content_hash": full_hash,
        "source_hash": result.source_hash,
        "source_path": source_path,
        "byte_coverage": result.byte_coverage,
        "atoms": [serialize_atom(a) for a in result.atoms],
        "relations": [
            {"source_atom_id": r.source_atom_id, "target_atom_id": r.target_atom_id, "relation_type": r.relation_type}
            for r in result.relations
        ],
        "unknowns": [{"description": u.description, "context": u.context} for u in result.unknowns],
        "conflicts": [{"atom_id_a": c.atom_id_a, "atom_id_b": c.atom_id_b, "description": c.description} for c in result.conflicts],
        "atom_count": len(result.atoms),
        "relation_count": len(result.relations),
        "unknown_count": len(result.unknowns),
        "conflict_count": len(result.conflicts),
    }


def main():
    atomizer = Atomizer()
    
    if len(sys.argv) < 2:
        print("Usage: python -m qclaw_knowledge_digest <source.md> [--fmt markdown] [--output result.json]")
        sys.exit(1)
    
    source_path = sys.argv[1]
    fmt = "markdown"
    output_path = None
    
    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--fmt" and i + 1 < len(args):
            fmt = args[i + 1]
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        else:
            i += 1
    
    with open(source_path, "r", encoding="utf-8") as f:
        source = f.read()
    
    # Redact first
    clean = redact(source)
    
    # Atomize
    result = atomizer.atomize(clean, fmt=fmt)
    
    # Add relations
    result.relations.extend(extract_proximity_relations(result.atoms))
    
    # Serialize
    packet = serialize_result(result, source_path)
    
    # Output
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
        print(f"Packet written to {output_path}")
    
    # Summary
    print(f"Atoms: {packet['atom_count']} | Relations: {packet['relation_count']} | "
          f"Unknowns: {packet['unknown_count']} | Conflicts: {packet['conflict_count']}")
    print(f"Coverage: {packet['byte_coverage']:.4f} | Packet ID: {packet['packet_id']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
