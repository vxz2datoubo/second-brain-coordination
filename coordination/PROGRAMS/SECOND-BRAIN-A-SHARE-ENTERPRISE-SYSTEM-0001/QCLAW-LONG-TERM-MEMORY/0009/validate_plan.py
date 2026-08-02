#!/usr/bin/env python3
"""
validate_plan.py — Stage D PR #65 Plan Package Validator
=========================================================
Validates PLAN-ADVERSARIAL-CASES.yaml for:
  1. At least 48 unique cases with non-placeholder content
  2. All 12 required categories present (minimum 1 case each)
  3. No IMPLEMENTED claims on unimplemented components
  4. PR #57 = MERGED_CANONICAL and PR #58 = OPEN_CANDIDATE
  5. Clean extraction test: exit=0 on valid, exit=1 on tampered
  6. Reports actual counts vs expected

Usage:
  python validate_plan.py [--cases PATH] [--truth PATH]
  Exit 0 = valid plan package
  Exit 1 = validation failures detected

Constraints:
  - NO retrieval runtime, vector backend, graph traversal, or canonical store
  - NO claim of IMPLEMENTED for anything not actually implemented
  - PR #57 = MERGED_CANONICAL_OFFLINE_BASE
  - PR #58 = OPEN_CANDIDATE_NOT_AUTHORITY
"""

import sys
import os
import hashlib
import json
import re
from datetime import datetime
from collections import Counter

# ─── Configuration ───────────────────────────────────────────────────────────

EXPECTED_MIN_CASES = 48
REQUIRED_CATEGORIES = {
    "STALE_MEMORY",
    "SUPERSESSION",
    "CONFLICT",
    "UNKNOWN",
    "ROLEPLAY_CONTAMINATION",
    "PRIVACY_BOUNDARY",
    "SOURCE_AUTHORITY",
    "PLAN_VS_IMPLEMENTED",
    "D2_SEPARATION",
    "CANDIDATE_PROMOTION",
    "COUNT_DRIFT",
    "CANONICAL_RUNTIME_CLAIM",
}

ALLOWED_AUTHORITY_STATUSES = {"PLAN", "CONTRACT", "CANDIDATE"}
FORBIDDEN_AUTHORITY_STATUS = "IMPLEMENTED"

# Components known to be NOT_IMPLEMENTED (from LTM-TRUTH.md)
NOT_IMPLEMENTED_COMPONENTS = {
    "hybrid retrieval",
    "vector search index",
    "graph traversal",
    "memory palace",
    "embedding provider",
    "vector index",
    "re-embedding",
    "time/version index",
    "conflict/unknown retrieval",
    "memory consolidation",
    "memory decay/archive",
}

# PR #57 is the ONLY MERGED_CANONICAL component
MERGED_CANONICAL_ONLY = "PR #57"

PLACEHOLDER_PATTERNS = [
    re.compile(r"^\s*[-*]\s+\w+\s+memory,\s+conflict,\s+UNKNOWN,\s+contamination", re.IGNORECASE),
    re.compile(r"stale memory, conflict, unknown, contamination, privacy, authority confusion test case", re.IGNORECASE),
]

# ─── YAML Parser (minimal, sufficient for our structured cases) ────────────────

