# ROLLBACK PACK

## Purpose

This pack provides the safest available rollback path for `FOUNDATION-DATA-GOVERNANCE-0001` without assuming Git exists.

## What Is Precise

1. SQLite row deletion for the 7 Foundation-specific records
2. JSONL tail truncation for the 7 Foundation-specific audit events
3. reverse patch for the additive changes in:
   - `brain_core/service.py`
   - `apps/cli/brainctl.py`
4. deletion of the new files introduced by the Foundation task

## What Is Not Byte-Exact

1. `bulletin/super-second-brain-v01-board.md`
   - a targeted rollback can remove the Foundation milestone and Foundation recent-event line
   - there is no byte-exact immediate pre-task file snapshot

2. `data/super_brain_v01.sqlite`
   - row-level rollback is precise
   - file-level pre-change SHA256 is unavailable because no DB snapshot existed before the task

## Files

1. `foundation_data_governance_reverse.patch`
2. `foundation_data_governance_rollback.sql`
3. `rollback_foundation_data_governance.py`
4. `rollback_health_check.py`
5. `SHA256-MANIFEST.md`

## Default Safety

- `rollback_foundation_data_governance.py` defaults to `--dry-run`
- nothing is deleted unless `--write` is passed
