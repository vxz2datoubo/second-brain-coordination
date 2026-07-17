# P0 Bug Root Cause

Task: `TDX-L2-AGGREGATE-HARDENING-0013`

## Confirmed Bug

`brain_core/realtime_l2_aggregate.py` had a P0 numeric conversion bug: `_to_number()` returned `None` after handling only `None` and `""`, while the `float(value)` conversion block was incorrectly left after `_has_text()`'s return statement and was therefore unreachable.

## Impact

- Numeric strings such as `"123.45"` did not become `123.45`.
- Numeric zero could not be reliably separated from missing/empty values.
- `missing_kind` collapsed most present values into a weak `present` bucket.
- Downstream L2 aggregate validation could not reason correctly about zero values, nonnumeric sentinels, or delta anomalies.

## Fix

- Restored numeric conversion inside `_to_number()`.
- Added explicit string stripping and safe failure for nonnumeric values.
- Added `_missing_kind()` with separate states for `missing`, `empty`, `zero_value`, `present_numeric`, `present_non_numeric`, `permission_denied`, `interface_error`, `not_applicable`, and `unknown_sentinel`.
- Removed the unreachable conversion block after `_has_text()`.