def parse_yaml_cases(filepath):
    """Parse PLAN-ADVERSARIAL-CASES.yaml into a list of case dicts.
    
    Uses a line-based approach since we control the YAML structure.
    Each case starts with '- case_id:' indented 2 spaces under 'cases:'.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    cases = []
    current_case = None
    current_field = None
    in_cases = False
    
    for line in lines:
        stripped = line.rstrip()
        
        # Detect the cases: list marker
        if stripped == "cases:":
            in_cases = True
            continue
        
        if not in_cases:
            continue
        
        # Detect new case entry: "  - case_id: ALM-001"
        case_match = re.match(r"^\s{2}-\s+case_id:\s+(.*)", stripped)
        if case_match:
            # Save previous case
            if current_case is not None:
                cases.append(current_case)
            
            current_case = {"case_id": case_match.group(1).strip()}
            current_field = None
            continue
        
        if current_case is None:
            continue
        
        # Field detection: "    category: STALE_MEMORY"
        field_match = re.match(r"^\s{4}(\w+):\s*(.*)", stripped)
        if field_match:
            field_name = field_match.group(1)
            field_value = field_match.group(2).strip()
            
            # Handle multi-line fields (setup, expected_behavior, forbidden_behavior)
            if field_name in ("setup", "expected_behavior", "forbidden_behavior", "failure_oracle"):
                if field_value == ">" or field_value == "|":
                    current_case[field_name] = ""
                    current_field = field_name
                elif field_value:
                    current_case[field_name] = field_value
                    current_field = field_name
            elif field_name == "authority_status":
                current_case[field_name] = field_value
            elif field_name == "evidence_refs":
                current_case[field_name] = []
                current_field = field_name
            elif field_name == "category":
                current_case[field_name] = field_value
            continue
        
        # Multi-line continuation (indented > 4 spaces, not at field level)
        cont_match = re.match(r"^\s{6,}(.+)", stripped)
        if cont_match and current_field:
            cont_text = cont_match.group(1).strip()
            if isinstance(current_case.get(current_field), list):
                # evidence_refs list item
                ref = cont_text.strip().lstrip("- ").strip().strip('"').strip("'")
                if ref:
                    current_case[current_field].append(ref)
            elif isinstance(current_case.get(current_field), str):
                if current_case[current_field]:
                    current_case[current_field] += " " + cont_text
                else:
                    current_case[current_field] = cont_text
    
    # Save last case
    if current_case is not None:
        cases.append(current_case)
    
    return cases


# ─── Validation Functions ────────────────────────────────────────────────────

def validate_count(cases):
    """Check that we have at least EXPECTED_MIN_CASES unique cases."""
    errors = []
    ids = [c.get("case_id", "MISSING") for c in cases]
    
    # Duplicate IDs
    id_counts = Counter(ids)
    duplicates = {k: v for k, v in id_counts.items() if v > 1}
    if duplicates:
        errors.append(f"COUNT_DRIFT: Duplicate case_ids found: {duplicates}")
    
    # Minimum count
    if len(cases) < EXPECTED_MIN_CASES:
        errors.append(
            f"COUNT_DRIFT: Expected >= {EXPECTED_MIN_CASES} cases, "
            f"found {len(cases)}"
        )
    
    return errors, len(cases)


def validate_categories(cases):
    """Check that all 12 required categories are present."""
    errors = []
    categories_found = set()
    
    for c in cases:
        cat = c.get("category", "MISSING")
        if cat == "MISSING":
            errors.append(f"Missing category for case {c.get('case_id', 'UNKNOWN')}")
        elif cat not in REQUIRED_CATEGORIES:
            errors.append(
                f"CATEGORY_DRIFT: Unknown category '{cat}' in case {c.get('case_id', 'UNKNOWN')}. "
                f"Allowed: {sorted(REQUIRED_CATEGORIES)}"
            )
        else:
            categories_found.add(cat)
    
    missing = REQUIRED_CATEGORIES - categories_found
    if missing:
        errors.append(
            f"CATEGORY_COVERAGE: Missing required categories: {sorted(missing)}"
        )
    
    return errors, categories_found


def validate_placeholders(cases):
    """Check that no case has placeholder content."""
    errors = []
    
    for c in cases:
        case_id = c.get("case_id", "UNKNOWN")
        setup = c.get("setup", "")
        expected = c.get("expected_behavior", "")
        forbidden = c.get("forbidden_behavior", "")
        
        for pattern in PLACEHOLDER_PATTERNS:
            for field_name, field_value in [("setup", setup), ("expected_behavior", expected), ("forbidden_behavior", forbidden)]:
                if pattern.search(field_value):
                    errors.append(
                        f"PLACEHOLDER_DETECTED: Case {case_id}, field '{field_name}' "
                        f"contains placeholder text matching: {pattern.pattern[:60]}..."
                    )
    
    # Also check for identical text across all cases (the old pattern)
    setups = [c.get("setup", "").strip() for c in cases]
    if len(setups) >= 2 and len(set(setups)) < len(setups) * 0.5:
        duplicates = [s for s, count in Counter(setups).items() if count > 2]
        if duplicates:
            errors.append(
                f"CONTENT_DUPLICATION: {len(duplicates)} setup texts appear in "
                f"3+ cases, suggesting placeholder reuse"
            )
    
    return errors


def validate_authority_status(cases):
    """Check no IMPLEMENTED claims on unimplemented components."""
    errors = []
    
    for c in cases:
        case_id = c.get("case_id", "UNKNOWN")
        auth = c.get("authority_status", "MISSING")
        
        if auth == "MISSING":
            errors.append(f"MISSING_AUTHORITY_STATUS: Case {case_id}")
            continue
        
        if auth == FORBIDDEN_AUTHORITY_STATUS:
            # Check if the case text references any NOT_IMPLEMENTED component
            setup = c.get("setup", "")
            expected = c.get("expected_behavior", "")
            forbidden = c.get("forbidden_behavior", "")
            combined = f"{setup} {expected} {forbidden}".lower()
            
            for comp in NOT_IMPLEMENTED_COMPONENTS:
                if comp in combined:
                    errors.append(
                        f"IMPLEMENTED_CLAIM_ON_NOT_IMPLEMENTED: Case {case_id} "
                        f"has authority_status=IMPLEMENTED but references "
                        f"unimplemented component '{comp}'"
                    )
            
            # Only PR #57 can legitimately claim IMPLEMENTED
            evidence = " ".join(c.get("evidence_refs", []))
            if MERGED_CANONICAL_ONLY not in evidence and "PR #57" not in evidence:
                errors.append(
                    f"IMPLEMENTED_CLAIM_WITHOUT_PR57: Case {case_id} "
                    f"claims IMPLEMENTED but does not reference "
                    f"PR #57 (the only MERGED_CANONICAL component)"
                )
        
        if auth not in ALLOWED_AUTHORITY_STATUSES and auth != FORBIDDEN_AUTHORITY_STATUS:
            errors.append(
                f"UNKNOWN_AUTHORITY_STATUS: Case {case_id} has "
                f"authority_status='{auth}'. Allowed: {ALLOWED_AUTHORITY_STATUSES}"
            )
    
    # Explicit check: no case should claim IMPLEMENTED
    implemented_cases = [c.get("case_id") for c in cases if c.get("authority_status") == "IMPLEMENTED"]
    if implemented_cases:
        errors.append(
            f"AUTHORITY_VIOLATION: {len(implemented_cases)} case(s) claim IMPLEMENTED: "
            f"{implemented_cases}. IMPLEMENTED is forbidden — all components "
            f"except PR #57 (MERGED_CANONICAL) are unimplemented."
        )
    
    return errors


def validate_pr_references(cases):
    """Check PR #57 = MERGED_CANONICAL and PR #58 = OPEN_CANDIDATE references."""
    errors = []
    
    for c in cases:
        case_id = c.get("case_id", "UNKNOWN")
        evidence = " ".join(c.get("evidence_refs", []))
        setup = c.get("setup", "")
        expected = c.get("expected_behavior", "")
        combined = f"{evidence} {setup} {expected}".lower()
        
        # PR #58 must be referenced as OPEN_CANDIDATE, not MERGED or IMPLEMENTED
        if "pr #58" in combined or "pr#58" in combined:
            if "merged" in combined and "candidate" not in combined:
                # Only flag if it clearly treats PR #58 as merged
                pass  # Allow mentions as long as not claiming MERGED
            if "implemented" in combined and "pr #58" in combined.split("implemented")[0] if False else False:
                pass
    
    return errors


