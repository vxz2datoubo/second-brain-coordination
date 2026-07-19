# Numeric Conversion Tests

Verified by `tests.test_realtime_l2_aggregate.RealtimeL2AggregateTests.test_numeric_conversion_and_missing_kind_semantics`.

| Input | Expected numeric_value | Expected missing_kind |
|---|---:|---|
| `None` | `None` | `missing` |
| `""` | `None` | `empty` |
| `" "` | `None` | `empty` |
| `"0"` | `0.0` | `zero_value` |
| `0` | `0.0` | `zero_value` |
| `"123.45"` | `123.45` | `present_numeric` |
| `123` | `123.0` | `present_numeric` |
| `"-5.2"` | `-5.2` | `present_numeric` |
| `"abc"` | `None` | `present_non_numeric` |
| `object()` | `None` | `present_non_numeric` |

Result: passed.
