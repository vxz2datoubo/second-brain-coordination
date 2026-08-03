#!/usr/bin/env python3
"""
QCLAW E28 — Knowledge Atomization Core v2
Fixes all E27 defects:
  - No wall-clock timestamps → source-commit-anchored time
  - No filesystem paths → repo-relative refs
  - Full semantic subfields per atom
  - Conservative CLAIM/OPINION/HYPOTHESIS/UNKNOWN defaults
  - Canonical packet hash covers all semantics
"""
import hashlib, json, re, os
from typing import Optional
from dataclasses import dataclass, field, asdict

SCHEMA_VERSION = "2.0.0"

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# ── Deterministic identity ─────────────────────────────────────────────
def deterministic_atom_id(content: str, source_blob_sha256: str, span_start: int, span_end: int) -> str:
    """Deterministic: content + source identity + exact span. No timestamps/paths."""
    key = content.strip() + "\0" + source_blob_sha256 + "\0" + str(span_start) + "\0" + str(span_end)
    return sha256(key)

# ── Content type classifier (conservative) ─────────────────────────────
def classify_content_type(source_text: str, unit_type: str = "paragraph") -> str:
    """Conservative classification. Unknown/Claim unless clear evidence."""
    t = source_text.lower().strip()
    
    if unit_type == "heading":
        return "heading"
    if unit_type == "code_block":
        return "code_block"
    if unit_type == "table":
        return "table"
    if unit_type == "list":
        return "list"
    
    # Structure-based first
    if "steps:" in t or "procedure:" in t or "algorithm:" in t:
        return "method"
    if "precondition:" in t or "requires:" in t:
        return "condition_precondition"
    if t.startswith("definition:") or "is defined as" in t:
        return "definition"
    if "must not" in t or "shall not" in t or "shall be" in t:
        return "constraint"
    
    # Evidence-based classification
    if "unknown" in t or "not yet understood" in t or "open question" in t or "remains to be" in t:
        return "unknown"
    if "counterexample" in t or "on the contrary" in t:
        return "counterexample"
    if "fails when" in t or "failure mode" in t or "will not work" in t:
        return "failure_condition"
    if "except when" in t or "unless" in t:
        return "exception_explicit"
    
    # ASSERTIONS default to CLAIM unless strong evidence
    if "proven" in t or "demonstrated" in t or "established" in t:
        return "statement_fact"
    if "study shows" in t or "data indicates" in t or "observed" in t:
        return "statement_fact"
    if "i think" in t or "i believe" in t or "in my opinion" in t:
        return "statement_opinion"
    if "claim:" in t or "asserts:" in t or "argues:" in t:
        return "statement_claim"
    if "may be" in t or "might be" in t or "could be" in t:
        return "statement_hypothesis"
    
    # Default conservative: CLAIM (not FACT)
    return "statement_claim"

# ── Semantic field extraction ──────────────────────────────────────────
def extract_semantic_fields(source_text: str) -> dict:
    """Extract structured conditions, exceptions, negations, etc."""
    t = source_text.lower()
    result = {
        "conditions": [],
        "exceptions": [],
        "negations": [],
        "failure_conditions": [],
        "counterexamples": [],
        "temporal_scope": {"is_timeless": True, "scope_text": None},
        "unknowns": [],
        "evidence_basis": "source_text",
        "structural_type": "paragraph"
    }
    
    # Extract conditions
    cond_patterns = [
        r'(?:if|when|whenever|provided that)\s+([^,\.;]+)',
        r'precondition\s*:\s*([^,\.;]+)',
        r'requires\s+([^,\.;]+)',
    ]
    for pat in cond_patterns:
        for m in re.finditer(pat, t):
            result["conditions"].append(m.group(1).strip()[:200])
    
    # Extract exceptions
    exc_patterns = [
        r'except\s+(?:when|for|if)\s+([^,\.;]+)',
        r'unless\s+([^,\.;]+)',
        r'with the exception of\s+([^,\.;]+)',
    ]
    for pat in exc_patterns:
        for m in re.finditer(pat, t):
            result["exceptions"].append(m.group(1).strip()[:200])
    
    # Extract negations
    neg_starts = ["it is not ", "this is not ", "does not ", "do not ", "should not ", "cannot ", "will not "]
    for ns in neg_starts:
        if t.startswith(ns):
            result["negations"].append(source_text.strip()[:200])
            break
    
    # Extract failure conditions
    fail_patterns = [
        r'(?:fails|breaks|will not work)\s+(?:when|if|unless)\s+([^,\.;]+)',
        r'failure (?:mode|condition)\s*:\s*([^,\.;]+)',
    ]
    for pat in fail_patterns:
        for m in re.finditer(pat, t):
            result["failure_conditions"].append(m.group(1).strip()[:200])
    
    # Counterexamples
    if "counterexample" in t or "on the contrary" in t or "contrary to" in t:
        result["counterexamples"].append(source_text.strip()[:300])
    
    # Temporal scope
    temporal_patterns = [
        r'effective from\s+([^,\.;]+)',
        r'valid until\s+([^,\.;]+)',
        r'from (\d{4}-\d{2}-\d{2})\s+to\s+(\d{4}-\d{2}-\d{2})',
    ]
    for pat in temporal_patterns:
        m = re.search(pat, t)
        if m:
            result["temporal_scope"]["is_timeless"] = False
            result["temporal_scope"]["scope_text"] = m.group(0)[:200]
            break
    
    # Unknown markers
    for marker in ["unknown", "not yet understood", "open question", "remains to be"]:
        if marker in t:
            result["unknowns"].append(marker)
    
    return result

