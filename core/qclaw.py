"""QClaw Bridge — 纯算力引擎调用层（v2.1，token+超时+幻觉防护加固版）

定位: QClaw 是迪迪的纯算力引擎, 不是独立 Agent.
- 不调 Agent / 不管理项目 / 不读写自己文件系统
- 只接收 prompt, 输出纯 Markdown, 由迪迪保存
- 端口动态探测 (QClaw 重启后端口会变)

⚠️ 重要约束: QClaw 是纯 LLM，**无法访问文件系统**。
    必须由迪迪把完整上下文喂给它——截断上下文=诱发性幻觉。

入口:
    from core.qclaw import QClawBridge
    qc = QClawBridge()
    content, path = qc.ask("分析...", save_as="xxx.md")

    # 一键消化到第二大脑
    qc.ask_and_ingest("...", save_as="xxx.md")
"""
import json, os, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

# 配置常量 (可被环境变量覆盖)
DEFAULT_PORT = 8234
QCLAW_TOKEN_ENV = "QCLAW_GATEWAY_TOKEN"
QCLAW_CONFIG_PATH = os.path.expanduser("~/.qclaw/qclaw.json")
OPENCLAW_CONFIG_PATH = os.path.expanduser("~/.qclaw/openclaw.json")
DEFAULT_OUTPUT_DIR = "F:/aidanao/qclaw-output"
HEALTH_TIMEOUT = 3       # 健康检查超时(秒)
CALL_TIMEOUT = 600       # 业务调用超时(秒) — QClaw 模型路由有先天延迟 (实测 ~24s/小请求)


def _read_qclaw_config() -> dict:
    """从 QClaw 配置文件读取运行时配置 (端口/token/路径)

    Returns:
        dict: 含 port / token / stateDir 等字段, 读不到则返回空字典
    """
    try:
        if os.path.exists(QCLAW_CONFIG_PATH):
            with open(QCLAW_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass
    return {}


def _get_runtime_port() -> int:
    """动态读取 QClaw 当前端口 (QClaw 重启会换端口, 旧值会失效)

    Returns:
        int: 当前 QClaw 端口, 读不到则用 DEFAULT_PORT
    """
    cfg = _read_qclaw_config()
    port = cfg.get("port")
    if isinstance(port, int) and 0 < port < 65536:
        return port
    return DEFAULT_PORT


def _ping_qclaw(port: int, timeout: float = HEALTH_TIMEOUT) -> bool:
    """健康检查: 探测 QClaw 是否真的在跑 (带 token 认证)

    QClaw gateway 的 auth mode 是 token, 不带 token 会被 401 拒绝.
    所以从 qclaw.json 读 port 的同时读 token 带上.

    Args:
        port: 端口号
        timeout: 超时秒数

    Returns:
        bool: True=通, False=不通
    """
    url = f"http://127.0.0.1:{port}/v1/models"
    try:
        cfg = _read_qclaw_config()
        # 复用 _resolve_token 的优先级链，避免健康检查和实际调用分叉
        token = _resolve_token(cfg)
        if not token:
            return False

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        }
        req = urllib.request.Request(url, headers=headers)
        urllib.request.urlopen(req, timeout=timeout)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError) as e:
        import logging
        logging.warning(f"QClaw health check failed on port {port}: {type(e).__name__}: {e}")
        return False


def _resolve_token(cfg: dict) -> str:
    """从配置读 token，依次尝试: 环境变量 → qclaw.json → openclaw.json

    QClaw 的 auth token 位于 openclaw.json 的 gateway.auth.token，
    但 _read_qclaw_config() 只读了 qclaw.json (端口信息)。
    所以需要额外读 openclaw.json。
    """
    env_token = os.environ.get(QCLAW_TOKEN_ENV, "").strip()
    if env_token:
        return env_token

    # 1) 先从 qclaw.json 找
    for key in ("token", "apiKey"):
        t = cfg.get(key)
        if isinstance(t, str) and len(t) > 16:
            return t

    # 2) 从 openclaw.json 找 (gateway → auth → token)
    try:
        if os.path.exists(OPENCLAW_CONFIG_PATH):
            with open(OPENCLAW_CONFIG_PATH, "r", encoding="utf-8") as f:
                ocfg = json.load(f)
            token = ocfg.get("gateway", {}).get("auth", {}).get("token")
            if isinstance(token, str) and len(token) > 16:
                return token
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        pass

    return ""


class QClawError(RuntimeError):
    """QClaw 调用异常，支持分类 (auth/timeout/network/unhealthy)"""

    def __init__(self, message: str, category: str = "unknown", detail: str = ""):
        super().__init__(message)
        self.category = category
        self.detail = detail


