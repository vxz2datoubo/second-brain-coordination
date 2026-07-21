# Candidate Memory Library Schema v0.2
# ── 候选记忆库架构设计 ──
#
# 设计原则:
# 1. knowledge_status / gpt_access / transport_visibility / authority_level 四轴独立
# 2. 所有知识完整入库（USER-DIRECTIVE-COMPLETE-KNOWLEDGE-LIBRARY-v1.0）
# 3. 冲突/修正/来源/版本完整保留
# 4. 凭证类秘密仅引用ID，不保存完整内容

## ── Tables ──

### atoms
- id TEXT PRIMARY KEY              # SHA256 content-addressed atom_id
- atom_type TEXT NOT NULL          # FACT / CONCEPT / PROCEDURE / RULE / OPINION / EVENT / RELATION / METADATA / WARNING / EXPERIENCE / PREFERENCE / GOAL / CONSTRAINT / ASSUMPTION / UNKNOWN
- canonical_statement TEXT NOT NULL
- scope TEXT                       # domain scope
- confidence REAL                  # 0.0–1.0
- verification_status TEXT         # VERIFIED / UNVERIFIED / DISPUTED / OUTDATED / REPLACED
- memory_type TEXT                 # SEMANTIC / EPISODIC / PROCEDURAL / META
- privacy_class TEXT               # PUBLIC_SAFE / INTERNAL / PERSONAL / RESTRICTED / CREDENTIAL_REF
- evidence_quality TEXT            # high / medium / low / synthetic / none
- premises TEXT                    # JSON array of premise strings
- exceptions TEXT                  # JSON array of exception strings
- failure_conditions TEXT          # JSON array of failure conditions
- source_reference TEXT            # human-readable source
- original_excerpt TEXT            # original text from source
- processor_version TEXT           # pipeline version
- base_knowledge_revision TEXT     # revision when this atom was introduced
- created_at TEXT NOT NULL         # ISO timestamp
- updated_at TEXT NOT NULL

### relations
- id TEXT PRIMARY KEY              # SHA256 content-addressed relation_id  
- relation_type TEXT NOT NULL      # IS_A / HAS_PROPERTY / CAUSES / CORRELATED_WITH / PRECEDES / SUPPORTS / CONTRADICTS / SUPERSEDES / UPDATES / REPLACES / DERIVED_FROM / DEPENDS_ON / BELONGS_TO / RELATED_TO / EXAMPLE_OF / PROCEDURE_FOR / EVIDENCE_FOR / UNKNOWN_RELATION
- from_atom_id TEXT NOT NULL       # FK → atoms.id
- to_atom_id TEXT NOT NULL         # FK → atoms.id
- confidence REAL
- context TEXT                     # relationship context/explanation
- privacy_class TEXT
- created_at TEXT NOT NULL

### conflicts
- id TEXT PRIMARY KEY              # conflict_id
- atom_id_a TEXT NOT NULL          # FK → atoms.id
- atom_id_b TEXT NOT NULL          # FK → atoms.id
- conflict_type TEXT               # DIRECT / FRAME / TEMPORAL / SCOPE / TERMINOLOGY
- resolution_status TEXT           # UNRESOLVED / A_WINS / B_WINS / BOTH_PARTIAL / SUPERSEDED / FALSE_DICHOTOMY
- resolution_note TEXT
- created_at TEXT NOT NULL
- resolved_at TEXT

### unknowns
- id TEXT PRIMARY KEY              # unknown_id
- question TEXT NOT NULL           # the unknown question
- scope TEXT
- raised_by_sources TEXT           # JSON array of source_ids
- related_atom_ids TEXT            # JSON array of atom_ids that reference this unknown
- status TEXT                      # OPEN / PARTIALLY_RESOLVED / RESOLVED / DEPRECATED
- resolution_note TEXT
- created_at TEXT NOT NULL
- resolved_at TEXT

### sources
- id TEXT PRIMARY KEY              # source_id
- source_type TEXT                 # SYNTHETIC / LOCAL_FILE / URL / CONVERSATION / API / IMPORT / USER
- title TEXT
- description TEXT
- location TEXT                    # file path / URL / reference
- content_hash TEXT                # SHA256 of source content
- ingested_at TEXT NOT NULL

