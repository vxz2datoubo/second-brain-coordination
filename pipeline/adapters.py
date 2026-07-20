"""QCLAW → LearningPacket v0.2 adapter."""
import json, hashlib, datetime
from typing import Any, Dict, List, Optional
from .canonical import (
    atom_identity, relation_identity, semantic_content_hash,
    packet_semantic_id, packet_instance_id, idempotency_key, content_hash,
)

SCHEMA_VERSION = "0.2"
PROCESSOR_VERSION = "qclaw-v0.2.33-pipeline-0003"

# ── Atom field mapping ──
def adapt_atom(qclaw_atom: Dict, source_hash: str, source_id: str, source_excerpt: str = "") -> Dict:
    """Convert QCLAW atom → LearningPacket v0.2 atom."""
    statement = qclaw_atom.get("canonical_statement", "")
    atom_type_map = {
        "FACT": "fact", "METHOD": "procedure", "CONCEPT": "concept",
        "DEFINITION": "concept", "CORRELATION": "observation",
        "EVIDENCE": "observation", "SCOPE": "observation",
        "EXCEPTION": "observation", "OUTDATED_FACT": "fact",
        "FRAMEWORK": "concept", "RULE": "rule",
        "MECHANISM_EXPLANATION": "concept",
        "CAUSAL_CHAIN": "concept", "CORE_CONCEPT": "concept",
        "REFINEMENT": "observation", "CORRECTION": "observation",
        "RISK": "observation", "INSIGHT": "insight",
        "META_OBSERVATION": "insight",
        "HYPOTHESIS": "question",
    }
    mapped_type = atom_type_map.get(qclaw_atom.get("atom_type", "FACT"), "observation")

    confidence_map = {
        (0.00, 0.30): "speculative",
        (0.30, 0.55): "low",
        (0.55, 0.75): "medium",
        (0.75, 0.90): "high",
        (0.90, 1.01): "certain",
    }
    conf = qclaw_atom.get("confidence", 0.5)
    mapped_conf = "medium"
    for (lo, hi), label in confidence_map.items():
        if lo <= conf < hi:
            mapped_conf = label
            break

    return {
        "atom_id": qclaw_atom.get("atom_id") or atom_identity(statement, mapped_type),
        "type": mapped_type,
        "type_original": qclaw_atom.get("atom_type"),  # preserved
        "statement": statement,
        "confidence": mapped_conf,
        "confidence_original": conf,  # preserved
        "scope": qclaw_atom.get("scope", ""),
        "premises": qclaw_atom.get("premises", []),
        "exceptions": qclaw_atom.get("exceptions", []),
        "failure_conditions": qclaw_atom.get("failure_conditions", []),
        "source": {
            "reference": qclaw_atom.get("source_reference", source_id),
            "hash": source_hash,
            "excerpt": source_excerpt or qclaw_atom.get("original_excerpt", ""),
        },
        "evidence_quality": qclaw_atom.get("evidence_quality") or qclaw_atom.get("verification_status", "unverified"),
        "verification_status": qclaw_atom.get("verification_status", "UNVERIFIED"),
        "memory_type": qclaw_atom.get("memory_type", "SEMANTIC"),
        "privacy_class": qclaw_atom.get("privacy_class", "PUBLIC_SAFE"),
    }

# ── Relation mapping ──
RELATION_TYPE_MAP = {
    "EXPLAINS": "refines", "PART_OF": "depends_on",
    "UNDERPINS": "supports", "EXEMPLIFIES": "exemplifies",
    "EVIDENCED_BY": "supports", "REFINES": "refines",
    "ALTERNATIVE_TO": "related_to", "QUALIFIES": "refines",
    "SUPPORTS": "supports", "DERIVED_FROM": "depends_on",
    "CONSEQUENCE_OF": "related_to", "APPLIES_TO": "generalizes",
    "ANALOGOUS_TO": "related_to", "MITIGATES": "related_to",
    "COMPOSES": "depends_on", "IMPLEMENTS": "depends_on",
    "CONSTRAINS": "refines", "CONTRADICTS_UNDER_CONDITION": "contradicts",
    "SUPERSEDES": "supersedes", "REPLACES": "supersedes",
    "EXPLAINS_POTENTIALLY": "related_to",
    "UPDATES": "supersedes",
}

def adapt_relation(qclaw_rel: Dict) -> Dict:
    """Convert QCLAW relation → LearningPacket v0.2 relation."""
    source = qclaw_rel.get("source", "")
    target = qclaw_rel.get("target", "")
    orig_type = qclaw_rel.get("type", "related_to")
    mapped_type = RELATION_TYPE_MAP.get(orig_type, "related_to")

    rel_id = relation_identity(source, target, orig_type)
    return {
        "relation_id": qclaw_rel.get("rel_id") or rel_id,
        "type": mapped_type,
        "type_original": orig_type,  # preserved
        "source_atom_id": source,
        "target_atom_id": target,
        "reason": qclaw_rel.get("reason", ""),
        "strength": "moderate",
        "confidence": qclaw_rel.get("confidence", 0.5),
    }

