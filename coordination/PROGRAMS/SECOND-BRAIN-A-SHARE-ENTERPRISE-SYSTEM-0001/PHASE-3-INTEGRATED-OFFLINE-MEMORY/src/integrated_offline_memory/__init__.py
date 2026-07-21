"""Governed offline market-data and candidate-memory integration."""

from .contracts import (
    FieldSemanticDecision,
    ParseIssue,
    ParseReport,
    SourceActivationPolicy,
    TdxDayRawRecord,
)
from .tdx_day import ParsedDayDataset, TdxDayParser, TdxDaySourceAdapter

__all__ = [
    "FieldSemanticDecision",
    "ParseIssue",
    "ParseReport",
    "ParsedDayDataset",
    "SourceActivationPolicy",
    "TdxDayParser",
    "TdxDayRawRecord",
    "TdxDaySourceAdapter",
]
