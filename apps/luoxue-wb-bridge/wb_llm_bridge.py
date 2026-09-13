# -*- coding: utf-8 -*-
"""
WB LLM Bridge - MaiBot <-> WorkBuddy (codebuddy CLI) OpenAI-compatible proxy
============================================================================
MaiBot (api_provider base_url -> http://127.0.0.1:8900/v1)
  POST /v1/chat/completions  -> codebuddy -p --model <mapped> "<prompt>"
  GET  /v1/models            -> wb-flash / wb-glm
  POST /v1/embeddings        -> 501 (embeddings stay on SiliconFlow provider)

Stdlib only. Port 8900. Concurrency capped at 3 CLI processes.
"""
import json
import os
import re
import subprocess
import threading
import time
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8900
CODEBUDDY_CMD = r"C:\Users\Administrator\AppData\Roaming\npm\codebuddy.cmd"
CLI_TIMEOUT = 150          # seconds, > MaiBot max hard_timeout (120)
MAX_CONCURRENT = 3         # concurrent codebuddy CLI processes

MODEL_MAP = {
    # 2026-09-12 临时：deepseek-v4.1-flash 无额度，wb-flash 也映射到 GLM
    # 额度恢复后改回： "wb-flash": "deepseek-v4.1-flash"
    "wb-flash": "glm-5.3-flash",
    "wb-glm": "glm-5.3-flash",
    "wb-vlm": "glm-5.3-flash",   # 识图任务：CLI agent 用 Read 工具看图
}
DEFAULT_MODEL = "wb-flash"

# 识图临时图片目录（call_cli 返回后立即清理）
IMG_DIR = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "wb_bridge_imgs")

_log = logging.getLogger("wb_bridge")
_log.setLevel(logging.INFO)
_h = logging.FileHandler(r"F:\aipengyou\logs\wb_bridge.log", encoding="utf-8")
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_log.addHandler(_h)

_sem = threading.BoundedSemaphore(MAX_CONCURRENT)
_stats = {"ok": 0, "fail": 0, "timeout": 0}
_lock = threading.Lock()

# CLI 内部 HTTP 服务端口池（默认 8694 会与 WorkBuddy 桌面应用的 prewarm 守护进程
# 冲突 → EADDRINUSE → 静默死锁）。每次调用分配独立端口彻底规避。
_PORT_BASE = 18701
_port_counter = [0]
_port_lock = threading.Lock()


def _next_port():
    with _port_lock:
        p = _PORT_BASE + (_port_counter[0] % 50)
        _port_counter[0] += 1
        return p

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def build_prompt(messages):
    """Flatten OpenAI messages into a single prompt for the CLI."""
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):  # multimodal parts -> text only
            content = " ".join(
                p.get("text", "") for p in content if isinstance(p, dict)
            )
        if role == "system":
            parts.append("[System Instructions]\n%s" % content)
        elif role == "user":
            parts.append("[User]\n%s" % content)
        elif role == "assistant":
            parts.append("[Assistant]\n%s" % content)
        else:
            parts.append("[%s]\n%s" % (role, content))
    return "\n\n".join(parts)


import base64
import urllib.request

def extract_images(messages):
    """Pull images out of multimodal messages and save them to disk.

    Supports OpenAI-style parts:
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..." | "https://..."}}
    Returns list of absolute image paths (empty if no images).
    """
    paths = []
    for m in messages:
        content = m.get("content")
        if not isinstance(content, list):
            continue
        for p in content:
            if not (isinstance(p, dict) and p.get("type") == "image_url"):
                continue
            url = (p.get("image_url") or {}).get("url", "")
            try:
                os.makedirs(IMG_DIR, exist_ok=True)
                if url.startswith("data:"):          # data:image/png;base64,xxxx
                    b64 = url.split(",", 1)[1]
                    raw = base64.b64decode(b64)
                    ext = "png" if "png" in url[:40] else (
                          "jpg" if ("jpeg" in url[:40] or "jpg" in url[:40]) else "png")
                elif url.startswith("http"):          # remote image -> download
                    req = urllib.request.Request(url, headers={"User-Agent": "wb-bridge"})
                    raw = urllib.request.urlopen(req, timeout=30).read()
                    ext = "jpg" if url.lower().endswith((".jpg", ".jpeg")) else "png"
                else:
                    _log.warning("unsupported image url scheme: %.60s", url)
                    continue
                fp = os.path.join(IMG_DIR, "img_%d_%d.%s" % (int(time.time() * 1000), len(paths), ext))
                with open(fp, "wb") as f:
                    f.write(raw)
                paths.append(fp)
            except Exception as e:
                _log.warning("image extract failed: %r", e)
    return paths


