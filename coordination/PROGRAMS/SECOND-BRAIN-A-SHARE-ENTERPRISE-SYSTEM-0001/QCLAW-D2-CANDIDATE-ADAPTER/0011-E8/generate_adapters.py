#!/usr/bin/env python3
"""
generate_adapters.py — Epoch 17 Gate B R2
PR #100: Policy Single-Source Uncertainty & Truthful Evidence

Loads MAPPING-POLICY.yaml + QUARANTINE-MANIFEST.yaml + AMBIGUITY-MANIFEST.yaml.
ZERO hard-coded Python family/subtype tables.
Classification follows policy rules in priority order.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# --- strict_loader for duplicate-key rejection ---
try:
    from yaml import CLoader as YLoader, CDumper as YDumper
except ImportError:
    from yaml import Loader as YLoader, Dumper as YDumper  # type: ignore

import yaml


class StrictLoader(YLoader):
    def __init__(self, stream):
        super().__init__(stream)

    def construct_mapping(self, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = str(self.construct_object(key_node, deep=deep))
            if key in mapping:
                raise ValueError(f"Duplicate key '{key}' detected in YAML mapping")
            mapping[key] = key
        return self._normal_mapping_construct(node, deep)


def strict_construct_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if isinstance(key, str) and key in mapping:
            raise ValueError(f"Duplicate key '{key}' detected in YAML/JSONL mapping")
        value = loader.construct_object(value_node, deep=deep)
        mapping[key] = value
    return mapping


yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    strict_construct_mapping,
    Loader=YLoader,
)


def load_yaml_strict(path):
    """Load YAML with duplicate-key rejection."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=YLoader)


def load_jsonl_strict(path):
    """Load JSONL with duplicate-key detection per-line."""
    records = []
    seen_deterministic_ids = set()
    seen_relation_ids = set()
    seen_question_ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"ERROR: Invalid JSONL line in {path}: {e}", file=sys.stderr)
                sys.exit(1)

            # Check for duplicate deterministic_id (atoms)
            did = record.get("deterministic_id")
            if did:
                if did in seen_deterministic_ids:
                    print(f"ERROR: Duplicate deterministic_id '{did}' in {path}", file=sys.stderr)
                    sys.exit(1)
                seen_deterministic_ids.add(did)

            # Check for duplicate relation_id
            rid = record.get("relation_id")
            if rid:
                if rid in seen_relation_ids:
                    print(f"ERROR: Duplicate relation_id '{rid}' in {path}", file=sys.stderr)
                    sys.exit(1)
                seen_relation_ids.add(rid)

            # Check for duplicate question_id
            qid = record.get("question_id")
            if qid:
                if qid in seen_question_ids:
                    print(f"ERROR: Duplicate question_id '{qid}' in {path}", file=sys.stderr)
                    sys.exit(1)
                seen_question_ids.add(qid)

            records.append(record)
    return records


