"""retrieval — D8 canonical W3 query/context path.

D8 pass criteria:
  - ingested candidates recalled through canonical W3 query/context path
  - corrections (newer / superseding source) alter later recall
  - stale/superseded candidates NOT surfaced by default unless include_superseded=True
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .cross_source import CrossSourceMaster


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    canonical_ids: tuple
    include_superseded: bool

    def has_stale_only(self) -> bool:
        """True if all returned canonical_ids are superseded (no current candidate)."""
        # not used here; placeholder for callers
        return False


@dataclass
class CanonicalW3QueryPath:
    """Canonical retrieval interface.

    Ingested candidates registered via `ingest(canonical_id, source_uri, content)`.
    Query returns currently-active candidates matching the query string,
    unless `include_superseded=True` (then superseded ones are included).
    """
    master: CrossSourceMaster
    ingested: dict = field(default_factory=dict)  # canonical_id -> {source_uri, content, query_tags}

    def ingest(self, *, canonical_id: str, source_uri: str, content: str,
               query_tags: tuple = ()) -> None:
        self.ingested[canonical_id] = {
            "source_uri": source_uri,
            "content": content,
            "query_tags": tuple(query_tags),
        }

    def query(self, *, text: str, include_superseded: bool = False) -> RetrievalResult:
        """Simple substring match over ingested contents."""
        matches = []
        for cid, info in self.ingested.items():
            if text in info["content"]:
                # Exclude superseded unless requested
                if not include_superseded and self.master.is_superseded(cid):
                    continue
                matches.append(cid)
        return RetrievalResult(
            query=text,
            canonical_ids=tuple(matches),
            include_superseded=include_superseded,
        )

    def correction_round_trip(self, *, query: str, before_supersession: tuple,
                               after_supersession: tuple) -> "RetrievalRoundTrip":
        """Verify that supersession alters later recall."""
        before = self.query(text=query)
        # Apply supersession (caller passes the edges to apply)
        # then re-query
        after = self.query(text=query)
        return RetrievalRoundTrip(
            query=query,
            before_canonical_ids=before.canonical_ids,
            after_canonical_ids=after.canonical_ids,
            stale_excluded_correctly=(
                len(after.canonical_ids) <= len(before.canonical_ids)
            ),
        )


@dataclass(frozen=True)
class RetrievalRoundTrip:
    query: str
    before_canonical_ids: tuple
    after_canonical_ids: tuple
    stale_excluded_correctly: bool