def call_cli(cli_model, prompt):
    """Run codebuddy -p and return (text, error)."""
    env = {k: v for k, v in os.environ.items() if k != "ELECTRON_RUN_AS_NODE"}
    env["SERVER__PORT"] = str(_next_port())  # 独立内部端口，避开 8694 冲突
    env.setdefault("SYSTEMROOT", os.environ.get("SYSTEMROOT", r"C:\Windows"))
    argv = [CODEBUDDY_CMD, "-p", "--model", cli_model]
    # 始终走 stdin：argv 经过 .cmd/cmd.exe 转发时换行符会截断 prompt，
    # 且 Windows 32K argv 上限装不下 MaiBot 的长 prompt
    t0 = time.time()
    try:
        with _sem:
            proc = subprocess.run(
                argv,
                input=prompt.encode("utf-8"),
                capture_output=True,
                timeout=CLI_TIMEOUT,
                env=env,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        out = ANSI_RE.sub("", proc.stdout.decode("utf-8", errors="replace")).strip()
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0 or not out:
            return None, "rc=%s out_empty=%s stderr=%s" % (
                proc.returncode, not out, err[-400:])
        return out, None
    except subprocess.TimeoutExpired:
        return None, "hard timeout %ss" % CLI_TIMEOUT
    except Exception as e:
        return None, repr(e)
    finally:
        _log.info("cli %s done in %.1fs (prompt=%d chars)",
                  cli_model, time.time() - t0, len(prompt))


def usage_est(text_in, text_out):
    return {
        "prompt_tokens": max(1, len(text_in) // 2),
        "completion_tokens": max(1, len(text_out) // 2),
        "total_tokens": max(2, (len(text_in) + len(text_out)) // 2),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        _log.info("%s %s", self.address_string(), fmt % args)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/") in ("/v1/models", "/v1/models/"):
            now = int(time.time())
            data = [
                {"id": mid, "object": "model", "created": now, "owned_by": "workbuddy",
                 "meta": {"cli_model": cli}}
                for mid, cli in MODEL_MAP.items()
            ]
            self._json(200, {"object": "list", "data": data})
        else:
            self._json(404, {"error": {"message": "not found: %s" % self.path}})

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception as e:
            return self._json(400, {"error": {"message": "bad json: %s" % e}})

        path = self.path.rstrip("/")
        if path == "/v1/embeddings":
            return self._json(501, {"error": {
                "message": "WB bridge does not serve embeddings; "
                           "keep embedding models on SiliconFlow provider."}})

        if path != "/v1/chat/completions":
            return self._json(404, {"error": {"message": "not found: %s" % self.path}})

        wb_model = req.get("model", DEFAULT_MODEL)
        cli_model = MODEL_MAP.get(wb_model, MODEL_MAP[DEFAULT_MODEL])
        messages = req.get("messages", [])

        # 识图：提取图片 → prompt 前置"先看图"指令（CLI agent 用 Read 工具看图）
        img_paths = extract_images(messages)
        if img_paths:
            see_cmd = ("请先用 Read 工具逐一查看以下图片文件，再结合图片内容回答问题：\n"
                       + "\n".join(img_paths) + "\n\n")
            prompt = see_cmd + build_prompt(messages)
            _log.info("vision request: %d image(s) -> %s", len(img_paths), img_paths[0])
        else:
            prompt = build_prompt(messages)

        want_stream = bool(req.get("stream"))
        req_id = "wb-%d" % int(time.time() * 1000)
        created = int(time.time())

        text, err = call_cli(cli_model, prompt)
        # 临时图片用完即删
        for fp in img_paths:
            try:
                os.remove(fp)
            except OSError:
                pass
        with _lock:
            if err:
                _stats["timeout" if "timeout" in err else "fail"] += 1
            else:
                _stats["ok"] += 1

        if err:
            _log.error("chat fail model=%s err=%s", wb_model, err)
            return self._json(502, {"error": {
                "message": "WB CLI failed: %s" % err,
                "type": "wb_bridge_error"}})

        _log.info("chat ok model=%s(%s) in=%d chars out=%d chars stream=%s",
                  wb_model, cli_model, len(prompt), len(text), want_stream)

        if want_stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

            def chunk(content, finish=None):
                return "data: %s\n\n" % json.dumps({
                    "id": req_id, "object": "chat.completion.chunk",
                    "created": created, "model": wb_model,
                    "choices": [{"index": 0, "delta": content,
                                 "finish_reason": finish}],
                }, ensure_ascii=False)

            self.wfile.write(chunk({"role": "assistant"}).encode("utf-8"))
            self.wfile.write(chunk({"content": text}).encode("utf-8"))
            self.wfile.write(chunk({}, finish="stop").encode("utf-8"))
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        else:
            self._json(200, {
                "id": req_id, "object": "chat.completion",
                "created": created, "model": wb_model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }],
                "usage": usage_est(prompt, text),
            })


def main():
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    srv.daemon_threads = True
    _log.info("WB LLM Bridge listening on %s:%d (models: %s, max_concurrent=%d)",
              HOST, PORT, MODEL_MAP, MAX_CONCURRENT)
    _log.info("WB LLM Bridge on http://%s:%d/v1 | models: %s", HOST, PORT, MODEL_MAP)
    srv.serve_forever()


if __name__ == "__main__":
    main()
