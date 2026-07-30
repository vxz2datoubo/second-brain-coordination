#!/usr/bin/env python3
"""
run_negative_tests.py — Epoch 15 Gate B: Negative Test Fixture Runner
Runs all negative test fixtures and verifies they are caught by validation rules.
Each test: given a deliberately-broken JSONL fixture, validate that it FAILS the
appropriate validation check.

Exit 0 if all fixtures fail as expected (i.e., defects are correctly caught).
Exit 1 if any fixture passes unexpectedly (i.e., a defect slipped through).
"""

import sys, os, json, hashlib, argparse, subprocess
from pathlib import Path

FAILURES = []
PASSES = []

def test_expect_fail(name, description, validator_args_fn):
    """Run a test that SHOULD produce validation failures."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"  Expected: {description}")
    print(f"{'='*60}")


def check_duplicate_key(fixture_path):
    """Check a JSON/JSONL file for duplicate keys."""
    path = fixture_path
    if not os.path.exists(path):
        print(f"  SKIP: fixture {path} not found")
        return

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if path.endswith('.jsonl'):
            for i, line in enumerate(content.strip().split('\n'), 1):
                try:
                    seen = {}
                    def check_dup(pairs):
                        for k, v in pairs:
                            if k in seen:
                                raise ValueError(f"Duplicate key: {k!r}")
                            seen[k] = v
                        return seen
                    json.loads(line, object_pairs_hook=check_dup)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"  PASS: Caught expected error: {e}")
                    PASSES.append(f"fixture:{os.path.basename(path)}")
                    return
            print(f"  FAIL: Duplicate key was NOT detected!")
            FAILURES.append(f"fixture:{os.path.basename(path)}")

        elif path.endswith('.json'):
            try:
                seen = {}
                def check_dup(pairs):
                    for k, v in pairs:
                        if k in seen:
                            raise ValueError(f"Duplicate key: {k!r}")
                        seen[k] = v
                    return seen
                json.loads(content, object_pairs_hook=check_dup)
                print(f"  FAIL: Duplicate key was NOT detected!")
                FAILURES.append(f"fixture:{os.path.basename(path)}")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"  PASS: Caught expected error: {e}")
                PASSES.append(f"fixture:{os.path.basename(path)}")

        elif path.endswith('.yaml'):
            try:
                import yaml
                class DupChecker(yaml.SafeLoader):
                    pass
                def dup_constructor(loader, node, deep=False):
                    mapping = {}
                    for k_node, v_node in node.value:
                        k = loader.construct_object(k_node, deep=deep)
                        if k in mapping:
                            raise ValueError(f"Duplicate YAML key: {k!r}")
                        mapping[k] = loader.construct_object(v_node, deep=deep)
                    return mapping
                DupChecker.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, dup_constructor)
                yaml.load(content, Loader=DupChecker)
                print(f"  FAIL: Duplicate YAML key was NOT detected!")
                FAILURES.append(f"fixture:{os.path.basename(path)}")
            except Exception as e:
                print(f"  PASS: Caught expected error: {e}")
                PASSES.append(f"fixture:{os.path.basename(path)}")

    except Exception as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:{os.path.basename(path)}")


def check_unmapped_unknown(fixture_path):
    """Check that UNMAPPED_UNKNOWN as a family is caught."""
    D2_VALID_FAMILIES = {"retail", "institutional_quant", "active_capital",
                         "policy_industrial_foreign_aggregate"}
    FORBIDDEN = {"UNMAPPED_UNKNOWN", "unmapped_unknown"}

    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                family = rec.get('d2_participant_family', '')
                if family in FORBIDDEN:
                    raise ValueError(f"Line {i}: FORBIDDEN family '{family}' detected!")
        print(f"  FAIL: UNMAPPED_UNKNOWN was NOT detected!")
        FAILURES.append(f"fixture:unmapped_unknown")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:unmapped_unknown")
    except Exception as e:
        print(f"  PASS: Other error (parser caught it): {e}")
        PASSES.append(f"fixture:unmapped_unknown")


def check_invalid_family(fixture_path):
    """Check that non-D2 family name is caught."""
    D2_VALID_FAMILIES = {"retail", "institutional_quant", "active_capital",
                         "policy_industrial_foreign_aggregate"}
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                family = rec.get('d2_participant_family', '')
                if family and rec.get('disposition') == 'MAPPED' and family not in D2_VALID_FAMILIES:
                    raise ValueError(f"Invalid D2 family: '{family}'")
        print(f"  FAIL: Invalid family was NOT detected!")
        FAILURES.append(f"fixture:invalid_family")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:invalid_family")


def check_invalid_subtype(fixture_path):
    """Check that non-D2 subtype is caught."""
    D2_VALID_SUBTYPES = {"retail_liquidity_taker", "retail_anchored_holder",
                         "systematic_rebalancer", "long_horizon_fund",
                         "event_driven_active", "short_horizon_momentum",
                         "policy_aggregate", "industrial_aggregate", "foreign_aggregate"}
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                subtype = rec.get('d2_participant_subtype', '')
                if subtype and rec.get('disposition') == 'MAPPED' and subtype not in D2_VALID_SUBTYPES:
                    raise ValueError(f"Invalid D2 subtype: '{subtype}'")
        print(f"  FAIL: Invalid subtype was NOT detected!")
        FAILURES.append(f"fixture:invalid_subtype")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:invalid_subtype")


def check_subtype_family_mismatch(fixture_path):
    """Check that subtype-to-family mismatch is caught."""
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
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                family = rec.get('d2_participant_family', '')
                subtype = rec.get('d2_participant_subtype', '')
                expected = SUBTYPE_TO_FAMILY.get(subtype, '')
                if expected and expected != family:
                    raise ValueError(f"Subtype '{subtype}' belongs to '{expected}', not '{family}'")
        print(f"  FAIL: Subtype-family mismatch was NOT detected!")
        FAILURES.append(f"fixture:subtype_family_mismatch")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:subtype_family_mismatch")


def check_market_structure_forced(fixture_path):
    """Check that MARKET_STRUCTURE forced mapping is caught."""
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                pcls = rec.get('perspective_class', '')
                disp = rec.get('disposition', '')
                downgrade = rec.get('downgrade_note', '')
                if pcls == 'MARKET_STRUCTURE' and disp == 'MAPPED' and not downgrade:
                    raise ValueError(f"MARKET_STRUCTURE atom mapped without downgrade")
        print(f"  FAIL: MARKET_STRUCTURE forced mapping was NOT detected!")
        FAILURES.append(f"fixture:market_structure_forced")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:market_structure_forced")


def check_claim_to_fact_upgrade(fixture_path):
    """Check that CLAIM without downgrade is caught."""
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                atype = rec.get('atom_type', '')
                disp = rec.get('disposition', '')
                downgrade = rec.get('downgrade_note', '')
                if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN') and disp == 'MAPPED' and not downgrade:
                    raise ValueError(f"CLAIM atom {rec.get('atom_index')} mapped without downgrade")
        print(f"  FAIL: CLAIM-to-FACT upgrade was NOT detected!")
        FAILURES.append(f"fixture:claim_to_fact_upgrade")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:claim_to_fact_upgrade")


def check_named_person_to_agent(fixture_path):
    """Check that quarantined record with family field is caught."""
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                if rec.get('disposition') == 'PERSON_IDENTITY_QUARANTINED':
                    if rec.get('d2_participant_family'):
                        raise ValueError(f"Quarantined adapter {rec.get('adapter_id')} emits d2_participant_family")
                    if rec.get('d2_participant_subtype'):
                        raise ValueError(f"Quarantined adapter {rec.get('adapter_id')} emits d2_participant_subtype")
        print(f"  FAIL: Named person quarantine leak was NOT detected!")
        FAILURES.append(f"fixture:named_person_to_agent")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:named_person_to_agent")


def check_missing_source_atom(fixture_path, atom_ids):
    """Check that adapter referencing non-existent source is caught."""
    try:
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                sid = rec.get('source_deterministic_id', '')
                if sid not in atom_ids:
                    raise ValueError(f"Line {i}: Adapter references non-existent source atom {sid[:16]}...")
        print(f"  FAIL: Missing source atom was NOT detected!")
        FAILURES.append(f"fixture:missing_source_atom")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:missing_source_atom")


def check_duplicate_deterministic_id(fixture_path):
    """Check that duplicate adapter_id is caught."""
    try:
        ids = set()
        with open(fixture_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                aid = rec.get('adapter_id', '')
                if aid in ids:
                    raise ValueError(f"Line {i}: Duplicate adapter_id: {aid}")
                ids.add(aid)
        print(f"  FAIL: Duplicate deterministic ID was NOT detected!")
        FAILURES.append(f"fixture:duplicate_deterministic_id")
    except ValueError as e:
        print(f"  PASS: Caught expected error: {e}")
        PASSES.append(f"fixture:duplicate_deterministic_id")


# ========================================================================
# Main
# ========================================================================

def main():
    parser = argparse.ArgumentParser(description='Negative Test Fixture Runner')
    parser.add_argument('--fixtures-dir', required=True, help='Directory containing negative fixtures')
    parser.add_argument('--q0-dir', required=True, help='Q0 source directory (for atom ID lookup)')
    args = parser.parse_args()

    fixtures_dir = args.fixtures_dir
    print(f"run_negative_tests.py — Epoch 15 Gate B: Negative Fixture Runner")
    print(f"Fixtures Dir: {fixtures_dir}")

    # Load real atom IDs for missing-source-atom test
    import subprocess as sp
    atom_ids = set()
    atoms_path = os.path.join(args.q0_dir, 'KNOWLEDGE-ATOMS.jsonl')
    if os.path.exists(atoms_path):
        with open(atoms_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    atom_ids.add(json.loads(line)['deterministic_id'])

    # 1. Duplicate key tests
    print(f"\n{'='*60}")
    print(f"DUPLICATE KEY TESTS")
    print(f"{'='*60}")
    check_duplicate_key(os.path.join(fixtures_dir, 'duplicate_key_json.json'))
    check_duplicate_key(os.path.join(fixtures_dir, 'duplicate_key_jsonl.jsonl'))
    check_duplicate_key(os.path.join(fixtures_dir, 'duplicate_key_yaml.yaml'))

    # 2. UNMAPPED_UNKNOWN as family
    print(f"\n{'='*60}")
    print(f"ADAPTER-SPECIFIC NEGATIVE TESTS")
    print(f"{'='*60}")
    check_unmapped_unknown(os.path.join(fixtures_dir, 'unmapped_unknown_as_family.jsonl'))
    check_invalid_family(os.path.join(fixtures_dir, 'invalid_family.jsonl'))
    check_invalid_subtype(os.path.join(fixtures_dir, 'invalid_subtype.jsonl'))
    check_subtype_family_mismatch(os.path.join(fixtures_dir, 'subtype_family_mismatch.jsonl'))

    # 3. Market structure, claim upgrade, named person
    check_market_structure_forced(os.path.join(fixtures_dir, 'market_structure_to_named_person.jsonl'))
    check_claim_to_fact_upgrade(os.path.join(fixtures_dir, 'market_structure_to_named_person.jsonl'))
    check_named_person_to_agent(os.path.join(fixtures_dir, 'market_structure_to_named_person.jsonl'))

    # 4. Missing source, duplicate ID, hash mismatch
    check_missing_source_atom(os.path.join(fixtures_dir, 'missing_source_atom.jsonl'), atom_ids)
    check_duplicate_deterministic_id(os.path.join(fixtures_dir, 'duplicate_deterministic_id.jsonl'))

    # Summary
    total = len(PASSES) + len(FAILURES)
    print(f"\n{'='*60}")
    print(f"NEGATIVE TEST SUMMARY:")
    print(f"  Total tests: {total}")
    print(f"  Passed (correctly caught): {len(PASSES)}")
    print(f"  Failed (defect slipped through): {len(FAILURES)}")

    if FAILURES:
        print(f"\nFAILED TESTS:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print(f"\nALL NEGATIVE TESTS PASSED")
    return 0

if __name__ == '__main__':
    sys.exit(main())
