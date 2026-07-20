"""Canonical serialization and content-addressed identity."""
import hashlib, json, re, unicodedata
from typing import Any, Dict, List, Optional

def normalize_text(s: str) -> str:
    """NFKC normal form, collapse whitespace, strip."""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def canonical_sort_key(obj: Any) -> str:
    """Deterministic sort key for any JSON value."""
    if isinstance(obj, dict):
        return json.dumps(obj, sort_keys=True, ensure_ascii=False)
    if isinstance(obj, list):
        return json.dumps(obj, ensure_ascii=False)
    return str(obj)

def canonical_dict(d: Dict) -> Dict:
    """Return dict with sorted keys, normalized values."""
    result = {}
    for k in sorted(d.keys()):
        v = d[k]
        if isinstance(v, str):
            result[k] = normalize_text(v)
        elif isinstance(v, dict):
            result[k] = canonical_dict(v)
        elif isinstance(v, list):
            result[k] = [
                canonical_dict(item) if isinstance(item, dict) else item
                for item in v
            ]
        else:
            result[k] = v
    return result

def content_hash(obj: Any) -> str:
    """SHA256 of canonical JSON."""
    canon = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()

def semantic_content_hash(obj: Dict) -> str:
    """Content hash of semantically normalized canonical form."""
    canon = canonical_dict(obj)
    return content_hash(canon)

def atom_identity(statement: str, atom_type: str, scope: Optional[str] = None) -> str:
    """Generate deterministic atom_id from semantic core."""
    core = {
        "s": normalize_text(statement),
        "t": atom_type,
    }
    if scope:
        core["sc"] = normalize_text(scope)
    h = content_hash(core)
    return f"at-{h[:16]}"

def relation_identity(source_atom_id: str, target_atom_id: str, rel_type: str) -> str:
    """Generate deterministic relation_id."""
    key = {
        "src": source_atom_id,
        "tgt": target_atom_id,
        "typ": rel_type,
    }
    h = content_hash(key)
    return f"rel-{h[:12]}"

def packet_semantic_id(source_hash: str, atom_ids: List[str]) -> str:
    """Generate semantic packet ID from source hash + ordered atom IDs."""
    key = {"sh": source_hash, "atoms": sorted(atom_ids)}
    h = content_hash(key)
    return f"lp-{h[:16]}"

def packet_instance_id(semantic_id: str, run_context: str) -> str:
    """Instance ID = semantic ID + run context hash."""
    h = hashlib.sha256(run_context.encode()).hexdigest()
    return f"lpi-{semantic_id}-{h[:8]}"

def idempotency_key(semantic_id: str, packet_content_hash_val: str) -> str:
    """Idempotency key for deduplication."""
    return f"{semantic_id}-{packet_content_hash_val[:12]}"

# Fields EXCLUDED from semantic identity (instance-level only):
IGNORABLE_RUNTIME_FIELDS = [
    "processed_at", "packet_instance_id", "processor_version",
    "run_number", "timestamp_ms", "run_context",
]
