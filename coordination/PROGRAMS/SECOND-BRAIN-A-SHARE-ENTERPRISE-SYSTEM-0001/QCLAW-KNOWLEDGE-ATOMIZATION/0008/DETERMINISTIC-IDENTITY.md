# ============================================================================
# DETERMINISTIC IDENTITY — Content-Addressable Knowledge Identifiers
# Program: SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001
# Task:    QCLAW-KNOWLEDGE-ATOMIZATION-DIGESTION-0008
# Version: 1.0.0
# ============================================================================

## Core Principle

Every knowledge entity in the QCLAW system has a **deterministic, content-addressed
identifier** generated from its semantic content using SHA-256. Same semantic input
always produces the same identifier. This enables:

- **Rebuild verification**: Re-running the atomization pipeline on the same source
  produces byte-for-byte identical output
- **Cross-agent deduplication**: Two different agents cannot create conflicting IDs
  for the same knowledge
- **Merge safety**: When two packets are merged, identical-content atoms share IDs
- **Audit trail integrity**: ID can be recomputed to verify content hasn't been tampered

## Hash Algorithm

| Parameter | Value |
|---|---|
| Algorithm | SHA-256 |
| Output encoding | Hexadecimal (lowercase) |
| ID prefix | Entity-type prefix followed by `-` |
| ID suffix length | First 8 characters of hex digest (for atoms), 8 for others |
| Collision strategy | See "Collision Handling" section below |

## Entity Identifier Schemes

### 1. KnowledgeAtom ID

```
atom_id = "AT-" + SHA256(canonical_statement ∥ scope ∥ time_scope_valid_from)[:8]
```

**Hash input construction:**
1. Apply Unicode normalization (NFKC) to `canonical_statement`
2. Apply Unicode normalization (NFKC) to `scope`
3. Apply Unicode normalization (NFKC) to `time_scope.valid_from` (ISO-8601 format, or empty string)
4. Concatenate with single newline (`\n`) separator: `NFKC(canonical_statement) + "\n" + NFKC(scope) + "\n" + NFKC(time_scope.valid_from)`
5. Remove leading/trailing whitespace from each component before NFKC
6. Compute SHA-256 of the UTF-8 encoded concatenation
7. Take first 8 hex characters, uppercase

**Example:**
```
canonical_statement: "The system supports Markdown, TXT, JSON, JSONL, and YAML formats for knowledge source ingestion."
scope: "QCLAW knowledge atomization"
time_scope.valid_from: "2026-07-22T00:00:00Z"

Hash input: "The system supports Markdown, TXT, JSON, JSONL, and YAML formats for knowledge source ingestion.\nQCLAW knowledge atomization\n2026-07-22T00:00:00Z"

atom_id: "AT-A7F3B92C"
```

**What's included in hash:**
- ✅ `canonical_statement` — the core semantic content
- ✅ `scope` — the domain/context where this atom applies
- ✅ `time_scope.valid_from` — temporal origin; atoms from different time periods with identical text are different atoms

**What's EXCLUDED from hash:**
- ❌ `created_at`, `updated_at` — wall-clock timestamps are non-deterministic
- ❌ `atom_id` itself — can't include your own hash (circular)
- ❌ `title` — human-readable label, not semantic content
- ❌ `tags` — categorization, not semantics
- ❌ `confidence`, `confidence_basis` — metadata about the atom, not the atom itself
- ❌ `knowledge_status`, `authority_level` — lifecycle/metadata fields
- ❌ `digest_run_id`, `extraction_decision_id` — process metadata
- ❌ `sources[].access_timestamp` — non-deterministic
- ❌ `version` — versioning metadata, not content
- ❌ Any field added after v1.0.0 (unless schema version is bumped)

### 2. KnowledgeRelation ID

```
relation_id = "REL-" + SHA256(source_atom_id ∥ target_atom_id ∥ relation_type)[:8]
```

