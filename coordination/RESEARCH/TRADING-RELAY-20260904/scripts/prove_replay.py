"""Verify existing P2 synthetic replay. No new trading engine or provider adapter."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
REPO = PACKAGE.parents[2]
P2_REL = "coordination/PROGRAMS/SECOND-BRAIN-A-SHARE-ENTERPRISE-SYSTEM-0001/PHASE-2-OFFLINE-VERTICAL-SLICE"
P2 = REPO / P2_REL
LOCK = PACKAGE / "replay-lock.json"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")


def text_hash(path: Path) -> str:
    # Explicit portable text normalization, independent of Git CRLF checkout policy.
    return sha(path.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8"))


def validate_lock(lock: dict) -> None:
    if lock["mode"] != "research_only" or lock["no_trade"] is not True:
        raise ValueError("NO_TRADE_LOCK_REQUIRED")
    if lock["repeat_runs"] != 2 or lock["expected_events"] != 8:
        raise ValueError("SYNTHETIC_CONTRACT_CHANGED")
    if lock["as_of"] != "2026-01-31T23:59:59Z":
        raise ValueError("FIXED_AS_OF_REQUIRED")
    for relative, expected in lock["source_text_sha256"].items():
        source = (REPO / relative).resolve()
        if not source.is_relative_to(P2.resolve()):
            raise ValueError("SOURCE_OUTSIDE_P2")
        if text_hash(source) != expected:
            raise ValueError("SOURCE_OR_FIXTURE_DRIFT:" + relative)


def artifact_hashes(directory: Path) -> dict[str, str]:
    return {p.name: sha(canonical(json.loads(p.read_text(encoding="utf-8"))))
            for p in sorted(directory.glob("*.json"))}


def verify_outputs(left: Path, right: Path) -> dict[str, str]:
    a, b = artifact_hashes(left), artifact_hashes(right)
    required = {"RunManifest.json", "DatasetManifest.json", "ReplayEventLedger.json",
                "ResearchDecisionLedger.json", "ReproducibilityBundleManifest.json",
                "LearningPacket.json", "ConfigurationSnapshot.json", "EvidenceLedger.json",
                "ContextBundle.json", "ValidationReport.json", "PortfolioLedger.json",
                "CapabilityDecisionLog.json", "checkpoint.json"}
    if set(a) != required or a != b:
        raise ValueError("ARTIFACT_SET_OR_REPLAY_MISMATCH")
    read = lambda name: json.loads((left / name).read_text(encoding="utf-8"))
    manifest = read("RunManifest.json")
    if manifest["research_only"] is not True or manifest["no_trade_gate"] is not True:
        raise ValueError("OUTPUT_NO_TRADE_VIOLATION")
    if len(read("ReplayEventLedger.json")) != 8:
        raise ValueError("EVENT_COUNT_MISMATCH")
    decisions = read("ResearchDecisionLedger.json")
    if not decisions or any(d["executed_in_simulation"] for d in decisions):
        raise ValueError("MISSING_CALENDAR_MUST_NOT_EXECUTE")
    if not any(d["reason"] == "UNKNOWN_OR_NON_TRADING_CALENDAR_DAY" for d in decisions):
        raise ValueError("CALENDAR_ABSTENTION_MISSING")
    if read("LearningPacket.json")["authority_write"] is not False:
        raise ValueError("CANDIDATE_ONLY_VIOLATION")
    bundle = read("ReproducibilityBundleManifest.json")
    if any(a.get(name) != value for name, value in bundle["content_hashes"].items()):
        raise ValueError("BUNDLE_HASH_MISMATCH")
    return a


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the existing synthetic P2 replay twice and attest content equality; NO_TRADE.")
    parser.add_argument("--output", required=True, type=Path, help="New output directory; existing paths are refused")
    parser.add_argument("--challenge", required=True, help="Caller supplied run correlation value, not a signature")
    args = parser.parse_args()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    validate_lock(lock)
    git = lambda *a: subprocess.check_output(["git", "-C", str(REPO), *a], text=True, encoding="utf-8").strip()
    commit = git("rev-parse", "HEAD")
    if git("status", "--porcelain", "--untracked-files=all", "--", P2_REL, str(PACKAGE)):
        raise ValueError("SOURCE_MUST_BE_COMMITTED_AND_CLEAN")
    output = args.output.resolve()
    if output.is_relative_to(P2.resolve()) or output.is_relative_to(PACKAGE.resolve()):
        raise ValueError("OUTPUT_MUST_NOT_POLLUTE_SOURCE")
    output.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    commands = []
    for index in range(2):
        target = output / ("run-" + str(index + 1))
        command = [sys.executable, "-X", "utf8", str(P2 / "run_demo.py"), "run-demo",
                   "--output", str(target), "--as-of", lock["as_of"]]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60)
        (output / f"process-{index + 1}.json").write_bytes(canonical({
            "command": command, "returncode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}))
        commands.append({"command": command, "returncode": completed.returncode})
        if completed.returncode:
            raise RuntimeError("P2_PROCESS_FAILED: inspect process receipt")
    hashes = verify_outputs(output / "run-1", output / "run-2")
    validate_lock(lock)
    if git("rev-parse", "HEAD") != commit or git("status", "--porcelain", "--untracked-files=all", "--", P2_REL, str(PACKAGE)):
        raise ValueError("SOURCE_CHANGED_DURING_RUN")
    receipt = {"schema_version": "1.0.0", "agent_id": "CODEX", "status": "PASS",
        "evidence_class": "EXECUTOR_VERIFIED_SYNTHETIC_ONLY", "source_commit": commit,
        "challenge": args.challenge, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "lock_sha256": sha(canonical(lock)), "source_text_sha256": lock["source_text_sha256"],
        "verifier_text_sha256": text_hash(Path(__file__)), "commands": commands,
        "artifact_hashes": hashes, "artifact_set_sha256": sha(canonical(hashes)),
        "repeat_runs": 2, "expected_events": 8, "no_trade": True,
        "gpt_session_execution_verified": False, "wb_deployment_verified": False,
        "independent_review": "PENDING", "live_market_verified": False,
        "note": "Missing governed calendar correctly prevents simulated execution. This is not profitability evidence."}
    (output / "execution-receipt.json").write_bytes(canonical(receipt) + b"\n")
    print(json.dumps({"status": "PASS", "source_commit": commit,
                      "artifact_set_sha256": receipt["artifact_set_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
