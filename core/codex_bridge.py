"""Codex Bridge — 让 Codex CLI 在 WorkBuddy 管理框架下做事

定位: Codex 是"更聪明的高级同事"——和 QClaw 角色不同.
- QClaw = 纯算力引擎 (一次性, 给 prompt 出 Markdown)
- Codex  = 智能体 (有上下文会话/能改文件/能跑命令/能 review)

调用范式:
    from core.codex_bridge import CodexBridge, quick_ask
    cb = CodexBridge()
    result = cb.run("帮我重构这个模块", cwd="F:/aidanao")
    # → Codex 在沙箱里跑完整流程, 最后输出结构化结果

CLI 形式:
    codex exec --skip-git-repo-check --ephemeral -C <dir> "<prompt>"
    codex exec resume --last                 # 续接上一个会话
    codex review                             # 对当前仓库做 code review

约束 (波仔要求):
1. Codex 地位高于 QClaw, 因为更聪明
2. 但必须在 WorkBuddy 管理框架下做事, 不能独立行动
3. 沙箱安全: 默认 read-only 或 workspace-write, 不开 danger-full-access
4. 每个任务必须可追溯: 留下 session_id, 写到第二大脑
5. Codex 输出 → 自动摄入第二大脑 (和 QClaw 同等流程)
"""
import json
import os
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# 路径常量
CODEX_BIN = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\codex.cmd"
CODEX_BIN_PS1 = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\codex.ps1"
CODEX_BIN_BASH = r"C:\Users\Administrator\.workbuddy\binaries\node\versions\22.22.2\codex"
CODEX_HOME = Path(os.path.expanduser("~/.codex"))
CODEX_VERSION = "0.140.0"  # codex --version 实测 (2026-06-16 验证, 之前 0.139 已升级)
DEFAULT_MODEL = "gpt-5.5"   # 实测 hello 任务用的模型 (ChatGPT 账号下 gpt-5-codex 不可用)
DEFAULT_OUTPUT_DIR = Path("F:/aidanao/qclaw-output/codex-runs")
DEFAULT_BRAIN_URL = "http://localhost:8766"

# 沙箱策略 (WorkBuddy 框架默认: read-only, 防止 Codex 改坏文件)
# key 是用户友好的 alias, value 是 codex CLI 实际接受的字符串
SANDBOX_POLICIES = {
    "read-only": "read-only",              # 默认, 最安全 (codex CLI 写法)
    "readonly": "read-only",                # 别名 (兼容老接口)
    "workspace-write": "workspace-write",   # 允许改工作区
    "danger": "danger-full-access",        # 严禁默认开, 必须显式 opt-in
}


@dataclass
class CodexRunResult:
    """Codex 一次调用的完整结果"""
    prompt: str
    cwd: str
    sandbox: str
    success: bool
    stdout: str
    stderr: str
    duration_sec: float
    session_id: Optional[str] = None
    output_file: Optional[str] = None
    ingested_to_brain: bool = False
    brain_node_id: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt,
            "cwd": self.cwd,
            "sandbox": self.sandbox,
            "success": self.success,
            "duration_sec": self.duration_sec,
            "session_id": self.session_id,
            "output_file": self.output_file,
            "ingested_to_brain": self.ingested_to_brain,
            "brain_node_id": self.brain_node_id,
            "error": self.error,
            "stdout_preview": self.stdout[:500] if self.stdout else "",
        }


