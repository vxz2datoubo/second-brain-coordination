#!/usr/bin/env python3
"""
QCLAW E28 — Integrated Pipeline: parse → atomize → relate → redact → packet → verify
Ingests pre-existing repository source with exact commit/blob/path/content anchoring.
"""
import os, sys, hashlib, json, tempfile, subprocess
from pathlib import Path
from datetime import datetime, timezone

THIS = Path(__file__).resolve().parent
SRC = THIS / "src"
OUT = THIS / "output"
sys.path.insert(0, str(SRC))

from qclaw_knowledge_digest.parser import parse_lossless, read_source, normalize_source_ref
from qclaw_knowledge_digest.atomizer_v2 import (
    create_atom, canonical_packet_hash, canonical_packet_id, SCHEMA_VERSION
)
from qclaw_knowledge_digest.relations_v2 import extract_relations, extract_unknowns, extract_conflicts
from qclaw_knowledge_digest.redact_v2 import redact, verify_zero_secrets

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def digest_real_source(source_content: str, source_meta: dict) -> dict:
    """
    Digest a pre-existing repository source document.
    source_meta must include: commit_sha, blob_sha, repo_relative_path, content_sha256
    """
    # Step 1: Redact (fail-closed)
    redacted_text, redaction_log = redact(source_content, source_meta["repo_relative_path"])
    clean, violations = verify_zero_secrets(redacted_text)
    if not clean:
        return {"error": "zero_secret_violation", "violations": violations}
    
    # Step 2: Lossless parse
    units, parse_report = parse_lossless(redacted_text)
    
    # Step 3: Create atoms (no timestamps, no paths)
    atoms = []
    for u in units:
        atom = create_atom(u, source_meta["content_sha256"], {
            "repo_relative_path": source_meta["repo_relative_path"],
            "blob_sha256": source_meta["blob_sha"],
            "commit_sha": source_meta["commit_sha"],
            "content_sha256": source_meta["content_sha256"],
            "encoding": "utf-8"
        })
        if atom:
            atoms.append(atom)
    
    # Step 4: Extract relations, unknowns, conflicts
    spans = {a["atom_id"]: (a["source_span"]["start_byte"], a["source_span"]["end_byte"]) 
             for a in atoms}
    relations = extract_relations(atoms, spans)
    unknowns = extract_unknowns(atoms)
    conflicts = extract_conflicts(atoms)
    
    # Step 5: Canonical packet
    source_manifest = {
        "source_relative_path": source_meta["repo_relative_path"],
        "source_commit_sha": source_meta["commit_sha"],
        "source_blob_sha": source_meta["blob_sha"],
        "source_content_sha256": source_meta["content_sha256"],
        "parser_version": "lossless_v3",
        "atomizer_version": SCHEMA_VERSION
    }
    
    packet_id = canonical_packet_id(atoms, source_meta["content_sha256"])
    content_hash = canonical_packet_hash(atoms, relations, unknowns, conflicts, source_manifest)
    # Document hash: same as content_hash for full packet
    packet_doc_hash = content_hash
    
    packet = {
        "schema_version": "learning-packet-1.0",
        "packet_id": packet_id,
        "packet_content_hash": content_hash,
        "packet_document_hash": packet_doc_hash,
        "idempotency_key": sha256(f"{source_meta['commit_sha']}:{source_meta['repo_relative_path']}:{content_hash}"),
        "status": "candidate",
        "authority_write": False,
        "no_trade_gate": True,
        "processor_version": f"QCLAW-E28-{SCHEMA_VERSION}",
        "base_knowledge_version": source_meta["commit_sha"],
        "source_manifest_ids": [source_meta["repo_relative_path"]],
        "source_hash": source_meta["content_sha256"],
        "validation_report": {
            "parse_report": {
                "source_bytes": parse_report.source_bytes,
                "atom_bytes_sum": parse_report.atom_bytes,
                "gap_bytes_sum": parse_report.gap_bytes,
                "coverage_ratio": parse_report.coverage_ratio,
                "byte_accounting_verified": (parse_report.atom_bytes + parse_report.gap_bytes == parse_report.source_bytes),
                "encoding_rejected_count": 0,
                "zero_secrets_verified": clean
            },
            "redactions": len(redaction_log),
            "validator_version": "e28-v1"
        },
        "evidence_refs": [
            f"commit:{source_meta['commit_sha']}",
            f"blob:{source_meta['blob_sha']}",
            f"content_sha256:{source_meta['content_sha256']}"
        ],
        "atoms": atoms,
        "relations": relations,
        "unknowns": unknowns,
        "conflicts": conflicts
    }
    
    return packet

# ── Run ────────────────────────────────────────────────────────────────
def run():
    import subprocess
    
    # Source: pre-existing governance decision (GPT-authored, in repo at base commit)
    SOURCE_COMMIT = "aa7ab8398f46ee77ce8f4f407aa7cea1ac4aebd1"
    SOURCE_BLOB = "862f223ecc7ef3cc5b7367cc7c70809b85de8734"
    SOURCE_PATH = "coordination/GOVERNANCE/DECISIONS/2026-07-27-DUAL-LAYER-INITIATIVE-AND-GPT-ORCHESTRATION-DECISION.md"
    
    # Fetch content from GitHub API
    r = subprocess.run([
        "gh", "api",
        f"/repos/vxz2datoubo/second-brain-coordination/contents/{SOURCE_PATH}?ref={SOURCE_COMMIT}",
        "-H", "Accept: application/vnd.github.raw+json"
    ], capture_output=True)
    
    source_content = r.stdout.decode("utf-8")
    source_bytes = r.stdout
    content_sha256 = hashlib.sha256(source_bytes).hexdigest()
    
    source_meta = {
        "commit_sha": SOURCE_COMMIT,
        "blob_sha": SOURCE_BLOB,
        "repo_relative_path": SOURCE_PATH,
        "content_sha256": content_sha256,
        "file_size_bytes": len(source_bytes)
    }
    
    print(f"Source: {SOURCE_PATH}")
    print(f"Size: {len(source_bytes)} bytes, SHA256: {content_sha256}")
    
    packet = digest_real_source(source_content, source_meta)
    
    if "error" in packet:
        print(f"ERROR: {packet}")
        return 1
    
    print(f"\nPacket ID: {packet['packet_id']}")
    print(f"Content Hash: {packet['packet_content_hash']}")
    print(f"Atoms: {len(packet['atoms'])}")
    print(f"Relations: {len(packet['relations'])}")
    print(f"Unknowns: {len(packet['unknowns'])}")
    print(f"Conflicts: {len(packet['conflicts'])}")
    print(f"Byte accounting: {packet['validation_report']['parse_report']['byte_accounting_verified']}")
    print(f"Coverage: {packet['validation_report']['parse_report']['coverage_ratio']:.4f}")
    print(f"Zero secrets: {packet['validation_report']['parse_report']['zero_secrets_verified']}")
    
    # Save packet
    OUT.mkdir(parents=True, exist_ok=True)
    packet_path = OUT / f"packet_{SOURCE_PATH.replace('/', '_')}_{packet['packet_id'][:12]}.json"
    with open(packet_path, "w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)
    print(f"\nSaved: {packet_path} ({packet_path.stat().st_size} bytes)")
    
    # Verify: re-parse and check determinism
    packet2 = digest_real_source(source_content, source_meta)
    print(f"\nDeterminism check:")
    print(f"  Packet ID match: {packet['packet_id'] == packet2['packet_id']}")
    print(f"  Content hash match: {packet['packet_content_hash'] == packet2['packet_content_hash']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(run())
