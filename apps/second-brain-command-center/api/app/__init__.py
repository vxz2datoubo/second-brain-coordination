"""Second Brain Command Center — Thin BFF.

READ-ONLY projection layer. It does NOT define authority.
All truth originates from existing authorities:
  - GitHub engineering truth (canonical main, routes, Issues, PRs)
  - Local repo/runtime state (git worktrees, ACTIVE-* task files)
  - Control Tower derived projections

This package only READS, NORMALIZES and PROJECTS.
"""

__version__ = "0.1.0-phase1"
