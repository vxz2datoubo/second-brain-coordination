"""
ChatGPT 第二大脑桥接服务（Chrome 扩展模式）
作用：
- 接收 WorkBuddy 技能发来的 prompt，排进任务队列
- 供 Chrome 扩展轮询 /pending 取任务
- 扩展执行完成后 POST /complete 回传回答
- 自动把回答摄入第二大脑 localhost:8766/api/digest/text
- 支持 /ingest 接收手动 ChatGPT 对话内容
"""
import os
import time
import uuid
import json
import threading
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

BRIDGE_PORT = 8799
SECOND_BRAIN = "http://localhost:8766"
BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="ChatGPT Bridge")

# 任务队列
pending_queue: list[dict] = []          # 等待被扩展取走的任务
in_progress: dict[str, dict] = {}       # 已认领但未完成的任务
completed: dict[str, dict] = {}        # 已完成的任务（临时缓存）
lock = threading.Lock()


def ingest_second_brain(text: str, title: str, source: str = "chatgpt"):
    """把内容摄入第二大脑"""
    try:
        payload = {"text": text, "title": title, "source": source}
        r = requests.post(
            f"{SECOND_BRAIN}/api/digest/text",
            json=payload,
            timeout=10,
        )
        print(f"[bridge] 摄入第二大脑: {r.status_code} {r.text[:120]}")
        return r.json()
    except Exception as e:
        print(f"[bridge] 摄入失败: {e}")
        return None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "pending": len(pending_queue),
        "in_progress": len(in_progress),
        "completed": len(completed),
        "mode": "extension",
    }


@app.post("/prompt")
async def prompt(req: Request):
    """WorkBuddy 技能调用：把用户问题排入任务队列"""
    data = await req.json()
    text = data.get("text", "").strip()
    if not text:
        return JSONResponse({"error": "text is empty"}, status_code=400)

    task_id = uuid.uuid4().hex[:12]
    with lock:
        pending_queue.append({"task_id": task_id, "text": text})
    print(f"[bridge] 新任务 {task_id}: {text[:60]}...")
    return {"success": True, "task_id": task_id}


@app.get("/pending")
def get_pending():
    """Chrome 扩展轮询：取一个待执行任务"""
    with lock:
        # 清理超时的 in_progress（5 分钟）
        now = time.time()
        expired = [tid for tid, t in in_progress.items() if now - t["claimed_at"] > 300]
        for tid in expired:
            print(f"[bridge] 任务 {tid} 超时，移回 pending")
            pending_queue.append(in_progress.pop(tid))

        if not pending_queue:
            return {}
        task = pending_queue.pop(0)
        task["claimed_at"] = now
        in_progress[task["task_id"]] = task
    return task


@app.post("/complete")
async def complete(req: Request):
    """Chrome 扩展回传：任务完成，回答入库"""
    data = await req.json()
    task_id = data.get("task_id")
    text = data.get("text", "").strip()
    title = data.get("title", "ChatGPT回答")
    if not task_id or not text:
        return JSONResponse({"error": "task_id or text empty"}, status_code=400)

    with lock:
        in_progress.pop(task_id, None)
        completed[task_id] = {"text": text, "title": title, "ts": time.time()}

    # 摄入第二大脑
    node = ingest_second_brain(text, title, source="chatgpt")
    print(f"[bridge] 任务 {task_id} 完成，回答已入库")
    return {"success": True, "node": node}


@app.get("/result")
def get_result(task_id: str):
    """WorkBuddy 技能轮询：获取任务结果"""
    with lock:
        if task_id in completed:
            return {"done": True, "text": completed[task_id]["text"]}
        if task_id in in_progress:
            return {"done": False, "status": "in_progress"}
        return {"done": False, "status": "not_found"}


@app.post("/ingest")
async def ingest(req: Request):
    """Chrome 扩展捕获手动 ChatGPT 对话，回传入库"""
    data = await req.json()
    text = data.get("text", "").strip()
    title = data.get("title", "ChatGPT手动对话")
    if not text:
        return JSONResponse({"error": "text is empty"}, status_code=400)

    node = ingest_second_brain(text, title, source="chatgpt")
    return {"success": True, "node": node}


if __name__ == "__main__":
    print(f"[bridge] ChatGPT 扩展桥启动于 http://localhost:{BRIDGE_PORT}")
    print(f"[bridge] 第二大脑: {SECOND_BRAIN}")
    uvicorn.run(app, host="127.0.0.1", port=BRIDGE_PORT)
