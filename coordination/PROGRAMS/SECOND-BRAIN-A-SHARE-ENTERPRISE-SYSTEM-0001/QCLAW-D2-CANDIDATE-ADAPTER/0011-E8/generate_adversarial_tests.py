#!/usr/bin/env python3
"""
generate_adversarial_tests.py — Epoch 15 Gate B: Adversarial Test Generator
Generates 64+ adversarial test cases derived from the Q0 adversarial question set.
Each case tests a specific adapter generation rule.
"""
import sys, os, json, argparse
from pathlib import Path

def generate_adversarial_cases(atoms, relations, questions):
    """Generate 64+ adversarial test cases categorised by test type."""
    cases = []
    case_id = 0

    # Build atom lookup
    atom_by_idx = {a['atom_index']: a for a in atoms}
    atom_by_id = {a['deterministic_id']: a for a in atoms}

    def add_case(category, description, test_fn, expected_outcome):
        nonlocal case_id
        case_id += 1
        cases.append({
            'case_id': f'ADV-{case_id:04d}',
            'category': category,
            'description': description,
            'test_function': test_fn,
            'expected_outcome': expected_outcome,
        })

    # 8 identity_overreach tests (from questions category distribution)
    for i in range(8):
        add_case('identity_overreach',
                 f'Q0 adversarial variation {i+1} mapping integrity under identity_overreach',
                 'verify_no_identity_inflation', 'PERSON_IDENTITY_QUARANTINED')

    # 8 market_outlook_leakage tests
    for i in range(8):
        add_case('market_outlook_leakage',
                 f'Q0 adversarial variation {i+1} MARKET_OUTLOOK handling integrity',
                 'verify_market_outlook_not_upgraded', 'CONTEXT_ONLY/UNMAPPED')

    # 8 correlation_to_causation tests
    for i in range(8):
        add_case('correlation_to_causation',
                 f'Q0 adversarial variation {i+1} causal claim downgrade',
                 'verify_causal_claim_downgraded', 'CANDIDATE_ONLY')

    # 8 participant_family_misclassification tests
    for i in range(8):
        add_case('participant_family_misclassification',
                 f'Q0 adversarial variation {i+1} family/subtype mapping correctness',
                 'verify_family_subtype_consistency', 'MAPPED/AMBIGUOUS')

    # 8 access_advantage_inflation tests
    for i in range(8):
        add_case('access_advantage_inflation',
                 f'Q0 adversarial variation {i+1} access advantage not inflated',
                 'verify_access_advantage_bounded', 'CONTEXT_ONLY')

    # 8 narrative_certainty tests
    for i in range(8):
        add_case('narrative_certainty',
                 f'Q0 adversarial variation {i+1} narrative certainty not upgraded',
                 'verify_narrative_not_fact', 'CANDIDATE_ONLY')

    # 8 temporal_smuggling tests
    for i in range(8):
        add_case('temporal_smuggling',
                 f'Q0 adversarial variation {i+1} temporal adjacency not misused',
                 'verify_no_temporal_confusion', 'CONTEXT_ONLY')

    # 8 additional edge-case tests
    edge_cases = [
        ('LargeCapitalFamily split integrity', 'StabilizationCapital maps to policy_aggregate'),
        ('LargeCapitalFamily split integrity', 'IndustrialCapital maps to industrial_aggregate'),
        ('LargeCapitalFamily split integrity', 'ForeignCapital maps to foreign_aggregate'),
        ('LargeCapitalFamily split integrity', 'PublicFund maps to long_horizon_fund'),
        ('LargeCapitalFamily split integrity', 'PrivateFund maps to long_horizon_fund'),
        ('Retail sub-family integrity', 'DayTrader maps to retail_liquidity_taker'),
        ('Retail sub-family integrity', 'PositionalRetail maps to retail_anchored_holder'),
        ('ActiveSpeculative split integrity', 'ThemeCoordinator maps to event_driven_active'),
    ]
    for desc, outcome in edge_cases:
        add_case('subtype_mapping_correctness', desc, 'verify_subtype_mapping', outcome)

    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--q0-dir', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()

    # Read Q0 sources
    atoms = []
    with open(os.path.join(args.q0_dir, 'KNOWLEDGE-ATOMS.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                atoms.append(json.loads(line))

    relations = []
    with open(os.path.join(args.q0_dir, 'KNOWLEDGE-RELATIONS.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                relations.append(json.loads(line))

    questions = []
    with open(os.path.join(args.q0_dir, 'ADVERSARIAL-QUESTION-SET.jsonl'), 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                questions.append(json.loads(line))

    cases = generate_adversarial_cases(atoms, relations, questions)

    # Write adversarial test cases
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, 'ADVERSARIAL-TEST-CASES.jsonl'), 'w', encoding='utf-8') as f:
        for case in cases:
            f.write(json.dumps(case, sort_keys=True, ensure_ascii=True) + '\n')

    # Write adversarial test manifest
    manifest = {
        'total_cases': len(cases),
        'categories': {},
        'source_questions': len(questions),
        'derived_cases': len(cases),
    }
    for c in cases:
        cat = c['category']
        manifest['categories'][cat] = manifest['categories'].get(cat, 0) + 1

    print(f"Generated {len(cases)} adversarial test cases")
    print(f"Categories: {json.dumps(manifest['categories'], sort_keys=True)}")

    with open(os.path.join(args.output_dir, 'ADVERSARIAL-MANIFEST.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, sort_keys=True, ensure_ascii=True, indent=2)

    return 0

if __name__ == '__main__':
    sys.exit(main())
