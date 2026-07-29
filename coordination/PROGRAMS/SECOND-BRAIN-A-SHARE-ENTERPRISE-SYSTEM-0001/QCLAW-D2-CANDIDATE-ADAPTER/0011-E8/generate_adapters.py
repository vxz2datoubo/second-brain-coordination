#!/usr/bin/env python3
"""
generate_adapters.py — Epoch 15 Gate B: Canonical D2 Adapter Builder
Builds deterministic D2 participant ontology adapters from Q0 knowledge package.

Architecture: Generator-first
Signal: QCLAW_E15_PR100_CANONICAL_D2_TRANSLATION_AND_GENERATION_DETERMINISM_READY_FOR_GPT_REVIEW
"""

import sys, os, json, hashlib, re, unicodedata, argparse
from pathlib import Path
from collections import OrderedDict

os.environ['PYTHONHASHSEED'] = os.environ.get('PYTHONHASHSEED', '0')

# ========================================================================
# D2 Canonical Contract (from d2_game_core.py @ d6f9e2e4)
# ========================================================================

D2_FAMILIES = {
    "retail": "retail",
    "institutional_quant": "institutional_quant",
    "active_capital": "active_capital",
    "policy_industrial_foreign_aggregate": "policy_industrial_foreign_aggregate",
}

