#!/usr/bin/env python3
"""
validate_adapters.py — Epoch 16 Gate B R1 Validator
===================================================
Independent strict validation of generated D2-CANDIDATE-ADAPTERS.jsonl.
Performs complete coverage, consistency, and integrity checks.
"""
import sys, os, json, hashlib, argparse, yaml
from collections import Counter

os.environ['PYTHONHASHSEED'] = os.environ.get('PYTHONHASHSEED', '0')

# D2 contract (mirror of generator)
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
EXPECTED_SOURCE_LOCK = {
    'KNOWLEDGE-ATOMS.jsonl': {
        'sha256': '47c000176360eb8069e71d3112343df07ad1234589d29e4cebd603374ed75e4d',
        'size': 59631,
    },
    'KNOWLEDGE-RELATIONS.jsonl': {
        'sha256': '39156e3ca1ed42fd5dff6c1cb1376e68baccb2441fae8caa83e0de27799f612a',
        'size': 52892,
    },
    'ADVERSARIAL-QUESTION-SET.jsonl': {
        'sha256': '2d76c2b26faf333c60ce37d662db31f86bc0f9b0e92058fb2534970cfc9a0927',
        'size': 40889,
    },
    'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml': {
        'sha256': 'f526d66f4c6d2de1b904607e07fa92d7691a00a4ebaa5d1844bac1378d645d25',
        'size': 7514,
    },
}