# ── Packet assembly ──
def build_packet(
    source_id: str, source_content: str, source_time: str,
    atoms: List[Dict], relations: List[Dict],
    unknowns: Optional[List[Dict]] = None,
    structures: Optional[List[Dict]] = None,
    skills: Optional[List[Dict]] = None,
    merge_decisions: Optional[List[Dict]] = None,
    privacy_class: str = "PUBLIC_SAFE",
    run_context: str = "",
) -> Dict:
    """Build a complete LearningPacket v0.2."""
    source_hash = content_hash(source_content)
    now = datetime.datetime.now().isoformat()

    adapted_atoms = [adapt_atom(a, source_hash, source_id) for a in atoms]
    adapted_relations = [adapt_relation(r) for r in relations]

    atom_ids = sorted([a["atom_id"] for a in adapted_atoms])
    semantic_id = packet_semantic_id(source_hash, atom_ids)

    # packet_content_hash: ordered atoms + relations
    content_core = {
        "atoms": [json.dumps(a, sort_keys=True, ensure_ascii=False) for a in sorted(adapted_atoms, key=lambda x: x["atom_id"])],
        "relations": [json.dumps(r, sort_keys=True, ensure_ascii=False) for r in sorted(adapted_relations, key=lambda x: x["relation_id"])],
    }
    packet_hash = content_hash(content_core)

    return {
        "schema_version": SCHEMA_VERSION,
        "packet_semantic_id": semantic_id,
        "packet_instance_id": packet_instance_id(semantic_id, run_context or now),
        "packet_content_hash": packet_hash,
        "idempotency_key": idempotency_key(semantic_id, packet_hash),
        "processor_version": PROCESSOR_VERSION,
        "processed_at": now,
        "knowledge_status": "candidate",
        "gpt_access": "FULL_SEMANTIC_ACCESS",
        "transport_visibility": "PUBLIC_SAFE",
        "authority_level": "CANDIDATE_ONLY",
        "source_artifacts": [{
            "source_id": source_id,
            "source_hash": source_hash,
            "source_time": source_time,
            "privacy_class": privacy_class,
        }],
        "atoms": adapted_atoms,
        "relations": adapted_relations,
        "structures": structures or [],
        "skills": skills or [],
        "unknowns": unknowns or [],
        "conflicts": merge_decisions or [],
        "retrieval_index": [],
        "quality_audit": {
            "completeness_score": min(1.0, len(atoms) / 5),
            "internal_consistency": "consistent",
            "source_coverage": 1.0 if source_content else 0.0,
            "notes": f"Generated by {PROCESSOR_VERSION}",
        },
        "write_proposal": {
            "auto_accept": [],
            "review_required": [],
        },
    }

# ── Verify packet ──
def verify_packet(packet: Dict) -> Dict[str, Any]:
    """Verify a LearningPacket for structural integrity."""
    errors = []
    warnings = []

    # Required top-level fields
    required = ["schema_version", "packet_semantic_id", "packet_content_hash",
                 "idempotency_key", "knowledge_status"]
    for f in required:
        if f not in packet:
            errors.append(f"missing required field: {f}")

    # Atoms integrity
    atom_ids = set()
    for a in packet.get("atoms", []):
        aid = a.get("atom_id", "")
        if not aid:
            errors.append("atom missing atom_id")
        elif aid in atom_ids:
            errors.append(f"duplicate atom_id: {aid}")
        atom_ids.add(aid)
        if not a.get("statement"):
            errors.append(f"atom {aid} missing statement")
        if "source" not in a:
            warnings.append(f"atom {aid} missing source")

    # Relations refer to real atoms
    for r in packet.get("relations", []):
        src = r.get("source_atom_id", "")
        tgt = r.get("target_atom_id", "")
        if src and src not in atom_ids:
            errors.append(f"relation {r.get('relation_id','?')} source {src} not in atoms")
        if tgt and tgt not in atom_ids:
            errors.append(f"relation {r.get('relation_id','?')} target {tgt} not in atoms")
        if not r.get("type"):
            errors.append(f"relation {r.get('relation_id','?')} missing type")

    # Boundary checks
    if packet.get("knowledge_status") in ("approved", "authority"):
        warnings.append("knowledge_status should not be approved/authority for candidate")
    if packet.get("authority_level") != "CANDIDATE_ONLY":
        warnings.append("authority_level should be CANDIDATE_ONLY")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "atom_count": len(packet.get("atoms", [])),
        "relation_count": len(packet.get("relations", [])),
    }
