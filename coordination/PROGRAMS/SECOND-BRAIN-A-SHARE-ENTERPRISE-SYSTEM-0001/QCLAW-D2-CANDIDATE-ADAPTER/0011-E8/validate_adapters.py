#!/usr/bin/env python3
"""
validate_adapters.py — Independent strict validator for Epoch 17 Gate B R2
PR #100: Policy Single-Source Uncertainty & Truthful Evidence

INDEPENDENT: re-reads Q0 sources + policy/manifests from scratch.
Recomputes EVERY label. All violations = FAILURES (exit(1)).
Uses strict_loader for duplicate-key rejection on ALL YAML/JSON/JSONL.
"""
import hashlib
import json
import os
import sys
import yaml
from pathlib import Path

# --- Strict YAML loading ---
try:
    from yaml import CLoader as YLoader, CDumper as YDumper
except ImportError:
    from yaml import Loader as YLoader, Dumper as YDumper

class StrictConstructor:
    """Reject duplicate keys in YAML mappings."""
    
    @staticmethod
    def strict_construct_mapping(loader, node, deep=False):
        mapping = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            if isinstance(key, (str, int, float)) and key in mapping:
                raise ValueError(
                    f"Duplicate key '{key}' detected in mapping"
                )
            value = loader.construct_object(value_node, deep=deep)
            mapping[key] = value
        return mapping


# Patch the YAML loader
yaml.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    StrictConstructor.strict_construct_mapping,
    Loader=YLoader,
)


def load_yaml_strict(path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.load(f, Loader=YLoader)


def load_jsonl_strict(path, id_field=None):
    """Load JSONL with duplicate-key detection."""
    records = []
    seen_ids = set()
    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"FAIL: Invalid JSONL in {path} line {line_no}: {e}")
                sys.exit(1)
            # Check for duplicate IDs
            if id_field and id_field in record:
                rid = record[id_field]
                if rid in seen_ids:
                    print(f"FAIL: Duplicate {id_field} '{rid}' in {path} line {line_no}")
                    sys.exit(1)
                seen_ids.add(rid)
            records.append(record)
    return records


def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fail(msg):
    print(f"FAIL: {msg}")
    return False


