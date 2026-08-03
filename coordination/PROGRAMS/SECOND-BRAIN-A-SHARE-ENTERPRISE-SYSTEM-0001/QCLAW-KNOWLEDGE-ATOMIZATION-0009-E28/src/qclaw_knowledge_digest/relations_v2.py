#!/usr/bin/env python3
"""
QCLAW E28 — Relation Extractor v2
Deterministic, span-grounded. No lexical fact/causality promotion.
"""
import re, hashlib

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

RELATION_PATTERNS = [
    # Explicit structural (high confidence)
    (r'([^.,:;]+?(?:depends on|requires|prerequisite for|needs)\s+[^.,:;]+)', "depends_on"),
    (r'([^.,:;]+?(?:contradicts|conflicts with|incompatible with)\s+[^.,:;]+)', "conflicts"),
    (r'([^.,:;]+?(?:is a |is an instance of|is a type of|is a kind of)\s+[^.,:;]+)', "is_a"),
    (r'([^.,:;]+?(?:is part of|is contained in|belongs to)\s+[^.,:;]+)', "part_of"),
    (r'([^.,:;]+?(?:supersedes|replaces|overrides|obsoletes)\s+[^.,:;]+)', "supersedes"),
    
    # Evidence-based (only with clear markers)
    (r'([^.,:;]+?(?:is evidence for|supports|confirms|validates)\s+[^.,:;]+)', "evidence_for"),
    (r'([^.,:;]+?(?:is counterevidence to|refutes|disproves)\s+[^.,:;]+)', "counterevidence_to"),
    
    # Precondition/causal (conservative — only with explicit markers)
    (r'([^.,:;]+?(?:precondition for|required for)\s+[^.,:;]+)', "precondition_for"),
    (r'([^.,:;]+?(?:is exception to|is excluded by)\s+[^.,:;]+)', "exception_to"),
]

def extract_relations(atoms: list, spans: dict) -> list:
    """
    Extract typed relations.
    Uses exact source spans, not whole-text matching.
    Conservative: no lexical causation promotion.
    """
    relations = []
    atom_texts = {a["atom_id"]: a["canonical_text"] for a in atoms}
    atom_spans = spans
    
    for atom_id, text in atom_texts.items():
        t = text.lower()
        for pattern, rel_type in RELATION_PATTERNS:
            matches = re.finditer(pattern, t, re.IGNORECASE)
            for match in matches:
                matched_text = match.group(1).strip()
                # Find target by content overlap (span-grounded)
                for other_id, other_text in atom_texts.items():
                    if other_id == atom_id:
                        continue
                    other_words = set(other_text.lower().split())
                    matched_words = set(matched_text.lower().split())
                    overlap = len(other_words & matched_words)
                    if overlap >= 3 and len(other_text) > 15:
                        rid = sha256(f"{rel_type}|{atom_id}|{other_id}|{matched_text[:80]}")
                        # Avoid duplicates
                        if not any(r.get("deterministic_id") == rid for r in relations):
                            relations.append({
                                "relation_type": rel_type,
                                "source_atom_id": atom_id,
                                "target_atom_id": other_id,
                                "relation_evidence": matched_text[:200],
                                "source_span_start": match.start(),
                                "source_span_end": match.end(),
                                "confidence": "extracted_span_grounded",
                                "deterministic_id": rid
                            })
                        break  # One relation per pattern match
    return relations

# UNKNOWN/Conflict detection
def extract_unknowns(atoms: list) -> list:
    markers = ["unknown", "not known", "uncertain", "unclear", "not yet understood",
               "open question", "gap in", "insufficient data", "remains to be"]
    unknowns = []
    for a in atoms:
        t = a["canonical_text"].lower()
        for m in markers:
            if m in t:
                unknowns.append({
                    "atom_id": a["atom_id"],
                    "detected_marker": m,
                    "annotation": a["canonical_text"][:300],
                    "status": "UNKNOWN",
                    "deterministic_id": sha256(f"UNKNOWN|{a['atom_id']}|{m}")
                })
                break
    return unknowns

def extract_conflicts(atoms: list) -> list:
    markers = ["however,", "on the contrary", "in contrast", "conflicting evidence",
               "alternative view", "opposing", "disagree"]
    conflicts = []
    for a in atoms:
        t = a["canonical_text"].lower()
        for m in markers:
            if m in t:
                conflicts.append({
                    "atom_id": a["atom_id"],
                    "detected_marker": m,
                    "annotation": a["canonical_text"][:300],
                    "status": "CONFLICT_DETECTED",
                    "deterministic_id": sha256(f"CONFLICT|{a['atom_id']}|{m}")
                })
                break
    return conflicts
