"""Compare two LearningPacket runs for determinism."""
from typing import Dict, Any

def compare_runs(run1: Dict, run2: Dict) -> Dict[str, Any]:
    """Compare two LearningPacket outputs."""
    mismatches = []

    # Atom IDs
    atoms1 = {a["atom_id"]: a for a in run1.get("atoms", [])}
    atoms2 = {a["atom_id"]: a for a in run2.get("atoms", [])}
    
    only_in_1 = set(atoms1.keys()) - set(atoms2.keys())
    only_in_2 = set(atoms2.keys()) - set(atoms1.keys())

    if only_in_1 or only_in_2:
        mismatches.append({
            "type": "ATOM_ID_DIFF",
            "only_run1": list(only_in_1),
            "only_run2": list(only_in_2),
        })

    # Relation IDs
    rels1 = {r["relation_id"]: r for r in run1.get("relations", [])}
    rels2 = {r["relation_id"]: r for r in run2.get("relations", [])}
    only_rel_1 = set(rels1.keys()) - set(rels2.keys())
    only_rel_2 = set(rels2.keys()) - set(rels1.keys())
    if only_rel_1 or only_rel_2:
        mismatches.append({
            "type": "RELATION_ID_DIFF",
            "only_run1": list(only_rel_1),
            "only_run2": list(only_rel_2),
        })

    # Semantic ID
    sem_id_match = run1.get("packet_semantic_id") == run2.get("packet_semantic_id")
    if not sem_id_match:
        mismatches.append({
            "type": "SEMANTIC_ID_MISMATCH",
            "run1": run1.get("packet_semantic_id"),
            "run2": run2.get("packet_semantic_id"),
        })

    # Content hash
    hash_match = run1.get("packet_content_hash") == run2.get("packet_content_hash")
    if not hash_match:
        mismatches.append({
            "type": "CONTENT_HASH_MISMATCH",
            "run1": run1.get("packet_content_hash"),
            "run2": run2.get("packet_content_hash"),
        })

    return {
        "deterministic": len(mismatches) == 0,
        "semantic_id_match": sem_id_match,
        "content_hash_match": hash_match,
        "atom_id_match": len(only_in_1) == 0 and len(only_in_2) == 0,
        "relation_id_match": len(only_rel_1) == 0 and len(only_rel_2) == 0,
        "mismatches": mismatches,
    }
