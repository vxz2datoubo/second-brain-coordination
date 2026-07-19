# Crawler Reliability Revision

Public crawler/WebSocket evidence remains `auxiliary_crosscheck_only`.

`source_reliability=0.55` is now documented as a conservative default hint, not a measured reliability score. The policy carries:

- `usage_class=auxiliary_crosscheck_only`
- `reliability_calibration_status=uncalibrated`
- `evidence_quality=official|licensed_vendor|public_portal|unofficial|unknown`

Reserved calibration fields:

- `delay_ms`
- `missing_rate`
- `timestamp_quality`
- `staleness_rate`
- `cross_source_consistency`
- `license_status`

Crawler routes cannot promote raw L2, clear proxy guard, or become primary market-data truth by themselves.
