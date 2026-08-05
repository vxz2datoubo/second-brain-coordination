"""E35 S3 — AtomExtractor: 21 content types, classification, byte-span linked atoms."""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from qclaw_byte_atomizer.byte_index import ByteSpan
import hashlib
import json
import re


class ContentType:
    """21 content types. Conservative: default CLAIM, never FACT."""
    CLAIM = "CLAIM"
    DEFINITION = "DEFINITION"
    METHOD = "METHOD"
    CONSTRAINT = "CONSTRAINT"
    CONDITION = "CONDITION"
    EXCEPTION = "EXCEPTION"
    GOVERNANCE = "GOVERNANCE"
    NEGATION = "NEGATION"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    TEMPORAL_SCOPE = "TEMPORAL_SCOPE"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    EXAMPLE = "EXAMPLE"
    REFERENCE = "REFERENCE"
    SOURCE = "SOURCE"
    DEPENDENCY = "DEPENDENCY"
    ASSUMPTION = "ASSUMPTION"
    RISK = "RISK"
    METADATA = "METADATA"
    CODE = "CODE"
    ADAPTIVE = "ADAPTIVE"


TYPE_PATTERNS = [
    (ContentType.GOVERNANCE, re.compile(r'\b(must\s+not|shall\s+not|forbidden|prohibited|MUST\s+NOT|SHALL\s+NOT)\b', re.IGNORECASE)),
    (ContentType.NEGATION, re.compile(r'\b(not\s+true\s+that|does\s+not|is\s+not|cannot|NO_)\b', re.IGNORECASE)),
    (ContentType.CONSTRAINT, re.compile(r'\b(must\s+|shall\s+|required\s+to|MUST\s+|SHALL\s+|validate\s+input)\b', re.IGNORECASE)),
    (ContentType.CONDITION, re.compile(r'\b(if\s+the|when\s+the|provided\s+that|on\s+condition)\b', re.IGNORECASE)),
    (ContentType.EXCEPTION, re.compile(r'\b(except\s+|unless\s+|other than|notwithstanding)\b', re.IGNORECASE)),
    (ContentType.TEMPORAL_SCOPE, re.compile(r'\b(from\s+\d{4}\s+to\s+\d{4}|between\s+\d{4}|during\s+|since\s+\d{4})\b', re.IGNORECASE)),
    (ContentType.COUNTEREXAMPLE, re.compile(r'\b(counterexample|counter-example|falsifying|refutation|gap\s+shows)\b', re.IGNORECASE)),
    (ContentType.UNKNOWN, re.compile(r'\b(unknown|not\s+known|remains\s+unclear|not\s+determined|boundary\s+condition)\b', re.IGNORECASE)),
    (ContentType.CONFLICT, re.compile(r'\b(conflicts?\s+with|contradicts?|incompatible|mutually\s+exclusive)\b', re.IGNORECASE)),
    (ContentType.DEFINITION, re.compile(r'\b(is\s+defined\s+as|means\s+that|refers?\s+to|a\s+\w+\s+is\s+a)\b', re.IGNORECASE)),
    (ContentType.REFERENCE, re.compile(r'\b(see\s+section|refer\s+to|cf\.|as\s+described\s+in|for\s+more\s+information)\b', re.IGNORECASE)),
    (ContentType.METHOD, re.compile(r'\b(algorithm|procedure|process|step|method|computes?|calculates?)\b', re.IGNORECASE)),
    (ContentType.EXAMPLE, re.compile(r'\b(for\s+example|e\.g\.|consider\s+the|illustrates?|instance)\b', re.IGNORECASE)),
    (ContentType.SOURCE, re.compile(r'\b(source|originates?\s+from|derived\s+from|from\s+\[)\b', re.IGNORECASE)),
]


@dataclass
class Atom:
    """A knowledge atom with deterministic ID and byte-span provenance."""
    deterministic_id: str
    content_type: str
    content_zh: str  # Non-truncated semantic content
    byte_span: ByteSpan
    source_blob_sha: Optional[str] = None
    source_commit_sha: Optional[str] = None
    source_blob_path: Optional[str] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "deterministic_id": self.deterministic_id,
            "content_type": self.content_type,
            "content_zh": self.content_zh,
            "byte_span": self.byte_span.to_dict(),
            "source_blob_sha": self.source_blob_sha,
            "source_commit_sha": self.source_commit_sha,
            "source_blob_path": self.source_blob_path,
            "metadata": self.metadata
        }

    def compute_id(self) -> None:
        """Compute deterministic SHA-256 ID from content + type + span."""
        h = hashlib.sha256()
        h.update(self.content_zh.encode("utf-8"))
        h.update(self.content_type.encode("utf-8"))
        h.update(str(self.byte_span.start).encode())
        h.update(str(self.byte_span.end).encode())
        self.deterministic_id = h.hexdigest()


class ContentClassifier:
    """Conservative classifier: default CLAIM, zero FACT promotion."""

    def classify(self, text: str) -> str:
        text_lower = text.lower()
        for ctype, pattern in TYPE_PATTERNS:
            if pattern.search(text):
                return ctype
        return ContentType.CLAIM


class AtomExtractor:
    """Extract atoms from adapted spans with byte-index provenance."""

    def __init__(self, source: str, classifier: ContentClassifier = None):
        self.source = source
        self.classifier = classifier or ContentClassifier()

    def extract_atoms(self, adapted_spans, source_blob_sha=None, source_commit_sha=None, source_blob_path=None) -> List[Atom]:
        """Extract atoms from adapted spans. Skip pure GAP/structure spans."""
        atoms = []
        for span in adapted_spans:
            if span.role == "GAP":
                continue
            text = span.byte_span.text.strip()
            if not text or len(text) < 4:
                continue

            ctype = self.classifier.classify(text)
            atom = Atom(
                deterministic_id="",
                content_type=ctype,
                content_zh=text,
                byte_span=span.byte_span,
                source_blob_sha=source_blob_sha,
                source_commit_sha=source_commit_sha,
                source_blob_path=source_blob_path,
                metadata={"adapter_role": span.role, **(span.metadata or {})}
            )
            atom.compute_id()
            atoms.append(atom)
        return atoms
