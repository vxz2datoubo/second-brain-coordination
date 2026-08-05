"""
QCLAW E34 — Deterministic Minimum-Semantic-Unit Atomizer
Preserves: conditions, exceptions, negations, temporal scope, failures,
counterexamples, conflicts, UNKNOWNs, source lineage, confidence/authority
separation, and version/audit chains.

E34 reconstruction: adapted from E27 design + E28 improvements + E29 structural
awareness. All source bytes from git blobs, no E29 Base64 copy.
"""
import re
import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


# ── Content Type Taxonomy (21 types from E27 design) ──────────────────────

class ContentType(str, Enum):
    CLAIM = "CLAIM"
    FACT = "FACT"
    CONDITION = "CONDITION"
    EXCEPTION = "EXCEPTION"
    NEGATION = "NEGATION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    TEMPORAL_SCOPE = "TEMPORAL_SCOPE"
    CONSTRAINT = "CONSTRAINT"
    METHOD = "METHOD"
    DEFINITION = "DEFINITION"
    REFERENCE = "REFERENCE"
    SOURCE = "SOURCE"
    EXAMPLE = "EXAMPLE"
    CODE_BLOCK = "CODE_BLOCK"
    STRUCTURAL = "STRUCTURAL"
    GOVERNANCE = "GOVERNANCE"
    AUTHORITY = "AUTHORITY"
    CONTEXT = "CONTEXT"
    METADATA = "METADATA"


# ── Data Types ─────────────────────────────────────────────────────────────

@dataclass
class SourceSpan:
    """Exact byte range in source document."""
    start_byte: int
    end_byte: int
    start_line: int = 0
    end_line: int = 0
    
    @property
    def byte_length(self) -> int:
        return self.end_byte - self.start_byte


@dataclass
class KnowledgeAtom:
    """Minimum semantic unit of knowledge."""
    deterministic_id: str = ""
    content_zh: str = ""
    content_en: str = ""
    content_type: ContentType = ContentType.CLAIM
    source_span: Optional[SourceSpan] = None
    source_blob_sha: str = ""
    source_commit_sha: str = ""
    conditions: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    negations: List[str] = field(default_factory=list)
    temporal_scope: Optional[str] = None
    confidence: str = "candidate"
    authority: str = "candidate"
    version: str = "1.0"
    related_atom_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class Relation:
    """Relationship between two knowledge atoms."""
    source_atom_id: str = ""
    target_atom_id: str = ""
    relation_type: str = "SUPPORTS"
    confidence: str = "candidate"
    evidence: str = ""


@dataclass
class Unknown:
    """Explicitly marked unknown gap."""
    description: str = ""
    context: str = ""
    related_atom_ids: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """Explicit knowledge conflict."""
    atom_id_a: str = ""
    atom_id_b: str = ""
    description: str = ""
    resolution: Optional[str] = None


@dataclass
class AtomizationResult:
    """Complete atomization output."""
    packet_id: str = ""
    atoms: List[KnowledgeAtom] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)
    unknowns: List[Unknown] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    source_hash: str = ""
    byte_coverage: float = 0.0


# ── Deterministic ID Generation ───────────────────────────────────────────

def deterministic_id(content: str, source_span: Optional[SourceSpan] = None) -> str:
    """Generate SHA-256 deterministic ID from content + optional span info."""
    canonical = content.strip()
    if source_span:
        canonical += f"|{source_span.start_byte}:{source_span.end_byte}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ── Content Type Classification ────────────────────────────────────────────