def _detect_hallucination_risk(content: str) -> list:
    """检测 QClaw 输出中的潜在幻觉信号

    QClaw 是纯 LLM, 无法访问文件系统. 任何 "文件/目录/模块 不存在" 的断言
    都可能是上下文不足导致的幻觉.

    Returns:
        str列表: 幻觉风险标签, 空列表=无异常
    """
    import re
    flags = []

    # 检测"不存在"断言模式
    not_exist_patterns = [
        r"(?:文件|目录|模块|文件夹)\s*[\"']?.+?[\"']?\s*(?:不存在|缺失|未找到|没有|not\s*found)",
        r"(?:不存在|缺失|未找到|nothing\s*found)",
        r"(?:not\s+exist|doesn['']t\s+exist|missing)",
    ]
    for pat in not_exist_patterns:
        if re.search(pat, content, re.IGNORECASE):
            flags.append("断言文件/模块不存在")
            break

    # 检测"完全未实现"断言
    if re.search(r'(?:完全|整个|全部)\s*(?:未实现|缺失|没有)', content):
        flags.append("断言功能完全未实现")

    # 检测自信的百分比断言
    if re.search(r'约\s*\d+%|大约\s*\d+%|约\s*\d+\s*%', content):
        flags.append("自估百分比(无数据支撑)")

    return flags


