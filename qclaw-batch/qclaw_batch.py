#!/usr/bin/env python3
"""
QClaw 批量任务调度器 v1.0
==========================
解决问题: 减少WorkBuddy对QClaw的"监工成本"
核心机制:
  1. 接收任务列表（标题+prompt）
  2. 串行调QClaw（避免端口冲突）
  3. 每完成一个立即摄入第二大脑
  4. 完成时写入信号文件 [STATUS: COMPLETE]
  5. 失败自动重试3次

使用方式:
  python qclaw_batch.py "task_name1::prompt1" "task_name2::prompt2" ...
  或: python qclaw_batch.py --from-file tasks.txt
  或: python qclaw_batch.py --recipe girlfriend_v1  (预设任务包)

输出:
  F:\ai\qclaw-output\<task_name>.md
  F:\ai\qclaw-output\BATCH_STATUS.json  (供WorkBuddy扫描)
"""
import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "F:/ai")
from core.qclaw import QClawBridge

OUTPUT_DIR = Path("F:/ai/qclaw-output")
SIGNAL_FILE = OUTPUT_DIR / "BATCH_STATUS.json"

def load_recipe(name: str) -> list:
    """加载预设任务包"""
    recipes_file = Path("F:/ai/qclaw-batch/recipes.json")
    if not recipes_file.exists():
        return []
    with open(recipes_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    return recipes.get(name, [])


def parse_task_args(args: list) -> list:
    """解析命令行任务，格式: 'name::prompt' 或 'name::prompt::max_tokens'"""
    tasks = []
    for arg in args:
        parts = arg.split("::", 2)
        if len(parts) < 2:
            print(f"[WARN] 跳过格式错误: {arg}")
            continue
        task = {
            "name": parts[0].strip(),
            "prompt": parts[1].strip(),
            "max_tokens": int(parts[2]) if len(parts) > 2 else 4000,
        }
        tasks.append(task)
    return tasks


def load_from_file(path: str) -> list:
    """从文件加载任务列表，格式: 每行 name::prompt"""
    p = Path(path)
    if not p.exists():
        return []
    with open(p, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return parse_task_args(lines)


def write_status(status: dict):
    """写入状态信号文件"""
    with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def ingest_to_brain(title: str, content: str) -> str:
    """摄入第二大脑"""
    import requests
    try:
        resp = requests.post(
            "http://localhost:8766/api/digest/text",
            json={"text": content[:8000], "title": title, "source": "qclaw-batch"},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("node", {}).get("id", "unknown")
    except Exception as e:
        print(f"[WARN] 摄入失败: {e}")
    return "ingest_failed"


def run_batch(tasks: list, ingest: bool = True, retry: int = 3):
    """执行批量任务"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not tasks:
        print("[ERROR] 没有任务")
        return

    print(f"\n{'='*60}")
    print(f"QClaw 批量任务调度器 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"任务数量: {len(tasks)} | 摄入第二大脑: {ingest} | 重试: {retry}")
    print(f"{'='*60}\n")

    qc = QClawBridge()

    # 健康检查
    health = qc.health_check()
    if not health.get("healthy"):
        print(f"[FATAL] QClaw 不健康: {health}")
        write_status({"status": "FAILED", "reason": "QClaw unhealthy", "health": health})
        return

    results = []
    start_time = time.time()

    for i, task in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {task['name']}")
        print(f"  max_tokens: {task['max_tokens']}")

        # 调用QClaw，重试
        content = None
        output_path = None
        last_error = None
        for attempt in range(1, retry + 1):
            try:
                content, output_path = qc.ask(
                    task["prompt"],
                    save_as=f"{task['name']}.md",
                    max_tokens=task["max_tokens"],
                )
                if content and len(content) > 100:
                    break
                else:
                    last_error = f"输出过短: {len(content) if content else 0} chars"
            except Exception as e:
                last_error = str(e)
                print(f"  [RETRY {attempt}/{retry}] {last_error}")
                time.sleep(2)

        if not content or len(content) < 100:
            results.append({
                "name": task["name"],
                "status": "FAILED",
                "error": last_error,
            })
            print(f"  [FAIL] {task['name']} 失败")
            continue

        # 摄入第二大脑
        node_id = "skip"
        if ingest:
            node_id = ingest_to_brain(task["name"], content)

        # 在文件末尾标记 [STATUS: COMPLETE]
        if output_path and Path(output_path).exists():
            with open(output_path, "a", encoding="utf-8") as f:
                f.write(f"\n\n---\n[STATUS: COMPLETE]\n[INGEST_ID: {node_id}]\n[BATCH_TIME: {datetime.now().isoformat()}]\n[CHAR_LENGTH: {len(content)}]\n")

        results.append({
            "name": task["name"],
            "status": "SUCCESS",
            "output_path": str(output_path),
            "node_id": node_id,
            "char_length": len(content),
        })
        print(f"  [OK] {task['name']} | {len(content)} chars | node={node_id}")

    # 写最终状态
    total_duration = time.time() - start_time
    final_status = {
        "status": "COMPLETE",
        "total_tasks": len(tasks),
        "success": sum(1 for r in results if r["status"] == "SUCCESS"),
        "failed": sum(1 for r in results if r["status"] == "FAILED"),
        "total_duration_sec": round(total_duration, 1),
        "completed_at": datetime.now().isoformat(),
        "results": results,
    }
    write_status(final_status)

    print(f"\n{'='*60}")
    print(f"完成 | 成功 {final_status['success']}/{final_status['total_tasks']} | 耗时 {total_duration:.1f}s")
    print(f"状态文件: {SIGNAL_FILE}")
    print(f"{'='*60}\n")

    return final_status


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="QClaw 批量任务调度器")
    parser.add_argument("tasks", nargs="*", help="任务列表，格式: name::prompt::max_tokens")
    parser.add_argument("--from-file", help="从文件加载任务")
    parser.add_argument("--recipe", help="加载预设任务包")
    parser.add_argument("--no-ingest", action="store_true", help="不摄入第二大脑")
    parser.add_argument("--retry", type=int, default=3, help="失败重试次数")

    args = parser.parse_args()

    if args.recipe:
        tasks = load_recipe(args.recipe)
    elif args.from_file:
        tasks = load_from_file(args.from_file)
    elif args.tasks:
        tasks = parse_task_args(args.tasks)
    else:
        print("用法:")
        print("  python qclaw_batch.py 'name1::prompt1::5000' 'name2::prompt2'")
        print("  python qclaw_batch.py --from-file tasks.txt")
        print("  python qclaw_batch.py --recipe girlfriend_v1")
        sys.exit(1)

    run_batch(tasks, ingest=not args.no_ingest, retry=args.retry)
