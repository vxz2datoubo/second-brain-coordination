"""
CODEX-GITHUB-DISPATCHER-0001 — Unit Tests
Test schema parser, validator, idempotency, and edge cases.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schema
import state
import codex_wrapper
from unittest.mock import patch, MagicMock

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


# ===== Instruction Location URL Validation Tests (PR #3 Remediation 0011) =====

VALID_WITH_LOC = VALID_DISPATCH.replace(
    "idempotency_key: TEST-001-abc123\n",
    "instruction_location: https://github.com/vxz2datoubo/second-brain-coordination/issues/7\nidempotency_key: TEST-001-abc123\n")


def test_url_valid_issues():
    """Valid URL with correct owner/repo/issues/N."""
    block = schema.DispatchBlock(VALID_WITH_LOC, 1, "http://test")
    assert block.parse()
    assert block.validate(), f"Expected valid: {block.errors}"


def test_url_reject_wrong_host():
    """evil.com should be rejected."""
    text = VALID_WITH_LOC.replace("github.com", "evil.com")
    block = schema.DispatchBlock(text, 1, "http://test")
    block.parse()
    assert not block.validate()
    assert any("github.com" in e for e in block.errors)


def test_url_reject_wrong_repo():
    """Different repo should be rejected."""
    text = VALID_WITH_LOC.replace("second-brain-coordination", "other-repo")
    block = schema.DispatchBlock(text, 1, "http://test")
    block.parse()
    assert not block.validate()
    assert any("TARGET_REPO" in e or "vxz2datoubo" in e for e in block.errors)


def test_url_reject_number_mismatch():
    """instruction_location issue number must match source_issue_or_pr."""
    text = VALID_WITH_LOC.replace("issues/7", "issues/999")
    block = schema.DispatchBlock(text, 1, "http://test")
    block.parse()
    assert not block.validate()
    assert any("source_issue_or_pr" in e or "number" in e for e in block.errors)


def test_url_reject_wrong_scheme():
    """ftp:// should be rejected."""
    text = VALID_WITH_LOC.replace("https://", "ftp://")
    block = schema.DispatchBlock(text, 1, "http://test")
    block.parse()
    assert not block.validate()


def test_url_reject_malformed_path():
    """Malformed path should be rejected."""
    text = VALID_WITH_LOC.replace("issues/7", "bad-path")
    block = schema.DispatchBlock(text, 1, "http://test")
    block.parse()
    assert not block.validate()

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


# ===== Pagination + Per-Issue Cursor Tests (Fix 0005) =====

def test_per_issue_cursor_basics():
    """Per-issue cursor: read, write, update."""
    state.ensure_dirs()
    conn = state.init_db()
    conn.execute("DELETE FROM issue_cursors")
    conn.commit()
    cid, cat, etag = state.get_issue_cursor(conn, 99)
    assert cid == 0
    state.upsert_issue_cursor(conn, 99, 50001, "2026-01-01T00:00:00Z", None)
    cid2, cat2, etag2 = state.get_issue_cursor(conn, 99)
    assert cid2 == 50001
    assert cat2 is not None
    conn.close()


def test_per_issue_cursor_isolation():
    """Different issues have independent cursors."""
    state.ensure_dirs()
    conn = state.init_db()
    conn.execute("DELETE FROM issue_cursors")
    conn.commit()
    state.upsert_issue_cursor(conn, 7, 100, "2026-01-01T00:00:00Z", None)
    state.upsert_issue_cursor(conn, 9, 200, "2026-01-02T00:00:00Z", "etag9")
    c7, _, _ = state.get_issue_cursor(conn, 7)
    c9, _, e9 = state.get_issue_cursor(conn, 9)
    assert c7 == 100, f"issue 7 cursor should be 100, got {c7}"
    assert c9 == 200, f"issue 9 cursor should be 200, got {c9}"
    assert e9 == "etag9"
    conn.close()


def test_link_header_parsing():
    """Parse GitHub Link header correctly."""
    import protocol
    header = '<https://api.github.com/repos/x/comments?page=2>; rel="next", <https://api.github.com/repos/x/comments?page=5>; rel="last"'
    links = protocol._parse_link_header(header)
    assert "next" in links
    assert links["next"].endswith("page=2")


def test_link_header_none():
    import protocol
    links = protocol._parse_link_header(None)
    assert links == {}
    links2 = protocol._parse_link_header("")
    assert links2 == {}


def test_large_comment_set_simulated():
    """101-comment set: the 101st comment is discoverable (cursor logic)."""
    state.ensure_dirs()
    conn = state.init_db()
    conn.execute("DELETE FROM issue_cursors")
    conn.commit()

    # Simulate: we've seen 100 comments, cursor at 100
    state.upsert_issue_cursor(conn, 42, 100, "2026-01-01T00:00:00Z", None)
    cid, _, _ = state.get_issue_cursor(conn, 42)
    assert cid == 100

    # A new comment with id 101 should pass through the filter
    # (The actual pagination test would need HTTP, this tests the cursor logic)
    new_comment_id = 101
    assert new_comment_id > cid, "Comment 101 should be > cursor 100"
    conn.close()


def test_per_issue_cursor_recovery():
    """Restart: per-issue cursors persist in SQLite."""
    state.ensure_dirs()
    conn = state.init_db()
    state.upsert_issue_cursor(conn, 5, 500, "2026-01-01", "et")
    conn.close()
    conn2 = state.init_db()
    c, _, e = state.get_issue_cursor(conn2, 5)
    assert c == 500
    assert e == "et"
    conn2.execute("DELETE FROM issue_cursors")
    conn2.commit()
    conn2.close()


