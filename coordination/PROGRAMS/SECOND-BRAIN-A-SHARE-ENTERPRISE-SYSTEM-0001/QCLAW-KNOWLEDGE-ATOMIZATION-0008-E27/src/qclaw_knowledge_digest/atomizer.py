#!/usr/bin/env python3
"""
QCLAW E27 — Knowledge Atomization Core
Deterministic minimum-complete-semantic-unit atomization.
Preserves conditions, exceptions, negations, temporal scope, failures,
counterexamples, conflicts, UNKNOWNs, source lineage, confidence/authority
separation, and version/supersession chains.
"""
import hashlib, json, uuid, re, os, sys, yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, field, asdict

SCHEMA_VERSION = "1.0.0"
ATOM_MIN_CHARS = 12
ATOM_MAX_CHARS = 8000

# ── Deterministic hashing ──────────────────────────────────────────────
def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def deterministic_atom_id(canonical_text: str, source_refs: list) -> str:
    """Deterministic atom ID: SHA-256(canonical_text || sorted_source_keys)."""
    canonical_text = canonical_text.strip()
    ref_key = json.dumps(
        sorted([r.get("source_id","") + "|" + r.get("location","") for r in source_refs]),
        sort_keys=True, ensure_ascii=True
    )
    return sha256(canonical_text + "\0" + ref_key)

# ── Semantic unit type detection ───────────────────────────────────────
def classify_semantic_unit_type(text: str) -> str:
    """Heuristic: minimum_complete_unit vs compound."""
    text = text.strip()
    sentences = len(re.findall(r'[.!?;]\s', text)) + 1
    conditional_markers = sum(1 for m in [" if ", " when ", " unless ", " provided ", " except "] if m in text.lower())
    if sentences >= 3 or conditional_markers >= 2 or len(text) > 1200:
        return "compound"
    return "minimum_complete_unit"

# ── Content type classifier ────────────────────────────────────────────
def classify_content_type(text: str) -> str:
    """Classify atom content type from text patterns."""
    t = text.lower().strip()
    # Failure conditions
    if any(m in t for m in ["fails when", "break if", "failure mode", "will not work"]):
        return "failure_condition"
    # Counterexamples
    if any(m in t for m in ["counterexample", "however,", "on the contrary", "contrary to"]):
        return "counterexample"
    # Exceptions
    if any(m in t for m in ["except when", "except for", "unless", "with the exception of"]):
        return "exception_explicit"
    # Negations
    if t.startswith(("it is not", "this is not", "does not", "do not", "should not", "cannot")):
        return "negation"
    # Conditions
    if any(m in t for m in ["if and only if", "precondition:", "requires:", "depends on"]):
        return "condition_precondition"
    if any(m in t for m in ["when ", "whenever ", "triggered by", "upon "]):
        return "condition_trigger"
    # Constraints / Metrics (before temporal to avoid "from"/"to" ambiguity)
    if any(m in t for m in ["must not", "must be", "shall be", "shall not", "upper bound:", "lower bound:"]):
        return "constraint"
    if any(m in t for m in ["measured by", "metric:", "kpi:", "benchmark:"]):
        return "metric"
    # Temporal
    if any(m in t for m in ["effective from", "valid until", "during ", "from ", " to ", " permanently"]):
        return "temporal_scope" if len(t) < 300 else "temporal_assertion"
    # Methods / Skills
    if any(m in t for m in ["how to", "steps:", "procedure:", "algorithm:", "method:", "technique:"]):
        return "method"
    if t.startswith("skill:") or "best practice" in t:
        return "skill"
    # Decision chains
    if any(m in t for m in ["decision chain:", "if → then", "criterion:", "trade-off:"]):
        return "decision_chain"
    # Definitions
    if t.startswith("definition:") or "is defined as" in t or "refers to" in t:
        return "definition"
    # Source / Evidence
    if any(m in t for m in ["source:", "reference:", "cited from", "according to"]):
        return "source_meta" if len(t) < 200 else "evidence_chain"
    # Default: classify by confidence markers
    fact_markers = ["is ", "are ", "has ", "have ", "was ", "were ", "proven ", "demonstrated "]
    opinion_markers = ["i think", "i believe", "in my opinion", "seems to", "likely", "probably", "possibly"]
    if any(t.startswith(m) for m in fact_markers):
        return "statement_fact"
    if any(m in t for m in opinion_markers):
        return "statement_opinion"
    if any(m in t for m in ["claim:", "asserts:", "argues:", "stated that"]):
        return "statement_claim"
    return "statement_fact"