D2_SUBTYPES = {
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

DISPOSITIONS = ["MAPPED", "UNMAPPED", "AMBIGUOUS", "CONTEXT_ONLY", "PERSON_IDENTITY_QUARANTINED"]

# Q0 family -> D2 family mapping (LargeCapitalFamily needs subtype-level granularity)
Q0_TO_D2_FAMILY = {
    "RetailPopulationFamily": "retail",
    "QuantStrategyFamily": "institutional_quant",
    "ActiveSpeculativeCapitalFamily": "active_capital",
}

# Q0 subtype -> D2 subtype mapping
Q0_TO_D2_SUBTYPE = {
    "DayTraderRetail": "retail_liquidity_taker",
    "PositionalRetail": "retail_anchored_holder",
    "IPOReversalRetail": "retail_liquidity_taker",
    "SmallCapHunterRetail": "retail_liquidity_taker",
    "IndexETFInvestor": "retail_anchored_holder",
    "SocialMediaFollowerRetail": "retail_liquidity_taker",
    "PublicFundSubtype": "long_horizon_fund",
    "PrivateFundSubtype": "long_horizon_fund",
    "StatisticalArbitrageQuant": "systematic_rebalancer",
    "HighFrequencyQuant": "systematic_rebalancer",
    "FactorModelQuant": "systematic_rebalancer",
    "SwingSpeculator": "short_horizon_momentum",
    "ThemeCoordinator": "event_driven_active",
    "StabilizationCapitalSubtype": "policy_aggregate",
    "IndustrialCapitalSubtype": "industrial_aggregate",
    "ForeignCapitalSubtype": "foreign_aggregate",
}

# Named-person atom indices (Liu Xin identity atoms)
NAMED_PERSON_ATOMS = {1, 2, 3, 4, 5, 6, 36, 37, 38, 39, 40, 69, 72, 80, 83, 85, 91, 97}

# MarketStructure/MethodologyNormative atoms (no participant mapping, CONTEXT_ONLY or UNMAPPED)
# All MARKET_STRUCTURE perspective atoms go to CONTEXT_ONLY regardless of subject_family
# This includes atoms 14-21, 46-53, 59, 99 that describe the mapping structure itself
MARKET_STRUCTURE_CONTEXT_ONLY = {7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
    22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 33, 34, 35, 41, 42, 43, 44, 45,
    46, 47, 48, 49, 50, 51, 52, 53, 59, 62, 63, 64, 70, 71, 73, 74, 75, 76,
    81, 82, 84, 86, 87, 88, 89, 93, 94, 95, 96, 99}

# Ambiguous atoms (could map to multiple D2 families)
AMBIGUOUS_ATOM_INDICES = {
    56: [("institutional_quant", "long_horizon_fund"), ("active_capital", "event_driven_active")],
    61: [("active_capital", "short_horizon_momentum"), ("retail", "retail_liquidity_taker")],
    65: [("retail", "retail_liquidity_taker"), ("institutional_quant", "long_horizon_fund")],
    67: [("institutional_quant", "systematic_rebalancer"), ("active_capital", "event_driven_active")],
    68: [("retail", "retail_anchored_holder"), ("institutional_quant", "systematic_rebalancer")],
    92: [("policy_industrial_foreign_aggregate", "foreign_aggregate"), ("active_capital", "event_driven_active")],
    98: [("policy_industrial_foreign_aggregate", "policy_aggregate"), ("institutional_quant", "long_horizon_fund")],
}

# ========================================================================
# Deterministic helpers
# ========================================================================

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def sha256_string(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def nfc(s):
    if isinstance(s, str):
        return unicodedata.normalize('NFC', s)
    return s

def nfc_sort(lst):
    if isinstance(lst, list) and lst and isinstance(lst[0], str):
        return sorted([nfc(x) for x in lst])
    if isinstance(lst, list) and lst and isinstance(lst[0], dict):
        return sorted(lst, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=True, separators=(',', ':')))
    return lst

def canonical_json(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(',', ':'))

def compute_deterministic_id(*components):
    payload = '||'.join(str(c) for c in components)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

# ========================================================================
# Source lock
# ========================================================================

def lock_sources(q0_dir):
    source_files = [
        'KNOWLEDGE-ATOMS.jsonl',
        'KNOWLEDGE-RELATIONS.jsonl',
        'ADVERSARIAL-QUESTION-SET.jsonl',
        'PARTICIPANT-FAMILY-AND-SUBTYPE-MAP.yaml',
    ]
    lock = {}
    for fn in source_files:
        fp = os.path.join(q0_dir, fn)
        lock[fn] = {'sha256': sha256_file(fp), 'size': os.path.getsize(fp)}
    return lock

# ========================================================================
# Read Q0 sources
# ========================================================================

def read_jsonl(path):
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records

def read_atoms(q0_dir):
    atoms = read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-ATOMS.jsonl'))
    return {a['atom_index']: a for a in atoms}

def read_relations(q0_dir):
    return read_jsonl(os.path.join(q0_dir, 'KNOWLEDGE-RELATIONS.jsonl'))

def read_questions(q0_dir):
    return read_jsonl(os.path.join(q0_dir, 'ADVERSARIAL-QUESTION-SET.jsonl'))

# ========================================================================
# Disposition classification
# ========================================================================

def classify_disposition(atom):
    idx = atom['atom_index']
    atype = atom.get('atom_type', '')
    pcls = atom.get('perspective_class', '')

    # RULE 1: Named-person atoms → PERSON_IDENTITY_QUARANTINED
    if idx in NAMED_PERSON_ATOMS:
        return 'PERSON_IDENTITY_QUARANTINED'

    # RULE 2: MarketStructure/Methodology atoms with no participant mapping → CONTEXT_ONLY
    if idx in MARKET_STRUCTURE_CONTEXT_ONLY:
        return 'CONTEXT_ONLY'

    # RULE 3: Ambiguous atoms → AMBIGUOUS
    if idx in AMBIGUOUS_ATOM_INDICES:
        return 'AMBIGUOUS'

    # RULE 4: Check if atom has explicit subject_family
    sf = atom.get('subject_family', '')
    ss = atom.get('subject_subtype', '')

    if sf and sf in Q0_TO_D2_FAMILY:
        # Direct family mapping exists
        return 'MAPPED'

    if sf == 'LargeCapitalFamily' and ss:
        # LargeCapitalFamily needs subtype-level mapping
        if ss in Q0_TO_D2_SUBTYPE:
            return 'MAPPED'

    # RULE 5: Has family but not mappable to D2
    if sf:
        return 'UNMAPPED'

    # RULE 6: No family info at all
    return 'UNMAPPED'

# ========================================================================
# Generate D2 mapping
# ========================================================================

def map_to_d2(atom):
    """Map a Q0 atom to D2 family and subtype. Returns (family, subtype, hypotheses)."""
    sf = atom.get('subject_family', '')
    ss = atom.get('subject_subtype', '')

    if sf == 'LargeCapitalFamily' and ss:
        d2_sub = Q0_TO_D2_SUBTYPE.get(ss)
        if d2_sub:
            d2_family = D2_SUBTYPES[d2_sub]
            return d2_family, d2_sub, None

    if sf in Q0_TO_D2_FAMILY:
        d2_family = Q0_TO_D2_FAMILY[sf]
        if ss and ss in Q0_TO_D2_SUBTYPE:
            d2_sub = Q0_TO_D2_SUBTYPE[ss]
            if D2_SUBTYPES[d2_sub] == d2_family:
                return d2_family, d2_sub, None
        # Family only, derive default subtype
        default_subs = {
            'retail': 'retail_liquidity_taker',
            'institutional_quant': 'systematic_rebalancer',
            'active_capital': 'short_horizon_momentum',
            'policy_industrial_foreign_aggregate': 'policy_aggregate',
        }
        return d2_family, default_subs.get(d2_family, ''), None

    return None, None, None

def get_ambiguous_hypotheses(atom_idx):
    return AMBIGUOUS_ATOM_INDICES.get(atom_idx, [])

# ========================================================================
# Generate adapter records
# ========================================================================

def generate_adapters(atoms, relations, questions, source_lock):
    adapter_records = []
    atom_ids_seen = set()
    summary = {
        'MAPPED': 0, 'UNMAPPED': 0, 'AMBIGUOUS': 0,
        'CONTEXT_ONLY': 0, 'PERSON_IDENTITY_QUARANTINED': 0,
    }

    version_info = {
        'adapter_version': '1.0.0',
        'schema_version': '22.0',
        'route_epoch': 15,
        'task_id': 'QCLAW-PR100-CANONICAL-D2-ONTOLOGY-TRANSLATION-AND-GENERATION-DETERMINISM-CLOSURE-0017-E15',
        'source_head': 'e54e04b',
        'd2_interface_head': 'd6f9e2e',
        'generation_timestamp': '2026-07-29T16:34:00+08:00',
    }

    # Process atoms in deterministic order (sorted by atom_index)
    for atom_idx in sorted(atoms.keys()):
        atom = atoms[atom_idx]
        did = atom['deterministic_id']
        idx = atom['atom_index']
        atype = atom.get('atom_type', '')
        pcls = atom.get('perspective_class', '')
        disposition = classify_disposition(atom)

        if did in atom_ids_seen:
            raise ValueError(f"Duplicate atom ID: {did}")
        atom_ids_seen.add(did)

        record = OrderedDict()
        record['adapter_id'] = compute_deterministic_id(
            'Q0-D2-ADAPTER', did, 'v22.0', disposition
        )
        record['source_deterministic_id'] = did
        record['atom_index'] = idx
        record['atom_type'] = atype
        record['perspective_class'] = pcls
        record['disposition'] = disposition

        if disposition == 'MAPPED':
            d2_family, d2_subtype, _ = map_to_d2(atom)
            # CLAIM/HYPOTHESIS/UNKNOWN downgrade check
            downgrade = ''
            if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN'):
                downgrade = 'CANDIDATE_ONLY'
            record['d2_participant_family'] = d2_family
            record['d2_participant_subtype'] = d2_subtype
            record['mapping_confidence'] = atom.get('confidence', 'MEDIUM')
            record['q0_family'] = atom.get('subject_family', '')
            record['q0_subtype'] = atom.get('subject_subtype', '')
            if downgrade:
                record['downgrade_note'] = downgrade
            summary['MAPPED'] += 1

        elif disposition == 'AMBIGUOUS':
            hypotheses = get_ambiguous_hypotheses(idx)
            record['d2_hypotheses'] = [
                {'family': h[0], 'subtype': h[1]} for h in hypotheses
            ]
            record['ambiguity_reason'] = 'Multiple D2 family hypotheses'
            downgrade = ''
            if atype in ('CLAIM', 'HYPOTHESIS', 'UNKNOWN'):
                downgrade = 'CANDIDATE_ONLY'
                record['downgrade_note'] = downgrade
            summary['AMBIGUOUS'] += 1

        elif disposition == 'PERSON_IDENTITY_QUARANTINED':
            record['quarantine_reason'] = 'Named person identity content; no agent identity emitted'
            record['quarantine_rule'] = 'NO_AGENT_IDENTITY'
            summary['PERSON_IDENTITY_QUARANTINED'] += 1

        elif disposition == 'CONTEXT_ONLY':
            record['context_reason'] = 'MarketStructure/Methodology atom; not a participant mapping'
            summary['CONTEXT_ONLY'] += 1

        elif disposition == 'UNMAPPED':
            # HARD RULE: UNMAPPED_UNKNOWN is NOT a D2 ParticipantFamily
            record['unmapped_reason'] = 'No mappable D2 family; UNMAPPED_UNKNOWN is NOT a valid D2 family'
            summary['UNMAPPED'] += 1

        # NEVER emit UNMAPPED_UNKNOWN as a family
        if 'd2_participant_family' in record and record.get('d2_participant_family') == 'UNMAPPED_UNKNOWN':
            raise ValueError(f"UNMAPPED_UNKNOWN emitted as family for atom {idx}")

        adapter_records.append(record)

    # Verify 99 atoms processed
    assert len(adapter_records) == 99, f"Expected 99 atoms, got {len(adapter_records)}"
    assert len(atom_ids_seen) == 99, f"Expected 99 unique IDs, got {len(atom_ids_seen)}"

    # Verify no UNMAPPED_UNKNOWN in any family field
    for rec in adapter_records:
        fam = rec.get('d2_participant_family', '')
        if fam == 'UNMAPPED_UNKNOWN':
            raise ValueError(f"UNMAPPED_UNKNOWN leaked into record {rec['adapter_id']}")

    # Build output package
    package = {
        'metadata': version_info,
        'source_lock': source_lock,
        'summary': summary,
        'adapters': adapter_records,
        'relation_count': len(relations),
        'question_count': len(questions),
    }

    return package

# ========================================================================
# Write outputs
# ========================================================================

def write_outputs(package, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Adapter JSONL
    adapter_path = os.path.join(output_dir, 'D2-CANDIDATE-ADAPTERS.jsonl')
    with open(adapter_path, 'w', encoding='utf-8') as f:
        for rec in package['adapters']:
            f.write(json.dumps(rec, sort_keys=True, ensure_ascii=True, separators=(',', ':')) + '\n')

    # 2. Mapping summary YAML
    summary_path = os.path.join(output_dir, 'D2-ADAPTER-SUMMARY.yaml')
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(f"# D2 Candidate Adapter Summary\n")
        f.write(f"# Generated: {package['metadata']['generation_timestamp']}\n")
        f.write(f"# Schema: {package['metadata']['schema_version']}\n\n")
        f.write(f"metadata:\n")
        for k, v in sorted(package['metadata'].items()):
            f.write(f"  {k}: {v}\n")
        f.write(f"\nsummary:\n")
        for k, v in sorted(package['summary'].items()):
            f.write(f"  {k}: {v}\n")
        f.write(f"\nsource_lock:\n")
        for fn, info in sorted(package['source_lock'].items()):
            f.write(f"  {fn}:\n")
            f.write(f"    sha256: {info['sha256']}\n")
            f.write(f"    size: {info['size']}\n")

    # 3. Full adapter package JSON
    package_path = os.path.join(output_dir, 'D2-ADAPTER-PACKAGE.json')
    with open(package_path, 'w', encoding='utf-8') as f:
        json.dump(package, f, sort_keys=True, ensure_ascii=True, indent=2)

    return {
        'adapters_jsonl': sha256_file(adapter_path),
        'summary_yaml': sha256_file(summary_path),
        'package_json': sha256_file(package_path),
    }

# ========================================================================
# Main
# ========================================================================

def main():
    parser = argparse.ArgumentParser(description='D2 Adapter Generator')
    parser.add_argument('--q0-dir', required=True, help='Path to Q0 source directory')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--hash-seed', default='0', help='PYTHONHASHSEED value')
    args = parser.parse_args()

    os.environ['PYTHONHASHSEED'] = args.hash_seed
    print(f"generate_adapters.py — Epoch 15 Gate B: D2 Adapter Builder")
    print(f"PYTHONHASHSEED={args.hash_seed}")
    print(f"Q0 Dir: {args.q0_dir}")
    print(f"Output Dir: {args.output_dir}")

    # Step 1: Lock sources
    print(f"\n[1/6] Locking sources...")
    source_lock = lock_sources(args.q0_dir)
    for fn, info in sorted(source_lock.items()):
        print(f"  {fn}: SHA256={info['sha256'][:16]}... size={info['size']}")

    # Step 2: Read Q0 sources
    print(f"\n[2/6] Reading Q0 sources...")
    atoms = read_atoms(args.q0_dir)
    relations = read_relations(args.q0_dir)
    questions = read_questions(args.q0_dir)
    print(f"  Atoms: {len(atoms)}, Relations: {len(relations)}, Questions: {len(questions)}")
    assert len(atoms) == 99, f"Expected 99 atoms, got {len(atoms)}"
    assert len(relations) == 147, f"Expected 147 relations, got {len(relations)}"
    assert len(questions) == 64, f"Expected 64 questions, got {len(questions)}"

    # Step 3: Generate adapters
    print(f"\n[3/6] Generating D2 adapters...")
    package = generate_adapters(atoms, relations, questions, source_lock)
    print(f"  Summary: {json.dumps(package['summary'], sort_keys=True)}")

    # Step 4: Validate no UNMAPPED_UNKNOWN
    print(f"\n[4/6] Validating no UNMAPPED_UNKNOWN...")
    for rec in package['adapters']:
        assert rec.get('d2_participant_family') != 'UNMAPPED_UNKNOWN', \
            f"UNMAPPED_UNKNOWN in record atom_index={rec['atom_index']}"
    print(f"  PASS: No UNMAPPED_UNKNOWN family values")

    # Step 5: Write outputs
    print(f"\n[5/6] Writing outputs...")
    output_hashes = write_outputs(package, args.output_dir)
    for fn, h in sorted(output_hashes.items()):
        print(f"  {fn}: SHA256={h[:32]}...")

    # Step 6: Print manifest
    print(f"\n[6/6] Generation complete")
    print(f"\nOUTPUT MANIFEST:")
    print(f"  adapters: {package['summary']['MAPPED']}")
    print(f"  unmapped: {package['summary']['UNMAPPED']}")
    print(f"  ambiguous: {package['summary']['AMBIGUOUS']}")
    print(f"  context_only: {package['summary']['CONTEXT_ONLY']}")
    print(f"  quarantined: {package['summary']['PERSON_IDENTITY_QUARANTINED']}")
    print(f"  total: {len(package['adapters'])}")
    print(f"  source_lock: {json.dumps(source_lock, sort_keys=True)}")

    # Write generation receipt
    receipt_path = os.path.join(args.output_dir, 'GENERATION-RECEIPT.json')
    receipt = {
        'task_id': package['metadata']['task_id'],
        'generation_timestamp': '2026-07-29T16:34:00+08:00',
        'python_version': sys.version.split()[0],
        'hashseed': args.hash_seed,
        'source_lock': source_lock,
        'output_hashes': output_hashes,
        'summary': package['summary'],
        'total_atoms': len(package['adapters']),
    }
    with open(receipt_path, 'w', encoding='utf-8') as f:
        json.dump(receipt, f, sort_keys=True, ensure_ascii=True, indent=2)
    print(f"  receipt: {receipt_path}")

    return 0

if __name__ == '__main__':
    sys.exit(main())
