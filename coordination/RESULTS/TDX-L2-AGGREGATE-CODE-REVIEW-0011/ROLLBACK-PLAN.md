# ROLLBACK-PLAN

## Rollback Scope

Rollback target: changes from `TDX-L2-AGGREGATE-EXHAUST-0010` and follow-up broker classifier additions.

## Files To Remove If Full Logical Rollback Is Approved

- `brain_core/realtime_l2_aggregate.py`
- `tests/test_realtime_l2_aggregate.py`
- `coordination/TASKS/TDX-L2-AGGREGATE-EXHAUST-0010/`

## Files To Patch If Full Logical Rollback Is Approved

- `brain_core/foundation_data_governance.py`: remove TDX L2 aggregate additions and restore previous snapshot field coverage.
- `bulletin/super-second-brain-v01-board.md`: remove three appended lines:
  - `tdx_l2_aggregate_exhaust_registered`
  - `broker_low_cost_market_data_outreach_pack_ready`
  - `broker_market_data_reply_classifier_ready`

## SQLite Records To Delete

- `skill_registry_entries`: `skill_dbf271470f3772`, `skill_956e0dcdb1a65d`, `skill_1ea0d68141c1d2`
- `module_status_records`: `mod_dbf271470f3772`, `mod_956e0dcdb1a65d`, `mod_1ea0d68141c1d2`
- `bulletin_state_records`: `bstate_0fb6ec04a57048`, `bstate_af1e0bd1459944`, `bstate_eaa52784b8be42`
- `evolution_logs`: `evo_fad7c16326a042`, `evo_578ee8cc042d43`, `evo_5cb632a1b36d41`

## JSONL Audit Log

`data/audit/events.jsonl` is append-only. Logical rollback should append a rollback event rather than deleting historical audit lines. Byte-level rollback would require restoring a pre-change copy of the JSONL file, which is not available from this review.

## Candidate Manual SQL

Do not run unless rollback is approved.

```sql
DELETE FROM skill_registry_entries WHERE id IN ('skill_dbf271470f3772','skill_956e0dcdb1a65d','skill_1ea0d68141c1d2');
DELETE FROM module_status_records WHERE id IN ('mod_dbf271470f3772','mod_956e0dcdb1a65d','mod_1ea0d68141c1d2');
DELETE FROM bulletin_state_records WHERE id IN ('bstate_0fb6ec04a57048','bstate_af1e0bd1459944','bstate_eaa52784b8be42');
DELETE FROM evolution_logs WHERE id IN ('evo_fad7c16326a042','evo_578ee8cc042d43','evo_5cb632a1b36d41');
```

## Verification After Rollback

1. `python -m py_compile F:/aidanao/brain_core/foundation_data_governance.py`
2. Run relevant regression tests excluding removed test module.
3. Query SQLite for the IDs above and confirm zero matches.
4. Search bulletin for the three event names and confirm zero matches.
5. Confirm no runtime services or ports changed.

## Rollback Precision

- Logical precise rollback: possible with approved file deletion/patching and SQL deletion.
- Byte-level restoration: not possible from current evidence because no Git baseline or pre-change byte snapshot exists.