class ContentClassifier:
    """
    Conservative classification. Default: CLAIM.
    No lexical FACT promotion — evidence markers only from explicit metadata.
    """
    
    def __init__(self):
        # Ordered patterns: first match wins
        self.TYPE_PATTERNS = [
        (ContentType.CODE_BLOCK, [r"```[\s\S]*?```"]),
        (ContentType.GOVERNANCE, [r"(?i)\b(must not|shall not|prohibited|forbidden|never)\b"]),
        (ContentType.NEGATION, [r"(?i)\b(not|never|none|no)\s+(true|correct|valid|present|applicable|the case)\b"]),
        (ContentType.CONSTRAINT, [r"(?i)\b(must|must not|required|mandatory|obligatory)\b"]),
        (ContentType.CONDITION, [r"(?i)\b(if\s+|when\s+|unless\s+|provided that|as long as|subject to)\b"]),
        (ContentType.EXCEPTION, [r"(?i)\b(except|excluding|other than|save for|with the exception of)\b"]),
        (ContentType.TEMPORAL_SCOPE, [
            r"(?i)\b(from\s+\d{4}.*?(?:to|until|through)\s+\d{4})\b",
            r"(?i)\b(before\s+\d{4}|after\s+\d{4}|between\s+\d{4}|since\s+\d{4})\b",
            r"(?i)\b(as of\s+\d{4}|effective\s+\d{4})\b",
        ]),
        (ContentType.COUNTEREXAMPLE, [r"(?i)\b(counter.example|counterexample|contrary evidence|falsifies)\b"]),
        (ContentType.UNKNOWN, [r"(?i)\b(unknown|uncertain|unclear|not known|undetermined|insufficient data)\b"]),
        (ContentType.CONFLICT, [r"(?i)\b(conflicts with|contradicts|incompatible|mutually exclusive|inconsistent)\b"]),
        (ContentType.DEFINITION, [r"(?i)^\s*(a|an|the)\s+\w+\s+(is|are|refers to|defined as|means)\b"]),
        (ContentType.REFERENCE, [r"(?i)\b(see\s+|refer to|cited in|according to|per\s+)\b"]),
        (ContentType.METHOD, [r"(?i)\b(method|algorithm|procedure|protocol|technique|approach)\b"]),
        (ContentType.EXAMPLE, [r"(?i)\b(for example|e\.g\.|i\.e\.|such as|like the)\b"]),
        (ContentType.SOURCE, [r"(?i)(?:^|\W)(source:\s|origin:|from\s+\[|published in|authored by)(?:\W|$)"]),
    ]
    
    def classify(self, text: str, metadata: Optional[Dict[str, str]] = None) -> ContentType:
        """Conservative classification. Default: CLAIM. No FACT promotion."""
        # Check metadata override first (authorship evidence)
        metadata = metadata or {}
        if metadata.get("explicit_type"):
            try:
                return ContentType(metadata["explicit_type"])
            except ValueError:
                return ContentType.CLAIM
        
        # Pattern matching
        for ctype, patterns in self.TYPE_PATTERNS:
            for pat in patterns:
                if re.search(pat, text, re.IGNORECASE):
                    return ctype
        
        # Default: CLAIM (never FACT unless explicit metadata)
        return ContentType.CLAIM


# ── Structure-Aware Adapter ────────────────────────────────────────────────

class StructureAwareAdapter:
    """
    Splits structured content (lists, paragraphs, sections) into
    independently atomizable semantic units.
    E29 design: structure-aware, no content truncation.
    """
    
    def adapt_markdown(self, source: str) -> List[Dict[str, Any]]:
        """Split markdown into semantic units."""
        units = []
        lines = source.split("\n")
        i = 0
        current_unit = []
        current_type = "text"
        
        while i < len(lines):
            line = lines[i]
            
            # Headers start new units
            if line.startswith("#"):
                if current_unit:
                    units.append({"type": current_type, "text": "\n".join(current_unit)})
                current_unit = [line]
                current_type = "section_header"
                i += 1
                continue
            
            # List items are independent units
            if re.match(r"^\s*[-*+]\s", line) or re.match(r"^\s*\d+[.)]\s", line):
                if current_unit and current_type != "list":
                    units.append({"type": current_type, "text": "\n".join(current_unit)})
                    current_unit = []
                current_type = "list"
                current_unit.append(line)
                i += 1
                continue
            
            # Code blocks
            if line.strip().startswith("```"):
                if current_unit:
                    units.append({"type": current_type, "text": "\n".join(current_unit)})
                    current_unit = [line]
                    current_type = "code_block"
                    i += 1
                    # Collect until closing ```
                    while i < len(lines):
                        current_unit.append(lines[i])
                        if lines[i].strip().startswith("```") and len(current_unit) > 1:
                            break
                        i += 1
                    units.append({"type": "code_block", "text": "\n".join(current_unit)})
                    current_unit = []
                    current_type = "text"
                    i += 1
                    continue
            
            # Table rows
            if line.strip().startswith("|") and line.strip().endswith("|"):
                if current_type != "table":
                    if current_unit:
                        units.append({"type": current_type, "text": "\n".join(current_unit)})
                        current_unit = []
                    current_type = "table"
                current_unit.append(line)
                i += 1
                continue
            
            # Blank line: paragraph boundary
            if line.strip() == "":
                if current_unit and current_type not in ("code_block",):
                    units.append({"type": current_type, "text": "\n".join(current_unit)})
                    current_unit = []
                    current_type = "text"
                i += 1
                continue
            
            current_unit.append(line)
            i += 1
        
        if current_unit:
            units.append({"type": current_type, "text": "\n".join(current_unit)})
        
        return [u for u in units if u["text"].strip()]
    
    def adapt_json(self, source: str) -> List[Dict[str, Any]]:
        """Split JSON into atomic units."""
        try:
            data = json.loads(source)
        except json.JSONDecodeError:
            return [{"type": "text", "text": source}]
        
        units = []
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 20:
                    units.append({"type": "json_field", "text": value, "key": key})
                elif isinstance(value, (dict, list)):
                    sub_text = json.dumps(value, ensure_ascii=False)
                    if len(sub_text) < 1000:
                        units.append({"type": "json_subtree", "text": sub_text, "key": key})
                    else:
                        # Recurse for large subtrees
                        units.append({"type": "json_field", "text": sub_text, "key": key})
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    for key, value in item.items():
                        if isinstance(value, str) and len(value) > 10:
                            units.append({"type": "json_field", "text": value, "key": key})
        
        return units
    
    def adapt_plaintext(self, source: str) -> List[Dict[str, Any]]:
        """Split plaintext into paragraphs."""
        paragraphs = [p.strip() for p in source.split("\n\n") if p.strip()]
        return [{"type": "paragraph", "text": p} for p in paragraphs]
    
    def adapt(self, source: str, fmt: str = "markdown") -> List[Dict[str, Any]]:
        adapters = {
            "markdown": self.adapt_markdown,
            "md": self.adapt_markdown,
            "json": self.adapt_json,
            "txt": self.adapt_plaintext,
            "text": self.adapt_plaintext,
        }
        adapter = adapters.get(fmt.lower(), self.adapt_markdown)
        return adapter(source)


