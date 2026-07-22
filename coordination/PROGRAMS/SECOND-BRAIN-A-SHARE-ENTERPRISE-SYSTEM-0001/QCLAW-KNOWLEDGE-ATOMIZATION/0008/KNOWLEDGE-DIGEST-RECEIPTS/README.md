# KNOWLEDGE DIGEST RECEIPTS

## Purpose

This directory stores KnowledgeDigestReceipt files — immutable records of completed
knowledge digestion runs. Each receipt serves as proof that a source was digested
and documents what was produced.

## Receipt Format

Each receipt is a YAML file with the following structure:

```yaml
receipt:
  receipt_id: "RCPT-DIG-XXXXXXXX"
  digest_run_id: "DIG-XXXXXXXX"
  created_at: "YYYY-MM-DDThh:mm:ss+08:00"
  
  source:
    source_id: "SRC-XXXXXXXX"
    source_type: "DESIGN_DOCUMENT | ISSUE | PULL_REQUEST | ..."
    source_location: "path/or/url"
    source_hash: "sha256..."
    source_name: "Human-readable name"

  output:
    atoms_produced: 42
    relations_produced: 15
    conflicts_produced: 2
    unknowns_produced: 5
    skills_produced: 0
    structures_produced: 0
    
    atom_types_distribution:
      FACT: 10
      CLAIM: 5
      DEFINITION: 8
      RULE: 12
      # ... etc
    
    relation_types_distribution:
      SUPPORTS: 5
      PART_OF: 4
      REQUIRES: 3
      # ... etc

  quality:
    quality_report_id: "QGR-YYYYMMDD-XXX-XXX"
    gates_pass: 20
    gates_warn: 4
    gates_fail: 0
    overall_result: "ACCEPT_WITH_WARNINGS"

  decisions:
    key_decisions:
      - "DEC-XXX: Description of key decision"
    
  errors_warnings:
    errors: []
    warnings:
      - "WARN: Description"

  packet:
    packet_id: "PKT-XXXXXXXX"
    packet_hash: "sha256..."
    packet_location: "learning-packets/digest-XXX-{label}.json"

  verification:
    content_hash_verified: true
    source_hash_match: true
    packet_hash_match: true
    rebuilt_identical: false  # set true after rebuild verification

integrity:
  receipt_hash: "sha256..."
  signed_by: "QCLAW"
```

## Naming Convention

```
RCPT-{digest_run_id}.yaml
```

Examples:
- `RCPT-DIG-A1B2C3D4.yaml` — receipt for digest run DIG-A1B2C3D4
- `RCPT-DIG-E5F6A7B8.yaml` — receipt for digest run DIG-E5F6A7B8

## Lifecycle

### 1. Created
A receipt is created immediately after a digestion run completes (Stage 9 of the
pipeline). It captures a snapshot of what was produced, quality results, and key
decisions.

### 2. Verified
When a receipt is created, its `content_hash_verified` and `packet_hash_match` fields
are set based on Stage 8 hash validation. Initially, `rebuilt_identical` is `false`
until a rebuild verification is performed.

### 3. Rebuild-Verified
During P2 (Architecture Validation), receipts are rebuild-verified: the same source
is re-digested and the resulting packet hash is compared. If identical, `rebuilt_identical`
is set to `true`. This confirms deterministic reproducibility.

### 4. Archival
Receipts are never deleted. They serve as an immutable audit trail of all digestion
activity. If a receipt's source is re-digested (e.g., after source update), a NEW
receipt is created with a new `digest_run_id`. Old receipts remain for historical
reference.

### 5. Superseded
If a receipt is superseded by a newer digestion of the same source:
- The old receipt is NOT deleted
- A `superseded_by` field is added linking to the new receipt
- The new receipt has a `supersedes` field linking to the old receipt
- Both receipts remain in the directory

## Integrity

Each receipt includes an `integrity.receipt_hash` field — a SHA-256 hash of the
receipt content (excluding the `receipt_hash` field itself). This allows verification
that the receipt has not been tampered with after creation.

## Related Files

- `../schemas/SECRET-SCAN-RECEIPT.schema.json` — Secret scan receipts (separate system)
- `../PIPELINE.yaml` — Stage 9: Storage & Handoff defines receipt creation
- `../ATOMIZATION-PIPELINE.md` — Stage 9 details