class CodexBridge:
    """Codex 智能体调用层 (在 WorkBuddy 框架下做事)

    核心方法:
        run(prompt, cwd, sandbox)        - 执行一次性任务
        resume()                          - 续接上次会话
        review()                          - 代码 review
        doctor()                          - 健康检查
    """

    def __init__(self, output_dir: str = str(DEFAULT_OUTPUT_DIR)):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._verify_install()

    def _verify_install(self):
        """确认 codex 装好了"""
        bin_path = Path(CODEX_BIN)
        if not bin_path.exists():
            raise FileNotFoundError(f"Codex CLI 不在: {CODEX_BIN}")
        # 用 .cmd 是因为 Windows 默认 shell 走 cmd.exe
        self._bin = CODEX_BIN

    def doctor(self) -> dict:
        """跑 codex doctor 看健康状态"""
        result = subprocess.run(
            [self._bin, "doctor"],
            capture_output=True, text=True, timeout=30
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "reachable": result.returncode == 0,
        }

    def run(
        self,
        prompt: str,
        cwd: str = "F:/aidanao",
        sandbox: str = "read-only",
        model: Optional[str] = None,
        ephemeral: bool = True,
        skip_git_check: bool = True,
        output_last_message: bool = True,
        timeout: int = 600,
    ) -> CodexRunResult:
        """执行 Codex 任务 (非交互式)

        Args:
            prompt: 任务描述 (中文/英文都行)
            cwd: 工作目录, 默认 F:/aidanao
            sandbox: 沙箱策略 (read-only / readonly / workspace-write / danger), 默认 read-only
            model: 模型名, 默认 gpt-5.5 (ChatGPT 账号下验证可用)
            ephemeral: True=不持久化 session 文件 (推荐)
            skip_git_check: True=允许在非 git 仓库跑
            output_last_message: True=把最后消息存文件
            timeout: 超时秒数, 默认 10 分钟

        Returns:
            CodexRunResult
        """
        if model is None:
            model = DEFAULT_MODEL
        if sandbox not in SANDBOX_POLICIES:
            raise ValueError(f"非法沙箱策略 {sandbox}, 必须是 {list(SANDBOX_POLICIES.keys())}")

        start = time.time()
        result = CodexRunResult(
            prompt=prompt, cwd=cwd, sandbox=sandbox, success=False,
            stdout="", stderr="", duration_sec=0,
        )

        # 1) 构造命令
        cmd = [self._bin, "exec", prompt]
        cmd += ["-C", cwd]
        cmd += ["-s", SANDBOX_POLICIES[sandbox]]
        cmd += ["-m", model]
        cmd += ["--json"]                    # JSONL 事件流, 方便解析
        if ephemeral:
            cmd += ["--ephemeral"]
        if skip_git_check:
            cmd += ["--skip-git-repo-check"]
        if output_last_message:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            out_file = self.output_dir / f"codex-{ts}.md"
            cmd += ["-o", str(out_file)]
            result.output_file = str(out_file)

        # 2) 执行
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout
            )
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = (proc.returncode == 0)
            result.error = None if result.success else f"exit code {proc.returncode}"

            # 3) 解析 JSONL 找 session/thread id (codex 0.140 用 thread.started, 老版本用 session_configured)
            for line in result.stdout.splitlines():
                if not line.strip().startswith("{"):
                    continue
                try:
                    evt = json.loads(line)
                except json.JSONDecodeError:
                    continue
                evt_type = evt.get("type", "")
                if evt_type == "thread.started":
                    result.session_id = evt.get("thread_id")
                    break
                if evt_type == "session_configured":
                    result.session_id = evt.get("session_id")
                    break
                if evt_type == "turn.started" and not result.session_id:
                    # 兜底: 实在找不到就用 thread_id
                    pass
        except subprocess.TimeoutExpired as e:
            result.error = f"timeout after {timeout}s"
            result.stderr = str(e)
        except FileNotFoundError as e:
            result.error = f"codex not found: {e}"

        result.duration_sec = round(time.time() - start, 2)
        return result

    def review(self, cwd: str = "F:/aidanao") -> CodexRunResult:
        """对工作目录做 code review"""
        start = time.time()
        result = CodexRunResult(
            prompt="<code review>", cwd=cwd, sandbox="readonly", success=False,
            stdout="", stderr="", duration_sec=0,
        )
        try:
            proc = subprocess.run(
                [self._bin, "review", "-C", cwd],
                capture_output=True, text=True, timeout=600,
            )
            result.stdout = proc.stdout
            result.stderr = proc.stderr
            result.success = (proc.returncode == 0)
        except Exception as e:
            result.error = str(e)
        result.duration_sec = round(time.time() - start, 2)
        return result

    def ingest_to_brain(
        self,
        run_result: CodexRunResult,
        brain_url: str = DEFAULT_BRAIN_URL,
        title_prefix: str = "Codex任务",
    ) -> bool:
        """把 Codex 任务结果摄入第二大脑 (关键: 让 Codex 留在管理框架内)

        Args:
            run_result: CodexRunResult
            brain_url: 第二大脑 API
            title_prefix: 节点标题前缀

        Returns:
            bool: 是否成功
        """
        if not run_result.output_file:
            print("⚠️ 没有 output_file, 无法摄入")
            return False

        out_path = Path(run_result.output_file)
        if not out_path.exists():
            print(f"⚠️ output_file 不存在: {out_path}")
            return False

        content = out_path.read_text(encoding="utf-8", errors="replace")
        title = f"{title_prefix} | {datetime.now().strftime('%m-%d %H:%M')}"

        text = f"""任务: {run_result.prompt}
工作目录: {run_result.cwd}
沙箱: {run_result.sandbox}
执行时长: {run_result.duration_sec}s
Session: {run_result.session_id or '(无)'}
状态: {'✅ 成功' if run_result.success else '❌ 失败'}

---
{content[:3000]}
"""
        try:
            data = json.dumps({
                "title": title,
                "text": text,
                "tags": "Codex,智能体,任务",
                "source": "codex-bridge",
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{brain_url}/api/digest/text",
                data=data, headers={"Content-Type": "application/json"},
            )
            resp = json.loads(urllib.request.urlopen(req, timeout=5).read())
            run_result.ingested_to_brain = True
            run_result.brain_node_id = resp.get("node", {}).get("id")
            return True
        except Exception as e:
            print(f"❌ 摄入失败: {e}")
            return False


def quick_ask(prompt: str, cwd: str = "F:/aidanao") -> CodexRunResult:
    """便捷调用: 跑 Codex + 自动摄入第二大脑"""
    cb = CodexBridge()
    result = cb.run(prompt, cwd=cwd)
    if result.success:
        cb.ingest_to_brain(result)
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        # 默认跑 doctor
        cb = CodexBridge()
        d = cb.doctor()
        print(json.dumps({
            "exit_code": d["exit_code"],
            "reachable": d["reachable"],
        }, indent=2, ensure_ascii=False))
    else:
        prompt = " ".join(sys.argv[1:])
        result = quick_ask(prompt)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