**Hash input construction:**
1. Uppercase `source_atom_id` (already canonical form)
2. Uppercase `target_atom_id` (already canonical form)
3. Uppercase `relation_type`
4. Concatenate: `source_atom_id + "\n" + target_atom_id + "\n" + relation_type`
5. Compute SHA-256
6. Take first 8 hex characters, uppercase

**Design decision:** The relation ID derives from its endpoints + type, not from
any description or metadata. This ensures that two relations with the same type
between the same atoms always have the same ID, regardless of which digest run
or agent creates them.

**Example:**
```
source_atom_id: "AT-A7F3B92C"
target_atom_id: "AT-B2E1D405"
relation_type: "SUPPORTS"

Hash input: "AT-A7F3B92C\nAT-B2E1D405\nSUPPORTS"
relation_id: "REL-C082F3A1"
```

### 3. KnowledgeConflict ID

```
conflict_id = "CNF-" + SHA256(atom_id_a ∥ atom_id_b ∥ conflict_type)[:8]
```

**Hash input construction:**
1. Sort `atom_id_a` and `atom_id_b` alphabetically (to ensure A-B and B-A produce same ID)
2. Concatenate: `sorted_atom_id_a + "\n" + sorted_atom_id_b + "\n" + conflict_type`
3. Compute SHA-256
4. Take first 8 hex characters, uppercase

**Sorting rule:**
- Conflicts are inherently unordered between two atoms
- By sorting IDs alphabetically, we guarantee that `CONTRADICTS(A, B)` and
  `CONTRADICTS(B, A)` produce the same `conflict_id`
- This prevents duplicate conflicts for the same pair

### 4. KnowledgeUnknown ID

```
unknown_id = "UNK-" + SHA256(question)[:8]
```

**Hash input construction:**
1. Apply Unicode normalization (NFKC) to `question`
2. Trim leading/trailing whitespace
3. Compute SHA-256 of NFKC(question) as UTF-8
4. Take first 8 hex characters, uppercase

**Design note:** Only the question text is used. This means the same question
raised in two different contexts will have the same `unknown_id`. This is
intentional — it deduplicates unknowns across sources.

### 5. KnowledgeSource Manifest ID

```
source_id = "SRC-" + SHA256(source_location)[:8]
```

**Hash input construction:**
1. For file sources: use the relative path from the program root
2. For URLs: use the full canonical URL (stripped of fragments `#`)
3. For issue/PR references: use `owner/repo#number` format
4. Apply Unicode normalization (NFKC)
5. Compute SHA-256
6. Take first 8 hex characters, uppercase

### 6. Digest Run ID

```
digest_run_id = "DIG-" + SHA256(batch_source_ids_concatenated ∥ YYYY-MM-DD)[:8]
```

**Hash input construction:**
1. Sort all `source_id` values in the batch alphabetically
2. Concatenate with `,` separator
3. Append `\n` + date in `YYYY-MM-DD` format
4. Compute SHA-256
5. Take first 8 hex characters, uppercase

**Design decision:** Including the date ensures different runs on different days
produce different IDs even with same sources (because sources may have been updated).

### 7. LearningPacket Hash

```
packet_hash = SHA256(canonical_packet_content)
```

**Canonical content construction:**
1. Build a JSON object with ONLY the deterministic fields:
   - `packet_id`, `version`, `label`, `parent_program`, `task_id`
   - `atoms` array: each atom with ONLY hash-input fields (canonical_statement, scope, time_scope)
   - `relations` array: each relation with ONLY hash-input fields (source_atom_id, target_atom_id, relation_type)
   - `conflicts` array: each conflict with ONLY hash-input fields (atom_id_a, atom_id_b, conflict_type)
   - `unknowns` array: each unknown with ONLY hash-input fields (question)
   - `sources` array: each source with ONLY source_location
2. Sort all arrays by their deterministic IDs
3. Sort all JSON object keys alphabetically
4. Serialize as compact JSON (no pretty-printing, no indentation)
5. Compute SHA-256 of UTF-8 serialization