### packets
- id TEXT PRIMARY KEY              # packet_semantic_id
- instance_id TEXT UNIQUE          # per-run unique id
- content_hash TEXT                # SHA256 of packet content
- source_id TEXT                   # FK → sources.id
- processor_version TEXT
- authority_level TEXT             # CANDIDATE_ONLY / APPROVED / AUTHORITY
- packet_status TEXT               # VALID / CORRUPT / DEPRECATED
- ingested_at TEXT NOT NULL
- json_blob TEXT                   # full original packet JSON

### packet_atoms (junction)
- packet_id TEXT NOT NULL
- atom_id TEXT NOT NULL
- PRIMARY KEY (packet_id, atom_id)

### packet_relations (junction)
- packet_id TEXT NOT NULL
- relation_id TEXT NOT NULL
- PRIMARY KEY (packet_id, relation_id)

### revisions
- revision_id TEXT PRIMARY KEY     # memory_revision hash
- parent_revision_id TEXT          # FK → revisions.revision_id
- packet_set_hash TEXT             # SHA256 of ordered packet IDs
- created_at TEXT NOT NULL
- snapshot_manifest TEXT           # JSON summary of contents

### audit_events
- id INTEGER PRIMARY KEY AUTOINCREMENT
- event_type TEXT NOT NULL         # INGEST / MERGE / CONFLICT / CORRECTION / ROLLBACK / SNAPSHOT / VERIFY
- revision_id TEXT                 # FK → revisions.revision_id
- packet_id TEXT
- atom_id TEXT
- detail TEXT                      # event detail
- timestamp TEXT NOT NULL

### skill_structures
- id TEXT PRIMARY KEY
- name TEXT NOT NULL
- type TEXT                        # SKILL / STRUCTURE
- content TEXT                     # full skill/structure body
- related_atom_ids TEXT            # JSON array
- packet_id TEXT
- created_at TEXT NOT NULL

### retrieval_terms (FTS index)
- atom_id TEXT NOT NULL            # FK → atoms.id
- term TEXT NOT NULL               # tokenized term
- weight REAL DEFAULT 1.0
- PRIMARY KEY (atom_id, term)

### credential_refs
- id TEXT PRIMARY KEY
- purpose TEXT NOT NULL            # what the credential is for
- system TEXT NOT NULL             # which system
- local_location TEXT NOT NULL     # where to find on disk
- checksum TEXT                    # SHA256 of credential content
- rotation_rule TEXT               # how often / how to rotate
- last_rotated TEXT
- valid_until TEXT
- related_atom_ids TEXT            # JSON array of atoms that depend on this credential
- created_at TEXT NOT NULL

## ── Indices ──

CREATE INDEX idx_atoms_type ON atoms(atom_type);
CREATE INDEX idx_atoms_scope ON atoms(scope);
CREATE INDEX idx_atoms_confidence ON atoms(confidence);
CREATE INDEX idx_atoms_privacy ON atoms(privacy_class);
CREATE INDEX idx_atoms_verification ON atoms(verification_status);
CREATE INDEX idx_atoms_created ON atoms(created_at);
CREATE INDEX idx_relations_from ON relations(from_atom_id);
CREATE INDEX idx_relations_to ON relations(to_atom_id);
CREATE INDEX idx_relations_type ON relations(relation_type);
CREATE INDEX idx_conflicts_status ON conflicts(resolution_status);
CREATE INDEX idx_unknowns_status ON unknowns(status);
CREATE INDEX idx_packets_ingested ON packets(ingested_at);
CREATE INDEX idx_packet_atoms_atom ON packet_atoms(atom_id);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp);
CREATE VIRTUAL TABLE retrieval_fts USING fts5(term, atom_id, weight);

## ── 4-Axis Independence ──
#
# knowledge_status:   NEW / VERIFIED / DISPUTED / OUTDATED / SUPERSEDED / REPLACED / UNRESOLVED
# gpt_access:         FULL_SEMANTIC_ACCESS (default per user directive)
# transport_visibility: LOCAL / PRIVATE_REPO / PUBLIC_REPO / PACKAGE_ONLY
# authority_level:    CANDIDATE_ONLY / APPROVED / AUTHORITY
#
# These are SET SEPARATELY. A RESTRICTED atom can still have FULL_SEMANTIC_ACCESS
# if locally stored. AUTHORITY atoms can still be marked LOCAL for transport.
