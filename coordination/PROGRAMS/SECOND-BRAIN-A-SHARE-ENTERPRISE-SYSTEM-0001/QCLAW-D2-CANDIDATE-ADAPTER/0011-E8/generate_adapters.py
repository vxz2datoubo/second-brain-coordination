#!/usr/bin/env python3
"""
generate_adapters.py — Epoch 18 Gate B R3
PR #100: Strict Canonical Identity, Lossless Quarantine & Executable Evidence

ALL 10 blocking defects fixed:
  E18-B01: json.loads(…, object_pairs_hook=OrderedDict) + duplicate key rejection
  E18-B02: Dedicated StrictSafeLoader class (NO global YAML patching)
  E18-B03: adapter_id = sha256(full did || policy_version || canonical_source_hash || disposition)
  E18-B04: Lossless canonical_source_hash covering ALL source fields (NFC-normalized, alphabetical)
  E18-B05: Full-ID quarantine — all 15 Liu Xin atoms via FULL-ID-QUARANTINE-MANIFEST.yaml
  E18-B06: AMBIGUITY-MANIFEST with >=2 hypotheses per entry
  E18-B10: Complete D2-ADAPTER-PACKAGE.json with all 99/147/64 IDs, hashes, artifact coverage
"""
import hashlib
import json
import os
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path

# Python 3.8+: SafeLoader is available
import yaml

# ═══════════════════════════════════════════════════════════════
# E18-B02: StrictSafeLoader — dedicated sealed class, NO global patch
# ═══════════════════════════════════════════════════════════════
class StrictSafeLoader(yaml.SafeLoader):
    """Dedicated YAML loader that rejects duplicate mappings in a sealed manner.
    NO global YAML patching — this class is instantiated explicitly for each load call."""

    @classmethod
    def construct_mapping(cls, loader, node, deep=False):
        """Override SafeLoader's construct_mapping to reject duplicates."""
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            # YAML keys can be str, int, float, bool, null, etc.
            # Use repr for deterministic duplicate detection
            try:
                hash(key)
                hashable = key
            except TypeError:
                hashable = str(key)
            if hashable in mapping:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    f"StrictSafeLoader: duplicate key {key!r} detected",
                    key_node.start_mark
                )
            mapping[hashable] = value_node
        # Build final mapping using parent class logic
        result = {}
        for key, (value_node) in mapping.items():
            value = loader.construct_object(value_node, deep=deep)
            if key in result:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    f"StrictSafeLoader: duplicate key {key!r} detected",
                    None
                )
            result[key] = value
        return result


# Override the mapping constructor ONLY in our subclass
StrictSafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    StrictSafeLoader.construct_mapping
)

# ═══════════════════════════════════════════════════════════════
# E18-B01: Strict JSON/JSONL parsing with duplicate key detection
# ═══════════════════════════════════════════════════════════════
def json_loads_no_duplicates(text, source_label=""):
    """Load JSON string, rejecting duplicate keys.
    Uses object_pairs_hook=OrderedDict and checks for duplicates."""
    seen = set()
    duplicates = []

    def check_duplicates(pairs):
        result = OrderedDict()
        for key, value in pairs:
            if key in result:
                duplicates.append(key)
            else:
                result[key] = value
        return result

    try:
        obj = json.loads(text, object_pairs_hook=check_duplicates)
    except json.JSONDecodeError:
        raise

    if duplicates:
        raise ValueError(
            f"JSON duplicate keys {duplicates} in {source_label}"
        )
    return obj


def load_jsonl_strict(path, id_field=None):
    """Load JSONL with duplicate key detection in JSON parsing + duplicate ID check."""
    records = []
    seen_ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json_loads_no_duplicates(line, f"{path}:{line_no}")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"ERROR: Invalid JSON in {path} line {line_no}: {e}", file=sys.stderr)
                sys.exit(1)

            if id_field and id_field in record:
                rid = record[id_field]
                if rid in seen_ids:
                    print(f"ERROR: Duplicate {id_field} '{rid}' in {path} line {line_no}", file=sys.stderr)
                    sys.exit(1)
                seen_ids.add(rid)
            records.append(record)
    return records


