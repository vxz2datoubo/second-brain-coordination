#!/usr/bin/env python3
"""
QCLAW E28 — Lossless Parser v3
Provably 100% byte accounting. Every source byte is atom or gap.
"""
import re
from dataclasses import dataclass, field
from typing import Optional, Tuple
from pathlib import Path

@dataclass
class SourceSpan:
    start_byte: int
    end_byte: int  # exclusive
    @property
    def length(self) -> int:
        return self.end_byte - self.start_byte

@dataclass
class GapEntry:
    span: SourceSpan
    reason: str
    content: str

@dataclass
class ParseUnit:
    span: SourceSpan
    content: str
    content_type: str
    extra: dict = field(default_factory=dict)

@dataclass
class ParseReport:
    source_bytes: int
    atom_bytes: int
    gap_bytes: int
    coverage_ratio: float
    segments_total: int
    gaps: list = field(default_factory=list)

# ── Core: lossless segmenter with byte accounting ──────────────────────

def parse_lossless(source: str) -> Tuple[list, ParseReport]:
    """
    Parse source into non-overlapping units + gaps.
    100% byte accounting: atoms_bytes + gaps_bytes == source_bytes.
    """
    raw = source.encode("utf-8")
    source_bytes = len(raw)
    units = []
    gaps = []
    
    # Split raw bytes on newline, track byte positions precisely
    lines_bytes = raw.split(b"\n")
    # Recover original line positions
    line_positions = []  # (start_byte, end_byte_inclusive)
    pos = 0
    for lb in lines_bytes:
        end = pos + len(lb)  # end byte of line content (exclusive of \n)
        line_positions.append((pos, end))
        pos = end + 1  # skip the \n
    
    # Now we know where each line starts in bytes. Process semantically.
    i = 0
    while i < len(lines_bytes):
        lb = lines_bytes[i]
        line_str = lb.decode("utf-8", errors="strict")  # fail closed
        stripped = line_str.strip()
        start_byte = line_positions[i][0]
        end_byte_content = line_positions[i][1]
        newline_byte = end_byte_content + 1 if i < len(lines_bytes) - 1 else end_byte_content
        # This line's byte range: start_byte to newline_byte (exclusive)
        line_span = SourceSpan(start_byte=start_byte, end_byte=newline_byte)
        
        # ── Code block detection ──
        if stripped.startswith("```"):
            code_start = start_byte
            code_lines = [line_str]
            i += 1
            # Consume until closing ```
            while i < len(lines_bytes):
                clb = lines_bytes[i]
                cls = clb.decode("utf-8", errors="strict")
                code_lines.append(cls)
                if cls.strip().startswith("```"):
                    i += 1
                    break
                i += 1
            code_end = (line_positions[i-1][1] if i <= len(lines_bytes) else line_positions[-1][1])
            if i < len(lines_bytes):
                code_end = line_positions[i-1][0] + len(lines_bytes[i-1]) + (1 if i-1 < len(lines_bytes)-1 else 0)
            else:
                code_end = source_bytes
            
            code_span = SourceSpan(start_byte=code_start, end_byte=code_end)
            full_code = "\n".join(code_lines)
            units.append(ParseUnit(span=code_span, content=full_code,
                                   content_type="code_block",
                                   extra={"language": stripped[3:].strip() or "text"}))
            continue
        
        # ── Empty line → gap ──
        if not stripped:
            gaps.append(GapEntry(span=line_span, reason="paragraph_boundary",
                                content=line_str))
            i += 1
            continue
        
        # ── Non-empty line: start a paragraph ──
        para_start = start_byte
        para_lines = [line_str]
        i += 1
        
        # Consume continuation lines (non-empty, non-heading, non-fence)
        while i < len(lines_bytes):
            nlb = lines_bytes[i]
            nls = nlb.decode("utf-8", errors="strict")
            nls_stripped = nls.strip()
            if not nls_stripped or nls_stripped.startswith("#") or nls_stripped.startswith("```"):
                break
            para_lines.append(nls)
            i += 1
        
        # Paragraph span
        para_end = (line_positions[i-1][0] + len(lines_bytes[i-1]) + 
                   (1 if i-1 < len(lines_bytes)-1 else 0))
        para_span = SourceSpan(start_byte=para_start, end_byte=para_end)
        content = "\n".join(para_lines).strip()
        
        if content:
            first_line = para_lines[0].strip()
            if first_line.startswith("#"):
                ct = "heading"
                extra = {"level": len(re.match(r'^#+', first_line).group())}
            elif all(l.strip().startswith(("- ", "* ", "+ ")) or not l.strip() 
                     for l in para_lines):
                ct = "list"
                extra = {}
            else:
                ct = "paragraph"
                extra = {}
            units.append(ParseUnit(span=para_span, content=content,
                                   content_type=ct, extra=extra))
    
    # ── Verification ──
    atom_bytes = sum(u.span.length for u in units)
    gap_bytes = sum(g.span.length for g in gaps)
    
    return units, ParseReport(
        source_bytes=source_bytes,
        atom_bytes=atom_bytes,
        gap_bytes=gap_bytes,
        coverage_ratio=(atom_bytes / source_bytes) if source_bytes > 0 else 1.0,
        segments_total=len(units),
        gaps=gaps
    )

# ── UTF-8 validation (fail-closed) ────────────────────────────────────
def validate_utf8(filepath: str) -> Tuple[bool, str, int]:
    path = Path(filepath)
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
        return True, "", 0
    except UnicodeDecodeError as e:
        return False, f"Invalid UTF-8 at byte {e.start}", e.start
    except Exception as e:
        return False, str(e), 0

def read_source(filepath: str) -> Tuple[str, dict]:
    import hashlib
    path = Path(filepath)
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise ValueError(f"FAIL_CLOSED: Invalid UTF-8 at byte {e.start} in {filepath}")
    return text, {
        "file_path": str(path),
        "file_size_bytes": len(raw),
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "encoding": "utf-8",
        "encoding_valid": True
    }

# ── Normalized source ref (no local paths) ─────────────────────────────
def normalize_source_ref(repo_root: str, file_path: str, blob_sha256: str = None) -> dict:
    try:
        rel = str(Path(file_path).relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        rel = Path(file_path).name
    return {
        "repo_relative_path": rel,
        "blob_sha256": blob_sha256 or "",
        "encoding": "utf-8"
    }

# ── Self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [
        ("# H\n\nPara.\n\n```\ncode\n```\n\nEnd.", True),
        ("Short.\nLong text here.\n### Heading\nCode block:\n```\nx\n```", True),
        ("\n\n", True),
        ("", True),
    ]
    all_ok = True
    for i, (text, _) in enumerate(tests):
        units, report = parse_lossless(text)
        atom_bytes = sum(u.span.length for u in units)
        gap_bytes = sum(g.span.length for g in report.gaps)
        ok = (atom_bytes + gap_bytes == report.source_bytes)
        if not ok:
            all_ok = False
            print(f"FAIL [{i}]: atoms={atom_bytes} gaps={gap_bytes} source={report.source_bytes} diff={atom_bytes+gap_bytes-report.source_bytes}")
        else:
            print(f"OK [{i}]: {report.source_bytes}B total = {atom_bytes}B atoms + {gap_bytes}B gaps ({len(units)} units)")
    print(f"\n{'ALL PASSED' if all_ok else 'FAILURES'} — lossless byte accounting: {all_ok}")