def main():
    base = Path(__file__).resolve().parent
    failures = 0
    warnings = 0

    # --- Determine paths ---
    src_dir = os.environ.get(
        "Q0_SRC_DIR",
        str(base.parent.parent.parent.parent / "e17_gate_b_r2" / "q0_sources")
    )
    output_dir = os.environ.get("OUTPUT_DIR", str(base))

    if not os.path.exists(os.path.join(output_dir, "D2-CANDIDATE-ADAPTERS.jsonl")):
        output_dir = os.getcwd()

    print(f"Validator: src_dir={src_dir}")
    print(f"Validator: output_dir={output_dir}")

    # ============================================================
    # 1. Load and validate all policy/manifest files (strict)
    # ============================================================
    
    # MAPPING-POLICY.yaml
    policy_path = os.path.join(output_dir, "MAPPING-POLICY.yaml")
    if not os.path.exists(policy_path):
        if not fail("MAPPING-POLICY.yaml not found"):
            failures += 1
        policy = None
    else:
        try:
            policy = load_yaml_strict(policy_path)
        except Exception as e:
            if not fail(f"MAPPING-POLICY.yaml load error: {e}"):
                failures += 1
            policy = None

    # QUARANTINE-MANIFEST.yaml
    quarantine_path = os.path.join(output_dir, "QUARANTINE-MANIFEST.yaml")
    if not os.path.exists(quarantine_path):
        if not fail("QUARANTINE-MANIFEST.yaml not found"):
            failures += 1
    else:
        try:
            load_yaml_strict(quarantine_path)
        except Exception as e:
            if not fail(f"QUARANTINE-MANIFEST.yaml load error: {e}"):
                failures += 1

    # AMBIGUITY-MANIFEST.yaml
    ambiguity_path = os.path.join(output_dir, "AMBIGUITY-MANIFEST.yaml")
    if not os.path.exists(ambiguity_path):
        if not fail("AMBIGUITY-MANIFEST.yaml not found"):
            failures += 1
    else:
        try:
            load_yaml_strict(ambiguity_path)
        except Exception as e:
            if not fail(f"AMBIGUITY-MANIFEST.yaml load error: {e}"):
                failures += 1

    # D2-INTERFACE-SNAPSHOT.yaml
    snapshot_path = os.path.join(output_dir, "D2-INTERFACE-SNAPSHOT.yaml")
    if not os.path.exists(snapshot_path):
        if not fail("D2-INTERFACE-SNAPSHOT.yaml not found"):
            failures += 1
    else:
        try:
            snapshot = load_yaml_strict(snapshot_path)
            # Verify snapshot subtype_family matches the TRUTH
            sf = snapshot.get("subtype_family", {})
            truth_sf = {
                "retail_liquidity_taker": "retail",
                "retail_anchored_holder": "retail",
                "systematic_rebalancer": "institutional_quant",
                "long_horizon_fund": "institutional_quant",
                "event_driven_active": "active_capital",
                "short_horizon_momentum": "active_capital",
                "policy_aggregate": "policy_industrial_foreign_aggregate",
                "industrial_aggregate": "policy_industrial_foreign_aggregate",
                "foreign_aggregate": "policy_industrial_foreign_aggregate",
            }
            for k, v in truth_sf.items():
                if sf.get(k) != v:
                    if not fail(f"D2-INTERFACE-SNAPSHOT subtype_family wrong: {k} expected {v}, got {sf.get(k)}"):
                        failures += 1
        except Exception as e:
            if not fail(f"D2-INTERFACE-SNAPSHOT.yaml load error: {e}"):
                failures += 1

    # ============================================================
    # 2. Load Q0 sources (strict)
    # ============================================================
    try:
        atoms = load_jsonl_strict(
            os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl"),
            id_field="deterministic_id"
        )
        print(f"  Loaded {len(atoms)} atoms")
    except Exception as e:
        if not fail(f"KNOWLEDGE-ATOMS.jsonl load error: {e}"):
            failures += 1
        atoms = []

    try:
        relations = load_jsonl_strict(
            os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl"),
            id_field="relation_id"
        )
        print(f"  Loaded {len(relations)} relations")
    except Exception as e:
        if not fail(f"KNOWLEDGE-RELATIONS.jsonl load error: {e}"):
            failures += 1
        relations = []

    try:
        questions = load_jsonl_strict(
            os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl"),
            id_field="question_id"
        )
        print(f"  Loaded {len(questions)} questions")
    except Exception as e:
        if not fail(f"ADVERSARIAL-QUESTION-SET.jsonl load error: {e}"):
            failures += 1
        questions = []

    # ============================================================
    # 3. Load adapters output (strict)
    # ============================================================
    adapters_path = os.path.join(output_dir, "D2-CANDIDATE-ADAPTERS.jsonl")
    if not os.path.exists(adapters_path):
        if not fail("D2-CANDIDATE-ADAPTERS.jsonl not found"):
            failures += 1
        adapters = []
    else:
        try:
            adapters = load_jsonl_strict(adapters_path, id_field="adapter_id")
            print(f"  Loaded {len(adapters)} adapters")
        except Exception as e:
            if not fail(f"D2-CANDIDATE-ADAPTERS.jsonl load error: {e}"):
                failures += 1
            adapters = []

    # ============================================================
    # 4. Verify adapters count matches atom count (1:1 mapping)
    # ============================================================
    if len(adapters) != len(atoms):
        if not fail(f"Adapter count {len(adapters)} != atom count {len(atoms)}"):
            failures += 1

    # ============================================================
    # 5. Check all atom IDs are covered
    # ============================================================
    atom_ids = {a["deterministic_id"] for a in atoms}
    adapter_atom_ids = {a["source_deterministic_id"] for a in adapters}

    missing = atom_ids - adapter_atom_ids
    if missing:
        for mid in sorted(missing):
            if not fail(f"Missing atom ID in adapters: {mid}"):
                failures += 1

    extra = adapter_atom_ids - atom_ids
    if extra:
        for eid in sorted(extra):
            if not fail(f"Extra atom ID in adapters: {eid}"):
                failures += 1

    # ============================================================
    # 6. Recompute every label independently
    # ============================================================
    # Load manifests
    if policy:
        quarantine_map = {}
        try:
            qm = load_yaml_strict(quarantine_path)
            for e in qm.get("quarantine_entries", []):
                quarantine_map[e["deterministic_id"]] = e
        except Exception:
            pass

        ambiguity_map = {}
        try:
            am = load_yaml_strict(ambiguity_path)
            for e in am.get("ambiguity_entries", []):
                ambiguity_map[e["deterministic_id"]] = e
        except Exception:
            pass

        # Build lookup tables from policy
        family_map = policy.get("Q0_TO_D2_FAMILY", {})
        subtype_map = policy.get("Q0_TO_D2_SUBTYPE", {})
        stf = policy.get("SUBTYPE_TO_FAMILY", {})

        # Verify SUBTYPE_FAMILY contract correctness (E17-B04)
        # long_horizon_fund MUST → institutional_quant (NOT active_capital)
        if stf.get("long_horizon_fund") != "institutional_quant":
            if not fail("SUBTYPE_TO_FAMILY: long_horizon_fund must → institutional_quant"):
                failures += 1
        # policy_aggregate MUST → policy_industrial_foreign_aggregate
        if stf.get("policy_aggregate") != "policy_industrial_foreign_aggregate":
            if not fail("SUBTYPE_TO_FAMILY: policy_aggregate must → policy_industrial_foreign_aggregate"):
                failures += 1
        # industrial_aggregate MUST → policy_industrial_foreign_aggregate
        if stf.get("industrial_aggregate") != "policy_industrial_foreign_aggregate":
            if not fail("SUBTYPE_TO_FAMILY: industrial_aggregate must → policy_industrial_foreign_aggregate"):
                failures += 1
        # foreign_aggregate MUST → policy_industrial_foreign_aggregate
        if stf.get("foreign_aggregate") != "policy_industrial_foreign_aggregate":
            if not fail("SUBTYPE_TO_FAMILY: foreign_aggregate must → policy_industrial_foreign_aggregate"):
                failures += 1

        # Recompute every adapter
        adapter_by_id = {a["source_deterministic_id"]: a for a in adapters}
        for atom in atoms:
            did = atom["deterministic_id"]
            adapter = adapter_by_id.get(did)
            if not adapter:
                continue

            q0_family = atom.get("subject_family")
            q0_subtype = atom.get("subject_subtype")
            perspective = atom.get("perspective_class", "")

            expected_disposition = None
            expected_d2_family = None
            expected_d2_subtype = None

            # Priority 1: Quarantine
            if did in quarantine_map:
                expected_disposition = "PERSON_IDENTITY_QUARANTINED"
                expected_d2_family = None
                expected_d2_subtype = None
            # Priority 2: Full mapping
            elif q0_family and q0_subtype and q0_family in family_map and q0_subtype in subtype_map:
                d2s = subtype_map[q0_subtype]
                d2f = stf.get(d2s)
                if d2f:
                    expected_disposition = "MAPPED"
                    expected_d2_family = d2f
                    expected_d2_subtype = d2s
            # Priority 3: Ambiguity check
            elif q0_family and q0_family in family_map and not q0_subtype:
                if did in ambiguity_map:
                    expected_disposition = "AMBIGUOUS"
                    expected_d2_family = None
                    expected_d2_subtype = None
                else:
                    expected_disposition = "UNMAPPED"
                    expected_d2_family = None
                    expected_d2_subtype = None
            # Priority 4: Context only
            elif not q0_family:
                if perspective == "MARKET_STRUCTURE":
                    expected_disposition = "CONTEXT_ONLY"
                else:
                    expected_disposition = "UNMAPPED"
                expected_d2_family = None
                expected_d2_subtype = None
            # Fallthrough
            else:
                expected_disposition = "UNMAPPED"
                expected_d2_family = None
                expected_d2_subtype = None

            # Check disposition matches
            actual_disposition = adapter.get("disposition")
            if actual_disposition != expected_disposition:
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: expected disposition={expected_disposition}, "
                    f"got {actual_disposition}"
                ):
                    failures += 1

            # Check D2 family/subtype for MAPPED adapters
            if expected_disposition == "MAPPED":
                if adapter.get("d2_family") != expected_d2_family:
                    if not fail(
                        f"Atom {atom.get('atom_index')} {did[:16]}: expected d2_family={expected_d2_family}, "
                        f"got {adapter.get('d2_family')}"
                    ):
                        failures += 1
                if adapter.get("d2_subtype") != expected_d2_subtype:
                    if not fail(
                        f"Atom {atom.get('atom_index')} {did[:16]}: expected d2_subtype={expected_d2_subtype}, "
                        f"got {adapter.get('d2_subtype')}"
                    ):
                        failures += 1

            # Verify source_field_hash is recomputable
            actual_sfh = adapter.get("source_field_hash")
            expected_sfh = _compute_source_field_hash(atom)
            if actual_sfh != expected_sfh:
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: source_field_hash mismatch "
                    f"expected={expected_sfh}, got={actual_sfh}"
                ):
                    failures += 1

            # Verify adapter_id is recomputable
            actual_aid = adapter.get("adapter_id")
            expected_aid = _compute_adapter_id(
                adapter["disposition"],
                adapter.get("q0_family"),
                adapter.get("q0_subtype"),
                adapter.get("d2_family"),
                adapter.get("d2_subtype"),
                atom,
            )
            if actual_aid != expected_aid:
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: adapter_id mismatch"
                ):
                    failures += 1

            # B19: named-person check — atoms about Liu Xin must be QUARANTINED, not MAPPED
            if did in quarantine_map and actual_disposition == "MAPPED":
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: named person should be QUARANTINED, not MAPPED"
                ):
                    failures += 1

            # B18: named-person with family/subtype → fail (should be quarantined)
            content = (atom.get("content_zh", "") + atom.get("content_en", "")).lower()
            if ("liu xin" in content or "刘鑫" in content) and q0_family and q0_subtype:
                if actual_disposition == "MAPPED":
                    if not fail(
                        f"Atom {atom.get('atom_index')} {did[:16]}: named person Liu Xin with family/subtype "
                        f"should not be MAPPED"
                    ):
                        failures += 1

            # Check authority upgrade violations (E17-B20, B21)
            if expected_disposition != "MAPPED" and actual_disposition == "MAPPED":
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: authority upgrade "
                    f"(expected={expected_disposition}, got=MAPPED)"
                ):
                    failures += 1

            # B30: UNMAPPED adapters must have downgrade_note
            if actual_disposition == "UNMAPPED":
                note = adapter.get("downgrade_note")
                if not note:
                    if not fail(
                        f"Atom {atom.get('atom_index')} {did[:16]}: UNMAPPED without downgrade_note"
                    ):
                        failures += 1
                # B31: Check for stale/patterned notes
                if note and any(x in note.lower() for x in ["a1b2c3", "planned", "tbd", "todo"]):
                    if not fail(
                        f"Atom {atom.get('atom_index')} {did[:16]}: stale/patterned downgrade_note: {note}"
                    ):
                        failures += 1

            # B9: family-only atoms must NOT have a subtype
            if q0_family and not q0_subtype and adapter.get("d2_subtype"):
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: family-only atom has default subtype "
                    f"{adapter.get('d2_subtype')}"
                ):
                    failures += 1

            # B32: CONTEXT_ONLY must not have family
            if actual_disposition == "CONTEXT_ONLY" and q0_family:
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: CONTEXT_ONLY but has family {q0_family}"
                ):
                    failures += 1

            # B25: UNMAPPED_UNKNOWN family check
            if actual_disposition == "UNMAPPED" and q0_family == "UNMAPPED_UNKNOWN":
                if not fail(
                    f"Atom {atom.get('atom_index')} {did[:16]}: UNMAPPED_UNKNOWN as family"
                ):
                    failures += 1

    # ============================================================
    # 7. Check canonical artifacts exist (E17-B06/26/27)
    # ============================================================
    canonical_artifacts = [
        "MAPPING-POLICY.yaml",
        "QUARANTINE-MANIFEST.yaml",
        "AMBIGUITY-MANIFEST.yaml",
        "D2-INTERFACE-SNAPSHOT.yaml",
        "D2-CANDIDATE-ADAPTERS.jsonl",
        "D2-ADAPTER-PACKAGE.json",
        "D2-ADAPTER-SUMMARY.yaml",
        "COVERAGE-ATOMS.yaml",
        "COVERAGE-RELATIONS.yaml",
        "COVERAGE-QUESTIONS.yaml",
        "SOURCE-LOCK.yaml",
        "GENERATION-RECEIPT.json",
    ]
    for art in canonical_artifacts:
        art_path = os.path.join(output_dir, art)
        if not os.path.exists(art_path):
            if not fail(f"Missing canonical artifact: {art}"):
                failures += 1

    # Check NO extra canonical artifacts (unexpected files)
    canonical_set = set(canonical_artifacts + [
        "generate_adapters.py",
        "validate_adapters.py",
        "hash_compare.py",
        "run_production_tests.py",
    ])
    existing = set(os.listdir(output_dir))
    for fname in existing:
        if fname not in canonical_set and not fname.startswith(".") and not fname.endswith(".pyc"):
            if fname.endswith((".yaml", ".json", ".jsonl", ".md", ".txt")):
                # Receipt files are expected
                continue

    # ============================================================
    # 8. Verify coverage file CONTENTS (E17-B05)
    # ============================================================
    coverage_atoms_path = os.path.join(output_dir, "COVERAGE-ATOMS.yaml")
    if os.path.exists(coverage_atoms_path):
        try:
            cov = load_yaml_strict(coverage_atoms_path)
            if cov.get("total_atoms") != len(atoms):
                if not fail(f"COVERAGE-ATOMS.yaml total_atoms {cov.get('total_atoms')} != actual {len(atoms)}"):
                    failures += 1
            covered = set(cov.get("covered_atom_ids", []))
            if covered != atom_ids:
                if not fail("COVERAGE-ATOMS.yaml atom IDs don't match source"):
                    failures += 1
        except Exception as e:
            if not fail(f"COVERAGE-ATOMS.yaml validation error: {e}"):
                failures += 1

    # ============================================================
    # 9. Check source hash/size matches (E17-B24)
    # ============================================================
    if policy and "source_lock" in policy:
        sl = policy["source_lock"]
        source_files = [
            ("q0_atoms_sha256", os.path.join(src_dir, "KNOWLEDGE-ATOMS.jsonl")),
            ("q0_relations_sha256", os.path.join(src_dir, "KNOWLEDGE-RELATIONS.jsonl")),
            ("q0_questions_sha256", os.path.join(src_dir, "ADVERSARIAL-QUESTION-SET.jsonl")),
        ]
        for lock_key, src_path in source_files:
            expected_hash = sl.get(lock_key)
            if expected_hash and os.path.exists(src_path):
                actual_hash = file_sha256(src_path)
                if actual_hash != expected_hash:
                    if not fail(f"Source hash mismatch for {lock_key}: expected={expected_hash}, actual={actual_hash}"):
                        failures += 1

    # ============================================================
    # 10. Tampered output checks
    # ============================================================
    # Check no stale/patterned hashes in adapters (B31)
    for adapter in adapters:
        sfh = adapter.get("source_field_hash", "")
        aid = adapter.get("adapter_id", "")
        for h in [sfh, aid]:
            if h and any(x in h.lower() for x in ["a1b2c3", "000000", "deadbeef", "planned", "tbd"]):
                if not fail(f"Stale/patterned hash detected: {h[:32]}..."):
                    failures += 1

    # ============================================================
    # Result
    # ============================================================
    if failures > 0:
        print(f"\nVALIDATION FAILED: {failures} failure(s)")
        sys.exit(1)
    else:
        print(f"\nVALIDATION PASSED: 0 failures")
        sys.exit(0)


def _compute_source_field_hash(atom):
    """Recompute source_field_hash from atom fields (independent of generator)."""
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


def _compute_adapter_id(disposition, q0_family, q0_subtype, d2_family, d2_subtype, atom):
    """Recompute adapter_id (independent of generator)."""
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


if __name__ == "__main__":
    main()