def load_yaml_strict(path):
    """Load YAML with StrictSafeLoader (dedicated, no global patch)."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=StrictSafeLoader)


# ═══════════════════════════════════════════════════════════════
# Common utilities
# ═══════════════════════════════════════════════════════════════
def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_size(path):
    return os.path.getsize(path)


# ═══════════════════════════════════════════════════════════════
# E18-B04: Lossless canonical source hash — ALL fields, NFC normalized
# ═══════════════════════════════════════════════════════════════
def nfc_normalize(val):
    """Recursively NFC-normalize all string values."""
    if isinstance(val, str):
        return unicodedata.normalize("NFC", val)
    elif isinstance(val, dict):
        return {k: nfc_normalize(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [nfc_normalize(v) for v in val]
    else:
        return val


def compute_canonical_source_hash(atom):
    """E18-B04: Hash ALL fields of the source record (lossless).
    NFC-normalize all strings, sort keys alphabetically, include all fields."""
    normalized = nfc_normalize(dict(atom))
    raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def make_canonical_source_record(atom):
    """Create the full canonical source record (all fields, NFC normalized, alphabetical)."""
    normalized = nfc_normalize(dict(atom))
    return OrderedDict(sorted(normalized.items()))


# ═══════════════════════════════════════════════════════════════
# E18-B03: Full-ID adapter_id
# = sha256(full_deterministic_id || policy_version || canonical_source_hash || disposition)
# ═══════════════════════════════════════════════════════════════
def build_adapter_id_full(deterministic_id, policy_version, canonical_source_hash, disposition):
    """E18-B03: Full deterministic_id (not truncated), lossless formula."""
    raw = f"{deterministic_id}||{policy_version}||{canonical_source_hash}||{disposition}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ═══════════════════════════════════════════════════════════════
# Policy / Manifest loading
# ═══════════════════════════════════════════════════════════════
def load_policy(policy_path):
    policy = load_yaml_strict(policy_path)
    required = ["Q0_TO_D2_FAMILY", "Q0_TO_D2_SUBTYPE", "SUBTYPE_TO_FAMILY", "classification_rules", "no_default_policy"]
    for key in required:
        if key not in policy:
            print(f"ERROR: MAPPING-POLICY.yaml missing required key: {key}", file=sys.stderr)
            sys.exit(1)
    return policy


def load_quarantine_manifest(path):
    """Load FULL-ID-QUARANTINE-MANIFEST.yaml (E18-B05: 15 entries)."""
    manifest = load_yaml_strict(path)
    entries = manifest.get("quarantine_entries", [])
    result = {}
    for e in entries:
        did = e["deterministic_id"]
        result[did] = e
    return result


def load_ambiguity_manifest(path):
    """Load AMBIGUITY-MANIFEST.yaml (E18-B06: >=2 hypotheses per entry).
    Also validates that every entry has >=2 hypotheses."""
    manifest = load_yaml_strict(path)
    entries = manifest.get("ambiguity_entries", [])

    # E18-B06 enforcement
    for e in entries:
        hyps = e.get("hypotheses", [])
        if len(hyps) < 2:
            print(f"ERROR: AMBIGUITY-MANIFEST entry for atom {e.get('atom_index')} has only {len(hyps)} hypothesis/hypotheses. "
                  f"E18-B06 requires >=2 distinct D2-compatible hypotheses.", file=sys.stderr)
            sys.exit(1)

    result = {}
    for e in entries:
        did = e["deterministic_id"]
        result[did] = e
    return result


# ═══════════════════════════════════════════════════════════════
# Classification
# ═══════════════════════════════════════════════════════════════
def classify_atom(atom, policy, quarantine_map, ambiguity_map):
    """Classify atom per MAPPING-POLICY.yaml priority rules.
    E18-B05: Full quarantine check (15 entries).
    E18-B06: Ambiguity requires >=2 hypotheses.
    """
    did = atom.get("deterministic_id", "")
    q0_family = atom.get("subject_family")
    q0_subtype = atom.get("subject_subtype")
    perspective = atom.get("perspective_class", "")

    family_map = policy.get("Q0_TO_D2_FAMILY", {})
    subtype_map = policy.get("Q0_TO_D2_SUBTYPE", {})
    subtype_to_family = policy.get("SUBTYPE_TO_FAMILY", {})

    # Priority 1: Quarantine check (E18-B05: full 15-person audit)
    if did in quarantine_map:
        return {
            "disposition": "PERSON_IDENTITY_QUARANTINED",
            "q0_family": q0_family,
            "q0_subtype": q0_subtype,
            "d2_family": None,
            "d2_subtype": None,
            "rationale": quarantine_map[did].get("rationale", "Named person quarantined"),
        }

    # Priority 2: Full mapping (both family + subtype recognized)
    if q0_family and q0_subtype:
        if q0_family in family_map and q0_subtype in subtype_map:
            d2_subtype = subtype_map[q0_subtype]
            d2_family = subtype_to_family.get(d2_subtype)
            if d2_family:
                return {
                    "disposition": "MAPPED",
                    "q0_family": q0_family,
                    "q0_subtype": q0_subtype,
                    "d2_family": d2_family,
                    "d2_subtype": d2_subtype,
                    "rationale": f"Full mapping: {q0_family}/{q0_subtype} -> {d2_family}/{d2_subtype}",
                }

    # Priority 3: Family recognized, no subtype -> AMBIGUOUS or UNMAPPED
    if q0_family and q0_family in family_map and not q0_subtype:
        if did in ambiguity_map:
            entry = ambiguity_map[did]
            hyps = entry.get("hypotheses", [])
            # E18-B06: Verify >=2 hypotheses (already checked at load time, defense in depth)
            if len(hyps) >= 2:
                return {
                    "disposition": "AMBIGUOUS",
                    "q0_family": q0_family,
                    "q0_subtype": None,
                    "d2_family": None,
                    "d2_subtype": None,
                    "hypotheses": hyps,
                    "rationale": entry.get("rationale", "Ambiguous per manifest with 2+ hypotheses"),
                    "ambiguity_entry": entry,
                }
            else:
                # Fall-through to UNMAPPED (E18-B06 protection)
                return {
                    "disposition": "UNMAPPED",
                    "q0_family": q0_family,
                    "q0_subtype": None,
                    "d2_family": None,
                    "d2_subtype": None,
                    "rationale": f"Family '{q0_family}' in ambiguity manifest but <2 hypotheses (E18-B06 violation)",
                    "downgrade_note": "AMBIGUITY_INSUFFICIENT_HYPOTHESES",
                }
        else:
            return {
                "disposition": "UNMAPPED",
                "q0_family": q0_family,
                "q0_subtype": None,
                "d2_family": None,
                "d2_subtype": None,
                "rationale": f"Family '{q0_family}' recognized but no subtype and not in AMBIGUITY-MANIFEST",
                "downgrade_note": "NO_SUBTYPE_AND_NO_MANIFEST_ENTRY",
            }

    # Priority 3 continued: Family present but not in family_map -> UNMAPPED
    if q0_family and not q0_subtype:
        return {
            "disposition": "UNMAPPED",
            "q0_family": q0_family,
            "q0_subtype": None,
            "d2_family": None,
            "d2_subtype": None,
            "rationale": f"Family '{q0_family}' not in mapping policy",
            "downgrade_note": "FAMILY_NOT_IN_POLICY",
        }

    # Priority 4: No family
    if not q0_family:
        if perspective == "MARKET_STRUCTURE":
            return {
                "disposition": "CONTEXT_ONLY",
                "q0_family": None,
                "q0_subtype": None,
                "d2_family": None,
                "d2_subtype": None,
                "rationale": "MARKET_STRUCTURE atom with no participant evidence",
            }
        return {
            "disposition": "UNMAPPED",
            "q0_family": None,
            "q0_subtype": None,
            "d2_family": None,
            "d2_subtype": None,
            "rationale": f"No family and perspective '{perspective}' is not MARKET_STRUCTURE",
            "downgrade_note": "NO_FAMILY_AND_NOT_MARKET_STRUCTURE",
        }

    return {
        "disposition": "UNMAPPED",
        "q0_family": q0_family,
        "q0_subtype": q0_subtype,
        "d2_family": None,
        "d2_subtype": None,
        "rationale": "Fallthrough - unclassifiable",
    }


# ═══════════════════════════════════════════════════════════════
# Main generation pipeline
# ═══════════════════════════════════════════════════════════════
def generate_adapters(src_dir, policy_dir, output_dir):
    """Main generation pipeline with all E18 fixes."""

    # Load policy and manifests
    policy = load_policy(os.path.join(policy_dir, "MAPPING-POLICY.yaml"))
    quarantine_map = load_quarantine_manifest(os.path.join(policy_dir, "FULL-ID-QUARANTINE-MANIFEST.yaml"))
    ambiguity_map = load_ambiguity_manifest(os.path.join(policy_dir, "AMBIGUITY-MANIFEST.yaml"))

    policy_version = policy.get("policy", {}).get("version", "18.0")

    # Load Q0 sources (strict: duplicate key detection)
    atoms_path = os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")
    atoms = load_jsonl_strict(atoms_path, id_field="deterministic_id")

    relations_path = os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")
    relations = load_jsonl_strict(relations_path, id_field="relation_id")

    questions_path = os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")
    questions = load_jsonl_strict(questions_path, id_field="question_id")

    # Load family map
    family_map_path = os.path.join(src_dir, "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml")
    family_map = load_yaml_strict(family_map_path)

    print(f"Loaded {len(atoms)} atoms, {len(relations)} relations, {len(questions)} questions", file=sys.stderr)

    # Verify source hashes against policy lock
    expected_hashes = {
        "atoms": policy["source_lock"]["q0_atoms_sha256"],
        "relations": policy["source_lock"]["q0_relations_sha256"],
        "questions": policy["source_lock"]["q0_questions_sha256"],
        "family_map": policy["source_lock"]["q0_family_map_sha256"],
    }
    actual_hashes = {
        "atoms": file_sha256(atoms_path),
        "relations": file_sha256(relations_path),
        "questions": file_sha256(questions_path),
        "family_map": file_sha256(family_map_path),
    }
    for key, expected in expected_hashes.items():
        actual = actual_hashes[key]
        if expected != actual:
            print(f"ERROR: Source hash mismatch for {key}: expected {expected}, got {actual}", file=sys.stderr)
            sys.exit(1)
    print("Source hashes verified against policy lock", file=sys.stderr)

    # Generate adapters
    adapters = []
    seen_adapter_ids = set()
    disposition_counts = {
        "MAPPED": 0,
        "AMBIGUOUS": 0,
        "CONTEXT_ONLY": 0,
        "UNMAPPED": 0,
        "PERSON_IDENTITY_QUARANTINED": 0,
    }

    for atom in atoms:
        did = atom.get("deterministic_id")
        result = classify_atom(atom, policy, quarantine_map, ambiguity_map)
        disposition = result["disposition"]
        disposition_counts[disposition] += 1

        # E18-B04: Lossless canonical source hash (ALL fields, NFC normalized)
        canonical_source_hash = compute_canonical_source_hash(atom)
        canonical_source_record = make_canonical_source_record(atom)

        # E18-B03: Full-ID adapter_id
        adapter_id = build_adapter_id_full(
            did, policy_version, canonical_source_hash, disposition
        )

        if adapter_id in seen_adapter_ids:
            print(f"ERROR: Duplicate adapter_id '{adapter_id}' generated", file=sys.stderr)
            sys.exit(1)
        seen_adapter_ids.add(adapter_id)

        adapter = OrderedDict()
        adapter["adapter_id"] = adapter_id
        adapter["source_deterministic_id"] = did
        adapter["atom_index"] = atom.get("atom_index")
        adapter["disposition"] = disposition
        adapter["q0_family"] = result.get("q0_family")
        adapter["q0_subtype"] = result.get("q0_subtype")
        adapter["d2_family"] = result.get("d2_family")
        adapter["d2_subtype"] = result.get("d2_subtype")
        adapter["policy_version"] = policy_version
        adapter["canonical_source_hash"] = canonical_source_hash
        adapter["canonical_source_record"] = canonical_source_record
        adapter["rationale"] = result.get("rationale", "")
        adapter["atom_type"] = atom.get("atom_type")
        adapter["confidence"] = atom.get("confidence")
        adapter["evidence_status"] = atom.get("evidence_status")
        adapter["perspective_class"] = atom.get("perspective_class")

        # Downgrade note for UNMAPPED
        if "downgrade_note" in result:
            adapter["downgrade_note"] = result["downgrade_note"]

        # Ambiguity hypotheses
        if disposition == "AMBIGUOUS" and "hypotheses" in result:
            adapter["ambiguity_hypotheses"] = result["hypotheses"]

        # Quarantine reference
        if disposition == "PERSON_IDENTITY_QUARANTINED":
            adapter["quarantine_rationale"] = result.get("rationale", "")

        adapters.append(adapter)

    return adapters, disposition_counts, atoms, relations, questions, family_map, quarantine_map, ambiguity_map


def main():
    base = Path(__file__).resolve().parent

    # Resolve paths
    src_dir = os.environ.get("Q0_SRC_DIR")
    if not src_dir or not os.path.exists(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")):
        # Default: relative to script location
        src_dir = str(base.parent.parent.parent.parent / "e17_gate_b_r2" / "q0_sources")

    policy_dir = os.environ.get("POLICY_DIR", str(base))
    output_dir = os.environ.get("OUTPUT_DIR", str(base))

    print(f"Source dir: {src_dir}", file=sys.stderr)
    print(f"Policy dir: {policy_dir}", file=sys.stderr)
    print(f"Output dir: {output_dir}", file=sys.stderr)

    # Verify required files
    required_src = [
        "KNOWLEDGE-ATOMS.jsonl", "KNOWLEDGE-RELATIONS.jsonl",
        "ADVERSARIAL-QUESTION-SET.jsonl", "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml"
    ]
    for f in required_src:
        p = os.path.join(src_dir, f)
        if not os.path.exists(p):
            print(f"ERROR: Required source file not found: {p}", file=sys.stderr)
            sys.exit(1)

    required_policy = [
        "MAPPING-POLICY.yaml", "FULL-ID-QUARANTINE-MANIFEST.yaml",
        "AMBIGUITY-MANIFEST.yaml", "D2-INTERFACE-SNAPSHOT.yaml"
    ]
    for f in required_policy:
        p = os.path.join(policy_dir, f)
        if not os.path.exists(p):
            print(f"ERROR: Required policy file not found: {p}", file=sys.stderr)
            sys.exit(1)

    adapters, counts, atoms, relations, questions, family_map, quarantine_map, ambiguity_map = generate_adapters(
        src_dir, policy_dir, output_dir
    )

    # ═══════════════════════════════════════════════════════════
    # Write D2-CANDIDATE-ADAPTERS.jsonl (deterministic key order)
    # ═══════════════════════════════════════════════════════════
    adapters_path = os.path.join(output_dir, "D2-CANDIDATE-ADAPTERS.jsonl")
    with open(adapters_path, "w", encoding="utf-8") as f:
        for a in adapters:
            # Write with sorted keys for deterministic output
            f.write(json.dumps(a, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Wrote {len(adapters)} adapters to {adapters_path}", file=sys.stderr)

    adapters_jsonl_sha256 = file_sha256(adapters_path)

    # ═══════════════════════════════════════════════════════════
    # Compute all derivative hashes/sizes
    # ═══════════════════════════════════════════════════════════
    atom_ids_list = [a["deterministic_id"] for a in atoms]
    relation_ids_list = [r["relation_id"] for r in relations]
    question_ids_list = [q["question_id"] for q in questions]
    adapter_dids = [a["source_deterministic_id"] for a in adapters]
    adapter_cshashes = [a["canonical_source_hash"] for a in adapters]

    source_hashes = {
        "atoms": file_sha256(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
        "relations": file_sha256(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
        "questions": file_sha256(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
        "family_map": file_sha256(os.path.join(src_dir, "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml")),
    }

    source_sizes = {
        "atoms": file_size(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
        "relations": file_size(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
        "questions": file_size(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
        "family_map": file_size(os.path.join(src_dir, "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml")),
    }

    policy_hashes = {
        "mapping_policy": file_sha256(os.path.join(policy_dir, "MAPPING-POLICY.yaml")),
        "quarantine_manifest": file_sha256(os.path.join(policy_dir, "FULL-ID-QUARANTINE-MANIFEST.yaml")),
        "ambiguity_manifest": file_sha256(os.path.join(policy_dir, "AMBIGUITY-MANIFEST.yaml")),
        "d2_snapshot": file_sha256(os.path.join(policy_dir, "D2-INTERFACE-SNAPSHOT.yaml")),
    }

    policy = load_policy(os.path.join(policy_dir, "MAPPING-POLICY.yaml"))
    policy_version = policy.get("policy", {}).get("version", "18.0")

    # ═══════════════════════════════════════════════════════════
    # E18-B10: Complete D2-ADAPTER-PACKAGE.json
    # Includes ALL 99 deterministic_ids with canonical_source_hashes,
    # ALL 147 relation_ids, ALL 64 question_ids, ALL artifact hashes/sizes
    # ═══════════════════════════════════════════════════════════
    package = OrderedDict()
    package["package_id"] = hashlib.sha256(
        b"E18-PR100-qclaw-d2-candidate-adapter-0011-e8-strict-canonical"
    ).hexdigest()
    package["epoch"] = 18
    package["schema"] = "25.0"
    package["task_id"] = "QCLAW-PR100-STRICT-CANONICAL-IDENTITY-LOSSLESS-QUARANTINE-AND-EXECUTABLE-EVIDENCE-CLOSURE-0020-E18"
    package["policy_version"] = policy_version
    package["adapter_count"] = len(adapters)
    package["atom_count"] = len(atoms)
    package["relation_count"] = len(relations)
    package["question_count"] = len(questions)
    package["disposition_counts"] = counts
    package["adapters_sha256"] = adapters_jsonl_sha256

    # Source lock (recomputed hashes)
    package["source_lock"] = OrderedDict([
        ("d2_interface_sha256", "33a7d821866bb327143a51c18cf7619bea1b706c189f6713584fd459229175f1"),
        ("d2_interface_commit", "d6f9e2e4d38861e91353be177c9ceacedde6d7ee"),
        ("q0_atoms_sha256", source_hashes["atoms"]),
        ("q0_relations_sha256", source_hashes["relations"]),
        ("q0_questions_sha256", source_hashes["questions"]),
        ("q0_family_map_sha256", source_hashes["family_map"]),
    ])

    # Policy manifest hashes
    package["policy_manifest_hashes"] = policy_hashes

    # ═══════════════════════════════════════════════════════════
    # ALL 99/147/64 IDs with their canonical source hashes
    # ═══════════════════════════════════════════════════════════
    package["atom_ids"] = [
        OrderedDict([
            ("deterministic_id", aid),
            ("canonical_source_hash", csh),
        ])
        for aid, csh in zip(adapter_dids, adapter_cshashes)
    ]

    package["relation_ids"] = [
        OrderedDict([
            ("relation_id", rid),
        ])
        for rid in relation_ids_list
    ]

    package["question_ids"] = [
        OrderedDict([
            ("question_id", qid),
        ])
        for qid in question_ids_list
    ]

    # Adapter identity coverage (link every adapter to its source)
    package["adapter_identity_coverage"] = [
        OrderedDict([
            ("adapter_id", a["adapter_id"]),
            ("source_deterministic_id", a["source_deterministic_id"]),
            ("disposition", a["disposition"]),
            ("canonical_source_hash", a["canonical_source_hash"]),
            ("d2_family", a.get("d2_family")),
            ("d2_subtype", a.get("d2_subtype")),
        ])
        for a in adapters
    ]

    package_path = os.path.join(output_dir, "D2-ADAPTER-PACKAGE.json")
    with open(package_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"Wrote package to {package_path}", file=sys.stderr)

    package_sha256 = file_sha256(package_path)

    # ═══════════════════════════════════════════════════════════
    # D2-ADAPTER-SUMMARY.yaml
    # ═══════════════════════════════════════════════════════════
    summary = {
        "d2_adapter_summary": OrderedDict([
            ("epoch", 18),
            ("schema", "25.0"),
            ("task_id", "QCLAW-PR100-STRICT-CANONICAL-IDENTITY-LOSSLESS-QUARANTINE-AND-EXECUTABLE-EVIDENCE-CLOSURE-0020-E18"),
            ("policy_version", policy_version),
            ("total_adapters", len(adapters)),
            ("total_atoms", len(atoms)),
            ("total_relations", len(relations)),
            ("total_questions", len(questions)),
            ("disposition_counts", counts),
            ("adapters_sha256", adapters_jsonl_sha256),
            ("package_sha256", package_sha256),
            ("source_lock", package["source_lock"]),
            ("policy_hashes", policy_hashes),
        ])
    }
    summary_path = os.path.join(output_dir, "D2-ADAPTER-SUMMARY.yaml")
    with open(summary_path, "w", encoding="utf-8") as f:
        yaml.dump(json.loads(json.dumps(summary)), f, default_flow_style=False, allow_unicode=True, Dumper=yaml.SafeDumper)
    print(f"Wrote summary to {summary_path}", file=sys.stderr)

    # ═══════════════════════════════════════════════════════════
    # Coverage files
    # ═══════════════════════════════════════════════════════════
    # COVERAGE-ATOMS.yaml
    atoms_coverage = OrderedDict()
    atoms_coverage["total_atoms"] = len(atoms)
    atoms_coverage["covered_atom_ids"] = [a["deterministic_id"] for a in atoms]
    atoms_coverage["covered_by_disposition"] = OrderedDict()
    for a in adapters:
        disp = a["disposition"]
        if disp not in atoms_coverage["covered_by_disposition"]:
            atoms_coverage["covered_by_disposition"][disp] = []
        atoms_coverage["covered_by_disposition"][disp].append(a["source_deterministic_id"])
    atoms_coverage["quarantine_count"] = len(quarantine_map)
    atoms_coverage["ambiguous_count"] = len(ambiguity_map)
    atoms_coverage_path = os.path.join(output_dir, "COVERAGE-ATOMS.yaml")
    with open(atoms_coverage_path, "w", encoding="utf-8") as f:
        yaml.dump(json.loads(json.dumps(atoms_coverage)), f, default_flow_style=False, allow_unicode=True, Dumper=yaml.SafeDumper)

    # COVERAGE-RELATIONS.yaml
    relations_coverage = {
        "total_relations": len(relations),
        "covered_relation_ids": [r["relation_id"] for r in relations],
    }
    with open(os.path.join(output_dir, "COVERAGE-RELATIONS.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(relations_coverage, f, default_flow_style=False, allow_unicode=True, Dumper=yaml.SafeDumper)

    # COVERAGE-QUESTIONS.yaml
    questions_coverage = {
        "total_questions": len(questions),
        "covered_question_ids": [q["question_id"] for q in questions],
    }
    with open(os.path.join(output_dir, "COVERAGE-QUESTIONS.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(questions_coverage, f, default_flow_style=False, allow_unicode=True, Dumper=yaml.SafeDumper)

    # ═══════════════════════════════════════════════════════════
    # SOURCE-LOCK.yaml
    # ═══════════════════════════════════════════════════════════
    source_lock = {
        "d2_interface": {
            "file": "d2_game_core.py",
            "commit": "d6f9e2e4d38861e91353be177c9ceacedde6d7ee",
            "sha256": "33a7d821866bb327143a51c18cf7619bea1b706c189f6713584fd459229175f1",
            "size_bytes": 75587,
        },
        "q0_sources": {
            "KNOWLEDGE-ATOMS.jsonl": {"sha256": source_hashes["atoms"], "size_bytes": source_sizes["atoms"]},
            "KNOWLEDGE-RELATIONS.jsonl": {"sha256": source_hashes["relations"], "size_bytes": source_sizes["relations"]},
            "ADVERSARIAL-QUESTION-SET.jsonl": {"sha256": source_hashes["questions"], "size_bytes": source_sizes["questions"]},
            "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml": {"sha256": source_hashes["family_map"], "size_bytes": source_sizes["family_map"]},
        },
        "policy_files": {
            "MAPPING-POLICY.yaml": {"sha256": policy_hashes["mapping_policy"]},
            "FULL-ID-QUARANTINE-MANIFEST.yaml": {"sha256": policy_hashes["quarantine_manifest"]},
            "AMBIGUITY-MANIFEST.yaml": {"sha256": policy_hashes["ambiguity_manifest"]},
            "D2-INTERFACE-SNAPSHOT.yaml": {"sha256": policy_hashes["d2_snapshot"]},
        },
        "output_files": {
            "D2-CANDIDATE-ADAPTERS.jsonl": {"sha256": adapters_jsonl_sha256, "size_bytes": file_size(adapters_path)},
            "D2-ADAPTER-PACKAGE.json": {"sha256": package_sha256, "size_bytes": file_size(package_path)},
        },
    }
    with open(os.path.join(output_dir, "SOURCE-LOCK.yaml"), "w", encoding="utf-8") as f:
        yaml.dump(source_lock, f, default_flow_style=False, allow_unicode=True, Dumper=yaml.SafeDumper)

    # ═══════════════════════════════════════════════════════════
    # GENERATION-RECEIPT.json
    # ═══════════════════════════════════════════════════════════
    receipt = OrderedDict()
    receipt["generation_receipt"] = OrderedDict([
        ("epoch", 18),
        ("schema", "25.0"),
        ("task_id", "QCLAW-PR100-STRICT-CANONICAL-IDENTITY-LOSSLESS-QUARANTINE-AND-EXECUTABLE-EVIDENCE-CLOSURE-0020-E18"),
        ("policy_version", policy_version),
        ("generator_sha256", file_sha256(__file__)),
        ("adapter_count", len(adapters)),
        ("disposition_counts", counts),
        ("adapters_sha256", adapters_jsonl_sha256),
        ("package_sha256", package_sha256),
        ("source_lock", package["source_lock"]),
        ("policy_hashes", policy_hashes),
        ("canonical_artifacts", OrderedDict([
            ("D2-CANDIDATE-ADAPTERS.jsonl", adapters_jsonl_sha256),
            ("D2-ADAPTER-PACKAGE.json", package_sha256),
        ])),
        ("completion_signal", "QCLAW_E18_PR100_STRICT_CANONICAL_IDENTITY_LOSSLESS_QUARANTINE_AND_EXECUTABLE_EVIDENCE_READY_FOR_GPT_REVIEW"),
    ])
    receipt_path = os.path.join(output_dir, "GENERATION-RECEIPT.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"Wrote receipt to {receipt_path}", file=sys.stderr)

    # ═══════════════════════════════════════════════════════════
    # Summary output
    # ═══════════════════════════════════════════════════════════
    print(f"\n=== Generation Complete (Epoch 18, Schema 25.0) ===", file=sys.stderr)
    print(f"Total adapters: {len(adapters)}", file=sys.stderr)
    print(f"Dispositions: {json.dumps(counts, indent=2, ensure_ascii=False)}", file=sys.stderr)
    print(f"Adapters SHA256: {adapters_jsonl_sha256}", file=sys.stderr)
    print(f"Package SHA256: {package_sha256}", file=sys.stderr)
    print(f"Completion signal: QCLAW_E18_PR100_STRICT_CANONICAL_IDENTITY_LOSSLESS_QUARANTINE_AND_EXECUTABLE_EVIDENCE_READY_FOR_GPT_REVIEW", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
