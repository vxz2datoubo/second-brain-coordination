"""
CODEX-GITHUB-DISPATCHER-0001 — Main Dispatcher
Single-process long-running polling dispatcher for Codex GitHub auto-dispatch.
Phase 1: START, risk_class:low, approval_policy:automatic, read-only tasks only.
"""
import sys
import time
import logging
import os
from pathlib import Path

import schema
import state
import protocol
import codex_wrapper

POLL_INTERVAL_SECONDS = 60
RUNNER_ID = "WB-DISPATCHER-0001"
WORKTREE_PATH = r"F:\aidanao\coordination\worktrees\codex-dispatcher-mvp"

# --- Logging ---
def _setup_logging():
    state.ensure_dirs()
    log_file = state.LOG_DIR / "dispatcher.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    # Redact common secrets from log output
    return logging.getLogger("dispatcher")

log = _setup_logging()


def check_worktree_clean() -> bool:
    """Verify the worktree is clean before execution."""
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=WORKTREE_PATH,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        log.error(f"git status failed in worktree: {result.stderr}")
        return False
    dirty = result.stdout.strip()
    if dirty:
        log.warning(f"Worktree is dirty — refusing to execute:\n{dirty}")
        return False
    return True


def get_worktree_head() -> str:
    import subprocess
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=WORKTREE_PATH,
        capture_output=True, text=True,
    )
    return result.stdout.strip()[:40]


def process_comment(token: str, conn, comment: dict):
    """Process a single comment: parse, validate, execute if valid."""
    comment_id = comment["id"]
    body = comment.get("body", "")
    issue_url = comment.get("issue_url", "")
    issue_number = int(issue_url.rstrip("/").split("/")[-1]) if issue_url else 0
    comment_url = comment.get("html_url", "")

    if not body or not issue_number:
        return

    # Check issue has codex-dispatch label
    labels = protocol.check_issue_labels(token, issue_number)
    if protocol.DISPATCH_LABEL not in labels:
        log.info(f"Issue #{issue_number} lacks {protocol.DISPATCH_LABEL} label — skipping")
        return

    blocks = schema.find_dispatch_blocks(body, comment_id, comment_url)
    if not blocks:
        return  # No dispatch blocks OR pre-filtered silently

    for block in blocks:
        if not block.parse():
            log.debug(f"Parse failed for comment {comment_id}: {block.errors}")
            protocol.post_comment(token, issue_number,
                protocol.format_receipt("UNKNOWN", "UNKNOWN", "INVALID", RUNNER_ID,
                                        WORKTREE_PATH, get_worktree_head(), codex_wrapper.CODEX_VERSION))
            return

        if not block.validate():
            # Check if unsupported action — write back to GitHub
            if block.is_unsupported_action:
                p = block.parsed if block.parsed else {}
                action = p.get("action", "UNKNOWN")
                task_id = p.get("task_id", "UNKNOWN")
                log.info(f"UNSUPPORTED_ACTION on comment {comment_id}: {action}")
                msg = f"""```yaml
CODEX_DISPATCH_UNSUPPORTED_ACTION:
  agent_id: CODEX-DISPATCHER
  task_id: {task_id}
  action: {action}
  reason: Phase 1 only supports action=START. {action} is not supported.
  issue: {issue_number}
  comment: {comment_id}
```"""
                protocol.post_comment(token, issue_number, msg)
                return
            log.debug(f"Validation failed for comment {comment_id}: {block.errors}")
            protocol.post_comment(token, issue_number,
                protocol.format_receipt(block.parsed.get("task_id", "UNKNOWN") if block.parsed else "UNKNOWN",
                                        block.parsed.get("idempotency_key", "UNKNOWN") if block.parsed else "UNKNOWN",
                                        "INVALID", RUNNER_ID, WORKTREE_PATH,
                                        get_worktree_head(), codex_wrapper.CODEX_VERSION))
            return
            protocol.post_comment(token, issue_number,
                protocol.format_receipt(block.parsed.get("task_id", "UNKNOWN"),
                                        block.parsed.get("idempotency_key", "UNKNOWN"),
                                        "INVALID", RUNNER_ID, WORKTREE_PATH,
                                        get_worktree_head(), codex_wrapper.CODEX_VERSION))
            return

        p = block.parsed
        task_id = p["task_id"]
        idem_key = p["idempotency_key"]

        # Idempotency check
        if state.is_idempotency_key_used(conn, idem_key):
            log.info(f"Duplicate idempotency key {idem_key} — posting DUPLICATE")
            protocol.post_comment(token, issue_number,
                protocol.format_receipt(task_id, idem_key, "DUPLICATE", RUNNER_ID,
                                        WORKTREE_PATH, get_worktree_head(), codex_wrapper.CODEX_VERSION))
            state.mark_idempotency_key(conn, idem_key, task_id, "DUPLICATE", comment_id)
            return

        # Safety: verify worktree clean
        if not check_worktree_clean():
            log.error("Worktree dirty — rejecting dispatch")
            protocol.post_comment(token, issue_number,
                protocol.format_receipt(task_id, idem_key, "BLOCKED", RUNNER_ID,
                                        WORKTREE_PATH, get_worktree_head(), codex_wrapper.CODEX_VERSION))
            state.mark_idempotency_key(conn, idem_key, task_id, "BLOCKED", comment_id)
            return

        # Accept
        log.info(f"ACCEPTING: task={task_id} idem={idem_key}")
        state.mark_idempotency_key(conn, idem_key, task_id, "ACCEPTED", comment_id)
        head = get_worktree_head()
        protocol.post_comment(token, issue_number,
            protocol.format_receipt(task_id, idem_key, "ACCEPTED", RUNNER_ID,
                                    WORKTREE_PATH, head, codex_wrapper.CODEX_VERSION))

        # Execute
        try:
            model = p.get("mode", "direct")
            instruction_loc = p.get("instruction_location")
            prompt = codex_wrapper.build_prompt(
                task_id, model, protocol.TARGET_REPO,
                str(p["source_issue_or_pr"]),
                p["workspace_alias"],
                instruction_loc,
            )
            log.info(f"Dispatching to Codex... (task={task_id})")
            output, exit_code = codex_wrapper.run_codex(prompt, WORKTREE_PATH)

            # Redact output (max 4000 chars)
            redacted = output[:4000]
            # Remove potential credential patterns
            for pattern in ["password=", "token=", "api_key=", "Bearer ", "-----BEGIN"]:
                if pattern.lower() in redacted.lower():
                    redacted = redacted[:1000] + "\n[REDACTED: output contained credential-like content]\n"

            status = "COMPLETED" if exit_code == 0 else "FAILED"
            protocol.post_comment(token, issue_number,
                protocol.format_completed(task_id, idem_key,
                    f"exit_code={exit_code}\noutput_preview={redacted[:500]}...",
                    status))
            log.info(f"Task {task_id} {status} (exit={exit_code})")

        except codex_wrapper.CodexTimeout:
            log.error(f"Task {task_id} timed out")
            protocol.post_comment(token, issue_number,
                protocol.format_completed(task_id, idem_key,
                    f"TIMEOUT after {codex_wrapper.MAX_RUNTIME_SECONDS}s", "TIMEOUT"))
        except codex_wrapper.CodexError as e:
            log.error(f"Task {task_id} Codex error: {e}")
            protocol.post_comment(token, issue_number,
                protocol.format_completed(task_id, idem_key,
                    f"CodexError: {str(e)[:200]}", "FAILED"))
        except Exception as e:
            log.error(f"Task {task_id} unexpected error: {e}")
            protocol.post_comment(token, issue_number,
                protocol.format_completed(task_id, idem_key,
                    f"Unexpected error: {str(e)[:200]}", "FAILED"))

        # Only process one dispatch per poll cycle
        break