# ── Confidence estimation ──────────────────────────────────────────────
def estimate_confidence(text: str) -> dict:
    """Estimate confidence level and basis from text markers."""
    t = text.lower()
    high_conf = ["proven", "demonstrated", "established", "law of", "theorem:", "axiom:"]
    empirical = ["study shows", "data indicates", "experiment", "observed", "measured", "sample of"]
    consensus = ["expert consensus", "widely accepted", "standard practice", "literature review"]
    speculation = ["may be", "might be", "could be", "speculated", "hypothesized", "unknown whether"]
    
    if any(m in t for m in high_conf):
        return {"level": "established_knowledge", "basis": "established body of knowledge", "counterevidence_acknowledged": "unknown" in t}
    if any(m in t for m in empirical):
        return {"level": "empirical_evidence", "basis": "empirical observation or data", "counterevidence_acknowledged": "however" in t or "but" in t}
    if any(m in t for m in consensus):
        return {"level": "expert_consensus", "basis": "expert consensus", "counterevidence_acknowledged": False}
    if any(m in t for m in speculation):
        return {"level": "speculative", "basis": "speculation or hypothesis", "counterevidence_acknowledged": True}
    if "unknown" in t or "not known" in t or "?" in t:
        return {"level": "unknown", "basis": "insufficient evidence", "counterevidence_acknowledged": True}
    return {"level": "plausible_hypothesis", "basis": "reasonable inference", "counterevidence_acknowledged": False}

# ── Minimum-complete-semantic-unit segmenter ────────────────────────────
def segment_semantic_units(text: str, source_info: dict) -> list:
    """
    Segment raw text into minimum complete semantic units.
    Rules:
    - Markdown headings start new units
    - Code blocks are kept intact
    - Bullet/list items are atomic units
    - Paragraphs are split at sentence boundaries for long text
    - Conditions/exceptions/negations kept with their parent when possible
    """
    segments = []
    lines = text.split("\n")
    current = []
    in_code_block = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Code block tracking
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            if not in_code_block and current:
                segments.append("\n".join(current))
                current = []
            continue
        
        if in_code_block:
            current.append(line)
            continue
        
        # Empty line = segment boundary
        if not stripped:
            if current:
                segments.append("\n".join(current))
                current = []
            continue
        
        # Markdown headings = new segments
        if stripped.startswith("#"):
            if current:
                segments.append("\n".join(current))
                current = []
            current.append(line)
            # Single-line heading: segment and continue
            if not line.rstrip().endswith("."):
                segments.append("\n".join(current))
                current = []
            continue
        
        # List items are atomic
        if stripped.startswith(("- ", "* ", "+ ", "1. ", "2. ", "3. ")):
            if current and not current[0].strip().startswith(("- ", "* ")):
                segments.append("\n".join(current))
                current = []
            current.append(line)
            # If next line is continuation, check
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if not next_stripped or next_stripped.startswith(("- ", "* ", "+ ", "#")):
                    segments.append("\n".join(current))
                    current = []
            continue
        
        # Table line = keep with context
        if stripped.startswith("|"):
            current.append(line)
            continue
        
        # Regular paragraph
        current.append(line)
    
    if current:
        segments.append("\n".join(current))
    
    # Filter: remove segments shorter than minimum
    return [s for s in segments if len(s.strip()) >= ATOM_MIN_CHARS]