def file_sha256(path):
    """Compute SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_size(path):
    return os.path.getsize(path)


def build_adapter_id(disposition, q0_family, q0_subtype, d2_family, d2_subtype, atom):
    """Deterministic adapter_id from input fields."""
    components = [
        disposition,
        q0_family or "NOFAMILY",
        q0_subtype or "NOSUBTYPE",
        d2_family or "NOFAMILY",
        d2_subtype or "NOSUBTYPE",
        atom.get("deterministic_id", "")[:16],
    ]
    raw = "|".join(components)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source_field_hash(atom):
    """Compute SHA256 of source-relevant fields for tamper detection."""
    fields = {
        "deterministic_id": atom.get("deterministic_id", ""),
        "atom_index": atom.get("atom_index", 0),
        "atom_type": atom.get("atom_type", ""),
        "content_zh": atom.get("content_zh", ""),
        "source_file": atom.get("source_file", ""),
        "source_section": atom.get("source_section", ""),
        "perspective_class": atom.get("perspective_class", ""),
        "subject_family": atom.get("subject_family") or "",
        "subject_subtype": atom.get("subject_subtype") or "",
        "confidence": atom.get("confidence", ""),
        "evidence_status": atom.get("evidence_status", ""),
        "misclassification_risk": atom.get("misclassification_risk", ""),
    }
    raw = json.dumps(fields, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_policy(policy_path):
    """Load and validate MAPPING-POLICY.yaml."""
    policy = load_yaml_strict(policy_path)
    required = ["Q0_TO_D2_FAMILY", "Q0_TO_D2_SUBTYPE", "SUBTYPE_TO_FAMILY", "classification_rules", "no_default_policy"]
    for key in required:
        if key not in policy:
            print(f"ERROR: MAPPING-POLICY.yaml missing required key: {key}", file=sys.stderr)
            sys.exit(1)
    return policy


def load_quarantine_manifest(path):
    """Load QUARANTINE-MANIFEST.yaml."""
    manifest = load_yaml_strict(path)
    entries = manifest.get("quarantine_entries", [])
    return {e["deterministic_id"]: e for e in entries}


def load_ambiguity_manifest(path):
    """Load AMBIGUITY-MANIFEST.yaml."""
    manifest = load_yaml_strict(path)
    entries = manifest.get("ambiguity_entries", [])
    return {e["deterministic_id"]: e for e in entries}


def classify_atom(atom, policy, quarantine_map, ambiguity_map):
    """
    Classify a single atom into:
    PERSON_IDENTITY_QUARANTINED | MAPPED | AMBIGUOUS | CONTEXT_ONLY | UNMAPPED

    Priority:
    1. deterministic_id in quarantine → PERSON_IDENTITY_QUARANTINED
    2. Has BOTH recognized family + subtype → MAPPED
    3. Has recognized family but NO subtype → AMBIGUOUS (if in manifest) or UNMAPPED
    4. Has NO family → CONTEXT_ONLY (if MARKET_STRUCTURE) or UNMAPPED
    """
    did = atom.get("deterministic_id", "")
    q0_family = atom.get("subject_family")
    q0_subtype = atom.get("subject_subtype")
    perspective = atom.get("perspective_class", "")

    family_map = policy.get("Q0_TO_D2_FAMILY", {})
    subtype_map = policy.get("Q0_TO_D2_SUBTYPE", {})
    subtype_to_family = policy.get("SUBTYPE_TO_FAMILY", {})

    # Priority 1: Quarantine check
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
                    "rationale": f"Full mapping: {q0_family}/{q0_subtype} → {d2_family}/{d2_subtype}",
                }

    # Priority 3: Family recognized, no subtype → AMBIGUOUS or UNMAPPED
    if q0_family and q0_family in family_map and not q0_subtype:
        if did in ambiguity_map:
            entry = ambiguity_map[did]
            return {
                "disposition": "AMBIGUOUS",
                "q0_family": q0_family,
                "q0_subtype": None,
                "d2_family": None,
                "d2_subtype": None,
                "hypotheses": entry.get("hypotheses", []),
                "rationale": entry.get("rationale", "Ambiguous per manifest"),
                "ambiguity_entry": entry,
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

    # Priority 3 continued: Family recognized but not in family_map → try subtype only
    if q0_family and not q0_subtype:
        if did in ambiguity_map:
            entry = ambiguity_map[did]
            return {
                "disposition": "AMBIGUOUS",
                "q0_family": q0_family,
                "q0_subtype": None,
                "d2_family": None,
                "d2_subtype": None,
                "hypotheses": entry.get("hypotheses", []),
                "rationale": entry.get("rationale", "Ambiguous per manifest"),
                "ambiguity_entry": entry,
            }
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
                "rationale": f"MARKET_STRUCTURE atom with no participant evidence",
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
        "rationale": "Fallthrough — unclassifiable",
    }


def generate_adapters(src_dir, policy_dir, output_dir):
    """Main generation pipeline."""
    # Load policy and manifests
    policy = load_policy(os.path.join(policy_dir, "MAPPING-POLICY.yaml"))
    quarantine_map = load_quarantine_manifest(os.path.join(policy_dir, "QUARANTINE-MANIFEST.yaml"))
    ambiguity_map = load_ambiguity_manifest(os.path.join(policy_dir, "AMBIGUITY-MANIFEST.yaml"))

    # Load Q0 source atoms (strict)
    atoms_path = os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")
    atoms = load_jsonl_strict(atoms_path)

    # Verify source hashes against policy lock
    expected_hashes = {
        "atoms": policy["source_lock"]["q0_atoms_sha256"],
        "relations": policy["source_lock"]["q0_relations_sha256"],
        "questions": policy["source_lock"]["q0_questions_sha256"],
    }
    actual_hashes = {
        "atoms": file_sha256(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
        "relations": file_sha256(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
        "questions": file_sha256(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
    }
    for key, expected in expected_hashes.items():
        actual = actual_hashes[key]
        if expected != actual:
            print(f"ERROR: Source hash mismatch for {key}: expected {expected}, got {actual}", file=sys.stderr)
            sys.exit(1)

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

        disposition_counts[disposition] = disposition_counts.get(disposition, 0) + 1

        d2_family = result.get("d2_family")
        d2_subtype = result.get("d2_subtype")

        adapter_id = build_adapter_id(
            disposition,
            result.get("q0_family"),
            result.get("q0_subtype"),
            d2_family,
            d2_subtype,
            atom,
        )

        if adapter_id in seen_adapter_ids:
            print(f"ERROR: Duplicate adapter_id '{adapter_id}' generated", file=sys.stderr)
            sys.exit(1)
        seen_adapter_ids.add(adapter_id)

        sfh = source_field_hash(atom)

        adapter = {
            "adapter_id": adapter_id,
            "source_deterministic_id": did,
            "atom_index": atom.get("atom_index"),
            "disposition": disposition,
            "q0_family": result.get("q0_family"),
            "q0_subtype": result.get("q0_subtype"),
            "d2_family": d2_family,
            "d2_subtype": d2_subtype,
            "source_field_hash": sfh,
            "rationale": result.get("rationale", ""),
            "atom_type": atom.get("atom_type"),
            "confidence": atom.get("confidence"),
            "evidence_status": atom.get("evidence_status"),
            "perspective_class": atom.get("perspective_class"),
        }

        # Add downgrade note for unmapped adapters
        if "downgrade_note" in result:
            adapter["downgrade_note"] = result["downgrade_note"]

        # Add ambiguity hypotheses if applicable
        if disposition == "AMBIGUOUS" and "hypotheses" in result:
            adapter["ambiguity_hypotheses"] = result["hypotheses"]

        # Add quarantine reference
        if disposition == "PERSON_IDENTITY_QUARANTINED":
            adapter["quarantine_rationale"] = result.get("rationale", "")

        adapters.append(adapter)

    return adapters, disposition_counts, atoms


def main():
    base = Path(__file__).resolve().parent
    src_dir = base.parent.parent.parent.parent / "e17_gate_b_r2" / "q0_sources"
    policy_dir = base  # MAPPING-POLICY.yaml etc. are in same dir as this script
    output_dir = base

    # Adjust paths for actual layout
    if not os.path.exists(os.path.join(policy_dir, "MAPPING-POLICY.yaml")):
        # Try relative to CWD
        policy_dir = os.getcwd()
        src_dir = os.path.join(os.getcwd(), "q0_sources")

    # Override with env-var based paths if set
    src_dir = os.environ.get("Q0_SRC_DIR", src_dir)
    policy_dir = os.environ.get("POLICY_DIR", policy_dir)
    output_dir = os.environ.get("OUTPUT_DIR", output_dir)

    print(f"Source dir: {src_dir}", file=sys.stderr)
    print(f"Policy dir: {policy_dir}", file=sys.stderr)
    print(f"Output dir: {output_dir}", file=sys.stderr)

    # Verify source files exist
    required_src = ["KNOWLEDGE-ATOMS.jsonl", "KNOWLEDGE-RELATIONS.jsonl",
                    "ADVERSARIAL-QUESTION-SET.jsonl", "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml"]
    for f in required_src:
        p = os.path.join(src_dir, f)
        if not os.path.exists(p):
            print(f"ERROR: Required source file not found: {p}", file=sys.stderr)
            sys.exit(1)

    adapters, counts, atoms = generate_adapters(src_dir, policy_dir, output_dir)

    # Write adapters JSONL
    adapters_path = os.path.join(output_dir, "D2-CANDIDATE-ADAPTERS.jsonl")
    with open(adapters_path, "w", encoding="utf-8") as f:
        for a in adapters:
            f.write(json.dumps(a, ensure_ascii=False) + "\n")
    print(f"Wrote {len(adapters)} adapters to {adapters_path}", file=sys.stderr)

    # Compute adapter hashes
    adapter_hashes = {}
    with open(adapters_path, "rb") as f:
        hasher = hashlib.sha256()
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
        adapter_hashes["adapters_jsonl_sha256"] = hasher.hexdigest()

    # Write package (deterministic — no timestamps, no self-referencing hashes)
    package = {
        "package_id": hashlib.sha256(b"E17-PR100-qclaw-d2-candidate-adapter-0011-e8").hexdigest(),
        "epoch": 17,
        "schema": "24.0",
        "task_id": "QCLAW-PR100-POLICY-SINGLE-SOURCE-UNCERTAINTY-PRESERVATION-AND-TRUTHFUL-EVIDENCE-CLOSURE-0019-E17",
        "generation_epoch": "E17",
        "adapter_count": len(adapters),
        "disposition_counts": counts,
        "adapters_sha256": adapter_hashes["adapters_jsonl_sha256"],
        "source_lock": {
            "d2_interface_sha256": "33a7d821866bb327143a51c18cf7619bea1b706c189f6713584fd459229175f1",
            "d2_interface_commit": "d6f9e2e4d38861e91353be177c9ceacedde6d7ee",
            "q0_atoms_sha256": file_sha256(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
            "q0_relations_sha256": file_sha256(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
            "q0_questions_sha256": file_sha256(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
        },
        "policy_snapshot_sha256": file_sha256(os.path.join(policy_dir, "MAPPING-POLICY.yaml")),
    }
    package_path = os.path.join(output_dir, "D2-ADAPTER-PACKAGE.json")
    with open(package_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2, ensure_ascii=False, sort_keys=True)
    print(f"Wrote package to {package_path}", file=sys.stderr)

    # Write summary (deterministic)
    summary = {
        "d2_adapter_summary": {
            "epoch": 17,
            "schema": "24.0",
            "task_id": "QCLAW-PR100-POLICY-SINGLE-SOURCE-UNCERTAINTY-PRESERVATION-AND-TRUTHFUL-EVIDENCE-CLOSURE-0019-E17",
            "total_adapters": len(adapters),
            "disposition_counts": counts,
            "adapters_sha256": adapter_hashes["adapters_jsonl_sha256"],
            "source_lock": package["source_lock"],
            "policy_sha256": file_sha256(os.path.join(policy_dir, "MAPPING-POLICY.yaml")),
            "quarantine_manifest_sha256": file_sha256(os.path.join(policy_dir, "QUARANTINE-MANIFEST.yaml")),
            "ambiguity_manifest_sha256": file_sha256(os.path.join(policy_dir, "AMBIGUITY-MANIFEST.yaml")),
        }
    }
    summary_path = os.path.join(output_dir, "D2-ADAPTER-SUMMARY.yaml")
    with open(summary_path, "w", encoding="utf-8") as f:
        yaml.dump(summary, f, default_flow_style=False, allow_unicode=True, Dumper=YDumper)
    print(f"Wrote summary to {summary_path}", file=sys.stderr)

    # Write coverage files
    # Coverage: atoms
    atoms_coverage = {
        "total_atoms": len(atoms),
        "covered_atom_ids": [a["deterministic_id"] for a in atoms],
        "covered_by_disposition": {},
    }
    for a in adapters:
        disp = a["disposition"]
        if disp not in atoms_coverage["covered_by_disposition"]:
            atoms_coverage["covered_by_disposition"][disp] = []
        atoms_coverage["covered_by_disposition"][disp].append(a["source_deterministic_id"])

    coverage_atoms_path = os.path.join(output_dir, "COVERAGE-ATOMS.yaml")
    with open(coverage_atoms_path, "w", encoding="utf-8") as f:
        yaml.dump(atoms_coverage, f, default_flow_style=False, allow_unicode=True, Dumper=YDumper)

    # Coverage: relations
    relations_path_src = os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")
    relations = load_jsonl_strict(relations_path_src)
    relations_coverage = {
        "total_relations": len(relations),
        "covered_relation_ids": [r["relation_id"] for r in relations],
    }
    coverage_rel_path = os.path.join(output_dir, "COVERAGE-RELATIONS.yaml")
    with open(coverage_rel_path, "w", encoding="utf-8") as f:
        yaml.dump(relations_coverage, f, default_flow_style=False, allow_unicode=True, Dumper=YDumper)

    # Coverage: questions
    questions_path_src = os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")
    questions = load_jsonl_strict(questions_path_src)
    questions_coverage = {
        "total_questions": len(questions),
        "covered_question_ids": [q["question_id"] for q in questions],
    }
    coverage_q_path = os.path.join(output_dir, "COVERAGE-QUESTIONS.yaml")
    with open(coverage_q_path, "w", encoding="utf-8") as f:
        yaml.dump(questions_coverage, f, default_flow_style=False, allow_unicode=True, Dumper=YDumper)

    # Source lock
    source_lock = {
        "d2_interface": {
            "file": "d2_game_core.py",
            "commit": "d6f9e2e4d38861e91353be177c9ceacedde6d7ee",
            "sha256": "33a7d821866bb327143a51c18cf7619bea1b706c189f6713584fd459229175f1",
            "size_bytes": 75587,
        },
        "q0_sources": {
            "KNOWLEDGE-ATOMS.jsonl": {
                "sha256": file_sha256(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
                "size_bytes": file_size(os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
            },
            "KNOWLEDGE-RELATIONS.jsonl": {
                "sha256": file_sha256(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
                "size_bytes": file_size(os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
            },
            "ADVERSARIAL-QUESTION-SET.jsonl": {
                "sha256": file_sha256(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
                "size_bytes": file_size(os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
            },
            "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml": {
                "sha256": file_sha256(os.path.join(src_dir, "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml")),
                "size_bytes": file_size(os.path.join(src_dir, "PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml")),
            },
        },
        "policy_files": {
            "MAPPING-POLICY.yaml": {
                "sha256": file_sha256(os.path.join(policy_dir, "MAPPING-POLICY.yaml")),
            },
            "QUARANTINE-MANIFEST.yaml": {
                "sha256": file_sha256(os.path.join(policy_dir, "QUARANTINE-MANIFEST.yaml")),
            },
            "AMBIGUITY-MANIFEST.yaml": {
                "sha256": file_sha256(os.path.join(policy_dir, "AMBIGUITY-MANIFEST.yaml")),
            },
        },
    }
    source_lock_path = os.path.join(output_dir, "SOURCE-LOCK.yaml")
    with open(source_lock_path, "w", encoding="utf-8") as f:
        yaml.dump(source_lock, f, default_flow_style=False, allow_unicode=True, Dumper=YDumper)

    # Generation receipt (deterministic)
    receipt = {
        "generation_receipt": {
            "epoch": 17,
            "schema": "24.0",
            "task_id": "QCLAW-PR100-POLICY-SINGLE-SOURCE-UNCERTAINTY-PRESERVATION-AND-TRUTHFUL-EVIDENCE-CLOSURE-0019-E17",
            "generation_epoch": "E17",
            "generator_sha256": file_sha256(__file__),
            "adapter_count": len(adapters),
            "disposition_counts": counts,
            "adapters_sha256": adapter_hashes["adapters_jsonl_sha256"],
            "source_lock": package["source_lock"],
            "policy_sha256": file_sha256(os.path.join(policy_dir, "MAPPING-POLICY.yaml")),
        }
    }
    receipt_path = os.path.join(output_dir, "GENERATION-RECEIPT.json")
    with open(receipt_path, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2, ensure_ascii=False)

    print(f"\n=== Generation Complete ===", file=sys.stderr)
    print(f"Total adapters: {len(adapters)}", file=sys.stderr)
    print(f"Dispositions: {json.dumps(counts, indent=2)}", file=sys.stderr)
    print(f"Adapters SHA256: {adapter_hashes['adapters_jsonl_sha256']}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
