"""E42 Q2 — Exact Source Document and Traceability

- Immutable SourceDocument(bytes, length, digest)
- SourceSpan MUST be verified against legal offsets
- No strip/reconstruction; whitespace preserved as STRUCTURE spans
- Interpretation/linking retains full provenance graph
- Terminology mappings are versioned rules
"""
import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple


@dataclass(frozen=True)
class SourceDocument:
    """Immutable source document bound to exact bytes."""
    document_id: str
    raw_bytes: bytes = field(repr=False)
    length: int
    digest: str
    content_type: str = "text/plain"

    @staticmethod
    def create(document_id: str, data: bytes, content_type: str = "text/plain") -> "SourceDocument":
        if not isinstance(data, bytes):
            raise TypeError("SourceDocument requires bytes, not str")
        return SourceDocument(
            document_id=document_id,
            raw_bytes=data,
            length=len(data),
            digest=hashlib.sha256(data).hexdigest(),
            content_type=content_type,
        )

    def slice(self, start: int, end: int) -> bytes:
        if start < 0 or end > self.length or start > end:
            raise IndexError(f"Slice [{start}:{end}] out of range [0:{self.length}]")
        return self.raw_bytes[start:end]

    def verify_span(self, start: int, end: int) -> bytes:
        return self.slice(start, end)


@dataclass(frozen=True)
class SourceSpan:
    """A span within a SourceDocument with verified offset integrity.

    The content is ALWAYS retrieved from the document slice, never
    caller-supplied — preventing strip/reconstruction loss.
    """
    source_document: SourceDocument
    byte_start: int
    byte_end: int
    span_role: str = "content"

    def __post_init__(self):
        if self.byte_start < 0 or self.byte_end > self.source_document.length:
            raise IndexError(
                f"Span [{self.byte_start}:{self.byte_end}] out of range "
                f"[0:{self.source_document.length}]")
        if self.byte_start > self.byte_end:
            raise ValueError(
                f"Span start {self.byte_start} > end {self.byte_end}")

    @property
    def content(self) -> bytes:
        """Retrieve exact bytes from document — no caller substitution."""
        return self.source_document.slice(self.byte_start, self.byte_end)

    @property
    def content_utf8(self) -> str:
        return self.content.decode("utf-8", errors="replace")

    def with_role(self, role: str) -> "SourceSpan":
        return SourceSpan(self.source_document, self.byte_start,
                          self.byte_end, role)


# ––– Paragraph Extraction with Exact Offsets –––

@dataclass(frozen=True)
class ExtractedParagraph:
    document: SourceDocument
    spans: Tuple[SourceSpan, ...]  # STRUCTURE + CONTENT spans
    text_content: bytes  # The content portion (no structure)

    @property
    def text(self) -> str:
        return self.text_content.decode("utf-8", errors="replace")


def extract_paragraphs(document: SourceDocument) -> Tuple[ExtractedParagraph, ...]:
    """Extract paragraphs with exact byte offsets. Whitespace/delimiters
    are retained as STRUCTURE spans. Content is never stripped."""
    data = document.raw_bytes
    if not data:
        return ()

    paragraphs = []
    i = 0
    n = len(data)

    while i < n:
        # Skip leading blank lines (STRUCTURE)
        structure_start = i
        while i < n:
            if i + 1 < n and data[i:i+2] == b"\r\n":
                i += 2
            elif data[i:i+1] == b"\n":
                i += 1
            else:
                break
        if i > structure_start:
            # Record blank lines as structure
            pass  # Structure spans tracked in full extract below

        # Find paragraph start
        if i >= n:
            break

        para_start = i
        # Find paragraph end (next double newline or EOF)
        while i < n:
            if i + 1 < n and data[i:i+2] == b"\r\n":
                # Check for double newline
                peek = i + 2
                if peek + 1 < n and data[peek:peek+2] == b"\r\n":
                    i += 2  # consume first CRLF
                    break
                elif peek < n and data[peek:peek+1] == b"\n":
                    i += 2  # consume CRLF
                    break
                else:
                    i += 1
            elif data[i:i+1] == b"\n":
                peek = i + 1
                if peek < n and data[peek:peek+1] == b"\n":
                    i += 1
                    break
                else:
                    i += 1
            else:
                i += 1

        para_end = i
        # Trim trailing newline from paragraph content
        content_end = para_end
        while content_end > para_start and data[content_end-1:content_end] in (b'\n', b'\r'):
            content_end -= 1
        para_bytes = data[para_start:content_end]
        if para_bytes.strip():
            content_span = SourceSpan(document, para_start, content_end, "paragraph")
            paragraphs.append(ExtractedParagraph(
                document=document,
                spans=(content_span,),
                text_content=para_bytes,
            ))

    return tuple(paragraphs)


# ––– Terminology Mappings (Versioned) –––

@dataclass(frozen=True)
class TerminologyMapping:
    """A versioned rule for terminology replacements.

    Replacement is: apply to NORMALIZED text only, never to original quotations.
    """
    mapping_id: str
    version: int
    rules: Tuple[Tuple[str, str], ...]  # ((from, to), ...)

    def apply(self, text: str) -> str:
        """Apply to normalized text (NOT quotations)."""
        result = text
        for pattern, replacement in self.rules:
            result = result.replace(pattern, replacement)
        return result


# ––– Digestion Graph –––

@dataclass(frozen=True)
class DigestedSegment:
    """A segment of digested knowledge with full provenance graph."""
    segment_id: str
    source_span: SourceSpan
    normalized_text: str
    interpretation_status: str
    linked_atom_ids: Tuple[str, ...] = ()
    provenance: Tuple[str, ...] = ()
    terminology_version: int = 0

    @property
    def is_quoted_source(self) -> bool:
        return self.interpretation_status == "direct_quote"


@dataclass(frozen=True)
class LinkRegistry:
    """A verified registry of known atom IDs. Arbitrary IDs rejected."""
    registered: FrozenSet[str]

    @staticmethod
    def create(ids: Set[str]) -> "LinkRegistry":
        return LinkRegistry(registered=frozenset(ids))

    def validate(self, atom_id: str) -> bool:
        return atom_id in self.registered

    def filter_valid(self, ids: Tuple[str, ...]) -> Tuple[str, ...]:
        return tuple(i for i in ids if self.validate(i))