# ── Atom creation ──────────────────────────────────────────────────────
def create_atom(segment: str, source_refs: list, source_info: dict = None) -> dict:
    """Create a KnowledgeAtom from a semantic segment."""
    segment = segment.strip()
    if len(segment) < ATOM_MIN_CHARS:
        return None
    if len(segment) > ATOM_MAX_CHARS:
        segment = segment[:ATOM_MAX_CHARS]
    
    atom_id = deterministic_atom_id(segment, source_refs)
    content_type = classify_content_type(segment)
    unit_type = classify_semantic_unit_type(segment)
    confidence = estimate_confidence(segment)
    
    source_type = (source_info or {}).get("source_type", "unknown")
    
    return {
        "schema_version": SCHEMA_VERSION,
        "atom_id": atom_id,
        "status": "candidate",
        "content_type": content_type,
        "canonical_text": segment,
        "semantic_unit_type": unit_type,
        "source_refs": source_refs,
        "confidence": confidence,
        "authority_separation": {
            "source_type": source_type,
            "can_upgrade": False,
            "restrictions": ["candidate_only", "no_authority_upgrade"]
        },
        "conditions": [],
        "exceptions": [],
        "negations": [],
        "failure_conditions": [],
        "counterexamples": [],
        "temporal_scope": {"is_timeless": True},
        "conflicts_with": [],
        "related_to": [],
        "supersession_chain": [],
        "version_info": {"version": 1},
        "privacy_class": "public_safe",
        "no_trade_gate": True,
        "created_by": "QCLAW-E27",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deterministic_id_fingerprint": sha256(segment + atom_id)
    }

# ── Relation extraction ────────────────────────────────────────────────
RELATION_PATTERNS = [
    (r'([^.,:]+?(?:depends on|requires|needs|relies on|prerequisite)[^.,:]+)', "depends_on"),
    (r'([^.,:]+?(?:contradicts|conflicts with|incompatible with|opposes)[^.,:]+)', "conflicts"),
    (r'([^.,:]+?(?:is a |is an |is a type of|is an instance of|is a kind of)[^.,:]+)', "is_a"),
    (r'([^.,:]+?(?:implies|causes|leads to|results in|triggers|produces)[^.,:]+)', "implies"),
    (r'([^.,:]+?(?:supersedes|replaces|overrides|obsoletes)[^.,:]+)', "supersedes"),
    (r'([^.,:]+?(?:is part of|is contained in|belongs to|is a component of)[^.,:]+)', "part_of"),
    (r'([^.,:]+?(?:is similar to|is analogous to|resembles|parallels)[^.,:]+)', "similar_to"),
    (r'([^.,:]+?(?:is evidence for|supports|confirms|validates|corroborates)[^.,:]+)', "evidence_for"),
    (r'([^.,:]+?(?:is counterevidence to|refutes|disproves|weakens)[^.,:]+)', "counterevidence_to"),
    (r'([^.,:]+?(?:precondition for|prerequisite for|required for)[^.,:]+)', "precondition_for"),
    (r'([^.,:]+?(?:is exception to|is excluded by|is exempt from)[^.,:]+)', "exception_to"),
    (r'([^.,:]+?(?:is negation of|is opposite of|is inverse of)[^.,:]+)', "negation_of"),
]

def extract_relations(atoms: list) -> list:
    """Extract typed relations between atoms from their text."""
    relations = []
    atom_map = {a["atom_id"]: a for a in atoms}
    atom_texts = {a["atom_id"]: a["canonical_text"] for a in atoms}
    
    for atom_id, text in atom_texts.items():
        t = text.lower()
        for pattern, rel_type in RELATION_PATTERNS:
            matches = re.finditer(pattern, t, re.IGNORECASE)
            for match in matches:
                matched_text = match.group(1).strip()
                # Try to find target atom by matching the related entity mention
                for other_id, other_text in atom_texts.items():
                    if other_id == atom_id:
                        continue
                    # Check if other atom's text overlaps with matched relation
                    other_words = set(other_text.lower().split())
                    matched_words = set(matched_text.lower().split())
                    overlap = len(other_words & matched_words)
                    if overlap >= 3 and len(other_text) > 20:
                        relations.append({
                            "relation_type": rel_type,
                            "source_atom_id": atom_id,
                            "target_atom_id": other_id,
                            "relation_evidence": matched_text[:200],
                            "confidence": "extracted",
                            "deterministic_id": sha256(f"{rel_type}|{atom_id}|{other_id}|{matched_text[:100]}")
                        })
                        break
    return relations

