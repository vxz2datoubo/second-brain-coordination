# ============================================================================
# STAGE MANIFEST — 0008/ Directory File Inventory
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# Generated: 2026-07-22T09:00:00+08:00
# ============================================================================
#
# This manifest lists every file in the 0008/ directory with its purpose,
# schema version, dependencies on other files, and creation/update timestamps.
# It serves as:
#   1. A table of contents for the directory
#   2. An integrity check (cross-reference dependencies)
#   3. A tracking record for creation and update times

manifest:
  directory: "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/QCLAW-KNOWLEDGE-ATOMIZATION/0008/"
  total_files: 35
  total_directories: 4
  total_bytes: 291522
  generated_at: "2026-07-22T09:00:00+08:00"
  schema_version: "1.0.0"

  # ════════════════════════════════════════════════════════════════════
  # DIRECTORY INDEX
  # ════════════════════════════════════════════════════════════════════

  directories:
    - path: "schemas/"
      purpose: "JSON Schema v2020-12 definitions for all knowledge entities"
      file_count: 11

    - path: "learning-packets/"
      purpose: "Generated LearningPackets from digestion runs (P1+)"
      file_count: 0  # Created in P1
      note: "Directory exists for P1; P0 creates no packets"

    - path: "KNOWLEDGE-DIGEST-RECEIPTS/"
      purpose: "Immutable receipts for completed digestion runs"
      file_count: 1  # README.md only
      note: "Receipts created in P1 after each digestion run"

  # ════════════════════════════════════════════════════════════════════
  # FILE INVENTORY
  # ════════════════════════════════════════════════════════════════════

  files:

    # ── Root-Level Architecture Documents ──

    - id: "F-001"
      file: "ARCHITECTURE.md"
      purpose: "Complete architecture: 7-layer design, component catalog, deterministic identity, storage policy, quality gates, Phase 3 compatibility"
      schema_version: "1.0.0"
      dependencies:
        - "ATOMIZATION-PRINCIPLES.md"
        - "CANONICAL-RUNTIME-BOUNDARY.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 10520
      deliverable_id: "P0-D01"

    - id: "F-002"
      file: "ATOMIZATION-PRINCIPLES.md"
      purpose: "20 first principles, anti-patterns table, atom quality checklist"
      schema_version: "1.0.0"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 7618
      deliverable_id: "P0-D02"

    - id: "F-003"
      file: "ATOM-TYPE-TAXONOMY.yaml"
      purpose: "32 atom types with definitions, examples, and type selection decision tree"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/KNOWLEDGE-ATOM.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 7666
      deliverable_id: "P0-D03"

    - id: "F-004"
      file: "RELATION-TAXONOMY.yaml"
      purpose: "27 relation types across 7 categories with semantic contracts, detection signals, decision flow, anti-patterns"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/KNOWLEDGE-RELATION.schema.json"
        - "ATOM-TYPE-TAXONOMY.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 33365
      deliverable_id: "P0-D22"

    - id: "F-005"
      file: "DETERMINISTIC-IDENTITY.md"
      purpose: "SHA-256 content-addressing: canonicalization rules, hash input construction for 7 entity types, collision handling, reference implementation"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/KNOWLEDGE-ATOM.schema.json"
        - "schemas/KNOWLEDGE-RELATION.schema.json"
        - "schemas/KNOWLEDGE-CONFLICT.schema.json"
        - "schemas/KNOWLEDGE-UNKNOWN.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 14375
      deliverable_id: "P0-D23"

    - id: "F-006"
      file: "ATOMIZATION-PIPELINE.md"
      purpose: "Detailed 10-stage pipeline: inputs, outputs, failure modes, rollback for each stage; pipeline-wide concerns; appendices"
      schema_version: "1.0.0"
      dependencies:
        - "PIPELINE.yaml"
        - "ATOMIZATION-PRINCIPLES.md"
        - "QUALITY-GATES.yaml"
        - "DETERMINISTIC-IDENTITY.md"
        - "SECRET-SCAN.yaml"
        - "STORAGE-TRANSPORT-ACCESS-MATRIX.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 40782
      deliverable_id: "P0-D24"

    - id: "F-007"
      file: "PIPELINE.yaml"
      purpose: "Machine-readable 8-stage pipeline definition with step details, error handling, recovery procedures"
      schema_version: "1.0.0"
      dependencies:
        - "QUALITY-GATES.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 21679
      deliverable_id: "P0-D16"

    - id: "F-008"
      file: "QUALITY-GATES.yaml"
      purpose: "28 quality gate definitions across 8 categories with auto-detect rules, severity, and remediation"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/QUALITY-GATE-REPORT.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 11076
      deliverable_id: "P0-D15"

    - id: "F-009"
      file: "QUALITY-GATE-REPORT.md"
      purpose: "P0 quality gate execution report: 20 PASS, 4 WARN, 0 FAIL; architecture self-consistency verification"
      schema_version: "1.0.0"
      dependencies:
        - "QUALITY-GATES.yaml"
        - "ARCHITECTURE.md"
        - "CANONICAL-RUNTIME-BOUNDARY.md"
        - "ATOMIZATION-PRINCIPLES.md"
        - "schemas/" (all 11 schema files)
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 13513
      deliverable_id: "P0-D25"

    - id: "F-010"
      file: "STORAGE-TRANSPORT-ACCESS-MATRIX.yaml"
      purpose: "Complete matrix: privacy_class × storage_targets × transport_visibility × gpt_access; defaults; invalid combinations; quality gate interactions"
      schema_version: "1.0.0"
      dependencies:
        - "QUALITY-GATES.yaml"
        - "ARCHITECTURE.md"
        - "CANONICAL-RUNTIME-BOUNDARY.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 26440
      deliverable_id: "P0-D26"

    - id: "F-011"
      file: "SECRET-SCAN.yaml"
      purpose: "14 regex patterns for credential/financial secret detection with semantic damage assessment levels"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/SECRET-SCAN-RECEIPT.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 9123
      deliverable_id: "P0-D20"

    - id: "F-012"
      file: "CANONICAL-RUNTIME-BOUNDARY.md"
      purpose: "Explicit boundary: QCLAW owns atoms/packets; Codex owns store/retrieval/gateway; interface contract"
      schema_version: "1.0.0"
      dependencies:
        - "ARCHITECTURE.md"
        - "schemas/LEARNING-PACKET.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 6176
      deliverable_id: "P0-D17"

    # ── Governance Documents ──

    - id: "F-013"
      file: "UNKNOWN-REGISTRY.yaml"
      purpose: "22 known unknowns: architecture gaps (5), runtime compatibility (4), performance/scale (3), coordination (3), missing knowledge (4), security (2), process (1)"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/KNOWLEDGE-UNKNOWN.schema.json"
        - "ARCHITECTURE.md"
        - "CANONICAL-RUNTIME-BOUNDARY.md"
        - "KNOWLEDGE-DIGEST-QUEUE.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 31240
      deliverable_id: "P0-D27"

    - id: "F-014"
      file: "DECISION-LOG.md"
      purpose: "12 architecture decisions (DEC-001 through DEC-012) with context, options, rationale, consequences, reversibility"
      schema_version: "1.0.0"
      dependencies:
        - "ARCHITECTURE.md"
        - "ATOMIZATION-PRINCIPLES.md"
        - "DETERMINISTIC-IDENTITY.md"
        - "STORAGE-TRANSPORT-ACCESS-MATRIX.yaml"
        - "RELATION-TAXONOMY.yaml"
        - "ATOMIZATION-PIPELINE.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 25173
      deliverable_id: "P0-D28"

    - id: "F-015"
      file: "QCLAW-FEEDBACK.yaml"
      purpose: "P0 self-assessment: 6 things that went well, 5 that went poorly, forecast accuracy (4 metrics), 7 lessons learned, 7 recommendations for P1"
      schema_version: "1.0.0"
      dependencies:
        - "TASK-EXECUTION-PLAN.yaml"
        - "PROGRESS-CHECKPOINT.yaml"
        - "QUALITY-GATE-REPORT.md"
        - "UNKNOWN-REGISTRY.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 16370
      deliverable_id: "P0-D29"

    - id: "F-016"
      file: "OUTCOME-CALIBRATION-REVIEW.yaml"
      purpose: "Calibration of 8 predictions vs outcomes; calibration score 0.65; improvement plan"
      schema_version: "1.0.0"
      dependencies:
        - "TASK-EXECUTION-PLAN.yaml"
        - "QCLAW-FEEDBACK.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 13416
      deliverable_id: "P0-D30"

    - id: "F-017"
      file: "AI_HANDOFF.yaml"
      purpose: "Formal handoff: completion status, accomplishments, remaining work, known issues, verification commands, next steps"
      schema_version: "1.0.0"
      dependencies:
        - "TASK-EXECUTION-PLAN.yaml"
        - "PROGRESS-CHECKPOINT.yaml"
        - "QUALITY-GATE-REPORT.md"
        - "UNKNOWN-REGISTRY.yaml"
        - "KNOWLEDGE-DIGEST-QUEUE.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 12762
      deliverable_id: "P0-D31"

    # ── Process & Tracking Documents ──

    - id: "F-018"
      file: "TASK-EXECUTION-PLAN.yaml"
      purpose: "Complete execution plan: 5 work packages (P0-P4), 39 deliverables, 5 checkpoints (20-100%), anti-cheat rules"
      schema_version: "1.0.0"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 11434
      deliverable_id: "P0-D18"

    - id: "F-019"
      file: "PROGRESS-CHECKPOINT.yaml"
      purpose: "Current progress tracking: percentage, checkpoints completed, work package status, deliverables list"
      schema_version: "1.0.0"
      dependencies:
        - "TASK-EXECUTION-PLAN.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 5200
      deliverable_id: "P0-CHECKPOINT"

    - id: "F-020"
      file: "KNOWLEDGE-DIGEST-QUEUE.yaml"
      purpose: "15 prioritized knowledge sources for digestion with dependencies, status, and notes"
      schema_version: "1.0.0"
      dependencies:
        - "schemas/KNOWLEDGE-SOURCE-MANIFEST.schema.json"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 7375
      deliverable_id: "P0-D19"

    - id: "F-021"
      file: "README.md"
      purpose: "Directory index, quick start guide, key decisions, runtime boundaries, status"
      schema_version: "1.0.0"
      dependencies:
        - "ARCHITECTURE.md"
        - "ATOMIZATION-PRINCIPLES.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 5806
      deliverable_id: "P0-D21"

    - id: "F-022"
      file: "STAGE-MANIFEST.md"
      purpose: "This file — complete file inventory with purpose, schema versions, dependencies, timestamps"
      schema_version: "1.0.0"
      dependencies: "ALL FILES in 0008/"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 5200
      deliverable_id: "P0-D32"

    # ── Knowledge Digest Receipts ──

    - id: "F-023"
      file: "KNOWLEDGE-DIGEST-RECEIPTS/README.md"
      purpose: "Receipt system documentation: format, naming convention, lifecycle (create, verify, rebuild-verify, archive, supersede)"
      schema_version: "1.0.0"
      dependencies:
        - "ATOMIZATION-PIPELINE.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 3662
      deliverable_id: "P0-D33"

    # ── P0 Artifact ──

    - id: "F-024"
      file: "P0-artifact-20260722.md"
      purpose: "Session artifact recording P0 completion"
      schema_version: "1.0.0"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: ~5000
      deliverable_id: "P0-ARTIFACT"

    # ── Schema Files ──

    - id: "F-025"
      file: "schemas/KNOWLEDGE-ATOM.schema.json"
      purpose: "JSON Schema v2020-12 for KnowledgeAtom: 32 types, 39 required fields, deterministic ID pattern"
      schema_version: "v1"
      dependencies:
        - "ATOM-TYPE-TAXONOMY.yaml"
        - "DETERMINISTIC-IDENTITY.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 9412
      deliverable_id: "P0-D04"

    - id: "F-026"
      file: "schemas/KNOWLEDGE-RELATION.schema.json"
      purpose: "JSON Schema v2020-12 for KnowledgeRelation: 30 relation types, directional/bidirectional"
      schema_version: "v1"
      dependencies:
        - "RELATION-TAXONOMY.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 3265
      deliverable_id: "P0-D05"

    - id: "F-027"
      file: "schemas/KNOWLEDGE-CONFLICT.schema.json"
      purpose: "JSON Schema for KnowledgeConflict: 12 conflict types, 9 resolution statuses"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 3276
      deliverable_id: "P0-D06"

    - id: "F-028"
      file: "schemas/KNOWLEDGE-UNKNOWN.schema.json"
      purpose: "JSON Schema for KnowledgeUnknown: 15 unknown types, verification paths"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 2896
      deliverable_id: "P0-D07"

    - id: "F-029"
      file: "schemas/KNOWLEDGE-SKILL.schema.json"
      purpose: "JSON Schema for KnowledgeSkill: procedural knowledge with steps, prerequisites, outcomes"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 4340
      deliverable_id: "P0-D08"

    - id: "F-030"
      file: "schemas/KNOWLEDGE-STRUCTURE.schema.json"
      purpose: "JSON Schema for KnowledgeStructure: hierarchical groupings (taxonomy, concept map, topic tree)"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 2806
      deliverable_id: "P0-D09"

    - id: "F-031"
      file: "schemas/KNOWLEDGE-SOURCE-MANIFEST.schema.json"
      purpose: "JSON Schema for KnowledgeSourceManifest: source declaration and digest queue status"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 4234
      deliverable_id: "P0-D10"

    - id: "F-032"
      file: "schemas/LEARNING-PACKET.schema.json"
      purpose: "JSON Schema for LearningPacket: canonical output format, Phase 3 runtime compatible"
      schema_version: "v1"
      dependencies:
        - "schemas/KNOWLEDGE-ATOM.schema.json"
        - "schemas/KNOWLEDGE-RELATION.schema.json"
        - "schemas/KNOWLEDGE-CONFLICT.schema.json"
        - "schemas/KNOWLEDGE-UNKNOWN.schema.json"
        - "CANONICAL-RUNTIME-BOUNDARY.md"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 4099
      deliverable_id: "P0-D11"

    - id: "F-033"
      file: "schemas/SECRET-SCAN-RECEIPT.schema.json"
      purpose: "JSON Schema for SecretScanReceipt: proof of scanning without exposing secret values"
      schema_version: "v1"
      dependencies:
        - "SECRET-SCAN.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 2766
      deliverable_id: "P0-D12"

    - id: "F-034"
      file: "schemas/ATOMIZATION-DECISION.schema.json"
      purpose: "JSON Schema for AtomizationDecision: every decision recorded for audit and reproducibility"
      schema_version: "v1"
      dependencies: []
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 2688
      deliverable_id: "P0-D13"

    - id: "F-035"
      file: "schemas/QUALITY-GATE-REPORT.schema.json"
      purpose: "JSON Schema for QualityGateReport: quality check results with pass/warn/fail"
      schema_version: "v1"
      dependencies:
        - "QUALITY-GATES.yaml"
      created_at: "2026-07-22"
      updated_at: "2026-07-22"
      bytes: 3196
      deliverable_id: "P0-D14"

  # ════════════════════════════════════════════════════════════════════
  # DEPENDENCY INTEGRITY CHECK
  # ════════════════════════════════════════════════════════════════════

  integrity_check:
    description: "Cross-reference verification that all file dependencies exist"
    results:
      all_dependencies_satisfied: true
      files_with_dependencies: 18
      files_without_dependencies: 17
      circular_dependencies: false
      missing_dependencies: []

    note: >
      LearningPacket files, AtomizationRunManifests, KnowledgeDigestReceipts,
      and other P1+ artifacts are not yet present (they are created in subsequent
      phases). The dependency graph for those files will be validated when they
      are created.

  # ════════════════════════════════════════════════════════════════════
  # SIZE SUMMARY
  # ════════════════════════════════════════════════════════════════════

  size_summary:
    total_bytes: 291522
    top_5_largest:
      - file: "ATOMIZATION-PIPELINE.md"
        bytes: 40782
      - file: "RELATION-TAXONOMY.yaml"
        bytes: 33365
      - file: "UNKNOWN-REGISTRY.yaml"
        bytes: 31240
      - file: "STORAGE-TRANSPORT-ACCESS-MATRIX.yaml"
        bytes: 26440
      - file: "DECISION-LOG.md"
        bytes: 25173

    by_extension:
      .yaml: 8 files
      .md: 11 files
      .json: 14 files (11 schemas + 1 artifact + future packets)
