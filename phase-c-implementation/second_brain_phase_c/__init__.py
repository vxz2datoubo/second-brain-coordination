"""
Second Brain PHASE_C: Knowledge Object and Reconciliation Layer

Implements KnowledgeEpisode/KnowledgeAtom schema, ReconciliationEngine,
GraphEvolutionManager, audit log with rollback, compatibility migration,
and human-readable Markdown templates.

Sits atop the R109-accepted Memory Palace foundation. Does not modify
W3 canonical structure; KnowledgeAtom is a compatible wrapper/extension.
"""

__version__ = "1.0.0"
__phase__ = "PHASE_C"
__status__ = "CANDIDATE_IMPLEMENTATION_AWAITING_REVIEW"