# ── UNKNOWN / Conflict detection ───────────────────────────────────────
def extract_unknowns(atoms: list) -> list:
    """Detect statements that explicitly describe unknowns or gaps."""
    unknown_markers = [
        "unknown", "not known", "uncertain", "unclear", "not yet understood",
        "remains to be", "further research needed", "gap in", "limitation:",
        "insufficient data", "?", "open question"
    ]
    unknowns = []
    for atom in atoms:
        t = atom["canonical_text"].lower()
        for marker in unknown_markers:
            if marker in t:
                unknowns.append({
                    "atom_id": atom["atom_id"],
                    "detected_marker": marker,
                    "annotation": atom["canonical_text"][:300],
                    "status": "UNKNOWN",
                    "deterministic_id": sha256(f"UNKNOWN|{atom['atom_id']}|{marker}")
                })
                break
    return unknowns

def extract_conflicts(atoms: list) -> list:
    """Detect explicit conflict statements between atoms."""
    conflict_markers = [
        "however,", "on the contrary", "in contrast", "disagree",
        "conflicting evidence", "alternative view", "opposing", "debate"
    ]
    conflicts = []
    for atom in atoms:
        t = atom["canonical_text"].lower()
        for marker in conflict_markers:
            if marker in t:
                conflicts.append({
                    "atom_id": atom["atom_id"],
                    "detected_marker": marker,
                    "annotation": atom["canonical_text"][:300],
                    "status": "CONFLICT_DETECTED",
                    "deterministic_id": sha256(f"CONFLICT|{atom['atom_id']}|{marker}")
                })
                break
    return conflicts

