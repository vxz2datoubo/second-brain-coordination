"""
CODEX-GITHUB-DISPATCHER-0001 — Unit Tests
Test schema parser, validator, idempotency, and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schema
import state

# ===== Schema Parser Tests =====

VALID_DISPATCH = """```yaml
CodexDispatch:
  schema_version: "1.0"
  issuer_agent: GPT
  target_agent: CODEX
  task_id: TEST-001
  action: START
  mode: direct
  repository: vxz2datoubo/second-brain-coordination
  source_issue_or_pr: 7
  workspace_alias: AIDANAO_ROOT
  risk_class: low
  approval_policy: automatic
  idempotency_key: TEST-001-abc123
```"""


def test_parse_valid():
    block = schema.DispatchBlock(VALID_DISPATCH, 1, "http://test")
    assert block.parse(), f"Parse failed: {block.errors}"
    assert block.parsed is not None


def test_validate_valid():
    block = schema.DispatchBlock(VALID_DISPATCH, 1, "http://test")
    assert block.parse()
    assert block.validate(), f"Validate failed: {block.errors}"


def test_reject_missing_fence():
    block = schema.DispatchBlock("CodexDispatch:\n  task_id: X", 1, "http://test")
    assert not block.parse()


def test_reject_wrong_issuer():
    text = VALID_DISPATCH.replace("issuer_agent: GPT", "issuer_agent: HACKER")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()
    assert any("issuer_agent" in e for e in block.errors)


def test_reject_wrong_action():
    text = VALID_DISPATCH.replace("action: START", "action: DELETE_EVERYTHING")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()


def test_reject_high_risk():
    text = VALID_DISPATCH.replace("risk_class: low", "risk_class: high")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()


def test_reject_wrong_repo():
    text = VALID_DISPATCH.replace("vxz2datoubo/second-brain-coordination", "evil/repo")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()


def test_reject_unknown_key():
    text = VALID_DISPATCH.replace("  idempotency_key:", "  shell_command: rm -rf /\n  idempotency_key:")
    block = schema.DispatchBlock(text, 1, "http://test")
    # Unknown key caught at parse time (defense-in-depth)
    assert (not block.parse()) or (not block.validate()), "Expected rejection"
    assert any("shell_command" in e for e in block.errors) or block.errors, f"Errors: {block.errors}"


def test_reject_missing_key():
    text = VALID_DISPATCH.replace("  task_id: TEST-001\n", "")
    block = schema.DispatchBlock(text, 1, "http://test")
    # Missing key caught at parse time
    assert (not block.parse()) or (not block.validate()), "Expected rejection"
    assert any("task_id" in e for e in block.errors) or block.errors, f"Errors: {block.errors}"
    assert any("task_id" in e for e in block.errors)


def test_reject_yaml_tag():
    text = "```yaml\nCodexDispatch: !!omap\n  - task_id: X\n```"
    block = schema.DispatchBlock(text, 1, "http://test")
    assert not block.parse()


def test_reject_oversized():
    big = "```yaml\nCodexDispatch:\n  task_id: X\n" + "  padding: " + "x" * 5000 + "\n```"
    block = schema.DispatchBlock(big, 1, "http://test")
    assert not block.parse()


def test_reject_non_gpt_continue():
    # CONTINUE is not in ALLOWED_ACTIONS for phase 1
    text = VALID_DISPATCH.replace("action: START", "action: CONTINUE")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()


def test_reject_unknown_workspace():
    text = VALID_DISPATCH.replace("workspace_alias: AIDANAO_ROOT", "workspace_alias: EVIL_ROOT")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()


# ===== Pre-Filter Tests (Phase 1 Fix 0002) =====

def test_skip_ordinary_comment():
    """Ordinary comment without CodexDispatch keyword should be silently skipped."""
    skip, reason = schema.should_skip_comment("This is a normal discussion comment.")
    assert skip, f"should skip, got reason={reason}"


def test_skip_auto_receipt():
    """Automated receipt comment should be silently skipped."""
    skip, reason = schema.should_skip_comment("CodexDispatchReceipt:\n  agent_id: CODEX-DISPATCHER\n  task_id: X")
    assert skip, f"should skip receipt, got reason={reason}"
    assert "auto_receipt" in reason


def test_skip_heartbeat():
    """Heartbeat comment should be silently skipped."""
    skip, reason = schema.should_skip_comment("WBDispatcherHeartbeat:\n  dispatcher_status: ONLINE")
    assert skip, f"should skip heartbeat, got reason={reason}"


def test_skip_task_started():
    """CODEX_TASK_STARTED should be silently skipped."""
    skip, reason = schema.should_skip_comment("CODEX_TASK_STARTED:\n  agent_id: CODEX\n  task_id: X")
    assert skip


def test_skip_task_completed():
    """CODEX_TASK_COMPLETED should be silently skipped."""
    skip, reason = schema.should_skip_comment("CODEX_TASK_COMPLETED:\n  task_id: X")
    assert skip


def test_skip_no_fenced_yaml():
    """Comment with CodexDispatch keyword but no fenced YAML should be skipped."""
    skip, reason = schema.should_skip_comment("CodexDispatch: this is a mention but not a block")
    assert skip, f"should skip, got reason={reason}"
    assert "fenced" in reason


def test_pass_valid_with_fence():
    """Valid dispatch with both keyword and fenced YAML should pass pre-filter."""
    skip, reason = schema.should_skip_comment(VALID_DISPATCH)
    assert not skip, f"should not skip, got reason={reason}"


# ===== Unsupported Action Tests (Phase 1 Fix 0002) =====

def test_unsupported_review_detected():
    text = VALID_DISPATCH.replace("action: START", "action: REVIEW")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse(), f"Parse failed: {block.errors}"
    assert not block.validate(), "Expected validation to fail for REVIEW"
    assert block.is_unsupported_action, "is_unsupported_action should be True for REVIEW"


def test_unsupported_continue_detected():
    text = VALID_DISPATCH.replace("action: START", "action: CONTINUE")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()
    assert block.is_unsupported_action


def test_unsupported_cancel_detected():
    text = VALID_DISPATCH.replace("action: START", "action: CANCEL")
    block = schema.DispatchBlock(text, 1, "http://test")
    assert block.parse()
    assert not block.validate()
    assert block.is_unsupported_action


# ===== Idempotency Tests =====

def test_idempotency():
    state.ensure_dirs()
    conn = state.init_db()
    # Clean
    conn.execute("DELETE FROM idempotency")
    conn.commit()
    key = "IDEM-TEST-001"
    assert not state.is_idempotency_key_used(conn, key)
    state.mark_idempotency_key(conn, key, "TASK-001", "ACCEPTED", 1)
    assert state.is_idempotency_key_used(conn, key)
    # Clean up
    conn.execute("DELETE FROM idempotency WHERE key=?", (key,))
    conn.commit()
    conn.close()


# ===== Cursor Tests =====

def test_cursor():
    state.ensure_dirs()
    conn = state.init_db()
    last_id, etag = state.get_cursor(conn)
    assert isinstance(last_id, int)
    state.update_cursor(conn, 99999, "test_etag")
    last_id2, etag2 = state.get_cursor(conn)
    assert last_id2 == 99999
    assert etag2 == "test_etag"
    state.update_cursor(conn, 0, None)  # reset
    conn.close()


# ===== Run all =====

if __name__ == "__main__":
    tests = [
        ("parse_valid", test_parse_valid),
        ("validate_valid", test_validate_valid),
        ("reject_missing_fence", test_reject_missing_fence),
        ("reject_wrong_issuer", test_reject_wrong_issuer),
        ("reject_wrong_action", test_reject_wrong_action),
        ("reject_high_risk", test_reject_high_risk),
        ("reject_wrong_repo", test_reject_wrong_repo),
        ("reject_unknown_key", test_reject_unknown_key),
        ("reject_missing_key", test_reject_missing_key),
        ("reject_yaml_tag", test_reject_yaml_tag),
        ("reject_oversized", test_reject_oversized),
        ("reject_non_gpt_continue", test_reject_non_gpt_continue),
        ("reject_unknown_workspace", test_reject_unknown_workspace),
        ("skip_ordinary_comment", test_skip_ordinary_comment),
        ("skip_auto_receipt", test_skip_auto_receipt),
        ("skip_heartbeat", test_skip_heartbeat),
        ("skip_task_started", test_skip_task_started),
        ("skip_task_completed", test_skip_task_completed),
        ("skip_no_fenced_yaml", test_skip_no_fenced_yaml),
        ("pass_valid_with_fence", test_pass_valid_with_fence),
        ("unsupported_review_detected", test_unsupported_review_detected),
        ("unsupported_continue_detected", test_unsupported_continue_detected),
        ("unsupported_cancel_detected", test_unsupported_cancel_detected),
        ("test_idempotency", test_idempotency),
        ("test_cursor", test_cursor),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            passed += 1
            print(f"  PASS: {name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {name} — {e}")
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