# ── Authority separation ───────────────────────────────────────────────
def determine_authority(source_meta: dict, content_type: str) -> dict:
    """Conservative authority: candidate-only, no auto-upgrade."""
    return {
        "status": "candidate",
        "can_upgrade": False,
        "upgrade_requires": "external_review",
        "source_trust": source_meta.get("source_trust", "unknown"),
        "content_type": content_type,
        "no_trade_gate": True
    }

# ── Atom creation ──────────────────────────────────────────────────────
def create_atom(parse_unit, source_blob_sha256: str, source_ref: dict) -> Optional[dict]:
    """Create a KnowledgeAtom v2 from a ParseUnit."""
    content = parse_unit.content.strip()
    if not content:
        return None
    
    atom_id = deterministic_atom_id(
        content, source_blob_sha256,
        parse_unit.span.start_byte, parse_unit.span.end_byte
    )
    
    content_type = classify_content_type(content, parse_unit.content_type)
    semantic_fields = extract_semantic_fields(content)
    authority = determine_authority({"source_trust": "repository"}, content_type)
    
    return {
        "schema_version": SCHEMA_VERSION,
        "atom_id": atom_id,
        "status": "candidate",
        "content_type": content_type,
        "canonical_text": content,
        
        # Source lineage (no paths, no timestamps)
        "source_refs": [source_ref],
        "source_span": {
            "start_byte": parse_unit.span.start_byte,
            "end_byte": parse_unit.span.end_byte,
            "length_bytes": parse_unit.span.length
        },
        
        # Semantic subfields
        "conditions": semantic_fields["conditions"],
        "exceptions": semantic_fields["exceptions"],
        "negations": semantic_fields["negations"],
        "failure_conditions": semantic_fields["failure_conditions"],
        "counterexamples": semantic_fields["counterexamples"],
        "temporal_scope": semantic_fields["temporal_scope"],
        
        # Authority
        "authority": authority,
        
        # Lineage
        "supersession_chain": [],
        "version_info": {"version": 1},
        "conflicts_with": [],
        "related_to": [],
        
        # Hard gates
        "privacy_class": "public_safe",
        "no_trade_gate": True
    }

# ── Canonical serialization (for deterministic hashing) ────────────────
def canonical_atom_form(atom: dict) -> str:
    """Deterministic canonical form of a single atom (sorted keys, no timestamps, no paths)."""
    stripped = {}
    for k in sorted(atom.keys()):
        if k in ("source_span",):
            continue  # covered by atom_id
        v = atom[k]
        stripped[k] = v
    return json.dumps(stripped, sort_keys=True, ensure_ascii=True, separators=(",", ":"))

def canonical_packet_hash(atoms: list, relations: list, unknowns: list, conflicts: list,
                          source_manifest: dict) -> str:
    """
    Canonical packet hash covering ALL semantics: atoms, relations, unknowns, conflicts, lineage.
    Deterministic across runs, roots, PYTHONHASHSEED values.
    """
    parts = []
    # All atoms in canonical form
    for a in sorted(atoms, key=lambda x: x["atom_id"]):
        parts.append(canonical_atom_form(a))
    # Relations sorted by deterministic ID
    for r in sorted(relations, key=lambda x: x.get("deterministic_id", "")):
        parts.append(json.dumps(r, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    # Unknowns
    for u in sorted(unknowns, key=lambda x: x.get("deterministic_id", "")):
        parts.append(json.dumps(u, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    # Conflicts
    for c in sorted(conflicts, key=lambda x: x.get("deterministic_id", "")):
        parts.append(json.dumps(c, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    # Source manifest
    parts.append(json.dumps(source_manifest, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    
    full = "\n".join(parts)
    return sha256(full)

def canonical_packet_id(atoms: list, source_blob_sha256: str) -> str:
    """Packet ID = SHA-256(sorted atom IDs + source blob). Deterministic."""
    ids = sorted([a["atom_id"] for a in atoms])
    return sha256("\n".join(ids) + "\0" + source_blob_sha256)
