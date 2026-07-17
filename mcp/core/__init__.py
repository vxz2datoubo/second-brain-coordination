"""core.qclaw — QClaw Gateway 桥接模块

通过 QClaw Gateway 的 OpenAI 兼容 API (localhost:6220/v1) 把分析任务
发给 QClaw 当前模型，取回结果。
"""
import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path


class QClawBridge:
    """QClaw 网关客户端，提供 ask() 同步接口"""

    def __init__(self):
        self.base_url = "http://localhost:6220/v1"
        self.token = self._detect_token()
        self.timeout = 180  # QClaw 分析可能需要较长时间

    def _detect_token(self) -> str:
        """从 OpenClaw 配置文件读取 token，支持路径变化"""
        config_paths = [
            Path(os.environ.get("USERPROFILE", "")) / ".qclaw" / "openclaw.json",
        ]
        for p in config_paths:
            if p.exists():
                try:
                    cfg = json.loads(p.read_text("utf-8"))
                    return cfg.get("gateway", {}).get("auth", {}).get("token", "")
                except Exception:
                    pass
        return ""

    def ask(self, prompt: str, max_tokens: int = 1500) -> tuple[str, dict]:
        """同步调用 QClaw 分析，返回 (content, metadata)。"""
        payload = json.dumps({
            "model": "auto",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 QClaw 的分析引擎。请基于事实和数据给出简洁、"
                        "可操作的结论。不闲聊，直接回答问题。"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max(100, min(max_tokens, 8000)),
            "temperature": 0.3,
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

        start = time.time()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers=headers,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return f"[QClaw API 错误 {exc.code}] {body[:500]}", {"status": exc.code}
        except Exception as exc:
            return f"[QClaw 连接失败] {exc}", {"status": 0}

        elapsed = round(time.time() - start, 1)
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = result.get("usage", {})

        meta = {
            "model": result.get("model", "?"),
            "tokens_used": usage.get("total_tokens", 0),
            "elapsed_s": elapsed,
        }
        return content.strip(), meta
