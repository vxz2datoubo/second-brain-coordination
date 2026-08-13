"""qclaw_e50_audit — Learning-system preproduction completeness audit (E50 R2).

E50 R2 mandatory: audit the canonical W3 / Codex implementations directly.
Local stand-ins (under ._untrusted_test_double) MUST NOT earn canonical PASS
credit; they exist only as documented UNTRUSTED_TEST_DOUBLE references.

Source policy: PUBLIC_SAFE_GENERALIZATION_ONLY.
No private/high-value user source ingestion.
No authoritative PROJECT/GLOBAL persistence.
No automatic formal skill/trading-rule promotion.
"""

# R2 re-exports are populated in submodules; the canonical audit modules
# are imported lazily so they can call canonical.access.setup_import_path()
# before importing any vendored snapshot module.