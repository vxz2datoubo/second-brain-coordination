# System Discovery And Opportunity Report

## Finding

Historical A-share research needs a first-class, effective-dated link between a data manifest and rule/security-status evidence. The existing contracts already protect source activation and time semantics; the gap is proof packaging, not a new runtime.

## Opportunity

After owner approval, propose a backward-compatible `RuleSnapshotRef` extension in the canonical registry. It should point to official source URL, document hash, publication/effective intervals, exchange/board/security context, and provision implementation state. It must not hard-code a universal ST, suspension, or price-limit rule.

## Boundaries

This task does not modify the canonical registry, W2/W3/W7, PR #51, PR #79, QCLAW work, or an actual market source. It supplies only the acceptance requirements that a later owner-approved change would need to meet.