**EXCLUDED from packet_hash:**
- ❌ `created_at`, `updated_at` on any object
- ❌ `digest_run_id`, `run_duration_ms`, `host_name`
- ❌ Quality gate report (process metadata)
- ❌ Statistics (derived from content, not content itself)
- ❌ Atomization decisions (process metadata)

## Canonicalization Rules

### Unicode Normalization
- **Standard:** NFKC (Normalization Form Compatibility Composition)
- **Rationale:** NFKC handles the broadest range of equivalence issues:
  - Fullwidth/halfwidth character equivalence (e.g., `Ａ` → `A`)
  - Ligature decomposition (e.g., `ﬁ` → `fi`)
  - Superscript/subscript normalization (e.g., `²` → `2`)
  - Compatibility character decomposition
- **Why not NFC?** NFC preserves compatibility characters, which could produce
  different hashes for visually/functionally identical text from different sources.
- **Why not NFD?** NFD (decomposed) produces longer strings; NFKC (composed) is
  more compact and widely supported.

### Whitespace Normalization
1. Trim leading whitespace from each component before concatenation
2. Trim trailing whitespace from each component before concatenation
3. Internal whitespace is PRESERVED (do NOT collapse multiple spaces)
4. Line endings are normalized to `\n` (Unix) before hashing
5. Do NOT strip internal newlines — they carry semantic meaning (list items, paragraph breaks)

### Field Ordering
- The order of fields in the hash input is FIXED and documented above
- Arrays within a field (e.g., multiple sources) are:
  1. Sorted by their deterministic ID
  2. Each element contributes to hash separately in sorted order

### JSON Serialization for Packet Hash
- Keys sorted alphabetically (stable sort)
- No trailing commas
- Unicode characters preserved as-is (not escaped)
- Numbers serialized as JSON numbers (no leading zeros)
- Booleans as `true`/`false` (lowercase)
- Null as `null`

## Versioning of the Hashing Scheme

The hashing scheme itself is versioned:

```
hash_scheme_version: "1.0.0"
```

**Versioning policy:**
- **PATCH bump** (1.0.x): Bug fix that doesn't change hash output for valid inputs
  (e.g., documentation fix)
- **MINOR bump** (1.x.0): Backward-compatible change; old hashes still valid,
  new fields added to hash input for new atoms only
- **MAJOR bump** (x.0.0): Hash output changes for same input; all IDs must be
  regenerated; all LearningPacket hashes will change

**When a major version change occurs:**
1. All existing atoms are marked `knowledge_status: superseded`
2. New atoms with new hash scheme IDs are generated
3. `SUPERSEDES` relations link old → new atoms
4. The version chain preserves history

## Collision Handling Policy

### Probability Context
With SHA-256 truncated to 8 hex characters (32 bits), the birthday problem gives:
- 50% collision probability at ~77,000 atoms
- 1% collision probability at ~9,300 atoms
- 0.1% collision probability at ~2,900 atoms

### Detection Strategy
- **Proactive:** During atom creation, check for existing atom with same ID
- **Reactive:** Quality gate QG-ATOM-010 detects identical canonical_statements
  (which would produce identical atom_ids)

### Response to Collision
If two semantically different atoms produce the same 8-char ID:

1. **Do NOT discard either atom** — both are valid knowledge
2. **Expand ID suffix:** Use 12 hex characters instead of 8 for the colliding atoms
   - `AT-A7F3B92C` → `AT-A7F3B92CE1D2`
   - Document the collision in `AtomizationDecision`
3. **Update relations:** Any relation referencing the original 8-char ID must be
   updated to the 12-char ID
4. **Bump schema:** If collisions become common (>0.1% of atoms), bump the hashing
   scheme major version and move to 12-char IDs by default

### Trigger for Scheme Change
If more than 1 in 1,000 atoms experience an 8-char collision, bump `hash_scheme_version`
to 2.0.0 and use 12 characters globally.