class QClawBridge:
    """QClaw 算力调用层 (纯算力, 不调度 Agent)"""

    def __init__(self, output_dir: str = DEFAULT_OUTPUT_DIR, api_url: Optional[str] = None):
        """初始化

        Args:
            output_dir: 产出物保存目录, 默认 F:/aidanao/qclaw-output/
            api_url: 强制指定 API URL (测试用), 默认 None=动态探测
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 动态探测端口 + 健康检查
        cfg = _read_qclaw_config()
        self.port = cfg.get("port", DEFAULT_PORT)
        self.token = _resolve_token(cfg)
        self.healthy = _ping_qclaw(self.port)

        if api_url:
            self.api_url = api_url
        else:
            self.api_url = f"http://127.0.0.1:{self.port}/v1/chat/completions"

    def health_check(self) -> dict:
        """主动健康检查, 返回状态字典"""
        healthy = _ping_qclaw(self.port)
        return {
            "port": self.port,
            "healthy": healthy,
            "token_available": bool(self.token),
            "config_source": QCLAW_CONFIG_PATH,
            "config_exists": os.path.exists(QCLAW_CONFIG_PATH),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }

    def _system_prompt(self) -> str:
        return (
            "你是 QClaw, WorkBuddy 的纯算力引擎. 你不是独立 Agent — "
            "不启动项目, 不调度子 Agent, 不管理自己的记忆. "
            "你唯一的角色: 接收迪迪交给你的计算任务, 输出分析结果.\n\n"
            "## 核心规则\n"
            "- 不管理自己的项目 (A股/女友/量化等), 只处理迪迪交给你的任务\n"
            "- 不读写自己的文件系统, 所有产出交给迪迪保存\n"
            "- 你之前的 T+0 策略 / Agent 调度 / 本地推理知识, 只有在被问到时才提供\n\n"
            "## 迪迪的工作区\n"
            "- 第二大脑: F:\\ai\\ | API: localhost:8766\n"
            "- 输出目录: F:\\ai\\qclaw-output\\ (迪迪保存你的产出)\n"
            "- 工具链: Playwright + core/qclaw.py\n\n"
            "## 输出规范\n"
            "每次回复末尾: [SAVE: 文件名.md]\n"
            "格式: 纯 Markdown, 不做文件操作, 不执行命令."
        )

    def ask(
        self,
        prompt: str,
        model: str = "openclaw/default",
        max_tokens: int = 3000,
        save_as: Optional[str] = None,
        timeout: int = CALL_TIMEOUT,
    ) -> Tuple[str, Optional[str]]:
        """调用 QClaw 算力, 可选自动保存产出

        Args:
            prompt: 任务提示词
            model: 模型名, 默认 openclaw/default
            max_tokens: 最大 token 数
            save_as: 指定保存文件名, 默认 None=从内容里 [SAVE_AS:xxx] 解析
            timeout: 请求超时秒数

        Returns:
            (content, saved_path) 元组

        Raises:
            RuntimeError: QClaw 不健康 (端口不通/token 无效/超时)
        """
        if not self.token:
            raise QClawError(
                "QClaw token missing. Provide ~/.qclaw/openclaw.json, ~/.qclaw/qclaw.json, or set QCLAW_GATEWAY_TOKEN.",
                category="auth",
                detail="token_source=missing",
            )
        # 1) 健康检查 (每次调用前都 ping 一下, 避免 QClaw 重启后端口变了)
        if not _ping_qclaw(self.port, timeout=HEALTH_TIMEOUT):
            raise QClawError(
                f"QClaw 不健康: 端口 {self.port} 无响应.\n"
                f"请确认 QClaw 已启动, 当前配置: {QCLAW_CONFIG_PATH}",
                category="unhealthy",
                detail=f"port={self.port}, config={QCLAW_CONFIG_PATH}",
            )

        # 2) 上下文大小检查 (大上下文 + QClaw 高延迟 = 容易超时)
        ctx_chars = len(prompt)
        if ctx_chars > 8000:
            print(f"[QClaw] ⚠️ 上下文较大 ({ctx_chars}字符), 预计响应时间 {ctx_chars//40:.0f}s+")

        # 3) 构造请求
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            self.api_url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )

        # 4) 发送请求 (带分类错误处理)
        try:
            response = urllib.request.urlopen(req, timeout=timeout)
            result = json.loads(response.read())
        except TimeoutError:
            raise QClawError(
                f"QClaw 调用超时 (port={self.port}, timeout={timeout}s).\n"
                f"上下文 {ctx_chars} 字符. QClaw 模型路由有先天延迟 (~24s/小请求),\n"
                f"建议: 1) 减少上下文, 分多次调用  2) 或用本地 LLM 替代",
                category="timeout",
                detail=f"port={self.port}, timeout={timeout}s, ctx={ctx_chars}chars",
            )
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise QClawError(
                    f"QClaw 认证失败 (port={self.port}): Token 无效或过期",
                    category="auth",
                    detail=str(e),
                )
            raise QClawError(
                f"QClaw HTTP 错误 (port={self.port}, code={e.code}): {e}",
                category="network",
                detail=str(e),
            )
        except (urllib.error.URLError, OSError) as e:
            raise QClawError(
                f"QClaw 网络错误 (port={self.port}): {e}",
                category="network",
                detail=str(e),
            )

        content = result["choices"][0]["message"]["content"]

        # 5) 幻觉防护: 检测 QClaw 是否对"不存在"做出了断言
        #    QClaw 是纯 LLM, 无文件系统访问 — 任何 "文件X不存在" 的断言都可能是幻觉
        hallucination_flags = _detect_hallucination_risk(content)
        if hallucination_flags:
            print(f"[QClaw] ⚠️ 幻觉风险: {', '.join(hallucination_flags)}")
            print("  → QClaw 是纯 LLM，无法验证文件存在性. 请迪迪手动核实.")

        # 6) 自动保存
        saved_path: Optional[str] = None
        if save_as or "[SAVE_AS:" in content:
            if not save_as:
                import re
                m = re.search(r"\[SAVE_AS:\s*(.+?)\]", content)
                save_as = m.group(1).strip() if m else f"qclaw-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"

            filepath = self.output_dir / save_as
            header = (
                f"# QClaw 输出 | {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                f"> 模型: {model} | 端口: {self.port} | "
                f"Token: {result.get('usage', {}).get('total_tokens', '?')}\n\n"
            )
            filepath.write_text(header + content, encoding="utf-8")
            saved_path = str(filepath)

        return content, saved_path

    def ask_and_ingest(
        self,
        prompt: str,
        save_as: Optional[str] = None,
        second_brain_url: str = "http://localhost:8766",
    ) -> Tuple[str, Optional[str], dict]:
        """调用 QClaw 并自动录入第二大脑 (一站式)

        Args:
            prompt: 任务提示词
            save_as: 保存文件名
            second_brain_url: 第二大脑 API 地址

        Returns:
            (content, saved_path, ingest_result) 三元组
        """
        content, path = self.ask(prompt, save_as=save_as)

        ingest_result = {"success": False, "error": "未尝试"}
        if path:
            try:
                payload = json.dumps({
                    "title": save_as.replace(".md", "") if save_as else "QClaw分析",
                    "text": content[:5000],
                    "source": "qclaw-bridge",
                }).encode("utf-8")
                req = urllib.request.Request(
                    f"{second_brain_url}/api/digest/text",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                resp = urllib.request.urlopen(req, timeout=5)
                ingest_result = json.loads(resp.read())
            except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
                ingest_result = {"success": False, "error": str(e)}

        return content, path, ingest_result


def quick_ask(prompt: str, save_as: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """便捷函数: 一次性调用, 不需要手动管理 Bridge 实例

    用法:
        from core.qclaw import quick_ask
        content, path = quick_ask("分析...", save_as="xxx.md")
    """
    return QClawBridge().ask(prompt, save_as=save_as)


if __name__ == "__main__":
    # CLI 模式: python -m core.qclaw "分析任务" [save_as]
    import sys
    if len(sys.argv) < 2:
        # 单独跑则只做健康检查
        bridge = QClawBridge()
        print(json.dumps(bridge.health_check(), indent=2, ensure_ascii=False))
    else:
        prompt = sys.argv[1]
        save_as = sys.argv[2] if len(sys.argv) > 2 else None
        content, path = quick_ask(prompt, save_as=save_as)
        print(f"[产出路径] {path or '(未保存)'}")
        print("---")
        print(content[:2000] + ("\n..." if len(content) > 2000 else ""))