def main_loop():
    log.info("=== CODEX-GITHUB-DISPATCHER-0001 STARTING ===")
    log.info(f"Worktree: {WORKTREE_PATH}")
    log.info(f"Codex CLI: {codex_wrapper.CODEX_VERSION}")
    log.info(f"Build head: {get_worktree_head()}")

    lock = state.SingleInstanceLock()
    if not lock.acquire():
        log.error("Another dispatcher instance is running — exiting")
        sys.exit(1)

    try:
        token = protocol._get_token()
        conn = state.init_db()

        # Init per-issue cursors for known issues on first run
        issues = protocol.fetch_labeled_issues(token)
        if issues:
            log.info(f"Found {len(issues)} labeled issues: {issues}")
        else:
            log.warning("No labeled issues found on startup — running discovery anyway")

        log.info("Entering polling loop (60s interval, per-issue paginated)")
        while True:
            try:
                issues = protocol.fetch_labeled_issues(token)
                degraded_any = False
                total_processed = 0

                for issue_num in issues:
                    # Per-issue cursor
                    last_cid, last_cat, last_etag = state.get_issue_cursor(conn, issue_num)
                    comments, new_etag, degraded = protocol.fetch_issue_comments_paginated(
                        token, issue_num, since_comment_id=last_cid, etag=last_etag)
                    if degraded:
                        degraded_any = True
                        log.warning(f"Issue #{issue_num}: pagination DEGRADED (page cap or API error)")

                    for c in comments:
                        process_comment(token, conn, c)
                        if c["id"] > last_cid:
                            last_cid = c["id"]
                            last_cat = c.get("created_at", last_cat)
                        total_processed += 1

                    # Atomically update per-issue cursor
                    if last_cid > 0:
                        state.upsert_issue_cursor(conn, issue_num, last_cid,
                                                   last_cat or "", new_etag)

                if degraded_any:
                    log.warning("One or more issues DEGRADED in this cycle")
                if total_processed > 0:
                    log.info(f"Processed {total_processed} comments across {len(issues)} issues")

                time.sleep(POLL_INTERVAL_SECONDS)
            except KeyboardInterrupt:
                log.info("Shutdown requested")
                break
            except Exception as e:
                log.error(f"Polling error: {e}")
                time.sleep(POLL_INTERVAL_SECONDS)
    finally:
        lock.release()
        log.info("=== DISPATCHER STOPPED ===")


if __name__ == "__main__":
    main_loop()