## Reference Implementation (Pseudocode)

```python
import hashlib
import unicodedata

def canonicalize(text: str) -> str:
    """Apply Unicode NFKC normalization and trim whitespace."""
    return unicodedata.normalize('NFKC', text).strip()

def sha256_hex(data: str) -> str:
    """Compute SHA-256 hex digest."""
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def make_atom_id(canonical_statement: str, scope: str, time_scope_valid_from: str) -> str:
    """Generate deterministic KnowledgeAtom ID."""
    components = [
        canonicalize(canonical_statement),
        canonicalize(scope),
        canonicalize(time_scope_valid_from or ""),
    ]
    hash_input = "\n".join(components)
    h = sha256_hex(hash_input)
    return f"AT-{h[:8].upper()}"

def make_relation_id(source_atom_id: str, target_atom_id: str, relation_type: str) -> str:
    """Generate deterministic KnowledgeRelation ID."""
    hash_input = f"{source_atom_id.upper()}\n{target_atom_id.upper()}\n{relation_type.upper()}"
    h = sha256_hex(hash_input)
    return f"REL-{h[:8].upper()}"

def make_conflict_id(atom_id_a: str, atom_id_b: str, conflict_type: str) -> str:
    """Generate deterministic KnowledgeConflict ID (sorts pairwise)."""
    a, b = sorted([atom_id_a.upper(), atom_id_b.upper()])
    hash_input = f"{a}\n{b}\n{conflict_type.upper()}"
    h = sha256_hex(hash_input)
    return f"CNF-{h[:8].upper()}"

def make_unknown_id(question: str) -> str:
    """Generate deterministic KnowledgeUnknown ID."""
    q = canonicalize(question)
    h = sha256_hex(q)
    return f"UNK-{h[:8].upper()}"

def make_source_id(source_location: str) -> str:
    """Generate deterministic KnowledgeSource ID."""
    loc = canonicalize(source_location)
    h = sha256_hex(loc)
    return f"SRC-{h[:8].upper()}"
```

## Testing the Determinism Guarantee

### Test Vector
```
Input:
  canonical_statement: "SHA-256 is used for deterministic atom ID generation."
  scope: "QCLAW architecture"
  time_scope.valid_from: "2026-07-22T00:00:00Z"

Expected atom_id: compute from the algorithm above

Verification:
  1. Run on Linux, macOS, Windows → same atom_id
  2. Run in Python, Node.js, Go → same atom_id (same SHA-256 implementation)
  3. Run 1000 times → same atom_id every time
  4. Re-order sources, change timestamps → same atom_id (those fields excluded)
  5. Change canonical_statement → different atom_id
```

### Determinism Contract
```
Same canonical_statement + same scope + same time_scope.valid_from
+ same hash_scheme_version
→ same atom_id
→ same relation_id (for same atom pairs + same relation_type)
→ same conflict_id (for same atom pairs + same conflict_type)
→ same unknown_id (for same question)
→ same packet_hash (for same content)
```

On ANY platform, ANY language, ANY implementation that follows this specification.

## Schema Compatibility

Atom IDs produced by this scheme:
- Match `pattern: "^AT-[A-Fa-f0-9]{8,12}$"` in KNOWLEDGE-ATOM.schema.json
- Default to 8 characters, extend to 12 on collision
- Are prefix-searchable: `AT-A7F3B92C` can be queried with `AT-A7F3*`

Relation IDs match `pattern: "^REL-[A-Fa-f0-9]{8}$"`
Conflict IDs match `pattern: "^CNF-[A-Fa-f0-9]{8}$"`
Unknown IDs match `pattern: "^UNK-[A-Fa-f0-9]{8}$"`
Source IDs match `pattern: "^SRC-[A-Fa-f0-9]{8}$"`
Digest run IDs match `pattern: "^DIG-[A-Fa-f0-9]{8}$"`