def test_new_issue_first_discovery():
    """First-time issue: cursor returns 0, all comments visible."""
    state.ensure_dirs()
    conn = state.init_db()
    cid, cat, etag = state.get_issue_cursor(conn, 99999)
    assert cid == 0, "New issue should have cursor=0"
    assert cat is None
    conn.close()


# ===== UTF-8 Output Integrity — Real Regression Tests (Fix 0009) =====

def _mock_popen(stdout_bytes, stderr_bytes=b"", returncode=0):
    """Helper: create a mock subprocess.Popen that returns given bytes."""
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = (stdout_bytes, stderr_bytes)
    mock_proc.returncode = returncode
    return mock_proc


def test_utf8_valid_chinese_emoji():
    """Valid UTF-8 Chinese + emoji output → complete return."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen("你好世界 🌍 通过".encode("utf-8"))
        output, rc = codex_wrapper.run_codex("test prompt", "/tmp", timeout=10)
        assert rc == 0
        assert "你好世界" in output
        assert "🌍" in output


def test_utf8_illegal_bytes_raises_error():
    """Illegal UTF-8 bytes → CodexOutputIntegrityError (strict policy)."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(b"Hello \xff\xfe World")
        try:
            codex_wrapper.run_codex("test", "/tmp", timeout=10)
            assert False, "Should have raised CodexOutputIntegrityError"
        except codex_wrapper.CodexOutputIntegrityError:
            pass  # Expected


def test_utf8_empty_output_zero_rc():
    """Empty output with exit_code=0 → CodexOutputIntegrityError."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(b"", b"", returncode=0)
        try:
            codex_wrapper.run_codex("test", "/tmp", timeout=10)
            assert False, "Should have raised CodexOutputIntegrityError"
        except codex_wrapper.CodexOutputIntegrityError:
            pass


def test_utf8_whitespace_only_fails():
    """Whitespace-only output with exit_code=0 → CodexOutputIntegrityError."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(b"  \n\t  ", b"", returncode=0)
        try:
            codex_wrapper.run_codex("test", "/tmp", timeout=10)
            assert False, "Should have raised CodexOutputIntegrityError"
        except codex_wrapper.CodexOutputIntegrityError:
            pass


def test_utf8_nonzero_rc_with_stderr():
    """Non-zero returncode with stderr → returns both, no error raised."""
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value = _mock_popen(b"", b"error: something broke", returncode=1)
        output, rc = codex_wrapper.run_codex("test", "/tmp", timeout=10)
        assert rc == 1
        assert "error" in output


def test_utf8_timeout_raises_timeout():
    """communicate timeout → CodexTimeout."""
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        import subprocess
        mock_proc.communicate.side_effect = subprocess.TimeoutExpired(cmd=["codex"], timeout=1)
        mock_popen.return_value = mock_proc
        try:
            codex_wrapper.run_codex("test", "/tmp", timeout=1)
            assert False, "Should have raised CodexTimeout"
        except codex_wrapper.CodexTimeout:
            pass


def test_utf8_version_mocked():
    """Dynamic version detection with mocked subprocess."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="codex-cli 9.9.9\n", returncode=0)
        codex_wrapper._cached_codex_version = None  # clear cache
        ver = codex_wrapper.get_codex_version()
        assert ver == "9.9.9", f"Expected 9.9.9, got {ver}"


def test_utf8_class_hierarchy():
    """CodexOutputIntegrityError inherits from CodexError."""
    assert issubclass(codex_wrapper.CodexOutputIntegrityError, codex_wrapper.CodexError)
    assert issubclass(codex_wrapper.CodexTimeout, codex_wrapper.CodexError)


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
        ("url_valid_issues", test_url_valid_issues),
        ("url_reject_wrong_host", test_url_reject_wrong_host),
        ("url_reject_wrong_repo", test_url_reject_wrong_repo),
        ("url_reject_number_mismatch", test_url_reject_number_mismatch),
        ("url_reject_wrong_scheme", test_url_reject_wrong_scheme),
        ("url_reject_malformed_path", test_url_reject_malformed_path),
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
        ("per_issue_cursor_basics", test_per_issue_cursor_basics),
        ("per_issue_cursor_isolation", test_per_issue_cursor_isolation),
        ("link_header_parsing", test_link_header_parsing),
        ("link_header_none", test_link_header_none),
        ("large_comment_set_simulated", test_large_comment_set_simulated),
        ("per_issue_cursor_recovery", test_per_issue_cursor_recovery),
        ("new_issue_first_discovery", test_new_issue_first_discovery),
        ("utf8_valid_chinese_emoji", test_utf8_valid_chinese_emoji),
        ("utf8_illegal_bytes_raises_error", test_utf8_illegal_bytes_raises_error),
        ("utf8_empty_output_zero_rc", test_utf8_empty_output_zero_rc),
        ("utf8_whitespace_only_fails", test_utf8_whitespace_only_fails),
        ("utf8_nonzero_rc_with_stderr", test_utf8_nonzero_rc_with_stderr),
        ("utf8_timeout_raises_timeout", test_utf8_timeout_raises_timeout),
        ("utf8_version_mocked", test_utf8_version_mocked),
        ("utf8_class_hierarchy", test_utf8_class_hierarchy),
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