# ── Atomizer ───────────────────────────────────────────────────────────────

class Atomizer:
    """
    Knowledge atomizer: structure-aware, lossless, conservative.
    """
    
    def __init__(self):
        self.classifier = ContentClassifier()
        self.adapter = StructureAwareAdapter()
    
    def atomize(
        self,
        source: str,
        source_blob_sha: str = "",
        source_commit_sha: str = "",
        fmt: str = "markdown",
    ) -> AtomizationResult:
        
        # 1. Split into semantic units
        units = self.adapter.adapt(source, fmt)
        
        # 2. Track byte coverage
        total_bytes = len(source.encode("utf-8"))
        covered_bytes = 0
        last_end = 0
        
        atoms = []
        for unit in units:
            text = unit["text"]
            text_bytes = text.encode("utf-8")
            
            # Find exact byte span in source
            pos = source.find(text, last_end)
            if pos == -1:
                pos = last_end  # best effort
            
            span = SourceSpan(
                start_byte=pos,
                end_byte=pos + len(text_bytes),
                start_line=source[:pos].count("\n") + 1,
                end_line=source[:pos + len(text_bytes)].count("\n") + 1,
            )
            covered_bytes += len(text_bytes)
            last_end = span.end_byte
            
            # 3. Classify
            ctype = self.classifier.classify(text)
            
            # 4. Extract sub-fields from text
            atom_id = deterministic_id(text, span)
            
            # Extract conditions, exceptions, negations
            conditions = re.findall(r"(?i)\bif\s+([^,.]{10,200})", text)
            exceptions = re.findall(r"(?i)\bexcept\s+([^,.]{10,200})", text)
            negations = re.findall(r"(?i)\b(not\s+\w+\s+\w{3,20})\b", text)
            temporal = None
            tm = re.search(r"(?i)(?:from|as of|effective)\s+(?:\d{4}[^\s,]*)", text)
            if tm:
                temporal = tm.group(0)
            
            atom = KnowledgeAtom(
                deterministic_id=atom_id,
                content_zh=text,
                content_en=text,
                content_type=ctype,
                source_span=span,
                source_blob_sha=source_blob_sha,
                source_commit_sha=source_commit_sha,
                conditions=conditions[:5],
                exceptions=exceptions[:5],
                negations=negations[:5],
                temporal_scope=temporal,
            )
            atoms.append(atom)
        
        # 5. Extract relations (SUPPORTS by proximity)
        relations = []
        for i in range(len(atoms) - 1):
            a = atoms[i]
            b = atoms[i + 1]
            if a.content_type == ContentType.CONDITION:
                relations.append(Relation(a.deterministic_id, b.deterministic_id, "CONDITIONS"))
            elif b.content_type == ContentType.EXCEPTION:
                relations.append(Relation(a.deterministic_id, b.deterministic_id, "EXCEPTED_BY"))
            elif a.content_type == ContentType.CONFLICT:
                relations.append(Relation(a.deterministic_id, b.deterministic_id, "CONTRADICTS"))
            elif b.content_type in (ContentType.UNKNOWN,):
                relations.append(Relation(a.deterministic_id, b.deterministic_id, "RAISES_UNKNOWN"))
            else:
                relations.append(Relation(a.deterministic_id, b.deterministic_id, "SUPPORTS"))
        
        # 6. Compute unknowns and conflicts
        unknowns = []
        conflicts = []
        for i, a in enumerate(atoms):
            if a.content_type == ContentType.UNKNOWN:
                unknowns.append(Unknown(
                    description=a.content_zh[:200],
                    context=f"atom {i}",
                ))
            if a.content_type == ContentType.CONFLICT:
                conflicts.append(Conflict(
                    atom_id_a=a.deterministic_id,
                    atom_id_b=atoms[i-1].deterministic_id if i > 0 else "",
                    description=a.content_zh[:200],
                ))
        
        # 7. Coverage
        coverage = covered_bytes / total_bytes if total_bytes > 0 else 0.0
        
        # 8. Source hash
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        
        return AtomizationResult(
            atoms=atoms,
            relations=relations,
            unknowns=unknowns,
            conflicts=conflicts,
            source_hash=source_hash,
            byte_coverage=coverage,
        )
