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

    lock = state.SingleInstanceLock()
    if not lock.acquire():
        log.error("Another dispatcher instance is running — exiting")
        sys.exit(1)

    try:
        token = protocol._get_token()
        conn = state.init_db()

        # Init cursor to latest comment (prevent replay)
        last_id, last_etag = state.get_cursor(conn)
        if last_id == 0:
            latest = protocol.get_current_comment_id(token)
            state.update_cursor(conn, latest, None)
            last_id = latest
            log.info(f"Cursor initialized to comment ID {last_id}")

        log.info("Entering polling loop (60s interval)")
        while True:
            try:
                comments, new_etag = protocol.fetch_new_comments(token, last_id, last_etag)
                if comments:
                    log.info(f"Found {len(comments)} new comments")
                    for c in comments:
                        process_comment(token, conn, c)
                        if c["id"] > last_id:
                            last_id = c["id"]
                    state.update_cursor(conn, last_id, new_etag)
                    last_etag = new_etag
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
