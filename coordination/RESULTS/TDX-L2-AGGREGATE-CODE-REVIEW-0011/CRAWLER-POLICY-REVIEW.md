# CRAWLER-POLICY-REVIEW

## Current Policy

`public_crawler_auxiliary_policy()` fixes crawler-derived default quality at:

- `quality_score = 0.45`
- `source_reliability = 0.55`
- `validation_status = auxiliary_only`
- `status = Experimental`

## Finding

The hard threshold `source_reliability <= 0.55` is conservative and directionally safe, but it lacks empirical calibration. It should not be treated as a measured reliability score.

## Recommended Future Model

Replace the fixed score with:

- `usage_class = auxiliary_crosscheck_only`
- `evidence_quality = official | licensed_vendor | public_portal | unofficial | unknown`
- dynamic reliability calculated from:
  - observed delay
  - missing-rate
  - timestamp quality
  - continuity / staleness
  - cross-source consistency
  - terms-of-service / license status

## Current Review Decision

Do not change code in this review. Keep the fixed conservative threshold as experimental policy, but mark it for future replacement.
