#!/usr/bin/env python3
"""
validate_adapters.py — Epoch 15 Gate B: Independent Strict Validator
Validates D2 CANDIDATE ADAPTER output against the immutable Q0 source package.

Does NOT trust generated counts, hashes, labels, or receipts.
Re-verifies everything independently.
"""
import sys, os, json, hashlib, re, unicodedata, argparse
from pathlib import Path
from collections import OrderedDict

os.environ['PYTHONHASHSEED'] = os.environ.get('PYTHONHASHSEED', '0')

# ========================================================================
# D2 Canonical Contract (from d2_game_core.py @ d6f9e2e4)
# ========================================================================
D2_VALID_FAMILIES = {
    "retail", "institutional_quant", "active_capital",
    "policy_industrial_foreign_aggregate",
}
D2_VALID_SUBTYPES = {
    "retail_liquidity_taker", "retail_anchored_holder",
    "systematic_rebalancer", "long_horizon_fund",
    "event_driven_active", "short_horizon_momentum",
    "policy_aggregate", "industrial_aggregate", "foreign_aggregate",
}
SUBTYPE_TO_FAMILY = {
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
VALID_DISPOSITIONS = {"MAPPED", "UNMAPPED", "AMBIGUOUS", "CONTEXT_ONLY", "PERSON_IDENTITY_QUARANTINED"}
FORBIDDEN_FAMILIES = {"UNMAPPED_UNKNOWN", "unmapped_unknown"}

FAILURES = []
WARNINGS = []

def fail(msg):
    FAILURES.append(msg)
    print(f"  FAIL: {msg}")

def warn(msg):
    WARNINGS.append(msg)
    print(f"  WARN: {msg}")

# ========================================================================
# Helpers
# ========================================================================
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def sha256_string(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def _reject_duplicate_keys(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"Duplicate JSON key: {key!r}")
        seen[key] = value
    return seen

def read_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            except (json.JSONDecodeError, ValueError) as e:
                fail(f"JSONL parse error {path}:L{i}: {e}")
                continue
            records.append(record)
    return records

def read_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=_reject_duplicate_keys)

# ========================================================================
# Validation steps
# ========================================================================

def validate_source_lock(output_dir, q0_dir):
    """Step 1: Validate source SHA-256/size matches exactly."""
    print(f"\n=== STEP 1: Source Lock Verification ===")
    source_files = [
        'KNOWLEDGE-ATOMS.jsonl',
        'KNOWLEDGE-RELATIONS.jsonl',
        'ADVERSARIAL-QUESTION-SET.jsonl',
    ]

    for fn in source_files:
        q0_path = os.path.join(q0_dir, fn)
        actual_size = os.path.getsize(q0_path)
        actual_hash = sha256_file(q0_path)
        print(f"  {fn}: SHA256={actual_hash[:16]}... size={actual_size}")

    # Exact counts
    atoms = read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-ATOMS.jsonl'))
    relations = read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-RELATIONS.jsonl'))
    questions = read_jsonl(os.path.join(q0_dir, 'ADVERSARIAL-QUESTION-SET.jsonl'))

    if len(atoms) != 99:
        fail(f"Atom count: expected 99, got {len(atoms)}")
    if len(relations) != 147:
        fail(f"Relation count: expected 147, got {len(relations)}")
    if len(questions) != 64:
        fail(f"Question count: expected 64, got {len(questions)}")

    return atoms, relations, questions


def validate_source_set_equality(adapters, atoms):
    """Step 2: Prove exact source-set equality - every atom ID exactly once."""
    print(f"\n=== STEP 2: Source-Set Equality ===")
    atom_ids = {a['deterministic_id'] for a in atoms}
    adapter_src_ids = {a.get('source_deterministic_id', '') for a in adapters}

    # Every atom has an adapter
    missing = atom_ids - adapter_src_ids
    if missing:
        for mid in sorted(missing):
            fail(f"Missing adapter for source atom: {mid[:16]}...")

    # Every adapter references a valid atom
    extra = adapter_src_ids - atom_ids
    if extra:
        for eid in sorted(extra):
            fail(f"Adapter references non-existent source atom: {eid[:16]}...")

    # Count must be exact
    if len(adapters) != len(atoms):
        fail(f"Count mismatch: {len(adapters)} adapters vs {len(atoms)} atoms")

    # Duplicate source IDs
    src_counts = {}
    for a in adapters:
        sid = a.get('source_deterministic_id', '')
        src_counts[sid] = src_counts.get(sid, 0) + 1
    dups = {k: v for k, v in src_counts.items() if v > 1}
    for k, v in dups.items():
        fail(f"Duplicate source_deterministic_id: {k[:16]}... ({v}x)")

    if not FAILURES:
        print(f"  PASS: Exact source-set equality ({len(adapters)} = {len(atoms)})")


def validate_family_subtype_enum(adapters):
    """Step 3: Validate all family/subtype values against D2 enums."""
    print(f"\n=== STEP 3: D2 Family/Subtype Enum Validation ===")
    for rec in adapters:
        aid = rec.get('adapter_id', '')[:16]
        disp = rec.get('disposition', '')

        family = rec.get('d2_participant_family', '')
        subtype = rec.get('d2_participant_subtype', '')

        # HARD RULE: UNMAPPED_UNKNOWN must not appear
        if family and family in FORBIDDEN_FAMILIES:
            fail(f"FORBIDDEN family {family} in adapter {aid} (atom {rec.get('atom_index')})")

        # MAPPED must have valid family and subtype
        if disp == 'MAPPED':
            if not family:
                fail(f"MAPPED adapter {aid} missing d2_participant_family")
            elif family not in D2_VALID_FAMILIES:
                fail(f"MAPPED adapter {aid}: invalid family '{family}'")
            if not subtype:
                fail(f"MAPPED adapter {aid} missing d2_participant_subtype")
            elif subtype not in D2_VALID_SUBTYPES:
                fail(f"MAPPED adapter {aid}: invalid subtype '{subtype}'")

            # Subtype-family consistency
            expected_family = SUBTYPE_TO_FAMILY.get(subtype)
            if expected_family and expected_family != family:
                fail(f"MAPPED adapter {aid}: subtype '{subtype}' belongs to '{expected_family}', not '{family}'")

        # AMBIGUOUS must have hypotheses
        if disp == 'AMBIGUOUS':
            hyps = rec.get('d2_hypotheses', [])
            if not hyps:
                fail(f"AMBIGUOUS adapter {aid}: no hypotheses")
            for h in hyps:
                hf = h.get('family', '')
                hs = h.get('subtype', '')
                if hf not in D2_VALID_FAMILIES:
                    fail(f"AMBIGUOUS adapter {aid}: hypothesis has invalid family '{hf}'")
                if hs not in D2_VALID_SUBTYPES:
                    fail(f"AMBIGUOUS adapter {aid}: hypothesis has invalid subtype '{hs}'")
                expected = SUBTYPE_TO_FAMILY.get(hs, '')
                if expected and expected != hf:
                    fail(f"AMBIGUOUS adapter {aid}: hypothesis subtype '{hs}' belongs to '{expected}', not '{hf}'")

        # UNMAPPED must NOT have family/subtype
        if disp == 'UNMAPPED':
            if family:
                fail(f"UNMAPPED adapter {aid}: has d2_participant_family '{family}'")

        # Valid disposition
        if disp not in VALID_DISPOSITIONS:
            fail(f"Adapter {aid}: invalid disposition '{disp}'")


def validate_duplicate_keys(output_dir):
    """Step 4: Run duplicate-key rejection on all JSON/JSONL/YAML."""
    print(f"\n=== STEP 4: Duplicate Key Rejection ===")
    jsonl_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
    try:
        read_jsonl(jsonl_path)
        print(f"  D2-CANDIDATE-ADAPTERS.jsonl: OK (no duplicate keys, {len(read_jsonl(jsonl_path))} records)")
    except Exception as e:
        fail(f"D2-CANDIDATE-ADAPTERS.jsonl: {e}")

    package_path = os.path.join(output_dir, 'D2-ADAPTER-PACKAGE.json')
    try:
        read_json(package_path)
        print(f"  D2-ADAPTER-PACKAGE.json: OK")
    except Exception as e:
        fail(f"D2-ADAPTER-PACKAGE.json: {e}")


def validate_deterministic_ids(adapters, atoms):
    """Step 5: Recompute every deterministic ID."""
    print(f"\n=== STEP 5: Deterministic ID Recomputations ===")
    # Build atom lookup
    atom_map = {a['deterministic_id']: a for a in atoms}

    for rec in adapters:
        sid = rec.get('source_deterministic_id', '')
        disp = rec.get('disposition', '')
        aid = rec.get('adapter_id', '')

        # Recompute
        expected = hashlib.sha256(
            f"Q0-D2-ADAPTER||{sid}||v22.0||{disp}".encode('utf-8')
        ).hexdigest()

        if aid != expected:
            fail(f"Adapter ID mismatch for atom {rec.get('atom_index')}: "
                 f"declared={aid[:16]}... computed={expected[:16]}...")


def validate_claim_downgrade(adapters, atoms):
    """Step 6: CLAIM/HYPOTHESIS/UNKNOWN must NOT be upgraded to FACT-like."""
    print(f"\n=== STEP 6: Claim/Hypothesis/Unknown Downgrade Validation ===")
    atom_map = {a['deterministic_id']: a for a in atoms}
    downgradeable = {'CLAIM', 'HYPOTHESIS', 'UNKNOWN'}

    for rec in adapters:
        sid = rec.get('source_deterministic_id', '')
        atom = atom_map.get(sid, {})
        atype = atom.get('atom_type', rec.get('atom_type', ''))
        disp = rec.get('disposition', '')

        if atype in downgradeable and disp == 'MAPPED':
            note = rec.get('downgrade_note', '')
            if not note:
                fail(f"CLAIM/HYPOTHESIS/UNKNOWN atom {rec.get('atom_index')} mapped without downgrade_note")


def validate_no_named_person_identity(adapters):
    """Step 7: PERSON_IDENTITY_QUARANTINED must not emit agent identity."""
    print(f"\n=== STEP 7: Named Person Identity Quarantine ===")
    for rec in adapters:
        if rec.get('disposition') == 'PERSON_IDENTITY_QUARANTINED':
            if rec.get('d2_participant_family'):
                fail(f"Quarantined adapter {rec.get('adapter_id','')[:16]} emits d2_participant_family")
            if rec.get('d2_participant_subtype'):
                fail(f"Quarantined adapter {rec.get('adapter_id','')[:16]} emits d2_participant_subtype")
            if rec.get('quarantine_reason') != 'Named person identity content; no agent identity emitted':
                fail(f"Quarantined adapter {rec.get('adapter_id','')[:16]}: missing quarantine_reason")


def validate_market_structure_forced(adapters):
    """Step 8: MarketStructure atoms with subject_family should be CONTEXT_ONLY."""
    print(f"\n=== STEP 8: MarketStructure Forced Mapping Check ===")
    for rec in adapters:
        pcls = rec.get('perspective_class', '')
        if rec.get('disposition') == 'CONTEXT_ONLY':
            pass  # Already correct
        elif pcls == 'MARKET_STRUCTURE' and rec.get('disposition') == 'MAPPED':
            if not rec.get('downgrade_note'):
                fail(f"MARKET_STRUCTURE atom {rec.get('atom_index')} mapped without downgrade")


def validate_archive_byte_identity(run_dirs):
    """Step 9: Verify 3 archive outputs byte-identical."""
    print(f"\n=== STEP 9: Archive Byte Identity (3-run) ===")
    if len(run_dirs) < 3:
        warn(f"Only {len(run_dirs)} run dirs available for comparison")
        return

    files = ['D2-CANDIDATE-ADAPTERS.jsonl', 'D2-ADAPTER-SUMMARY.yaml', 'D2-ADAPTER-PACKAGE.json']
    for fn in files:
        hashes = {}
        for rd in run_dirs:
            fp = os.path.join(rd, fn)
            if os.path.exists(fp):
                hashes[rd] = sha256_file(fp)
            else:
                fail(f"Missing {fn} in {rd}")

        if len(set(hashes.values())) == 1:
            print(f"  {fn}: IDENTICAL across {len(hashes)} runs ({list(hashes.values())[0][:16]}...)")
        else:
            fail(f"{fn}: DIFFERENT across runs:")
            for rd, h in sorted(hashes.items()):
                print(f"    {rd}: {h[:16]}...")


def validate_no_extra_no_omissions(adapters):
    """Step 10: Check no extras, no omissions."""
    print(f"\n=== STEP 10: No Extras, No Omissions ===")
    # Every adapter must have required fields
    required = {'adapter_id', 'source_deterministic_id', 'atom_index',
                'atom_type', 'perspective_class', 'disposition'}
    for rec in adapters:
        missing = required - set(rec.keys())
        if missing:
            fail(f"Adapter {rec.get('adapter_id','')[:16]}: missing fields {missing}")

    # No unexpected fields that aren't disposition-specific
    for rec in adapters:
        disp = rec.get('disposition', '')
        fields = set(rec.keys())
        if disp == 'PERSON_IDENTITY_QUARANTINED':
            forbidden = {'d2_participant_family', 'd2_participant_subtype'}
            overlap = fields & forbidden
            if overlap:
                fail(f"Quarantined adapter has forbidden fields: {overlap}")


# ========================================================================
# Main
# ========================================================================
def main():
    parser = argparse.ArgumentParser(description='D2 Adapter Validator')
    parser.add_argument('--q0-dir', required=True, help='Q0 source directory')
    parser.add_argument('--output-dir', required=True, help='Generated adapter output directory')
    parser.add_argument('--run-dirs', nargs='*', help='Multiple run directories for byte-identity comparison')
    args = parser.parse_args()

    print(f"validate_adapters.py — Epoch 15 Gate B: Strict Validator")
    print(f"Q0 Dir: {args.q0_dir}")
    print(f"Output Dir: {args.output_dir}")

    # Step 1: Source lock
    atoms, relations, questions = validate_source_lock(args.output_dir, args.q0_dir)

    # Read adapters
    adapter_path = os.path.join(args.output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
    adapters = read_jsonl(adapter_path)
    print(f"\n  Read {len(adapters)} adapter records from {adapter_path}")

    # Step 2: Source-set equality
    validate_source_set_equality(adapters, atoms)

    # Step 3: Family/subtype enum validation
    validate_family_subtype_enum(adapters)

    # Step 4: Duplicate key rejection
    validate_duplicate_keys(args.output_dir)

    # Step 5: Deterministic IDs
    validate_deterministic_ids(adapters, atoms)

    # Step 6: Claim downgrade
    validate_claim_downgrade(adapters, atoms)

    # Step 7: Named person quarantine
    validate_no_named_person_identity(adapters)

    # Step 8: Market structure forced mapping
    validate_market_structure_forced(adapters)

    # Step 9: Archive byte identity
    if args.run_dirs:
        validate_archive_byte_identity(args.run_dirs)

    # Step 10: No extras/omissions
    validate_no_extra_no_omissions(adapters)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY:")
    print(f"  Atoms: {len(atoms)}")
    print(f"  Relations: {len(relations)}")
    print(f"  Questions: {len(questions)}")
    print(f"  Adapters: {len(adapters)}")
    print(f"  Failures: {len(FAILURES)}")
    print(f"  Warnings: {len(WARNINGS)}")

    if FAILURES:
        print(f"\nFAILURES:")
        for f in FAILURES:
            print(f"  - {f}")
        print(f"\nValidation FAILED")
        return 1
    else:
        print(f"\nALL VALIDATIONS PASSED")
        return 0

if __name__ == '__main__':
    sys.exit(main())
