#!/usr/bin/env python3
"""
QCLAW E27 — Integrated Pipeline: redact → atomize → validate → packet
"""
import sys, json, os
from pathlib import Path
from datetime import datetime, timezone

SRC = Path(__file__).resolve().parent / "src"
sys.path.insert(0, str(SRC))

from qclaw_knowledge_digest.redact import redact, verify_zero_secrets, sha256
from qclaw_knowledge_digest.atomizer import (
    atomize_document, generate_learning_packet, run_digest_queue,
    segment_semantic_units, create_atom, classify_content_type
)

def integrated_atomize(filepath: str) -> dict:
    """Redact then atomize a single document. Returns full pipeline result."""
    path = Path(filepath)
    
    # Step 1: Redact
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()
    raw_hash = sha256(raw)
    
    redacted_text, redaction_log = redact(raw, str(path))
    redacted_hash = sha256(redacted_text)
    
    # Step 2: Write redacted to temp, atomize
    tmp = path.parent / f".redacted_{path.name}"
    tmp.write_text(redacted_text, encoding="utf-8")
    
    source_refs = [{
        "source_id": str(path),
        "location": f"file:{path.name}",
        "doc_hash": raw_hash,
        "redacted_hash": redacted_hash,
        "redactions": len(redaction_log)
    }]
    
    result = atomize_document(str(tmp), {"source_type": "file"}, source_refs)
    
    # Step 3: Verify zero secrets in output
    for atom in result["atoms"]:
        if not verify_zero_secrets(atom["canonical_text"]):
            result["parse_report"]["zero_secret_violation"] = True
            result["parse_report"]["violating_atom_id"] = atom["atom_id"]
    
    result["parse_report"]["redactions_applied"] = len(redaction_log)
    result["parse_report"]["redaction_log"] = redaction_log
    result["parse_report"]["original_hash"] = raw_hash
    result["parse_report"]["redacted_hash"] = redacted_hash
    result["parse_report"]["zero_secrets_verified"] = verify_zero_secrets(redacted_text)
    
    # Cleanup
    tmp.unlink()
    
    return result

def integrated_digest_queue(queue_dir: str, output_dir: str) -> dict:
    """Redact + atomize + packet + verify entire queue."""
    qpath = Path(queue_dir)
    opath = Path(output_dir)
    opath.mkdir(parents=True, exist_ok=True)
    
    source_files = sorted(
        [f for f in qpath.iterdir() if f.is_file() and f.suffix in {".md", ".txt", ".json", ".yaml", ".jsonl"}],
        key=lambda x: x.name
    )
    
    report = {
        "pipeline": "QCLAW-E27-integrated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "queue_dir": str(qpath),
        "files_processed": 0,
        "total_atoms": 0,
        "total_relations": 0,
        "total_unknowns": 0,
        "total_conflicts": 0,
        "total_redactions": 0,
        "zero_secret_violations": 0,
        "packets": []
    }
    
    for sf in source_files:
        result = integrated_atomize(str(sf))
        packet = generate_learning_packet(result)
        
        pkt_file = opath / f"{sf.stem}_packet_{packet['packet_id'][:12]}.json"
        with open(pkt_file, "w", encoding="utf-8") as f:
            json.dump(packet, f, ensure_ascii=False, indent=2)
        
        report["files_processed"] += 1
        report["total_atoms"] += len(result["atoms"])
        report["total_relations"] += len(result["relations"])
        report["total_unknowns"] += len(result["unknowns"])
        report["total_conflicts"] += len(result["conflicts"])
        report["total_redactions"] += result["parse_report"].get("redactions_applied", 0)
        
        if result["parse_report"].get("zero_secret_violation"):
            report["zero_secret_violations"] += 1
        
        report["packets"].append({
            "source": str(sf),
            "packet_id": packet["packet_id"],
            "atoms": len(result["atoms"]),
            "relations": len(result["relations"]),
            "redactions": result["parse_report"].get("redactions_applied", 0),
            "zero_secrets_ok": not result["parse_report"].get("zero_secret_violation", False)
        })
    
    with open(opath / "QUEUE-REPORT.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    return {"status": "DIGEST_COMPLETE" if report["zero_secret_violations"] == 0 else "SECRET_VIOLATION_DETECTED", "report": report}

if __name__ == "__main__":
    # Run batch 002 through integrated pipeline
    e27 = Path(__file__).resolve().parent
    queue = e27 / "digest_queue" / "batch_002"
    output = e27 / "output_batch_002"
    
    r = integrated_digest_queue(str(queue), str(output))
    print(json.dumps(r["report"], indent=2, ensure_ascii=False))