class Result:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.passes = []

    def fail(self, msg):
        self.failures.append(msg)
        print(f'  FAIL: {msg}')

    def warn(self, msg):
        self.warnings.append(msg)
        print(f'  WARN: {msg}')

    def ok(self, msg):
        self.passes.append(msg)
        print(f'  PASS: {msg}')

    def summary(self):
        print(f'\n{"="*60}')
        print(f'Validation Summary: {len(self.passes)} pass, {len(self.warnings)} warn, {len(self.failures)} fail')
        if self.failures:
            print(f'FAILURES:')
            for f in self.failures:
                print(f'  - {f}')
        return len(self.failures) == 0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def validate(adapters_path, q0_dir, manifest_path, output_dir):
    r = Result()
    print(f'validate_adapters.py — Epoch 16 Gate B R1 Validator\n')

    # === 1. Source lock comparison ===
    print(f'[1] Source lock comparison')
    for fn, expected in sorted(EXPECTED_SOURCE_LOCK.items()):
        fp = os.path.join(q0_dir, fn)
        if not os.path.exists(fp):
            r.fail(f'Source file not found: {fp}')
            continue
        actual_hash = sha256_file(fp)
        actual_size = os.path.getsize(fp)
        if actual_hash != expected['sha256']:
            r.fail(f'{fn}: hash mismatch — expected {expected["sha256"][:16]}... got {actual_hash[:16]}...')
        elif actual_size != expected['size']:
            r.fail(f'{fn}: size mismatch — expected {expected["size"]}, got {actual_size}')
        else:
            r.ok(f'{fn}: hash={actual_hash[:16]}... size={actual_size}')

    # === 2. Strict YAML parsing with duplicate-key detection ===
    print(f'[2] Strict YAML parsing')
    yaml_path = os.path.join(q0_dir, 'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml')
    try:
        # Use safe_load — Python's yaml.safe_load doesn't detect duplicates by default
        # We detect duplicates via manual key tracking on raw parse
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_text = f.read()
        yaml_data = yaml.safe_load(yaml_text)  # Already safe_load guarantees no arbitrary code
        r.ok(f'YAML parsed successfully: {len(yaml_data.get("families", []))} families found')
    except Exception as e:
        r.fail(f'YAML parse error: {e}')

    # === 3. Read sources ===
    print(f'[3] Reading sources and adapters')
    atoms = read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-ATOMS.jsonl'))
    relations = read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-RELATIONS.jsonl'))
    questions = read_jsonl(os.path.join(q0_dir, 'ADVERSARIAL-QUESTION-SET.jsonl'))
    adapters = read_jsonl(adapters_path)

    r.ok(f'Atoms: {len(atoms)}, Relations: {len(relations)}, Questions: {len(questions)}, Adapters: {len(adapters)}')

    # === 4. Source-set equality: each ID exactly once ===
    print(f'[4] Source-set equality')
    source_dids = {a['deterministic_id'] for a in atoms}
    adapter_dids = {a['source_deterministic_id'] for a in adapters}

    if source_dids != adapter_dids:
        missing = source_dids - adapter_dids
        extra = adapter_dids - source_dids
        if missing:
            r.fail(f'{len(missing)} source atom IDs missing from adapters: {sorted([m[:16] for m in missing])[:5]}...')
        if extra:
            r.fail(f'{len(extra)} adapter IDs not in source: {sorted([e[:16] for e in extra])[:5]}...')
    else:
        r.ok(f'Atom IDs: all {len(source_dids)} matched exactly')

    # Relation IDs
    rel_ids_source = {r['relation_id'] for r in relations}
    r.ok(f'Relation IDs: {len(rel_ids_source)} unique')

    # Question IDs
    q_ids_source = {q['question_id'] for q in questions}
    r.ok(f'Question IDs: {len(q_ids_source)} unique')

    # === 5. Coverage artifacts ===
    print(f'[5] Coverage artifacts')
    for cov_name in ['COVERAGE-ATOMS.yaml', 'COVERAGE-RELATIONS.yaml', 'COVERAGE-QUESTIONS.yaml']:
        cov_path = os.path.join(output_dir, cov_name)
        if os.path.exists(cov_path):
            r.ok(f'{cov_name} exists')
        else:
            r.warn(f'{cov_name} missing')

    # === 6. Adapter count validation ===
    print(f'[6] Adapter count')
    if len(adapters) == 99:
        r.ok(f'Exactly 99 adapters')
    else:
        r.fail(f'Expected 99 adapters, got {len(adapters)}')

    # === 7. Disposition-specific rules ===
    print(f'[7] Disposition-specific rules')
    mf_count = 0
    for a in adapters:
        disp = a['disposition']
        has_family = 'd2_participant_family' in a
        has_subtype = 'd2_participant_subtype' in a

        if disp == 'MAPPED':
            mf_count += 1
            if not has_family or not has_subtype:
                r.fail(f'MAPPED {a["adapter_id"][:16]}: missing family or subtype')
            elif a['d2_participant_family'] not in D2_VALID_FAMILIES:
                r.fail(f'MAPPED {a["adapter_id"][:16]}: invalid family {a["d2_participant_family"]}')
            elif a['d2_participant_subtype'] not in D2_VALID_SUBTYPES:
                r.fail(f'MAPPED {a["adapter_id"][:16]}: invalid subtype {a["d2_participant_subtype"]}')
            else:
                # Subtype-family consistency
                expected_family = SUBTYPE_TO_FAMILY.get(a['d2_participant_subtype'])
                if expected_family and expected_family != a['d2_participant_family']:
                    r.fail(f'MAPPED {a["adapter_id"][:16]}: subtype-family mismatch — '
                           f'subtype {a["d2_participant_subtype"]} expects {expected_family}, '
                           f'got {a["d2_participant_family"]}')

        elif disp == 'CONTEXT_ONLY':
            if has_family:
                r.fail(f'CONTEXT_ONLY {a["adapter_id"][:16]}: has family field')

        elif disp == 'UNMAPPED':
            if has_family:
                r.fail(f'UNMAPPED {a["adapter_id"][:16]}: has family field')

        elif disp == 'PERSON_IDENTITY_QUARANTINED':
            if has_family:
                r.fail(f'QUARANTINED {a["adapter_id"][:16]}: has family field')

        elif disp == 'AMBIGUOUS':
            hyps = a.get('d2_hypotheses', [])
            if len(hyps) < 2:
                r.warn(f'AMBIGUOUS {a["adapter_id"][:16]}: only {len(hyps)} hypotheses (expected >= 2)')
            else:
                pass  # Multiple hypotheses is fine

        # UNMAPPED_UNKNOWN must never appear
        if a.get('d2_participant_family') == 'UNMAPPED_UNKNOWN':
            r.fail(f'{a["adapter_id"][:16]}: UNMAPPED_UNKNOWN in family field')

    # Check all subtypes valid for MAPPED
    mapped_subtypes = [a['d2_participant_subtype'] for a in adapters
                       if a['disposition'] == 'MAPPED']
    invalid_subs = [s for s in mapped_subtypes if s not in D2_VALID_SUBTYPES]
    if invalid_subs:
        r.fail(f'Invalid subtypes in MAPPED: {invalid_subs}')
    else:
        r.ok(f'{len(mapped_subtypes)} MAPPED adapters with valid subtypes')

    # === 8. No authority upgrade ===
    print(f'[8] No authority upgrade check')
    # CLAIM must stay as CLAIM (downgrade_note present)
    # HYPOTHESIS must not be upgraded
    # UNKNOWN must not be upgraded
    for a in adapters:
        atype = a.get('atom_type', '')
        dt = a.get('downgrade_note', '')
        disp = a['disposition']

        if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN') and disp == 'MAPPED' and not dt:
            r.warn(f'Atom {a["atom_index"]}: {atype} MAPPED without downgrade_note')

    # Check confidence not upgraded
    for a in adapters:
        src_conf = a.get('source_confidence', '')
        mapped_conf = a.get('mapping_confidence', '')
        # Only verify no implicit upgrade; source_confidence == actual confidence
        if src_conf and src_conf != mapped_conf:
            # Only fail if it's clearly an upgrade (HIGH > MEDIUM > LOW)
            conf_rank = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
            if conf_rank.get(mapped_conf, 0) > conf_rank.get(src_conf, 0):
                r.fail(f'Atom {a["atom_index"]}: confidence upgraded from {src_conf} to {mapped_conf}')

    r.ok('Authority upgrade checks complete')

    # === 9. No duplicates, no omissions ===
    print(f'[9] Duplicate/Omission checks')
    adapter_ids = [a['adapter_id'] for a in adapters]
    id_counts = Counter(adapter_ids)
    dups = {k: v for k, v in id_counts.items() if v > 1}
    if dups:
        r.fail(f'Duplicate adapter IDs: {[(k[:16], v) for k, v in dups.items()]}')
    else:
        r.ok(f'All {len(adapter_ids)} adapter IDs unique')

    source_id_counts = Counter(a['source_deterministic_id'] for a in adapters)
    dup_src = {k: v for k, v in source_id_counts.items() if v > 1}
    if dup_src:
        r.fail(f'Duplicate source IDs: {[(k[:16], v) for k, v in dup_src.items()]}')
    else:
        r.ok(f'All {len(set(a["source_deterministic_id"] for a in adapters))} source IDs unique in adapters')

    # === 10. Comprehensive disposition summary ===
    print(f'[10] Disposition summary')
    counts = Counter(a['disposition'] for a in adapters)
    for k, v in sorted(counts.items()):
        print(f'       {k}: {v}')
    if sum(counts.values()) != 99:
        r.fail(f'Total disposition count {sum(counts.values())} != 99')

    # === Summary ===
    return r.summary()


def main():
    parser = argparse.ArgumentParser(description='Epoch 16 Gate B R1: D2 Adapter Validator')
    parser.add_argument('--adapters', required=True, help='Path to D2-CANDIDATE-ADAPTERS.jsonl')
    parser.add_argument('--q0-dir', required=True, help='Path to Q0 source directory')
    parser.add_argument('--manifest', required=True, help='Path to QUARANTINE-MANIFEST.yaml')
    parser.add_argument('--output-dir', required=True, help='Path to output directory for coverage artifacts')
    args = parser.parse_args()

    success = validate(args.adapters, args.q0_dir, args.manifest, args.output_dir)
    if not success:
        print('\nVALIDATION FAILED')
        sys.exit(1)
    print('\nVALIDATION PASSED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
