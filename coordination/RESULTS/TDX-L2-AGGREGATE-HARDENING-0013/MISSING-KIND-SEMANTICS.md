# Missing Kind Semantics

The normalizer now uses the following explicit buckets:

- `missing`: field key absent, or value is `None`
- `empty`: blank string after trimming
- `zero_value`: numeric zero, including `"0"` and `0`
- `present_numeric`: valid nonzero numeric value
- `present_non_numeric`: nonnumeric string/object that is not a known sentinel
- `permission_denied`: explicit permission/entitlement denial sentinel
- `interface_error`: explicit interface or timeout error sentinel
- `not_applicable`: `N/A`, `NA`, `null`, or equivalent not-applicable sentinel
- `unknown_sentinel`: unknown placeholder such as `unknown`, `--`, `-`, or `nan`

Unknown, unconfirmed TDX-specific strings are not guessed into permissions or interface errors. They remain `present_non_numeric` unless they match an explicit generic sentinel.
