"""qclaw_e50_audit - Learning-system preproduction completeness audit (E50 R3).

E50 R3 mandatory: audit the canonical W3 / Codex implementations DIRECTLY
from the checked-out repository tree (no vendored copies earn canonical PASS
credit). Local stand-ins (under _untrusted_test_double/) exist only as
documented UNTRUSTED_TEST_DOUBLE references and MUST NOT earn PASS credit.

Source policy: PUBLIC_SAFE_GENERALIZATION_ONLY.
No private/high-value user source ingestion.
No authoritative PROJECT/GLOBAL persistence.
No automatic formal skill/trading-rule promotion.
"""

# The canonical audit modules are imported lazily so each dimension can call
# authoritative.setup_import_path() before importing any authoritative module.