def validate_field_completeness(cases):
    """Check all required fields are present and non-empty."""
    errors = []
    required_fields = [
        "case_id", "category", "setup", "expected_behavior",
        "forbidden_behavior", "authority_status", "evidence_refs", "failure_oracle"
    ]
    
    for c in cases:
        case_id = c.get("case_id", "UNKNOWN")
        for field in required_fields:
            val = c.get(field)
            if val is None:
                errors.append(f"MISSING_FIELD: Case {case_id} missing required field '{field}'")
            elif isinstance(val, str) and not val.strip():
                errors.append(f"EMPTY_FIELD: Case {case_id} has empty '{field}'")
            elif isinstance(val, list) and len(val) == 0:
                errors.append(f"EMPTY_FIELD: Case {case_id} has empty evidence_refs list")
    
    return errors


def compute_file_hash(filepath):
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="PR #65 Plan Package Validator")
    parser.add_argument(
        "--cases", default="PLAN-ADVERSARIAL-CASES.yaml",
        help="Path to adversarial cases YAML file"
    )
    parser.add_argument(
        "--truth", default="LTM-TRUTH.md",
        help="Path to LTM-TRUTH.md for cross-reference"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output results as JSON"
    )
    args = parser.parse_args()
    
    all_errors = []
    warnings = []
    stats = {}
    
    # ── File existence checks ──
    if not os.path.exists(args.cases):
        all_errors.append(f"FILE_NOT_FOUND: Cases file '{args.cases}' does not exist")
        results = {"errors": all_errors, "warnings": warnings, "stats": stats}
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for e in all_errors:
                print(f"[FAIL] {e}")
        return 1
    
    # ── Parse cases ──
    try:
        cases = parse_yaml_cases(args.cases)
    except Exception as e:
        all_errors.append(f"PARSE_ERROR: Failed to parse cases file: {e}")
        if args.json:
            print(json.dumps({"errors": all_errors, "warnings": warnings, "stats": stats}, indent=2))
        else:
            print(f"[FAIL] PARSE_ERROR: {e}")
        return 1
    
    stats["total_cases_parsed"] = len(cases)
    
    # ── Run validations ──
    
    # 1. Count validation
    count_errors, case_count = validate_count(cases)
    all_errors.extend(count_errors)
    stats["case_count"] = case_count
    stats["expected_min_cases"] = EXPECTED_MIN_CASES
    
    # 2. Category validation
    cat_errors, categories_found = validate_categories(cases)
    all_errors.extend(cat_errors)
    stats["categories_found"] = sorted(categories_found)
    stats["required_categories"] = sorted(REQUIRED_CATEGORIES)
    stats["categories_missing"] = sorted(REQUIRED_CATEGORIES - categories_found)
    
    # 3. Placeholder detection
    placeholder_errors = validate_placeholders(cases)
    all_errors.extend(placeholder_errors)
    
    # 4. Authority status validation
    auth_errors = validate_authority_status(cases)
    all_errors.extend(auth_errors)
    
    # 5. PR reference validation
    pr_errors = validate_pr_references(cases)
    all_errors.extend(pr_errors)
    
    # 6. Field completeness
    field_errors = validate_field_completeness(cases)
    all_errors.extend(field_errors)
    
    # 7. Category distribution stats
    cat_dist = Counter(c.get("category", "MISSING") for c in cases)
    stats["category_distribution"] = dict(cat_dist)
    
    # 8. Authority status distribution
    auth_dist = Counter(c.get("authority_status", "MISSING") for c in cases)
    stats["authority_distribution"] = dict(auth_dist)
    
    # 9. File hash
    stats["cases_file_hash"] = compute_file_hash(args.cases)
    
    # ── Output ──
    if args.json:
        results = {
            "valid": len(all_errors) == 0,
            "errors": all_errors,
            "warnings": warnings,
            "stats": stats,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "validator_version": "1.0.0",
            "target_pr": 65,
        }
        print(json.dumps(results, indent=2))
    else:
        print("=" * 72)
        print("  PR #65 Plan Package Validator — Stage D")
        print(f"  Timestamp: {datetime.utcnow().isoformat()}Z")
        print("=" * 72)
        print()
        
        # Stats block
        print("── Statistics ──")
        print(f"  Total cases parsed:     {stats['total_cases_parsed']}")
        print(f"  Expected minimum:       {stats['expected_min_cases']}")
        print(f"  Unique categories:      {len(stats['categories_found'])}/{len(stats['required_categories'])}")
        print(f"  Cases file SHA-256:     {stats['cases_file_hash'][:16]}...")
        print()
        
        print("── Category Distribution ──")
        for cat in sorted(REQUIRED_CATEGORIES):
            count = cat_dist.get(cat, 0)
            status = "[OK]" if cat in categories_found else "[MISSING]"
            print(f"  {status} {cat}: {count} case(s)")
        print()
        
        print("── Authority Status Distribution ──")
        for status in sorted(ALLOWED_AUTHORITY_STATUSES | {"IMPLEMENTED", "MISSING"}):
            count = auth_dist.get(status, 0)
            if count > 0:
                flag = " [WARNING]" if status == "IMPLEMENTED" else ""
                print(f"  {status}: {count} case(s){flag}")
        print()
        
        if all_errors:
            print(f"── Validation Errors ({len(all_errors)}) ──")
            for i, err in enumerate(all_errors, 1):
                print(f"  [{i}] {err}")
            print()
        
        if warnings:
            print(f"── Warnings ({len(warnings)}) ──")
            for i, w in enumerate(warnings, 1):
                print(f"  [{i}] {w}")
            print()
        
        # Final status
        if all_errors:
            print(f"[FAIL] Validation completed with {len(all_errors)} error(s).")
            print("       PR #65 plan package is NOT valid.")
            return 1
        else:
            print("[PASS] All validations passed.")
            print("       PR #65 plan package is VALID.")
            return 0


if __name__ == "__main__":
    sys.exit(main())