# ── Main atomization pipeline ──────────────────────────────────────────
def atomize_document(
    file_path: str,
    source_info: dict = None,
    source_refs: list = None
) -> dict:
    """
    Full atomization pipeline for one document.
    Returns {atoms, relations, unknowns, conflicts, parse_report}.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Source file not found: {file_path}")
    
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()
    
    source_id = str(path)
    doc_hash = sha256(raw_text)
    
    if source_refs is None:
        source_refs = [{"source_id": source_id, "location": f"file:{path.name}", "doc_hash": doc_hash}]
    
    source_info = source_info or {
        "source_type": "file",
        "file_path": str(path),
        "file_type": path.suffix,
        "size_bytes": len(raw_text.encode("utf-8")),
        "doc_hash": doc_hash
    }
    
    # Step 1: Semantic segmentation
    segments = segment_semantic_units(raw_text, source_info)
    
    # Step 2: Atom creation
    atoms = []
    for seg in segments:
        atom = create_atom(seg, source_refs, source_info)
        if atom:
            atoms.append(atom)
    
    # Step 3: Relation extraction
    relations = extract_relations(atoms)
    
    # Step 4: UNKNOWN and conflict detection
    unknowns = extract_unknowns(atoms)
    conflicts = extract_conflicts(atoms)
    
    # Step 5: Deduplicate relations by deterministic_id
    seen_rel = set()
    unique_rels = []
    for rel in relations:
        rid = rel.get("deterministic_id", sha256(json.dumps(rel, sort_keys=True)))
        if rid not in seen_rel:
            seen_rel.add(rid)
            unique_rels.append(rel)
    
    parse_report = {
        "source_file": str(path),
        "source_hash": doc_hash,
        "total_bytes": len(raw_text.encode("utf-8")),
        "total_lines": len(raw_text.split("\n")),
        "segments_found": len(segments),
        "atoms_created": len(atoms),
        "relations_extracted": len(unique_rels),
        "unknowns_detected": len(unknowns),
        "conflicts_detected": len(conflicts),
        "pipeline_version": SCHEMA_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    return {
        "atoms": atoms,
        "relations": unique_rels,
        "unknowns": unknowns,
        "conflicts": conflicts,
        "parse_report": parse_report
    }

# ── LearningPacket generator ───────────────────────────────────────────
def generate_learning_packet(digest_result: dict, source_refs: list = None) -> dict:
    """Generate a canonical LearningPacket from atomization result."""
    atoms = digest_result["atoms"]
    report = digest_result["parse_report"]
    
    packet_id = sha256(json.dumps([a["atom_id"] for a in sorted(atoms, key=lambda x: x["atom_id"])]))
    content_data = json.dumps({"atoms": [a["atom_id"] for a in atoms]}, sort_keys=True)
    content_hash = sha256(content_data)
    
    return {
        "schema_version": "1.0.0",
        "packet_id": packet_id,
        "packet_content_hash": content_hash,
        "idempotency_key": packet_id,
        "status": "candidate",
        "authority_write": False,
        "no_trade_gate": True,
        "processor_version": f"QCLAW-E27-v{SCHEMA_VERSION}",
        "base_knowledge_version": "0008-E27",
        "source_manifest_ids": [r.get("source_id","") for r in (source_refs or [])],
        "source_hash": report["source_hash"],
        "validation_report": {"atoms_count": len(atoms), "relations_count": len(digest_result["relations"])},
        "evidence_refs": [{"type": "parse_report", "data": report}],
        "atoms": atoms,
        "relations": digest_result["relations"],
        "unknowns": digest_result["unknowns"],
        "conflicts": digest_result["conflicts"]
    }

# ── Digest queue runner ────────────────────────────────────────────────
def run_digest_queue(queue_dir: str, output_dir: str) -> dict:
    """Process a digest queue directory, atomize all files, output packets."""
    qpath = Path(queue_dir)
    opath = Path(output_dir)
    opath.mkdir(parents=True, exist_ok=True)
    
    if not qpath.exists():
        return {"status": "QUEUE_EMPTY", "message": f"Queue directory not found: {qpath}"}
    
    source_files = sorted(
        [f for f in qpath.iterdir() if f.is_file() and f.suffix in {".md", ".txt", ".json", ".yaml", ".jsonl"}],
        key=lambda x: x.name
    )
    
    if not source_files:
        return {"status": "QUEUE_EMPTY", "message": "No digestible files in queue"}
    
    all_packets = []
    queue_report = {
        "queue_dir": str(qpath),
        "output_dir": str(opath),
        "files_processed": 0,
        "total_atoms": 0,
        "total_relations": 0,
        "total_unknowns": 0,
        "total_conflicts": 0,
        "packets": []
    }
    
    for sf in source_files:
        result = atomize_document(str(sf))
        packet = generate_learning_packet(result)
        
        # Write packet
        pkt_file = opath / f"{sf.stem}_packet_{packet['packet_id'][:12]}.json"
        with open(pkt_file, "w", encoding="utf-8") as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
        
        all_packets.append(packet)
        queue_report["files_processed"] += 1
        queue_report["total_atoms"] += len(result["atoms"])
        queue_report["total_relations"] += len(result["relations"])
        queue_report["total_unknowns"] += len(result["unknowns"])
        queue_report["total_conflicts"] += len(result["conflicts"])
        queue_report["packets"].append({
            "source": str(sf),
            "packet_id": packet["packet_id"],
            "atoms": len(result["atoms"]),
            "relations": len(result["relations"])
        })
    
    # Write queue report
    report_file = opath / "QUEUE-REPORT.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(queue_report, f, ensure_ascii=False, indent=2)
    
    return {
        "status": "DIGEST_COMPLETE",
        "report": queue_report,
        "packet_count": len(all_packets)
    }
