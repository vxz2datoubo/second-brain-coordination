"""E52 strict-byte production implementation.

This namespace is independent from the frozen E40 candidate namespace.
"""

from .index import ByteTruthIndex, Chunk, LineRecord, ScannerProgressError

__all__ = ["ByteTruthIndex", "Chunk", "LineRecord", "ScannerProgressError"]
